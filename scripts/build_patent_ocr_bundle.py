#!/usr/bin/env python3
"""Build a content-addressed OCR job bundle for a macOS worker."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

USPTO_PDF = "https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/{number}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cache_path(cache: Path, url: str) -> Path:
    return cache / (hashlib.sha256(url.encode()).hexdigest() + ".bin")


def publication_digits(number: str) -> str:
    digits = "".join(character for character in number[2:] if character.isdigit())
    if not number.startswith("US") or not digits:
        raise ValueError(f"only cached USPTO documents are supported: {number}")
    # Kind codes end in a digit, so remove the final digit captured from A1/B2.
    return digits[:-1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("research/patent_search_config.json"))
    parser.add_argument("--cache", type=Path, default=Path("research/.patent-cache"))
    parser.add_argument("--output-root", type=Path, default=Path("jobs"))
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    job_id = "patent-ocr-" + str(uuid.uuid4())
    bundle = args.output_root / job_id
    inputs = bundle / "inputs"
    scripts = bundle / "scripts"
    inputs.mkdir(parents=True, exist_ok=False)
    scripts.mkdir(parents=True, exist_ok=True)
    jobs = []

    for publication in config["seed_publications"]:
        digits = publication_digits(publication)
        url = USPTO_PDF.format(number=digits)
        source = cache_path(args.cache, url)
        if not source.exists():
            raise FileNotFoundError(f"cached source missing for {publication}: {source}")
        destination = inputs / f"{publication}.pdf"
        shutil.copyfile(source, destination)
        os.chmod(destination, 0o600)
        jobs.append({
            "publication_number": publication,
            "input": str(destination.relative_to(bundle)),
            "source_url": url,
            "source_sha256": sha256_file(destination),
            "source_bytes": destination.stat().st_size,
        })

    project_scripts = Path(__file__).resolve().parent
    worker_scripts = []
    for name in ("patent_ocr_worker.py", "macos_vision_ocr.swift"):
        destination = scripts / name
        shutil.copyfile(project_scripts / name, destination)
        os.chmod(destination, 0o700 if name.endswith(".py") else 0o600)
        worker_scripts.append({
            "path": str(destination.relative_to(bundle)),
            "sha256": sha256_file(destination),
            "bytes": destination.stat().st_size,
        })

    manifest: Dict[str, object] = {
        "schema_version": "1.0",
        "job_id": job_id,
        "created_at": utc_now(),
        "controller_role": "search, source acquisition, hashing, manifest, verification",
        "worker_role": "parallel PDF rendering, Apple Vision OCR, deterministic claim extraction",
        "verification_role": "Jev semantic relevance plus deterministic element charting after OCR",
        "jobs": jobs,
        "worker_scripts": worker_scripts,
    }
    manifest_path = bundle / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.chmod(manifest_path, 0o600)
    print(json.dumps({
        "job_id": job_id,
        "bundle": str(bundle),
        "documents": len(jobs),
        "bytes": sum(job["source_bytes"] for job in jobs),
        "manifest_sha256": sha256_file(manifest_path),
    }, indent=2))


if __name__ == "__main__":
    main()
