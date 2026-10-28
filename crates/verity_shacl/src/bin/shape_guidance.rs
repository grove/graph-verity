#![forbid(unsafe_code)]
use oxigraph::{
    io::RdfFormat,
    model::{NamedOrBlankNode, Term},
    store::Store,
};
use sha2::{Digest, Sha256};
use std::{
    collections::{BTreeMap, BTreeSet},
    env,
    io::Write,
    process::ExitCode,
};
use verity_core::{
    catalog::Policy,
    discovery::{DiscoveryConfig, DiscoveryIndex, Source},
    find::FindRequest,
    read_limited, reject,
    vocabulary::{VocabularyBudget, VocabularyRequest},
    Result, Snapshot,
};
use verity_shacl::{build_shape_guidance, RdfSource, ShapeConfig};

const MAX_RDF_BYTES: usize = 16 * 1024 * 1024;
const MAX_JSON_BYTES: usize = 2 * 1024 * 1024;
const MAX_OUTPUT_BYTES: usize = 4 * 1024 * 1024;
const DIRECT_CLAIM: &str = "http://wikiba.se/ontology#directClaim";
const PROPERTY_METADATA_GRAPH: &str = "urn:graph-verity:assisted-ask:property-metadata:q279724";
const PROPERTY_METADATA_SOURCE: &str = "studies/nl-ask-v1/sources/Q279724.ttl";
const USAGE: &str = "shape_guidance DATA FORMAT POLICY SCOPE DISCOVERY SHAPES SHAPE_FORMAT SHAPE_CONFIG PROPERTY_METADATA REQUEST BUDGET";

fn json<T: serde::de::DeserializeOwned>(path: &str, limit: usize) -> Result<T> {
    Ok(serde_json::from_slice(&read_limited(path, limit)?)?)
}

struct PropertyMapping {
    predicate: String,
    statement: String,
    source_statements: Vec<String>,
}

fn metadata_text_predicate(predicate: &str) -> bool {
    matches!(
        predicate,
        "http://www.w3.org/2000/01/rdf-schema#label"
            | "http://www.w3.org/2004/02/skos/core#prefLabel"
            | "http://schema.org/name"
            | "https://schema.org/name"
            | "http://www.w3.org/2004/02/skos/core#altLabel"
            | "http://schema.org/alternateName"
            | "https://schema.org/alternateName"
            | "http://www.w3.org/2000/01/rdf-schema#comment"
            | "http://www.w3.org/2004/02/skos/core#definition"
            | "http://purl.org/dc/terms/description"
            | "http://schema.org/description"
            | "https://schema.org/description"
    )
}

fn supported_language(language: Option<&str>) -> bool {
    language.is_none_or(|language| {
        matches!(language.split('-').next(), Some("en" | "no" | "nb" | "nn"))
    })
}

fn sha256(bytes: &[u8]) -> String {
    format!("sha256:{:x}", Sha256::digest(bytes))
}

