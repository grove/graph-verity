//! Opt-in experiment transport: one authorized index, bounded requests, no model.
use std::io::{self, BufRead, Read, Write};
use std::time::Instant;
use verity_core::{
    catalog::Policy, discovery::DiscoveryConfig, find::FindRequest, read_limited, Snapshot,
};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.len() != 4 {
        return Err("usage: retrieval_session RDF POLICY SCOPE DISCOVERY".into());
    }
    let start = Instant::now();
    let snapshot = Snapshot::from_bytes(&read_limited(&args[0], 16 * 1024 * 1024)?, "nquads")?;
    let policy: Policy = serde_json::from_slice(&read_limited(&args[1], 65536)?)?;
    let scope: Vec<String> = serde_json::from_slice(&read_limited(&args[2], 65536)?)?;
    let config: DiscoveryConfig = serde_json::from_slice(&read_limited(&args[3], 65536)?)?;
    let index = snapshot.build_discovery(&scope, &policy, &config)?;
    let mut output = io::stdout().lock();
    writeln!(
        output,
        "{}",
        serde_json::json!({
            "ready": true, "build_ms": start.elapsed().as_secs_f64() * 1000.0,
            "index_bytes": serde_json::to_vec(&index)?.len(), "manifest": index.manifest()
        })
    )?;
    output.flush()?;
    let mut input = io::stdin().lock();
    loop {
        let mut bytes = Vec::new();
        let size = (&mut input).take(65537).read_until(b'\n', &mut bytes)?;
        if size == 0 {
            break;
        }
        if size > 65536 || bytes.last() != Some(&b'\n') {
            return Err("request exceeds bounded NDJSON frame".into());
        }
        let request: FindRequest = serde_json::from_slice(&bytes)?;
        let response = index.find(&request, &policy)?;
        serde_json::to_writer(&mut output, &response)?;
        writeln!(output)?;
        output.flush()?;
    }
    Ok(())
}
