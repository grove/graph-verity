//! Deterministic local RDF execution; no model runtime or public raw-SPARQL API.
#![forbid(unsafe_code)]

pub mod ask;
pub mod catalog;
pub mod compact;
pub mod compiler;
pub mod discovery;
pub mod evaluation;
pub mod execution;
pub mod find;
pub mod ir;
pub mod navigation;
pub mod parser;
pub mod vocabulary;

use oxigraph::io::RdfFormat;
use oxigraph::sparql::{QueryResults, SparqlEvaluator};
use oxigraph::store::Store;
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::{fs::File, io::Read, path::Path};

pub type Result<T> = std::result::Result<T, Error>;

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("{code}: {message}")]
    Rejected { code: &'static str, message: String },
    #[error("RDF/storage error: {0}")]
    Store(String),
    #[error(transparent)]
    Io(#[from] std::io::Error),
    #[error(transparent)]
    Json(#[from] serde_json::Error),
}

pub fn reject(code: &'static str, message: impl Into<String>) -> Error {
    Error::Rejected {
        code,
        message: message.into(),
    }
}

pub fn read_limited(path: impl AsRef<Path>, max_bytes: usize) -> Result<Vec<u8>> {
    let file = File::open(path)?;
    let mut bytes = Vec::new();
    file.take(max_bytes as u64 + 1).read_to_end(&mut bytes)?;
    if bytes.len() > max_bytes {
        return Err(reject(
            "input_limit",
            "Input file exceeds the command's byte limit",
        ));
    }
    Ok(bytes)
}

/// Release-byte identity, not RDF isomorphism or blank-node canonicalization.
pub fn snapshot_id(bytes: &[u8], format: &str) -> String {
    let mut hash = Sha256::new();
    hash.update(b"graph-verity-snapshot-v1\0");
    hash.update(format.as_bytes());
    hash.update([0]);
    hash.update(bytes);
    format!("sha256:{:x}", hash.finalize())
}

pub struct Snapshot {
    pub(crate) store: Store,
    id: String,
}

#[derive(Debug, Serialize)]
pub struct SnapshotInfo {
    pub snapshot_id: String,
    pub quad_count: usize,
    pub named_graphs: Vec<String>,
    pub entailment: &'static str,
}

impl Snapshot {
    pub fn id(&self) -> &str {
        &self.id
    }

    pub fn from_bytes(bytes: &[u8], format: &str) -> Result<Self> {
        if bytes.len() > 16 * 1024 * 1024 {
            return Err(reject("input_limit", "RDF input exceeds 16 MiB"));
        }
        let rdf_format = match format {
            "trig" => RdfFormat::TriG,
            "nquads" => RdfFormat::NQuads,
            "turtle" => RdfFormat::Turtle,
            _ => return Err(reject("format", "Use trig, nquads, or turtle")),
        };
        let store = Store::new().map_err(|e| Error::Store(e.to_string()))?;
        store
            .load_from_reader(rdf_format, bytes)
            // Parser diagnostics can quote data from graphs the caller cannot access.
            .map_err(|_| Error::Store("RDF input could not be parsed".into()))?;
        if store.len().map_err(|e| Error::Store(e.to_string()))? > 100_000 {
            return Err(reject("quad_limit", "Snapshot exceeds 100,000 quads"));
        }
        Ok(Self {
            store,
            id: snapshot_id(bytes, format),
        })
    }

    /// Administrative inspection, not an authorization-filtered end-user endpoint.
    pub fn info(&self) -> Result<SnapshotInfo> {
        let mut graphs = self
            .store
            .named_graphs()
            .map(|g| {
                g.map(|g| g.to_string())
                    .map_err(|e| Error::Store(e.to_string()))
            })
            .collect::<Result<Vec<_>>>()?;
        graphs.sort();
        Ok(SnapshotInfo {
            snapshot_id: self.id.clone(),
            quad_count: self.store.len().map_err(|e| Error::Store(e.to_string()))?,
            named_graphs: graphs,
            entailment: "explicit_quads_only_open_world",
        })
    }

    /// Administrative fixed smoke query, never a user/model-supplied query.
    pub fn smoke_count(&self) -> Result<String> {
        let result = SparqlEvaluator::new()
            .parse_query("SELECT (COUNT(*) AS ?count) WHERE { GRAPH ?g { ?s ?p ?o } }")
            .map_err(|e| Error::Store(e.to_string()))?
            .on_store(&self.store)
            .execute()
            .map_err(|e| Error::Store(e.to_string()))?;
        if let QueryResults::Solutions(mut rows) = result {
            if let Some(row) = rows.next() {
                let row = row.map_err(|e| Error::Store(e.to_string()))?;
                if let Some(value) = row.get("count") {
                    return Ok(value.to_string());
                }
            }
        }
        Err(Error::Store("Expected a count binding".into()))
    }
}

pub fn schemas() -> serde_json::Value {
    serde_json::json!({
        "contract_version": 1,
        "plan": schemars::schema_for!(ir::Plan),
        "policy": schemars::schema_for!(catalog::Policy),
        "benchmark": schemars::schema_for!(evaluation::Benchmark),
        "parser_input": schemars::schema_for!(parser::ParserRequest),
        "parser_output": schemars::schema_for!(parser::ParserResponse),
        "future_local_config": schemars::schema_for!(parser::FutureLocalConfig)
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    const FIXTURE: &[u8] = include_bytes!("../../../tests/fixtures/smoke.trig");
    #[test]
    fn parses_and_queries_real_oxigraph() {
        let graph = Snapshot::from_bytes(FIXTURE, "trig").unwrap();
        assert_eq!(graph.info().unwrap().quad_count, 14);
        assert_eq!(graph.info().unwrap().named_graphs.len(), 2);
        assert_eq!(
            graph.smoke_count().unwrap(),
            "\"14\"^^<http://www.w3.org/2001/XMLSchema#integer>"
        );
    }
    #[test]
    fn reproducible_snapshot_and_explicit_format() {
        let a = Snapshot::from_bytes(FIXTURE, "trig").unwrap();
        let b = Snapshot::from_bytes(FIXTURE, "trig").unwrap();
        assert_eq!(a.id(), b.id());
        assert_ne!(snapshot_id(FIXTURE, "trig"), snapshot_id(FIXTURE, "turtle"));
        assert!(Snapshot::from_bytes(b"not RDF", "trig").is_err());
        assert!(Snapshot::from_bytes(FIXTURE, "unknown").is_err());
    }
}
