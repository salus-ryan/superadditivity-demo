#!/usr/bin/env python3
"""macOS worker for parallel Apple Vision OCR and patent-claim extraction."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def page_count(path: Path, binary: Path) -> int:
    output = subprocess.check_output([str(binary), "--page-count", str(path)], text=True).strip()
    if not output.isdigit():
        raise RuntimeError(f"could not determine page count: {path}")
    return int(output)


def compile_vision_worker(source: Path, binary: Path) -> None:
    binary.parent.mkdir(parents=True, exist_ok=True)
    needs_build = not binary.exists() or source.stat().st_mtime_ns > binary.stat().st_mtime_ns
    if needs_build:
        subprocess.run(["xcrun", "swiftc", "-O", str(source), "-o", str(binary)], check=True)


def claim_region(pages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
    ordered = sorted(pages, key=lambda row: int(row["page"]))
    for index, page in enumerate(ordered):
        text = page.get("text") or ""
        if re.search(r"\bwhat\s+is\s+claimed\s+is\b", text, re.I):
            return ordered[index:], "explicit_heading"
    # If OCR missed the heading, work backward from the document end and
    # prefer the last page that begins claim 1 and is followed by dependent
    # references to claim 1. This avoids numbered figures and background lists.
    for index in range(len(ordered) - 1, -1, -1):
        text = ordered[index].get("text") or ""
        following = "\n".join(page.get("text") or "" for page in ordered[index:index + 4])
        if (
            re.search(r"(?m)^\s*1\s*[.)]\s+", text)
            and re.search(r"\bcomprising\b", following, re.I)
            and re.search(r"\bclaim\s+1\b", following, re.I)
        ):
            return ordered[index:], "numbered_claim_pattern"
    return [], "not_found"


def extract_claims(pages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
    region, method = claim_region(pages)
    if not region:
        return [], method
    text = "\n".join(page.get("text") or "" for page in region)
    heading = re.search(r"\bwhat\s+is\s+claimed\s+is\s*:?", text, re.I)
    if heading:
        text = text[heading.end():]
    matches = list(re.finditer(r"(?m)^\s*(\d{1,3})\s*[.)]\s+", text))
    claims = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = re.sub(r"\s+", " ", text[match.end():end]).strip()
        if len(body) < 25:
            continue
        number = int(match.group(1))
        dependent_on = [int(value) for value in re.findall(r"\bclaim\s+(\d{1,3})\b", body, re.I)]
        claims.append({
            "number": number,
            "text": body,
            "independent": not dependent_on,
            "depends_on": sorted(set(dependent_on)),
            "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        })
    return claims, method


def run_range(binary: Path, pdf: Path, output: Path, start: int, end: int) -> List[Dict[str, Any]]:
    subprocess.run([str(binary), str(pdf), str(output), str(start), str(end)], check=True)
    payload = json.loads(output.read_text(encoding="utf-8"))
    return payload.get("pages", [])


def assess_claim_quality(claims: List[Dict[str, Any]], extraction_method: str) -> Dict[str, Any]:
    claim_numbers = [claim["number"] for claim in claims]
    maximum_claim = max(claim_numbers, default=0)
    sequence_coverage = (len(set(claim_numbers)) / maximum_claim) if maximum_claim else 0.0
    minimum_coverage = 0.7 if extraction_method == "explicit_heading" else 0.8
    passed = bool(
        claim_numbers and claim_numbers[0] == 1 and
        any(claim["independent"] for claim in claims) and sequence_coverage >= minimum_coverage
    )
    return {
        "passed": passed,
        "starts_at_claim_one": bool(claim_numbers and claim_numbers[0] == 1),
        "sequence_coverage": round(sequence_coverage, 4),
        "minimum_coverage": minimum_coverage,
        "explicit_heading": extraction_method == "explicit_heading",
    }


def process_document(
    job: Dict[str, Any], bundle: Path, output_dir: Path, binary: Path, window: int
) -> Dict[str, Any]:
    pdf = bundle / job["input"]
    if sha256_file(pdf) != job["source_sha256"]:
        raise ValueError(f"source digest mismatch: {pdf}")
    total_pages = page_count(pdf, binary)
    document_dir = output_dir / job["publication_number"]
    document_dir.mkdir(parents=True, exist_ok=True)
    all_pages: Dict[int, Dict[str, Any]] = {}
    claims: List[Dict[str, Any]] = []
    extraction_method = "not_found"
    ranges = []

    end = total_pages
    while end > 0:
        start = max(1, end - window + 1)
        range_output = document_dir / f"pages-{start:04d}-{end:04d}.json"
        pages = run_range(binary, pdf, range_output, start, end)
        os.chmod(range_output, 0o600)
        ranges.append([start, end])
        for page in pages:
            all_pages[int(page["page"])] = page
        claims, extraction_method = extract_claims(list(all_pages.values()))
        if assess_claim_quality(claims, extraction_method)["passed"]:
            break
        end = start - 1

    ordered_pages = [all_pages[number] for number in sorted(all_pages)]
    text_digest = hashlib.sha256(
        "\n".join(page.get("text") or "" for page in ordered_pages).encode("utf-8")
    ).hexdigest()
    quality = assess_claim_quality(claims, extraction_method)
    result = {
        "publication_number": job["publication_number"],
        "source_sha256": job["source_sha256"],
        "source_pages": total_pages,
        "ocr_ranges": ranges,
        "ocr_pages": len(ordered_pages),
        "ocr_engine": "Apple Vision VNRecognizeTextRequest accurate",
        "ocr_text_sha256": text_digest,
        "extraction_method": extraction_method,
        "claims": claims,
        "independent_claim_count": sum(1 for claim in claims if claim["independent"]),
        "quality": quality,
        "generated_at": utc_now(),
    }
    result_path = document_dir / "claims.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.chmod(result_path, 0o600)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--page-window", type=int, default=25)
    args = parser.parse_args()

    bundle = args.bundle.resolve()
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    output_dir = (args.output or (bundle / "output")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    for script in manifest.get("worker_scripts", []):
        script_path = bundle / script["path"]
        if sha256_file(script_path) != script["sha256"]:
            raise ValueError(f"worker script digest mismatch: {script_path}")
    os.chmod(output_dir, 0o700)

    source = Path(__file__).with_name("macos_vision_ocr.swift")
    binary = output_dir / ".bin" / "vision-ocr"
    compile_vision_worker(source, binary)

    results = []
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        future_map = {
            pool.submit(process_document, job, bundle, output_dir, binary, args.page_window): job
            for job in manifest["jobs"]
        }
        for future in concurrent.futures.as_completed(future_map):
            job = future_map[future]
            try:
                results.append(future.result())
            except Exception as exc:
                failures.append({
                    "publication_number": job["publication_number"],
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                })

    summary = {
        "schema_version": "1.0",
        "job_id": manifest["job_id"],
        "manifest_sha256": sha256_file(bundle / "manifest.json"),
        "completed_at": utc_now(),
        "documents_requested": len(manifest["jobs"]),
        "documents_completed": len(results),
        "documents_failed": len(failures),
        "claims_extracted": sum(len(result["claims"]) for result in results),
        "independent_claims_extracted": sum(result["independent_claim_count"] for result in results),
        "documents_quality_passed": sum(1 for result in results if result["quality"]["passed"]),
        "quality_failures": [result["publication_number"] for result in results if not result["quality"]["passed"]],
        "results": sorted(results, key=lambda row: row["publication_number"]),
        "failures": failures,
    }
    summary_path = output_dir / "claim-ocr-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    os.chmod(summary_path, 0o600)
    print(json.dumps({key: summary[key] for key in (
        "job_id", "documents_requested", "documents_completed", "documents_failed",
        "claims_extracted", "independent_claims_extracted", "documents_quality_passed"
    )}, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
