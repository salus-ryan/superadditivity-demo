#!/usr/bin/env python3
"""Bounded Android/Poppler/Tesseract baseline for the workflow benchmark."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import patent_ocr_worker as extraction


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pdf_pages(path: Path) -> int:
    output = subprocess.check_output(["pdfinfo", str(path)], text=True, stderr=subprocess.DEVNULL)
    match = re.search(r"(?m)^Pages:\s+(\d+)\s*$", output)
    if not match:
        raise RuntimeError(f"could not read page count: {path}")
    return int(match.group(1))


def recognize_page(pdf: Path, page: int, work: Path) -> Dict[str, Any]:
    prefix = work / f"page-{page:04d}"
    subprocess.run([
        "pdftoppm", "-f", str(page), "-l", str(page), "-singlefile",
        "-r", "150", "-gray", "-png", str(pdf), str(prefix),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    image = prefix.with_suffix(".png")
    text = subprocess.check_output([
        "tesseract", str(image), "stdout", "--psm", "3", "-l", "eng",
    ], text=True, stderr=subprocess.DEVNULL)
    image.unlink(missing_ok=True)
    return {"page": page, "text": text}


def process(job: Dict[str, Any], bundle: Path, output: Path, window: int) -> Dict[str, Any]:
    pdf = bundle / job["input"]
    if sha256_file(pdf) != job["source_sha256"]:
        raise ValueError(f"source digest mismatch: {pdf}")
    total = pdf_pages(pdf)
    start = max(1, total - window + 1)
    document_dir = output / job["publication_number"]
    document_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="android-ocr-") as temporary:
        work = Path(temporary)
        pages = [recognize_page(pdf, page, work) for page in range(start, total + 1)]
    page_path = document_dir / f"pages-{start:04d}-{total:04d}.json"
    page_path.write_text(json.dumps({"pages": pages}, indent=2) + "\n", encoding="utf-8")
    os.chmod(page_path, 0o600)
    claims, method = extraction.extract_claims(pages)
    quality = extraction.assess_claim_quality(claims, method)
    text_digest = hashlib.sha256("\n".join(page["text"] for page in pages).encode()).hexdigest()
    result = {
        "publication_number": job["publication_number"],
        "source_sha256": job["source_sha256"],
        "source_pages": total,
        "ocr_ranges": [[start, total]],
        "ocr_pages": len(pages),
        "ocr_engine": "Poppler 150 DPI grayscale + Tesseract 5 psm 3",
        "ocr_text_sha256": text_digest,
        "extraction_method": method,
        "claims": claims,
        "independent_claim_count": sum(1 for claim in claims if claim["independent"]),
        "quality": quality,
        "generated_at": utc_now(),
    }
    claim_path = document_dir / "claims.json"
    claim_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.chmod(claim_path, 0o600)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--page-window", type=int, default=25)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    started = time.monotonic()
    results = []
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        future_jobs = {
            pool.submit(process, job, bundle, output, args.page_window): job
            for job in manifest["jobs"]
        }
        for future in concurrent.futures.as_completed(future_jobs):
            job = future_jobs[future]
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
        "mode": "android-only",
        "job_id": manifest["job_id"],
        "manifest_sha256": sha256_file(manifest_path),
        "completed_at": utc_now(),
        "elapsed_seconds": round(time.monotonic() - started, 3),
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
    summary_path = output / "claim-ocr-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    os.chmod(summary_path, 0o600)
    print(json.dumps({key: summary[key] for key in (
        "elapsed_seconds", "documents_completed", "documents_failed", "claims_extracted",
        "independent_claims_extracted", "documents_quality_passed", "quality_failures",
    )}, indent=2))


if __name__ == "__main__":
    main()
