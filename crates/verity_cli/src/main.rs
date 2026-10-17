#![forbid(unsafe_code)]
use std::{
    env, fs,
    io::{self, BufRead, Write},
    process::ExitCode,
};
use verity_core::{
    catalog::Policy,
    compact::decode_intent,
    evaluation::Benchmark,
    execution::PlanOrigin,
    ir::decode_plan,
    parser::{FixtureParser, ParserOutcome, ParserRequest, Proposal, SemanticParser},
    read_limited, reject, Result, Snapshot,
};

const USAGE: &str = "verity schema | schema-compact | inspect|smoke RDF FORMAT | catalog RDF FORMAT POLICY SCOPE | run RDF FORMAT POLICY PLAN | evaluate RDF FORMAT POLICY BENCHMARK SPLIT OUTDIR | evaluate-local RDF FORMAT POLICY BENCHMARK SPLIT MODEL_ID | replay RDF FORMAT POLICY SCOPE QUESTION_FILE RESPONSE_FILE | resolve RDF FORMAT POLICY SCOPE ROLE TEXT | compact-context RDF FORMAT POLICY SCOPE QUESTION_FILE LIMIT | compact RDF FORMAT POLICY SCOPE QUESTION_FILE LIMIT INTENT_FILE\nFORMAT: trig|nquads|turtle; POLICY, SCOPE, PLAN and BENCHMARK are JSON files. evaluate-local is the private stdio bridge owned by tools/local_parser.py.";

// The parent owns llama.cpp, deadlines and process cleanup; model bytes stay inside response.
struct LlamaCppBridge(String);
impl SemanticParser for LlamaCppBridge {
    fn origin(&self) -> PlanOrigin {
        PlanOrigin::LocalModel
    }
    fn model(&self) -> Option<String> {
        Some(self.0.clone())
    }
    fn propose(&self, request: &ParserRequest) -> Result<Vec<u8>> {
        println!("{}", serde_json::json!({"parser_request": request}));
        io::stdout().flush()?;
        let mut line = Vec::new();
        let mut input = io::stdin().lock();
        // Bound before allocation, including JSON escaping in the bridge envelope.
        loop {
            let available = input.fill_buf()?;
            if available.is_empty() {
                return Err(reject("local_backend", "Parser parent disconnected"));
            }
            let length = available
                .iter()
                .position(|b| *b == b'\n')
                .map_or(available.len(), |i| i + 1);
            if line.len() + length > 1024 * 1024 {
                return Err(reject("input_limit", "Parser bridge line exceeds 1 MiB"));
            }
            line.extend_from_slice(&available[..length]);
            input.consume(length);
            if line.last() == Some(&b'\n') {
                break;
            }
        }
        let reply: serde_json::Value = serde_json::from_slice(&line)?;
        if let Some(error) = reply.get("error").and_then(|v| v.as_str()) {
            return Err(reject("local_backend", error));
        }
        let raw = reply
            .get("response")
            .and_then(|v| v.as_str())
            .ok_or_else(|| reject("local_backend", "Missing model response"))?;
        if raw.len() > 131_072 {
            return Err(reject("input_limit", "Model output exceeds 128 KiB"));
        }
        Ok(raw.as_bytes().to_vec())
    }
}

fn json(path: &str) -> Result<serde_json::Value> {
    Ok(serde_json::from_slice(&read_limited(
        path,
        2 * 1024 * 1024,
    )?)?)
}
fn print_json(value: &impl serde::Serialize) -> Result<()> {
    println!("{}", serde_json::to_string_pretty(value)?);
    Ok(())
}

