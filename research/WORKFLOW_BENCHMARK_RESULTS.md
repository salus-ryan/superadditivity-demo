# Bounded workflow benchmark results

- Run: 2026-10-14 UTC
- Protocol: [`WORKFLOW_BENCHMARK_PROTOCOL.md`](WORKFLOW_BENCHMARK_PROTOCOL.md)
- Job: `patent-ocr-6fe76320-d10d-43a3-b6e1-4855780d9e6a`
- Manifest SHA-256: `0ca414ed958d6fe8af9ca879d6ae6f0dde2c886072fb80a5169f152054f379c3`

## Verdict

**The connected workflow passed the pre-registered operational go/no-go threshold, but the experiment does not establish scientific or architectural novelty.**

Connected utility was 1.00 versus 0.833 for the best solo mode, a 20% relative lift against a required 15%. It recovered 19/20 accuracy anchors, completed in 95.754 seconds including coordination and semantic triage, and retained a valid eight-event controller audit chain.

The one-point advantage over Mac-only came from controller-side semantic triage while API credentials remained off the worker. This is useful under the deployed least-privilege policy, but it is an operational trust/resource-placement benefit—not evidence that Mac hardware intrinsically cannot perform the semantic step.

## Results

| Mode | Time | Documents | Quality pass | Claim segments | Anchor recall | Deliverables | Utility |
|---|---:|---:|---:|---:|---:|---:|---:|
| Android-only | ≥600 s (capped) | 0/5 | 0/5 | 0 | 0/20 | 2/6 | 0.333 |
| Mac-only | 91 s | 5/5 | 5/5 | 91 | 19/20 | 5/6 | 0.833 |
| Connected | 95.754 s | 5/5 | 5/5 | 91 | 19/20 | 6/6 | 1.000 |

Connected coordination and controller-side semantic triage added 4.754 seconds over the Mac-only OCR-and-chart path. Android Poppler/Tesseract reached the 600-second cap before completing any 25-page document; no OCR/render child processes remained afterward.

## Frozen deliverables

| Deliverable | Android-only | Mac-only | Connected |
|---|:---:|:---:|:---:|
| D1 — source digests verified | ✓ | ✓ | ✓ |
| D2 — all five documents OCRed | — | ✓ | ✓ |
| D3 — all five claim-quality gates passed | — | ✓ | ✓ |
| D4 — deterministic claim chart produced | — | ✓ | ✓ |
| D5 — semantic claim-text triage produced | — | — | ✓ |
| D6 — audit chain verified | ✓ | ✓ | ✓ |

## Threshold evaluation

- Relative utility lift over best solo: **20%**; required ≥15% — **pass**
- Connected anchor recall: **0.95**; required ≥0.90 — **pass**
- Connected latency: **95.754 seconds**; required ≤600 — **pass**
- Connected claim-quality gates: **5/5** — **pass**
- Connected audit chain: **valid, 8 events** — **pass**

## Decision

Do not discard the implementation solely for lack of workflow value: it demonstrated a bounded operational advantage under the actual security constraint. Do stop treating that result as proof of scientific superadditivity or broad novelty. The next investment gate should be external value—whether a real user will pay for or repeatedly use the audited distributed workflow—not another internally defined integration metric.

A post-run Jev decision check assigned 0.77 probability that the evidence supports a bounded operational advantage, 0.09 probability that it establishes scientific superadditivity, and selected a bounded customer-value gate over either immediate abandonment or a continued novelty push with 0.99 probability. These are calibrated judgment signals, not additional experimental observations.

## Limitations

- This is one fixed five-document corpus and one run per mode; it does not estimate variance.
- Mac elapsed time has one-second resolution; connected timing has millisecond resolution.
- The utility is a pre-registered six-deliverable operational score, not a universal scientific utility measure.
- Mac-only lacked semantic triage because of credential placement, not an inherent hardware limitation.
- Anchor recall checks 20 material phrases, not complete legal-text transcription.
- OCR omitted some printed claim-number labels; segment counts are not authoritative legal claim counts.
- Jev outputs are technical triage signals, not legal conclusions.

Machine-readable results are in [`workflow_benchmark_results.json`](workflow_benchmark_results.json).
