"""#122: Model-free tests of real #119 documents and guarded local completion."""
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

import document_rag as docs
import grounded_rag as existing
import local_cited_generation as local


class LocalGenerationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="verity-local-answer-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.no = self.root / "frister.md"
        self.en = self.root / "policy.txt"
        self.private = self.root / "private.txt"
        self.no.write_text(
            "Søknadsfristen er 1. mai. Kontoret ligger i Oslo.\n", encoding="utf-8")
        self.en.write_text(
            "The application deadline is June 3. Applications go to Tromsø.\n",
            encoding="utf-8")
        self.private.write_text("PRIVATE_CANARY Do not reveal this.\n", encoding="utf-8")
        self.manifest = self.root / "sources.json"
        self.index = self.root / "index.json"
        records = []
        for ident, path, language, scope in (
            ("norwegian", self.no, "nb", "public"),
            ("english", self.en, "en", "public"),
            ("private", self.private, "en", "secret"),
        ):
            records.append({
                "id": ident, "path": path.name, "sha256": docs.sha(path.read_bytes()),
                "language": language, "license": "CC-BY-4.0", "scope": scope,
            })
        self.manifest.write_text(json.dumps({"version": 1, "documents": records}))
        docs.write_index(self.index, docs.make_index(self.manifest, "public"),
                         self.manifest)
        self.registration = self.root / "registration.json"
        self.authorization = self.root / "run-authorization.json"
        self.ledger = self.root / "run-ledger"
        self.ledger.mkdir(mode=0o700)
        self.binary = self.root / "llama-server"
        self.model = self.root / "small-model.gguf"
        self.binary.write_bytes(b"test-fake-runtime-not-executable")
        self.model.write_bytes(b"GGUF mock model -- no actual model loaded")
        self.template = self.root / "chat.jinja"
        self.tokenizer_config = self.root / "tokenizer_config.json"
        self.tokenizer = self.root / "tokenizer.json"
        self.template.write_text("SYNTHETIC template, not a usable model template")
        self.tokenizer_config.write_text(json.dumps({"chat_template": self.template.read_text()}))
        self.tokenizer.write_text('{"synthetic":true}')
        self.reg = {
            "version": 2, "backend": local.BACKEND,
            "host": "127.0.0.1", "port": 8095, "model_name": "graph-verity-test",
            "model_path": str(self.model), "model_sha256": docs.sha(self.model.read_bytes()),
            "runtime_path": str(self.binary),
            "runtime_sha256": docs.sha(self.binary.read_bytes()),
            "system_prompt_sha256": docs.sha(local.SYSTEM_INSTRUCTION.encode()),
            "context_tokens": 8192, "max_output_tokens": 128,
            "timeout_seconds": 10, "temperature": 0, "seed": 7,
            "cpu_threads": 4, "gpu_layers": 0, "server_pid": 424242,
            "server_started": "synthetic-process-start",
            "runtime_revision": "a" * 40, "model_revision": "b" * 40,
            "gguf_revision": "c" * 40,
            "chat_template_path": str(self.template),
            "chat_template_sha256": docs.sha(self.template.read_bytes()),
            "tokenizer_config_path": str(self.tokenizer_config),
            "tokenizer_config_sha256": docs.sha(self.tokenizer_config.read_bytes()),
            "tokenizer_path": str(self.tokenizer),
            "tokenizer_sha256": docs.sha(self.tokenizer.read_bytes()),
        }
        self.registration.write_text(json.dumps(self.reg))
        # Synthetic host evidence is isolated from the production admission path.
        self.host = dict(hardware="Apple M1 Pro", ram_bytes=str(32 * 1024**3),
                         swap_used_mib=0, memory_free_percent=75,
                         process_inventory="observed", competing_model_processes=[],
                         server_started=self.reg["server_started"],
                         server_command=" ".join(local.server_command(self.reg)),
                         listener="p424242\nn127.0.0.1:8095",
                         processes=[dict(pid=424242, rss_kib=1024)], load_per_cpu=0.1)
        self.observe_host = local.host_observation
        self.memory_class = local.RunMemory
        patcher = patch.object(local, "host_observation", return_value=self.host)
        patcher.start()
        self.addCleanup(patcher.stop)
        memory = Mock(exceeded=False, metrics={"samples": 1, "error": None, "measurement": "synthetic test fixture"})
        patcher = patch.object(local, "RunMemory", return_value=memory)
        patcher.start()
        self.addCleanup(patcher.stop)

    def packet(self, language="en"):
        question = ("What is the application deadline?" if language == "en"
                    else "Hva er søknadsfristen?")
        return existing.retrieve(self.manifest, self.index, "public",
                                 question, language, 3)

    def candidate(self, packet):
        text = ("The application deadline is June 3." if packet["language"] == "en"
                else "Søknadsfristen er 1. mai.")
        target = next(item for item in packet["document_evidence"]
                      if text in item["text"])
        return {"version": local.VERSION, "status": "answer",
                "language": packet["language"], "answer": text,
                "citation_id": target["citation_id"]}

    def approve(self, packet, *, ident="operator-test-run-1"):
        self.reg["port"] = self.reg.get("port", 8095)
        self.registration.write_text(json.dumps(self.reg))
        auth = {
            "version": 1, "authorization_id": ident,
            "action": "one_shot_local_document_answer",
            "registration_sha256": local.fingerprint(self.reg),
            "packet_sha256": local.fingerprint(packet),
            "question_sha256": docs.sha(packet["question"].encode()),
            "scope": "public", "owner_approved": True, "owner_identity": "synthetic-test-owner",
            "trial_id": "synthetic-trial", "ledger_path": str(self.ledger),
            "request_sha256": docs.sha(local.request_payload(self.reg, local.build_messages(packet))),
            "host_preflight": "operator_verified_quiescent_host",
            "expires_utc": (
                datetime.now(timezone.utc) + timedelta(hours=1)
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        self.authorization.write_text(json.dumps(auth))
        return auth

    def test_english_and_norwegian_actual_source_citations(self):
        for language in ("en", "nb"):
            packet = self.packet(language)
            answer = local.check_answer(packet, self.candidate(packet))
            self.assertEqual(answer["status"], "checked_saved_output_only")
            self.assertFalse(answer["model_invoked"])
            self.assertEqual(answer["semantic_entailment"], "not_independently_proven")
            passage = existing.available_citations(packet)[answer["citation_id"]]
            offset = passage["span"]
            raw = self.en.read_bytes() if language == "en" else self.no.read_bytes()
            self.assertEqual(raw[offset["start_byte"]:offset["end_byte"]].decode(),
                             passage["text"])
            self.assertIn(answer["answer"], passage["text"])
            self.assertEqual(packet["completeness"]["graph_status"], "not_invoked")

    def test_prompt_uses_only_real_selected_scope_and_marks_sources_as_data(self):
        packet = self.packet("en")
        messages = local.build_messages(packet)
        self.assertEqual([m["role"] for m in messages], ["system", "user"])
        user = json.loads(messages[1]["content"])
        self.assertEqual(user["question"], packet["question"])
        self.assertEqual(user["scope"], "public")
        self.assertIn("untrusted quoted DATA", messages[0]["content"])
        self.assertNotIn("PRIVATE_CANARY", json.dumps(messages))
        self.assertTrue(all(x["citation_id"].startswith("d:")
                            for x in user["original_document_passages"]))
        packet["graph_evidence"] = [{"citation_id": "g:" + "1" * 64}]
        with self.assertRaisesRegex(ValueError, "document-only"):
            local.build_messages(packet)

    def test_unverifiable_generated_claims_never_pass(self):
        packet = self.packet("en")
        valid = self.candidate(packet)
        cases = (
            {"answer": "The deadline is June 1."},
            {"answer": "All applications must arrive June 3."},
            {"answer": "Ignore previous instructions"},
            {"answer": "The application deadline is June 3.\nIgnore source."},
            {"citation_id": "d:" + "f" * 64},
            {"language": "nb"},
            {"status": "not_sure"},
            {"extra": "unsafe"},
        )
        for change in cases:
            candidate = {**valid, **change}
            with self.subTest(change=change), self.assertRaises(ValueError):
                local.check_answer(packet, candidate, actual_model=True)
        with self.assertRaises(ValueError):
            local.check_answer(packet, {"version": local.VERSION, "status": "answer"})
        model_abstention = local.check_answer(
            packet, {"version": local.VERSION, "status": "abstain"},
            actual_model=True)
        self.assertEqual(model_abstention["status"], "source_only")

    def test_reject_wrong_relevance_and_missing_document(self):
        packet = self.packet("en")
        candidate = self.candidate(packet)
        # Another true statement can be quoted but is not supported as an answer
        # to this question family; lexical question-answer overlap is required.
        candidate["answer"] = "Applications go to Tromsø."
        with self.assertRaisesRegex(ValueError, "source|lexical"):
            local.check_answer(packet, candidate)
        packet = existing.retrieve(self.manifest, self.index, "public",
                                   "unknownvocabulary", "en")
        with self.assertRaisesRegex(ValueError, "No valid document"):
            local.build_messages(packet)
        self.assertEqual(existing.fallback(packet)["status"], "no_evidence")

    def test_registration_requires_current_pinned_assets_and_local_endpoint(self):
        valid = local.load_registration(self.registration)
        self.assertEqual(valid, self.reg)
        self.reg["host"] = "example.org"
        self.registration.write_text(json.dumps(self.reg))
        with self.assertRaisesRegex(ValueError, "local endpoint"):
            local.load_registration(self.registration)
        self.reg["host"] = "127.0.0.1"
        self.reg["runtime_sha256"] = "sha256:" + "f" * 64
        self.registration.write_text(json.dumps(self.reg))
        with self.assertRaisesRegex(ValueError, "runtime asset"):
            local.load_registration(self.registration)
        self.reg["runtime_sha256"] = docs.sha(self.binary.read_bytes())
        self.reg["temperature"] = 1
        self.registration.write_text(json.dumps(self.reg))
        with self.assertRaisesRegex(ValueError, "decoding"):
            local.load_registration(self.registration)

    def test_one_shot_owner_authorization_precedes_transport(self):
        packet = self.packet("en")
        self.approve(packet)
        transport = Mock(return_value=self.candidate(packet))
        response = local.attempt_generation(
            packet, self.manifest, self.index, "public",
            self.registration, self.authorization, self.ledger,
            transport=transport)
        self.assertEqual(response["status"], "generated_checked_extractive")
        self.assertTrue(response["model_request_attempted"])
        self.assertEqual(response["registered_model_alias"], "graph-verity-test")
        self.assertEqual(transport.call_count, 1)
        receipts = list(self.ledger.glob("*.consumed.json"))
        self.assertEqual(len(receipts), 1)
        self.assertIn("consumed_before_any_inference", receipts[0].read_text())
        with self.assertRaises(FileExistsError):
            local.attempt_generation(
                packet, self.manifest, self.index, "public",
                self.registration, self.authorization, self.ledger,
                transport=transport)
        self.assertEqual(transport.call_count, 1)

    def test_wrong_binding_stale_expiry_and_no_approval_never_contact_model(self):
        packet = self.packet("en")
        self.approve(packet)
        transport = Mock(return_value=self.candidate(packet))
        authorization = json.loads(self.authorization.read_text())
        for field, value in (
            ("question_sha256", docs.sha(b"forged question")),
            ("packet_sha256", docs.sha(b"forged evidence")),
            ("registration_sha256", docs.sha(b"forged checkpoint")),
            ("request_sha256", docs.sha(b"changed request")),
            ("ledger_path", str(self.root / "another-ledger")),
            ("owner_approved", False),
            ("host_preflight", "unavailable"),
            ("expires_utc", "2020-01-01T00:00:00Z"),
        ):
            changed = {**authorization, field: value}
            self.authorization.write_text(json.dumps(changed))
            with self.subTest(field=field), self.assertRaises(ValueError):
                local.attempt_generation(
                    packet, self.manifest, self.index, "public",
                    self.registration, self.authorization, self.ledger,
                    transport=transport)
        self.assertEqual(transport.call_count, 0)
        self.assertEqual(list(self.ledger.glob("*.consumed.json")), [])
        self.assertEqual(len(list(self.ledger.glob("run-*/receipt.json"))), 8)

    def test_transport_error_and_unsupported_generated_answer_fall_back(self):
        packet = self.packet()
        self.approve(packet, ident="fail-transport")
        answer = local.attempt_generation(
            packet, self.manifest, self.index, "public",
            self.registration, self.authorization, self.ledger,
            transport=Mock(side_effect=TimeoutError("no response")))
        self.assertEqual(answer["status"], "source_only")
        self.assertEqual(answer["reason"], "inference_or_grounding_failed")
        self.assertTrue(answer["model_request_attempted"])
        self.approve(packet, ident="wrong-answer")
        invalid = {**self.candidate(packet), "answer": "The deadline is fabricated"}
        result = local.attempt_generation(
            packet, self.manifest, self.index, "public",
            self.registration, self.authorization, self.ledger,
            transport=Mock(return_value=invalid))
        self.assertEqual(result["status"], "source_only")
        self.assertTrue(result["model_request_attempted"])

    def test_source_change_during_completion_cannot_be_returned_as_answer(self):
        packet = self.packet()
        self.approve(packet)
        def change_then_answer(reg, messages):
            self.en.write_text("Changed while inference was running.", encoding="utf-8")
            return self.candidate(packet)
        result = local.attempt_generation(
            packet, self.manifest, self.index, "public",
            self.registration, self.authorization, self.ledger,
            transport=change_then_answer)
        self.assertEqual(result["status"], "source_unavailable")
        self.assertEqual(result["reason"], "source_changed_during_inference")
        self.assertEqual(result["evidence"], [])
        self.assertIsNone(result["answer"])

    def test_real_loopback_http_contract_uses_fake_server_only(self):
        packet = self.packet("en")
        expected = self.candidate(packet)
        captured = []
        class MockHandler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers["Content-Length"])
                request = json.loads(self.rfile.read(length))
                captured.append({"path": self.path, "payload": request})
                payload = json.dumps({
                    "model": "graph-verity-test",
                    "choices": [{
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": json.dumps(expected)},
                    }],
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            def log_message(self, *args):
                pass
        server = http.server.HTTPServer(("127.0.0.1", 0), MockHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close(), thread.join()))
        reg = {**self.reg, "port": server.server_port}
        returned = local.request_local_completion(reg, local.build_messages(packet))
        self.assertEqual(returned, expected)
        self.assertEqual(captured[0]["path"], "/v1/chat/completions")
        self.assertEqual(captured[0]["payload"]["temperature"], 0)
        self.assertFalse(captured[0]["payload"]["stream"])
        self.assertEqual(captured[0]["payload"]["model"], "graph-verity-test")

    def http_reply(self, body, *, status=200, headers=None, error=None):
        response = Mock(status=status)
        safe_headers = {"Content-Length": str(len(body)), "Content-Type": "application/json"}
        safe_headers.update(headers or {})
        response.getheader.side_effect = lambda key, default=None: safe_headers.get(key, default)
        response.read1.side_effect = [body, error] if error else [body, b""]
        connection = Mock()
        connection.getresponse.return_value = response
        return connection

    def envelope(self, candidate=None, *, alias="graph-verity-test", finish="stop"):
        return json.dumps({"model": alias, "usage": {"prompt_tokens": 200, "completion_tokens": 40},
                           "choices": [{"finish_reason": finish,
                                        "message": {"content": json.dumps(candidate or self.candidate(self.packet()))}}]}).encode()

    def run_http_fixture(self, connection, ident):
        self.approve(self.packet(), ident=ident)
        with patch.object(local.http.client, "HTTPConnection", return_value=connection):
            result = local.attempt_generation(
                self.packet(), self.manifest, self.index, "public", self.registration,
                self.authorization, self.ledger)
        run = Path(result["receipt_directory"])
        return result, run, json.loads((run / "receipt.json").read_bytes())

    def test_native_http_receipts_retain_success_and_rejected_bytes(self):
        cases = [
            ("good", self.envelope(), 200, {}, None, "generated_checked_extractive"),
            ("bad-json", b"not JSON", 200, {}, None, "source_only"),
            ("wrong-alias", self.envelope(alias="other-model"), 200, {}, None, "source_only"),
            ("truncated", self.envelope(finish="length"), 200, {}, None, "source_only"),
            ("disconnect", b'{"partial":', 200, {"Content-Length": "999"}, None, "source_only"),
            ("timeout", b'{"partial":', 200, {}, TimeoutError("synthetic timeout"), "source_only"),
            ("unavailable", b"server unavailable", 503, {}, None, "source_only"),
            ("oversized", b"x" * (local.MAX_COMPLETION_BYTES + 1), 200, {}, None, "source_only"),
            ("unsupported", self.envelope({**self.candidate(self.packet()), "answer": "Fabricated deadline."}),
             200, {}, None, "source_only"),
            ("fake-citation", self.envelope({**self.candidate(self.packet()), "citation_id": "d:" + "0" * 64}),
             200, {}, None, "source_only"),
            ("abstain", self.envelope({"version": local.VERSION, "status": "abstain"}),
             200, {}, None, "source_only"),
        ]
        for number, (ident, body, status, headers, error, expected) in enumerate(cases, 1):
            with self.subTest(ident=ident):
                conn = self.http_reply(body, status=status, headers=headers, error=error)
                result, run, receipt = self.run_http_fixture(conn, ident)
                self.assertEqual(result["status"], expected)
                self.assertEqual((run / "response.bin").read_bytes(), body[:local.MAX_COMPLETION_BYTES])
                self.assertTrue(receipt["model_request_attempted"])
                self.assertEqual(receipt["http_status"], status)
                self.assertEqual(receipt["final_view"], result)
                self.assertEqual(len(list(self.ledger.glob("*.consumed.json"))), number)
                prepared = json.loads((run / "prepared.json").read_bytes())
                self.assertEqual(prepared["request_sha256"], docs.sha((run / "request.json").read_bytes()))
                self.assertEqual(prepared["packet_sha256"], local.fingerprint(self.packet()))
                if expected == "generated_checked_extractive":
                    self.assertEqual(receipt["finish_reason"], "stop")
                    self.assertEqual(receipt["token_usage"]["completion_tokens"], 40)
                elif ident != "abstain":
                    self.assertIsNotNone(receipt["error"])
                for item in run.iterdir():
                    self.assertEqual(item.stat().st_mode & 0o777, 0o600)
                self.assertEqual(run.stat().st_mode & 0o777, 0o700)
                before = (run / "receipt.json").read_bytes()
                with self.assertRaises(FileExistsError):
                    local._private_write(run / "receipt.json", b"overwrite")
                self.assertEqual((run / "receipt.json").read_bytes(), before)

    def test_context_assets_and_runtime_controls_fail_closed(self):
        for field, wrong in (
            ("model_sha256", "sha256:" + "0" * 64),
            ("runtime_sha256", "sha256:" + "0" * 64),
            ("system_prompt_sha256", "sha256:" + "0" * 64),
            ("chat_template_sha256", "sha256:" + "0" * 64),
            ("tokenizer_sha256", "sha256:" + "0" * 64),
            ("cpu_threads", 8), ("gpu_layers", 1), ("version", 1),
        ):
            with self.subTest(field=field):
                self.registration.write_text(json.dumps({**self.reg, field: wrong}))
                with self.assertRaises(ValueError):
                    local.load_registration(self.registration)
        bad = {**self.reg, "context_tokens": 512}
        with self.assertRaisesRegex(ValueError, "Context"):
            local.request_payload(bad, local.build_messages(self.packet()))
        self.template.write_text("changed")
        self.reg["chat_template_sha256"] = docs.sha(self.template.read_bytes())
        self.registration.write_text(json.dumps(self.reg))
        with self.assertRaisesRegex(ValueError, "Template differs"):
            local.load_registration(self.registration)

    def test_failed_host_or_missing_authorization_has_private_unattempted_receipt(self):
        packet = self.packet()
        self.approve(packet)
        with patch.object(local, "admit_host", side_effect=ValueError("synthetic host failure")):
            with self.assertRaisesRegex(ValueError, "host failure"):
                local.attempt_generation(packet, self.manifest, self.index, "public", self.registration,
                                         self.authorization, self.ledger)
        self.authorization.unlink()
        with self.assertRaises(ValueError):
            local.attempt_generation(packet, self.manifest, self.index, "public", self.registration,
                                     self.authorization, self.ledger)
        receipts = list(self.ledger.glob("run-*/receipt.json"))
        self.assertEqual(len(receipts), 2)
        self.assertFalse(any(json.loads(p.read_text())["model_request_attempted"] for p in receipts))
        self.assertEqual(list(self.ledger.glob("*.consumed.json")), [])
        self.approve(packet)
        auth = json.loads(self.authorization.read_text())
        self.authorization.write_text(json.dumps({**auth, "scope": "secret"}))
        with self.assertRaisesRegex(ValueError, "bind"):
            local.attempt_generation(packet, self.manifest, self.index, "public", self.registration,
                                     self.authorization, self.ledger)

    def test_runtime_host_observations_are_separate_from_model_alias(self):
        local.admit_host(self.reg, self.host)
        for field, value in (("server_started", "new process"), ("listener", None),
                             ("server_command", "other runtime"), ("swap_used_mib", "unmeasured"),
                             ("memory_free_percent", 10), ("competing_model_processes", ["ollama"]),
                             ("process_inventory", "unmeasured"), ("load_per_cpu", 2)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                local.admit_host(self.reg, {**self.host, field: value})
        conn = self.http_reply(self.envelope())
        conn.connect.side_effect = ConnectionRefusedError("synthetic server unavailable")
        result, run, receipt = self.run_http_fixture(conn, "connection-refused")
        self.assertEqual(result["status"], "source_only")
        self.assertFalse(receipt["request_send_attempted"])
        self.assertEqual((run / "response.bin").read_bytes(), b"")

    def test_ledger_must_be_private_and_non_symlink(self):
        self.approve(self.packet())
        self.ledger.chmod(0o755)
        with self.assertRaisesRegex(ValueError, "private"):
            local.attempt_generation(self.packet(), self.manifest, self.index, "public",
                                     self.registration, self.authorization, self.ledger)
        self.ledger.chmod(0o700)
        alias = self.root / "ledger-link"
        alias.symlink_to(self.ledger, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "private"):
            local.attempt_generation(self.packet(), self.manifest, self.index, "public",
                                     self.registration, self.authorization, alias)


    def test_process_tree_samples_and_missing_metrics_are_honest(self):
        memory = self.memory_class(42)
        def sample(args):
            memory.done.set()
            return "42 1 100\n43 42 200\n99999 1 900"
        with patch.object(local, "_command", side_effect=sample):
            memory.sample()
        self.assertEqual(memory.metrics["model_peak_rss_kib"], 100)
        self.assertEqual(memory.metrics["model_tree_peak_rss_kib"], 300)
        self.assertEqual(memory.metrics["total_tree_peak_rss_kib"], 300)
        memory = self.memory_class(42)
        def missing(args):
            memory.done.set()
            return None
        with patch.object(local, "_command", side_effect=missing):
            memory.sample()
        self.assertEqual(memory.metrics["model_peak_rss_kib"], "unmeasured")
        self.assertIsNotNone(memory.metrics["error"])
        memory = self.memory_class(42)
        memory.abort = Mock()
        def huge(args):
            memory.done.set()
            return "42 1 9000000"
        with patch.object(local, "_command", side_effect=huge):
            memory.sample()
        self.assertTrue(memory.exceeded)
        memory.abort.assert_called_once()

    def test_host_measurements_unavailable_are_not_reported_as_zero(self):
        with patch.object(local, "_command", return_value=None):
            host = self.observe_host(self.reg)
        self.assertEqual(host["swap_used_mib"], "unmeasured")
        self.assertEqual(host["memory_free_percent"], "unmeasured")
        self.assertEqual(host["process_inventory"], "unmeasured")
        with self.assertRaises(ValueError):
            local.admit_host(self.reg, host)

    def test_source_changed_during_failed_http_retains_raw_but_suppresses_sources(self):
        self.approve(self.packet(), ident="changed-failed-http")
        conn = self.http_reply(b"invalid-json")
        def edited():
            self.en.write_text("Source revoked during request.")
            return conn.getresponse.return_value
        conn.getresponse.side_effect = edited
        with patch.object(local.http.client, "HTTPConnection", return_value=conn):
            result = local.attempt_generation(self.packet(), self.manifest, self.index, "public",
                                             self.registration, self.authorization, self.ledger)
        self.assertEqual(result["status"], "source_unavailable")
        self.assertEqual(result["evidence"], [])
        self.assertEqual((Path(result["receipt_directory"]) / "response.bin").read_bytes(), b"invalid-json")


    def test_authorization_expiring_during_preflight_is_not_consumed(self):
        self.approve(self.packet())
        def expire(reg):
            auth = json.loads(self.authorization.read_text())
            self.authorization.write_text(json.dumps({**auth, "expires_utc": "2020-01-01T00:00:00Z"}))
            return self.host
        with patch.object(local, "host_observation", side_effect=expire):
            with self.assertRaisesRegex(ValueError, "stale"):
                local.attempt_generation(self.packet(), self.manifest, self.index, "public",
                                         self.registration, self.authorization, self.ledger)
        self.assertEqual(list(self.ledger.glob("*.consumed.json")), [])

    def test_proposed_collection_is_pinned_and_bilingual_without_inference(self):
        root = Path(local.__file__).resolve().parents[1]
        source = root / "tests/fixtures/document-rag-native-v1/sources.json"
        proposal = json.loads((root / "configs/local-document-rag-native-v1.proposal.json").read_bytes())
        self.assertEqual(proposal["sources_manifest_sha256"], docs.sha(source.read_bytes()))
        self.assertFalse(proposal["inference_occurred"])
        index = self.root / "proposal-index.json"
        docs.write_index(index, docs.make_index(source, "development"), source)
        cases = json.loads((source.parent / "cases.json").read_bytes())
        for case in cases["cases"][:2]:
            packet = existing.retrieve(source, index, "development", case["question"], case["language"])
            passage = next(item for item in packet["document_evidence"]
                           if case["development_reference"] in item["text"])
            candidate = dict(version=local.VERSION, status="answer", language=case["language"],
                             answer=case["development_reference"], citation_id=passage["citation_id"])
            self.assertEqual(local.check_answer(packet, candidate)["status"], "checked_saved_output_only")
            self.assertIn("untrusted quoted DATA", local.build_messages(packet)[0]["content"])
        packet = existing.retrieve(source, index, "development", "xylophoniczebra?", "en")
        result = local.attempt_generation(packet, source, index, "development", self.registration,
                                         self.authorization, self.ledger)
        self.assertEqual(result["status"], "no_evidence")
        receipt = json.loads(next(self.ledger.glob("run-*/receipt.json")).read_bytes())
        self.assertFalse(receipt["model_request_attempted"])
        self.assertEqual(list(self.ledger.glob("*.consumed.json")), [])


    def test_resource_gaps_and_post_request_identity_changes_reject_answer(self):
        conn = self.http_reply(self.envelope())
        with patch.object(local, "RunMemory") as factory:
            factory.return_value.exceeded = False
            factory.return_value.metrics = {"samples": 0, "error": "unmeasured"}
            result, run, receipt = self.run_http_fixture(conn, "memory-gap")
        self.assertEqual(result["status"], "source_only")
        self.assertIn("sampling", receipt["error"]["message"])
        self.assertTrue((run / "response.bin").read_bytes())
        with patch.object(local, "host_observation", side_effect=[self.host, {**self.host, "server_started": "changed"}]):
            result, run, receipt = self.run_http_fixture(self.http_reply(self.envelope()), "pid-changed")
        self.assertEqual(result["status"], "source_only")
        self.assertIn("identity", receipt["error"]["message"])

    def test_cli_revocation_suppresses_outer_packet_too(self):
        output = io.StringIO()
        with patch.object(local, "attempt_generation", return_value={
                "status": "source_unavailable", "answer": None, "evidence": []}), redirect_stdout(output):
            local.main(["--manifest", str(self.manifest), "--index", str(self.index),
                        "--scope", "public", "--language", "en", "--question", self.packet()["question"],
                        "--runtime-registration", str(self.registration), "--run-authorization",
                        str(self.authorization), "--ledger-dir", str(self.ledger),
                        "--execute-authorized-inference"])
        self.assertIsNone(json.loads(output.getvalue())["packet"])


    def test_deadline_and_partial_read_failures_keep_received_bytes(self):
        conn = self.http_reply(b"partial", error=local.http.client.IncompleteRead(b"tail", 20))
        result, run, receipt = self.run_http_fixture(conn, "incomplete-chunk")
        self.assertEqual(result["status"], "source_only")
        self.assertEqual((run / "response.bin").read_bytes(), b"partialtail")
        self.assertEqual(receipt["body_read_error"], "incomplete_read")
        class ImmediateTimer:
            def __init__(self, delay, callback):
                self.callback = callback
            def start(self):
                self.callback()
            def cancel(self):
                pass
        with patch.object(local.threading, "Timer", ImmediateTimer):
            result, run, receipt = self.run_http_fixture(self.http_reply(self.envelope()), "whole-deadline")
        self.assertEqual(result["status"], "source_only")
        self.assertTrue(receipt["deadline_expired"])
        self.assertGreaterEqual(receipt["http_elapsed_ms"], 0)


    def test_cli_default_source_only_and_saved_replay_do_not_infer(self):
        cmd = [
            sys.executable, str(Path(local.__file__).resolve()),
            "--manifest", str(self.manifest), "--index", str(self.index),
            "--scope", "public", "--question", "What is the application deadline?",
            "--language", "en",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        view = json.loads(proc.stdout)["view"]
        self.assertEqual(view["status"], "source_only")
        self.assertFalse(view["model_invoked"])
        candidate_path = self.root / "saved.json"
        candidate_path.write_text(json.dumps(self.candidate(self.packet())))
        proc = subprocess.run(cmd + ["--saved-completion", str(candidate_path)],
                              capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        view = json.loads(proc.stdout)["view"]
        self.assertEqual(view["status"], "checked_saved_output_only")
        self.assertFalse(view["model_invoked"])
        proc = subprocess.run(cmd + ["--execute-authorized-inference"],
                              capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("registration", proc.stderr)


if __name__ == "__main__":
    unittest.main()
