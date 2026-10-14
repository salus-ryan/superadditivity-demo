# Silo Swarm prior-art review

**Search date:** 2026-10-14 UTC
**Scope:** scientific, technical, product/demo, secure-logging, and patent-oriented discovery
**Conclusion:** differentiated integration; no support for a broad technical or scientific novelty claim

## Executive conclusion

The search found substantial prior art for every major technical component and several systems that combine most of them. In particular:

- concurrent multi-agent incident triage with four specialist panels already exists;
- multi-agent incident-response systems with deterministic gates and tamper-evident logs already exist;
- real-time agent dashboards backed by hash-chained audit trails already exist;
- parallel/layered LLM aggregation, typed model outputs, probabilistic judging, and deterministic host composition are established patterns; and
- HMAC/hash-chained audit logging predates modern AI systems by decades.

No reviewed item matched **all** of Silo Swarm's narrow presentation choices: four evidence silos, TypeSafe/Jev typed probabilities, an isolated-versus-connected verification reveal, explicit threshold superadditivity, and data-minimized local audit evidence. That makes the project a **distinctive demonstration and integration**, but exact-match absence does not establish scientific novelty, technical novelty, or patentability.

### Claim decisions

| Claim | Finding | Confidence |
|---|---|---:|
| C1 — New scientific method/result | **Not supported.** The sealed run is an illustration, not a controlled study. | High |
| C2 — Broadly new technical architecture | **Not supported.** Close public systems combine multi-agent incident response, deterministic policy, dashboards, and cryptographic audit trails. | High |
| C3 — Distinctive demo/presentation | **Supported with qualification.** The exact visual and typed-judgment composition was not found in the reviewed set. | Medium-high |
| C4 — Novel compliance/audit mechanism | **Not supported.** Hash/HMAC chaining, signed logs, append-only audit trails, and AI-agent audit dashboards are established. | High |

A defensible public description is:

> **Silo Swarm is a visual integration demo that combines parallel typed judgments, connected evidence verification, deterministic response policy, and tamper-evident local audit evidence.**

Avoid “first,” “scientifically proves superadditivity,” “SOC 2 compliant,” or “novel architecture” without further evidence.

## Search coverage

The preregistered protocol is in [`PRIOR_ART_PROTOCOL.md`](PRIOR_ART_PROTOCOL.md). The reproducible metadata is in [`prior_art_results.json`](prior_art_results.json).

| Source | Queries | Raw results | Unique records |
|---|---:|---:|---:|
| OpenAlex | 10 | 200 | 196 |
| General web/Bing RSS | 14 | 137 | 107 |
| Google Patents | 5 | 50 | 46 |
| GitHub repositories | 5 initial queries | 45 | 45 |
| **Total discovery set** | **34** | **432** | **394 within-source unique** |

Six follow-up GitHub queries targeted exact combinations such as `multi-agent dashboard tamper-evident` and `incident response multi-agent tamper-evident`. Primary READMEs were then inspected for the closest systems. Primary documentation and source pages were checked for TypeSafe, Mixture-of-Agents, LangGraph, AutoGen Studio, RFC 5848, NIST SP 800-92, and foundational secure-audit logging.

## Closest public implementations

### 1. On-Call Copilot: Multi-Agent Incident Triage

**Overlap:** four specialist agents run concurrently over alerts, logs, metrics, and runbook excerpts; they produce structured root-cause analysis, actions, communications, and post-incident output; the UI displays four agent panels.

This strongly anticipates the four-way parallel incident-response presentation. It does not appear to provide Silo Swarm's typed probability primitives, connected verification reveal, superadditive utility, or HMAC chain.

- Repository: <https://github.com/leestott/On-Call-Copilot-Multi-Agent>
- Public repository creation: 2026-02-18
- Classification: **close adjacent art**

### 2. AI Incident Response Copilot

**Overlap:** specialist-agent orchestration, cloud incident investigation, dashboard, tool boundaries, role-based access, approval gates, and tamper-evident accountability.

This is one of the closest end-to-end combinations. Its purpose and governance structure overlap heavily even though the Jev judgment interface and silo/superadditivity framing differ.

- Repository: <https://github.com/Varshini1612/ai-incident-response-copilot>
- Public repository creation: 2026-07-26
- Classification: **close adjacent art approaching direct functional overlap**

### 3. Fleetgate

**Overlap:** multi-agent incident response, a hard deterministic policy gate, proposals separated from execution, and hash-chained audit records with Merkle checkpoints, HMAC, verification, and replay.

This directly anticipates the architectural principle “models propose; deterministic code disposes; every step is verifiable.” Its simulation and audit evidence are more extensive than Silo Swarm's current sealed run. It does not use the same four-silo UI or typed Jev judgments.

