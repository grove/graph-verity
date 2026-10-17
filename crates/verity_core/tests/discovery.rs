use serde_json::json;
use sha2::{Digest, Sha256};
use std::path::Path;
use verity_core::{
    catalog::Policy,
    discovery::{tokens, DiscoveryConfig, Field, Source},
    Snapshot,
};

const RDF: &[u8] = include_bytes!("../../../tests/fixtures/discovery.trig");
const A: &str = "urn:discovery:a";
const B: &str = "urn:discovery:b";
const PRIVATE: &str = "urn:discovery:private";
const SHARED: &str = "urn:discovery:shared";

fn policy() -> Policy {
    Policy {
        version: 1,
        graphs: vec![A.into(), B.into()],
        max_rows: 100,
        max_evidence: 100,
        timeout_ms: 1000,
    }
}

fn config(snapshot: &Snapshot) -> DiscoveryConfig {
    DiscoveryConfig {
        version: 1,
        snapshot_id: snapshot.id().into(),
        graphs: [A, B, PRIVATE]
            .into_iter()
            .map(|graph| {
                (
                    graph.into(),
                    Source {
                        source: if graph == PRIVATE {
                            "PRIVATE_SOURCE_CANARY"
                        } else {
                            "Apache-2.0 synthetic fixture"
                        }
                        .into(),
                        license: "Apache-2.0".into(),
                        source_revision: "fixture-v1".into(),
                        importer_revision: "handwritten-fixture-v1".into(),
                    },
                )
            })
            .collect(),
    }
}

fn serialized(value: &impl serde::Serialize) -> Vec<u8> {
    serde_json::to_vec_pretty(value).unwrap()
}

#[test]
fn graph_local_coverage_postings_and_provenance_are_reproducible() {
    let snapshot = Snapshot::from_bytes(RDF, "trig").unwrap();
    let scope = vec![B.into(), A.into()];
    let index = snapshot
        .build_discovery(&scope, &policy(), &config(&snapshot))
        .unwrap();
    let bytes = serialized(&index);
    let second_snapshot = Snapshot::from_bytes(RDF, "trig").unwrap();
    assert_eq!(
        bytes,
        serialized(
            &second_snapshot
                .build_discovery(&[A.into(), B.into()], &policy(), &config(&second_snapshot))
                .unwrap()
        )
    );
    assert_eq!(index.manifest().scope, [A, B]);
    assert_eq!(index.manifest().snapshot_id, snapshot.id());
    assert_eq!(index.manifest().sources.len(), 2);
    assert_eq!(index.manifest().graph_hashes.len(), 2);
    for (graph, data) in index.graphs() {
        let catalog = snapshot
            .catalog(std::slice::from_ref(graph), &policy())
            .unwrap();
        assert_eq!(
            data.documents.keys().collect::<Vec<_>>(),
            catalog.entries.keys().collect::<Vec<_>>()
        );
        for (iri, doc) in &data.documents {
            assert_eq!(doc.roles, catalog.entries[iri].roles);
            let postings_count: u32 = data
                .postings
                .values()
                .filter_map(|posting| posting.get(iri))
                .sum();
            assert_eq!(doc.token_count, postings_count);
        }
        assert_eq!(data.statistics.documents, data.documents.len());
        assert_eq!(data.statistics.terms, data.postings.len());
        assert_eq!(
            data.statistics.tokens,
            data.documents
                .values()
                .map(|d| u64::from(d.token_count))
                .sum::<u64>()
        );
    }
    let a = &index.graphs()[A];
    let b = &index.graphs()[B];
    assert!(a.documents["urn:discovery:unlabelled"].texts.is_empty());
    assert!(a.documents.contains_key("urn:discovery:blankTarget"));
    assert!(a.documents["urn:discovery:Class"].roles.contains("class"));
    assert!(a.documents["urn:discovery:link"]
        .roles
        .contains("predicate"));
    assert!(!b.documents["urn:discovery:link"]
        .roles
        .contains("predicate"));
    assert!(!a.postings.contains_key("second"));
    assert!(b.postings["second"].contains_key(SHARED));
    assert!(a.postings["0042"].contains_key(SHARED));
    assert!(a.postings["shared"].contains_key(SHARED));
    assert!(a.postings["øya"].contains_key(SHARED));
    assert_eq!(a.statistics.omitted_language_values, 1);
    assert_eq!(a.statistics.empty_values, 1);
    let texts = &a.documents[SHARED].texts;
    assert!(texts
        .iter()
        .any(|t| t.value.language.as_deref() == Some("nn")));
    assert!(texts
        .iter()
        .any(|t| t.value.language.as_deref() == Some("en-gb")));
    assert!(texts
        .iter()
        .any(|t| t.field == Field::Label && t.value.text.is_empty()));
    let identifier = texts.iter().find(|t| t.field == Field::Identifier).unwrap();
    assert_eq!(identifier.value.text, "0042");
    assert_eq!(
        identifier.value.datatype,
        "http://www.w3.org/2001/XMLSchema#string"
    );
    assert!(texts.iter().any(|t| t.field == Field::Identifier
        && t.value.datatype == "http://www.w3.org/2001/XMLSchema#integer"
        && t.value.text == "42"));
    // Same label/alias gives several original IRIs, with no identity merging.
    assert_eq!(
        a.postings["felles"].keys().cloned().collect::<Vec<_>>(),
        ["urn:discovery:other", SHARED]
    );
    assert!(a.postings["island"].contains_key("urn:discovery:other"));
    assert_eq!(a.postings["island"][SHARED], 2);
    assert_eq!(a.postings["island"].len(), 2);
    assert!(String::from_utf8(bytes.clone())
        .unwrap()
        .contains("<script>"));
    assert_eq!(
        bytes,
        serialized(
            &snapshot
                .load_discovery(&bytes, &scope, &policy(), &config(&snapshot))
                .unwrap()
        )
    );
}

