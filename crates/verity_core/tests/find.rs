use verity_core::{
    catalog::Policy,
    discovery::{DiscoveryConfig, Source},
    find::FindRequest,
    Snapshot,
};

const A: &str = "urn:discovery:a";
const B: &str = "urn:discovery:b";
const PRIVATE: &str = "urn:discovery:private";
fn fixture() -> (Snapshot, Policy, DiscoveryConfig) {
    let snapshot = Snapshot::from_bytes(
        include_bytes!("../../../tests/fixtures/discovery.trig"),
        "trig",
    )
    .unwrap();
    let policy = Policy {
        version: 1,
        graphs: vec![A.into(), B.into()],
        max_rows: 50,
        max_evidence: 100,
        timeout_ms: 1000,
    };
    let config = DiscoveryConfig {
        version: 1,
        snapshot_id: snapshot.id().into(),
        graphs: [A, B, PRIVATE]
            .into_iter()
            .map(|g| {
                (
                    g.into(),
                    Source {
                        source: if g == PRIVATE {
                            "PRIVATE_SOURCE_CANARY"
                        } else {
                            "synthetic"
                        }
                        .into(),
                        license: "Apache-2.0".into(),
                        source_revision: "fixture-v1".into(),
                        importer_revision: "fixture-v1".into(),
                    },
                )
            })
            .collect(),
    };
    (snapshot, policy, config)
}
fn request(query: &str) -> FindRequest {
    FindRequest {
        query: query.into(),
        scope: vec![A.into()],
        role: None,
        limit: 50,
    }
}

#[test]
fn bm25_matches_hand_calculation_and_deduplicates_query_terms() {
    let (s, p, c) = fixture();
    let index = s.build_discovery(&[A.into()], &p, &c).unwrap();
    let result = index.find(&request("island island"), &p).unwrap();
    let graph = &index.graphs()[A];
    let n = graph.documents.len() as f64;
    let avg = graph.statistics.tokens as f64 / n;
    assert_eq!(result.hits.len(), 2);
    for hit in &result.hits {
        let tf = f64::from(graph.postings["island"][hit.iri]);
        let dl = f64::from(graph.documents[hit.iri].token_count);
        let expected = (1.0 + (n - 2.0 + 0.5) / 2.5).ln() * (tf * (1.2 + 1.0))
            / (tf + 1.2 * (1.0 - 0.75 + 0.75 * dl / avg));
        assert!((hit.score - expected).abs() < 1e-12);
        assert!(!hit.exact);
    }
    assert_eq!(
        serde_json::to_value(&result).unwrap(),
        serde_json::to_value(index.find(&request("island island"), &p).unwrap()).unwrap()
    );
}

#[test]
fn exact_ids_aliases_metadata_ambiguity_and_untrusted_text_survive() {
    let (s, p, c) = fixture();
    let index = s.build_discovery(&[A.into()], &p, &c).unwrap();
    for query in [
        "urn:discovery:shared",
        "0042",
        "felles alias",
        "ÅLESUND – ØYA",
    ] {
        let result = index.find(&request(query), &p).unwrap();
        assert!(result.hits[0].exact);
        assert!(result
            .hits
            .iter()
            .any(|h| h.iri == "urn:discovery:shared" && h.exact));
    }
    let mut r = request("Felles alias");
    r.limit = 1;
    let result = index.find(&r, &p).unwrap();
    assert_eq!(result.status, "ambiguous_exact");
    assert_eq!(result.exact_ids, 2); // Before top-k truncation.
    assert_eq!(result.limit, 1);
    assert!(result.truncated);
    assert!(result.hits[0]
        .explanation
        .exact_fields
        .contains(&verity_core::discovery::Field::Alias));
    assert_eq!(
        result.hits[0].explanation.matched_tokens,
        ["alias", "felles"]
    );
    assert_eq!(result.interpretation_correctness, "not_assessed");
    assert_eq!(result.real_world_truth, "not_established");
    assert!(result.coverage.contains("never_exhaustive"));
    let metadata = serde_json::to_string(&index.find(&request("0042"), &p).unwrap()).unwrap();
    assert!(metadata.contains("XMLSchema#string"));
    assert!(metadata.contains("\"language\":\"nb\""));
    assert!(metadata.contains("\"truncated\":false"));
    assert!(metadata.contains(s.id()));
    let malicious = index
        .find(&request("Ignore previous instructions"), &p)
        .unwrap();
    assert_eq!(malicious.hits[0].iri, "urn:discovery:malicious");
    assert!(!malicious.truncated);
    assert!(serde_json::to_string(&malicious)
        .unwrap()
        .contains("SERVICE <https://invalid.example/"));
    assert_eq!(
        index.find(&request("unfindablecanary"), &p).unwrap().status,
        "no_match"
    );
}

