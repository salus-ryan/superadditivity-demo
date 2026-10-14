#!/usr/bin/env python3
"""Wait for the authorized Mac, dispatch OCR, retrieve results, and rescore charts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tarfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from audit import AuditLogger, digest_payload  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ssh_base(key: Path, target: str, timeout: int = 10):
    return [
        "ssh", "-i", str(key), "-o", "BatchMode=yes",
        "-o", f"ConnectTimeout={timeout}", "-o", "ConnectionAttempts=1",
        "-o", "StrictHostKeyChecking=yes", target,
    ]


def remote(key: Path, target: str, command: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(ssh_base(key, target) + [command], capture_output=True, text=True, timeout=timeout)


def transfer_bundle(key: Path, target: str, bundle: Path, remote_root: str) -> None:
    tar = subprocess.Popen(["tar", "-C", str(bundle.parent), "-cf", "-", bundle.name], stdout=subprocess.PIPE)
    assert tar.stdout
    command = f"mkdir -p {shlex.quote(remote_root)} && tar -C {shlex.quote(remote_root)} -xf -"
    ssh = subprocess.run(ssh_base(key, target, 30) + [command], stdin=tar.stdout, timeout=900)
    tar.stdout.close()
    tar_status = tar.wait()
    if tar_status or ssh.returncode:
        raise RuntimeError(f"bundle transfer failed: tar={tar_status} ssh={ssh.returncode}")


def retrieve_output(key: Path, target: str, remote_job: str, bundle: Path) -> None:
    command = f"tar -C {shlex.quote(remote_job)} -cf - output"
    ssh = subprocess.Popen(ssh_base(key, target, 30) + [command], stdout=subprocess.PIPE)
    assert ssh.stdout
    with tarfile.open(fileobj=ssh.stdout, mode="r|") as archive:
        for member in archive:
            destination = (bundle / member.name).resolve()
            if bundle not in destination.parents and destination != bundle:
                raise ValueError("unsafe path in returned archive")
            archive.extract(member, bundle)
    status = ssh.wait(timeout=300)
    if status:
        raise RuntimeError(f"output retrieval failed: ssh={status}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--key", type=Path, default=Path.home() / ".ssh" / "elevate_mac_ed25519")
    parser.add_argument("--target", default="ryanbarrett@192.168.1.12")
    parser.add_argument("--remote-root", default="/Users/ryanbarrett/CascadeProjects/superadditivity-demo/jobs")
    parser.add_argument("--wait-hours", type=float, default=24.0)
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--landscape", type=Path, default=PROJECT / "research" / "patent_landscape.json")
    parser.add_argument("--report", type=Path, default=PROJECT / "research" / "PATENT_LANDSCAPE.md")
    args = parser.parse_args()

    bundle = args.bundle.resolve()
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    session_id = manifest["job_id"]
    audit = AuditLogger(PROJECT / "jobs" / "controller-audit" / session_id)
    deadline = time.monotonic() + args.wait_hours * 3600
    audit.append(actor="android-controller", action="worker.wait.started", target="mac-ocr-worker", outcome="pending", details={"poll_seconds": args.poll_seconds, "wait_hours": args.wait_hours, "manifest_digest": sha256_file(manifest_path)}, session_id=session_id)

    while time.monotonic() < deadline:
        check = remote(args.key, args.target, "echo online", timeout=15)
        if check.returncode == 0 and check.stdout.strip() == "online":
            break
        time.sleep(args.poll_seconds)
    else:
        audit.append(actor="android-controller", action="worker.wait.expired", target="mac-ocr-worker", outcome="timeout", details={"wait_hours": args.wait_hours}, session_id=session_id)
        raise SystemExit("Mac did not become reachable before the deadline")

    remote_root = args.remote_root
    remote_job = remote_root.rstrip("/") + "/" + bundle.name
    audit.append(actor="android-controller", action="worker.reachable", target="mac-ocr-worker", outcome="success", details={"transport":"ssh"}, session_id=session_id)
    transfer_bundle(args.key, args.target, bundle, remote_root)
    audit.append(actor="android-controller", action="ocr.bundle.transferred", target="mac-ocr-worker", outcome="success", details={"document_count":len(manifest["jobs"]),"source_bytes":sum(job["source_bytes"] for job in manifest["jobs"]),"manifest_digest":sha256_file(manifest_path)}, session_id=session_id)

    start_command = (
        f"cd {shlex.quote(remote_job)} && "
        "if [ -f output/claim-ocr-summary.json ]; then echo done; "
        "elif [ -f .worker.pid ] && kill -0 \"$(cat .worker.pid)\" 2>/dev/null; then echo running; "
        "else nohup caffeinate -dimsu python3 scripts/patent_ocr_worker.py . --workers 3 --page-window 25 "
        "> worker.log 2>&1 </dev/null & echo $! > .worker.pid; echo started; fi"
    )
    started = remote(args.key, args.target, start_command, timeout=30)
    if started.returncode:
        raise RuntimeError("could not start remote OCR worker")
    audit.append(actor="android-controller", action="ocr.worker.dispatched", target="mac-ocr-worker", outcome="success", details={"state":started.stdout.strip(),"worker_count":3,"page_window":25}, session_id=session_id)

    while time.monotonic() < deadline:
        status_command = (
            f"cd {shlex.quote(remote_job)} && "
            "if [ -f output/claim-ocr-summary.json ]; then echo done; "
            "elif [ -f .worker.pid ] && kill -0 \"$(cat .worker.pid)\" 2>/dev/null; then echo running; "
            "else echo failed; fi"
        )
        try:
            status = remote(args.key, args.target, status_command, timeout=20)
        except subprocess.TimeoutExpired:
            time.sleep(args.poll_seconds)
            continue
        state = status.stdout.strip() if status.returncode == 0 else "offline"
        if state == "done":
            break
        if state == "failed":
            log = remote(args.key, args.target, f"tail -80 {shlex.quote(remote_job + '/worker.log')}", timeout=20)
            failure_path = bundle / "worker-failure.log"
            failure_path.write_text(log.stdout[-20000:], encoding="utf-8")
            audit.append(actor="mac-ocr-worker", action="ocr.worker.completed", target="patent-claims", outcome="failure", details={"failure_log_digest":sha256_file(failure_path)}, session_id=session_id)
            raise SystemExit("remote OCR worker failed; see worker-failure.log")
        time.sleep(args.poll_seconds)
    else:
        raise SystemExit("OCR worker did not finish before the deadline")

    retrieve_output(args.key, args.target, remote_job, bundle)
    summary_path = bundle / "output" / "claim-ocr-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary["manifest_sha256"] != sha256_file(manifest_path):
        raise ValueError("returned result references a different manifest")
    if summary["documents_failed"]:
        raise ValueError("returned OCR summary contains failed documents")
    if summary.get("quality_failures"):
        raise ValueError(f"returned OCR claims failed quality checks: {summary['quality_failures']}")
    audit.append(actor="android-controller", action="ocr.results.retrieved", target="claim-ocr-summary", outcome="success", details={"documents_completed":summary["documents_completed"],"documents_quality_passed":summary["documents_quality_passed"],"claims_extracted":summary["claims_extracted"],"independent_claims_extracted":summary["independent_claims_extracted"],"summary_digest":sha256_file(summary_path)}, session_id=session_id)

    subprocess.run([
        sys.executable, str(PROJECT / "scripts" / "apply_claim_ocr.py"), str(summary_path),
        "--landscape", str(args.landscape),
        "--report", str(args.report),
    ], check=True)
    audit.append(actor="deterministic-charting", action="patent.element_charts.updated", target=str(args.landscape), outcome="success", details={"landscape_digest":sha256_file(args.landscape),"report_digest":sha256_file(args.report)}, session_id=session_id)
    print(json.dumps({"job_id":session_id,"summary":str(summary_path),"audit":audit.verify()}, indent=2))


if __name__ == "__main__":
    main()
