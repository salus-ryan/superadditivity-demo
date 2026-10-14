# Silo Swarm

A local visual demonstration of complementary typed judgments becoming an executable incident-response decision.

- Four evidence silos
- Four Jev judgments per silo, dispatched in parallel (16 total)
- One connected verification wave (4 judgments)
- Deterministic policy composition
- HMAC-chained, append-only JSONL audit events
- Loopback-only web server
- No API credentials, raw prompts, or raw model responses in audit logs

## Important assurance boundary

The project implements **SOC 2-aligned demo controls**: data minimization, UTC event records, actor/action/target/outcome fields, restrictive file permissions, unique request and event IDs, HMAC chaining, durability via `fsync`, and verification tests. This is **not** SOC 2 certification, a compliance guarantee, or an auditor's opinion. Production assurance would also require organizational controls, independent key custody, centralized immutable retention, access reviews, monitoring, incident response, change management, and an external audit.

## Run

```bash
python3 generate_run.py
python3 -m unittest discover -s tests -v
python3 server.py
```

Open <http://127.0.0.1:8787> and choose **Connect Silos**.

## Audit verification

```bash
python3 - <<'PY'
from audit import AuditLogger
print(AuditLogger("logs").verify())
PY
```

Runtime artifacts under `logs/` and `data/demo-run.json` are excluded from version control. The sealed run shown in the demo was produced through the controller's Jev integration; the Mac receives results, not API credentials.
