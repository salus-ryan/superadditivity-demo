"""Tamper-evident, data-minimized audit logging for the Silo Swarm demo.

These controls are SOC 2-aligned demo controls, not a claim of SOC 2 compliance.
"""

from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

SCHEMA_VERSION = "1.0"
GENESIS_HASH = "0" * 64
SENSITIVE_KEY_FRAGMENTS = (
    "authorization",
    "api_key",
    "apikey",
    "password",
    "secret",
    "token",
    "credential",
    "raw_state",
    "raw_response",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _validate_safe_metadata(value: Any, path: str = "details") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS):
                raise ValueError(f"sensitive audit field rejected: {path}.{key}")
            _validate_safe_metadata(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _validate_safe_metadata(child, f"{path}[{index}]")
    elif not isinstance(value, (str, int, float, bool, type(None))):
        raise TypeError(f"unsupported audit metadata at {path}: {type(value).__name__}")


class AuditLogger:
    """Append-only JSONL audit trail protected by an HMAC hash chain."""

    def __init__(self, directory: Union[str, Path]):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.directory, 0o700)
        self.key_path = self.directory / "audit.key"
        self.log_path = self.directory / "audit.jsonl"
        self._ensure_key()
        self.log_path.touch(mode=0o600, exist_ok=True)
        os.chmod(self.log_path, 0o600)

    def _ensure_key(self) -> None:
        try:
            fd = os.open(self.key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            os.chmod(self.key_path, 0o600)
            return
        with os.fdopen(fd, "wb") as handle:
            handle.write(secrets.token_bytes(32))
            handle.flush()
            os.fsync(handle.fileno())

    def _key(self) -> bytes:
        return self.key_path.read_bytes()

    def append(
        self,
        *,
        actor: str,
        action: str,
        target: str,
        outcome: str,
        details: Optional[dict[str, Any]] = None,
        session_id: str,
        request_id: Optional[str] = None,
    ) -> dict[str, Any]:
        metadata = details or {}
        _validate_safe_metadata(metadata)
        with self.log_path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            handle.seek(0)
            lines = [line for line in handle.read().splitlines() if line.strip()]
            previous = json.loads(lines[-1]) if lines else None
            record = {
                "schema_version": SCHEMA_VERSION,
                "sequence": (int(previous["sequence"]) + 1) if previous else 1,
                "event_id": str(uuid.uuid4()),
                "request_id": request_id or str(uuid.uuid4()),
                "session_id": session_id,
                "timestamp_utc": utc_now(),
                "actor": actor,
                "action": action,
                "target": target,
                "outcome": outcome,
                "data_classification": "internal-demo-metadata",
                "details": metadata,
                "previous_hash": previous["event_hash"] if previous else GENESIS_HASH,
            }
            record["event_hash"] = hmac.new(self._key(), canonical_json(record), hashlib.sha256).hexdigest()
            handle.seek(0, os.SEEK_END)
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return record

    def verify(self) -> dict[str, Any]:
        key = self._key()
        previous_hash = GENESIS_HASH
        count = 0
        with self.log_path.open("r", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_SH)
            for expected_sequence, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                count += 1
                record = json.loads(line)
                supplied_hash = record.pop("event_hash")
                expected_hash = hmac.new(key, canonical_json(record), hashlib.sha256).hexdigest()
                if record.get("sequence") != expected_sequence:
                    raise ValueError(f"sequence mismatch at event {expected_sequence}")
                if record.get("previous_hash") != previous_hash:
                    raise ValueError(f"chain mismatch at event {expected_sequence}")
                if not hmac.compare_digest(supplied_hash, expected_hash):
                    raise ValueError(f"signature mismatch at event {expected_sequence}")
                previous_hash = supplied_hash
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return {"valid": True, "events": count, "head_hash": previous_hash}
