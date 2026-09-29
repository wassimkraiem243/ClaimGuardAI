from sqlalchemy import text
from sqlalchemy.orm import Session

from app.infrastructure.ollama import OllamaClient


class KnowledgeRetriever:
    def __init__(self, db: Session, ollama: OllamaClient) -> None:
        self._db = db
        self._ollama = ollama

    async def retrieve(self, query: str, category: str, top_k: int) -> list[str]:
        embedding = await self._ollama.embed(query)
        vector_literal = f"[{','.join(str(x) for x in embedding)}]"
        stmt = text(
            """
            SELECT content FROM "KnowledgeChunk"
            WHERE category = :category
            ORDER BY embedding <=> :vector::vector
            LIMIT :limit
            """
        )
        rows = self._db.execute(
            stmt,
            {"category": category, "vector": vector_literal, "limit": top_k},
        ).all()
        return [row[0] for row in rows]
