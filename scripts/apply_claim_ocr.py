#!/usr/bin/env python3
"""Merge verified OCR claims into the deterministic patent element charts."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def load_landscape_module():
    path = Path(__file__).with_name("patent_landscape.py")
    spec = importlib.util.spec_from_file_location("patent_landscape_runtime", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("summary", type=Path)
    parser.add_argument("--landscape", type=Path, default=Path("research/patent_landscape.json"))
    parser.add_argument("--report", type=Path, default=Path("research/PATENT_LANDSCAPE.md"))
    args = parser.parse_args()

    module = load_landscape_module()
    landscape = json.loads(args.landscape.read_text(encoding="utf-8"))
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    if summary.get("documents_failed"):
        raise ValueError("refusing to merge an OCR run with failed documents")
    if summary.get("quality_failures"):
        raise ValueError("refusing to merge OCR claims that failed sequence-quality checks")
    by_number = {result["publication_number"]: result for result in summary["results"]}
    rescored = []
    for record in landscape["ranked"]:
        result = by_number.get(record.get("publication_number"))
        if result:
            detail = record.setdefault("detail", {})
            detail["claims"] = [claim["text"] for claim in result["claims"]]
            detail["claim_records"] = result["claims"]
            detail["detail_source"] = result["ocr_engine"]
            detail["source_sha256"] = result["source_sha256"]
            detail["ocr_text_sha256"] = result["ocr_text_sha256"]
            detail["ocr_ranges"] = result["ocr_ranges"]
        rescored.append(module.score_record(record, landscape["config"]["claim_elements"]))
    rescored.sort(key=lambda row: (
        row["claim_element_coverage"], row["element_coverage"], row["weighted_score"]
    ), reverse=True)
    landscape["ranked"] = rescored
    landscape["stats"]["details_with_claims"] = sum(1 for row in rescored if (row.get("detail") or {}).get("claims"))
    landscape["stats"]["claims_extracted"] = sum(len((row.get("detail") or {}).get("claims") or []) for row in rescored)
    landscape["ocr_provenance"] = {
        "job_id": summary["job_id"],
        "manifest_sha256": summary["manifest_sha256"],
        "completed_at": summary["completed_at"],
        "documents_completed": summary["documents_completed"],
        "claims_extracted": summary["claims_extracted"],
    }
    args.landscape.write_text(json.dumps(landscape, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    module.render_report(landscape, args.report)
    print(json.dumps(landscape["ocr_provenance"], indent=2))


if __name__ == "__main__":
    main()
