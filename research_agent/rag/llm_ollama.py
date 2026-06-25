import httpx
from .config import rag_config

SYSTEM_PROMPT = (
    "You answer only from the evidence snippets provided. "
    "If the evidence doesn't contain the answer, say so. "
    "Never invent business facts not present in the evidence."
)

async def generate_answer(question: str, context_chunks: list[str]) -> str:
    context = "\n\n".join(f"[{i+1}] {c}" for i, c in enumerate(context_chunks))
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{rag_config.ollama_base_url}/api/chat",
            json={
                "model": rag_config.llm_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Evidence:\n{context}\n\nQuestion: {question}"},
                ],
                "stream": False,
            },
            timeout=120.0
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]