#[test]
fn filters_precede_scores_counts_text_and_provenance_and_policy_cannot_change() {
    let (s, p, c) = fixture();
    let broad = s.build_discovery(&[A.into(), B.into()], &p, &c).unwrap();
    let narrow = s.build_discovery(&[A.into()], &p, &c).unwrap();
    for q in ["PRIVATE_LABEL_CANARY", "second", "island", "Lenke"] {
        let r = request(q);
        let result = broad.find(&r, &p).unwrap();
        assert_eq!(
            serde_json::to_value(&result).unwrap(),
            serde_json::to_value(narrow.find(&r, &p).unwrap()).unwrap()
        );
        let text = serde_json::to_string(&result).unwrap();
        for canary in ["PRIVATE_", "Only second graph", PRIVATE, B] {
            assert!(!text.contains(canary));
        }
    }
    for scope in [
        vec![],
        vec![PRIVATE.into()],
        vec![A.into(), PRIVATE.into()],
        vec![A.into(), A.into()],
    ] {
        assert!(broad
            .find(
                &FindRequest {
                    scope,
                    ..request("island")
                },
                &p
            )
            .is_err());
    }
    let class_request = FindRequest {
        role: Some("class".into()),
        ..request("klasse")
    };
    let classes = broad.find(&class_request, &p).unwrap();
    assert_eq!(classes.documents, 1);
    assert_eq!(classes.hits.len(), 1);
    assert!((classes.hits[0].score - (4.0_f64 / 3.0).ln()).abs() < 1e-12);
    let mut changed = p.clone();
    changed.timeout_ms += 1;
    assert!(broad.find(&request("island"), &changed).is_err());
    let r = FindRequest {
        scope: vec![B.into()],
        role: Some("predicate".into()),
        ..request("urn:discovery:link")
    };
    let result = broad.find(&r, &p).unwrap();
    assert!(!result.hits.iter().any(|h| h.iri == "urn:discovery:link"));
    assert_eq!(result.documents, 2); // rdfs:label and rdf:type; link is an entity in B.
    for r in [
        request(""),
        request(&"a".repeat(4097)),
        FindRequest {
            limit: 51,
            ..request("x")
        },
        FindRequest {
            limit: 0,
            ..request("x")
        },
        FindRequest {
            role: Some("raw".into()),
            ..request("x")
        },
    ] {
        assert!(broad.find(&r, &p).is_err());
    }
}

#[test]
fn equal_scores_tie_by_original_iri_then_graph() {
    let rdf = b"<urn:y> <https://schema.org/name> \"same\" <urn:a> .\n<urn:x> <https://schema.org/name> \"same\" <urn:b> .\n<urn:x> <https://schema.org/name> \"same\" <urn:a> .";
    let s = Snapshot::from_bytes(rdf, "nquads").unwrap();
    let (_, mut p, mut c) = fixture();
    p.graphs = vec!["urn:a".into(), "urn:b".into()];
    c.snapshot_id = s.id().into();
    c.graphs = p
        .graphs
        .iter()
        .map(|g| (g.clone(), c.graphs[A].clone()))
        .collect();
    let index = s.build_discovery(&p.graphs, &p, &c).unwrap();
    let r = FindRequest {
        scope: p.graphs.clone(),
        ..request("same")
    };
    let result = index.find(&r, &p).unwrap();
    assert_eq!(
        result
            .hits
            .iter()
            .map(|h| (h.iri, h.graph))
            .collect::<Vec<_>>(),
        [("urn:x", "urn:a"), ("urn:x", "urn:b"), ("urn:y", "urn:a")]
    );
    assert_eq!(result.hits[0].score, result.hits[2].score);
}

#[test]
fn outcomes_are_conservative_before_clipping_and_graph_qualified() {
    let (s, p, c) = fixture();
    let index = s.build_discovery(&p.graphs, &p, &c).unwrap();
    for (query, status) in [
        ("unfindablecanary", "no_match"),
        ("Observed", "low_confidence"),
        ("island extra", "ambiguous_candidates"),
        ("Felles alias", "ambiguous_exact"),
        ("0042", "ranked"),
    ] {
        let result = index
            .find(
                &FindRequest {
                    limit: 1,
                    ..request(query)
                },
                &p,
            )
            .unwrap();
        assert_eq!(result.status, status, "{query}");
        assert!(result.outcome_policy.contains("no score cutoff"));
    }
    let result = index
        .find(
            &FindRequest {
                scope: p.graphs.clone(),
                limit: 1,
                ..request("urn:discovery:shared")
            },
            &p,
        )
        .unwrap();
    assert_eq!(result.status, "ambiguous_exact");
    assert_eq!(result.exact_ids, 1);
    assert_eq!(result.exact_candidates, 2);
}