- Repository: <https://github.com/Intermountainh8ter/fleetgate>
- Public repository creation: 2026-10-13 according to GitHub metadata
- Classification: **close adjacent art**

### 4. AgentGuard

**Overlap:** multi-agent security orchestration, policy-as-code decisions before execution, PII redaction, SHA-256 hash-chained audit records, and a live dashboard.

This strongly anticipates the dashboard + deterministic policy + tamper-evident logging combination, but not the incident-evidence aggregation experiment.

- Repository: <https://github.com/BROCKUGANDA/agentguard>
- Public repository creation: 2026-09-08
- Classification: **close adjacent art**

### 5. AgentLens

**Overlap:** real-time agent observability dashboard, append-only SHA-256 hash-chained events, chain verification, signed evidence export, and AI record-keeping positioning.

This directly anticipates the control-evidence panel and tamper-detection story.

- Repository: <https://github.com/agentkitai/agentlens>
- Classification: **component/close adjacent art**

### 6. Edict and RagaAI Catalyst

Edict provides a multi-agent orchestration system with a real-time dashboard and full audit trails. RagaAI Catalyst provides multi-agent tracing, timeline/execution-graph visualization, monitoring, evaluation, and a self-hosted dashboard.

- <https://github.com/cft0808/edict>
- <https://github.com/raga-ai-hub/RagaAI-Catalyst>
- Classification: **dashboard and orchestration prior art**

### 7. HMAC/hash-chain agent logging implementations

Several public implementations already describe the same core audit mechanism:

- `agent-audit-log-examples`: HMAC-linked entries and chain verification
  <https://github.com/lulzasaur9192/agent-audit-log-examples>
- Warden: deterministic tool middleware and an HMAC-chained audit log with external key-provider support
  <https://github.com/mosafariuk/warden>
- Agent Audit Trail: hash-chained JSONL with sequence-level tamper detection
  <https://github.com/kanson1996/agent-audit-trail>
- Open Agent Primitives: authorization outside the model plus signed, chained, offline-verifiable audit records
  <https://github.com/authzed/openagentprimitives>

Classification: **direct component prior art**.

## Closest scholarly work

### Parallel and layered aggregation

**Mixture-of-Agents Enhances Large Language Model Capabilities** constructs layers of multiple LLM agents in which each later agent receives the prior layer's outputs. This directly establishes parallel fan-out followed by connected aggregation as a known LLM architecture.

- Wang et al., 2024: <https://arxiv.org/abs/2406.04692>
- Classification: **foundational component prior art**

Multi-agent debate, ensemble aggregation, confidence-weighted debate, and LLM-as-a-judge are now broad literatures. The search returned surveys and multiple aggregation frameworks; Silo Swarm does not introduce the general fan-out/aggregate pattern.

### Multi-agent incident response

**Multi-Agent Collaboration in Incident Response with Large Language Models** and its AutoBnB publication compare centralized, decentralized, and hybrid LLM-agent teams for incident response.

- arXiv version: <https://arxiv.org/abs/2412.00652>
- AutoBnB DOI: <https://doi.org/10.1109/ISDFS65363.2025.11012055>

**Multi-Agent LLM Orchestration Achieves Deterministic, High-Quality Decision Support for Incident Response** reports 348 controlled trials and explicitly frames multi-agent orchestration as a source of deterministic, actionable incident-response quality.

- <https://arxiv.org/abs/2511.15755>

Classification: **close scholarly prior art for the application and deterministic decision-support claim**.

### Superadditivity and collaboration costs

**Super-additive Cooperation in Language Model Agents** studies cooperation in team-based Prisoner's Dilemma tournaments. It uses “super-additive” differently from Silo Swarm's threshold utility, but establishes explicit prior use around LLM agents.

- <https://arxiv.org/abs/2508.15510>

**The Collaboration Tax: How Much LLM Multi-Agent Systems Pay to Coordinate** formalizes team decentralization loss and max-superadditivity violations, then measures collaboration costs across models and tasks.

- <https://arxiv.org/abs/2608.22152>

These works weaken broad claims that applying superadditivity concepts to LLM-agent cooperation is itself new. They do not duplicate the visual evidence-silo demo.

### Cryptographic AI audit records

The discovery set includes several 2026 works on cryptographic records for AI agents, including:

- **The Offline Attestation Record**: signed append-only offline enterprise-AI provenance
  <https://doi.org/10.5281/zenodo.22143717>
- **Cryptographic Audit Ledgers for Autonomous Browser Agents**: hash-linked, signed action records
  <https://osf.io/7mjzg>
- **AegisAudit**: chain-linked decision governance for multi-agent systems
  <https://doi.org/10.5281/zenodo.23137187>

Some are repository or preprint records rather than mature peer-reviewed evidence, so their empirical claims should be treated cautiously. They nevertheless count as public technical disclosures relevant to novelty.