#[test]
fn unauthorized_text_ids_sources_and_counts_never_enter_index() {
    let snapshot = Snapshot::from_bytes(RDF, "trig").unwrap();
    let index = snapshot
        .build_discovery(&[A.into()], &policy(), &config(&snapshot))
        .unwrap();
    let bytes = serialized(&index);
    let text = String::from_utf8(bytes).unwrap();
    for canary in [
        "PRIVATE_",
        PRIVATE,
        "\"urn:discovery:b\"",
        "Only second graph",
    ] {
        assert!(!text.contains(canary), "leaked {canary}");
    }
    for scope in [
        vec![PRIVATE.into()],
        vec![A.into(), PRIVATE.into()],
        vec![],
        vec![A.into(), A.into()],
    ] {
        assert!(snapshot
            .build_discovery(&scope, &policy(), &config(&snapshot))
            .is_err());
    }
    let more_private = [
        RDF,
        b"\n<urn:discovery:private> { <urn:private:new> <urn:private:p> \"extra private text\" . }",
    ]
    .concat();
    let changed = Snapshot::from_bytes(&more_private, "trig").unwrap();
    let changed_index = changed
        .build_discovery(&[A.into()], &policy(), &config(&changed))
        .unwrap();
    assert_eq!(
        serialized(index.graphs()),
        serialized(changed_index.graphs())
    );
    assert_eq!(
        index.manifest().graph_hashes,
        changed_index.manifest().graph_hashes
    );
}

