# Distributed claim-search run

Final source job: `patent-ocr-6a477753-d490-4467-999e-971aa46abccd`

## Roles

- **Android controller:** query expansion, source acquisition, content-addressed caching, SHA-256 manifests, dispatch, result verification, deterministic element charts, and HMAC-chained control events.
- **Mac worker:** parallel PDF rendering and Apple Vision OCR over five image-only USPTO documents.
- **Jev verification wave:** semantic technical-disclosure triage over the extracted claim text.

## Result

The authorized Mac completed Apple Vision OCR for all five documents. The final bundle was bound to manifest SHA-256 `09e75219c860402523148ef970fdc593c8aa44cf8c68f8773ee3fa3ec7d3810b`; the manifest also bound the exact worker-script hashes. Three documents ran concurrently.

The first extraction strategy could confuse numbered background lists with claims when OCR omitted the printed claim heading. The controller rejected those results rather than merging them. The corrected extractor searches backward for the final plausible claim-1 page, requires claim language and dependent references, and then re-extracted the existing OCR artifacts without rerunning recognition. Final quality gates passed for 5/5 documents, yielding 91 claim segments and 12 segments classified as independent.

Apple Vision omitted some printed claim-number labels even though the surrounding text was recovered. Accordingly, segment and independent-segment counts are extraction metrics, not authoritative legal claim counts. The landscape explicitly records this limitation.

## Semantic claim-text triage

Jev model `typesafe/jev-1.13-20260917` assessed seven fixed elements against all extracted claim text. At a 0.75 triage threshold:

- `US12596813B2` and `US12526244B2` were strongest on partitioned agents, connected verification, and deterministic policy behavior.
- `US20250328560A1` was strongest on deterministic policy behavior and tamper-evident audit records.
- None of the five reviewed claim sets crossed 0.75 for parallel typed probabilistic judgments, coalitional utility/contribution measurement, or isolated-versus-connected visualization.
- No reviewed claim set covered all seven elements.

Full calibrated probabilities and provenance are in `research/jev_claim_assessment.json`. These are technical triage signals, not legal conclusions.

## Current baseline

On the Android controller, rasterizing and OCRing a twelve-page tail from one patent failed to finish within 600 seconds. Ordinary PDF text extraction returned only page separators because the USPTO PDFs are image-only. The Mac completed the same class of work with Apple Vision. This establishes a resource/workflow difference, not superadditivity.

## Measurement

The run records:

- documents requested/completed/failed;
- source pages and OCR pages;
- elapsed execution evidence from event timestamps;
- extracted and independent-segment counts;
- source, OCR-text, claim, manifest, summary, landscape, and report digests;
- deterministic claim-element coverage; and
- calibrated semantic triage probabilities.

A positive connected result is not by itself proof of superadditivity. A controlled comparison must still measure Android-only, Mac-only, and connected workflows under the same corpus, cutoff, extraction criteria, and coordination-cost accounting.

## Audit boundary

Runtime controller events are kept in `jobs/controller-audit/<job-id>/audit.jsonl` with an HMAC chain. The final source-job audit verifies with six events. Raw patent text is excluded from the audit log; only counts and digests are recorded. OCR outputs remain local and permission-restricted. These are SOC 2-aligned audit controls, not SOC 2 certification or a patent opinion.
