#!/usr/bin/env python3
"""Finalize one workflow benchmark mode with minimized audit metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from audit import AuditLogger  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--landscape", type=Path)
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--elapsed-seconds", type=float, required=True)
    parser.add_argument("--semantic-triage", action="store_true")
    parser.add_argument("--semantic-digest")
    args = parser.parse_args()

    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    session_id = f"benchmark-{args.mode}-{summary['job_id']}"
    audit = AuditLogger(args.audit_dir)
    audit.append(
        actor=f"{args.mode}-controller",
        action="benchmark.started",
        target="fixed-five-patent-corpus",
        outcome="success",
        details={"manifest_digest": summary["manifest_sha256"]},
        session_id=session_id,
    )
    audit.append(
        actor=summary["results"][0]["ocr_engine"] if summary.get("results") else "ocr-worker",
        action="ocr.completed",
        target="patent-claims",
        outcome="success" if summary["documents_completed"] == 5 else "failure",
        details={
            "documents_completed": summary["documents_completed"],
            "documents_quality_passed": summary["documents_quality_passed"],
            "claims_extracted": summary["claims_extracted"],
            "summary_digest": digest(args.summary),
        },
        session_id=session_id,
    )
    if args.landscape and args.landscape.exists():
        audit.append(
            actor="deterministic-charting",
            action="claim.chart.produced",
            target=args.landscape.name,
            outcome="success",
            details={"landscape_digest": digest(args.landscape)},
            session_id=session_id,
        )
    if args.semantic_triage:
        audit.append(
            actor="typesafe-jev",
            action="semantic.triage.completed",
            target="seven-claim-elements",
            outcome="success",
            details={"assessment_digest": args.semantic_digest},
            session_id=session_id,
        )
    audit.append(
        actor=f"{args.mode}-controller",
        action="benchmark.completed",
        target=args.mode,
        outcome="success",
        details={
            "elapsed_seconds": round(args.elapsed_seconds, 3),
            "semantic_triage": args.semantic_triage,
        },
        session_id=session_id,
    )
    result = {
        "mode": args.mode,
        "elapsed_seconds": round(args.elapsed_seconds, 3),
        "audit": audit.verify(),
        "semantic_triage": args.semantic_triage,
        "summary": {key: summary[key] for key in (
            "documents_completed", "documents_failed", "claims_extracted",
            "independent_claims_extracted", "documents_quality_passed", "quality_failures",
        )},
    }
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
