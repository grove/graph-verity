//! Explicit, authorized one-hop navigation. Each returned edge is its own snapshot witness.
use crate::{
    catalog::Policy,
    compiler::entity_query,
    discovery::{DiscoveryIndex, Document, Source},
    execution::{select, Deadline, Statement},
    reject, Result, Snapshot,
};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum EdgeDirection {
    Incoming,
    Outgoing,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EntityRequest {
    pub snapshot_id: String,
    pub scope: Vec<String>,
    pub iri: String,
    pub direction: EdgeDirection,
    pub offset: usize,
    pub limit: usize,
}

#[derive(Debug, Serialize)]
pub struct EntityResult<'a> {
    pub snapshot_id: &'a str,
    pub scope: Vec<String>,
    pub iri: Option<String>,
    /// Labels and roles remain graph-qualified; never fill missing labels from another graph.
    pub documents: BTreeMap<&'a str, &'a Document>,
    pub sources: BTreeMap<&'a str, &'a Source>,
    pub graph_hashes: BTreeMap<&'a str, &'a str>,
    pub status: &'static str,
    pub direction: EdgeDirection,
    pub offset: usize,
    pub limit: usize,
    pub next_offset: Option<usize>,
    pub truncated: bool,
    pub evidence: Vec<Statement>,
    pub evidence_verification: &'static str,
    pub evidence_semantics: &'static str,
    pub interpretation_correctness: &'static str,
    pub real_world_truth: &'static str,
    pub absence_policy: &'static str,
}

impl Snapshot {
    pub fn entity<'a>(
        &'a self,
        index: &'a DiscoveryIndex,
        request: &EntityRequest,
        policy: &Policy,
    ) -> Result<EntityResult<'a>> {
        index.authorize(&request.scope, policy)?;
        if index.manifest().snapshot_id != self.id() || request.snapshot_id != self.id() {
            return Err(reject(
                "snapshot",
                "Navigation requires the same snapshot and index",
            ));
        }
        if request.limit == 0
            || request.limit > 50
            || request.limit > policy.max_rows as usize
            || request.limit > policy.max_evidence as usize
            || request.offset > 100_000
        {
            return Err(reject(
                "complexity",
                "Entity page requires limit 1..50 within row/evidence policy and offset 0..100000",
            ));
        }
        let query = entity_query(request)?;
        let mut rows = select(
            &self.store,
            &query,
            request.limit + 1,
            &Deadline::new(policy.timeout_ms),
        )?;
        let truncated = rows.len() > request.limit;
        rows.truncate(request.limit);
        let evidence = rows
            .into_iter()
            .map(Statement::from_row)
            .collect::<Result<Vec<_>>>()?;
        let mut scope = request.scope.clone();
        scope.sort();
        let documents: BTreeMap<_, _> = scope
            .iter()
            .filter_map(|g| {
                let (graph, data) = index.graphs().get_key_value(g).unwrap();
                data.documents
                    .get(&request.iri)
                    .map(|d| (graph.as_str(), d))
            })
            .collect();
        let manifest = index.manifest();
        let result = EntityResult {
            snapshot_id: self.id(),
            iri: (!documents.is_empty()).then(|| request.iri.clone()),
            status: if documents.is_empty() {
                "no_match"
            } else if evidence.is_empty() {
                "no_relationships_on_page"
            } else if truncated {
                "truncated"
            } else {
                "observed"
            },
            documents,
            sources: scope
                .iter()
                .map(|g| {
                    let (g, source) = manifest.sources.get_key_value(g).unwrap();
                    (g.as_str(), source)
                })
                .collect(),
            graph_hashes: scope
                .iter()
                .map(|g| {
                    let (g, hash) = manifest.graph_hashes.get_key_value(g).unwrap();
                    (g.as_str(), hash.as_str())
                })
                .collect(),
            scope,
            direction: request.direction,
            offset: request.offset,
            limit: request.limit,
            next_offset: truncated.then_some(request.offset + evidence.len()),
            truncated,
            evidence,
            evidence_verification: "verified_against_snapshot",
            evidence_semantics:
                "one_page_of_explicit_directed_statements_only; no_inference_or_recursive_expansion",
            interpretation_correctness: "not_assessed",
            real_world_truth: "not_established",
            absence_policy: "open_world_missing_facts_are_not_false",
        };
        if serde_json::to_vec(&result)?.len() > 8 * 1024 * 1024 {
            return Err(reject(
                "output_limit",
                "Entity details and evidence exceed 8 MiB",
            ));
        }
        Ok(result)
    }
}