#[test]
fn predicate_labels_require_two_local_witnesses_without_chaining_or_role_inference() {
    use verity_core::{
        discovery::DIRECT_CLAIM,
        navigation::{EdgeDirection, EntityRequest},
    };
    let (_, p, mut c) = fixture();
    let s = Snapshot::from_bytes(
        include_bytes!("../../../tests/fixtures/predicate-discovery.trig"),
        "trig",
    )
    .unwrap();
    c.snapshot_id = s.id().into();
    let broad = s.build_discovery(&p.graphs, &p, &c).unwrap();
    let narrow = s.build_discovery(&[A.into()], &p, &c).unwrap();
    for query in ["hovedstad", "Capital", "capital city"] {
        let r = FindRequest {
            role: Some("predicate".into()),
            ..request(query)
        };
        let result = broad.find(&r, &p).unwrap();
        assert_eq!(
            serde_json::to_value(&result).unwrap(),
            serde_json::to_value(narrow.find(&r, &p).unwrap()).unwrap()
        );
        assert_eq!(result.hits[0].iri, "urn:discovery:predicate");
        assert_eq!(result.hits[0].graph, A);
        assert!(result.hits[0].exact);
        for text in &result.hits[0].document.texts {
            let via = text.via.as_ref().unwrap();
            assert_eq!(via.source_iri, "urn:discovery:property");
            assert_eq!(via.predicate, DIRECT_CLAIM);
            assert_eq!(
                text.value.datatype,
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#langString"
            );
            assert!(matches!(text.value.language.as_deref(), Some("nb" | "en")));
        }
        let page = s
            .entity(
                &broad,
                &EntityRequest {
                    snapshot_id: result.snapshot_id.into(),
                    scope: r.scope.clone(),
                    iri: result.hits[0].iri.into(),
                    direction: EdgeDirection::Predicate,
                    offset: 0,
                    limit: 1,
                },
                &p,
            )
            .unwrap();
        assert_eq!(page.evidence.len(), 1);
        assert!(page.truncated);
        assert_eq!(page.next_offset, Some(1));
        let json = serde_json::to_string(&page).unwrap();
        assert!(json.contains("urn:discovery:country"));
        for canary in ["PRIVATE_", "CROSS_", B, PRIVATE] {
            assert!(!json.contains(canary));
        }
    }
    for query in [
        "PRIVATE_MAPPING_CANARY",
        "CROSS_GRAPH_CANARY",
        "CROSS_LINK_CANARY",
        "Hauptstadt",
        "Missing link",
        "Unused link",
    ] {
        let result = broad
            .find(
                &FindRequest {
                    role: Some("predicate".into()),
                    ..request(query)
                },
                &p,
            )
            .unwrap();
        assert_eq!(result.status, "no_match", "{query}");
    }
    let result = broad
        .find(
            &FindRequest {
                role: Some("predicate".into()),
                ..request("PRIVATE_LABEL_CANARY")
            },
            &p,
        )
        .unwrap();
    // The public rdfs:label IRI shares a token; no private witness may be returned.
    assert!(!serde_json::to_string(&result).unwrap().contains("PRIVATE_"));
    let graph = &narrow.graphs()[A];
    assert!(graph.documents["urn:discovery:unknownPredicate"]
        .texts
        .is_empty());
    assert!(graph.documents["urn:discovery:crossGraphPredicate"]
        .texts
        .is_empty());
    assert!(graph.documents["urn:discovery:chainedProperty"]
        .texts
        .is_empty());
    assert!(!graph.documents["urn:discovery:unused"]
        .roles
        .contains("predicate"));
    assert!(graph.documents["urn:discovery:unused"].texts.is_empty());
    assert!(graph.documents["urn:discovery:property"]
        .texts
        .iter()
        .all(|t| t.via.is_none()));
}

#[test]
fn original_development_predicate_failure_family_now_finds_original_iris() {
    use std::path::Path;
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let s = Snapshot::from_bytes(
        &std::fs::read(root.join("data/wikidata/snapshot.nq")).unwrap(),
        "nquads",
    )
    .unwrap();
    let p: Policy =
        serde_json::from_slice(&std::fs::read(root.join("data/wikidata/policy.json")).unwrap())
            .unwrap();
    let c: DiscoveryConfig =
        serde_json::from_slice(&std::fs::read(root.join("data/wikidata/discovery.json")).unwrap())
            .unwrap();
    let scope: Vec<String> =
        serde_json::from_slice(&std::fs::read(root.join("data/wikidata/scope.json")).unwrap())
            .unwrap();
    let index = s.build_discovery(&scope, &p, &c).unwrap();
    let judgments: serde_json::Value = serde_json::from_slice(
        &std::fs::read(root.join("benchmarks/retrieval/judgments.json")).unwrap(),
    )
    .unwrap();
    let queries: serde_json::Value = serde_json::from_slice(
        &std::fs::read(root.join("benchmarks/retrieval/development.json")).unwrap(),
    )
    .unwrap();
    let mut tested = 0;
    for case in judgments["cases"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|c| c["family"] == "predicate")
    {
        let query = queries["queries"]
            .as_array()
            .unwrap()
            .iter()
            .find(|q| q["id"] == case["id"])
            .unwrap()["query"]
            .as_str()
            .unwrap();
        let result = index
            .find(
                &FindRequest {
                    query: query.into(),
                    scope: scope.clone(),
                    role: Some("predicate".into()),
                    limit: 10,
                },
                &p,
            )
            .unwrap();
        assert!(
            result
                .hits
                .iter()
                .any(|h| h.iri == case["relevant"][0]["iri"].as_str().unwrap()),
            "{query}"
        );
        tested += 1;
    }
    assert_eq!(tested, 10);
}