#[test]
fn description_limits_and_unicode_rules_do_not_rewrite_rdf_identity() {
    assert_eq!(
        tokens("ÅLESUND Øya blåbær 東京 0042"),
        ["ålesund", "øya", "blåbær", "東京", "0042"]
    );
    assert_eq!(tokens("---\n  "), Vec::<String>::new());
    assert_ne!(tokens("é"), tokens("e\u{301}")); // Explicitly no NFC normalization.
    let description = format!("{}TAIL_CANARY", "ø".repeat(512));
    let rdf = format!("<urn:s> <https://schema.org/description> \"{description}\"@nb <{A}> .");
    let snapshot = Snapshot::from_bytes(rdf.as_bytes(), "nquads").unwrap();
    let index = snapshot
        .build_discovery(&[A.into()], &policy(), &config(&snapshot))
        .unwrap();
    let data = &index.graphs()[A];
    let text = data.documents["urn:s"].texts.first().unwrap();
    assert_eq!(text.value.text.chars().count(), 512);
    assert!(text.truncated);
    assert_eq!(text.value.language.as_deref(), Some("nb"));
    assert_eq!(data.statistics.truncated_descriptions, 1);
    assert!(!String::from_utf8(serialized(&index))
        .unwrap()
        .contains("TAIL_CANARY"));
}

#[test]
fn oversized_posting_expansion_fails_with_an_explicit_limit() {
    let iri = format!("urn:{}", "x".repeat(4096));
    let label = (0..3000)
        .map(|i| format!("token{i}"))
        .collect::<Vec<_>>()
        .join(" ");
    let rdf = format!("<{iri}> <https://schema.org/name> \"{label}\" <{A}> .");
    let snapshot = Snapshot::from_bytes(rdf.as_bytes(), "nquads").unwrap();
    let error = snapshot
        .build_discovery(&[A.into()], &policy(), &config(&snapshot))
        .unwrap_err();
    assert!(error.to_string().starts_with("index_limit:"));
}

#[test]
fn incompatible_or_tampered_persisted_indexes_fail_closed() {
    let snapshot = Snapshot::from_bytes(RDF, "trig").unwrap();
    let scope = vec![A.into(), B.into()];
    let config = config(&snapshot);
    let index = snapshot
        .build_discovery(&scope, &policy(), &config)
        .unwrap();
    let bytes = serialized(&index);
    let value = serde_json::to_value(&index).unwrap();
    for pointer in [
        "/manifest/version",
        "/manifest/snapshot_id",
        "/manifest/scope",
        "/manifest/policy_hash",
        "/manifest/config_hash",
        "/manifest/index_revision",
        "/manifest/rules",
        "/manifest/sources",
        "/manifest/graph_hashes",
        "/graphs",
        "/digest",
    ] {
        let mut modified = value.clone();
        *modified.pointer_mut(pointer).unwrap() = json!("tampered");
        assert!(
            snapshot
                .load_discovery(&serialized(&modified), &scope, &policy(), &config)
                .is_err(),
            "accepted {pointer}"
        );
    }
    let mut modified = value.clone();
    modified["graphs"][A]["documents"][SHARED]["texts"][0]["value"]["text"] =
        json!("PRIVATE_INJECTED_CANARY");
    assert!(snapshot
        .load_discovery(&serialized(&modified), &scope, &policy(), &config)
        .is_err());
    assert!(snapshot
        .load_discovery(b"{}", &scope, &policy(), &config)
        .is_err());
    assert!(snapshot
        .load_discovery(b"not json", &scope, &policy(), &config)
        .is_err());
    assert!(snapshot
        .load_discovery(&bytes, &[A.into()], &policy(), &config)
        .is_err());
    assert!(snapshot
        .load_discovery(&bytes, &[PRIVATE.into()], &policy(), &config)
        .is_err());
    let mut new_policy = policy();
    new_policy.max_rows -= 1;
    assert!(snapshot
        .load_discovery(&bytes, &scope, &new_policy, &config)
        .is_err());
    let mut new_config: DiscoveryConfig = serde_json::from_slice(&serialized(&config)).unwrap();
    new_config.graphs.get_mut(A).unwrap().importer_revision = "different importer".into();
    assert!(snapshot
        .load_discovery(&bytes, &scope, &policy(), &new_config)
        .is_err());
    new_config.version += 1;
    assert!(snapshot
        .build_discovery(&scope, &policy(), &new_config)
        .is_err());
    new_config.version = 1;
    new_config.graphs.remove(A);
    assert!(snapshot
        .build_discovery(&scope, &policy(), &new_config)
        .is_err());
    new_config.graphs.insert(
        A.into(),
        Source {
            source: String::new(),
            license: String::new(),
            source_revision: String::new(),
            importer_revision: String::new(),
        },
    );
    assert!(snapshot
        .build_discovery(&scope, &policy(), &new_config)
        .is_err());
    let changed = Snapshot::from_bytes(&[RDF, b"\n"].concat(), "trig").unwrap();
    assert!(changed.build_discovery(&scope, &policy(), &config).is_err());
    let mut changed_config = config;
    changed_config.snapshot_id = changed.id().into();
    assert!(changed
        .load_discovery(&bytes, &scope, &policy(), &changed_config)
        .is_err());
    let mut absent_policy = policy();
    absent_policy.graphs.push("urn:absent".into());
    changed_config
        .graphs
        .insert("urn:absent".into(), changed_config.graphs[A].clone());
    assert!(changed
        .build_discovery(&["urn:absent".into()], &absent_policy, &changed_config)
        .is_err());
    let mut extra = serde_json::to_value(&changed_config).unwrap();
    extra["unknown"] = json!(true);
    assert!(serde_json::from_value::<DiscoveryConfig>(extra).is_err());
}

