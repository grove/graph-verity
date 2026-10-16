#![forbid(unsafe_code)]
use std::{env, fs, process::ExitCode};
use verity_core::{catalog::Policy, evaluation::Benchmark, execution::PlanOrigin,
    ir::decode_plan, parser::FixtureParser, read_limited, reject, Result, Snapshot};

const USAGE: &str = "verity schema | inspect|smoke RDF FORMAT | catalog RDF FORMAT POLICY SCOPE | run RDF FORMAT POLICY PLAN | evaluate RDF FORMAT POLICY BENCHMARK SPLIT OUTDIR | replay RDF FORMAT POLICY SCOPE QUESTION_FILE RESPONSE_FILE | resolve RDF FORMAT POLICY SCOPE ROLE TEXT\nFORMAT: trig|nquads|turtle; POLICY, SCOPE, PLAN and BENCHMARK are JSON files";

fn json(path: &str) -> Result<serde_json::Value> {
    Ok(serde_json::from_slice(&read_limited(path, 2 * 1024 * 1024)?)?)
}
fn print_json(value: &impl serde::Serialize) -> Result<()> {
    println!("{}", serde_json::to_string_pretty(value)?);
    Ok(())
}

fn run() -> Result<()> {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.as_slice() == ["schema"] { return print_json(&verity_core::schemas()); }
    if args.len() < 3 { return Err(reject("usage", USAGE)); }
    let graph = Snapshot::from_bytes(&read_limited(&args[1], 16 * 1024 * 1024)?, &args[2])?;
    if args.len() == 3 {
        return match args[0].as_str() {
            "inspect" => print_json(&graph.info()?),
            "smoke" => { println!("{}", graph.smoke_count()?); Ok(()) }
            _ => Err(reject("usage", USAGE)),
        };
    }
    if args.len() < 5 { return Err(reject("usage", USAGE)); }
    let policy: Policy = serde_json::from_value(json(&args[3])?)?;
    match (args[0].as_str(), args.len()) {
        ("run", 5) => {
            let plan = decode_plan(&read_limited(&args[4], 65_536)?)?;
            print_json(&graph.execute(&plan, &policy, PlanOrigin::Manual)?)
        }
        ("catalog", 5) => {
            let scope = serde_json::from_value(json(&args[4])?)?;
            print_json(&graph.catalog(&scope, &policy)?)
        }
        ("resolve", 7) => {
            let scope = serde_json::from_value(json(&args[4])?)?;
            print_json(&graph.catalog(&scope, &policy)?.resolve(&args[6], &args[5])?)
        }
        ("replay", 7) => {
            let scope = serde_json::from_value(json(&args[4])?)?;
            let question = String::from_utf8(read_limited(&args[5], 4096)?)
                .map_err(|_| reject("question", "Question file is not UTF-8"))?;
            let request = graph.parser_request(question.trim(), &scope, &policy)?;
            let mut fixture = FixtureParser::default();
            fixture.insert(&request, read_limited(&args[6], 131_072)?)?;
            print_json(&graph.run_parser(&fixture, question.trim(), &scope, &policy)?)
        }
        ("evaluate", 7) => {
            let benchmark: Benchmark = serde_json::from_value(json(&args[4])?)?;
            let report = graph.evaluate(&benchmark, &args[5], &policy, None)?;
            fs::create_dir_all(&args[6])?;
            fs::write(format!("{}/report.json", args[6]), serde_json::to_vec_pretty(&report)?)?;
            let mut markdown = format!("# Graph Verity oracle evaluation\n\nMode: `{}`. Split: `{}`.\n\n**{} / {} checks passed.** Expected-abstention fixture bookkeeping is not parser accuracy.\n\nSnapshot: `{}`\n\n| Case | Family | Stage | Pass |\n|---|---|---|---|\n", report.mode, report.split, report.passed, report.total, report.snapshot_id);
            for case in &report.cases {
                markdown.push_str(&format!("| {} | {} | {} | {} |\n", case.id.replace('|', "\\|"), case.family.replace('|', "\\|"), case.stage, case.passed));
            }
            markdown.push_str("\nSee report.json for failures, exact set metrics, measured timings, hashes and limitations. No language model was run. Human gold review and independent holdout are still required.\n");
            fs::write(format!("{}/report.md", args[6]), markdown)?;
            print_json(&report)?;
            if report.passed != report.total { return Err(reject("evaluation_failed", "One or more benchmark checks failed")); }
            Ok(())
        }
        _ => Err(reject("usage", USAGE)),
    }
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("{}", serde_json::json!({"status":"error", "detail":error.to_string()}));
            ExitCode::FAILURE
        }
    }
}
