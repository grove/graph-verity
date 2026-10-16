//! Oracle and parser runs share scoring. Fixture correctness is never reported as model accuracy.
use crate::{catalog::Policy, execution::{PlanOrigin, Row}, ir::Plan,
    parser::{decode_response, Proposal, SemanticParser}, reject, snapshot_id, Result, Snapshot};
use serde::{Deserialize, Serialize};
use std::{collections::{BTreeMap, BTreeSet}, time::Instant};

#[derive(Clone, Debug, Serialize, Deserialize)]
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

#[derive(Debug, Serialize, Deserialize)]
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
}

impl CaseScore {
    fn new(case: &Case) -> Self {
        Self { id: case.id.clone(), family: case.family.clone(), passed: false,
            stage: "not_run".into(), detail: String::new(), json_valid: None,
            structural_ir_exact: None, exact_result_set: None, wrong_plan_successful_execution: false,
            precision: None, recall: None, f1: None, pipeline_ms: None }
    }
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
    let precision = if actual.is_empty() { if expected.is_empty() { 1.0 } else { 0.0 } } else { common / actual.len() as f64 };
    let recall = if expected.is_empty() { 1.0 } else { common / expected.len() as f64 };
    let f1 = if precision + recall == 0.0 { 0.0 } else { 2.0 * precision * recall / (precision + recall) };
    (actual == expected, precision, recall, f1)
}

fn quantile(values: &[f64], fraction: f64) -> Option<f64> {
    if values.is_empty() { return None; }
    let index = ((values.len() as f64 * fraction).ceil() as usize).saturating_sub(1);
    values.get(index).copied()
}

fn wilson(passed: usize, total: usize) -> (f64, f64) {
    if total == 0 { return (0.0, 1.0); }
    let n = total as f64;
    let p = passed as f64 / n;
    let z2 = 1.96_f64.powi(2);
    let denominator = 1.0 + z2 / n;
    let center = (p + z2 / (2.0 * n)) / denominator;
    let radius = 1.96 * ((p * (1.0 - p) + z2 / (4.0 * n)) / n).sqrt() / denominator;
    ((center - radius).max(0.0), (center + radius).min(1.0))
}

fn peak_rss() -> Option<u64> {
    std::fs::read_to_string("/proc/self/status").ok()?.lines()
        .find_map(|line| line.strip_prefix("VmHWM:").and_then(|v| v.split_whitespace().next()?.parse().ok()))
}

