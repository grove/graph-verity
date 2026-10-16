"""No-model regressions for the real GeoNames-derived/schema.org transfer ontology."""
import sys
from pathlib import Path
import unittest

from rdflib import Dataset

sys.path.insert(0, str(Path(__file__).resolve().parent))
import worldcities_transfer as wc

class TransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = wc.read_rows()
        cls.store = Dataset()
        cls.store.parse(data=(wc.DATA / "snapshot.nq").read_bytes(), format="nquads")

    def query(self, q):
        return list(self.store.query(q))

    def test_pinned_snapshot_exact_rebuild_and_attribution(self):
        meta = wc.verify()
        self.assertTrue(meta["verified"])
        self.assertEqual(meta["quads"], 1508)
        self.assertEqual(meta["cities"], 328)
        self.assertEqual(meta["regions"], 62)
        self.assertEqual(meta["license"], "CC-BY-4.0")

    def test_countries_are_real_source_rows_and_scopes_do_not_leak(self):
        expected = {"NO": 42, "SE": 111, "DK": 67, "FI": 102, "IS": 6}
        for code, number in expected.items():
            with self.subTest(country=code):
                graph = f"<urn:graph-verity:worldcities:transfer:{code}>"
                rows = self.query(f"""SELECT (COUNT(DISTINCT ?city) AS ?n) WHERE {{
                  GRAPH {graph} {{
                    ?city a <https://schema.org/City> .
                  }}
                }}""")
                self.assertEqual(int(rows[0][0]), number)

    def test_two_hop_traversals_preserve_direction(self):
        examples = {
            "3143244": "NO",    # Oslo, not Oslo municipality Q585
            "2673730": "SE",    # Stockholm
            "658225": "FI",     # Helsinki
            "3413829": "IS",    # Reykjavik
        }
        for city_id, country in examples.items():
            with self.subTest(id=city_id):
                query = f"""SELECT ?country WHERE {{
                  GRAPH <urn:graph-verity:worldcities:transfer:{country}> {{
                    <https://sws.geonames.org/{city_id}/> <https://schema.org/containedInPlace> ?admin .
                    ?admin <https://schema.org/containedInPlace> ?country .
                  }}
                }}"""
                results = self.query(query)
                self.assertEqual(len(results), 1)
                self.assertEqual(str(results[0][0]),
                                 f"urn:graph-verity:worldcities:country:{country}")

    def test_named_graph_scope_excludes_other_country(self):
        rows = self.query("""SELECT ?name WHERE {
          GRAPH <urn:graph-verity:worldcities:transfer:SE> {
            <https://sws.geonames.org/3143244/> <https://schema.org/name> ?name .
          }
        }""")
        self.assertEqual(rows, [])

    def test_numeric_identifiers_are_typed_not_populations(self):
        rows = self.query("""SELECT ?name WHERE {
          GRAPH <urn:graph-verity:worldcities:transfer:NO> {
            <https://sws.geonames.org/3143244/> <https://schema.org/name> ?name ;
               <https://schema.org/identifier> ?identifier .
            FILTER(?identifier >= 3143244)
          }
        }""")
        self.assertEqual([str(r[0]) for r in rows], ["Oslo"])

    def test_explicit_city_and_admin_relationships(self):
        actual = self.query("""SELECT ?city WHERE {
          GRAPH <urn:graph-verity:worldcities:transfer:NO> {
            ?city a <https://schema.org/City> ;
              <https://schema.org/containedInPlace>
                <urn:graph-verity:worldcities:admin:NO:Rogaland> .
          }
        }""")
        expected = [r for r in self.rows if r["country"] == "Norway"
                    and r["subcountry"] == "Rogaland"]
        self.assertEqual(len(actual), len(expected))

if __name__ == "__main__":
    unittest.main()
