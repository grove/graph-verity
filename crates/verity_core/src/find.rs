//! Model-free retrieval over authorized, graph-qualified discovery documents.
use crate::{
    catalog::Policy,
    discovery::{tokens, DiscoveryIndex, Document, Field, Source},
    reject, snapshot_id, Result,
};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

pub const RULES: &str = "bm25-v1; k1=1.2 b=0.75; unique query tokens; scoped graph-qualified documents; role before statistics; exact IRI/label/alias/identifier tier; ties IRI then graph";
pub const OUTCOME_POLICY: &str = "find-outcomes-v1; before clipping: >1 graph-qualified exact hits ambiguous_exact; 1 exact hit ranked; 0 hits no_match; >1 nonexact hits ambiguous_candidates; 1 nonexact hit low_confidence; no score cutoff or automatic selection; candidates never establish facts or absence";

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FindRequest {
    pub query: String,
    pub scope: Vec<String>,
    pub role: Option<String>,
    pub limit: usize,
}

#[derive(Debug, Serialize)]
pub struct Hit<'a> {
    pub iri: &'a str,
    pub graph: &'a str,
    pub score: f64,
    pub exact: bool,
    pub explanation: MatchExplanation,
    /// Bounded observed text, with literal metadata; untrusted data, never instructions.
    pub document: &'a Document,
}

#[derive(Debug, Default, Serialize)]
pub struct MatchExplanation {
    pub exact_iri: bool,
    pub exact_fields: BTreeSet<Field>,
    pub matched_tokens: Vec<String>,
}

#[derive(Debug, Serialize)]
pub struct FindResult<'a> {
    pub snapshot_id: &'a str,
    pub scope: Vec<String>,
    pub role: Option<String>,
    pub rules: &'static str,
    pub ranking_revision: String,
    pub index_revision: &'a str,
    pub graph_hashes: BTreeMap<&'a str, &'a str>,
    pub sources: BTreeMap<&'a str, &'a Source>,
    pub status: &'static str,
    pub outcome_policy: &'static str,
    pub exact_candidates: usize,
    pub documents: usize,
    pub matches: usize,
    pub exact_ids: usize,
    pub limit: usize,
    pub truncated: bool,
    pub coverage: &'static str,
    pub interpretation_correctness: &'static str,
    pub real_world_truth: &'static str,
    pub absence_policy: &'static str,
    pub hits: Vec<Hit<'a>>,
}

