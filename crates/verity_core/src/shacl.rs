//! Bounded SHACL property guidance. This module never validates data or executes a plan.
use crate::{
    catalog::{graph_id, Policy},
    discovery::Source,
    reject, snapshot_id,
    vocabulary::VocabularyPacket,
    Result, Snapshot,
};
use oxigraph::model::{NamedOrBlankNode, Term};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet, HashMap};

pub const VERSION: &str = "shacl-property-guidance-v1";
const SH: &str = "http://www.w3.org/ns/shacl#";
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

#[derive(Clone, Debug, Serialize, JsonSchema)]
pub struct PropertyGuidance {
    pub predicate_iri: String,
    pub target_classes: Vec<String>,
    pub datatype: Option<String>,
    pub class: Option<String>,
    pub node_kind: Option<String>,
    pub min_count: Option<u64>,
    pub max_count: Option<u64>,
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
    shape_graph: String,
    data_graph: String,
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
        if packet.request().snapshot_id != self.data_snapshot_id
            || packet.policy_hash() != self.policy_hash
            || graph != self.data_graph
            || !packet.request().scope.iter().any(|scope| scope == graph)
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

impl Snapshot {
    /// Index metadata only; unsupported shapes never remove candidates or validate triples.
    pub fn build_shape_guidance(
        &self,
        data: &Snapshot,
        config: &ShapeConfig,
        policy: &Policy,
    ) -> Result<ShapeGuidanceIndex> {
        if config.version != 1
            || config.shape_snapshot_id != self.id()
            || config.data_snapshot_id != data.id()
            || config.shape_graph.len() > MAX_IRI_BYTES
            || config.data_graph.len() > MAX_IRI_BYTES
        {
            return Err(reject("shape_manifest", "Stale or invalid shape manifest"));
        }
        policy
            .authorize(std::slice::from_ref(&config.data_graph))
            .map_err(|_| reject("shape_scope", "Mapped data graph is not authorized"))?;
        let (shape_graphs, has_default_graph) = named_graphs(self)?;
        if has_default_graph
            || shape_graphs != BTreeSet::from([config.shape_graph.clone()])
            || !has_named_graph(data, &config.data_graph)?
        {
            return Err(reject(
                "shape_scope",
                "Use one explicitly mapped named shape graph and an authorized named data graph",
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
        for quad in self.store.iter() {
            let quad = quad.map_err(|_| reject("shape_input", "Shape RDF could not be read"))?;
            if graph_id(&quad.graph_name) == Some(&config.shape_graph) {
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
                    .and_then(|property| parse_property(triples.get(&property), &targets));
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
                &a.target_classes,
                &a.datatype,
                &a.class,
                &a.node_kind,
                a.min_count,
                a.max_count,
            )
                .cmp(&(
                    &b.predicate_iri,
                    &b.target_classes,
                    &b.datatype,
                    &b.class,
                    &b.node_kind,
                    b.min_count,
                    b.max_count,
                ))
        });
        let policy_hash = snapshot_id(&serde_json::to_vec(policy)?, "discovery-policy-v1");
        let index_revision = snapshot_id(
            concat!(
                include_str!("shacl.rs"),
                include_str!("discovery.rs"),
                include_str!("../../../Cargo.lock"),
                include_str!("../../../rust-toolchain.toml")
            )
            .as_bytes(),
            VERSION,
        );
        let packet_id = snapshot_id(
            &serde_json::to_vec(&(
                config,
                self.source_sha256(),
                &policy_hash,
                &index_revision,
                &properties,
                unsupported_property_shapes,
            ))?,
            VERSION,
        );
        let index = ShapeGuidanceIndex {
            version: VERSION,
            packet_id,
            shape_snapshot_id: self.id().into(),
            shape_sha256: self.source_sha256().into(),
            data_snapshot_id: data.id().into(),
            policy_hash,
            index_revision,
            shape_graph: config.shape_graph.clone(),
            data_graph: config.data_graph.clone(),
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
}

type SubjectTriples = HashMap<NamedOrBlankNode, BTreeMap<String, Vec<Term>>>;

fn named_graphs(snapshot: &Snapshot) -> Result<(BTreeSet<String>, bool)> {
    let mut graphs = BTreeSet::new();
    let mut has_default_graph = false;
    for quad in snapshot.store.iter() {
        let quad =
            quad.map_err(|_| reject("shape_input", "Snapshot graph names could not be read"))?;
        if let Some(graph) = graph_id(&quad.graph_name) {
            graphs.insert(graph.into());
        } else {
            has_default_graph = true;
        }
    }
    Ok((graphs, has_default_graph))
}

fn has_named_graph(snapshot: &Snapshot, wanted: &str) -> Result<bool> {
    for quad in snapshot.store.iter() {
        let quad =
            quad.map_err(|_| reject("shape_input", "Snapshot graph names could not be read"))?;
        if graph_id(&quad.graph_name) == Some(wanted) {
            return Ok(true);
        }
    }
    Ok(false)
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
    predicates: Option<&BTreeMap<String, Vec<Term>>>,
    target_classes: &[String],
) -> Option<PropertyGuidance> {
    let predicates = predicates?;
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
    let [Term::NamedNode(path)] = objects(predicates, &format!("{SH}path")) else {
        return None;
    };
    let predicate_iri = path.as_str();
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
        target_classes: target_classes.to_vec(),
        datatype,
        class,
        node_kind,
        min_count,
        max_count,
    })
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
