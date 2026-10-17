//! Deterministic discovery data, built and validated inside the catalog's authorization boundary.
use crate::{
    catalog::{graph_id, Label, Policy},
    reject, snapshot_id, Error, Result, Snapshot,
};
use oxigraph::model::{NamedOrBlankNode, Term};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

pub const MAX_INDEX_BYTES: usize = 64 * 1024 * 1024;
const DESCRIPTION_CHARS: usize = 512;
const RULES: &str = "unicode-lowercase-alphanumeric-v1; no NFC, stemming, transliteration or stopwords; IRI plus observed text; en/no/nb/nn language families and untagged; descriptions including skos:definition first 512 Unicode scalars; graph-local explicit wikibase:directClaim label/alias retrieval via source statements, observed predicates only, no inference or chaining";
pub const DIRECT_CLAIM: &str = "http://wikiba.se/ontology#directClaim";

/// Operator-supplied provenance, bound to immutable snapshot bytes. Never model input.
#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DiscoveryConfig {
    pub version: u32,
    pub snapshot_id: String,
    pub graphs: BTreeMap<String, Source>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Source {
    pub source: String,
    pub license: String,
    pub source_revision: String,
    pub importer_revision: String,
}

#[derive(Debug, Serialize)]
pub struct Manifest {
    pub version: u32,
    pub snapshot_id: String,
    pub scope: Vec<String>,
    pub policy_hash: String,
    pub config_hash: String,
    pub index_revision: String,
    pub rules: &'static str,
    pub sources: BTreeMap<String, Source>,
    pub graph_hashes: BTreeMap<String, String>,
}

/// Read-only after construction. Loading persisted data requires Snapshot::load_discovery.
#[derive(Debug, Serialize)]
pub struct DiscoveryIndex {
    manifest: Manifest,
    graphs: BTreeMap<String, GraphIndex>,
    digest: String,
}

impl DiscoveryIndex {
    pub(crate) fn authorize(&self, scope: &[String], policy: &Policy) -> Result<()> {
        policy.authorize(scope)?;
        if self.manifest.policy_hash != hash(policy, "discovery-policy-v1")?
            || scope.iter().any(|g| !self.graphs.contains_key(g))
        {
            return Err(reject(
                "scope",
                "Index does not cover this policy and scope",
            ));
        }
        Ok(())
    }

    pub fn manifest(&self) -> &Manifest {
        &self.manifest
    }

    pub fn graphs(&self) -> &BTreeMap<String, GraphIndex> {
        &self.graphs
    }
}

#[derive(Debug, Serialize)]
pub struct GraphIndex {
    pub documents: BTreeMap<String, Document>,
    /// token -> original resource IRI -> term frequency, within this graph only.
    pub postings: BTreeMap<String, BTreeMap<String, u32>>,
    pub statistics: Statistics,
}

#[derive(Debug, Serialize)]
pub struct Document {
    pub roles: BTreeSet<String>,
    pub texts: BTreeSet<ObservedText>,
    pub token_count: u32,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Field {
    Label,
    Alias,
    Identifier,
    Description,
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize)]
pub struct ObservedText {
    pub field: Field,
    pub predicate: String,
    pub value: Label,
    pub truncated: bool,
    /// Retrieval association only: source_iri has this text and links to the document IRI.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub via: Option<PredicateMapping>,
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize)]
pub struct PredicateMapping {
    pub source_iri: String,
    pub predicate: String,
}

#[derive(Debug, Default, Serialize)]
pub struct Statistics {
    pub documents: usize,
    pub terms: usize,
    pub tokens: u64,
    pub empty_values: usize,
    pub omitted_language_values: usize,
    pub truncated_descriptions: usize,
}

/// Versioned lexical normalization only; RDF identity and stored text are unchanged.
pub fn tokens(text: &str) -> Vec<String> {
    text.to_lowercase()
        .split(|c: char| !c.is_alphanumeric())
        .filter(|part| !part.is_empty())
        .map(str::to_owned)
        .collect()
}

