"""Model-free #119 tests: source authorization, exact UTF-8 citations and BM25."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import document_rag as rag


class DocumentRagTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="verity-doc-rag-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "sources").mkdir()
        self.no = self.root / "sources" / "norge.md"
        self.en = self.root / "sources" / "policy.txt"
        self.secret = self.root / "sources" / "private.txt"
        self.no.write_text(
            "# Søknad\nOslo er hovedstaden i Norge.\n"
            "Søknadsfristen er 1. mai. Offisielle dokumenter er på norsk.\n",
            encoding="utf-8",
        )
        self.en.write_text(
            "The application deadline is June 3. The administration is in Oslo.\n",
            encoding="utf-8",
        )
        self.secret.write_text(
            "SECRET_PRIVATE_MARKER confidential procedure\n", encoding="utf-8",
        )
        self.manifest = self.root / "sources.json"
        self.index_path = self.root / "bm25.json"
        self.records = [
            self.record("norge", "sources/norge.md", self.no, "nb", "public"),
            self.record("policy", "sources/policy.txt", self.en, "en", "public"),
            self.record("private", "sources/private.txt", self.secret, "en", "private"),
        ]
        self.save_manifest()

    @staticmethod
    def record(identifier, path, file, language, scope):
        return {
            "id": identifier,
            "path": path,
            "sha256": rag.sha(file.read_bytes()),
            "language": language,
            "license": "CC-BY-4.0 (test fixture)",
            "scope": scope,
        }

    def save_manifest(self):
        self.manifest.write_text(
            json.dumps({"version": 1, "documents": self.records},
                       ensure_ascii=False), encoding="utf-8",
        )

    def build(self):
        index = rag.make_index(self.manifest, "public")
        rag.write_index(self.index_path, index, self.manifest)
        return index

    def test_real_no_en_passages_reproduce_and_cite_original_bytes(self):
        one = self.build()
        two = rag.make_index(self.manifest, "public")
        self.assertEqual(one, two)
        persisted = rag.load_index(self.manifest, self.index_path, "public")
        self.assertEqual(persisted, one)
        self.assertEqual(len(one["payload"]["documents"]), 2)
        self.assertEqual([r["id"] for r in one["payload"]["documents"]],
                         ["norge", "policy"])
        for chunk in persisted["payload"]["chunks"]:
            source = self.no if chunk["document_id"] == "norge" else self.en
            start = chunk["span"]["start_byte"]
            end = chunk["span"]["end_byte"]
            self.assertEqual(source.read_bytes()[start:end].decode("utf-8"),
                             chunk["text"])
            self.assertEqual(
                rag.cite(persisted, chunk["citation_id"])["evidence"]["text"],
                chunk["text"],
            )
            self.assertLessEqual(end - start, rag.CHUNK_BYTES)
        no = rag.search_index(persisted, "Søknadsfristen", 5)
        en = rag.search_index(persisted, "application deadline", 5)
        self.assertEqual(no["hits"][0]["document_id"], "norge")
        self.assertEqual(en["hits"][0]["document_id"], "policy")
        self.assertEqual(no["retriever"], "bm25-only")
        self.assertEqual(no["hits"][0]["score_kind"], "bm25_not_confidence")
        self.assertNotIn("SECRET_PRIVATE_MARKER", json.dumps(persisted))
        self.assertFalse(any(c["document_id"] == "private"
                             for c in persisted["payload"]["chunks"]))

    def test_no_match_and_bounded_rank_ties(self):
        persisted = self.build()
        self.assertEqual(rag.search_index(persisted, "zuluvocabulary")["status"],
                         "no_match")
        self.assertEqual(rag.search_index(persisted, "zuluvocabulary")["hits"], [])
        result = rag.search_index(persisted, "Oslo", 1)
        self.assertEqual(result["matches"], 2)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["hits"]), 1)
        with self.assertRaises(ValueError):
            rag.search_index(persisted, "Oslo", 0)
        with self.assertRaises(ValueError):
            rag.search_index(persisted, "Oslo", 21)
        with self.assertRaises(ValueError):
            rag.search_index(persisted, "X" * (rag.MAX_QUERY + 1))
        with self.assertRaises(ValueError):
            rag.search_index(persisted, "   ")

    def test_long_document_stable_chunks_and_no_cut_utf8(self):
        self.no.write_text("Ålesund kyst " * 850, encoding="utf-8")
        self.records[0]["sha256"] = rag.sha(self.no.read_bytes())
        self.save_manifest()
        built = self.build()
        chunks = [c for c in built["payload"]["chunks"]
                  if c["document_id"] == "norge"]
        self.assertGreater(len(chunks), 2)
        self.assertEqual([c["citation_id"] for c in chunks],
                         [c["citation_id"] for c in
                          rag.make_index(self.manifest, "public")["payload"]["chunks"]
                          if c["document_id"] == "norge"])
        for chunk in chunks:
            b = self.no.read_bytes()
            start, end = chunk["span"].values()
            self.assertEqual(b[start:end].decode("utf-8"), chunk["text"])
            self.assertLessEqual(end - start, rag.CHUNK_BYTES)
            self.assertTrue(chunk["text"].startswith("Ålesund") or
                            chunk["text"].startswith("kyst"))

    def test_private_documents_not_opened_by_public_scope(self):
        # Explicit scope selection must happen *before* source bytes are read.
        self.secret.unlink()
        self.build()  # non-selected source need not exist
        with self.assertRaises((OSError, ValueError)):
            rag.make_index(self.manifest, "private")
        with self.assertRaises(ValueError):
            rag.load_index(self.manifest, self.index_path, "private")
        self.assertNotIn("SECRET_PRIVATE_MARKER",
                         self.index_path.read_text(encoding="utf-8"))

    def test_fails_closed_on_mutated_source_and_manifest(self):
        self.build()
        self.no.write_text("Replacement Norwegian text", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Source changed"):
            rag.load_index(self.manifest, self.index_path, "public")
        self.records[0]["sha256"] = rag.sha(self.no.read_bytes())
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "Stale manifest"):
            rag.load_index(self.manifest, self.index_path, "public")

    def test_corrupt_or_repacked_index_cannot_fabricate_excerpts(self):
        self.build()
        index = json.loads(self.index_path.read_text(encoding="utf-8"))
        index["payload"]["chunks"][0]["text"] = "forged evidence"
        index["index_sha256"] = rag.sha(rag.serialized(index["payload"]))
        self.index_path.write_text(json.dumps(index), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "cannot be verified"):
            rag.load_index(self.manifest, self.index_path, "public")
        self.index_path.write_text("{}", encoding="utf-8")
        with self.assertRaises(ValueError):
            rag.load_index(self.manifest, self.index_path, "public")

    def test_bad_manifest_missing_license_scope_duplicate_and_path_escape(self):
        original = [dict(record) for record in self.records]
        try:
            for changed in [
                lambda: self.records[0].pop("license"),
                lambda: self.records[0].update(scope="invalid scope"),
                lambda: self.records[0].update(path="../private.txt"),
                lambda: self.records[0].update(language="fr"),
                lambda: self.records[0].update(sha256="not-pinned"),
                lambda: self.records[0].update(id="../escape"),
                lambda: self.records[1].update(id="norge"),
            ]:
                self.records = [dict(record) for record in original]
                changed()
                self.save_manifest()
                with self.assertRaises(ValueError):
                    rag.make_index(self.manifest, "public")
        finally:
            self.records = original
            self.save_manifest()

    def test_symlink_and_binary_sources_rejected(self):
        self.build()
        if hasattr(self.root, "symlink_to"):
            linked = self.root / "linked.md"
            try:
                linked.symlink_to(self.no)
            except (OSError, NotImplementedError):
                pass
            else:
                self.records[0]["path"] = "linked.md"
                self.save_manifest()
                with self.assertRaisesRegex(ValueError, "Symlink"):
                    rag.make_index(self.manifest, "public")
                self.records[0]["path"] = "sources/norge.md"
        self.no.write_bytes(b"binary\x00payload")
        self.records[0]["sha256"] = rag.sha(self.no.read_bytes())
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "binary"):
            rag.make_index(self.manifest, "public")

    def test_cli_build_search_and_cite_without_network_or_models(self):
        script = Path(rag.__file__).resolve()

        def run(*args):
            return subprocess.run(
                [sys.executable, str(script), *args,
                 "--manifest", str(self.manifest),
                 "--index", str(self.index_path),
                 "--scope", "public"],
                capture_output=True, text=True, timeout=20,
            )

        built = run("build")
        self.assertEqual(built.returncode, 0, built.stderr)
        searched = run("search", "--query", "hovedstaden", "--limit", "1")
        self.assertEqual(searched.returncode, 0, searched.stderr)
        result = json.loads(searched.stdout)
        self.assertEqual(result["hits"][0]["document_id"], "norge")
        citation_id = result["hits"][0]["citation_id"]
        cited = run("cite", "--citation-id", citation_id)
        self.assertEqual(cited.returncode, 0, cited.stderr)
        self.assertEqual(json.loads(cited.stdout)["evidence"]["citation_id"],
                         citation_id)
        missing = run("cite", "--citation-id", "d:invalid")
        self.assertEqual(missing.returncode, 2)
        self.assertNotIn("SECRET_PRIVATE_MARKER", missing.stderr)


if __name__ == "__main__":
    unittest.main()
