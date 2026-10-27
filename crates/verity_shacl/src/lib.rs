//! Bounded SHACL property guidance. This module never validates data or executes a plan.
use oxigraph::{
    io::RdfFormat,
    model::{GraphName, NamedOrBlankNode, Term},
    store::Store,
};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use sha2::Digest;
use std::collections::{BTreeMap, BTreeSet, HashMap};
use verity_core::{
    catalog::Policy,
    discovery::{DiscoveryIndex, Source},
    reject, snapshot_id,
    vocabulary::VocabularyPacket,
    Error, Result,
};

pub const VERSION: &str = "shacl-property-guidance-v1";
const SH: &str = "http://www.w3.org/ns/shacl#";
const SH_INVERSE_PATH: &str = "http://www.w3.org/ns/shacl#inversePath";
const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
const MAX_PROPERTY_SHAPES: usize = 512;
const MAX_IRI_BYTES: usize = 1024;
const MAX_TARGET_CLASSES: usize = 8;
const MAX_PACKET_BYTES: usize = 16 * 1024 * 1024;

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq, Serialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum ShapeOrigin {
    SourcePublished,
    OperatorAuthoredDemo,
}

/// Operator-supplied provenance; values are claims, not automatic license verification.
#[derive(Clone, Debug, Deserialize, Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ShapeConfig {
    pub version: u32,
    pub shape_snapshot_id: String,
    pub data_snapshot_id: String,
    pub shape_graph: String,
    pub data_graph: String,
    pub origin: ShapeOrigin,
    pub source: Source,
}

pub struct RdfSource<'a> {
    pub bytes: &'a [u8],
    pub format: &'a str,
}

#[derive(Clone, Debug, Serialize, JsonSchema)]
pub struct PropertyGuidance {
    pub predicate_iri: String,
    pub path_direction: PathDirection,
    pub target_classes: Vec<String>,
    pub datatype: Option<String>,
    pub class: Option<String>,
    pub node_kind: Option<String>,
    pub min_count: Option<u64>,
    pub max_count: Option<u64>,
}

#[derive(
    Clone, Copy, Debug, Deserialize, PartialEq, Eq, PartialOrd, Ord, Serialize, JsonSchema,
)]
#[serde(rename_all = "snake_case")]
pub enum PathDirection {
    Forward,
    Inverse,
}

/// Rebuilt from selected shape bytes; serialized copies are display data, never trusted input.
#[derive(Debug, Serialize, JsonSchema)]
pub struct ShapeGuidanceIndex {
    version: &'static str,
    packet_id: String,
    shape_snapshot_id: String,
    shape_sha256: String,
    data_snapshot_id: String,
    policy_hash: String,
    index_revision: String,
    discovery_revision: String,
    shape_graph: String,
    data_graph: String,
    data_graph_hash: String,
    data_source: Source,
    origin: ShapeOrigin,
    source: Source,
    properties: Vec<PropertyGuidance>,
    unsupported_property_shapes: usize,
    semantics: &'static str,
}

impl ShapeGuidanceIndex {
    pub fn shape_sha256(&self) -> &str {
        &self.shape_sha256
    }

    pub fn unsupported_property_shapes(&self) -> usize {
        self.unsupported_property_shapes
    }

