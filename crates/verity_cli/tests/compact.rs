use serde_json::{json, Value};
use std::{
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

#[test]
fn compact_cli_replays_public_examples_and_arbitrary_candidates() {
    let schema = cli(&["schema-compact"]);
    assert!(schema.status.success());
    assert_eq!(
        serde_json::from_slice::<Value>(&schema.stdout).unwrap(),
        verity_core::compact::schema()
    );
    for (rdf, policy, scope, question, input, expected) in [
        (
            "data/worldcities-transfer/snapshot.nq",
            "data/worldcities-transfer/policy.json",
            "examples/compact-v2/schema-scope.json",
            "examples/compact-v2/schema-question.txt",
            "examples/compact-v2/schema-two-hop.json",
            "urn:graph-verity:worldcities:country:NO",
        ),
        (
            "data/wikidata/snapshot.nq",
            "data/wikidata/policy.json",
            "data/wikidata/scope.json",
            "examples/compact-v2/wikidata-question.txt",
            "examples/compact-v2/wikidata-two-hop.json",
            "http://www.wikidata.org/entity/Q585",
        ),
    ] {
        let args = [
            "compact-context",
            rdf,
            "nquads",
            policy,
            scope,
            question,
            "100",
        ];
        let context = cli(&args);
        assert!(
            context.status.success(),
            "{}",
            String::from_utf8_lossy(&context.stderr)
        );
        assert_eq!(context.stdout, cli(&args).stdout);
        let output = cli(&[
            "compact", rdf, "nquads", policy, scope, question, "100", input,
        ]);
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        let result: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(result["result"]["plan"]["version"], 1);
        assert_eq!(result["result"]["origin"], "fixture");
        assert_eq!(
            result["result"]["bindings"],
            json!([{"v1":{"kind":"iri","value":expected}}])
        );
        assert_eq!(result["result"]["evidence"].as_array().unwrap().len(), 2);
    }
    let prefix = [
        "compact",
        "data/worldcities-transfer/snapshot.nq",
        "nquads",
        "data/worldcities-transfer/policy.json",
        "examples/compact-v2/schema-scope.json",
        "examples/compact-v2/schema-question.txt",
        "100",
    ];
    for (file, status) in [
        ("examples/compact-v2/unsupported.json", "unsupported"),
        (
            "examples/compact-v2/clarification.json",
            "needs_clarification",
        ),
    ] {
        let mut args = prefix.to_vec();
        args.push(file);
        let output = cli(&args);
        assert!(output.status.success());
        let result: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(result["status"], "abstained");
        assert_eq!(result["proposal"]["status"], status);
        assert!(result.get("result").is_none());
    }
    let custom = std::env::temp_dir().join(format!("verity-compact-{}.json", std::process::id()));
    std::fs::write(
        &custom,
        br#"{"version":2,"proposal":{"status":"candidate","sparql":"DELETE WHERE {?s ?p ?o}"}}"#,
    )
    .unwrap();
    let mut args = prefix.to_vec();
    args.push(custom.to_str().unwrap());
    let output = cli(&args);
    std::fs::remove_file(custom).unwrap();
    assert!(!output.status.success());
    assert!(output.stdout.is_empty());
    let error: Value = serde_json::from_slice(&output.stderr).unwrap();
    assert!(error["detail"]
        .as_str()
        .unwrap()
        .starts_with("compact_json:"));
}
