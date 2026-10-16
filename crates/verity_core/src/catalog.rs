//! Catalogs are constructed only after authorization, from the requested named graphs.
use crate::{ir::{iri, Value, RDF_TYPE}, reject, snapshot_id, Error, Result, Snapshot};
use oxigraph::model::{GraphName, NamedOrBlankNode, Term};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Policy {
    pub version: u32,
    pub graphs: Vec<String>,
    pub max_rows: u32,
    pub max_evidence: u32,
    pub timeout_ms: u64,
}

impl Policy {
    pub(crate) fn authorize(&self, scope: &[String]) -> Result<()> {
        if self.version != 1 || self.max_rows == 0 || self.max_rows > 1000
            || self.max_evidence > 10_000 || self.timeout_ms == 0 || self.timeout_ms > 30_000 {
            return Err(reject("policy", "Invalid operator-supplied policy"));
        }
        if scope.is_empty() || scope.len() > 8 || scope.iter().collect::<BTreeSet<_>>().len() != scope.len()
            || scope.iter().any(|g| !self.graphs.contains(g)) {
            return Err(reject("scope", "Scope is not authorized"));
        }
        for graph in scope { iri(graph)?; }
        Ok(())
    }
}

#[derive(Clone, Debug, Default, Serialize, JsonSchema)]
pub struct Entry {
    pub roles: BTreeSet<String>,
    pub labels: BTreeSet<Label>,
    pub graphs: BTreeSet<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, JsonSchema)]
pub struct Label { pub text: String, pub language: Option<String>, pub datatype: String }

#[derive(Clone, Debug, Default, Serialize, JsonSchema)]
pub struct Profile {
    pub object_types: BTreeSet<String>,
    pub ill_typed: bool,
}

#[derive(Clone, Debug, Serialize, JsonSchema)]
pub struct Catalog {
    pub snapshot_id: String,
    pub scope: Vec<String>,
    pub entries: BTreeMap<String, Entry>,
    pub profiles: BTreeMap<String, BTreeMap<String, Profile>>,
    pub digest: String,
}

impl Catalog {
    /// Exact IRI or case-folded exact label only. This is not semantic retrieval.
    pub fn resolve(&self, text: &str, role: &str) -> Result<String> {
        let folded = text.to_lowercase();
        let candidates: Vec<_> = self.entries.iter().filter(|(id, entry)| {
            entry.roles.contains(role) && (id.as_str() == text
                || entry.labels.iter().any(|l| l.text.to_lowercase() == folded))
        }).map(|(id, _)| id.clone()).collect();
        match candidates.as_slice() {
            [id] => Ok(id.clone()),
            [] => Err(reject("unknown_identifier", "No authorized exact identifier or label match")),
            _ => Err(reject("needs_clarification", "Several authorized identifiers share this label")),
        }
    }
}

fn record(entries: &mut BTreeMap<String, Entry>, id: &str, role: &str, graph: &str) {
    let entry = entries.entry(id.into()).or_default();
    entry.roles.insert(role.into());
    entry.graphs.insert(graph.into());
}

pub(crate) fn graph_id(graph: &GraphName) -> Option<&str> {
    if let GraphName::NamedNode(node) = graph { Some(node.as_str()) } else { None }
}

impl Snapshot {
    pub fn catalog(&self, scope: &[String], policy: &Policy) -> Result<Catalog> {
        policy.authorize(scope)?;
        let mut entries = BTreeMap::new();
        let mut profiles: BTreeMap<String, BTreeMap<String, Profile>> = BTreeMap::new();
        let mut labels: BTreeMap<String, BTreeSet<Label>> = BTreeMap::new();
        for quad in self.store.iter() {
            let quad = quad.map_err(|e| Error::Store(e.to_string()))?;
            let Some(graph) = graph_id(&quad.graph_name) else { continue; };
            if !scope.iter().any(|g| g == graph) { continue; }
            let predicate = quad.predicate.as_str();
            record(&mut entries, predicate, "predicate", graph);
            if let NamedOrBlankNode::NamedNode(node) = &quad.subject {
                record(&mut entries, node.as_str(), "entity", graph);
                if matches!(predicate,
                    "http://www.w3.org/2000/01/rdf-schema#label" |
                    "http://www.w3.org/2004/02/skos/core#altLabel") {
                    if let Term::Literal(literal) = &quad.object {
                        labels.entry(node.as_str().into()).or_default().insert(Label {
                            text: literal.value().into(),
                            language: literal.language().map(str::to_owned),
                            datatype: literal.datatype().as_str().into(),
                        });
                    }
                }
            }
            let profile = profiles.entry(graph.into()).or_default().entry(predicate.into()).or_default();
            match &quad.object {
                Term::NamedNode(node) => {
                    record(&mut entries, node.as_str(), "entity", graph);
                    if predicate == RDF_TYPE { record(&mut entries, node.as_str(), "class", graph); }
                    profile.object_types.insert("resource".into());
                }
                Term::BlankNode(_) => { profile.object_types.insert("resource".into()); }
                Term::Literal(literal) => {
                    profile.object_types.insert(literal.datatype().as_str().into());
                    let value = Value {
                        lexical: literal.value().into(),
                        datatype: literal.datatype().as_str().into(),
                        language: literal.language().map(str::to_owned),
                    };
                    profile.ill_typed |= value.literal().is_err();
                }
            }
        }
        for (id, value) in labels { entries.entry(id).or_default().labels = value; }
        let mut scope = scope.to_vec();
        scope.sort();
        let mut catalog = Catalog { snapshot_id: self.id.clone(), scope, entries, profiles, digest: String::new() };
        catalog.digest = snapshot_id(&serde_json::to_vec(&catalog)?, "catalog-v1");
        Ok(catalog)
    }
}
