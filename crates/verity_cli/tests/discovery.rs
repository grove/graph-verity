use serde_json::Value;
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
fn discovery_cli_builds_and_validates_saved_data_without_partial_error_output() {
    let directory = std::env::temp_dir().join(format!("verity-discovery-{}", std::process::id()));
    std::fs::create_dir(&directory).unwrap();
    let path = directory.join("index.json");
    for (dataset, scope) in [
        ("wikidata", "data/wikidata/scope.json"),
        (
            "worldcities-transfer",
            "examples/compact-v2/schema-scope.json",
        ),
    ] {
        let rdf = format!("data/{dataset}/snapshot.nq");
        let policy = format!("data/{dataset}/policy.json");
        let config = format!("data/{dataset}/discovery.json");
        let args = ["index-build", &rdf, "nquads", &policy, scope, &config];
        let built = cli(&args);
        assert!(
            built.status.success(),
            "{}",
            String::from_utf8_lossy(&built.stderr)
        );
        assert_eq!(built.stdout, cli(&args).stdout);
        let value: Value = serde_json::from_slice(&built.stdout).unwrap();
        assert_eq!(value["manifest"]["version"], 1);
        assert_eq!(value["graphs"].as_object().unwrap().len(), 1);
        std::fs::write(&path, &built.stdout).unwrap();
        let inspect = [
            "index-inspect",
            &rdf,
            "nquads",
            &policy,
            scope,
            &config,
            path.to_str().unwrap(),
        ];
        let loaded = cli(&inspect);
        assert!(
            loaded.status.success(),
            "{}",
            String::from_utf8_lossy(&loaded.stderr)
        );
        assert_eq!(built.stdout, loaded.stdout);
        let mut changed = value;
        changed["manifest"]["version"] = 999.into();
        std::fs::write(&path, serde_json::to_vec(&changed).unwrap()).unwrap();
        let rejected = cli(&inspect);
        assert!(!rejected.status.success());
        assert!(rejected.stdout.is_empty());
        let error: Value = serde_json::from_slice(&rejected.stderr).unwrap();
        assert!(error["detail"]
            .as_str()
            .unwrap()
            .starts_with("index_manifest:"));
    }
    std::fs::remove_dir_all(directory).unwrap();
}