    /// Join only to a current, exact graph-qualified predicate candidate from the BM25 packet.
    pub fn for_candidate<'a>(
        &'a self,
        packet: &VocabularyPacket,
        candidate_id: &str,
        graph: &str,
    ) -> Result<Vec<&'a PropertyGuidance>> {
        let packet_json = serde_json::to_value(packet)?;
        let request = &packet_json["request"];
        let packet_scope = request["scope"]
            .as_array()
            .ok_or_else(|| reject("shape_snapshot", "Vocabulary packet scope is unavailable"))?;
        if request["snapshot_id"].as_str() != Some(self.data_snapshot_id.as_str())
            || packet_json["policy_hash"].as_str() != Some(self.policy_hash.as_str())
            || request["index_revision"].as_str() != Some(self.discovery_revision.as_str())
            || graph != self.data_graph
            || !packet_scope
                .iter()
                .any(|scope| scope.as_str() == Some(graph))
            || packet_json["graph_hashes"][graph] != self.data_graph_hash
            || packet_json["sources"][graph] != serde_json::to_value(&self.data_source)?
        {
            return Err(reject(
                "shape_snapshot",
                "Shape guidance and vocabulary packet do not share a snapshot, policy and scope",
            ));
        }
        let candidate = packet.resolve(candidate_id, "predicate", graph)?;
        Ok(self
            .properties
            .iter()
            .filter(|property| property.predicate_iri == candidate.iri)
            .collect())
    }
}

