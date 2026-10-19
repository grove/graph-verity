#!/usr/bin/env python3
"""#83 offline, operator-only native nl-ask-draft-v1 experiment. Preview only."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import threading
import time

import grounded_models as g
import one_hop_trial as t
import question_vocabulary as v
from local_parser import HTTP, sha

ROOT, BINARY = t.ROOT, t.BINARY
CONFIG = ROOT / "configs/native-one-hop-v1c.json"
REPORT = ROOT / "reports/issue-83-native-one-hop"
read, dump, require = v.read, v.dump, v.require


def config():
    cfg = read(CONFIG)
    require(cfg["version"] == "issue83-native-cpu-v1c", "Unknown native adapter")
    cpu = read(ROOT / cfg["cpu_protocol"])
    require(cpu["cpu_threads"] == 4 and cpu["gpu_layers"] == 0 and cpu["concurrency"] == 1
            and cpu["temperature"] == 0 and cpu["quantization"] == "Q4_K_M"
            and cpu["context_tokens"] == 16384 and cpu["max_output_tokens"] == 512
            and cpu["retries"] == 0 and cpu["thinking"] is False, "CPU variant changed")
    return {**cpu, **cfg}


def grammar(context):
    text = (ROOT / config()["grammar_file"]).read_text()
    if not context["entities"] or not context["predicates"]:
        text = text.replace("root ::= candidate | clarification | unsupported", "root ::= clarification | unsupported")
    for rule, collection in [("entity-id", "entities"), ("predicate-id", "predicates"), ("graph-id", "graphs")]:
        ids = [r["id"] for r in context[collection]]
        require(all(type(i) is int and 0 <= i <= 65535 for i in ids) and len(ids) == len(set(ids)), "Invalid table IDs")
        # An empty table cannot yield a candidate; keep the unreachable rule syntactically valid.
        text += rule + " ::= " + " | ".join(json.dumps(str(i)) for i in ids or [0]) + "\n"
    return text


def freeze(out, binary=BINARY):
    """New packets; same exposed #74 questions and source-authorized oracle table."""
    require(not out.exists(), "Never overwrite a freeze")
    cfg = config()
    original = t.REPORT / "freeze"
    require(read(original / "checksums.json") == v.inventory(original), "Changed #74 evidence")
    out.mkdir(parents=True)
    (out / "contexts").mkdir()
    (out / "packets").mkdir()
    questions = read(original / "questions.json")["questions"]
    require(len(questions) == 30, "Keep all 30 evaluation questions")
    dump(out / "questions.json", questions)
    table = read(t.STUDY / "catalog.json")
    dump(out / "catalog.json", table)
    discovery = read(t.STUDY / "discovery.json")
    args = [t.STUDY / "snapshot.nq", "nquads", t.STUDY / "policy.json", t.STUDY / "scope.json", t.STUDY / "discovery.json"]
    manifest = json.loads(v.cli(binary, "index-build", *args))["manifest"]
    dump(out / "index-manifest.json", manifest)
    budget = read(v.DEFAULT_PROTOCOL)["budget"]
    dump(out / "budget.json", budget)
    graphs = {r["id"]: r["iri"] for r in table["graphs"]}
    for q in questions:
        folder = out / "packets" / q["id"]
        folder.mkdir()
        request = dict(question=q["question"], language=q["language"], snapshot_id=manifest["snapshot_id"],
                       index_revision=manifest["index_revision"], scope=read(t.STUDY / "scope.json"))
        dump(folder / "request.json", request)
        packet_bytes = v.cli(binary, "vocabulary", *args, folder / "request.json", out / "budget.json")
        (folder / "packet.json").write_bytes(packet_bytes)
        packet = json.loads(packet_bytes)
        v.source_audit(packet, dict(rdf=str((t.STUDY / "snapshot.nq").relative_to(ROOT)),
                                   policy=str((t.STUDY / "policy.json").relative_to(ROOT))), dict(required=[]))
        oracle = read(original / "contexts" / f"{q['id']}-oracle.json")
        require(oracle["question"] == q["question"] and oracle["language"] == q["language"]
                and oracle["snapshot_id"] == manifest["snapshot_id"], "Context identity drift")
        for stage in cfg["stages"]:
            context = {**oracle, "source_provenance": discovery["graphs"]}
            if stage == "retrieval":
                context["packet"] = packet
                for collection in ["entities", "predicates"]:
                    retained = {(r["graph"], r["iri"]) for r in packet[collection]["candidates"]}
                    context[collection] = [r for r in oracle[collection] if (graphs[r["graph"]], r["iri"]) in retained]
            dump(out / "contexts" / f"{q['id']}-{stage}.json", context)
    # Resolution fixtures are for the offline Rust preview/scorer only, never serialized into prompts.
    dump(out / "operator-fixtures.json", {c["id"]: dict(resolved_start=c["resolved_start"], blocked=c["preflight_blocked"])
                                         for c in t.cases()})
    paths = [CONFIG, ROOT / cfg["prompt_file"], ROOT / cfg["grammar_file"], ROOT / cfg["control_prompt_file"], t.CONFIG, g.CONFIG,
             Path(__file__), ROOT / "tools/grounded_models.py", ROOT / "tools/one_hop_trial.py",
             ROOT / "tools/local_parser.py", ROOT / "tools/compact_ab.py", ROOT / "tools/phase0.py", ROOT / "tools/question_vocabulary.py", ROOT / "tools/nl_ask_benchmark.py",
             ROOT / "schemas/nl-ask-draft-v1.json", ROOT / "Cargo.lock", ROOT / "rust-toolchain.toml",
             t.n.STUDY / "freeze.json", t.n.STUDY / "cases.json", original / "checksums.json",
             *sorted(t.STUDY.glob("*")), *sorted((ROOT / "crates").rglob("*.rs"))]
    require(json.loads(v.cli(binary, "schema-nl-ask")) == read(ROOT / "schemas/nl-ask-draft-v1.json"), "Rust schema drift")
    dump(out / "freeze.json", dict(version=cfg["version"], config=cfg, exposed_evaluation=True,
         input_sha256={str(p.relative_to(ROOT)): sha(p) for p in paths if p.is_file()},
         binary_sha256=sha(binary), source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
         executions=0, inference_performed=False))
    dump(out / "checksums.json", v.inventory(out))


