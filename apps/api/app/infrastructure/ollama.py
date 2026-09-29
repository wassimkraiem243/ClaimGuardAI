import httpx

from app.config import settings


class OllamaClient:
    def __init__(self) -> None:
        self._base = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model
        self._embed_model = settings.ollama_embed_model

    async def generate_json(self, prompt: str) -> tuple[str, int, int | None]:
        started = __import__("time").time()
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                f"{self._base}/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
            )
            res.raise_for_status()
            data = res.json()
        duration_ms = int((__import__("time").time() - started) * 1000)
        return data["response"], duration_ms, data.get("eval_count")

    async def embed(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                f"{self._base}/api/embed",
                json={"model": self._embed_model, "input": text},
            )
            res.raise_for_status()
            data = res.json()
        vector = data.get("embeddings", [None])[0] or data.get("embedding")
        if not isinstance(vector, list):
            raise RuntimeError("Ollama embed response missing embedding vector")
        return vector
