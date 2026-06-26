from .chunking import chunk_text
from .embeddings import embed
from .vector_store import VectorStore
from .llm_ollama import generate_answer
from .config import rag_config
from .lru_cache import (
    register_session,
    touch_session,
    get_run_id_for_query,
    get_current_run_id
)

async def index_evidence(run_id: str, evidence_items: list[dict], query: str = ""):
    """Index evidence once with optional embeddings and mandatory text fallback."""
    print(f"\nINDEXING: {run_id} | items: {len(evidence_items)}")

    store = VectorStore(run_id)
    total_chunks = 0
    embedding_failures = 0

    for item in evidence_items:
        chunks = chunk_text(
            item["text"],
            rag_config.chunk_size,
            rag_config.chunk_overlap
        )
        for chunk in chunks:
            vec = None
            if rag_config.enabled:
                try:
                    vec = await embed(chunk)
                except Exception as exc:
                    embedding_failures += 1
                    if embedding_failures == 1:
                        print(f"RAG embedding unavailable, using lexical fallback: {type(exc).__name__}")
            store.add(vec, chunk, item["source_url"])
            total_chunks += 1

    store.save()

    # Register in LRU cache
    if query:
        register_session(run_id, query, chunk_count=total_chunks)

    print(f"INDEXED {total_chunks} chunks for run: {run_id}")
    return total_chunks

async def answer_question(run_id: str, question: str) -> dict:
    """Answer from stored research evidence and update LRU on access."""
    print(f"\nQUESTION: {question}")
    print(f"RUN ID: {run_id}")

    # Touch LRU when this session is accessed.
    touch_session(run_id)

    store = VectorStore(run_id)

    if not store.chunks:
        return {
            "answer": "No research data found. Please run a search first.",
            "sources": [],
            "run_id": run_id
        }

    q_vec = None
    if rag_config.enabled and store.vectors:
        try:
            q_vec = await embed(question)
        except Exception as exc:
            print(f"RAG question embedding unavailable, using lexical fallback: {type(exc).__name__}")
    results = store.search(q_vec, rag_config.top_k)
    if not results:
        results = store.lexical_search(question, rag_config.top_k)

    if not results:
        return {
            "answer": "No relevant information found in indexed data.",
            "sources": [],
            "run_id": run_id
        }

    chunks = [r[0] for r in results]
    sources = list({r[1] for r in results})
    answer = await generate_answer(question, chunks)

    return {
        "answer": answer,
        "sources": sources,
        "run_id": run_id,
        "retrieval_mode": "semantic" if q_vec is not None else "lexical"
    }
