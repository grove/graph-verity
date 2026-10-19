//! Experimental host bridge. Original numeric identities, complete membership, preview only.
use serde::Deserialize;
use std::collections::BTreeSet;
use verity_core::{
    catalog::Policy,
    discovery::DiscoveryConfig,
    nl_ask::{decode_draft, CatalogSelection, Outcome, Reference},
    read_limited, reject,
    vocabulary::{VocabularyBudget, VocabularyRequest},
    Result, Snapshot,
};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Binding {
    condition: String,
    request: VocabularyRequest,
    budget: VocabularyBudget,
    saved_packet_id: Option<String>,
    selection: CatalogSelection,
}

fn fail() -> verity_core::Error {
    reject(
        "packet_integrity",
        "Changed source, policy, scope, packet or original numeric binding",
    )
}

fn identities(rows: &[Reference]) -> BTreeSet<(u16, u16, &str)> {
    rows.iter()
        .map(|r| (r.id, r.graph, r.iri.as_str()))
        .collect()
}

fn preview(args: &[String]) -> Result<Outcome> {
    if args.len() != 7 {
        return Err(reject(
            "usage",
            "v1g_preview RDF POLICY SCOPE DISCOVERY BINDING PACKET DRAFT",
        ));
    }
    let snapshot = Snapshot::from_bytes(&read_limited(&args[0], 16 * 1024 * 1024)?, "nquads")?;
    let policy: Policy = serde_json::from_slice(&read_limited(&args[1], 65536)?)?;
    let scope: Vec<String> = serde_json::from_slice(&read_limited(&args[2], 65536)?)?;
    let discovery: DiscoveryConfig = serde_json::from_slice(&read_limited(&args[3], 65536)?)?;
    let binding: Binding = serde_json::from_slice(&read_limited(&args[4], 65536)?)?;
    let packet_bytes = read_limited(&args[5], 1024 * 1024)?;
    // This experiment's immutable table is host input compiled into the bridge, never model input.
    let original: CatalogSelection = serde_json::from_str(include_str!(
        "../../../studies/nl-ask-v1/evaluation/catalog.json"
    ))?;
    let original_policy: Policy = serde_json::from_str(include_str!(
        "../../../studies/nl-ask-v1/evaluation/policy.json"
    ))?;
    if snapshot.id() != original.snapshot_id
        || serde_json::to_value(&policy)? != serde_json::to_value(original_policy)?
        || scope
            != original
                .graphs
                .iter()
                .map(|g| g.iri.clone())
                .collect::<Vec<_>>()
        || binding.request.scope != scope
        || binding.selection.snapshot_id != original.snapshot_id
        || serde_json::to_value(&binding.selection.graphs)?
            != serde_json::to_value(&original.graphs)?
        || binding.selection.limit != original.limit
    {
        return Err(fail());
    }
    let index = snapshot.build_discovery(&scope, &policy, &discovery)?;
    // Validate the complete original graph/IRI/role table independently of Python.
    snapshot.freeze_nl_ask_catalog(&index, original.clone(), &policy)?;
    let packet = match binding.condition.as_str() {
        "oracle" => {
            if !packet_bytes.is_empty() || binding.saved_packet_id.is_some() {
                return Err(fail());
            }
            None
        }
        "BM25-v1" => {
            let packet = snapshot.revalidate_vocabulary_packet(
                &index,
                &packet_bytes,
                &binding.request,
                &policy,
                &binding.budget,
            )?;
            if packet_bytes != serde_json::to_vec(&packet)? {
                return Err(fail());
            }
            Some(serde_json::to_value(packet)?)
        }
        "neighborhood-v2" => Some(serde_json::to_value(
            snapshot.revalidate_neighborhood_packet(
                &index,
                &packet_bytes,
                &binding.request,
                &policy,
                &binding.budget,
            )?,
        )?),
        _ => return Err(fail()),
    };
    if let Some(packet) = &packet {
        if packet["packet_id"].as_str() != binding.saved_packet_id.as_deref() {
            return Err(fail());
        }
    }
    for (name, full, selected) in [
        ("entities", &original.entities, &binding.selection.entities),
        (
            "predicates",
            &original.predicates,
            &binding.selection.predicates,
        ),
    ] {
        let expected: Vec<_> = full
            .iter()
            .filter(|r| {
                packet.as_ref().is_none_or(|p| {
                    p[name]["candidates"].as_array().is_some_and(|rows| {
                        rows.iter().any(|c| {
                            c["iri"].as_str() == Some(&r.iri)
                                && c["graph"].as_str()
                                    == Some(&original.graphs[r.graph as usize].iri)
                        })
                    })
                })
            })
            .cloned()
            .collect();
        if identities(selected) != identities(&expected)
            || selected.len() != expected.len()
            || packet.as_ref().is_some_and(|p| {
                p[name]["candidates"].as_array().map(Vec::len) != Some(expected.len())
            })
        {
            return Err(fail());
        }
    }
    // All integrity checks precede even an abstention's decoding or preview.
    let draft = decode_draft(&read_limited(&args[6], 16384)?)?;
    if binding.condition == "neighborhood-v2" {
        let packet = snapshot.revalidate_neighborhood_packet(
            &index,
            &packet_bytes,
            &binding.request,
            &policy,
            &binding.budget,
        )?;
        let context =
            snapshot.freeze_neighborhood_catalog(&index, &packet, binding.selection, &policy)?;
        snapshot.preview_neighborhood_draft(
            &context,
            binding.saved_packet_id.as_deref().ok_or_else(fail)?,
            draft,
            &policy,
        )
    } else {
        let context = snapshot.freeze_nl_ask_catalog(&index, binding.selection, &policy)?;
        snapshot.preview_nl_ask(&context, draft, &policy)
    }
}

fn main() {
    match preview(&std::env::args().skip(1).collect::<Vec<_>>()) {
        Ok(outcome) => println!("{}", serde_json::to_string(&outcome).unwrap()),
        Err(error) => {
            eprintln!(
                "{}",
                serde_json::json!({"status":"error", "detail":error.to_string()})
            );
            std::process::exit(1);
        }
    }
}