fn property_metadata_suggestions(
    source_bytes: &[u8],
    data_discovery: &DiscoveryIndex,
    data_graph: &str,
    policy: &Policy,
    question: &str,
    budget: &VocabularyBudget,
) -> Result<serde_json::Value> {
    let source_hash = sha256(source_bytes);
    let predicates = &data_discovery
        .graphs()
        .get(data_graph)
        .ok_or_else(|| {
            reject(
                "scope",
                "Property metadata requires the selected data graph",
            )
        })?
        .documents;
    let source = Store::new()
        .map_err(|_| reject("property_metadata", "Unable to read property metadata"))?;
    source
        .load_from_reader(RdfFormat::Turtle, source_bytes)
        .map_err(|_| reject("property_metadata", "Unable to parse property metadata"))?;

    let mut mappings = BTreeMap::new();
    for quad in source.iter() {
        let quad =
            quad.map_err(|_| reject("property_metadata", "Unable to read property metadata"))?;
        if quad.predicate.as_str() != DIRECT_CLAIM {
            continue;
        }
        let (NamedOrBlankNode::NamedNode(property), Term::NamedNode(predicate)) =
            (&quad.subject, &quad.object)
        else {
            continue;
        };
        if !predicates
            .get(predicate.as_str())
            .is_some_and(|document| document.roles.contains("predicate"))
        {
            continue;
        }
        mappings.insert(
            property.as_str().to_owned(),
            PropertyMapping {
                predicate: predicate.as_str().to_owned(),
                statement: format!("{} {} {} .", quad.subject, quad.predicate, quad.object),
                source_statements: Vec::new(),
            },
        );
    }

    // This isolated index ranks only source metadata already mapped to predicates in the data graph.
    let mut index_bytes = String::new();
    let mut text_languages = BTreeSet::new();
    for quad in source.iter() {
        let quad =
            quad.map_err(|_| reject("property_metadata", "Unable to read property metadata"))?;
        let (NamedOrBlankNode::NamedNode(property), Term::Literal(literal)) =
            (&quad.subject, &quad.object)
        else {
            continue;
        };
        let Some(mapping) = mappings.get_mut(property.as_str()) else {
            continue;
        };
        if !metadata_text_predicate(quad.predicate.as_str())
            || !supported_language(literal.language())
        {
            continue;
        }
        if let Some(language) = literal.language() {
            text_languages.insert(language.to_owned());
        }
        let statement = format!("{} {} {} .", quad.subject, quad.predicate, quad.object);
        mapping.source_statements.push(statement);
        index_bytes.push_str(&format!(
            "{} {} {} <{}> .\n",
            quad.subject, quad.predicate, quad.object, PROPERTY_METADATA_GRAPH
        ));
    }
    for mapping in mappings.values_mut() {
        mapping.source_statements.sort();
    }
    if index_bytes.is_empty() {
        return Ok(serde_json::json!({
            "source_file": PROPERTY_METADATA_SOURCE,
            "license": "CC0-1.0",
            "source_sha256": source_hash,
            "source_graph": "Turtle default graph",
            "data_graph": data_graph,
            "text_languages": [],
            "status": "no_scoped_property_metadata",
            "score_semantics": "BM25 ranking scores are not probabilities or relevance judgments",
            "matches": 0,
            "clipped": false,
            "candidates": []
        }));
    }

    let snapshot = Snapshot::from_bytes(index_bytes.as_bytes(), "nquads")?;
    let scope = vec![PROPERTY_METADATA_GRAPH.to_owned()];
    let mut metadata_policy = policy.clone();
    metadata_policy.graphs = scope.clone();
    let config = DiscoveryConfig {
        version: 1,
        snapshot_id: snapshot.id().to_owned(),
        graphs: BTreeMap::from([(
            PROPERTY_METADATA_GRAPH.to_owned(),
            Source {
                source: PROPERTY_METADATA_SOURCE.to_owned(),
                license: "CC0-1.0".to_owned(),
                source_revision: source_hash.clone(),
                importer_revision: "assisted-ask-property-metadata-index-v1".to_owned(),
            },
        )]),
    };
    let index = snapshot.build_discovery(&scope, &metadata_policy, &config)?;
    let found = index.find(
        &FindRequest {
            query: question.to_owned(),
            scope: scope.clone(),
            role: Some("entity".to_owned()),
            limit: budget.per_role_top_k,
        },
        &metadata_policy,
    )?;
    let mut seen = BTreeSet::new();
    let candidates = found
        .hits
        .iter()
        .filter_map(|hit| {
            let mapping = mappings.get(hit.iri)?;
            if !seen.insert(mapping.predicate.clone()) {
                return None;
            }
            let texts = hit
                .document
                .texts
                .iter()
                .filter(|text| text.value.text.len() <= budget.max_text_bytes)
                .take(budget.texts_per_candidate)
                .collect::<Vec<_>>();
            Some(serde_json::json!({
                "rank": seen.len(),
                "candidate": {
                    "iri": mapping.predicate,
                    "graph": data_graph,
                    "exact": hit.exact,
                    "ranking_score": hit.score,
                    "texts": texts,
                    "texts_clipped": texts.len() < hit.document.texts.len() || texts.iter().any(|text| text.truncated),
                },
                "metadata": {
                    "property_entity": hit.iri,
                    "direct_claim_statement": mapping.statement,
                    "source_statements": mapping.source_statements,
                }
            }))
        })
        .collect::<Vec<_>>();
    Ok(serde_json::json!({
        "source_file": PROPERTY_METADATA_SOURCE,
        "license": "CC0-1.0",
        "source_sha256": source_hash,
        "source_graph": "Turtle default graph",
        "retrieval_graph": PROPERTY_METADATA_GRAPH,
        "retrieval_snapshot_id": snapshot.id(),
        "index_revision": index.manifest().index_revision,
        "data_graph": data_graph,
        "text_languages": text_languages,
        "status": if candidates.is_empty() { "no_match" } else { "ranked" },
        "rules": found.rules,
        "ranking_revision": found.ranking_revision,
        "score_semantics": "BM25 over CC0 property labels and descriptions; scores are not probabilities or relevance judgments",
        "matches": candidates.len(),
        "clipped": found.truncated,
        "candidates": candidates
    }))
}

