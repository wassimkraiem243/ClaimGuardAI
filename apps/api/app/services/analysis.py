import json
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.infrastructure.knowledge import KnowledgeRetriever
from app.infrastructure.ollama import OllamaClient
from app.mappers.findings import (
    build_ai_narrative,
    finding_context_from_row,
    to_unified_finding,
)
from app.repositories.analysis import FindingAnalysisRepository
from app.repositories.store import FindingRepository

DEFAULT_RAG_CATEGORY = "payer-policy"


async def enrich_finding(db: Session, ai_finding: dict) -> dict:
    ollama = OllamaClient()
    retriever = KnowledgeRetriever(db, ollama)
    category = (ai_finding.get("category") or DEFAULT_RAG_CATEGORY).lower()
    query = " ".join(
        x
        for x in [
            ai_finding.get("title"),
            ai_finding.get("description"),
            ai_finding.get("ruleId"),
        ]
        if x
    )
    chunks = await retriever.retrieve(query, category, 3)
    if not chunks:
        chunks = await retriever.retrieve(query, DEFAULT_RAG_CATEGORY, 2)
    if chunks:
        return {
            **ai_finding,
            "groundingSource": "rag",
            "groundingContent": chunks,
        }
    return {**ai_finding, "groundingSource": "none", "groundingContent": []}


def build_finding_analysis_prompt(finding: dict) -> str:
    lines = [
        "You are a healthcare claims administrative reviewer. Explain validation issues only — do not give clinical advice.",
        "",
        "FINDING:",
        f"[id: {finding['id']}] [{finding['category']}] [{finding['severity']}] {finding['title']}",
        f"Narrative: {finding['narrative']}",
    ]
    if finding.get("description"):
        lines.append(f"Description: {finding['description']}")
    if finding.get("groundingContent"):
        lines.append(
            f"Grounding ({finding['groundingSource']}): {' | '.join(finding['groundingContent'])}"
        )
    else:
        lines.append("Grounding: none — use general knowledge, note lower confidence")
    lines.extend(
        [
            "",
            "Respond with JSON only:",
            '{"explanation":"...","suggestedFix":"...","priority":"high|medium|low",'
            '"confidence":"high|medium|low","isLikelyFalsePositive":false,'
            '"falsePositiveReasoning":null}',
        ]
    )
    return "\n".join(lines)


async def analyze_finding(
    db: Session, finding_id: str, force: bool = False
) -> dict:
    findings = FindingRepository(db)
    analysis_repo = FindingAnalysisRepository(db)

    if not force:
        existing = analysis_repo.find_by_finding_id(finding_id)
        if existing and existing.status == "completed":
            return FindingAnalysisRepository.to_response(existing)

    row = findings.find_by_id_with_context(finding_id)
    if not row:
        raise HTTPException(status_code=404, detail=f'Finding "{finding_id}" not found.')

    finding, scan = row
    ctx = finding_context_from_row(finding, scan)
    unified = to_unified_finding(ctx)
    ai_finding = {**unified, "narrative": build_ai_narrative(ctx)}
    enriched = await enrich_finding(db, ai_finding)

    ollama = OllamaClient()
    prompt = build_finding_analysis_prompt({**enriched, "narrative": ai_finding["narrative"]})
    raw, duration_ms, eval_count = await ollama.generate_json(prompt)
    parsed = json.loads(raw)

    now = datetime.now(timezone.utc)
    record = analysis_repo.upsert(
        {
            "id": str(uuid.uuid4()),
            "findingId": finding_id,
            "explanation": parsed["explanation"],
            "suggestedFix": parsed["suggestedFix"],
            "priority": parsed["priority"],
            "confidence": parsed["confidence"],
            "isLikelyFalsePositive": parsed["isLikelyFalsePositive"],
            "falsePositiveReasoning": parsed.get("falsePositiveReasoning"),
            "groundingSource": enriched["groundingSource"],
            "modelUsed": settings.ollama_model,
            "promptTokens": eval_count,
            "responseTimeMs": duration_ms,
            "status": "completed",
            "errorMessage": None,
            "createdAt": now,
            "updatedAt": now,
        }
    )
    return FindingAnalysisRepository.to_response(record)


def get_finding_analysis(db: Session, finding_id: str) -> dict:
    analysis_repo = FindingAnalysisRepository(db)
    record = analysis_repo.find_by_finding_id(finding_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f'No analysis stored for finding "{finding_id}". Trigger POST /analysis/findings/{finding_id} first.',
        )
    return FindingAnalysisRepository.to_response(record)