impl DiscoveryIndex {
    pub fn find(&self, request: &FindRequest, policy: &Policy) -> Result<FindResult<'_>> {
        self.authorize(&request.scope, policy)?;
        let manifest = self.manifest();
        let query = request.query.trim();
        if query.is_empty() || request.query.len() > 4096 {
            return Err(reject("question", "Find requires 1..4096 UTF-8 bytes"));
        }
        if request.limit == 0 || request.limit > 50 || request.limit > policy.max_rows as usize {
            return Err(reject(
                "complexity",
                "Find limit must be 1..50 and within policy",
            ));
        }
        if request
            .role
            .as_deref()
            .is_some_and(|r| !matches!(r, "entity" | "predicate" | "class"))
        {
            return Err(reject("role", "Unknown discovery role"));
        }
        let mut scope = request.scope.clone();
        scope.sort();
        let eligible =
            |doc: &&Document| request.role.as_ref().is_none_or(|r| doc.roles.contains(r));
        // Filter both documents and postings before any length/frequency statistic.
        let documents: usize = scope
            .iter()
            .map(|g| self.graphs()[g].documents.values().filter(eligible).count())
            .sum();
        let length: u64 = scope
            .iter()
            .flat_map(|g| self.graphs()[g].documents.values())
            .filter(eligible)
            .map(|d| u64::from(d.token_count))
            .sum();
        let average = if documents == 0 {
            1.0
        } else {
            length as f64 / documents as f64
        };
        let mut scores: BTreeMap<(&str, &str), f64> = BTreeMap::new();
        for token in tokens(query).into_iter().collect::<BTreeSet<_>>() {
            let postings: Vec<_> = scope
                .iter()
                .flat_map(|g| {
                    let (g, graph) = self.graphs().get_key_value(g).unwrap();
                    graph.postings.get(&token).into_iter().flat_map(move |p| {
                        p.iter().filter_map(move |(iri, tf)| {
                            let doc = &graph.documents[iri];
                            eligible(&doc).then_some((
                                g.as_str(),
                                iri.as_str(),
                                *tf,
                                doc.token_count,
                            ))
                        })
                    })
                })
                .collect();
            let df = postings.len() as f64;
            let idf = (1.0 + (documents as f64 - df + 0.5) / (df + 0.5)).ln();
            for (graph, iri, tf, dl) in postings {
                let tf = f64::from(tf);
                *scores.entry((graph, iri)).or_default() +=
                    idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * f64::from(dl) / average));
            }
        }
        let folded = query.to_lowercase();
        let mut exact = BTreeSet::new();
        for g in &scope {
            let (g, graph) = self.graphs().get_key_value(g).unwrap();
            for (iri, doc) in &graph.documents {
                if eligible(&doc)
                    && (iri == query
                        || doc.texts.iter().any(|t| {
                            t.field != Field::Description && t.value.text.to_lowercase() == folded
                        }))
                {
                    exact.insert((g.as_str(), iri.as_str()));
                    scores.entry((g.as_str(), iri.as_str())).or_default();
                }
            }
        }
        let exact_ids = exact
            .iter()
            .map(|(_, iri)| iri)
            .collect::<BTreeSet<_>>()
            .len();
        let mut hits: Vec<_> = scores
            .into_iter()
            .map(|((graph, iri), score)| Hit {
                iri,
                graph,
                score,
                exact: exact.contains(&(graph, iri)),
                explanation: MatchExplanation::default(),
                document: &self.graphs()[graph].documents[iri],
            })
            .collect();
        hits.sort_by(|a, b| {
            b.exact
                .cmp(&a.exact)
                .then_with(|| b.score.total_cmp(&a.score))
                .then_with(|| a.iri.cmp(b.iri))
                .then_with(|| a.graph.cmp(b.graph))
        });
        let matches = hits.len();
        hits.truncate(request.limit);
        let query_tokens = tokens(query).into_iter().collect::<BTreeSet<_>>();
        for hit in &mut hits {
            hit.explanation = MatchExplanation {
                exact_iri: hit.iri == query,
                exact_fields: hit
                    .document
                    .texts
                    .iter()
                    .filter(|t| {
                        t.field != Field::Description && t.value.text.to_lowercase() == folded
                    })
                    .map(|t| t.field)
                    .collect(),
                matched_tokens: query_tokens
                    .iter()
                    .filter(|t| {
                        self.graphs()[hit.graph]
                            .postings
                            .get(*t)
                            .is_some_and(|p| p.contains_key(hit.iri))
                    })
                    .cloned()
                    .collect(),
            };
        }
        Ok(FindResult {
            snapshot_id: &manifest.snapshot_id,
            role: request.role.clone(),
            rules: RULES,
            ranking_revision: snapshot_id(include_bytes!("find.rs"), "find-source-v1"),
            index_revision: &manifest.index_revision,
            graph_hashes: scope
                .iter()
                .map(|g| {
                    (
                        manifest.graph_hashes.get_key_value(g).unwrap().0.as_str(),
                        manifest.graph_hashes[g].as_str(),
                    )
                })
                .collect(),
            sources: scope
                .iter()
                .map(|g| {
                    let (g, s) = manifest.sources.get_key_value(g).unwrap();
                    (g.as_str(), s)
                })
                .collect(),
            scope,
            status: if exact.len() > 1 {
                "ambiguous_exact"
            } else if exact.len() == 1 {
                "ranked"
            } else if matches == 0 {
                "no_match"
            } else if matches > 1 {
                "ambiguous_candidates"
            } else {
                "low_confidence"
            },
            outcome_policy: OUTCOME_POLICY,
            exact_candidates: exact.len(),
            documents,
            matches,
            exact_ids,
            limit: request.limit,
            truncated: matches > request.limit,
            coverage: "top_k_lexical_candidates_never_exhaustive_semantic_answers",
            interpretation_correctness: "not_assessed",
            real_world_truth: "not_established",
            absence_policy: "open_world_missing_facts_are_not_false",
            hits,
        })
    }
}