#[test]
fn retained_snapshot_configs_pin_sources_importers_and_cover_every_resource() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    for (dataset, importer) in [
        ("wikidata", "dataset.py"),
        ("worldcities-transfer", "worldcities_transfer.py"),
    ] {
        let data = root.join("data").join(dataset);
        let snapshot =
            Snapshot::from_bytes(&std::fs::read(data.join("snapshot.nq")).unwrap(), "nquads")
                .unwrap();
        let config: DiscoveryConfig =
            serde_json::from_slice(&std::fs::read(data.join("discovery.json")).unwrap()).unwrap();
        let policy: Policy =
            serde_json::from_slice(&std::fs::read(data.join("policy.json")).unwrap()).unwrap();
        let scope = policy.graphs.clone();
        let index = snapshot.build_discovery(&scope, &policy, &config).unwrap();
        let source_hash = format!(
            "manifest-sha256:{:x}",
            Sha256::digest(std::fs::read(data.join("manifest.json")).unwrap())
        );
        let importer_hash = format!(
            "sha256:{:x}",
            Sha256::digest(std::fs::read(root.join("tools").join(importer)).unwrap())
        );
        for graph in &scope {
            assert_eq!(config.graphs[graph].source_revision, source_hash);
            assert_eq!(config.graphs[graph].importer_revision, importer_hash);
            let catalog = snapshot
                .catalog(std::slice::from_ref(graph), &policy)
                .unwrap();
            assert_eq!(
                index.graphs()[graph].documents.keys().collect::<Vec<_>>(),
                catalog.entries.keys().collect::<Vec<_>>()
            );
        }
        let bytes = serialized(&index);
        let fresh =
            Snapshot::from_bytes(&std::fs::read(data.join("snapshot.nq")).unwrap(), "nquads")
                .unwrap();
        assert_eq!(
            bytes,
            serialized(&fresh.build_discovery(&scope, &policy, &config).unwrap())
        );
        if dataset == "wikidata" {
            let graph = &index.graphs()["urn:graph-verity:wikidata:development"];
            assert!(graph.postings["oslo"].contains_key("http://www.wikidata.org/entity/Q585"));
            assert!(
                graph.postings["befolkning"].contains_key("http://www.wikidata.org/entity/P1082")
            );
        } else {
            let graph = &index.graphs()["urn:graph-verity:worldcities:transfer:NO"];
            assert!(!graph.postings["oslo"].is_empty());
            assert!(graph
                .documents
                .values()
                .flat_map(|d| &d.texts)
                .any(|t| t.field == Field::Identifier));
        }
    }
}