impl Snapshot {
    pub fn evaluate(&self, benchmark: &Benchmark, split: &str, policy: &Policy, parser: Option<&dyn SemanticParser>) -> Result<Report> {
        if benchmark.version != 1 || benchmark.snapshot_id != self.id || benchmark.cases.len() > 1000 {
            return Err(reject("benchmark", "Invalid benchmark version, snapshot or size"));
        }
        let mut ids = BTreeSet::new();
        for case in &benchmark.cases {
            if !ids.insert(&case.id) || case.question.is_empty() || case.review_status.is_empty() {
                return Err(reject("benchmark", "Missing review/question metadata or duplicate case ID"));
            }
            if !matches!(case.expected_status.as_str(), "executed" | "needs_clarification" | "unsupported" | "parsing_error") {
                return Err(reject("benchmark", "Unknown expected status"));
            }
            let answerable = case.expected_status == "executed";
            if answerable != case.gold.is_some() || answerable != case.reference_sparql.is_some()
                || answerable != case.expected_bindings.is_some() {
                return Err(reject("benchmark", "Answerable cases require IR, independent query and frozen bindings"));
            }
        }
        let start = Instant::now();
        let mut cases = Vec::new();
        for case in benchmark.cases.iter().filter(|c| c.split == split) {
            let mut score = CaseScore::new(case);
            let scored: Result<()> = (|| {
                policy.authorize(&case.scope)?;
                score.stage = "proposal".into();
                let proposal = if let Some(parser) = parser {
                    let request = self.parser_request(&case.question, &case.scope, policy)?;
                    let raw = parser.propose(&request)?;
                    score.json_valid = Some(serde_json::from_slice::<serde_json::Value>(&raw).is_ok());
                    decode_response(&raw)?.proposal
                } else if let Some(gold) = &case.gold {
                    Proposal::Candidate { plan: gold.clone() }
                } else {
                    // Bookkeeping only: no question understanding or abstention capability is measured.
                    score.stage = "fixture_status_only".into();
                    score.detail = "Expected abstention recorded, not inferred or model-tested".into();
                    score.passed = true;
                    return Ok(());
                };
                let plan = match proposal {
                    Proposal::Candidate { plan } => plan,
                    Proposal::NeedsClarification { .. } => { score.passed = case.expected_status == "needs_clarification"; return Ok(()); }
                    Proposal::Unsupported { .. } => { score.passed = case.expected_status == "unsupported"; return Ok(()); }
                    Proposal::ParsingError { .. } => { score.passed = case.expected_status == "parsing_error"; return Ok(()); }
                };
                score.stage = "validation".into();
                if plan.scope.iter().collect::<BTreeSet<_>>() != case.scope.iter().collect::<BTreeSet<_>>() {
                    return Err(reject("scope", "Proposal changes the question's requested scope"));
                }
                self.compile(&plan, policy)?;
                score.structural_ir_exact = Some(case.gold.as_ref() == Some(&plan));
                score.stage = "execution".into();
                let result = self.execute(&plan, policy, PlanOrigin::Fixture)?;
                score.pipeline_ms = Some(result.validation_ms + result.query_ms + result.evidence_ms);
                score.wrong_plan_successful_execution = score.structural_ir_exact == Some(false);
                if case.expected_status != "executed" {
                    score.detail = "Executed a plan for a question expected to abstain".into();
                    return Ok(());
                }
                score.stage = "reference".into();
                let reference = self.reference(case.reference_sparql.as_deref().unwrap_or_default(), &case.scope, policy)?;
                let expected = case.expected_bindings.as_deref().unwrap_or_default();
                if !set_scores(&reference, expected).0 {
                    return Err(reject("gold_reference_mismatch", "Frozen bindings disagree with independent reference SPARQL"));
                }
                let (exact, precision, recall, f1) = set_scores(&result.bindings, expected);
                score.exact_result_set = Some(exact);
                score.precision = Some(precision); score.recall = Some(recall); score.f1 = Some(f1);
                score.passed = exact && score.structural_ir_exact == Some(true) && result.complete_within_scope;
                score.stage = "scored".into();
                Ok(())
            })();
            if let Err(error) = scored { score.detail = error.to_string(); }
            cases.push(score);
        }
        if cases.is_empty() { return Err(reject("benchmark", "No cases in the explicitly requested split")); }
        let passed = cases.iter().filter(|c| c.passed).count();
        let mut per_family = BTreeMap::new();
        for case in &cases {
            let counts = per_family.entry(case.family.clone()).or_insert((0, 0));
            counts.0 += usize::from(case.passed); counts.1 += 1;
        }
        let mut latencies: Vec<_> = cases.iter().filter_map(|c| c.pipeline_ms).collect();
        latencies.sort_by(f64::total_cmp);
        let source = [include_bytes!("lib.rs").as_slice(), include_bytes!("ir.rs"),
            include_bytes!("catalog.rs"), include_bytes!("compiler.rs"), include_bytes!("execution.rs"),
            include_bytes!("parser.rs"), include_bytes!("evaluation.rs")].concat();
        Ok(Report {
            mode: if parser.is_some() { "parser_proposals" } else { "oracle_no_model" },
            benchmark: benchmark.name.clone(), benchmark_digest: snapshot_id(&serde_json::to_vec(benchmark)?, "benchmark-json-v1"),
            snapshot_id: self.id.clone(), schema_digest: snapshot_id(&serde_json::to_vec(&schemars::schema_for!(Plan))?, "ir-schema-v1"),
            implementation_digest: snapshot_id(&source, "core-source-v1"),
            dependency_lock_digest: snapshot_id(include_bytes!("../../../Cargo.lock"), "cargo-lock"),
            model: None, split: split.into(), total: cases.len(), passed, per_family,
            pass_rate_wilson_95: wilson(passed, cases.len()), cases,
            pipeline_p50_ms: quantile(&latencies, 0.50), pipeline_p95_ms: quantile(&latencies, 0.95),
            pipeline_p99_ms: quantile(&latencies, 0.99), process_peak_rss_kib: peak_rss(),
            measurement_scope: "single-process warm query pipeline including validation and evidence; excludes ingestion, parser generation and reference evaluation; VmHWM is process lifetime peak, not model RAM",
            elapsed_ms: start.elapsed().as_secs_f64() * 1000.0,
            readiness_claim: "no_semantic_parser_feasibility_claim; candidate_gold_requires_independent_human_review",
        })
    }
}
