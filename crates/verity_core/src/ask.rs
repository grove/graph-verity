//! Experimental deterministic templates. No question parser or model is invoked.
use crate::{
    catalog::Policy,
    execution::{Execution, PlanOrigin},
    ir::{Compare, Direction, Filter, Node, Pattern, Plan, Projection, Value},
    reject, snapshot_id, Result, Snapshot,
};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct AskRequest {
    pub version: u32,
    pub snapshot_id: String,
    pub scope: Vec<String>,
    pub template: AskTemplate,
    pub limit: u32,
}

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum AskTemplate {
    FollowPath {
        start: String,
        steps: Vec<PathStep>,
        filter: Option<TypedComparison>,
        output: PathOutput,
    },
}

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct PathStep {
    pub graph: String,
    pub predicate: String,
    pub direction: Direction,
}

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct TypedComparison {
    pub op: Compare,
    pub value: Value,
}

#[derive(Clone, Copy, Debug, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum PathOutput {
    Values,
    CountDistinct,
}

#[derive(Debug, Serialize)]
pub struct AskPreview {
    pub status: &'static str,
    pub experimental: bool,
    pub approval_id: String,
    pub plan: Plan,
    pub summary: Vec<String>,
    pub ambiguity: &'static str,
    pub limitations: &'static str,
}

#[derive(Debug, Serialize)]
#[serde(tag = "status", rename_all = "snake_case")]
pub enum AskOutcome {
    Cancelled,
    Executed {
        method: &'static str,
        approval_id: String,
        result: Box<Execution>,
    },
}

pub fn decode_request(bytes: &[u8]) -> Result<AskRequest> {
    if bytes.len() > 65_536 {
        return Err(reject("input_limit", "Ask request exceeds 64 KiB"));
    }
    serde_json::from_slice(bytes).map_err(|_| {
        reject(
            "needs_clarification",
            "Select the follow_path template with exact IRIs and typed arguments; free text, labels, raw plans and negation are unsupported",
        )
    })
}

// JSON quoting also escapes control characters in operator-supplied RDF terms.
fn quoted(value: &str) -> String {
    serde_json::to_string(value).expect("String serialization is infallible")
}

fn readable(node: &Node) -> Result<String> {
    Ok(match node {
        Node::Variable { name } => format!("variable ?{name}"),
        Node::Iri { iri } => format!("IRI {}", quoted(iri)),
        Node::Literal { value } => format!("literal {}", value.literal()?),
    })
}