/// Index metadata only; unsupported shapes never remove candidates or validate triples.
pub fn build_shape_guidance(
    shape: RdfSource<'_>,
    data: RdfSource<'_>,
    config: &ShapeConfig,
    data_index: &DiscoveryIndex,
    packet: &VocabularyPacket,
    policy: &Policy,
) -> Result<ShapeGuidanceIndex> {
    let RdfSource {
        bytes: shape_bytes,
        format: shape_format,
    } = shape;
    let RdfSource {
        bytes: data_bytes,
        format: data_format,
    } = data;
    if shape_bytes.len() > 16 * 1024 * 1024 || data_bytes.len() > 16 * 1024 * 1024 {
        return Err(reject("input_limit", "RDF input exceeds 16 MiB"));
    }
    let shape_id = snapshot_id(shape_bytes, checked_format(shape_format)?.0);
    let data_id = snapshot_id(data_bytes, checked_format(data_format)?.0);
    if config.version != 1
        || config.shape_snapshot_id != shape_id
        || config.data_snapshot_id != data_id
        || config.shape_graph.len() > MAX_IRI_BYTES
        || config.data_graph.len() > MAX_IRI_BYTES
    {
        return Err(reject("shape_manifest", "Stale or invalid shape manifest"));
    }
    let policy_hash = snapshot_id(&serde_json::to_vec(policy)?, "discovery-policy-v1");
    let manifest = data_index.manifest();
    if manifest.snapshot_id != data_id
        || manifest.policy_hash != policy_hash
        || !manifest.scope.contains(&config.data_graph)
        || !policy.graphs.contains(&config.data_graph)
        || !manifest.graph_hashes.contains_key(&config.data_graph)
    {
        return Err(reject(
            "shape_scope",
            "Mapped data graph must be authorized in the current discovery index",
        ));
    }
    let data_graph_hash = manifest
        .graph_hashes
        .get(&config.data_graph)
        .ok_or_else(|| {
            reject(
                "shape_scope",
                "Data graph is absent from the discovery index",
            )
        })?
        .clone();
    let data_source = manifest
        .sources
        .get(&config.data_graph)
        .ok_or_else(|| {
            reject(
                "shape_scope",
                "Data graph source is absent from the discovery index",
            )
        })?
        .clone();
    if !packet_matches(packet, config, manifest, &policy_hash)? {
        return Err(reject(
            "shape_snapshot",
            "Shape guidance and vocabulary packet do not share a snapshot, policy and scope",
        ));
    }
    let shape_store = load_shape_store(shape_bytes, shape_format)?;
    let (shape_graphs, has_default_graph) = named_graphs(&shape_store)?;
    if has_default_graph || shape_graphs != BTreeSet::from([config.shape_graph.clone()]) {
        return Err(reject(
            "shape_scope",
            "Use one explicitly mapped named shape graph",
        ));
    }
    if [
        &config.source.source,
        &config.source.license,
        &config.source.source_revision,
        &config.source.importer_revision,
    ]
    .iter()
    .any(|value| value.trim().is_empty())
        || serde_json::to_vec(&config.source)?.len() > 8192
    {
        return Err(reject(
            "shape_manifest",
            "Shape source provenance is incomplete",
        ));
    }

    let mut triples = SubjectTriples::new();
    for quad in shape_store.iter() {
        let quad = quad.map_err(|_| reject("shape_input", "Shape RDF could not be read"))?;
        if graph_id(&quad.graph_name) == Some(config.shape_graph.as_str()) {
            triples
                .entry(quad.subject)
                .or_default()
                .entry(quad.predicate.as_str().into())
                .or_default()
                .push(quad.object);
        }
    }

    let mut properties = Vec::new();
    let mut unsupported_property_shapes = 0;
    for predicates in triples.values() {
        if !objects(predicates, RDF_TYPE)
            .iter()
            .any(|value| named_node_is(value, &format!("{SH}NodeShape")))
        {
            continue;
        }
        let target_values = objects(predicates, &format!("{SH}targetClass"));
        let mut targets = target_values
            .iter()
            .filter_map(named_node)
            .map(str::to_owned)
            .collect::<Vec<_>>();
        targets.sort();
        targets.dedup();
        let parent_supported = predicates.keys().all(|predicate| {
            !predicate.starts_with(SH)
                || matches!(
                    predicate.as_str(),
                    "http://www.w3.org/ns/shacl#property"
                        | "http://www.w3.org/ns/shacl#targetClass"
                )
        }) && target_values.len() == targets.len()
            && targets.len() <= MAX_TARGET_CLASSES
            && targets.iter().all(|target| target.len() <= MAX_IRI_BYTES);
        for property in objects(predicates, &format!("{SH}property")) {
            if properties.len() + unsupported_property_shapes >= MAX_PROPERTY_SHAPES {
                return Err(reject("shape_limit", "Too many SHACL property shapes"));
            }
            let guidance = subject_term(property)
                .filter(|_| parent_supported)
                .and_then(|property| parse_property(&triples, &property, &targets));
            if let Some(guidance) = guidance {
                properties.push(guidance);
            } else {
                unsupported_property_shapes += 1;
            }
        }
    }
    properties.sort_by(|a, b| {
        (
            &a.predicate_iri,
            a.path_direction,
            &a.target_classes,
            &a.datatype,
            &a.class,
            &a.node_kind,
            a.min_count,
            a.max_count,
        )
            .cmp(&(
                &b.predicate_iri,
                b.path_direction,
                &b.target_classes,
                &b.datatype,
                &b.class,
                &b.node_kind,
                b.min_count,
                b.max_count,
            ))
    });
    let index_revision = snapshot_id(
        concat!(
            include_str!("lib.rs"),
            include_str!("../Cargo.toml"),
            include_str!("../Cargo.lock"),
            include_str!("../../../rust-toolchain.toml")
        )
        .as_bytes(),
        VERSION,
    );
    let packet_id = snapshot_id(
        &serde_json::to_vec(&(
            config,
            format!("{:x}", sha2::Sha256::digest(shape_bytes)),
            &policy_hash,
            &index_revision,
            &manifest.index_revision,
            &data_graph_hash,
            &data_source,
            &properties,
            unsupported_property_shapes,
        ))?,
        VERSION,
    );
    let index = ShapeGuidanceIndex {
            version: VERSION,
            packet_id,
            shape_snapshot_id: shape_id,
            shape_sha256: format!("{:x}", sha2::Sha256::digest(shape_bytes)),
            data_snapshot_id: data_id,
            policy_hash,
            index_revision: format!("{index_revision}:{}", manifest.index_revision),
        discovery_revision: manifest.index_revision.clone(),
            shape_graph: config.shape_graph.clone(),
            data_graph: config.data_graph.clone(),
        data_graph_hash,
        data_source,
            origin: config.origin,
            source: config.source.clone(),
            properties,
            unsupported_property_shapes,
            semantics: "guidance_only; no_data_validation_or_entailment; no_question_interpretation_or_execution_authority; empty_guidance_is_not_no_match",
        };
    if serde_json::to_vec(&index)?.len() > MAX_PACKET_BYTES {
        return Err(reject("shape_limit", "Shape guidance exceeds 16 MiB"));
    }
    Ok(index)
}