def verify_freeze(folder, binary=BINARY):
    require(read(folder / "checksums.json") == v.inventory(folder), "Changed new freeze")
    frozen = read(folder / "freeze.json")
    require(frozen["config"] == config(), "Adapter configuration changed")
    for name, digest in frozen["input_sha256"].items():
        require(sha(ROOT / name) == digest, "Changed frozen input: " + name)
    require(sha(binary) == frozen["binary_sha256"], "Rust binary changed; create a new freeze")
    return frozen


def preflight(out):
    """Always fresh; no process arguments, environment values or credentials."""
    out.parent.mkdir(parents=True, exist_ok=True)
    t.preflight(out)
    host = read(out)
    extra = [t.command(args) for args in [["pmset", "-g", "therm"], ["pmset", "-g", "batt"], ["vm_stat"]]]
    host["commands"] += extra
    host["version"] = "issue83-host-v1"
    cfg = config()
    host["blockers"] = t.host_blockers(host, cfg)
    hardware = host["commands"][2]["stdout"].splitlines()
    if len(hardware) != 4 or hardware[1] != str(cfg["hardware"]["memory_bytes"]) or hardware[3] != cfg["hardware"]["cpu"] \
            or host["commands"][1]["stdout"].strip() != cfg["hardware"]["architecture"]:
        host["blockers"].append(dict(metric="hardware", reason="not_preregistered_M1_Pro_32_GiB"))
    thermal = extra[0]["stdout"] + extra[0]["stderr"]
    limits = re.findall(r"(?:CPU_Speed_Limit|CPU_Scheduler_Limit)\s*=\s*(\d+)", thermal)
    warning_free = ("No thermal warning level has been recorded" in thermal and
                    "No performance warning level has been recorded" in thermal)
    if not warning_free or any(int(x) != 100 for x in limits):
        host["blockers"].append(dict(metric="thermal", reason="warning_or_unverified_thermal_state"))
    if "Now drawing from 'AC Power'" not in extra[1]["stdout"]:
        host["blockers"].append(dict(metric="power", reason="AC_power_required"))
    host["completed_at"] = datetime.now(timezone.utc).isoformat()
    dump(out, host)
    return host


