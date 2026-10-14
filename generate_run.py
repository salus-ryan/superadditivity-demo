#!/usr/bin/env python3
"""Seal the live Jev fan-out result and create its audit trail."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from audit import AuditLogger, digest_payload

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "demo-run.json"
LOG_DIR = ROOT / "logs"

SILOS = [
    {
        "id": "north",
        "name": "North",
        "role": "Symptoms & capacity",
        "position": "front-left",
        "evidence": [
            "API p95 latency: 180 ms → 8.4 s",
            "HTTP 503 responses increased",
            "DB connections pinned at 100/100",
            "TLS certificate valid for 74 days",
        ],
        "result": {
            "root_cause": "database connection pool exhaustion",
            "selected_probability": 1.00,
            "choice_confidence": 1.00,
            "sufficiency": 1.83,
            "sufficiency_confidence": 0.54,
            "requires_action": 0.94,
            "material_contradiction": 0.12,
        },
        "tokens": {"input": 548, "output": 124},
    },
    {
        "id": "south",
        "name": "South",
        "role": "Change & infrastructure",
        "position": "front-right",
        "evidence": [
            "Worker concurrency increased fourfold",
            "DNS lookup latency remains normal",
            "Database CPU remains moderate",
            "Disk utilization is 42%",
        ],
        "result": {
            "root_cause": "database connection pool exhaustion",
            "selected_probability": 0.91,
            "choice_confidence": 0.88,
            "sufficiency": 0.75,
            "sufficiency_confidence": 0.26,
            "requires_action": 0.29,
            "material_contradiction": 0.48,
        },
        "tokens": {"input": 523, "output": 124},
    },
    {
        "id": "east",
        "name": "East",
        "role": "Exclusions & controls",
        "position": "rear-left",
        "evidence": [
            "Database pool cap was unchanged",
            "Queries are fast after connection acquisition",
            "Non-database health endpoint remains fast",
            "No certificate errors observed",
        ],
        "result": {
            "root_cause": "database connection pool exhaustion",
            "selected_probability": 0.42,
            "choice_confidence": 0.23,
            "sufficiency": 0.78,
            "sufficiency_confidence": 0.22,
            "requires_action": 0.25,
            "material_contradiction": 0.67,
        },
        "tokens": {"input": 532, "output": 124},
    },
    {
        "id": "west",
        "name": "West",
        "role": "Correlation & recovery",
        "position": "rear-right",
        "evidence": [
            "Request wait tracks DB-pool wait",
            "Concurrency rollback restores service",
            "Request queue tracks pool waiters",
            "No DNS failures recorded",
        ],
        "result": {
            "root_cause": "database connection pool exhaustion",
            "selected_probability": 1.00,
            "choice_confidence": 1.00,
            "sufficiency": 1.86,
            "sufficiency_confidence": 0.70,
            "requires_action": 0.90,
            "material_contradiction": 0.07,
        },
        "tokens": {"input": 527, "output": 124},
    },
]

CONNECTED = {
    "root_cause": "database connection pool exhaustion",
    "selected_probability": 1.00,
    "choice_confidence": 1.00,
    "sufficiency": 2.75,
    "sufficiency_confidence": 0.75,
    "response": "rollback worker concurrency and resize the pool",
    "response_probability": 1.00,
    "coherent": 0.90,
    "tokens": {"input": 668, "output": 166},
}


def main() -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    payload = {
        "schema_version": "1.0",
        "run_id": run_id,
        "generated_at": generated,
        "model": "typesafe/jev-1.13-20260917",
        "execution": {
            "parallel_silos": 4,
            "parallel_judgments": 16,
            "connected_verification_judgments": 4,
            "latency_ms": None,
            "latency_note": "Latency was not instrumented for this sealed run.",
        },
        "silos": SILOS,
        "connected": CONNECTED,
        "utility": {
            "definition": "Safe executable response: root cause, sufficient evidence, supported action, and coherence are all present.",
            "isolated": [0, 0, 0, 0],
            "connected": 1,
            "surplus": 1,
            "note": "Illustrative threshold utility; not an empirical performance claim.",
        },
        "assurance": {
            "claim": "SOC 2-aligned demo controls; not SOC 2 certification or an audit opinion.",
            "raw_prompts_logged": False,
            "raw_responses_logged": False,
            "tamper_evident": True,
            "local_bind_only": True,
        },
    }
    DATA_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.chmod(DATA_PATH, 0o600)

    logger = AuditLogger(LOG_DIR)
    common = {"session_id": run_id}
    logger.append(
        actor="pi-controller",
        action="demo.run.started",
        target="silo-swarm",
        outcome="success",
        details={"model": payload["model"], "silo_count": 4},
        **common,
    )
    logger.append(
        actor="typesafe-jev",
        action="jev.parallel_fanout.completed",
        target="isolated-silos",
        outcome="success",
        details={
            "request_count": 4,
            "question_count": 16,
            "question_types": {"choice": 4, "score": 4, "noul": 8},
            "input_digest": digest_payload([silo["evidence"] for silo in SILOS]),
            "output_digest": digest_payload([silo["result"] for silo in SILOS]),
            "input_unit_count": sum(silo["tokens"]["input"] for silo in SILOS),
            "output_unit_count": sum(silo["tokens"]["output"] for silo in SILOS),
        },
        **common,
    )
    logger.append(
        actor="typesafe-jev",
        action="jev.connected_verification.completed",
        target="connected-network",
        outcome="success",
        details={
            "question_count": 4,
            "input_digest": digest_payload([silo["evidence"] for silo in SILOS]),
            "output_digest": digest_payload(CONNECTED),
            "input_unit_count": CONNECTED["tokens"]["input"],
            "output_unit_count": CONNECTED["tokens"]["output"],
        },
        **common,
    )
    logger.append(
        actor="deterministic-policy",
        action="decision.composed",
        target="incident-response",
        outcome="approved",
        details={
            "rule": "root_cause AND sufficient_evidence AND supported_action AND coherence",
            "isolated_utility": [0, 0, 0, 0],
            "connected_utility": 1,
            "surplus": 1,
        },
        **common,
    )
    sealed = logger.append(
        actor="pi-controller",
        action="demo.run.sealed",
        target="data/demo-run.json",
        outcome="success",
        details={"artifact_digest": digest_payload(payload)},
        **common,
    )
    verification = logger.verify()
    print(json.dumps({
        "run_id": run_id,
        "artifact": str(DATA_PATH),
        "audit_events": verification["events"],
        "audit_head": verification["head_hash"],
        "seal_event": sealed["event_id"],
    }, indent=2))


if __name__ == "__main__":
    main()
