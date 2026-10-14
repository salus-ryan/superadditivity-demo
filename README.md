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

## Prior-art review

The systematic discovery protocol, reproducible metadata, and conclusions are in:

- [`research/PRIOR_ART_PROTOCOL.md`](research/PRIOR_ART_PROTOCOL.md)
- [`research/PRIOR_ART_REPORT.md`](research/PRIOR_ART_REPORT.md)
- [`research/prior_art_results.json`](research/prior_art_results.json)

The responsible current label is **distinctive integration demo**, not novel scientific method or novel technical architecture.

The claim-oriented patent-search tooling and preliminary landscape are in:

- [`scripts/patent_landscape.py`](scripts/patent_landscape.py)
- [`research/patent_search_config.json`](research/patent_search_config.json)
- [`research/PATENT_LANDSCAPE.md`](research/PATENT_LANDSCAPE.md)
- [`research/patent_landscape.json`](research/patent_landscape.json)
- [`research/DISTRIBUTED_PATENT_SEARCH.md`](research/DISTRIBUTED_PATENT_SEARCH.md)

The tool expands queries, applies a priority-date cutoff, deduplicates publications and proxy families, retrieves USPTO documents, scores seven claim elements, emits preliminary element charts, caches source evidence, and fails closed behind a circuit breaker when a source rate-limits requests. A content-addressed worker bundle can dispatch image-only USPTO documents to macOS Apple Vision OCR and merge verified claims back into the charts. It remains a discovery aid rather than a legal opinion.

## Bounded workflow benchmark

The pre-registered Android-only, Mac-only, and connected comparison is documented in:

- [`research/WORKFLOW_BENCHMARK_PROTOCOL.md`](research/WORKFLOW_BENCHMARK_PROTOCOL.md)
- [`research/WORKFLOW_BENCHMARK_RESULTS.md`](research/WORKFLOW_BENCHMARK_RESULTS.md)
- [`research/workflow_benchmark_results.json`](research/workflow_benchmark_results.json)

The connected workflow passed the operational threshold under the deployed credential-separation policy. This is a bounded workflow result, not proof of scientific superadditivity or broad technical novelty.
