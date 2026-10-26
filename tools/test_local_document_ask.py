"""Model-free API and browser tests for local document Ask."""
import base64
import http.client
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

import document_rag as documents
import local_document_ask as ask
import local_cited_generation as generation


FIXTURE = ask.ROOT / "tests/fixtures/document-rag-native-v1"
EN_QUESTION = "What does the default local answer mode display?"
NB_QUESTION = "Hva viser kildevisningen?"
CONFLICT_QUESTION = "What identifier does the CPU trial have?"


class LocalDocumentAsk(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="verity-local-document-ask-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.corpus = self.root / "corpus"
        shutil.copytree(FIXTURE, self.corpus)
        self.manifest = self.corpus / "sources.json"
        self.index = self.root / "index.json"
        documents.write_index(self.index, documents.make_index(self.manifest, "development"),
                              self.manifest)
        self.bundle = ask.Bundle(self.manifest, self.index, "development")
        self.server = ask.Server(self.bundle)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def post(self, route, payload, headers=None):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        request_headers = {
            "Origin": self.server.origin,
            "Authorization": "Bearer " + self.server.credential,
            "Content-Type": "application/json",
        }
        request_headers.update(headers or {})
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=5)
        connection.request("POST", route, body=body, headers=request_headers)
        response = connection.getresponse()
        result = response.status, response.read(), response.getheaders()
        connection.close()
        return result

    def ask(self, question, language="en"):
        status, body, _ = self.post(ask.PREFIX + "ask", {"question": question, "language": language})
        self.assertEqual(status, 200, body)
        return json.loads(body)

    def test_english_and_bokmal_source_only_show_original_citations(self):
        for question, language, expected, source_language in (
                (EN_QUESTION, "en", "The default local answer mode displays source passages.", "en"),
                (NB_QUESTION, "nb", "Kildevisningen viser originale dokumentutdrag.", "nb")):
            result = self.ask(question, language)
            self.assertEqual(result["view"]["status"], "source_only")
            self.assertEqual(result["view"]["reason"], "generation_not_authorized")
            self.assertIsNone(result["view"]["answer"])
            self.assertFalse(result["view"]["model_invoked"])
            self.assertEqual(result["execution"], "none")
            self.assertEqual(result["packet"]["graph_evidence"], [])
            passages = result["packet"]["document_evidence"]
            passage = next(item for item in passages if expected in item["text"])
            self.assertEqual(passage["language"], source_language)
            self.assertRegex(passage["citation_id"], r"^d:[0-9a-f]{64}$")
            self.assertEqual(passage["text"], self.source_bytes(passage)[
                passage["span"]["start_byte"]:passage["span"]["end_byte"]].decode("utf-8"))

    def source_bytes(self, passage):
        return (self.corpus / passage["source"]).read_bytes()

    def test_risk_cases_keep_sources_and_never_claim_a_generated_answer(self):
        cases = [
            ("What is the identifier?", "en", "AMBIGUOUS", "ambiguous_question"),
            ("What is the measured startup latency?", "en", "INSUFFICIENT_EVIDENCE", "insufficient_source_support"),
            ("What does the quoted note instruct?", "en", "UNTRUSTED_INSTRUCTION_RISK", "untrusted_instructions"),
            ("Count all CPU trials in every document.", "en", "UNSUPPORTED_QUESTION", "unsupported_answer_type"),
        ]
        for question, language, classification, reason in cases:
            result = self.ask(question, language)
            self.assertEqual(result["view"]["grounding_risk"]["classification"], classification)
            self.assertEqual(result["view"]["reason"], reason)
            self.assertFalse(result["view"]["model_invoked"])
            self.assertGreater(len(result["packet"]["document_evidence"]), 0)

        conflict = self.ask(CONFLICT_QUESTION)
        self.assertEqual(conflict["view"]["grounding_risk"]["classification"], "CONFLICTING_EVIDENCE")
        self.assertEqual(conflict["view"]["reason"], "conflicting_evidence")
        passages = conflict["packet"]["document_evidence"]
        self.assertTrue(any("RAG-CPU-01" in item["text"] for item in passages))
        self.assertTrue(any("RAG-CPU-99" in item["text"] for item in passages))
        self.assertGreaterEqual(len({item["citation_id"] for item in passages}), 2)
        self.assertFalse(conflict["view"]["model_invoked"])

    def test_clipped_conflict_is_undetermined_not_conflicting(self):
        with patch.object(ask, "RESULT_LIMIT", 1):
            result = self.ask(CONFLICT_QUESTION)
        self.assertTrue(result["packet"]["completeness"]["documents_clipped"])
        self.assertNotEqual(result["view"]["grounding_risk"]["classification"], "CONFLICTING_EVIDENCE")
        self.assertEqual(result["view"]["reason"], "retrieval_coverage_incomplete")

    def test_no_evidence_is_not_a_claim_of_nonexistence(self):
        result = self.ask("xylophoniczebra?")
        self.assertEqual(result["view"]["status"], "no_evidence")
        self.assertEqual(result["view"]["reason"], "no_document_evidence")
        self.assertIn("does not prove absence", result["view"]["message"])
        self.assertEqual(result["packet"]["document_evidence"], [])

    def test_ask_and_prepare_do_not_call_inference_or_consume_authorization(self):
        with patch.object(generation, "attempt_generation", side_effect=AssertionError("inference")) as attempt, \
             patch.object(generation, "request_local_completion", side_effect=AssertionError("transport")) as send:
            asked = self.ask(EN_QUESTION)
            status, body, _ = self.post(ask.PREFIX + "prepare", {"question": EN_QUESTION, "language": "en"})
        prepared = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(asked["view"]["status"], "source_only")
        self.assertEqual(prepared["preparation"]["reason"], "model_registration_unavailable")
        attempt.assert_not_called()
        send.assert_not_called()
        denied, _, _ = self.post(ask.PREFIX + "run", {})
        self.assertEqual(denied, 400)

    def test_preparation_shows_exact_request_without_approval_or_private_data(self):
        registration = {
            "backend": "llama.cpp-openai-chat-loopback-v1", "model_name": "test-local-qwen",
            "model_revision": "a" * 40, "model_sha256": "sha256:" + "1" * 64,
            "runtime_revision": "b" * 40, "runtime_sha256": "sha256:" + "2" * 64,
            "context_tokens": 4096, "max_output_tokens": 64, "timeout_seconds": 30,
            "cpu_threads": 4, "gpu_layers": 0, "seed": 7,
            "api_key_path": "/private/api-key", "api_key_sha256": "sha256:" + "3" * 64,
            "ledger_path": "/private/ledger", "private_test_marker": "NEVER_RETURN",
        }
        self.bundle.runtime_registration = Path("/private/runtime-registration.json")
        with patch.object(ask.generation, "load_registration", return_value=registration), \
             patch.object(ask.generation, "host_observation", return_value={"private": "NEVER_RETURN"}), \
             patch.object(ask.generation, "admit_host") as admit, \
             patch.object(ask.generation, "attempt_generation", side_effect=AssertionError("inference")) as attempt, \
             patch.object(ask.generation, "request_local_completion", side_effect=AssertionError("transport")) as send:
            status, body, _ = self.post(ask.PREFIX + "prepare", {"question": EN_QUESTION, "language": "en"})
        result = json.loads(body)
        prep = result["preparation"]
        self.assertEqual(status, 200)
        self.assertEqual(prep["status"], "prepared")
        packet = self.bundle.packet({"question": EN_QUESTION, "language": "en"})
        expected_request = generation.request_payload(registration, generation.build_messages(packet))
        self.assertEqual(prep["request_sha256"], documents.sha(expected_request))
        self.assertEqual(prep["packet_sha256"], generation.fingerprint(packet))
        self.assertEqual(prep["request"]["model"], registration["model_name"])
        self.assertEqual(prep["host_admission"]["status"], "admitted")
        self.assertIs(prep["authorization"]["owner_approved"], False)
        self.assertIs(prep["authorization"]["consumed"], False)
        self.assertEqual(prep["authorization"]["recommended_expiry_seconds"], 600)
        self.assertFalse(prep["model_invoked"])
        encoded = body.decode()
        for private in ("/private/api-key", "NEVER_RETURN", "ledger_path", "api_key_sha256"):
            self.assertNotIn(private, encoded)
        admit.assert_called_once()
        attempt.assert_not_called()
        send.assert_not_called()

    def test_fabricated_citation_and_synthetic_fake_native_receipt_are_withheld(self):
        packet = self.bundle.packet({"question": EN_QUESTION, "language": "en"})
        replay = {
            "packet": packet,
            "view": {"status": "checked_saved_output_only", "model_invoked": False,
                     "answer": "The default local answer mode displays source passages.",
                     "citation_id": "d:" + "0" * 64},
        }
        result_path = self.root / "saved-result.json"
        result_path.write_text(json.dumps(replay), encoding="utf-8")
        result_path.chmod(0o600)
        saved_bundle = ask.Bundle(self.manifest, self.index, "development", checked_result=result_path)
        output = saved_bundle.api(ask.PREFIX + "ask", {"question": EN_QUESTION, "language": "en"})
        self.assertEqual(output["view"]["status"], "source_only")
        self.assertEqual(output["view"]["reason"], "invalid_model_response")
        self.assertIsNone(output["view"]["answer"])
        self.assertNotEqual(output["execution"], "native_authorized_cli")

        citation = packet["document_evidence"][0]["citation_id"]
        candidate = {"version": generation.VERSION, "status": "answer", "language": "en",
                     "answer": "The default local answer mode displays source passages.",
                     "citation_id": citation}
        fake_view = generation.check_answer(packet, candidate, actual_model=True)
        fake_result = {"packet": packet, "view": fake_view}
        fake_receipt = {
            "version": 2, "transport_kind": "synthetic_test", "model_request_attempted": True,
            "request_send_attempted": True, "sources_still_current": True,
            "citation_check": "exact_quote_and_citation_only",
            "candidate_validation": {"complete_validator": "passed"},
            "final_view": fake_view,
        }
        result_path.write_text(json.dumps(fake_result), encoding="utf-8")
        receipt_path = self.root / "receipt.json"
        receipt_path.write_text(json.dumps(fake_receipt), encoding="utf-8")
        receipt_path.chmod(0o600)
        fake_bundle = ask.Bundle(self.manifest, self.index, "development",
                                 checked_result=result_path, checked_receipt=receipt_path)
        output = fake_bundle.api(ask.PREFIX + "ask", {"question": EN_QUESTION, "language": "en"})
        self.assertEqual(output["view"]["status"], "source_only")
        self.assertEqual(output["view"]["reason"], "invalid_model_response")
        self.assertFalse(output["view"]["model_invoked"])

    def test_source_change_returns_no_stale_passages(self):
        self.ask(EN_QUESTION)
        source = self.corpus / "operator-en.md"
        source.write_text("Revoked source must never be returned.", encoding="utf-8")
        status, body, _ = self.post(ask.PREFIX + "ask", {"question": EN_QUESTION, "language": "en"})
        self.assertEqual(status, 200)
        result = json.loads(body)
        self.assertIsNone(result["packet"])
        self.assertEqual(result["view"]["status"], "source_unavailable")
        self.assertEqual(result["view"]["reason"], "source_changed")
        self.assertNotIn(b"The default local answer mode displays source passages.", body)
        self.assertNotIn(b"d:", body)

    def test_http_origin_auth_paths_and_private_session_assets(self):
        payload = {"question": EN_QUESTION, "language": "en"}
        for headers in (
            {"Authorization": ""}, {"Origin": "https://example.invalid"},
            {"Host": "example.invalid"}, {"Sec-Fetch-Site": "cross-site"},
            {"Content-Type": "text/plain"},
        ):
            status, _, _ = self.post(ask.PREFIX + "ask", payload, headers)
            self.assertEqual(status, 400)
        for route in (ask.PREFIX + "execute", "/api/file", "/../tests/fixtures/document-rag-native-v1/operator-en.md"):
            status, _, _ = self.post(route, {})
            self.assertEqual(status, 400)
        for host in ("0.0.0.0", "::", "localhost", "127.0.0.2", "192.168.1.2"):
            with self.assertRaises(ValueError):
                ask.Server(self.bundle, host)
        for route, (expected, _) in self.server.assets.items():
            connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=5)
            connection.request("GET", route)
            response = connection.getresponse()
            body, headers = response.read(), dict(response.getheaders())
            connection.close()
            self.assertEqual(response.status, 200)
            self.assertEqual(body, expected)
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertIn("default-src 'none'", headers["Content-Security-Policy"])

    def test_headless_browser(self):
        chrome = os.environ.get("CHROME_BINARY") or next(
            (path for name in ("google-chrome", "chromium", "chromium-browser")
             if (path := shutil.which(name))), None)
        mac = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        chrome = chrome or (str(mac) if mac.exists() else None)
        if not chrome or not shutil.which("node"):
            if os.environ.get("REQUIRE_FIND_BROWSER") == "1":
                self.fail("Headless Chrome and Node required")
            self.skipTest("Headless Chrome / Node unavailable")
        packet = self.bundle.packet({"question": EN_QUESTION, "language": "en"})
        source = packet["document_evidence"][0]
        sentence = "The default local answer mode displays source passages."
        candidate = {"version": generation.VERSION, "status": "answer", "language": "en",
                     "answer": sentence, "citation_id": source["citation_id"]}
        validated = generation.check_answer(packet, candidate, actual_model=True)
        synthetic = {"execution": "synthetic_test_fixture", "packet": packet, "view": validated}
        encoded = base64.b64encode(documents.serialized(synthetic)).decode("ascii")
        subprocess.run(["node", str(ask.ROOT / "tools/local_document_ask_browser.mjs"),
                        chrome, self.server.url, encoded], check=True, timeout=120)


if __name__ == "__main__":
    unittest.main()
