#!/usr/bin/env python3
"""Score fixed claim-text anchors for the bounded workflow benchmark."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ANCHORS = {
    "US12526244B2": [
        "privacy-preserving evaluations of artificial intelligence agents",
        "machine-readable data structure",
        "first transformation operation set",
        "verification record",
    ],
    "US12596813B2": [
        "non-transitory computer-readable storage medium",
        "plurality of observing agents",
        "conflict-resolution rule set",
        "auditable ledger",
    ],
    "US20220210200A1": [
        "automated cybersecurity defensive strategy",
        "recommendation engine",
        "endpoint agents",
        "network packet capturing devices",
    ],
    "US20250259042A1": [
        "platform for orchestrating a scalable privacy-enabled network",
        "collaborative and negotiating agents",
        "hierarchical memory structure",
        "common token space",
    ],
    "US20250328560A1": [
        "securing inter-process communications",
        "permission validation",
        "immutable blockchain registry",
        "tamper-proof audit trails",
    ],
}


def compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("summary", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    text_by_publication = {
        result["publication_number"]: compact("\n".join(claim["text"] for claim in result["claims"]))
        for result in summary.get("results", [])
    }
    checks = []
    for publication, anchors in ANCHORS.items():
        text = text_by_publication.get(publication, "")
        for anchor in anchors:
            checks.append({
                "publication_number": publication,
                "anchor": anchor,
                "matched": compact(anchor) in text,
            })
    matched = sum(check["matched"] for check in checks)
    result = {
        "matched": matched,
        "total": len(checks),
        "recall": matched / len(checks),
        "checks": checks,
    }
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
