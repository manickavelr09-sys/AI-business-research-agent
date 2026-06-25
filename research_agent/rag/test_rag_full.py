import asyncio
from embeddings import embed
from vector_store import VectorStore
from llm_ollama import generate_answer
from config import rag_config

async def test():
    run_id = "test_run_001"
    
    # Step 1 — Create store and add test data
    store = VectorStore(run_id)
    
    test_texts = [
        "38th Street Dental phone (512) 458-6222 address 1500 W 38th St Austin TX rating 4.5",
        "Smiles of Austin phone (512) 451-8310 website smilesofaustin.com open Monday to Friday",
        "Breeze Dental phone (512) 828-7659 address 4501 Spicewood Springs Rd Austin TX rating 4.8",
    ]
    
    print("STEP 1: Embedding and storing...")
    for i, text in enumerate(test_texts):
        vec = await embed(text)
        store.add(vec, text, f"https://source{i}.com")
        print(f"  Added chunk {i+1} — vector size: {len(vec)}")
    
    store.save()
    print(f"SAVED {len(store.vectors)} vectors")
    
    # Step 2 — Search
    print("\nSTEP 2: Searching...")
    question = "Which dentist has the best rating?"
    q_vec = await embed(question)
    results = store.search(q_vec, top_k=3)
    print(f"Found {len(results)} results")
    
    # Step 3 — Generate answer
    print("\nSTEP 3: Generating answer...")
    chunks = [r[0] for r in results]
    answer = await generate_answer(question, chunks)
    print(f"\nQUESTION: {question}")
    print(f"ANSWER: {answer}")
    print("\nRAG FULL TEST PASSED!")

asyncio.run(test())