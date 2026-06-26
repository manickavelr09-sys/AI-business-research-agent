import json
import os
from urllib.parse import urlparse

import httpx
from .config import rag_config
from research_agent.config import settings

SYSTEM_PROMPT = (
    "You answer only from the evidence snippets provided. "
    "If the evidence doesn't contain the answer, say so. "
    "Never invent business facts not present in the evidence."
)

async def generate_answer(question: str, context_chunks: list[str]) -> str:
    context = "\n\n".join(f"[{i+1}] {c}" for i, c in enumerate(context_chunks))
    hosted_answer = await _hosted_llm_answer(question, context)
    if hosted_answer:
        return hosted_answer
    if _ollama_is_remote_or_local_allowed():
        try:
            return await _ollama_answer(question, context)
        except Exception as exc:
            print(f"Ollama RAG answer unavailable: {type(exc).__name__}")
    return _deterministic_answer(question, context_chunks)


async def _hosted_llm_answer(question: str, context: str) -> str:
    if not settings.llm_api_key:
        return ""
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Evidence:\n{context[:12000]}\n\nQuestion: {question}"},
        ],
        "temperature": 0,
    }
    url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            )
        if resp.status_code >= 400:
            print(f"Hosted RAG LLM failed with status {resp.status_code}: {resp.text[:200]}")
            return ""
        content = resp.json()["choices"][0]["message"]["content"]
        return str(content).strip()
    except (KeyError, json.JSONDecodeError, httpx.HTTPError) as exc:
        print(f"Hosted RAG LLM unavailable: {type(exc).__name__}")
        return ""


async def _ollama_answer(question: str, context: str) -> str:
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


def _ollama_is_remote_or_local_allowed() -> bool:
    host = urlparse(rag_config.ollama_base_url).hostname or ""
    if settings.host and host in {"127.0.0.1", "localhost"}:
        return not bool(os.getenv("VERCEL"))
    return True


def _deterministic_answer(question: str, context_chunks: list[str]) -> str:
    if not context_chunks:
        return "I could not find matching evidence in this research run."
    bullets = []
    for chunk in context_chunks[:5]:
        line = " ".join(chunk.split())
        bullets.append(f"- {line[:350]}")
    return (
        "I found the following evidence from this research run. "
        "No external facts were added.\n" + "\n".join(bullets)
    )
