import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "patent_landscape.py"
SPEC = importlib.util.spec_from_file_location("patent_landscape", MODULE_PATH)
patent_landscape = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(patent_landscape)


class PatentLandscapeTests(unittest.TestCase):
    def test_query_url_applies_priority_cutoff(self):
        url = patent_landscape.google_query_url('"multi-agent" audit', 2, "2026-10-14")
        self.assertIn("patents.google.com", url)
        decoded = patent_landscape.urllib.parse.unquote(url)
        self.assertIn("priority%3A20261014", decoded)
        self.assertIn("page=2", decoded)

    def test_claim_matches_receive_highest_weight(self):
        element = {"id": "E7", "name": "audit", "terms": ["hash chain"]}
        record = {
            "publication_number": "TEST1",
            "title": "Audit system",
            "snippet": "",
            "detail": {"abstract": "An audit record.", "claims": ["A method comprising writing each event to a hash chain."]},
        }
        scored = patent_landscape.score_record(record, [element])
        self.assertEqual(scored["element_coverage"], 1)
        self.assertEqual(scored["claim_element_coverage"], 1)
        self.assertEqual(scored["weighted_score"], 5)

    def test_meta_parser_handles_attribute_order(self):
        page = '<meta content="A title" name="DC.title"><meta scheme="CPC" name="DC.subject" content="G06F 21/00">'
        tags = patent_landscape.parse_meta_tags(page)
        self.assertEqual(patent_landscape.meta_values(tags, "DC.title"), ["A title"])
        self.assertEqual(patent_landscape.meta_values(tags, "DC.subject", "CPC"), ["G06F 21/00"])


if __name__ == "__main__":
    unittest.main()
