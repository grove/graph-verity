"""Offline integrity checks for the retained Wikidata source slice."""
import json
from pathlib import Path
import tempfile
import unittest

from rdflib import Dataset

import rgcn_compgcn_wikidata as wd


class WikidataExportTests(unittest.TestCase):
    def test_retained_queries_responses_and_relation_adequacy_are_bound(self):
        wd.verify_query_files()
        roots, edges, labels = wd.source_data()
        stats = wd.graph_stats(edges, roots, labels)
        self.assertEqual(len(roots), 1000)
        self.assertEqual(len(edges), 5756)
        self.assertEqual(stats["predicate_count"], 84)
        self.assertEqual(stats["entity_nodes"], 2157)
        self.assertEqual(stats["nodes_with_english_or_norwegian_labels"], 2067)
        self.assertEqual(stats["directed_two_hop_reachable_pairs"], 1449)
        self.assertEqual(stats["synthetic_or_inferred_edges"], 0)

    def test_export_contains_only_original_directed_claim_edges_and_rebuilds(self):
        roots, edges, _ = wd.source_data()
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "export"
            wd.export(folder)
            exported = [json.loads(line) for line in (folder / "edges.jsonl").read_text().splitlines()]
            self.assertEqual({(row["subject_iri"], row["predicate"], row["object_iri"])
                              for row in exported}, set(edges))
            self.assertTrue(all(row["graph"] == wd.GRAPH for row in exported))
            dataset = Dataset()
            dataset.parse(folder / "snapshot.nq", format="nquads")
            self.assertEqual({str(g) for _, _, _, g in dataset.quads((None, None, None, None))}, {wd.GRAPH})
            self.assertEqual(wd.verify(folder)["stats"]["selected_organization_roots"], len(roots))


if __name__ == "__main__":
    unittest.main()
