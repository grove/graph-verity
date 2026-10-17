use serde_json::{json, Value};
use std::{path::Path, process::Command};

#[test]
fn find_cli_and_batch_preserve_failures_and_reject_scope_without_output() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let directory = std::env::temp_dir().join(format!("verity-find-{}", std::process::id()));
    std::fs::create_dir(&directory).unwrap();
    let file = directory.join("request.json");
    let scope = "urn:graph-verity:wikidata:development";
    let request = json!({"query":"Oslo","scope":[scope],"role":"entity","limit":10});
    let run = |command: &str| {
        Command::new(env!("CARGO_BIN_EXE_verity"))
            .current_dir(&root)
            .args([
                command,
                "data/wikidata/snapshot.nq",
                "nquads",
                "data/wikidata/policy.json",
                "data/wikidata/scope.json",
                "data/wikidata/discovery.json",
                file.to_str().unwrap(),
            ])
            .output()
            .unwrap()
    };
    std::fs::write(&file, serde_json::to_vec(&request).unwrap()).unwrap();
    let found = run("find");
    assert!(
        found.status.success(),
        "{}",
        String::from_utf8_lossy(&found.stderr)
    );
    let result: Value = serde_json::from_slice(&found.stdout).unwrap();
    assert_eq!(
        result["hits"][0]["iri"],
        "http://www.wikidata.org/entity/Q585"
    );
    assert_eq!(result["hits"][0]["graph"], scope);
    assert_eq!(result["hits"][0]["exact"], true);
    let mut invalid = request.clone();
    invalid["scope"] = json!(["urn:private:CANARY"]);
    std::fs::write(&file, serde_json::to_vec(&invalid).unwrap()).unwrap();
    let rejected = run("find");
    assert!(!rejected.status.success());
    assert!(rejected.stdout.is_empty());
    assert!(String::from_utf8_lossy(&rejected.stderr).contains("scope:"));
    std::fs::write(
        &file,
        serde_json::to_vec(&json!([invalid, request])).unwrap(),
    )
    .unwrap();
    let batch = run("find-batch");
    assert!(batch.status.success());
    let value: Value = serde_json::from_slice(&batch.stdout).unwrap();
    assert!(value["results"][0]["error"]
        .as_str()
        .unwrap()
        .starts_with("scope:"));
    assert_eq!(value["results"][1]["result"], result);
    std::fs::remove_dir_all(directory).unwrap();
}
