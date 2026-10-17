//! Oracle and parser runs share scoring. Fixture correctness is never reported as model accuracy.
use crate::{
    catalog::Policy,
    compact::{decode_intent, CompactProposal},
    execution::{Execution, PlanOrigin, Row},
    ir::Plan,
    parser::{decode_response, preflight, Proposal, SemanticParser},
    reject, snapshot_id, Result, Snapshot,
};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::{
    collections::{BTreeMap, BTreeSet},
    time::Instant,
};

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Case {
    pub id: String,
    pub question: String,
    pub interpretation: String,
    pub family: String,
    pub split: String,
    pub review_status: String,
    pub provenance: String,
    pub scope: Vec<String>,
    pub expected_status: String,
    pub gold: Option<Plan>,
    pub reference_sparql: Option<String>,
    pub expected_bindings: Option<Vec<Row>>,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Benchmark {
    pub version: u32,
    pub name: String,
    pub snapshot_id: String,
    pub cases: Vec<Case>,
}

#[derive(Debug, Serialize)]
pub struct CaseScore {
    pub id: String,
    pub family: String,
    pub split: String,
    pub provenance: String,
    pub review_status: String,
    pub error_code: Option<String>,
    pub catalog_ms: Option<f64>,
    pub validation_compile_ms: Option<f64>,
    pub execution: Option<Execution>,
    pub result_classification: String,
    pub missing_fact_status: &'static str,
    pub user_facing_false_confidence: &'static str,
    pub passed: bool,
    pub stage: String,
    pub detail: String,
    pub json_valid: Option<bool>,
    pub structural_ir_exact: Option<bool>,
    pub exact_result_set: Option<bool>,
    pub wrong_plan_successful_execution: bool,
    pub precision: Option<f64>,
    pub recall: Option<f64>,
    pub f1: Option<f64>,
    pub pipeline_ms: Option<f64>,
    pub expected_status: String,
    pub proposal_status: Option<String>,
    /// Independent deterministic preflight advice; does not rescore raw model proposals.
    pub preflight_would_block: Option<String>,
    pub contract_valid: Option<bool>,
    pub safety_valid: Option<bool>,
    pub raw_response: Option<String>,
    pub generation_ms: Option<f64>,
    pub end_to_end_ms: f64,
    pub components_exact: BTreeMap<String, bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub expanded_plan: Option<Plan>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub expansion_ms: Option<f64>,
}

impl CaseScore {
    fn new(case: &Case) -> Self {
        Self {
            id: case.id.clone(),
            family: case.family.clone(),
            split: case.split.clone(),
            provenance: case.provenance.clone(),
            review_status: case.review_status.clone(),
            error_code: None,
            catalog_ms: None,
            validation_compile_ms: None,
            execution: None,
            result_classification: "not_executed".into(),
            missing_fact_status: "unknown_completeness_no_independent_missing_fact_evidence",
            user_facing_false_confidence: "not_measured_no_complete_user_interface",
            passed: false,
            stage: "not_run".into(),
            detail: String::new(),
            json_valid: None,
            structural_ir_exact: None,
            exact_result_set: None,
            wrong_plan_successful_execution: false,
            precision: None,
            recall: None,
            f1: None,
            pipeline_ms: None,
            expected_status: case.expected_status.clone(),
            proposal_status: None,
            preflight_would_block: None,
            contract_valid: None,
            safety_valid: None,
            raw_response: None,
            generation_ms: None,
            end_to_end_ms: 0.0,
            components_exact: BTreeMap::new(),
            expanded_plan: None,
            expansion_ms: None,
        }
    }
}

// Compact slots and v1 names differ. Normalize names only; retain order and every operation.
fn canonical_plan(plan: &Plan) -> Plan {
    use crate::ir::{Node, Projection};
    let mut plan = plan.clone();
    let mut variables = BTreeMap::new();
    let mut rename = |name: &mut String| {
        let next = format!("v{}", variables.len());
        *name = variables.entry(name.clone()).or_insert(next).clone();
    };
    for edge in &mut plan.patterns {
        for node in [&mut edge.from, &mut edge.to] {
            if let Node::Variable { name } = node {
                rename(name);
            }
        }
    }
    for filter in &mut plan.filters {
        rename(&mut filter.variable);
    }
    let mut aliases = BTreeMap::new();
    for (i, projection) in plan.projection.iter_mut().enumerate() {
        match projection {
            Projection::Variable { name } => rename(name),
            Projection::CountDistinct { variable, alias } => {
                rename(variable);
                let canonical = format!("c{i}");
                aliases.insert(alias.clone(), canonical.clone());
                *alias = canonical;
            }
        }
    }
    for name in &mut plan.group_by {
        rename(name);
    }
    for having in &mut plan.having {
        if let Some(alias) = aliases.get(&having.alias) {
            having.alias.clone_from(alias);
        }
    }
    plan
}

fn align_columns(rows: &[Row], actual: &Plan, gold: &Plan) -> Vec<Row> {
    use crate::ir::Projection;
    let name = |p: &Projection| match p {
        Projection::Variable { name } => name.clone(),
        Projection::CountDistinct { alias, .. } => alias.clone(),
    };
    let columns: BTreeMap<_, _> = actual
        .projection
        .iter()
        .map(name)
        .zip(gold.projection.iter().map(name))
        .collect();
    rows.iter()
        .map(|row| {
            row.iter()
                .map(|(key, value)| (columns.get(key).unwrap_or(key).clone(), value.clone()))
                .collect()
        })
        .collect()
}

/// Conservative, order-sensitive reference comparisons, not semantic equivalence.
pub fn plan_components(actual: &Plan, gold: &Plan) -> BTreeMap<String, bool> {
    fn parts(plan: &Plan) -> BTreeMap<String, serde_json::Value> {
        let p = serde_json::to_value(plan).expect("Plan serialization is infallible");
        let patterns = p["patterns"].as_array().expect("Plan patterns");
        let filters = p["filters"].as_array().expect("Plan filters");
        let having = p["having"].as_array().expect("Plan having");
        let values: Vec<_> = filters
            .iter()
            .map(|f| &f["value"])
            .chain(
                patterns
                    .iter()
                    .flat_map(|e| [&e["from"]["value"], &e["to"]["value"]])
                    .filter(|v| !v.is_null()),
            )
            .collect();
        BTreeMap::from([
            (
                "operator".into(),
                serde_json::json!([
                    filters.iter().map(|f| &f["op"]).collect::<Vec<_>>(),
                    having.iter().map(|h| &h["op"]).collect::<Vec<_>>(),
                    p["projection"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .map(|v| &v["kind"])
                        .collect::<Vec<_>>()
                ]),
            ),
            (
                "direction".into(),
                serde_json::json!(patterns.iter().map(|e| &e["direction"]).collect::<Vec<_>>()),
            ),
            (
                "predicate".into(),
                serde_json::json!(patterns.iter().map(|e| &e["predicate"]).collect::<Vec<_>>()),
            ),
            (
                "entity".into(),
                serde_json::json!(patterns
                    .iter()
                    .map(|e| [&e["from"]["iri"], &e["to"]["iri"]])
                    .collect::<Vec<_>>()),
            ),
            (
                "datatype".into(),
                serde_json::json!(values
                    .iter()
                    .map(|v| [&v["datatype"], &v["language"]])
                    .collect::<Vec<_>>()),
            ),
            (
                "number".into(),
                serde_json::json!([
                    values
                        .iter()
                        .filter(|v| v["datatype"].as_str().is_some_and(crate::ir::numeric))
                        .map(|v| &v["lexical"])
                        .collect::<Vec<_>>(),
                    having.iter().map(|h| &h["value"]).collect::<Vec<_>>()
                ]),
            ),
            (
                "date_operand".into(),
                serde_json::json!(values
                    .iter()
                    .filter(|v| v["datatype"]
                        .as_str()
                        .is_some_and(|d| d.ends_with("#date") || d.ends_with("#dateTime")))
                    .map(|v| &v["lexical"])
                    .collect::<Vec<_>>()),
            ),
            (
                "variables".into(),
                serde_json::json!([
                    patterns
                        .iter()
                        .map(|e| [&e["from"]["name"], &e["to"]["name"]])
                        .collect::<Vec<_>>(),
                    filters.iter().map(|f| &f["variable"]).collect::<Vec<_>>()
                ]),
            ),
            (
                "aggregation".into(),
                serde_json::json!(p["projection"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .filter(|v| v["kind"] != "variable")
                    .collect::<Vec<_>>()),
            ),
            ("having".into(), p["having"].clone()),
            ("literal".into(), serde_json::json!(values)),
            (
                "scope".into(),
                serde_json::json!([
                    p["scope"],
                    patterns.iter().map(|e| &e["graph"]).collect::<Vec<_>>()
                ]),
            ),
            ("projection".into(), p["projection"].clone()),
            ("group_by".into(), p["group_by"].clone()),
            ("limit".into(), p["limit"].clone()),
            ("snapshot".into(), p["snapshot_id"].clone()),
        ])
    }
    let gold = parts(gold);
    parts(actual)
        .into_iter()
        .map(|(key, value)| {
            let exact = gold.get(&key) == Some(&value);
            (key, exact)
        })
        .collect()
}

#[derive(Debug, Serialize)]
pub struct Report {
    pub mode: &'static str,
    pub benchmark: String,
    pub benchmark_digest: String,
    pub snapshot_id: String,
    pub schema_digest: String,
    pub implementation_digest: String,
    pub dependency_lock_digest: String,
    pub model: Option<String>,
    pub split: String,
    pub cases: Vec<CaseScore>,
    pub passed: usize,
    pub total: usize,
    pub per_family: BTreeMap<String, (usize, usize)>,
    pub pass_rate_wilson_95: (f64, f64),
    pub pipeline_p50_ms: Option<f64>,
    pub pipeline_p95_ms: Option<f64>,
    pub pipeline_p99_ms: Option<f64>,
    pub process_peak_rss_kib: Option<u64>,
    pub measurement_scope: &'static str,
    pub elapsed_ms: f64,
    pub readiness_claim: &'static str,
}

pub fn set_scores(actual: &[Row], expected: &[Row]) -> (bool, f64, f64, f64) {
    let actual: BTreeSet<_> = actual.iter().collect();
    let expected: BTreeSet<_> = expected.iter().collect();
    let common = actual.intersection(&expected).count() as f64;
    let precision = if actual.is_empty() {
        if expected.is_empty() {
            1.0
        } else {
            0.0
        }
    } else {
        common / actual.len() as f64
    };
    let recall = if expected.is_empty() {
        1.0
    } else {
        common / expected.len() as f64
    };
    let f1 = if precision + recall == 0.0 {
        0.0
    } else {
        2.0 * precision * recall / (precision + recall)
    };
    (actual == expected, precision, recall, f1)
}

fn quantile(values: &[f64], fraction: f64) -> Option<f64> {
    if values.is_empty() {
        return None;
    }
    let index = ((values.len() as f64 * fraction).ceil() as usize).saturating_sub(1);
    values.get(index).copied()
}

fn wilson(passed: usize, total: usize) -> (f64, f64) {
    if total == 0 {
        return (0.0, 1.0);
    }
    let n = total as f64;
    let p = passed as f64 / n;
    let z2 = 1.96_f64.powi(2);
    let denominator = 1.0 + z2 / n;
    let center = (p + z2 / (2.0 * n)) / denominator;
    let radius = 1.96 * ((p * (1.0 - p) + z2 / (4.0 * n)) / n).sqrt() / denominator;
    ((center - radius).max(0.0), (center + radius).min(1.0))
}

fn peak_rss() -> Option<u64> {
    std::fs::read_to_string("/proc/self/status")
        .ok()?
        .lines()
        .find_map(|line| {
            line.strip_prefix("VmHWM:")
                .and_then(|v| v.split_whitespace().next()?.parse().ok())
        })
}

impl Snapshot {
    pub fn evaluate(
        &self,
        benchmark: &Benchmark,
        split: &str,
        policy: &Policy,
        parser: Option<&dyn SemanticParser>,
    ) -> Result<Report> {
        // Locked/private evaluation requires an isolated operator workflow, never this public runner.
        if !matches!(split, "dev" | "transfer_dev") {
            return Err(reject(
                "locked_evaluation",
                "Only public development splits are enabled",
            ));
        }
        if benchmark.version != 1
            || benchmark.snapshot_id != self.id
            || benchmark.cases.len() > 1000
        {
            return Err(reject(
                "benchmark",
                "Invalid benchmark version, snapshot or size",
            ));
        }
        let mut ids = BTreeSet::new();
        for case in &benchmark.cases {
            if !ids.insert(&case.id) || case.question.is_empty() || case.review_status.is_empty() {
                return Err(reject(
                    "benchmark",
                    "Missing review/question metadata or duplicate case ID",
                ));
            }
            if !matches!(
                case.expected_status.as_str(),
                "executed" | "needs_clarification" | "unsupported" | "parsing_error"
            ) {
                return Err(reject("benchmark", "Unknown expected status"));
            }
            let answerable = case.expected_status == "executed";
            if answerable != case.gold.is_some()
                || answerable != case.reference_sparql.is_some()
                || answerable != case.expected_bindings.is_some()
            {
                return Err(reject(
                    "benchmark",
                    "Answerable cases require IR, independent query and frozen bindings",
                ));
            }
        }
        let start = Instant::now();
        let mut cases = Vec::new();
        for case in benchmark.cases.iter().filter(|c| c.split == split) {
            let mut score = CaseScore::new(case);
            let case_start = Instant::now();
            let scored: Result<()> = (|| {
                policy.authorize(&case.scope)?;
                score.stage = "proposal".into();
                let proposal = if let Some(parser) = parser {
                    score.stage = "catalog".into();
                    let catalog_start = Instant::now();
                    let request = self.parser_request(&case.question, &case.scope, policy);
                    score.catalog_ms = Some(catalog_start.elapsed().as_secs_f64() * 1000.0);
                    let request = request?;
                    let context = if parser.compact_v2() {
                        Some(self.compact_context(
                            &case.question,
                            &case.scope,
                            policy,
                            100.min(policy.max_rows),
                        )?)
                    } else {
                        None
                    };
                    score.catalog_ms = Some(catalog_start.elapsed().as_secs_f64() * 1000.0);
                    // Diagnostics only: evaluate the untouched model proposal. This
                    // marker is NOT a correct model abstention or compiler rejection.
                    score.preflight_would_block = preflight(&request).map(|v| v.code().into());
                    score.stage = "generation".into();
                    let generation_start = Instant::now();
                    let generated = if let Some(context) = &context {
                        parser.propose_compact(context)
                    } else {
                        parser.propose(&request)
                    };
                    score.generation_ms = Some(generation_start.elapsed().as_secs_f64() * 1000.0);
                    let raw = generated?;
                    score.raw_response = Some(String::from_utf8_lossy(&raw).into_owned());
                    score.json_valid =
                        Some(serde_json::from_slice::<serde_json::Value>(&raw).is_ok());
                    score.contract_valid = Some(false);
                    score.stage = if score.json_valid == Some(true) {
                        "response_schema"
                    } else {
                        "json_generation"
                    }
                    .into();
                    if let Some(context) = &context {
                        let decoded = decode_intent(&raw)?;
                        score.contract_valid = Some(true);
                        score.proposal_status = Some(
                            match &decoded.proposal {
                                CompactProposal::Candidate { .. } => "candidate",
                                CompactProposal::Unsupported { .. } => "unsupported",
                                CompactProposal::NeedsClarification { .. } => "needs_clarification",
                            }
                            .into(),
                        );
                        score.stage = "compact_expansion".into();
                        score.safety_valid = Some(false);
                        let started = Instant::now();
                        let expanded = self.expand_compact(context, &decoded, policy);
                        score.expansion_ms = Some(started.elapsed().as_secs_f64() * 1000.0);
                        let expanded = expanded?;
                        score.safety_valid = None;
                        if let Proposal::Candidate { plan } = &expanded {
                            score.expanded_plan = Some(plan.clone());
                        }
                        expanded
                    } else {
                        let decoded = decode_response(&raw)?;
                        score.contract_valid = Some(true);
                        decoded.proposal
                    }
                } else if let Some(gold) = &case.gold {
                    Proposal::Candidate { plan: gold.clone() }
                } else {
                    // Bookkeeping only: no question understanding or abstention capability is measured.
                    score.stage = "fixture_status_only".into();
                    score.detail =
                        "Expected abstention recorded, not inferred or model-tested".into();
                    score.passed = true;
                    return Ok(());
                };
                score.proposal_status = Some(
                    match &proposal {
                        Proposal::Candidate { .. } => "candidate",
                        Proposal::NeedsClarification { .. } => "needs_clarification",
                        Proposal::Unsupported { .. } => "unsupported",
                        Proposal::ParsingError { .. } => "parsing_error",
                    }
                    .into(),
                );
                score.stage = "abstention".into();
                let plan = match proposal {
                    Proposal::Candidate { plan } => plan,
                    Proposal::NeedsClarification { .. } => {
                        score.passed = case.expected_status == "needs_clarification";
                        return Ok(());
                    }
                    Proposal::Unsupported { .. } => {
                        score.passed = case.expected_status == "unsupported";
                        return Ok(());
                    }
                    Proposal::ParsingError { .. } => {
                        score.passed = case.expected_status == "parsing_error";
                        return Ok(());
                    }
                };
                score.stage = "validation".into();
                score.safety_valid = Some(false);
                let compact = parser.is_some_and(SemanticParser::compact_v2);
                let comparable_plan = if compact {
                    canonical_plan(&plan)
                } else {
                    plan.clone()
                };
                let gold = case.gold.as_ref().map(|p| {
                    if compact {
                        canonical_plan(p)
                    } else {
                        p.clone()
                    }
                });
                score.structural_ir_exact = Some(gold.as_ref() == Some(&comparable_plan));
                if let Some(gold) = &gold {
                    score.components_exact = plan_components(&comparable_plan, gold);
                }
                if plan.scope.iter().collect::<BTreeSet<_>>()
                    != case.scope.iter().collect::<BTreeSet<_>>()
                {
                    return Err(reject(
                        "scope",
                        "Proposal changes the question's requested scope",
                    ));
                }
                let validation_start = Instant::now();
                let compiled = self.compile(&plan, policy);
                score.validation_compile_ms =
                    Some(validation_start.elapsed().as_secs_f64() * 1000.0);
                compiled?;
                score.safety_valid = Some(true);
                score.stage = "execution".into();
                let origin = parser.map_or(PlanOrigin::Fixture, SemanticParser::origin);
                let result = self.execute(&plan, policy, origin)?;
                score.end_to_end_ms = case_start.elapsed().as_secs_f64() * 1000.0;
                score.pipeline_ms =
                    Some(result.validation_ms + result.query_ms + result.evidence_ms);
                score.wrong_plan_successful_execution = score.structural_ir_exact == Some(false);
                score.result_classification = if result.bindings.is_empty() {
                    "empty_query_result_not_real_world_false"
                } else {
                    "nonempty_query_result"
                }
                .into();
                score.execution = Some(result);
                let result = score.execution.as_ref().expect("stored execution");
                if case.expected_status != "executed" {
                    score.detail = "Executed a plan for a question expected to abstain".into();
                    return Ok(());
                }
                score.stage = "reference".into();
                let reference = self.reference(
                    case.reference_sparql.as_deref().unwrap_or_default(),
                    &case.scope,
                    policy,
                )?;
                let expected = case.expected_bindings.as_deref().unwrap_or_default();
                if !set_scores(&reference, expected).0 {
                    return Err(reject(
                        "gold_reference_mismatch",
                        "Frozen bindings disagree with independent reference SPARQL",
                    ));
                }
                // Compact output names are slots; compare columns by projection position.
                let bindings = if compact {
                    align_columns(
                        &result.bindings,
                        &plan,
                        case.gold.as_ref().expect("answerable gold"),
                    )
                } else {
                    result.bindings.clone()
                };
                let (exact, precision, recall, f1) = if compact
                    && plan.projection.len()
                        != case
                            .gold
                            .as_ref()
                            .expect("answerable gold")
                            .projection
                            .len()
                {
                    (false, 0.0, 0.0, 0.0)
                } else {
                    set_scores(&bindings, expected)
                };
                score.exact_result_set = Some(exact);
                score.precision = Some(precision);
                score.recall = Some(recall);
                score.f1 = Some(f1);
                score.passed = exact
                    && score.structural_ir_exact == Some(true)
                    && result.complete_within_scope;
                score.stage = "scored".into();
                Ok(())
            })();
            if let Err(error) = scored {
                score.error_code = Some(match &error {
                    crate::Error::Rejected { code, .. } => (*code).into(),
                    crate::Error::Json(_) => "json_contract".into(),
                    crate::Error::Store(_) => "store".into(),
                    crate::Error::Io(_) => "io".into(),
                });
                if score.error_code.as_deref() == Some("compiled_query") {
                    score.stage = "compiler".into();
                }
                score.detail = error.to_string();
            }
            if score.end_to_end_ms == 0.0 {
                score.end_to_end_ms = case_start.elapsed().as_secs_f64() * 1000.0;
            }
            cases.push(score);
        }
        if cases.is_empty() {
            return Err(reject(
                "benchmark",
                "No cases in the explicitly requested split",
            ));
        }
        let passed = cases.iter().filter(|c| c.passed).count();
        let mut per_family = BTreeMap::new();
        for case in &cases {
            let counts = per_family.entry(case.family.clone()).or_insert((0, 0));
            counts.0 += usize::from(case.passed);
            counts.1 += 1;
        }
        let mut latencies: Vec<_> = cases.iter().filter_map(|c| c.pipeline_ms).collect();
        latencies.sort_by(f64::total_cmp);
        let source = [
            include_bytes!("lib.rs").as_slice(),
            include_bytes!("ir.rs"),
            include_bytes!("catalog.rs"),
            include_bytes!("compiler.rs"),
            include_bytes!("execution.rs"),
            include_bytes!("parser.rs"),
            include_bytes!("evaluation.rs"),
            include_bytes!("compact.rs"),
        ]
        .concat();
        Ok(Report {
            mode: if parser.is_some() { "parser_proposals" } else { "oracle_no_model" },
            benchmark: benchmark.name.clone(), benchmark_digest: snapshot_id(&serde_json::to_vec(benchmark)?, "benchmark-json-v1"),
            snapshot_id: self.id.clone(), schema_digest: snapshot_id(&serde_json::to_vec(&schemars::schema_for!(Plan))?, "ir-schema-v1"),
            implementation_digest: snapshot_id(&source, "core-source-v1"),
            dependency_lock_digest: snapshot_id(include_bytes!("../../../Cargo.lock"), "cargo-lock"),
            model: parser.and_then(SemanticParser::model), split: split.into(), total: cases.len(), passed, per_family,
            pass_rate_wilson_95: wilson(passed, cases.len()), cases,
            pipeline_p50_ms: quantile(&latencies, 0.50), pipeline_p95_ms: quantile(&latencies, 0.95),
            pipeline_p99_ms: quantile(&latencies, 0.99), process_peak_rss_kib: peak_rss(),
            measurement_scope: "single-process warm query pipeline including validation and evidence; excludes ingestion, parser generation and reference evaluation; VmHWM is process lifetime peak, not model RAM",
            elapsed_ms: start.elapsed().as_secs_f64() * 1000.0,
            readiness_claim: "no_semantic_parser_feasibility_claim; candidate_gold_requires_independent_human_review",
        })
    }
}