impl Snapshot {
    /// Authorize and independently compile before disclosing a preview. No query executes.
    pub fn preview_ask(&self, request: &AskRequest, policy: &Policy) -> Result<AskPreview> {
        policy.authorize(&request.scope)?;
        if request.version != 1 {
            return Err(reject("ask_version", "Only Ask version 1 is supported"));
        }
        let AskTemplate::FollowPath {
            start,
            steps,
            filter,
            output,
        } = &request.template;
        if steps.is_empty() || steps.len() > 2 {
            return Err(reject(
                "needs_clarification",
                "Select one or two explicit directed path steps",
            ));
        }
        let mut from = Node::Iri { iri: start.clone() };
        let mut patterns = Vec::new();
        for (i, step) in steps.iter().enumerate() {
            let to = Node::Variable {
                name: format!("step{}", i + 1),
            };
            patterns.push(Pattern {
                graph: step.graph.clone(),
                from,
                predicate: step.predicate.clone(),
                direction: step.direction,
                to: to.clone(),
            });
            from = to;
        }
        let terminal = format!("step{}", steps.len());
        let plan = Plan {
            version: 1,
            snapshot_id: request.snapshot_id.clone(),
            scope: request.scope.clone(),
            patterns,
            filters: filter
                .iter()
                .map(|f| Filter {
                    variable: terminal.clone(),
                    op: f.op,
                    value: f.value.clone(),
                })
                .collect(),
            projection: vec![match output {
                PathOutput::Values => Projection::Variable {
                    name: terminal.clone(),
                },
                PathOutput::CountDistinct => Projection::CountDistinct {
                    variable: terminal.clone(),
                    alias: "count".into(),
                },
            }],
            group_by: vec![],
            having: vec![],
            limit: request.limit,
        };
        self.compile(&plan, policy)?;
        let mut summary = vec![
            format!("Immutable snapshot: {}", quoted(&plan.snapshot_id)),
            format!("Exact authorized named-graph scope: {}", serde_json::to_string(&plan.scope)?),
            format!("Start at IRI {}. All steps must match (a conjunction); only explicit stored triples are used.", quoted(start)),
        ];
        for (i, pattern) in plan.patterns.iter().enumerate() {
            let (subject, object) = pattern.ends();
            let direction = match pattern.direction {
                Direction::Forward => "outgoing",
                Direction::Reverse => "incoming",
            };
            summary.push(format!(
                "Step {} ({direction}) in graph {}: {} -- predicate IRI {} --> {}.",
                i + 1,
                quoted(&pattern.graph),
                readable(subject)?,
                quoted(&pattern.predicate),
                readable(object)?
            ));
        }
        if let Some(filter) = filter {
            summary.push(format!(
                "Keep ?{terminal} {} literal lexical {}, datatype IRI {}, language {}.",
                filter.op.sparql(),
                quoted(&filter.value.lexical),
                quoted(&filter.value.datatype),
                serde_json::to_string(&filter.value.language)?
            ));
        } else {
            summary.push("Typed filters: none.".into());
        }
        summary.push(match output {
            PathOutput::Values => format!("Return distinct ?{terminal} values; intermediate nodes are not returned."),
            PathOutput::CountDistinct => format!("Return COUNT(DISTINCT ?{terminal}) as ?count across all matching paths, not a count of paths. Zero means no matching stored values, not real-world absence."),
        });
        summary.push(format!(
            "Row limit: {} (including count rows). Evidence limit: {} triples; timeout: {} ms. Rows and evidence may be truncated separately.",
            plan.limit, policy.max_evidence, policy.timeout_ms
        ));
        let approval_id = snapshot_id(
            &serde_json::to_vec(&(&plan, policy))?,
            "graph-verity-confirmed-ask-v1",
        );
        Ok(AskPreview {
            status: "awaiting_confirmation",
            experimental: true,
            approval_id,
            plan,
            summary,
            ambiguity: "exact_iris_required; no_label_resolution_or_natural_language_interpretation",
            limitations: "Confirmation records your choice, not proof of correct interpretation or expert review. Execution verification, source evidence and real-world truth are separate. Missing facts remain unknown. Experimental prototype; user need and usability are unproven; no production/release GO.",
        })
    }

    /// Approval is a deliberate caller decision, not an authentication credential or attestation.
    /// Rebuild under the current snapshot, scope and policy; stale/edited approvals fail closed.
    pub fn execute_confirmed_ask(
        &self,
        request: &AskRequest,
        policy: &Policy,
        approval: Option<&str>,
    ) -> Result<AskOutcome> {
        let Some(approval) = approval else {
            return Ok(AskOutcome::Cancelled);
        };
        let preview = self.preview_ask(request, policy)?;
        if approval != preview.approval_id {
            return Err(reject(
                "confirmation",
                "Approval does not match the exact current plan, scope, snapshot and policy; review a new preview",
            ));
        }
        Ok(AskOutcome::Executed {
            method: "experimental_user_confirmed_deterministic_template",
            approval_id: preview.approval_id,
            result: Box::new(self.execute(&preview.plan, policy, PlanOrigin::Manual)?),
        })
    }
}

pub fn schema() -> serde_json::Value {
    serde_json::json!({"ask_version": 1, "request": schemars::schema_for!(AskRequest)})
}