fn run() -> Result<()> {
    let args = env::args().skip(1).collect::<Vec<_>>();
    if args.len() != 11 {
        return Err(reject("usage", USAGE));
    }
    let data_bytes = read_limited(&args[0], MAX_RDF_BYTES)?;
    let data = Snapshot::from_bytes(&data_bytes, &args[1])?;
    let policy: Policy = json(&args[2], MAX_JSON_BYTES)?;
    let scope: Vec<String> = json(&args[3], MAX_JSON_BYTES)?;
    let discovery_config: DiscoveryConfig = json(&args[4], MAX_JSON_BYTES)?;
    let shape_bytes = read_limited(&args[5], MAX_RDF_BYTES)?;
    let shape_config: ShapeConfig = json(&args[7], MAX_JSON_BYTES)?;
    let property_metadata_bytes = read_limited(&args[8], MAX_RDF_BYTES)?;
    let request: VocabularyRequest = json(&args[9], MAX_JSON_BYTES)?;
    let budget: VocabularyBudget = json(&args[10], MAX_JSON_BYTES)?;
    let mut operator_scope = scope.clone();
    let mut request_scope = request.scope.clone();
    operator_scope.sort();
    request_scope.sort();
    if request_scope.len() != 1
        || request_scope[0] != shape_config.data_graph
        || !operator_scope.contains(&shape_config.data_graph)
        || operator_scope.windows(2).any(|pair| pair[0] == pair[1])
    {
        return Err(reject(
            "scope",
            "Use exactly the authorized data graph mapped by the shape manifest",
        ));
    }

    let discovery = data.build_discovery(&request_scope, &policy, &discovery_config)?;
    let packet = data.vocabulary_packet(&discovery, &request, &policy, &budget)?;
    let property_metadata = property_metadata_suggestions(
        &property_metadata_bytes,
        &discovery,
        &shape_config.data_graph,
        &policy,
        &request.question,
        &budget,
    )?;
    let guidance = build_shape_guidance(
        RdfSource {
            bytes: &shape_bytes,
            format: &args[6],
        },
        RdfSource {
            bytes: &data_bytes,
            format: &args[1],
        },
        &shape_config,
        &discovery,
        &packet,
        &policy,
    )?;
    let guidance_value = serde_json::to_value(&guidance)?;
    let neighborhood = data.neighborhood_packet(&discovery, &request, &policy, &budget)?;
    let entity_candidates = packet
        .candidates("entity")?
        .iter()
        .enumerate()
        .map(|(index, candidate)| serde_json::json!({"rank": index + 1, "candidate": candidate}))
        .collect::<Vec<_>>();
    let candidates = packet
        .candidates("predicate")?
        .iter()
        .enumerate()
        .map(|(index, candidate)| {
            Ok(serde_json::json!({
                "rank": index + 1,
                "candidate": candidate,
                "shape_properties": guidance.for_candidate(&packet, &candidate.id, &candidate.graph)?,
            }))
        })
        .collect::<Result<Vec<_>>>()?;
    let bm25_entities = packet.candidates("entity")?;
    let bm25_predicates = packet.candidates("predicate")?;
    let neighborhood_entities = neighborhood.candidates("entity")?;
    let mut neighboring_entity_candidates = Vec::new();
    let mut neighboring_entity_keys = BTreeSet::new();
    let mut neighboring_entities_clipped = false;
    'seeds: for (rank, seed) in bm25_entities.iter().enumerate() {
        let Some(neighborhood_seed) = neighborhood_entities
            .iter()
            .find(|item| item.iri == seed.iri && item.graph == seed.graph)
        else {
            continue;
        };
        for page in &neighborhood_seed.usage {
            for statement in &page.evidence {
                let seed_term = verity_core::execution::RdfTerm::Iri {
                    value: seed.iri.clone(),
                };
                if statement.source_graph
                    != (verity_core::execution::RdfTerm::Iri {
                        value: seed.graph.clone(),
                    })
                {
                    continue;
                }
                let (direction, neighbor) = match page.direction.as_str() {
                    "outgoing" if statement.subject == seed_term => ("outgoing", &statement.object),
                    "incoming" if statement.object == seed_term => ("incoming", &statement.subject),
                    _ => continue,
                };
                let verity_core::execution::RdfTerm::Iri { value } = neighbor else {
                    continue;
                };
                if bm25_entities
                    .iter()
                    .any(|bm25| bm25.iri == *value && bm25.graph == seed.graph)
                    || !neighboring_entity_keys.insert((seed.graph.clone(), value.clone()))
                {
                    continue;
                }
                let Some(document) = discovery
                    .graphs()
                    .get(&seed.graph)
                    .and_then(|graph| graph.documents.get(value))
                    .filter(|document| document.roles.contains("entity"))
                else {
                    continue;
                };
                if neighboring_entity_candidates.len() >= budget.per_role_top_k {
                    neighboring_entities_clipped = true;
                    break 'seeds;
                }
                let texts = document
                    .texts
                    .iter()
                    .filter(|text| text.value.text.len() <= budget.max_text_bytes)
                    .take(budget.texts_per_candidate)
                    .collect::<Vec<_>>();
                neighboring_entity_candidates.push(serde_json::json!({
                    "candidate": {
                        "iri": value,
                        "graph": seed.graph,
                        "texts": texts,
                        "texts_clipped": texts.len() < document.texts.len() || texts.iter().any(|text| text.truncated),
                    },
                    "witness": {
                        "entity": {"rank": rank + 1, "iri": seed.iri, "graph": seed.graph},
                        "direction": direction,
                        "statement": statement,
                    },
                }));
            }
        }
    }
    let neighborhood_properties = guidance_value["properties"]
        .as_array()
        .ok_or_else(|| reject("shape_guidance", "Shape properties are unavailable"))?;
    let mut neighborhood_candidates = Vec::new();
    for (rank, candidate) in neighborhood.candidates("predicate")?.iter().enumerate() {
        if bm25_predicates
            .iter()
            .any(|bm25| bm25.iri == candidate.iri && bm25.graph == candidate.graph)
            || candidate.graph != shape_config.data_graph
        {
            continue;
        }
        let shape_properties = neighborhood_properties
            .iter()
            .filter(|property| property["predicate_iri"] == candidate.iri)
            .collect::<Vec<_>>();
        let mut witness = None;
        'seeds: for (entity_rank, seed) in bm25_entities.iter().enumerate() {
            if seed.graph != candidate.graph {
                continue;
            }
            let Some(neighborhood_seed) = neighborhood_entities
                .iter()
                .find(|item| item.iri == seed.iri && item.graph == seed.graph)
            else {
                continue;
            };
            for direction in ["outgoing", "incoming"] {
                if let Ok(statement) = neighborhood.direction_witness(
                    &neighborhood_seed.id,
                    &candidate.id,
                    &candidate.graph,
                    direction,
                ) {
                    witness = Some(serde_json::json!({
                        "entity": {"rank": entity_rank + 1, "iri": seed.iri, "graph": seed.graph},
                        "direction": direction,
                        "statement": statement,
                    }));
                    break 'seeds;
                }
            }
        }
        if let Some(witness) = witness {
            neighborhood_candidates.push(serde_json::json!({
                "neighborhood_rank": rank + 1,
                "candidate": {
                    "id": candidate.id,
                    "iri": candidate.iri,
                    "graph": candidate.graph,
                    "exact": candidate.exact,
                    "ranking_score": candidate.ranking_score,
                    "texts": candidate.texts,
                    "texts_clipped": candidate.texts_clipped,
                },
                "witness": witness,
                "shape_properties": shape_properties,
            }));
        }
    }
    let packet = serde_json::to_value(&packet)?;
    let neighborhood = serde_json::to_value(&neighborhood)?;
    let result = serde_json::json!({
        "version": "assisted-ask-shape-neighborhood-metadata-suggestions-v3",
        "packet_id": packet["packet_id"],
        "request": packet["request"],
        "score_semantics": packet["score_semantics"],
        "entity_candidates": entity_candidates,
        "candidates": candidates,
        "neighborhood": {
            "version": neighborhood["version"],
            "packet_id": neighborhood["packet_id"],
            "rules": neighborhood["rules"],
            "score_semantics": neighborhood["score_semantics"],
            "clipped": neighborhood["clipped"],
            "matches_semantics": neighborhood["matches_semantics"],
        },
        "neighborhood_entity_candidates": neighboring_entity_candidates,
        "neighborhood_entities_clipped": neighboring_entities_clipped,
        "neighborhood_candidates": neighborhood_candidates,
        "property_metadata": property_metadata,
        "shape_guidance": guidance_value,
    });
    let encoded = serde_json::to_vec(&result)?;
    if encoded.len() > MAX_OUTPUT_BYTES {
        return Err(reject(
            "output_limit",
            "Shape suggestions exceed the response limit",
        ));
    }
    std::io::stdout().write_all(&encoded)?;
    std::io::stdout().write_all(b"\n")?;
    Ok(())
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("{error}");
            ExitCode::FAILURE
        }
    }
}
