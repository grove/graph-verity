use serde_json::Value;
use verity_core::{
    catalog::Policy,
    discovery::{DiscoveryConfig, Source},
    navigation::{EdgeDirection, EntityRequest},
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
        max_evidence: 50,
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
fn request(s: &Snapshot, iri: &str) -> EntityRequest {
    EntityRequest {
        snapshot_id: s.id().into(),
        scope: vec![A.into()],
        iri: iri.into(),
        direction: EdgeDirection::Outgoing,
        offset: 0,
        limit: 50,
    }
}

#[test]
fn directed_pages_preserve_exact_witnesses_literals_and_linked_entities() {
    let (s, p, c) = fixture();
    let index = s.build_discovery(&[A.into(), B.into()], &p, &c).unwrap();
    let mut r = request(&s, "urn:discovery:shared");
    let all = serde_json::to_value(s.entity(&index, &r, &p).unwrap()).unwrap();
    assert_eq!(all["status"], "observed");
    assert_eq!(all["snapshot_id"], s.id());
    assert_eq!(all["real_world_truth"], "not_established");
    assert_eq!(all["interpretation_correctness"], "not_assessed");
    assert_eq!(all["evidence_verification"], "verified_against_snapshot");
    let edges = all["evidence"].as_array().unwrap();
    assert!(edges
        .iter()
        .all(|e| e["subject"]["value"] == r.iri && e["source_graph"]["value"] == A));
    assert!(edges.iter().any(|e| e["object"]["language"] == "nb"));
    assert!(edges.iter().any(|e| e["object"]["value"] == "42"
        && e["object"]["datatype"] == "http://www.w3.org/2001/XMLSchema#integer"));
    r.limit = 2;
    let mut paged = Vec::<Value>::new();
    loop {
        let page = serde_json::to_value(s.entity(&index, &r, &p).unwrap()).unwrap();
        let values = page["evidence"].as_array().unwrap();
        assert!(values.len() <= 2);
        paged.extend(values.iter().cloned());
        if let Some(next) = page["next_offset"].as_u64() {
            assert_eq!(page["truncated"], true);
            assert_eq!(next as usize, r.offset + values.len());
            r.offset = next as usize;
        } else {
            assert_eq!(page["truncated"], false);
            break;
        }
    }
    assert_eq!(&paged, edges);
    let link = edges
        .iter()
        .find(|e| e["predicate"]["value"] == "urn:discovery:link")
        .unwrap();
    let mut linked = request(&s, link["object"]["value"].as_str().unwrap());
    linked.direction = EdgeDirection::Incoming;
    let incoming = serde_json::to_value(s.entity(&index, &linked, &p).unwrap()).unwrap();
    assert_eq!(incoming["evidence"], serde_json::json!([link]));
    let outgoing = s
        .entity(&index, &request(&s, "urn:discovery:unlabelled"), &p)
        .unwrap();
    assert_eq!(outgoing.status, "no_relationships_on_page");
    assert!(outgoing.documents[A].texts.is_empty());
    let blank = s
        .entity(
            &index,
            &EntityRequest {
                direction: EdgeDirection::Incoming,
                ..request(&s, "urn:discovery:blankTarget")
            },
            &p,
        )
        .unwrap();
    assert!(serde_json::to_string(&blank.evidence)
        .unwrap()
        .contains("blank_node"));
}

#[test]
fn authorization_precedes_navigation_text_counts_and_provenance() {
    let (s, p, c) = fixture();
    let broad = s.build_discovery(&[A.into(), B.into()], &p, &c).unwrap();
    let narrow = s.build_discovery(&[A.into()], &p, &c).unwrap();
    for iri in [
        "urn:discovery:shared",
        "urn:discovery:PRIVATE_ID_CANARY",
        "urn:discovery:link",
        "urn:discovery:malicious",
    ] {
        for direction in [EdgeDirection::Incoming, EdgeDirection::Outgoing] {
            let r = EntityRequest {
                direction,
                ..request(&s, iri)
            };
            let result = serde_json::to_value(s.entity(&broad, &r, &p).unwrap()).unwrap();
            assert_eq!(
                result,
                serde_json::to_value(s.entity(&narrow, &r, &p).unwrap()).unwrap()
            );
            let text = result.to_string();
            for canary in ["PRIVATE_", "Only second graph", PRIVATE, B] {
                assert!(!text.contains(canary), "{text}");
            }
            if iri.contains("PRIVATE_") {
                assert_eq!(result["status"], "no_match");
                assert!(result["iri"].is_null());
            }
        }
    }
    let both = s
        .entity(
            &broad,
            &EntityRequest {
                scope: vec![A.into(), B.into()],
                ..request(&s, "urn:discovery:shared")
            },
            &p,
        )
        .unwrap();
    assert_eq!(both.documents.len(), 2);
    assert!(both.documents[B]
        .texts
        .iter()
        .any(|t| t.value.text == "Only second graph"));
    assert!(!both.documents[A]
        .texts
        .iter()
        .any(|t| t.value.text == "Only second graph"));
    for scope in [
        vec![],
        vec![PRIVATE.into()],
        vec![A.into(), PRIVATE.into()],
        vec![A.into(), A.into()],
    ] {
        let error = s
            .entity(
                &broad,
                &EntityRequest {
                    scope,
                    ..request(&s, "urn:discovery:PRIVATE_ID_CANARY")
                },
                &p,
            )
            .unwrap_err()
            .to_string();
        assert!(error.starts_with("scope:"));
        assert!(!error.contains("PRIVATE"));
    }
}

#[test]
fn incompatible_snapshots_indexes_and_unbounded_or_invalid_requests_fail_closed() {
    let error = Snapshot::from_bytes(
        b"<urn:public> <urn:p> <urn:o> <urn:g> .\nPRIVATE_TEXT_CANARY:PRIVATE_ID_CANARY",
        "nquads",
    )
    .err()
    .unwrap()
    .to_string();
    assert!(!error.contains("PRIVATE_"));
    let (s, p, c) = fixture();
    let index = s.build_discovery(&[A.into()], &p, &c).unwrap();
    let other =
        Snapshot::from_bytes(b"<urn:x> <urn:p> <urn:y> <urn:discovery:a> .", "nquads").unwrap();
    assert!(other
        .entity(&index, &request(&other, "urn:x"), &p)
        .unwrap_err()
        .to_string()
        .starts_with("snapshot:"));
    let mut changed = p.clone();
    changed.timeout_ms += 1;
    assert!(s
        .entity(&index, &request(&s, "urn:discovery:shared"), &changed)
        .is_err());
    for r in [
        EntityRequest {
            snapshot_id: "other".into(),
            ..request(&s, "urn:x")
        },
        EntityRequest {
            scope: vec![B.into()],
            ..request(&s, "urn:x")
        },
        EntityRequest {
            limit: 0,
            ..request(&s, "urn:x")
        },
        EntityRequest {
            limit: 51,
            ..request(&s, "urn:x")
        },
        EntityRequest {
            offset: 100_001,
            ..request(&s, "urn:x")
        },
        request(&s, "<urn:x> SERVICE <https://invalid.example/>"),
        request(&s, &format!("urn:{}", "x".repeat(2049))),
    ] {
        assert!(s.entity(&index, &r, &p).is_err());
    }
    let mut limited = p.clone();
    limited.max_evidence = 1;
    let index = s.build_discovery(&[A.into()], &limited, &c).unwrap();
    assert!(s.entity(&index, &request(&s, "urn:x"), &limited).is_err());
    let page = s
        .entity(
            &index,
            &EntityRequest {
                offset: 100_000,
                limit: 1,
                ..request(&s, "urn:discovery:shared")
            },
            &limited,
        )
        .unwrap();
    assert!(page.evidence.is_empty());
    assert!(page.next_offset.is_none());
    let mut raw = serde_json::json!({"snapshot_id":s.id(), "scope":[A], "iri":"urn:x", "direction":"outgoing", "offset":0, "limit":1});
    raw["sparql"] = "SELECT * WHERE {}".into();
    assert!(serde_json::from_value::<EntityRequest>(raw).is_err());
}

#[test]
fn oversized_entity_evidence_fails_without_echoing_literal_text() {
    let rdf = format!("<urn:x> <urn:p> \"{}\" <{A}> .", "CANARY".repeat(1_500_000));
    let s = Snapshot::from_bytes(rdf.as_bytes(), "nquads").unwrap();
    let (_, p, mut c) = fixture();
    c.snapshot_id = s.id().into();
    let index = s.build_discovery(&[A.into()], &p, &c).unwrap();
    let error = s
        .entity(&index, &request(&s, "urn:x"), &p)
        .unwrap_err()
        .to_string();
    assert!(error.starts_with("output_limit:"));
    assert!(!error.contains("CANARY"));
}
