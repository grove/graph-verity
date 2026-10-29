"""Synthetic contract tests for the provenance-preserving navigation export."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rgcn_compgcn_directional as directional


class DirectionalExportTests(unittest.TestCase):
    def make_export(self, root: Path) -> Path:
        folder = root / "source"
        folder.mkdir()
        graph = directional.GRAPH
        s, p, o = "urn:entity:s", "urn:property:p", "urn:entity:o"
        prop = "urn:property-resource:p"
        nq = [
            f"<{s}> <{p}> <{o}> <{graph}> .",
            f'<{prop}> <{directional.RDFS_LABEL}> "property"@en <{graph}> .',
            f'<{prop}> <{directional.RDFS_LABEL}> "egenskap"@nb <{graph}> .',
        ]
        (folder / "manifest.json").write_text(json.dumps({"source_graph": graph, "license": "CC0"}))
        (folder / "snapshot.nq").write_text("\n".join(nq) + "\n")
        for name, rows in (
            ("nodes.jsonl", [{"id": 0, "graph": graph, "iri": s, "labels": {}},
                             {"id": 1, "graph": graph, "iri": o, "labels": {}}]),
            ("relations.jsonl", [{"id": 0, "iri": p, "property_iri": prop,
                                  "labels": {"en": ["property"], "nb": ["egenskap"]}}]),
            ("edges.jsonl", [{"graph": graph, "subject_id": 0, "subject_iri": s,
                              "predicate_id": 0, "predicate": p, "object_id": 1,
                              "object_iri": o}]),
        ):
            (folder / name).write_text("".join(json.dumps(row) + "\n" for row in rows))
        return folder

    def test_inverse_navigation_keeps_original_witness_and_is_not_an_rdf_fact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.make_export(root)
            result = directional.build(source, root / "directional")
            edges = directional.read_jsonl(root / "directional/directional-edges.jsonl")
            self.assertEqual(result["stats"]["original_edges"], 1)
            self.assertEqual(result["stats"]["directional_navigation_edges"], 2)
            forward, reverse = edges
            self.assertEqual(forward["direction"], "forward")
            self.assertEqual(reverse["direction"], "reverse")
            self.assertNotEqual(forward["relation_id"], reverse["relation_id"])
            self.assertEqual((forward["subject_iri"], forward["object_iri"]),
                             ("urn:entity:s", "urn:entity:o"))
            self.assertEqual((reverse["subject_iri"], reverse["object_iri"]),
                             ("urn:entity:o", "urn:entity:s"))
            self.assertEqual(reverse["source_quad"], forward["source_quad"])
            self.assertEqual(reverse["derived_from_source_quad"], forward["source_quad"])
            self.assertFalse(reverse["asserted_rdf_fact"])
            self.assertTrue(forward["asserted_rdf_fact"])
            self.assertIsNone(result.get("owl:inverseOf"))

    def test_bilingual_metadata_marks_templates_and_missing_source_definitions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.make_export(root)
            directional.build(source, root / "directional")
            row = directional.read_jsonl(root / "directional/predicate-vocabulary.jsonl")[0]
            self.assertEqual({x["language"] for x in row["source_labels"]}, {"en", "nb"})
            self.assertTrue(all(x["source_quad"] for x in row["source_labels"]))
            self.assertEqual(row["aliases"], [])
            self.assertEqual(row["source_descriptions"], [])
            self.assertEqual(row["description_status"], "absent_from_frozen_export")
            self.assertTrue(all(x["origin"] == "generated_navigation_template" and
                                x["review_status"] == "unreviewed"
                                for x in row["navigation_descriptions"]))
            self.assertIsNone(directional.navigation_text(None, "no", "forward"))

    def test_verify_rebuilds_deterministically_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.make_export(root)
            out = root / "directional"
            directional.build(source, out)
            manifest = directional.verify(source, out)
            self.assertEqual(manifest["stats"]["derived_reverse_edges"], 1)
            self.assertEqual(manifest["stats"]["top_five_predicate_edge_share"], 1.0)
            self.assertEqual(manifest["stats"]["source_label_predicate_coverage"],
                             {"en": 1, "norwegian_nb_nn_no": 1})
            with self.assertRaisesRegex(ValueError, "Output exists"):
                directional.build(source, out)


if __name__ == "__main__":
    unittest.main()
