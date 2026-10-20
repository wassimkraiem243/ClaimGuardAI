# ClaimGuard AI — Project conception (team edition)

**Challenge:** CSTAM-VELODOC · Trustworthy agentic copilot for healthcare claim **pre-validation**  
**Scoring target:** 50 (Phase 1) + 30 (Phase 2) + up to 10 bonus  
**Authoritative requirements:** `ClaimGuardAI_Student_Starter_Pack/` (v1.0.0, Sept 2026)  
**Diagrams (Phase 1):** [docs/architecture/README.md](../docs/architecture/README.md)

> This file supersedes the exported HTML in `Conceptions/ClaimGuard.html` where it conflicts with the student pack.

---

## 1. Product framing

ClaimGuard is a **pre-submission gate** for claims officers: normalize the package, run **15 fictional payer rules**, show evidence and corrective actions, route uncertainty to humans, and log everything in a tamper-evident audit trail.

**Pitch line:** Administrative errors caught early—with exact field-level evidence, clear fixes, human escalation when unsure, and an auditable trail.

---

## 2. Scoring → deliverables

| ID | Area | Pts | Artifact |
|----|------|-----|----------|
| P1.1 | Ingestion & normalization | 15 | JSONL/CSV + FHIR example → claim envelope |
| P1.2 | Rule engine | 15 | R001–R015, all statuses incl. UNABLE / N/A |
| P1.3 | Structured output | 10 | `result.schema.json` compliance |
| P1.4 | Audit log | 10 | Hash chain + `verify` + demo |
| P1.D | Docs & demo | — | `docs/architecture/*`, video, README |
| P2.* | Quality, HITL, security | 30 | Evaluation + review polish + threat model |

Full checklist: [docs/deliverables/PHASE1_CHECKLIST.md](../docs/deliverables/PHASE1_CHECKLIST.md).

---

## 3. Architecture (summary)

See [system-architecture.md](../docs/architecture/system-architecture.md) for the full Mermaid diagram and trust boundaries.

- **apps/web** — review console (queue, evidence, actions).  
- **apps/api** — ingest, policy resolve, rule engine, explanation adapter, audit.  
- **packages/shared-types** — DTOs mirroring pack schemas.  
- **Postgres** — runs, results, reviews; **ledger** — append-only hash chain.

Orchestration is a **fixed pipeline** (ingest → policy → 15 rules → optional explain → queue). LangGraph is optional if the graph matches [validation-pipeline.md](../docs/architecture/validation-pipeline.md).

---

## 4. Data flow

See [data-flow.md](../docs/architecture/data-flow.md).

Critical grading point: audit writes on **each** transition, not one blob at the end.

---

## 5. Domain model

See [domain-model.md](../docs/architecture/domain-model.md).

**Correction:** Use the pack **ClaimEnvelope** and **RuleResult**, not the pre-pack `CanonicalClaim` / `CG-R010` examples.

---

## 6. Rule catalogue (R001–R015)

Source: `ClaimGuardAI_Student_Starter_Pack/rules/rules.json` and `docs/04_Rulebook.md`.

| Rule | Title (short) | Severity |
|------|---------------|----------|
| R001 | Required claim information | high |
| R002 | Service vs submission dates | high |
| R003 | Coverage active on service date | high |
| R004 | Member / beneficiary consistency | high |
| R005 | Provider in network | high |
| R006 | Possible duplicate service lines | medium |
| R007 | Line arithmetic | high |
| R008 | Required authorization reference | high |
| R009 | Authorization record matches service | high |
| R010 | Required supporting document | medium |
| R011 | Service code in fictional catalogue | high |
| R012 | Claim total equals line amounts | high |
| R013 | Quantity and price limits | medium |
| R014 | Submission window | medium |
| R015 | Currency matches policy | high |

(Exact logic strings live in `rules.json`; implement against `expected_results.jsonl`, not prose paraphrase.)

**Removed from early conception:** sixteenth rule, NCCI/Luhn/NPI rules, hybrid dx↔CPT LLM rule as a separate scorer—the pack keeps diagnosis/service checks **deterministic** on fictional catalogues.

---

## 7. AI scope (Phase 1)

**One** bounded capability (pack MVP #6):

- Plain-language **explanation** or reviewer handover from **validated findings only**.
- Prompt: `prompts/explain_findings.md`; adapter pattern: `llm_adapter.py`.
- Output JSON: explanation, `cited_evidence_paths`, `cited_rule_ids`, `needs_human_review`.
- On failure: keep deterministic results; show fallback message.

The LLM **must not** change `status` on any `RuleResult`.

---

## 8. Audit engine (prototype)

- `entry_hash = SHA256(seq ‖ ts ‖ event_type ‖ actor ‖ canonical_json(payload) ‖ prev_hash)`
- Events: `INGEST_*`, `NORMALIZED`, `RULE_EVALUATED`, `AI_*`, `HUMAN_REVIEW`, …
- Demo: tamper one byte → `verify` fails (worth showing in video).

Production note: immutability, access control, and retention called out in Phase 2 security deliverable.

---

## 9. Human review

MVP actions (pack):

- confirm  
- dismiss (with reason)  
- request information  
- corrected-for-recheck (new version / re-run; preserve original)

Phase 2 expands routing, RBAC, and override analytics.

---

## 10. Repository layout (this monorepo)

```
ClaimGuardAI/
├── apps/api/          FastAPI
├── apps/web/          Next.js
├── packages/shared-types/
├── data/              synthetic inputs (sync from pack when implementing)
├── docs/architecture/ Phase 1 diagrams
├── docs/deliverables/ checklists, work plan, video script
├── ClaimGuardAI_Student_Starter_Pack/   reference pack (read-only)
└── Conceptions/       this file + legacy HTML export
```

Early conception proposed `backend/` + `rules/payer_alpha.yaml`—**not** used; mirror pack JSON rule files under `data/payer-rules/` or load from pack path in dev.

---

## 11. Work plan & demo

- Plan: [docs/deliverables/WORK_PLAN.md](../docs/deliverables/WORK_PLAN.md)  
- Demo script (suggested 7 min in pack): clean claim → failures → uncertainty → AI explanation fallback → audit → metrics/limitations.

---

## 12. First documentation commits (no app code yet)

1. Architecture + data-flow diagrams under `docs/architecture/`.  
2. Phase 1 checklist + work plan under `docs/deliverables/`.  
3. This conception file aligned to student pack.

Implementation commits follow: schemas frozen → audit core → ingest → rules.
