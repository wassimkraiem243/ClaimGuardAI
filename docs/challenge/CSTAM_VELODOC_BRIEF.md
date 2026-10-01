# CSTAM-VELODOC — ClaimGuard AI challenge brief

> Canonical copy of the Velodoc challenge description. Source: company challenge booklet (`cstamBook.txt`).

## Challenge title

**ClaimGuard AI: Trustworthy Agentic Copilot for Healthcare Claim Pre-Validation**

| | |
|---|---|
| Reference | CSTAM-VELODOC |
| Collaborator | Velodoc Amazit |
| Mentors | Dr. Wael Hilali (CTO), Mr. Bilel Said (CEO) |

## Context

Velodoc (Amazit – FZCO) operates in HealthTech and AI-driven healthcare operational automation. The challenge targets **agentic AI**, **HL7 FHIR R4**, and **security, privacy, and auditability** for claim pre-validation before submission.

## Problem statement

Design a **human-supervised agentic copilot** that:

- Ingests **synthetic** healthcare claim packages
- Detects administrative risks and policy inconsistencies
- Produces human-understandable explanations and recommendations
- Logs all actions for auditability

Constraints: no unauthorized clinical decisions; must not disrupt existing administrative infrastructure.

## Phase 1 — MVP (50 points)

| Area | Points | Requirement |
|------|--------|-------------|
| Data ingestion & normalization | 15 | FHIR R4 JSON / CSV → consistent internal model (patient, encounter, coverage, provider, diagnosis, claim lines) |
| Deterministic & AI rule engine | 15 | Validate against fictional payer catalogue (**15 rules R001–R015** in student pack): missing, inconsistent, duplicate, unsupported data; include UNABLE_TO_ASSESS / NOT_APPLICABLE |
| Explainability & structured output | 10 | Findings: Claim ID, Rule ID, evidence, severity, confidence, corrective action |
| Audit log engine | 10 | Immutable log of checks, AI recommendations, confidence, decisions |

**Deliverables:** architecture diagram, data-flow doc, short demo video, repo with install/run instructions.

**Team copies:** See `docs/architecture/` and `docs/deliverables/PHASE1_CHECKLIST.md`. Detailed MVP behaviour and schemas live in `ClaimGuardAI_Student_Starter_Pack/docs/01_Challenge_Brief.md`.

## Phase 2 — Integration & testing (30 points)

| Area | Points | Requirement |
|------|--------|-------------|
| Detection quality | 15 | Benchmark on **50 claims**; high macro F1; low false-positive rate on valid claims |
| Human-in-the-loop | 10 | Route low-confidence / high-severity to reviewers; overrides + feedback logging |
| Privacy & security | 5 | Minimization, access control, prompt/data guards (no hallucinated clinical advice), malformed FHIR handling |

**Deliverables:** evaluation report (F1, FPR, latency, limits); privacy & security note (threat model, RBAC, audit).

## Optional bonuses (2 pts each)

- Multi-format attachment parsing (OCR/RAG for PDF notes)
- Dynamic payer-rule management GUI/API
- Active learning from human overrides
- Cryptographic / local ledger audit log
- Real-time async streaming REST / WebSocket API

## Recommended stack (non-binding)

Python (LangChain/LangGraph, FastAPI), React/Next.js, Docker, FHIR, RAG, PII anonymization, RBAC.

This repository uses a **TypeScript + Python** layout: FastAPI under `apps/api`, Next.js under `apps/web`, shared DTOs in `packages/shared-types`.