type SubjectTriples = HashMap<NamedOrBlankNode, BTreeMap<String, Vec<Term>>>;

fn checked_format(format: &str) -> Result<(&'static str, RdfFormat)> {
    match format {
        "trig" => Ok(("trig", RdfFormat::TriG)),
        "nquads" => Ok(("nquads", RdfFormat::NQuads)),
        "turtle" => Ok(("turtle", RdfFormat::Turtle)),
        _ => Err(reject("format", "Use trig, nquads, or turtle")),
    }
}

fn load_shape_store(bytes: &[u8], format: &str) -> Result<Store> {
    let (_, format) = checked_format(format)?;
    let store = Store::new().map_err(|_| Error::Store("RDF storage could not be opened".into()))?;
    store
        .load_from_reader(format, bytes)
        .map_err(|_| Error::Store("RDF input could not be parsed".into()))?;
    if store
        .len()
        .map_err(|_| Error::Store("RDF storage could not be read".into()))?
        > 100_000
    {
        return Err(reject("quad_limit", "Snapshot exceeds 100,000 quads"));
    }
    Ok(store)
}

fn packet_matches(
    packet: &VocabularyPacket,
    config: &ShapeConfig,
    manifest: &verity_core::discovery::Manifest,
    policy_hash: &str,
) -> Result<bool> {
    let packet_json = serde_json::to_value(packet)?;
    let request = &packet_json["request"];
    let Some(scope) = request["scope"].as_array() else {
        return Ok(false);
    };
    if request["snapshot_id"].as_str() != Some(manifest.snapshot_id.as_str())
        || request["index_revision"].as_str() != Some(manifest.index_revision.as_str())
        || packet_json["policy_hash"].as_str() != Some(policy_hash)
        || !scope
            .iter()
            .any(|value| value.as_str() == Some(&config.data_graph))
        || scope
            .iter()
            .filter_map(serde_json::Value::as_str)
            .any(|graph| !manifest.scope.iter().any(|authorized| authorized == graph))
    {
        return Ok(false);
    }
    for graph in scope.iter().filter_map(serde_json::Value::as_str) {
        let Some(graph_hash) = manifest.graph_hashes.get(graph) else {
            return Ok(false);
        };
        let Some(source) = manifest.sources.get(graph) else {
            return Ok(false);
        };
        if packet_json["graph_hashes"][graph] != *graph_hash
            || packet_json["sources"][graph] != serde_json::to_value(source)?
        {
            return Ok(false);
        }
    }
    Ok(true)
}

fn named_graphs(store: &Store) -> Result<(BTreeSet<String>, bool)> {
    let mut graphs = BTreeSet::new();
    let mut has_default_graph = false;
    for quad in store.iter() {
        let quad =
            quad.map_err(|_| reject("shape_input", "Shape graph names could not be read"))?;
        if let Some(graph) = graph_id(&quad.graph_name) {
            graphs.insert(graph.into());
        } else {
            has_default_graph = true;
        }
    }
    Ok((graphs, has_default_graph))
}

fn graph_id(graph: &GraphName) -> Option<&str> {
    match graph {
        GraphName::NamedNode(node) => Some(node.as_str()),
        _ => None,
    }
}

fn objects<'a>(predicates: &'a BTreeMap<String, Vec<Term>>, predicate: &str) -> &'a [Term] {
    predicates.get(predicate).map_or(&[], Vec::as_slice)
}

fn named_node_is(term: &Term, iri: &str) -> bool {
    matches!(term, Term::NamedNode(value) if value.as_str() == iri)
}

fn named_node(term: &Term) -> Option<&str> {
    match term {
        Term::NamedNode(value) => Some(value.as_str()),
        _ => None,
    }
}

