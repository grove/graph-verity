use serde_json::{json, Value};
use std::{path::Path, process::Command};

#[test]
fn vocabulary_cli_replays_bounded_packets_and_rejects_unknown_fields_and_stale_ids() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let dir = std::env::temp_dir().join(format!("verity-vocabulary-{}", std::process::id()));
    std::fs::create_dir(&dir).unwrap();
    let run = |args: &[&str]| {
        Command::new(env!("CARGO_BIN_EXE_verity"))
            .current_dir(&root)
            .args(args)
            .output()
            .unwrap()
    };
    let args = [
        "data/wikidata/snapshot.nq",
        "nquads",
        "data/wikidata/policy.json",
        "data/wikidata/scope.json",
        "data/wikidata/discovery.json",
    ];
    let index = run(&[&["index-build"], &args[..]].concat());
    assert!(index.status.success());
    let manifest: Value = serde_json::from_slice(&index.stdout).unwrap();
    let request = dir.join("request.json");
    let budget = dir.join("budget.json");
    let saved = dir.join("packet.json");
    let mut r = json!({"question":"Hva er hovedstaden i Norge?", "language":"nb", "scope":["urn:graph-verity:wikidata:development"], "snapshot_id":manifest["manifest"]["snapshot_id"], "index_revision":manifest["manifest"]["index_revision"]});
    std::fs::write(&request, serde_json::to_vec(&r).unwrap()).unwrap();
    std::fs::write(&budget, br#"{"per_role_top_k":20,"max_packet_bytes":262144,"texts_per_candidate":8,"max_text_bytes":2048,"evidence_per_page":3,"max_source_bytes":4096}"#).unwrap();
    let request_args = [request.to_str().unwrap(), budget.to_str().unwrap()];
    let output = run(&[&["vocabulary"], &args[..], &request_args].concat());
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stdout.len() <= 262145);
    std::fs::write(&saved, output.stdout.trim_ascii_end()).unwrap();
    let replay = run(&[
        &["vocabulary-replay"],
        &args[..],
        &request_args,
        &[saved.to_str().unwrap()],
    ]
    .concat());
    assert!(
        replay.status.success(),
        "{}",
        String::from_utf8_lossy(&replay.stderr)
    );
    assert_eq!(output.stdout, replay.stdout);
    let schema = run(&["schema-vocabulary"]);
    assert_eq!(
        serde_json::from_slice::<Value>(&schema.stdout).unwrap(),
        serde_json::from_slice::<Value>(
            &std::fs::read(root.join("schemas/question-vocabulary-packet-v1.json")).unwrap()
        )
        .unwrap()
    );
    for field in ["extra_field", "snapshot_id", "index_revision", "scope"] {
        let old = r.get(field).cloned();
        r[field] = json!("untrusted");
        std::fs::write(&request, serde_json::to_vec(&r).unwrap()).unwrap();
        let rejected = run(&[&["vocabulary"], &args[..], &request_args].concat());
        assert!(!rejected.status.success());
        assert!(rejected.stdout.is_empty());
        if let Some(value) = old {
            r[field] = value;
        } else {
            r.as_object_mut().unwrap().remove(field);
        }
    }
    std::fs::remove_dir_all(dir).unwrap();
}