fn field(predicate: &str) -> Option<Field> {
    Some(match predicate {
        "http://www.w3.org/2000/01/rdf-schema#label"
        | "http://www.w3.org/2004/02/skos/core#prefLabel"
        | "http://schema.org/name"
        | "https://schema.org/name" => Field::Label,
        "http://www.w3.org/2004/02/skos/core#altLabel"
        | "http://schema.org/alternateName"
        | "https://schema.org/alternateName" => Field::Alias,
        "http://purl.org/dc/terms/identifier"
        | "http://schema.org/identifier"
        | "https://schema.org/identifier" => Field::Identifier,
        "http://www.w3.org/2000/01/rdf-schema#comment"
        | "http://www.w3.org/2004/02/skos/core#definition"
        | "http://purl.org/dc/terms/description"
        | "http://schema.org/description"
        | "https://schema.org/description" => Field::Description,
        _ => return None,
    })
}

fn hash(value: &impl Serialize, domain: &str) -> Result<String> {
    Ok(snapshot_id(&serde_json::to_vec(value)?, domain))
}

// Conservative JSON allocation budget prevents long identifiers multiplying through postings.
fn reserve(budget: &mut usize, bytes: usize) -> Result<()> {
    *budget = budget.checked_sub(bytes).ok_or_else(|| {
        reject(
            "index_limit",
            "Discovery allocation budget exceeded; narrow scope",
        )
    })?;
    Ok(())
}