fn subject_term(term: &Term) -> Option<NamedOrBlankNode> {
    match term {
        Term::NamedNode(value) => Some(NamedOrBlankNode::NamedNode(value.clone())),
        Term::BlankNode(value) => Some(NamedOrBlankNode::BlankNode(value.clone())),
        _ => None,
    }
}

fn parse_property(
    triples: &SubjectTriples,
    property: &NamedOrBlankNode,
    target_classes: &[String],
) -> Option<PropertyGuidance> {
    let predicates = triples.get(property)?;
    let allowed = [
        RDF_TYPE,
        "http://www.w3.org/ns/shacl#path",
        "http://www.w3.org/ns/shacl#datatype",
        "http://www.w3.org/ns/shacl#class",
        "http://www.w3.org/ns/shacl#nodeKind",
        "http://www.w3.org/ns/shacl#minCount",
        "http://www.w3.org/ns/shacl#maxCount",
    ];
    if predicates
        .keys()
        .any(|predicate| predicate.starts_with(SH) && !allowed.contains(&predicate.as_str()))
    {
        return None;
    }
    let [path] = objects(predicates, &format!("{SH}path")) else {
        return None;
    };
    let (predicate_iri, path_direction) = parse_path(path, triples)?;
    if predicate_iri.len() > MAX_IRI_BYTES {
        return None;
    }
    let datatype = optional_iri(objects(predicates, &format!("{SH}datatype")))?;
    let class = optional_iri(objects(predicates, &format!("{SH}class")))?;
    let node_kind = optional_iri(objects(predicates, &format!("{SH}nodeKind")))?;
    if node_kind.as_deref().is_some_and(|kind| {
        ![
            "IRI",
            "BlankNode",
            "Literal",
            "BlankNodeOrIRI",
            "BlankNodeOrLiteral",
            "IRIOrLiteral",
        ]
        .iter()
        .any(|name| format!("{SH}{name}") == kind)
    }) {
        return None;
    }
    let min_count = optional_count(objects(predicates, &format!("{SH}minCount")))?;
    let max_count = optional_count(objects(predicates, &format!("{SH}maxCount")))?;
    if min_count.zip(max_count).is_some_and(|(min, max)| min > max) {
        return None;
    }
    Some(PropertyGuidance {
        predicate_iri: predicate_iri.into(),
        path_direction,
        target_classes: target_classes.to_vec(),
        datatype,
        class,
        node_kind,
        min_count,
        max_count,
    })
}

fn parse_path<'a>(path: &'a Term, triples: &'a SubjectTriples) -> Option<(&'a str, PathDirection)> {
    match path {
        Term::NamedNode(iri) => Some((iri.as_str(), PathDirection::Forward)),
        Term::BlankNode(node) => {
            let inverse_path = triples.get(&NamedOrBlankNode::BlankNode(node.clone()))?;
            if inverse_path.len() != 1 {
                return None;
            }
            let [Term::NamedNode(iri)] = objects(inverse_path, SH_INVERSE_PATH) else {
                return None;
            };
            Some((iri.as_str(), PathDirection::Inverse))
        }
        _ => None,
    }
}

fn optional_iri(values: &[Term]) -> Option<Option<String>> {
    match values {
        [] => Some(None),
        [Term::NamedNode(value)] if value.as_str().len() <= MAX_IRI_BYTES => {
            Some(Some(value.as_str().into()))
        }
        _ => None,
    }
}

fn optional_count(values: &[Term]) -> Option<Option<u64>> {
    match values {
        [] => Some(None),
        [Term::Literal(value)]
            if value.language().is_none()
                && matches!(
                    value.datatype().as_str(),
                    "http://www.w3.org/2001/XMLSchema#integer"
                        | "http://www.w3.org/2001/XMLSchema#nonNegativeInteger"
                ) =>
        {
            value.value().parse::<u64>().ok().map(Some)
        }
        _ => None,
    }
}
