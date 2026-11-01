# Privacy and security — ClaimGuard AI (Phase 2)

Teaching prototype for **synthetic** claim pre-validation only. Not certified for production PHI.

## Threat model (summary)

| Threat | Mitigation |
|--------|------------|
| Unauthorized API use | `x-api-key` on ingest/validate; JWT + roles on dashboard routes |
| Privilege escalation via review body | Reviewer **actor** taken from reviewer key mapping, never from JSON body |
| Audit tampering | Hash-chained JSONL; `GET /v1/audit/verify` |
| Oversized / malicious uploads | 5 MB cap; FHIR/CSV preflight rejects malformed bundles |
| Clinical harm from LLM | Pattern guards in `safety.py`; explanations are administrative only |
| Secret leakage in audit | Audit layer rejects suspicious key names and token-shaped values |

## Data minimization

- Ingest accepts synthetic pack files only in this repository workflow.
- Audit stores hashes, rule outcomes, and reviewer rationale — not full attachment text (`ATTACHMENT_RECEIVED` uses text SHA-256 only).
- Rejected uploads log error **class**, not raw claim content.

## Access control (RBAC)

| Role | Access |
|------|--------|
| API key (`dev-local-key`) | Ingest, validate, rules catalog, benchmark read, audit trace |
| Reviewer key (`REVIEWER_KEYS`) | Human decisions `POST /v1/reviews/decisions` |
| JWT `analyst` | Dashboard findings list, analysis |
| JWT `auditor` | Legacy `/claims/audit` (Postgres/file backend), audit router |
| JWT `admin` | All of the above |

## Auditability

- Rule runs: `RUN_STARTED` → per-rule results in `RUN_COMPLETED` → optional `REVIEW_DECISION`.
- External anchors: see `audit_log.anchor_line()` / evaluation report.

## Residual risks

- Local JSONL is tamper-**evident**, not WORM storage.
- API keys in `.env` must be rotated for any shared demo host.
- Perfect benchmark scores on the development split do not imply generalisation (see evaluation UI).