fn run() -> Result<()> {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.as_slice() == ["schema"] {
        return print_json(&verity_core::schemas());
    }
    if args.as_slice() == ["schema-compact"] {
        return print_json(&verity_core::compact::schema());
    }
    if args.len() < 3 {
        return Err(reject("usage", USAGE));
    }
    let graph = Snapshot::from_bytes(&read_limited(&args[1], 16 * 1024 * 1024)?, &args[2])?;
    if args.len() == 3 {
        return match args[0].as_str() {
            "inspect" => print_json(&graph.info()?),
            "smoke" => {
                println!("{}", graph.smoke_count()?);
                Ok(())
            }
            _ => Err(reject("usage", USAGE)),
        };
    }
    if args.len() < 5 {
        return Err(reject("usage", USAGE));
    }
    let policy: Policy = serde_json::from_value(json(&args[3])?)?;
    match (args[0].as_str(), args.len()) {
        ("compact-context", 7) | ("compact", 8) => {
            let scope: Vec<String> = serde_json::from_value(json(&args[4])?)?;
            let question = String::from_utf8(read_limited(&args[5], 4096)?)
                .map_err(|_| reject("question", "Question file is not UTF-8"))?;
            let limit = args[6]
                .parse()
                .map_err(|_| reject("complexity", "Invalid trusted limit"))?;
            let context = graph.compact_context(question.trim(), &scope, &policy, limit)?;
            if args[0] == "compact-context" {
                return print_json(&context);
            }
            let intent = decode_intent(&read_limited(&args[7], 65_536)?)?;
            let outcome = match graph.expand_compact(&context, &intent, &policy)? {
                Proposal::Candidate { plan } => ParserOutcome::Executed {
                    result: Box::new(graph.execute(&plan, &policy, PlanOrigin::Fixture)?),
                },
                proposal => ParserOutcome::Abstained { proposal },
            };
            print_json(&outcome)
        }
        ("run", 5) => {
            let plan = decode_plan(&read_limited(&args[4], 65_536)?)?;
            print_json(&graph.execute(&plan, &policy, PlanOrigin::Manual)?)
        }
        ("catalog", 5) => {
            let scope: Vec<String> = serde_json::from_value(json(&args[4])?)?;
            print_json(&graph.catalog(&scope, &policy)?)
        }
        ("resolve", 7) => {
            let scope: Vec<String> = serde_json::from_value(json(&args[4])?)?;
            print_json(
                &graph
                    .catalog(&scope, &policy)?
                    .resolve(&args[6], &args[5])?,
            )
        }
        ("replay", 7) => {
            let scope: Vec<String> = serde_json::from_value(json(&args[4])?)?;
            let question = String::from_utf8(read_limited(&args[5], 4096)?)
                .map_err(|_| reject("question", "Question file is not UTF-8"))?;
            let request = graph.parser_request(question.trim(), &scope, &policy)?;
            let mut fixture = FixtureParser::default();
            fixture.insert(&request, read_limited(&args[6], 131_072)?)?;
            print_json(&graph.run_parser(&fixture, question.trim(), &scope, &policy)?)
        }
        ("evaluate", 7) => {
            if !matches!(args[5].as_str(), "dev" | "transfer_dev") {
                return Err(reject(
                    "locked_evaluation",
                    "Private evaluation is disabled in the public CLI",
                ));
            }
            let benchmark: Benchmark = serde_json::from_value(json(&args[4])?)?;
            let report = graph.evaluate(&benchmark, &args[5], &policy, None)?;
            fs::create_dir_all(&args[6])?;
            fs::write(
                format!("{}/report.json", args[6]),
                serde_json::to_vec_pretty(&report)?,
            )?;
            let mut markdown = format!("# Graph Verity oracle evaluation\n\nMode: `{}`. Split: `{}`.\n\n**{} / {} checks passed.** Expected-abstention fixture bookkeeping is not parser accuracy.\n\nSnapshot: `{}`\n\n| Case | Family | Stage | Pass |\n|---|---|---|---|\n", report.mode, report.split, report.passed, report.total, report.snapshot_id);
            for case in &report.cases {
                markdown.push_str(&format!(
                    "| {} | {} | {} | {} |\n",
                    case.id.replace('|', "\\|"),
                    case.family.replace('|', "\\|"),
                    case.stage,
                    case.passed
                ));
            }
            markdown.push_str("\nSee report.json for failures, exact set metrics, measured timings, hashes and limitations. No language model was run. Human gold review and independent holdout are still required.\n");
            fs::write(format!("{}/report.md", args[6]), markdown)?;
            print_json(&report)?;
            if report.passed != report.total {
                return Err(reject(
                    "evaluation_failed",
                    "One or more benchmark checks failed",
                ));
            }
            Ok(())
        }
        ("evaluate-local", 7) => {
            if !matches!(args[5].as_str(), "dev" | "transfer_dev") {
                return Err(reject(
                    "split",
                    "Local spike only accepts public development splits",
                ));
            }
            let benchmark: Benchmark = serde_json::from_value(json(&args[4])?)?;
            println!("{}", serde_json::json!({"startup_ready": true}));
            io::stdout().flush()?;
            let report = graph.evaluate(
                &benchmark,
                &args[5],
                &policy,
                Some(&LlamaCppBridge(args[6].clone())),
            )?;
            println!("{}", serde_json::json!({"report": report}));
            Ok(())
        }
        _ => Err(reject("usage", USAGE)),
    }
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!(
                "{}",
                serde_json::json!({"status":"error", "detail":error.to_string()})
            );
            ExitCode::FAILURE
        }
    }
}
