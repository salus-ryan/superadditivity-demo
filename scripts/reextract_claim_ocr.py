#!/usr/bin/env python3
"""Re-extract patent claims from existing OCR page artifacts without rerunning OCR."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path


def load_worker():
    path = Path(__file__).with_name("patent_ocr_worker.py")
    spec = importlib.util.spec_from_file_location("patent_ocr_worker_runtime", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path, help="OCR output directory containing claim-ocr-summary.json")
    args = parser.parse_args()
    output = args.output.resolve()
    summary_path = output / "claim-ocr-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    worker = load_worker()

    refreshed = []
    for result in summary["results"]:
        document_dir = output / result["publication_number"]
        pages_by_number = {}
        for page_path in sorted(document_dir.glob("pages-*.json")):
            payload = json.loads(page_path.read_text(encoding="utf-8"))
            for page in payload.get("pages", []):
                pages_by_number[int(page["page"])] = page
        claims, method = worker.extract_claims(list(pages_by_number.values()))
        quality = worker.assess_claim_quality(claims, method)
        result["claims"] = claims
        result["extraction_method"] = method
        result["independent_claim_count"] = sum(1 for claim in claims if claim["independent"])
        result["quality"] = quality
        claim_path = document_dir / "claims.json"
        claim_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        os.chmod(claim_path, 0o600)
        refreshed.append(result)

    summary["results"] = refreshed
    summary["claims_extracted"] = sum(len(result["claims"]) for result in refreshed)
    summary["independent_claims_extracted"] = sum(result["independent_claim_count"] for result in refreshed)
    summary["documents_quality_passed"] = sum(1 for result in refreshed if result["quality"]["passed"])
    summary["quality_failures"] = [result["publication_number"] for result in refreshed if not result["quality"]["passed"]]
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    os.chmod(summary_path, 0o600)
    print(json.dumps({
        "documents": len(refreshed),
        "claims_extracted": summary["claims_extracted"],
        "independent_claims_extracted": summary["independent_claims_extracted"],
        "documents_quality_passed": summary["documents_quality_passed"],
        "quality_failures": summary["quality_failures"],
    }, indent=2))


if __name__ == "__main__":
    main()