## Foundational secure-logging art

Silo Swarm's audit-chain mechanism is an application of established controls:

- Schneier and Kelsey, **Secure Audit Logs to Support Computer Forensics** (1999): forward-secure/tamper-evident audit logging
  <https://www.schneier.com/academic/archives/1999/05/secure_audit_logs_to.html>
- RFC 5848, **Signed Syslog Messages** (2010): origin authentication, integrity, replay resistance, and sequence detection
  <https://www.rfc-editor.org/rfc/rfc5848>
- NIST SP 800-92, **Guide to Computer Security Log Management**
  <https://csrc.nist.gov/pubs/sp/800/92/final>

Therefore the local HMAC chain is useful engineering and audit evidence, not a novel compliance mechanism. Keeping the HMAC key beside the log is also weaker than independent key custody or external anchoring.

## Typed and probabilistic judgment art

TypeSafe's own public API and fan-out documentation establish:

- typed `Choice`, `Score`, and `Noul` questions;
- probability-bearing answers;
- multiple independent questions in one evaluation; and
- speculative parallel fan-out followed by deterministic host selection.

- API: <https://docs.typesafe.ai/api>
- Fan-out: <https://docs.typesafe.ai/patterns/fan-out>

Silo Swarm is a creative use of these primitives, not the origin of them.

## Patent-oriented findings

The Google Patents search reviewed 50 ranked results across five queries, representing 46 unique publications. The closest surfaced families included:

- **US20250328560A1**, *Security Methods and Systems for Multi-Agent Generative AI Applications*, priority 2023-05-04. It intercepts multi-agent/tool communications, performs security and permission analysis, and approves or blocks operations.
  <https://patents.google.com/patent/US20250328560A1/en>
- **US12526244B2**, *Encrypted autonomous agent verification in multi-tiered distributed systems*, priority 2024-02-06. It concerns privacy-preserving evaluation and operative boundaries for AI agents.
  <https://patents.google.com/patent/US12526244B2/en>
- **US12596813B2**, *Autonomous agent observation and control*, priority 2023-01-19.
  <https://patents.google.com/patent/US12596813B2/en>
- **US20220210200A1**, *AI-driven defensive cybersecurity strategy analysis and recommendation system*, priority 2015-10-28.
  <https://patents.google.com/patent/US20220210200A1/en>

The ranked set did not reveal one publication whose title/snippet clearly claims Silo Swarm's complete narrow combination. That is **not a clearance conclusion**. Patent novelty depends on claims, priority dates, families, prosecution history, and combinations a skilled person would find obvious. A professional search would need CPC/IPC expansion, citation chasing, non-English families, and claim charts.

## What appears differentiated

The following narrow combination was not found as one item in the reviewed set:

1. four visually literal evidence silos;
2. TypeSafe/Jev typed probability readouts;
3. an isolated-to-connected reveal over pooled evidence;
4. an explicit threshold-utility depiction of superadditivity; and
5. a deliberately modest assurance panel that distinguishes local controls from certification.

This is best treated as **presentation and integration distinctiveness**. It may be valuable for teaching, product communication, or a conference demonstration even though the underlying architecture is not new.

The name “Silo Swarm” produced no exact software or AI repository match in the searched indexes. Because the visual concept was inspired by the television series *Silo*, public branding should avoid Apple artwork, logos, character names, or claims of affiliation. “Silo” is also an ordinary technical metaphor; this note is not trademark advice.

## What would create a research contribution

A research claim would require an experiment rather than a sealed illustration. A promising design is:

1. preregister incident tasks, evidence partitions, overlap levels, and utility;
2. compare isolated judgments, pooled one-shot judgment, multi-agent dialogue, and deterministic composition;
3. measure accuracy, calibration, action safety, latency, cost, and coordination failures;
4. estimate coalition utilities and Shapley contributions from actual outcomes;
5. test whether connected typed judgments produce statistically significant positive surplus after communication and coordination costs;
6. repeat across models, task families, and fresh held-out incidents; and
7. publish all prompts, outputs, failures, audit verification, and confidence intervals.

The potentially novel question is not whether parallel agents or hash chains exist. It is:

> **Under what evidence partitions and policy compositions do independently calibrated semantic judgments become measurably superadditive after real coordination costs?**

That question is narrower, testable, and not answered by the current demo or the closest reviewed systems.

## Bottom line

Silo Swarm is a polished and memorable synthesis. The systematic search changes the responsible label from “possibly novel architecture” to:

> **A distinctive visual integration of established multi-agent, typed-judgment, deterministic-policy, incident-response, and tamper-evident logging patterns.**

It should be demonstrated and developed, but not marketed as a first-of-kind scientific or technical invention on the current evidence.
