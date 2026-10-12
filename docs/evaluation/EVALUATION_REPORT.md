# Evaluation report — ClaimGuard AI (Phase 2)

_Generated 2026-10-12 by `apps/api/scripts/make_eval_report.py`. All numbers are computed, not typed._

## 1. Reproducibility

- Commit: `5ea88b9`
- Ruleset fingerprint (sha256 of rule files, first 16): `eaffef595d3ccd64`
- Command: `cd apps/api && python scripts/make_eval_report.py`
- Rulebook: fictional teaching rulebook v1.0.0 (04_Rulebook); metrics follow 07_Evaluation_and_Acceptance.

## 2. Data discipline (declaration)

- Development split: used to build and tune the rule engine. **Perfect scores on it are expected and are not evidence of generalisation.**
- A commit was frozen (tag `phase2-freeze`) before any validation run.
- Validation / stress splits: reported below only if their labelled files were available in `data/evaluation/`. If validation labels influence any later change, that change must be listed in section 6.
- Held-out inputs/labels were never available to the team.

## 3. Summary

| Split | Claims | Pairs | Macro F1 | Issue P | Issue R | Issue F1 | False-alarm | Status acc. | Claim exact | p50 / p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|
| development | 400 | 6000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 400/400 | 0.63 / 1.51 |

Metric definitions: issue = FAIL status at claim-rule level; undefined precision/recall is `null` (never 100%); an undefined per-rule F1 counts as 0 in the macro average. False-alarm rate = predicted FAIL among pairs whose expected status is not FAIL.

## 4. Split `development`

Missing pairs: 0 · extra pairs: 0 · false abstentions: 0 · missed abstentions: 0

| Rule | TP | FP | FN | Precision | Recall | F1 | Status acc. | Evidence mismatch |
|---|---|---|---|---|---|---|---|---|
| R001 | 36 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| R002 | 11 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| R003 | 28 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| R004 | 28 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| R005 | 26 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| R006 | 24 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| R007 | 23 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| R008 | 11 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| R009 | 15 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| R010 | 15 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| R011 | 10 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| R012 | 23 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| R013 | 30 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| R014 | 20 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| R015 | 19 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |

Confusion (expected → predicted):

| Expected | Predicted | Count |
|---|---|---|
| FAIL | FAIL | 319 |
| NOT_APPLICABLE | NOT_APPLICABLE | 487 |
| PASS | PASS | 5014 |
| UNABLE_TO_ASSESS | UNABLE_TO_ASSESS | 180 |

## 5. Latency

Measured in-process per claim (15 rules), single thread, on the author's machine; excludes HTTP, database and audit-log I/O. Treat as an order of magnitude.

## 6. Limitations (to keep honest)

- Synthetic, rule-based benchmark: high accuracy here says nothing about real payer data or clinical correctness.
- Evidence checks compare JSON pointer + observed value; they do not prove semantic relevance.
- Ambiguous inputs follow the rulebook literally (no trimming, case-sensitive IDs): e.g. a whitespace-only authorization id counts as present (R008); numeric strings in `quantity` give UNABLE_TO_ASSESS (R013). Real data may need a documented policy for these.
- Deterministic checks carry `confidence=null`; routing to human review is based on status and severity, not on a probability.
- Audit log is a local hash-chained file (tamper-evident, not immutable); anchors must be stored elsewhere.
- LLM-assisted explanations (if used) are evaluated separately; a model failure must never remove a deterministic finding.