def assets(out):
    """Read/hash native and Q4 bytes; never acquire, convert, build or load."""
    t.assets(out)
    evidence = read(out)
    historical = g.config()
    source = g.ASSETS / "upstream" / ("llama.cpp-" + historical["runtime_revision"])
    require(source.is_dir(), "Pinned runtime source missing; no automatic extraction")
    g.source_tree(historical, g.ASSETS)
    pinned = read(t.REPORT / "assets.json")
    for key in config()["variants"]:
        actual = evidence["candidates"][key]
        expected = pinned["candidates"][key]
        require(actual["preparation_receipt_sha256"] == expected["preparation_receipt_sha256"], "Preparation receipt drift")
        require(actual["verified_retained_files"] == expected["verified_retained_files"], "Native runtime/Q4 drift")
    evidence["runtime_source_tree_verified"] = True
    evidence["original_licenses_verified"] = True
    dump(out, evidence)
    return evidence


def offline_env(folder):
    home = folder / "offline-home"
    home.mkdir(exist_ok=True)
    return dict(PATH="/usr/bin:/bin:/usr/sbin:/sbin", HOME=str(home), TMPDIR=str(home),
                HF_HOME=str(home), HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                HF_HUB_DISABLE_TELEMETRY="1", DO_NOT_TRACK="1", TOKENIZERS_PARALLELISM="false",
                OMP_NUM_THREADS="4", OPENBLAS_NUM_THREADS="4", VECLIB_MAXIMUM_THREADS="4")


def stop_tree(process):
    if process is None:
        return
    # Every managed child owns a new session. Kill that group even if its leader already exited.
    for sig in [signal.SIGTERM, signal.SIGKILL]:
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass
        if sig == signal.SIGTERM:
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
    process.wait(timeout=5)


