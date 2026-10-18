//! Untrusted one-hop proposals to Confirmed Ask. This module never executes a query.
use crate::{
    ask::{AskPreview, AskRequest, AskTemplate, PathOutput, PathStep},
    catalog::Policy,
    discovery::DiscoveryIndex,
    ir::Direction,
    reject, snapshot_id, Result, Snapshot,
};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub enum Version {
    #[serde(rename = "nl-ask-draft-v1")]
    V1,
}

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum Output {
    Values,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(tag = "status", rename_all = "snake_case", deny_unknown_fields)]
pub enum Draft {
    Candidate {
        version: Version,
        start: u16,
        predicate: u16,
        graph: u16,
        direction: Direction,
        output: Output,
        #[schemars(length(min = 1, max = 512))]
        rationale: String,
    },
    NeedsClarification {
        version: Version,
        #[schemars(length(min = 1, max = 512))]
        rationale: String,
    },
    Unsupported {
        version: Version,
        #[schemars(length(min = 1, max = 512))]
        rationale: String,
    },
}

pub fn decode_draft(bytes: &[u8]) -> Result<Draft> {
    if bytes.len() > 16_384 {
        return Err(reject("invalid_contract", "Draft exceeds 16 KiB"));
    }
    serde_json::from_slice::<serde_json::Value>(bytes)
        .map_err(|_| reject("invalid_json", "Draft is not one JSON value"))?;
    // Decode original bytes so duplicate fields cannot be silently collapsed.
    let draft: Draft = serde_json::from_slice(bytes)
        .map_err(|_| reject("invalid_contract", "Expected strict nl-ask-draft-v1"))?;
    let rationale = match &draft {
        Draft::Candidate { rationale, .. }
        | Draft::NeedsClarification { rationale, .. }
        | Draft::Unsupported { rationale, .. } => rationale,
    };
    if rationale.is_empty() || rationale.chars().count() > 512 {
        return Err(reject(
            "invalid_contract",
            "Rationale requires 1..512 characters",
        ));
    }
    Ok(draft)
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GraphReference {
    pub id: u16,
    pub iri: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Reference {
    pub id: u16,
    pub graph: u16,
    pub iri: String,
}

/// Trusted host input, never accepted from a model. IDs are local to this frozen table.
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CatalogSelection {
    pub snapshot_id: String,
    pub graphs: Vec<GraphReference>,
    pub entities: Vec<Reference>,
    pub predicates: Vec<Reference>,
    /// Exact start explicitly resolved by the host/user; None prohibits a candidate.
    pub resolved_start: Option<u16>,
    /// An operator decision, not an inferred claim about the model's understanding.
    pub blocked: bool,
    pub limit: u32,
}

/// No deserialization or public mutable fields: freeze again after any host-side edit.
#[derive(Debug, Serialize)]
pub struct Context {
    selection: CatalogSelection,
    policy_hash: String,
    source_index_hash: String,
}

#[derive(Debug, Serialize)]
#[serde(tag = "status", rename_all = "snake_case")]
pub enum Outcome {
    ModelNeedsClarification {
        display_rationale: String,
    },
    ModelUnsupported {
        display_rationale: String,
    },
    Candidate {
        request: Box<AskRequest>,
        preview: Box<AskPreview>,
        display_rationale: String,
        interpretation_correctness: &'static str,
    },
}

fn preflight() -> crate::Error {
    reject(
        "deterministic_preflight_block",
        "Host snapshot, source, scope, resolution or limits prohibit this draft",
    )
}

impl Snapshot {
    pub fn freeze_nl_ask_catalog(
        &self,
        index: &DiscoveryIndex,
        selection: CatalogSelection,
        policy: &Policy,
    ) -> Result<Context> {
        let scope: Vec<_> = selection.graphs.iter().map(|g| g.iri.clone()).collect();
        index.authorize(&scope, policy).map_err(|_| preflight())?;
        if selection.snapshot_id != self.id()
            || index.manifest().snapshot_id != self.id()
            || selection.limit == 0
            || selection.limit > 100
            || selection.limit > policy.max_rows
            || selection.entities.len() > 64
            || selection.predicates.len() > 64
            || selection
                .graphs
                .iter()
                .map(|g| g.id)
                .collect::<BTreeSet<_>>()
                .len()
                != selection.graphs.len()
        {
            return Err(preflight());
        }
        for (references, role) in [
            (&selection.entities, "entity"),
            (&selection.predicates, "predicate"),
        ] {
            if references
                .iter()
                .map(|r| r.id)
                .collect::<BTreeSet<_>>()
                .len()
                != references.len()
                || references
                    .iter()
                    .map(|r| (r.graph, &r.iri))
                    .collect::<BTreeSet<_>>()
                    .len()
                    != references.len()
            {
                return Err(preflight());
            }
            for reference in references {
                let graph = selection
                    .graphs
                    .iter()
                    .find(|g| g.id == reference.graph)
                    .ok_or_else(preflight)?;
                if !index
                    .graphs()
                    .get(&graph.iri)
                    .and_then(|g| g.documents.get(&reference.iri))
                    .is_some_and(|d| d.roles.contains(role))
                {
                    return Err(preflight());
                }
            }
        }
        if selection
            .resolved_start
            .is_some_and(|id| !selection.entities.iter().any(|r| r.id == id))
        {
            return Err(preflight());
        }
        Ok(Context {
            selection,
            policy_hash: snapshot_id(&serde_json::to_vec(policy)?, "nl-ask-policy-v1"),
            source_index_hash: snapshot_id(&serde_json::to_vec(index)?, "nl-ask-source-index-v1"),
        })
    }

    /// Only a Confirmed Ask preview is produced. Execution still requires independent approval.
    pub fn preview_nl_ask(
        &self,
        context: &Context,
        draft: Draft,
        policy: &Policy,
    ) -> Result<Outcome> {
        let table = &context.selection;
        if table.snapshot_id != self.id()
            || context.policy_hash != snapshot_id(&serde_json::to_vec(policy)?, "nl-ask-policy-v1")
        {
            return Err(preflight());
        }
        let (start, predicate, graph, direction, rationale) = match draft {
            Draft::NeedsClarification { rationale, .. } => {
                return Ok(Outcome::ModelNeedsClarification {
                    display_rationale: rationale,
                })
            }
            Draft::Unsupported { rationale, .. } => {
                return Ok(Outcome::ModelUnsupported {
                    display_rationale: rationale,
                })
            }
            Draft::Candidate {
                start,
                predicate,
                graph,
                direction,
                rationale,
                ..
            } => (start, predicate, graph, direction, rationale),
        };
        let invalid_ref = || {
            reject(
                "invalid_catalog_reference",
                "Unknown ID, role or graph-qualified reference",
            )
        };
        let graph = table
            .graphs
            .iter()
            .find(|g| g.id == graph)
            .ok_or_else(invalid_ref)?;
        let entity = table
            .entities
            .iter()
            .find(|r| r.id == start && r.graph == graph.id)
            .ok_or_else(invalid_ref)?;
        let predicate = table
            .predicates
            .iter()
            .find(|r| r.id == predicate && r.graph == graph.id)
            .ok_or_else(invalid_ref)?;
        if table.blocked || table.resolved_start != Some(start) {
            return Err(preflight());
        }
        let request = AskRequest {
            version: 1,
            snapshot_id: table.snapshot_id.clone(),
            scope: vec![graph.iri.clone()],
            template: AskTemplate::FollowPath {
                start: entity.iri.clone(),
                steps: vec![PathStep {
                    graph: graph.iri.clone(),
                    predicate: predicate.iri.clone(),
                    direction,
                }],
                filter: None,
                output: PathOutput::Values,
            },
            limit: table.limit,
        };
        let preview = self
            .preview_ask(&request, policy)
            .map_err(|_| preflight())?;
        Ok(Outcome::Candidate {
            request: Box::new(request),
            preview: Box::new(preview),
            display_rationale: rationale,
            interpretation_correctness: "not_assessed",
        })
    }
}

pub fn schema() -> serde_json::Value {
    serde_json::to_value(schemars::schema_for!(Draft)).expect("Schema serialization is infallible")
}
