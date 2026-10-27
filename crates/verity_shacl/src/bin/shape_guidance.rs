#![forbid(unsafe_code)]
use std::{env, io::Write, process::ExitCode};
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
    let packet = serde_json::to_value(&packet)?;
    let guidance = serde_json::to_value(&guidance)?;
    let result = serde_json::json!({
        "version": "assisted-ask-shape-suggestions-v1",
        "packet_id": packet["packet_id"],
        "request": packet["request"],
        "score_semantics": packet["score_semantics"],
        "candidates": candidates,
        "shape_guidance": guidance,
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