impl Snapshot {
    pub fn build_discovery(
        &self,
        scope: &[String],
        policy: &Policy,
        config: &DiscoveryConfig,
    ) -> Result<DiscoveryIndex> {
        policy.authorize(scope)?;
        if config.version != 1 || config.snapshot_id != self.id() {
            return Err(reject(
                "index_manifest",
                "Incompatible source manifest or snapshot",
            ));
        }
        let mut scope = scope.to_vec();
        scope.sort();
        let mut sources = BTreeMap::new();
        let mut graphs = BTreeMap::new();
        let mut budget = MAX_INDEX_BYTES;
        for graph in &scope {
            let source = config.graphs.get(graph).ok_or_else(|| {
                reject(
                    "index_manifest",
                    "Missing provenance for an authorized graph",
                )
            })?;
            if [
                &source.source,
                &source.license,
                &source.source_revision,
                &source.importer_revision,
            ]
            .iter()
            .any(|s| s.trim().is_empty())
            {
                return Err(reject("index_manifest", "Incomplete source provenance"));
            }
            // Reuse graph-local roles and resource coverage; never merge roles across graphs.
            let catalog = self.catalog(std::slice::from_ref(graph), policy)?;
            if catalog.entries.is_empty() {
                return Err(reject(
                    "index_manifest",
                    "Requested named graph is absent or empty",
                ));
            }
            for iri in catalog.entries.keys() {
                reserve(&mut budget, 6 * iri.len() + 256)?;
            }
            sources.insert(graph.clone(), source.clone());
            graphs.insert(
                graph.clone(),
                GraphIndex {
                    documents: catalog
                        .entries
                        .into_iter()
                        .map(|(iri, entry)| {
                            (
                                iri,
                                Document {
                                    roles: entry.roles,
                                    texts: BTreeSet::new(),
                                    token_count: 0,
                                },
                            )
                        })
                        .collect(),
                    postings: BTreeMap::new(),
                    statistics: Statistics::default(),
                },
            );
        }
        for quad in self.store.iter() {
            let quad = quad.map_err(|e| Error::Store(e.to_string()))?;
            let Some(index) = graph_id(&quad.graph_name).and_then(|g| graphs.get_mut(g)) else {
                continue;
            };
            let (NamedOrBlankNode::NamedNode(subject), Term::Literal(literal)) =
                (&quad.subject, &quad.object)
            else {
                continue;
            };
            let Some(field) = field(quad.predicate.as_str()) else {
                continue;
            };
            if literal.language().is_some_and(|language| {
                !matches!(language.split('-').next(), Some("en" | "no" | "nb" | "nn"))
            }) {
                index.statistics.omitted_language_values += 1;
                continue;
            }
            let truncated =
                field == Field::Description && literal.value().chars().count() > DESCRIPTION_CHARS;
            let text = if field == Field::Description {
                literal.value().chars().take(DESCRIPTION_CHARS).collect()
            } else {
                literal.value().to_owned()
            };
            reserve(
                &mut budget,
                6 * (text.len() + quad.predicate.as_str().len()) + 512,
            )?;
            index.statistics.empty_values += usize::from(text.trim().is_empty());
            index.statistics.truncated_descriptions += usize::from(truncated);
            index
                .documents
                .get_mut(subject.as_str())
                .expect("catalog covers named subjects")
                .texts
                .insert(ObservedText {
                    field,
                    predicate: quad.predicate.as_str().into(),
                    value: Label {
                        text,
                        language: literal.language().map(str::to_owned),
                        datatype: literal.datatype().as_str().into(),
                    },
                    truncated,
                    via: None,
                });
        }
        // Both witnesses must be in this authorized graph; IRI spelling is never evidence.
        for quad in self.store.iter() {
            let quad = quad.map_err(|e| Error::Store(e.to_string()))?;
            let Some(index) = graph_id(&quad.graph_name).and_then(|g| graphs.get_mut(g)) else {
                continue;
            };
            let (NamedOrBlankNode::NamedNode(source), Term::NamedNode(target)) =
                (&quad.subject, &quad.object)
            else {
                continue;
            };
            if quad.predicate.as_str() != DIRECT_CLAIM
                || !index.documents[target.as_str()].roles.contains("predicate")
            {
                continue;
            }
            let mut texts = BTreeSet::new();
            for text in &index.documents[source.as_str()].texts {
                if text.via.is_none() && matches!(text.field, Field::Label | Field::Alias) {
                    reserve(
                        &mut budget,
                        6 * (text.value.text.len()
                            + text.predicate.len()
                            + source.as_str().len()
                            + DIRECT_CLAIM.len())
                            + 768,
                    )?;
                    let mut text = text.clone();
                    text.via = Some(PredicateMapping {
                        source_iri: source.as_str().into(),
                        predicate: DIRECT_CLAIM.into(),
                    });
                    texts.insert(text);
                }
            }
            index
                .documents
                .get_mut(target.as_str())
                .unwrap()
                .texts
                .extend(texts);
        }
        for index in graphs.values_mut() {
            for (iri, document) in &mut index.documents {
                for text in std::iter::once(iri.as_str())
                    .chain(document.texts.iter().map(|text| text.value.text.as_str()))
                {
                    for token in tokens(text) {
                        if index
                            .postings
                            .get(&token)
                            .is_none_or(|p| !p.contains_key(iri))
                        {
                            reserve(&mut budget, 6 * (iri.len() + token.len()) + 128)?;
                        }
                        *index
                            .postings
                            .entry(token)
                            .or_default()
                            .entry(iri.clone())
                            .or_default() += 1;
                        document.token_count += 1;
                    }
                }
                index.statistics.tokens += u64::from(document.token_count);
            }
            index.statistics.documents = index.documents.len();
            index.statistics.terms = index.postings.len();
        }
        let graph_hashes = graphs
            .iter()
            .map(|(graph, index)| Ok((graph.clone(), hash(index, "discovery-graph-v1")?)))
            .collect::<Result<_>>()?;
        let mut index = DiscoveryIndex {
            manifest: Manifest {
                version: 1,
                snapshot_id: self.id().into(),
                scope,
                policy_hash: hash(policy, "discovery-policy-v1")?,
                config_hash: hash(&sources, "discovery-config-v1")?,
                index_revision: snapshot_id(
                    concat!(
                        include_str!("discovery.rs"),
                        include_str!("catalog.rs"),
                        include_str!("lib.rs"),
                        include_str!("../../../Cargo.lock"),
                        include_str!("../../../rust-toolchain.toml")
                    )
                    .as_bytes(),
                    "discovery-source-v1",
                ),
                rules: RULES,
                sources,
                graph_hashes,
            },
            graphs,
            digest: String::new(),
        };
        index.digest = hash(&index, "discovery-index-v1")?;
        if serde_json::to_vec_pretty(&index)?.len() >= MAX_INDEX_BYTES {
            return Err(reject(
                "index_limit",
                "Discovery index exceeds 64 MiB; narrow scope",
            ));
        }
        Ok(index)
    }

    /// Rebuild before exposing persisted documents, postings or statistics. Also detects tampering.
    pub fn load_discovery(
        &self,
        bytes: &[u8],
        scope: &[String],
        policy: &Policy,
        config: &DiscoveryConfig,
    ) -> Result<DiscoveryIndex> {
        // shortcut: inspection rebuilds the bounded index; add verified caching when serving needs it.
        let expected = self.build_discovery(scope, policy, config)?;
        if bytes.len() > MAX_INDEX_BYTES {
            return Err(reject("index_limit", "Discovery index exceeds 64 MiB"));
        }
        let stored: serde_json::Value = serde_json::from_slice(bytes)?;
        if stored != serde_json::to_value(&expected)? {
            return Err(reject(
                "index_manifest",
                "Stale, incompatible or modified discovery index",
            ));
        }
        Ok(expected)
    }
}
