from .chunking import chunk_text
from .embeddings import embed
from .vector_store import VectorStore
from .llm_ollama import generate_answer
from .config import rag_config

async def index_evidence(run_id: str, evidence_items: list[dict]):
    print("INDEX_EVIDENCE CALLED")
    print("\nINDEXING RUN:", run_id)
    print("EVIDENCE ITEMS:", len(evidence_items))

    store = VectorStore(run_id)

    total_chunks = 0

    for item in evidence_items:

        chunks = chunk_text(
            item["text"],
            rag_config.chunk_size,
            rag_config.chunk_overlap
        )

        print("CHUNKS:", len(chunks))

        for chunk in chunks:

            vec = await embed(chunk)

            print("VECTOR SIZE:", len(vec))

            store.add(
                vec,
                chunk,
                item["source_url"]
            )

            total_chunks += 1

    print("TOTAL CHUNKS:", total_chunks)

    store.save()

    print("VECTOR STORE SAVED")


''' async def answer_question(run_id: str, question: str) -> dict:
    if not rag_config.enabled:
        return {"error": "RAG is disabled. Set RAG_ENABLED=true and configure Ollama."}
    store = VectorStore(run_id)
    q_vec = await embed(question)
    results = store.search(q_vec, rag_config.top_k)
    chunks = [r[0] for r in results]
    sources = list({r[1] for r in results})
    answer = await generate_answer(question, chunks)
    return {"answer": answer, "sources": sources}'''
#Test teh rag connection
async def answer_question(run_id: str, question: str):

    print("\nQUESTION:", question)
    print("RUN ID:", run_id)

    store = VectorStore(run_id)

    q_vec = await embed(question)

    results = store.search(
        q_vec,
        rag_config.top_k
    )

    print("RESULTS FOUND:", len(results))

    for r in results:
        print(r)

    chunks = [r[0] for r in results]

    sources = list({r[1] for r in results})

    answer = await generate_answer(
        question,
        chunks
    )

    print("ANSWER:", answer)

    return {
        "answer": answer,
        "sources": sources
    }