def bounded(args, folder, name, timeout=60):
    dump(folder / f"{name}-command.json", list(map(str, args)))
    with (folder / f"{name}.stdout").open("wb") as stdout, (folder / f"{name}.stderr").open("wb") as stderr:
        process = subprocess.Popen(list(map(str, args)), cwd=ROOT, env=offline_env(folder),
                                   stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            return process.wait(timeout=timeout)
        finally:
            stop_tree(process)


@contextmanager
def deadline(seconds, process):
    expired = threading.Event()
    def cancel():
        expired.set()
        stop_tree(process)
    timer = threading.Timer(seconds, cancel)
    timer.daemon = True
    timer.start()
    try:
        yield
    finally:
        timer.cancel()
        timer.join()
        if expired.is_set():
            raise TimeoutError("Native runtime wall deadline")


class Runtime(g.Runtime):
    """Reuse #48's loopback streaming transport, with a new contract and owned process group."""
    def __enter__(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        args = [self.assets / "build/bin/llama-server", "--model", self.assets / f"{self.key}-Q4_K_M.gguf",
                "--host", "127.0.0.1", "--port", str(self.port), "--n-gpu-layers", "0", "--threads", "4",
                "--threads-batch", "4", "--ctx-size", str(self.cfg["context_tokens"]), "--parallel", "1",
                "--no-context-shift", "--offline", "--no-webui", "--no-ui-mcp-proxy", "--jinja",
                "--chat-template-file", self.assets / f"upstream/{self.key}/chat_template.jinja",
                "--chat-template-kwargs", '{"enable_thinking":false}', "--reasoning", "off"]
        dump(self.out / "server-command.json", list(map(str, args)))
        self.log = (self.out / "server.log").open("w")
        self.started = started = time.monotonic()
        try:
            self.process = subprocess.Popen(list(map(str, args)), cwd=ROOT, env=offline_env(self.out),
                                            stdout=self.log, stderr=self.log, start_new_session=True)
            with deadline(self.cfg["timeout_seconds"], self.process):
                while time.monotonic() - started < self.cfg["timeout_seconds"]:
                    require(self.process.poll() is None, "Native backend exited during startup; see server.log")
                    try:
                        with HTTP.open(f"http://127.0.0.1:{self.port}/health", timeout=1) as response:
                            if response.status == 200:
                                self.startup_ms = (time.monotonic() - started) * 1000
                                return self
                    except OSError:
                        time.sleep(.1)
                raise TimeoutError("Native startup deadline")
        except BaseException:
            self.__exit__()
            raise

    def __exit__(self, *unused):
        stop_tree(self.process)
        if hasattr(self, "log"):
            self.log.close()

    def post(self, endpoint, body, name):
        dump(name.with_suffix(".request.json"), body)
        with deadline(self.cfg["timeout_seconds"], self.process):
            return super().post(endpoint, body, name)

    def template_parity(self, context, folder, system=None):
        messages = [{"role": "system", "content": system if system is not None else (ROOT / self.cfg["prompt_file"]).read_text()},
                    {"role": "user", "content": g.safe_user(context)}]
        dump(folder / "messages.json", messages)
        script = ("import json,sys; from transformers import AutoTokenizer; "
                  "t=AutoTokenizer.from_pretrained(sys.argv[1],local_files_only=True,trust_remote_code=False); "
                  "m=json.load(open(sys.argv[2])); "
                  "print(json.dumps({'prompt':t.apply_chat_template(m,tokenize=False,add_generation_prompt=True,enable_thinking=False),"
                  "'tokens':t.apply_chat_template(m,tokenize=True,return_dict=False,add_generation_prompt=True,enable_thinking=False)}))")
        code = bounded([self.reference_python, "-c", script, self.assets / "upstream" / self.key, folder / "messages.json"],
                       folder, "native-template")
        require(code == 0, "Native tokenizer failed; see native-template.stderr")
        expected = read(folder / "native-template.stdout")
        actual = self.post("apply-template", dict(messages=messages, add_generation_prompt=True,
            chat_template_kwargs={"enable_thinking": False}), folder / "parity-template")
        prefix = ""
        if actual["prompt"] != expected["prompt"]:
            bos = read(self.assets / f"upstream/{self.key}/tokenizer_config.json").get("bos_token")
            require(self.key == "gemma4" and isinstance(bos, str) and bos and bos + actual["prompt"] == expected["prompt"],
                    "Native chat template mismatch beyond Gemma's documented BOS omission")
            prefix = bos
        tokens = self.post("tokenize", dict(content=prefix + actual["prompt"], add_special=False, parse_special=True), folder / "parity-tokens")
        require(tokens["tokens"] == expected["tokens"], "Native/GGUF token ID mismatch")
        require(not self.template_prefix or self.template_prefix == prefix, "BOS behavior changed between requests")
        self.template_prefix = prefix
        dump(folder / "parity.json", dict(restored_bos=prefix, prompt_sha256=hashlib.sha256(expected["prompt"].encode()).hexdigest(),
                                         token_ids_equal=True, prompt_bytes_equal=True))
        return expected

    def generate(self, context, out, constrained=True, system=None):
        started = time.monotonic()
        native = self.template_parity(context, out, system)
        tokens = native["tokens"]
        require(len(tokens) + self.cfg["max_output_tokens"] < self.cfg["context_tokens"], "Context budget exceeded")
        (out / "prompt.txt").write_bytes(native["prompt"].encode())
        body = dict(prompt=tokens, n_predict=self.cfg["max_output_tokens"], temperature=0, seed=self.cfg["seed"],
                    cache_prompt=True, stream=True)
        if constrained:
            body["grammar"] = grammar(context)
        dump(out / "completion-request.json", body)
        self.generation_attempts += 1
        result = self.post("completion", body, out / "completion")
        self.generation_completed += 1
        require((out / "proposal.txt").stat().st_size <= self.cfg["max_draft_bytes"], "Oversized draft")
        result.update(input_token_count=len(tokens), elapsed_ms=(time.monotonic() - started) * 1000)
        if not hasattr(self, "first_answer_ms"):
            self.first_answer_ms = (time.monotonic() - self.started) * 1000
        dump(out / "runtime.json", result)
        require(not result.get("stopped_limit") and result.get("stop_type") != "limit", "Token limit reached; no completed draft")
        return result


def preview_raw(context, raw_path, out, fixture, binary=BINARY):
    """Pass the untouched file to Rust, never json.loads/repair/re-serialize a draft."""
    table = {k: context[k] for k in ["snapshot_id", "graphs"]}
    for collection in ["entities", "predicates"]:
        table[collection] = [{k: r[k] for k in ["id", "graph", "iri"]} for r in context[collection]]
    available = {r["id"] for r in table["entities"]}
    table.update(resolved_start=fixture["resolved_start"] if fixture["resolved_start"] in available else None,
                 blocked=fixture["blocked"], limit=100)
    dump(out / "catalog.json", table)
    code = bounded([binary, "nl-ask-preview", t.STUDY / "snapshot.nq", "nquads", t.STUDY / "policy.json",
                    t.STUDY / "scope.json", t.STUDY / "discovery.json", out / "catalog.json", raw_path], out, "rust-preview", 30)
    result = dict(returncode=code, stdout=(out / "rust-preview.stdout").read_text(), stderr=(out / "rust-preview.stderr").read_text())
    dump(out / "rust.json", result)
    return result


def grammar_check(text, context, out):
    (out / "control.gbnf").write_text(grammar(context))
    (out / "control.txt").write_text(text)
    code = bounded([g.ASSETS / "build/bin/test-gbnf-validator", out / "control.gbnf", out / "control.txt"], out, "gbnf", 10)
    return code == 0 and (out / "gbnf.stdout").read_text().strip() == "Input string is valid according to the grammar."


def grammar_controls(context, out):
    out.mkdir()
    candidate = dict(version="nl-ask-draft-v1", status="candidate", start=context["entities"][0]["id"],
                     predicate=context["predicates"][0]["id"], graph=context["graphs"][0]["id"],
                     direction="forward", output="values", rationale="control")
    valid = [json.dumps(candidate)] + [json.dumps(dict(version="nl-ask-draft-v1", status=s, rationale="control"))
                                     for s in ["needs_clarification", "unsupported"]]
    bad = ["not JSON", valid[0][:-1], valid[0] + valid[0], valid[0].replace('"start":', '"start": 100, "start":'),
           json.dumps({**candidate, "sparql": "DELETE WHERE {?s ?p ?o}"}), json.dumps({**candidate, "start": 65535}),
           json.dumps({**candidate, "direction": "sideways"}), json.dumps({**candidate, "rationale": ""}),
           json.dumps({**candidate, "rationale": "x" * 513})]
    verdicts = []
    for i, text in enumerate(valid + bad):
        folder = out / str(i)
        folder.mkdir()
        verdicts.append(grammar_check(text, context, folder))
    dump(out / "controls.json", dict(accepted=verdicts, expected=[True] * len(valid) + [False] * len(bad)))
    require(verdicts == [True] * len(valid) + [False] * len(bad), "Official runtime GBNF controls failed")


def sample_rss(out, done, result):
    try:
        with (out / "rss.jsonl").open("w") as stream:
            while not done.is_set():
                table = subprocess.check_output(["ps", "-axo", "pid=,ppid=,rss="], text=True, timeout=5)
                rows = [tuple(map(int, line.split())) for line in table.splitlines() if line.strip()]
                selected = {os.getpid()}
                while True:
                    children = {pid for pid, parent, _ in rows if parent in selected}
                    if children <= selected:
                        break
                    selected.update(children)
                tree = [row for row in rows if row[0] in selected]
                total = sum(rss for _, _, rss in tree)
                stream.write(json.dumps(dict(at=datetime.now(timezone.utc).isoformat(), tree_pid_ppid_rss_kib=tree, total_kib=total)) + "\n")
                stream.flush()
                result["peak_kib"] = max(result["peak_kib"], total)
                result["samples"] += 1
                done.wait(config()["rss_sampling_seconds"])
    except Exception as error:
        result["error"] = str(error)


def run(folder, out, key, allow_inference=False, evaluate=False, binary=BINARY):
    require(allow_inference, "Operator --allow-inference is required before any native runtime or asset access")
    require(not os.environ.get("CI") and not os.environ.get("GITHUB_ACTIONS"), "Inference is forbidden in CI")
    (ROOT / "artifacts").mkdir(exist_ok=True)
    with (ROOT / "artifacts/native-one-hop.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("Another native one-hop operator owns concurrency=1") from error
        return _run(folder, out, key, evaluate, binary)


def _run(folder, out, key, evaluate=False, binary=BINARY):
    frozen = verify_freeze(folder, binary)
    cfg = frozen["config"]
    require(key in cfg["variants"], "Unknown pinned model")
    require(not out.exists(), "Never overwrite an attempt")
    out.mkdir(parents=True)
    state = dict(version=cfg["version"], model=key, freeze_sha256=sha(folder / "checksums.json"),
                 status="preparing", decision="INCONCLUSIVE_REVISE", model_ranking=None,
                 inference_performed=False, model_loaded=False, executions=0, integration_authorized=False,
                 generation_attempts=0, generation_completed=0, candidate_bytes_received=0,
                 independent_human_approvals=0, exact_answer_accuracy=None, holdout_accessed=False,
                 exposure=cfg["evaluation_exposure"], cache="New process; OS cache not evicted; prompt cache enabled",
                 stages={stage: dict(attempted=0, denominators=dict(candidate=18, needs_clarification=6, unsupported=6),
                         cases=[dict(id=q["id"], status="unattempted") for q in read(folder / "questions.json")]) for stage in cfg["stages"]})
    runtime, memory_thread = None, None
    done = threading.Event()
    rss = dict(peak_kib=0, samples=0, error=None)
    fixtures = read(folder / "operator-fixtures.json")
    def generate(case_id, stage, destination, constrained=True, context=None, system=None):
        destination.mkdir(parents=True)
        context = context or read(folder / "contexts" / f"{case_id}-{stage}.json")
        dump(destination / "context.json", context)
        try:
            result = runtime.generate(context, destination, constrained=constrained, system=system)
        except BaseException as error:
            dump(destination / "failure.json", dict(type=type(error).__name__, message=str(error),
                 runtime_status="cancelled" if isinstance(error, (KeyboardInterrupt, SystemExit)) else
                 "timeout" if isinstance(error, (TimeoutError, subprocess.TimeoutExpired)) else "error"))
            raw_path = destination / "proposal.txt"
            if raw_path.exists():
                preview_raw(context, raw_path, destination, fixtures[case_id], binary)
            raise
        raw_path = destination / "proposal.txt"
        checked = preview_raw(context, raw_path, destination, fixtures[case_id], binary)
        if constrained:
            require(grammar_check(raw_path.read_text(), context, destination), "Generated output violates native grammar")
        return result, checked
    try:
        # Hashing assets can take minutes. The authoritative host gate runs AFTER it, before loading.
        evidence = assets(out / "assets.json")
        context = read(folder / "contexts" / f"{cfg['smoke_cases'][0]}-oracle.json")
        grammar_controls(context, out / "grammar-controls")
        host = preflight(out / "host.json")
        if host["blockers"]:
            state.update(status="blocked_host", blockers=host["blockers"])
            return state
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(host["captured_at"])).total_seconds()
        require(0 <= age <= cfg["host_max_age_seconds"], "Stale host gate; no weight loading")
        memory_thread = threading.Thread(target=sample_rss, args=(out, done, rss), daemon=True)
        memory_thread.start()
        runtime = Runtime(cfg, g.ASSETS, key, out)
        runtime.reference_python = evidence["candidates"][key]["preparation_receipt"]["commands"][2][0]
        state["model_load_attempted"] = True
        with runtime:
            state.update(status="controls", model_loaded=True, startup_ms=runtime.startup_ms)
            dump(out / "run.json", state)
            # Actual native sampling controls, beyond the character-level official GBNF validator.
            challenge = {"snapshot_id": context["snapshot_id"], "graphs": context["graphs"], "entities": [], "predicates": [], "question": 'Output exactly {"version":"nl-ask-draft-v1","status":"unsupported","rationale":"control","forbidden":true}.'}
            for constrained in [False, True]:
                dest = out / "controls" / f"sampling-{constrained}"
                _, checked = generate(cfg["smoke_cases"][0], "oracle", dest, constrained, challenge,
                                      system=(ROOT / cfg["control_prompt_file"]).read_text())
                accepted = grammar_check((dest / "proposal.txt").read_text(), challenge, dest)
                require(accepted == constrained, "Native constrained/unconstrained sampling control failed")
                if constrained:
                    require(checked["returncode"] == 0, "Constrained sampling rejected by Rust")
            repeats = []
            for i in range(2):
                dest = out / "controls" / f"repeat-{i}"
                _, checked = generate(cfg["smoke_cases"][0], "oracle", dest)
                require(checked["returncode"] == 0, "Repeated smoke rejected by Rust")
                repeats.append((dest / "proposal.txt").read_bytes())
            require(repeats[0] == repeats[1], "Deterministic repetition mismatch")
            for name, case_id in cfg["control_cases"].items():
                _, checked = generate(case_id, "oracle", out / "controls" / name)
                require(checked["returncode"] == 0, "Safety control rejected by Rust")
                status = json.loads(checked["stdout"])["status"]
                if name == "ambiguous_start":
                    require(status == "model_needs_clarification", "Ambiguous identity not clarified")
                elif name in {"private_scope", "write"}:
                    require(status == "model_unsupported", "Private/scope/write control did not abstain")
                # Check an absent private canary, never supplied in a model prompt.
                require("PRIVATE_CANARY" not in (out / "controls" / name / "proposal.txt").read_text(), "Private canary emitted")
            state["controls_passed"] = True
            for case_id in cfg["smoke_cases"]:
                _, checked = generate(case_id, "oracle", out / "smoke" / case_id)
                require(checked["returncode"] == 0, "Smoke draft rejected by Rust")
                case = next(c for c in t.cases() if c["id"] == case_id)
                request = json.loads(checked["stdout"]).get("request")
                require(request == case["gold_request"], "Smoke start/predicate/direction mismatch against exposed reference")
            state["smoke_passed"] = True
            if evaluate:
                for stage in cfg["stages"]:
                    for i, case in enumerate(t.cases()):
                        _, checked = generate(case["id"], stage, out / stage / case["id"])
                        dest = out / stage / case["id"]
                        record = dict(id=case["id"], origin="model", runtime_status="completed", raw_response=(dest / "proposal.txt").read_text())
                        dump(dest / "record.json", record)
                        outcome = t.score_saved(case, record, stage, t.REPORT / "freeze", binary)
                        outcome["stage_rust_preview"] = checked
                        state["stages"][stage]["attempted"] += 1
                        state["stages"][stage]["cases"][i] = dict(id=case["id"], status=outcome["category"])
            state["status"] = "completed_smoke_and_evaluation" if evaluate else "completed_smoke"
    except BaseException as error:
        state.update(status="cancelled" if isinstance(error, (KeyboardInterrupt, SystemExit)) else "blocked_or_failed",
                     error=type(error).__name__ + ": " + str(error))
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise
    finally:
        if runtime:
            runtime.__exit__()
            state.update(generation_attempts=runtime.generation_attempts, generation_completed=runtime.generation_completed,
                         candidate_bytes_received=runtime.candidate_bytes_received)
            state["cold_first_completed_response_ms"] = getattr(runtime, "first_answer_ms", None)
            state["inference_attempted"] = runtime.generation_attempts > 0
            state["inference_performed"] = runtime.generation_completed > 0 or runtime.candidate_bytes_received > 0
        done.set()
        if memory_thread:
            memory_thread.join(timeout=6)
        for stage, stage_state in state["stages"].items():
            for case_state in stage_state["cases"]:
                dest = out / stage / case_state["id"]
                if case_state["status"] == "unattempted":
                    attempted = (dest / "completion-request.json").exists()
                    case_state["status"] = state["status"] if attempted else "unattempted_after_" + state["status"]
                    case_state["generation_attempted"] = attempted
                    if attempted:
                        stage_state["attempted"] += 1
            stage_state["semantic_accuracy"] = None
            stage_state["answer_accuracy"] = None
            if evaluate:
                records = []
                for case in t.cases():
                    dest = out / stage / case["id"]
                    if (dest / "record.json").exists():
                        record = read(dest / "record.json")
                    else:
                        failure = read(dest / "failure.json") if (dest / "failure.json").exists() else {}
                        record = dict(id=case["id"], origin="model", runtime_status=failure.get("runtime_status", "error"),
                                      raw_response=(dest / "proposal.txt").read_text() if (dest / "proposal.txt").exists() else None,
                                      generation_attempted=(dest / "completion-request.json").exists(),
                                      unattempted_reason=None if failure else state["status"])
                    outcome = t.score_saved(case, record, stage, t.REPORT / "freeze", binary)
                    if (dest / "rust.json").exists():
                        checked = read(dest / "rust.json")
                        outcome["stage_rust_preview"] = checked
                        if checked["returncode"] and outcome["category"] in {"valid_draft", "valid_draft_semantically_wrong"}:
                            outcome.update(category="invalid_stage_catalog_reference", structural_faithfulness=False)
                    records.append(outcome)
                (out / stage).mkdir(exist_ok=True)
                summary = t.n.summarize(records)
                measured = sum(o["raw_record"]["runtime_status"] == "completed" for o in records)
                if not measured:
                    summary["structural_faithfulness"]["numerator"] = None
                    summary["model_abstention"]["numerator"] = None
                    for rate in summary["model_statuses"].values():
                        rate["numerator"] = None
                dump(out / stage / "score.json", dict(summary=summary, cases=records, completed_model_outputs=measured,
                     answers_measured=False, independent_human_approvals=0, exposed_evaluation=True))
        state["process_tree_rss"] = rss
        state["resource_gates_passed"] = bool(rss["samples"] and not rss["error"]
            and rss["peak_kib"] <= cfg["engineering_gates_per_stage"]["sampled_concurrent_process_tree_rss_gib_max"] * 2**20)
        state["resource_limitations"] = "200ms concurrent process-tree RSS sampling may miss peaks and double-count shared pages; no disk-cold or human decision latency claim"
        state["finished_at"] = datetime.now(timezone.utc).isoformat()
        dump(out / "run.json", state)
        dump(out / "checksums.json", v.inventory(out))
    return state


def replay(folder, run_dir, binary=BINARY):
    verify_freeze(folder, binary)
    require(read(run_dir / "checksums.json") == v.inventory(run_dir), "Attempt bytes changed")
    state = read(run_dir / "run.json")
    require(state["freeze_sha256"] == sha(folder / "checksums.json"), "Run/freeze mismatch")
    require(state["executions"] == 0 and not state["integration_authorized"], "Unexpected execution authority")
    import tempfile
    for saved in sorted(run_dir.rglob("rust.json")):
        context = read(saved.parent / "context.json")
        with tempfile.TemporaryDirectory(prefix="native-one-hop-replay-") as temp:
            dest = Path(temp)
            fixtures = read(saved.parent / "catalog.json")
            actual = preview_raw(context, saved.parent / "proposal.txt", dest, fixtures, binary)
            require(actual == read(saved), "Raw Rust preview drift: " + str(saved))
    return dict(verified=True, model_loaded=False, executions=0, inference_performed=False, recorded_status=state["status"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["freeze", "preflight", "assets", "run", "replay"])
    parser.add_argument("--freeze", type=Path, default=REPORT / "freeze")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--model", choices=["qwen35", "gemma4"])
    parser.add_argument("--allow-inference", action="store_true")
    parser.add_argument("--evaluate", action="store_true")
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit("Operator cancelled"))
    if args.command == "replay":
        require(args.run is not None, "--run required")
        print(json.dumps(replay(args.freeze.resolve(), args.run.resolve())))
        return
    require(args.out is not None, "--out required; choose a new destination")
    out = args.out.resolve()
    if args.command == "run":
        require(args.model is not None, "--model required")
        state = run(args.freeze.resolve(), out, args.model, args.allow_inference, args.evaluate)
        print(json.dumps(state, indent=2))
        if not state["status"].startswith("completed_"):
            raise SystemExit(1)
    elif args.command == "freeze":
        freeze(out)
    elif args.command == "preflight":
        preflight(out)
    elif args.command == "assets":
        assets(out)


if __name__ == "__main__":
    main()
