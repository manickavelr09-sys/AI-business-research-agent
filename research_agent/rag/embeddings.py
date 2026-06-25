import httpx
from .config import rag_config

async def embed(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{rag_config.ollama_base_url}/api/embeddings",
            json={"model": rag_config.embed_model, "prompt": text},
        )
        resp.raise_for_status()
        return resp.json()["embedding"]

async def embed_many(texts: list[str]) -> list[list[float]]:
    return [await embed(t) for t in texts]  # Ollama has no native batch endpoint