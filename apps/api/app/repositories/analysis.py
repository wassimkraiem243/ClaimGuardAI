from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import FindingAnalysis


class FindingAnalysisRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_finding_id(self, finding_id: str) -> FindingAnalysis | None:
        return self._db.scalar(
            select(FindingAnalysis).where(FindingAnalysis.findingId == finding_id)
        )

    def upsert(self, data: dict) -> FindingAnalysis:
        existing = self.find_by_finding_id(data["findingId"])
        if existing:
            for key, value in data.items():
                if key == "id":
                    continue
                setattr(existing, key, value)
            self._db.commit()
            self._db.refresh(existing)
            return existing

        record = FindingAnalysis(**data)
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return record

    @staticmethod
    def to_response(record: FindingAnalysis) -> dict:
        return {
            "findingId": record.findingId,
            "status": record.status,
            "explanation": record.explanation,
            "suggestedFix": record.suggestedFix,
            "priority": record.priority,
            "confidence": record.confidence,
            "isLikelyFalsePositive": record.isLikelyFalsePositive,
            "falsePositiveReasoning": record.falsePositiveReasoning,
            "groundingSource": record.groundingSource,
            "modelUsed": record.modelUsed,
            "responseTimeMs": record.responseTimeMs or 0,
        }
