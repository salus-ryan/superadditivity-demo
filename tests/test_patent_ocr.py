import importlib.util
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


builder = load("build_patent_ocr_bundle")
worker = load("patent_ocr_worker")


class PatentOcrTests(unittest.TestCase):
    def test_publication_number_to_uspto_digits(self):
        self.assertEqual(builder.publication_digits("US20250328560A1"), "20250328560")
        self.assertEqual(builder.publication_digits("US12526244B2"), "12526244")
        with self.assertRaises(ValueError):
            builder.publication_digits("WO2025080963A1")

    def test_generic_claim_word_does_not_start_claim_region(self):
        pages = [
            {"page": 10, "text": "The description claims an improvement.\n1. Background item.\n2. Another item."},
            {"page": 11, "text": "What is claimed is:\n1. A system comprising an agent."},
        ]
        region, method = worker.claim_region(pages)
        self.assertEqual(method, "explicit_heading")
        self.assertEqual(region[0]["page"], 11)

    def test_fallback_prefers_last_claim_one_page(self):
        pages = [
            {"page": 10, "text": "1. Background attack.\n2. Another background item comprising text."},
            {"page": 20, "text": "1. A system comprising multiple agents.\n2. The system of claim 1, further comprising a verifier."},
            {"page": 21, "text": "3. The system of claim 1, further comprising an audit record."},
        ]
        region, method = worker.claim_region(pages)
        self.assertEqual(method, "numbered_claim_pattern")
        self.assertEqual(region[0]["page"], 20)

    def test_extracts_independent_and_dependent_claims(self):
        pages = [{
            "page": 20,
            "text": "What is claimed is:\n1. A system comprising a plurality of agents and an aggregator.\n2. The system of claim 1, further comprising an audit log.\n3. A method comprising verifying agent outputs.",
            "error": None,
        }]
        claims, method = worker.extract_claims(pages)
        self.assertEqual(method, "explicit_heading")
        self.assertEqual([claim["number"] for claim in claims], [1, 2, 3])
        self.assertTrue(claims[0]["independent"])
        self.assertFalse(claims[1]["independent"])
        self.assertEqual(claims[1]["depends_on"], [1])
        self.assertTrue(claims[2]["independent"])
        quality = worker.assess_claim_quality(claims, method)
        self.assertTrue(quality["passed"])
        self.assertTrue(quality["explicit_heading"])


if __name__ == "__main__":
    unittest.main()
