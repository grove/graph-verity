//! Bounded SELECT execution and explicit, separately bounded supporting statements.
use crate::{catalog::{graph_id, Policy}, ir::Plan, reject, Error, Result, Snapshot};
use oxigraph::{model::Term, sparql::{CancellationToken, QueryResults, SparqlEvaluator}, store::Store};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::{collections::BTreeMap, sync::mpsc, thread, time::{Duration, Instant}};

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize, JsonSchema)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum RdfTerm {
    Iri { value: String },
    BlankNode { value: String },
    Literal { value: String, datatype: String, language: Option<String> },
}

impl From<&Term> for RdfTerm {
    fn from(term: &Term) -> Self {
        match term {
            Term::NamedNode(node) => Self::Iri { value: node.as_str().into() },
            Term::BlankNode(node) => Self::BlankNode { value: node.as_str().into() },
            Term::Literal(literal) => Self::Literal {
                value: literal.value().into(), datatype: literal.datatype().as_str().into(),
                language: literal.language().map(str::to_owned),
            },
        }
    }
}

pub type Row = BTreeMap<String, RdfTerm>;

#[derive(Clone, Copy, Debug, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum PlanOrigin { Manual, Fixture }

#[derive(Debug, Serialize)]
pub struct Statement {
    pub subject: RdfTerm,
    pub predicate: RdfTerm,
    pub object: RdfTerm,
    pub source_graph: RdfTerm,
}

#[derive(Debug, Serialize)]
pub struct Execution {
    pub status: &'static str,
    pub origin: PlanOrigin,
    pub interpretation_correctness: &'static str,
    pub real_world_truth: &'static str,
    pub absence_policy: &'static str,
    pub snapshot_id: String,
    pub scope: Vec<String>,
    pub plan: Plan,
    pub sparql: String,
    pub catalog_digest: String,
    pub bindings: Vec<Row>,
    pub complete_within_scope: bool,
    pub evidence: Vec<Statement>,
    pub evidence_complete_for_returned_rows: bool,
    pub evidence_semantics: &'static str,
    pub validation_ms: f64,
    pub query_ms: f64,
    pub evidence_ms: f64,
}

/// Cooperative cancellation; the watchdog is joined and never left sleeping after a query.
struct Deadline {
    token: CancellationToken,
    done: Option<mpsc::Sender<()>>,
    worker: Option<thread::JoinHandle<()>>,
    start: Instant,
    duration: Duration,
}
impl Deadline {
    fn new(milliseconds: u64) -> Self {
        let token = CancellationToken::new();
        let other = token.clone();
        let (send, receive) = mpsc::channel();
        let duration = Duration::from_millis(milliseconds);
        let worker = thread::spawn(move || {
            if receive.recv_timeout(duration).is_err() { other.cancel(); }
        });
        Self { token, done: Some(send), worker: Some(worker), start: Instant::now(), duration }
    }
    fn check(&self) -> Result<()> {
        if self.start.elapsed() >= self.duration {
            Err(reject("timeout", "Execution deadline exceeded; no complete result is asserted"))
        } else { Ok(()) }
    }
}
impl Drop for Deadline {
    fn drop(&mut self) {
        if let Some(done) = self.done.take() { let _ = done.send(()); }
        if let Some(worker) = self.worker.take() { let _ = worker.join(); }
    }
}

fn select(store: &Store, query: &str, cap: usize, deadline: &Deadline) -> Result<Vec<Row>> {
    deadline.check()?;
    let result = SparqlEvaluator::new().with_cancellation_token(deadline.token.clone())
        .parse_query(query).map_err(|e| reject("compiled_query", e.to_string()))?
        .on_store(store).execute().map_err(|e| reject("execution", e.to_string()))?;
    let QueryResults::Solutions(solutions) = result else {
        return Err(reject("execution", "Only SELECT results are accepted"));
    };
    let mut rows = Vec::new();
    for solution in solutions {
        deadline.check()?;
        let solution = solution.map_err(|e| reject("execution", e.to_string()))?;
        rows.push(solution.iter().map(|(name, term)| (name.as_str().into(), RdfTerm::from(term))).collect());
        if rows.len() > cap { return Err(reject("row_limit", "Reference query exceeds the evaluation row bound")); }
    }
    deadline.check()?;
    Ok(rows)
}

impl Snapshot {
    pub fn execute(&self, plan: &Plan, policy: &Policy, origin: PlanOrigin) -> Result<Execution> {
        let start = Instant::now();
        let compiled = self.compile(plan, policy)?;
        let validation_ms = start.elapsed().as_secs_f64() * 1000.0;
        let deadline = Deadline::new(policy.timeout_ms);
        let start = Instant::now();
        let mut bindings = select(&self.store, &compiled.query, plan.limit as usize + 1, &deadline)?;
        let complete = bindings.len() <= plan.limit as usize;
        bindings.truncate(plan.limit as usize);
        let query_ms = start.elapsed().as_secs_f64() * 1000.0;
        let start = Instant::now();
        let mut witnesses = select(&self.store, &compiled.evidence_query, policy.max_evidence as usize + 1, &deadline)?;
        let evidence_complete = witnesses.len() <= policy.max_evidence as usize;
        witnesses.truncate(policy.max_evidence as usize);
        let mut evidence = Vec::new();
        for mut row in witnesses {
            let mut take = |key: &str| row.remove(key).ok_or_else(|| reject("evidence", "Unbound witness term"));
            evidence.push(Statement {
                subject: take("__s")?, predicate: take("__p")?,
                object: take("__o")?, source_graph: take("__g")?,
            });
        }
        let execution = Execution {
            status: if complete { "executed" } else { "truncated" }, origin,
            interpretation_correctness: "not_assessed", real_world_truth: "not_established",
            absence_policy: "open_world_missing_facts_are_not_false",
            snapshot_id: self.id.clone(), scope: plan.scope.clone(), plan: plan.clone(),
            sparql: compiled.query, catalog_digest: compiled.catalog_digest, bindings,
            complete_within_scope: complete, evidence,
            evidence_complete_for_returned_rows: evidence_complete,
            evidence_semantics: "union_of_contributing_pattern_statements_for_returned_rows_or_groups; counts_require_the_scoped_query_not_just_positive_witnesses",
            validation_ms, query_ms, evidence_ms: start.elapsed().as_secs_f64() * 1000.0,
        };
        if serde_json::to_vec(&execution)?.len() > 8 * 1024 * 1024 {
            return Err(reject("output_limit", "Result and evidence exceed 8 MiB"));
        }
        Ok(execution)
    }

    /// Evaluation-only path. The reference sees a physically isolated authorized store.
    /// No public raw-query execution API is exposed by the CLI or library.
    pub(crate) fn reference(&self, query: &str, scope: &[String], policy: &Policy) -> Result<Vec<Row>> {
        policy.authorize(scope)?;
        if query.len() > 65_536 { return Err(reject("input_limit", "Reference exceeds 64 KiB")); }
        let scoped = Store::new().map_err(|e| Error::Store(e.to_string()))?;
        for quad in self.store.iter() {
            let quad = quad.map_err(|e| Error::Store(e.to_string()))?;
            if graph_id(&quad.graph_name).is_some_and(|g| scope.iter().any(|s| s == g)) {
                scoped.insert(quad.as_ref()).map_err(|e| Error::Store(e.to_string()))?;
            }
        }
        select(&scoped, query, policy.max_rows as usize, &Deadline::new(policy.timeout_ms))
    }
}
