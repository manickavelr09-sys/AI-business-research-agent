from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.mark.anyio
async def test_rag_chat_answers_without_ollama_embeddings(monkeypatch, tmp_path) -> None:
    from research_agent.rag import pipeline, vector_store

    monkeypatch.setattr(vector_store, "RAG_INDEX_DIR", str(tmp_path))
    monkeypatch.setattr(pipeline, "register_session", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline, "touch_session", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        pipeline,
        "rag_config",
        SimpleNamespace(enabled=True, chunk_size=800, chunk_overlap=120, top_k=3),
    )

    async def unavailable_embed(text: str) -> list[float]:
        raise RuntimeError("ollama unavailable")

    async def evidence_answer(question: str, chunks: list[str]) -> str:
        return f"Evidence answer: {chunks[0]}"

    monkeypatch.setattr(pipeline, "embed", unavailable_embed)
    monkeypatch.setattr(pipeline, "generate_answer", evidence_answer)

    total_chunks = await pipeline.index_evidence(
        "live_chat_run",
        [
            {
                "text": (
                    "Business Name: ABC Dental Clinic\n"
                    "Phone: 12345\n"
                    "Address: Thanjavur\n"
                    "Services: dental clinic"
                ),
                "source_url": "https://example.com/abc",
            }
        ],
        query="dentists in thanjavur",
    )
    answer = await pipeline.answer_question("live_chat_run", "What is the phone number?")

    assert total_chunks == 1
    assert answer["retrieval_mode"] == "lexical"
    assert "12345" in answer["answer"]
    assert answer["sources"] == ["https://example.com/abc"]
