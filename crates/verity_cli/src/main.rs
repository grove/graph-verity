#![forbid(unsafe_code)]

use std::{env, fs, process::ExitCode};
use verity_core::{reject, Result, Snapshot};

fn run() -> Result<()> {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() != 3 || !matches!(args[0].as_str(), "inspect" | "smoke") {
        return Err(reject("usage", "verity <inspect|smoke> <file> <trig|nquads|turtle>"));
    }
    let graph = Snapshot::from_bytes(&fs::read(&args[1])?, &args[2])?;
    match args[0].as_str() {
        "inspect" => println!("{}", serde_json::to_string_pretty(&graph.info()?)?),
        "smoke" => println!("{}", graph.smoke_count()?),
        _ => unreachable!(),
    }
    Ok(())
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("{error}");
            ExitCode::FAILURE
        }
    }
}
