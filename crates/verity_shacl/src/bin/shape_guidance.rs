#![forbid(unsafe_code)]
use std::{collections::BTreeSet, env, io::Write, process::ExitCode};
use verity_core::{
    catalog::Policy,
    discovery::DiscoveryConfig,
    read_limited, reject,
    vocabulary::{VocabularyBudget, VocabularyRequest},
    Result, Snapshot,
};
use verity_shacl::{build_shape_guidance, RdfSource, ShapeConfig};

const MAX_RDF_BYTES: usize = 16 * 1024 * 1024;
const MAX_JSON_BYTES: usize = 2 * 1024 * 1024;
const MAX_OUTPUT_BYTES: usize = 4 * 1024 * 1024;
const USAGE: &str = "shape_guidance DATA FORMAT POLICY SCOPE DISCOVERY SHAPES SHAPE_FORMAT SHAPE_CONFIG REQUEST BUDGET";

fn json<T: serde::de::DeserializeOwned>(path: &str, limit: usize) -> Result<T> {
    Ok(serde_json::from_slice(&read_limited(path, limit)?)?)
}

fn run() -> Result<()> {
    let args = env::args().skip(1).collect::<Vec<_>>();
    if args.len() != 10 {
        return Err(reject("usage", USAGE));
    }
    let data_bytes = read_limited(&args[0], MAX_RDF_BYTES)?;
    let data = Snapshot::from_bytes(&data_bytes, &args[1])?;
    let policy: Policy = json(&args[2], MAX_JSON_BYTES)?;
    let scope: Vec<String> = json(&args[3], MAX_JSON_BYTES)?;
    let discovery_config: DiscoveryConfig = json(&args[4], MAX_JSON_BYTES)?;
    let shape_bytes = read_limited(&args[5], MAX_RDF_BYTES)?;
    let shape_config: ShapeConfig = json(&args[7], MAX_JSON_BYTES)?;
    let request: VocabularyRequest = json(&args[8], MAX_JSON_BYTES)?;
    let budget: VocabularyBudget = json(&args[9], MAX_JSON_BYTES)?;
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
        if shape_properties.is_empty() {
            continue;
        }
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
        "version": "assisted-ask-shape-neighborhood-suggestions-v2",
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
