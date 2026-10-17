use serde_json::{json, Value};
use std::{
    fs,
    path::Path,
    process::{Command, Output},
};

fn cli(args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_verity"))
        .current_dir(Path::new(env!("CARGO_MANIFEST_DIR")).join("../.."))
        .args(args)
        .output()
        .unwrap()
}
fn result(output: Output) -> Value {
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stderr.is_empty());
    serde_json::from_slice(&output.stdout).unwrap()
}

#[test]
fn fresh_offline_bilingual_search_to_relationship_linked_entity_and_snapshot() {
    let common = [
        "data/wikidata/snapshot.nq",
        "nquads",
        "data/wikidata/policy.json",
        "data/wikidata/scope.json",
        "data/wikidata/discovery.json",
    ];
    let run =
        |command: &str, request: &str| result(cli(&[&[command][..], &common, &[request]].concat()));
    let no = run("find", "examples/find/norway-no.json");
    let en = run("find", "examples/find/norway-en.json");
    assert_eq!(no["hits"][0]["iri"], "http://www.wikidata.org/entity/Q20");
    assert_eq!(no["hits"][0]["iri"], en["hits"][0]["iri"]);
    let country = run("entity", "examples/find/norway-entity.json");
    let edge = country["evidence"]
        .as_array()
        .unwrap()
        .iter()
        .find(|e| e["predicate"]["value"] == "http://www.wikidata.org/prop/direct/P36")
        .unwrap();
    assert_eq!(edge["subject"]["value"], no["hits"][0]["iri"]);
    assert_eq!(
        edge["object"]["value"],
        "http://www.wikidata.org/entity/Q585"
    );
    let city = run("entity", "examples/find/oslo-incoming.json");
    assert_eq!(city["iri"], edge["object"]["value"]);
    assert!(city["evidence"].as_array().unwrap().contains(edge));
    assert_eq!(city["snapshot_id"], country["snapshot_id"]);
    assert_eq!(city["snapshot_id"], no["snapshot_id"]);
    let graph = edge["source_graph"]["value"].as_str().unwrap();
    assert_eq!(city["sources"][graph]["license"], "CC0-1.0");
    assert_eq!(city["evidence_verification"], "verified_against_snapshot");
}

#[test]
fn cli_private_canaries_stay_out_of_output_and_errors_and_stale_bundles_fail() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let dir = std::env::temp_dir().join(format!("verity-navigation-{}", std::process::id()));
    fs::create_dir(&dir).unwrap();
    let rdf = root.join("tests/fixtures/discovery.trig");
    let graph = "urn:discovery:a";
    let snapshot = verity_core::snapshot_id(&fs::read(&rdf).unwrap(), "trig");
    let policy = dir.join("policy.json");
    let scope = dir.join("scope.json");
    let config = dir.join("config.json");
    let request = dir.join("request.json");
    let index = dir.join("index.json");
    fs::write(
        &policy,
        json!({"version":1,"graphs":[graph],"max_rows":50,"max_evidence":50,"timeout_ms":1000})
            .to_string(),
    )
    .unwrap();
    fs::write(&scope, json!([graph]).to_string()).unwrap();
    fs::write(&config, json!({"version":1,"snapshot_id":snapshot,"graphs":{graph:{"source":"synthetic","license":"Apache-2.0","source_revision":"v1","importer_revision":"v1"}}}).to_string()).unwrap();
    let common = [
        rdf.to_str().unwrap(),
        "trig",
        policy.to_str().unwrap(),
        scope.to_str().unwrap(),
        config.to_str().unwrap(),
    ];
    let mut entity = json!({"snapshot_id":snapshot,"scope":[graph],"iri":"urn:discovery:shared","direction":"outgoing","offset":0,"limit":1});
    let built = result(cli(&[&["index-build"][..], &common].concat()));
    fs::write(&index, built.to_string()).unwrap();
    for command in ["entity", "find"] {
        let mut req = if command == "entity" {
            entity.clone()
        } else {
            json!({"query":"Island","scope":[graph],"role":null,"limit":1})
        };
        fs::write(&request, req.to_string()).unwrap();
        let args = [
            &[command][..],
            &common,
            &[request.to_str().unwrap(), index.to_str().unwrap()],
        ]
        .concat();
        let value = result(cli(&args));
        assert_eq!(value["truncated"], true);
        assert!(!value.to_string().contains("PRIVATE_"));
        req["scope"] = json!(["urn:discovery:private"]);
        fs::write(&request, req.to_string()).unwrap();
        let rejected = cli(&args);
        assert!(!rejected.status.success());
        assert!(rejected.stdout.is_empty());
        let error = String::from_utf8(rejected.stderr).unwrap();
        assert!(error.contains("scope:"));
        assert!(!error.contains("private"));
        assert!(!error.contains("PRIVATE_"));
    }
    entity["iri"] = "urn:discovery:PRIVATE_ID_CANARY".into();
    fs::write(&request, entity.to_string()).unwrap();
    let args = [
        &["entity"][..],
        &common,
        &[request.to_str().unwrap(), index.to_str().unwrap()],
    ]
    .concat();
    let absent = result(cli(&args));
    assert_eq!(absent["status"], "no_match");
    assert!(!absent.to_string().contains("PRIVATE_"));
    let mut tampered = built;
    tampered["graphs"][graph]["statistics"]["documents"] = 987654321.into();
    tampered["graphs"]["urn:discovery:private"] =
        json!({"PRIVATE_ID_CANARY":"PRIVATE_TEXT_CANARY"});
    fs::write(&index, tampered.to_string()).unwrap();
    for command in ["entity", "find"] {
        let rejected = cli(&[
            &[command][..],
            &common,
            &[request.to_str().unwrap(), index.to_str().unwrap()],
        ]
        .concat());
        assert!(!rejected.status.success());
        assert!(rejected.stdout.is_empty());
        let error = String::from_utf8(rejected.stderr).unwrap();
        assert!(error.contains("index_manifest:"));
        for secret in ["PRIVATE_", "987654321", "urn:discovery:private"] {
            assert!(!error.contains(secret));
        }
    }
    let malformed = dir.join("malformed.nq");
    fs::write(
        &malformed,
        b"<PRIVATE_ID_CANARY> <urn:p> \"PRIVATE_TEXT_CANARY\" <urn:private> .",
    )
    .unwrap();
    for command in ["find", "entity"] {
        let rejected = cli(&[
            command,
            malformed.to_str().unwrap(),
            "nquads",
            policy.to_str().unwrap(),
            scope.to_str().unwrap(),
            config.to_str().unwrap(),
            request.to_str().unwrap(),
        ]);
        assert!(!rejected.status.success());
        assert!(rejected.stdout.is_empty());
        let error = String::from_utf8(rejected.stderr).unwrap();
        assert!(error.contains("RDF input could not be parsed"));
        assert!(!error.contains("PRIVATE_"));
    }
    fs::remove_dir_all(dir).unwrap();
}
