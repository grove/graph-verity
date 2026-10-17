use serde_json::{json, Value};
use std::{
    fs,
    io::Write,
    path::Path,
    process::{Command, Output, Stdio},
};

const COMMON: &[&str] = &[
    "data/wikidata/snapshot.nq",
    "nquads",
    "data/wikidata/policy.json",
];
const EXAMPLE: &str = "examples/ask/norway-capital.json";
fn cli(args: &[&str], input: &str) -> Output {
    let mut child = Command::new(env!("CARGO_BIN_EXE_verity"))
        .current_dir(Path::new(env!("CARGO_MANIFEST_DIR")).join("../.."))
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(input.as_bytes())
        .unwrap();
    child.wait_with_output().unwrap()
}
fn values(output: &Output) -> Vec<Value> {
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    serde_json::Deserializer::from_slice(&output.stdout)
        .into_iter::<Value>()
        .map(Result::unwrap)
        .collect()
}
fn args<'a>(command: &'a str, request: &'a str) -> Vec<&'a str> {
    [&[command][..], COMMON, &[request]].concat()
}
fn approval() -> String {
    values(&cli(&args("ask-preview", EXAMPLE), ""))[0]["approval_id"]
        .as_str()
        .unwrap()
        .into()
}

#[test]
fn offline_find_to_preview_confirmation_and_evidence_is_explicit() {
    let found = cli(
        &[
            "find",
            COMMON[0],
            COMMON[1],
            COMMON[2],
            "data/wikidata/scope.json",
            "data/wikidata/discovery.json",
            "examples/find/norway-no.json",
        ],
        "",
    );
    let found = &values(&found)[0];
    let preview = cli(&args("ask-preview", EXAMPLE), "");
    assert!(preview.stderr.is_empty());
    let preview = &values(&preview)[0];
    assert_eq!(
        preview["plan"]["patterns"][0]["from"]["iri"],
        found["hits"][0]["iri"]
    );
    assert!(preview.get("result").is_none());
    assert_eq!(
        preview["ambiguity"],
        "exact_iris_required; no_label_resolution_or_natural_language_interpretation"
    );
    let decision = format!("approve {}\n", preview["approval_id"].as_str().unwrap());
    let output = cli(&args("ask", EXAMPLE), &decision);
    let prompts = String::from_utf8_lossy(&output.stderr);
    assert!(prompts.contains("Review the complete experimental plan"));
    let output = values(&output);
    assert_eq!(output.len(), 2);
    assert_eq!(output[0], *preview);
    assert_eq!(output[1]["status"], "executed");
    assert_eq!(
        output[1]["method"],
        "experimental_user_confirmed_deterministic_template"
    );
    assert_eq!(output[1]["approval_id"], preview["approval_id"]);
    let result = &output[1]["result"];
    assert_eq!(
        result["bindings"],
        json!([{"step1":{"kind":"iri","value":"http://www.wikidata.org/entity/Q585"}}])
    );
    assert_eq!(result["snapshot_id"], preview["plan"]["snapshot_id"]);
    assert_eq!(result["scope"], preview["plan"]["scope"]);
    assert_eq!(result["origin"], "manual");
    assert_eq!(result["interpretation_correctness"], "not_assessed");
    assert_eq!(result["real_world_truth"], "not_established");
    assert_eq!(
        result["evidence"][0]["subject"]["value"],
        found["hits"][0]["iri"]
    );
    assert_eq!(
        result["evidence"][0]["object"]["value"],
        "http://www.wikidata.org/entity/Q585"
    );
    assert_eq!(
        result["evidence"][0]["source_graph"]["value"],
        preview["plan"]["scope"][0]
    );
}

#[test]
fn eof_cancel_yes_missing_and_stale_confirmation_never_execute() {
    let id = approval();
    for decision in [
        "".into(),
        "\n".into(),
        "cancel\n".into(),
        "yes\n".into(),
        "approve\n".into(),
        "approve sha256:stale\n".into(),
        format!("approve {id} EXTRA\n"),
        "x".repeat(1000),
    ] {
        let output = values(&cli(&args("ask", EXAMPLE), &decision));
        assert_eq!(output.len(), 2);
        assert_eq!(output[1], json!({"status":"cancelled"}));
        assert!(output.iter().all(|v| v.get("result").is_none()));
    }
    // A valid edit needs a new approval even though it uses the same graph and entity.
    let output = values(&cli(
        &args("ask", "examples/ask/norway-capital-count.json"),
        &format!("approve {id}\n"),
    ));
    assert_ne!(output[0]["approval_id"], id);
    assert_eq!(output[1], json!({"status":"cancelled"}));
    let current = output[0]["approval_id"].as_str().unwrap();
    let count = values(&cli(
        &args("ask", "examples/ask/norway-capital-count.json"),
        &format!("approve {current}\n"),
    ));
    assert_eq!(count[1]["result"]["bindings"][0]["count"]["value"], "1");
}

#[test]
fn rejected_scope_and_raw_model_plans_disclose_no_private_canaries() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let dir = std::env::temp_dir().join(format!("verity-ask-rejected-{}", std::process::id()));
    fs::create_dir(&dir).unwrap();
    let file = dir.join("request.json");
    let file = file.to_str().unwrap();
    let base: Value = serde_json::from_slice(&fs::read(root.join(EXAMPLE)).unwrap()).unwrap();
    for (pointer, value) in [
        ("/scope", json!(["urn:PRIVATE_GRAPH_CANARY"])),
        ("/template/start", json!("urn:PRIVATE_ID_CANARY")),
        (
            "/template/steps/0/predicate",
            json!("urn:PRIVATE_PREDICATE_CANARY"),
        ),
    ] {
        let mut request = base.clone();
        *request.pointer_mut(pointer).unwrap() = value;
        fs::write(file, request.to_string()).unwrap();
        for command in ["ask-preview", "ask"] {
            let output = cli(&args(command, file), "approve sha256:anything\n");
            assert!(!output.status.success());
            assert!(output.stdout.is_empty());
            assert!(!String::from_utf8_lossy(&output.stderr).contains("PRIVATE_"));
        }
    }
    for (dataset, id) in [
        ("adversarial", "inverse"),
        ("adversarial", "two-hop"),
        ("adversarial", "alias"),
        ("adversarial-transfer", "negation"),
    ] {
        let report: Value = serde_json::from_slice(
            &fs::read(root.join(format!("reports/issue-9-adversarial/{dataset}-report.json")))
                .unwrap(),
        )
        .unwrap();
        let raw = report["cases"]
            .as_array()
            .unwrap()
            .iter()
            .find(|c| c["id"] == id)
            .unwrap()["raw_response"]
            .as_str()
            .unwrap();
        fs::write(file, raw).unwrap();
        let output = cli(&args("ask", file), "approve sha256:anything\n");
        assert!(!output.status.success());
        assert!(output.stdout.is_empty());
        assert!(String::from_utf8_lossy(&output.stderr).contains("needs_clarification:"));
    }
    fs::remove_dir_all(dir).unwrap();
}

#[test]
fn experimental_schema_matches_separate_committed_contract() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let schema = values(&cli(&["schema-ask"], ""));
    let committed: Value =
        serde_json::from_slice(&fs::read(root.join("schemas/confirmed-ask-v1.json")).unwrap())
            .unwrap();
    assert_eq!(schema, [committed]);
}
