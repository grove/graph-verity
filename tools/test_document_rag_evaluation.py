"""Model-free runner regression on the existing dev fixture, not an evaluation."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

import document_rag as documents
import evaluate_document_rag as evaluation


class DocumentRagEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        fixture = Path(__file__).resolve().parents[1] / "tests/fixtures/document-rag-native-v1"
        self.manifest = fixture / "sources.json"
        self.index_path = self.root / "index.json"
        index = documents.make_index(self.manifest, "development")
        documents.write_index(self.index_path, index, self.manifest)
        self.questions = self.root / "questions.csv"
        self.case = json.loads((fixture / "cases.json").read_bytes())["cases"][0]

    def tearDown(self):
        self.temp.cleanup()

    def write_questions(self, **changes):
        row = {
            "case_id": "case-1", "question": self.case["question"],
            "language": self.case["language"],
            "source_expectation": "OWNER_REVIEW_REQUIRED",
            "expectation_reviewer": "",
            "expected_document_id": "", "expected_citation_id": "",
            "human_relevance_judgment": "", "human_reviewer": "", "notes": "",
            **changes,
        }
        with self.questions.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=evaluation.QUESTION_FIELDS)
            writer.writeheader()
            writer.writerow(row)

    def test_emits_verified_source_only_result_and_pending_human_judgments(self):
        self.write_questions()
        case = evaluation.read_questions(self.questions)[0]
        index = documents.load_index(self.manifest, self.index_path, "development")
        bundle = evaluation.ask.Bundle(self.manifest, self.index_path, "development")
        result = evaluation.evaluate_case(
            bundle, self.manifest, self.index_path, "development",
            {"manifest_sha256": documents.sha(self.manifest.read_bytes()),
             "index_sha256": index["index_sha256"]}, case)

        self.assertEqual(result["native_inference_status"], "NOT_RUN")
        self.assertEqual(result["source_only_status"], "source_only")
        self.assertEqual(result["source_only_reason"], "generation_not_authorized")
        self.assertEqual(result["grounding_risk"]["classification"], "CLEAR_SUPPORTED_CASE")
        self.assertTrue(result["retrieved_passages"][0]["original_source_span_verified"])
        self.assertEqual(result["retrieved_passages"][0]["score_kind"], "bm25_not_confidence")
        self.assertIsNone(result["expected_passage_returned_by_source_only_ask"])
        self.assertIsNone(result["answer_supported"])
        self.assertIsNone(result["useful_to_answer"])
        self.assertIsNone(result["human_relevance_judgment"])

    def test_requires_real_review_labels_and_exact_case_columns(self):
        self.write_questions(human_relevance_judgment="SUPPORTED_BY_SOURCE")
        with self.assertRaisesRegex(ValueError, "reviewer name"):
            evaluation.read_questions(self.questions)

        self.write_questions(source_expectation="FABRICATED_GOLD")
        with self.assertRaisesRegex(ValueError, "Invalid or duplicate"):
            evaluation.read_questions(self.questions)


if __name__ == "__main__":
    unittest.main()
