# Pre-registered bounded workflow benchmark

Registered: 2026-10-14 UTC, before the fresh benchmark runs.

## Decision

Determine whether the connected Android-controller/Mac-worker workflow delivers at least 15% more end-to-end operational utility than the better solo workflow on a fixed five-document patent-claim task. This tests deployment value, not scientific novelty, patentability, or intrinsic hardware superiority.

## Fixed corpus

The five image-only USPTO PDFs already bound by the OCR manifest:

- `US12526244B2`
- `US12596813B2`
- `US20220210200A1`
- `US20250259042A1`
- `US20250328560A1`

All modes use the same source bytes, SHA-256 checks, 25-page tail window, three-worker maximum, claim extractor, quality gates, deterministic seven-element chart, and 600-second end-to-end cap. Runtime OCR text remains local.

## Modes

1. **Android-only:** Android verifies sources, renders with Poppler at 150 DPI, recognizes text with Tesseract, extracts claims, charts elements, performs controller-side Jev semantic triage, and writes a local HMAC-chained audit.
2. **Mac-only:** Mac verifies sources, uses Apple Vision OCR, extracts claims, and charts elements. Under the deployed least-privilege policy, controller credentials are not copied to the Mac, so the semantic-triage deliverable is unavailable. The Mac writes its own local HMAC-chained audit.
3. **Connected:** Android verifies and dispatches a content-addressed bundle, Mac runs Apple Vision OCR, Android verifies and charts returned results, controller-side Jev performs semantic triage, and the controller audit covers handoff and outputs. Transfer and orchestration time count toward latency.

The Mac-only credential restriction is an operational deployment constraint, not an inherent limitation of Mac hardware. Results therefore support only a workflow decision.

## Frozen deliverables and utility

Each completed deliverable is worth one point:

- D1: all five source SHA-256 digests verified;
- D2: all five documents produce OCR text;
- D3: all five documents pass frozen claim-region quality gates;
- D4: a deterministic seven-element claim chart is produced;
- D5: seven-element semantic claim-text triage is produced;
- D6: the mode's audit chain verifies.

Utility is completed points divided by six. Missing, failed, or post-cap deliverables receive zero. The connected workflow wins only if:

- its utility is at least 1.15 times the better solo utility;
- all connected hard-quality gates pass;
- OCR anchor recall is at least 0.90; and
- total latency, including coordination, is no more than 600 seconds.

If the best solo utility is 1.0, connected cannot win. If the connected workflow does not win, stop treating cross-device composition as a demonstrated practical advantage for this task.

## Accuracy anchors

Twenty manually selected phrases—four per document—are checked after case-folding and removing punctuation and whitespace. Anchor recall is matches divided by 20.

| Publication | Anchors |
|---|---|
| US12526244B2 | privacy-preserving evaluations of artificial intelligence agents; machine-readable data structure; first transformation operation set; verification record |
| US12596813B2 | non-transitory computer-readable storage medium; plurality of observing agents; conflict-resolution rule set; auditable ledger |
| US20220210200A1 | automated cybersecurity defensive strategy; recommendation engine; endpoint agents; network packet capturing devices |
| US20250259042A1 | platform for orchestrating a scalable privacy-enabled network; collaborative and negotiating agents; hierarchical memory structure; common token space |
| US20250328560A1 | securing inter-process communications; permission validation; immutable blockchain registry; tamper-proof audit trails |

These anchors test retrieval of material claim phrases, not complete legal-text transcription or claim construction.

## Reported metrics

For each mode: elapsed wall time, documents completed, quality-passing documents, extracted claim segments, anchor recall, deliverables, utility, failures, and coordination time where applicable. No result will be relabeled as scientific superadditivity solely because a thresholded workflow utility is positive.
