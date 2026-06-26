import os
import re
import numpy as np
from .lru_cache import RAG_INDEX_DIR

os.makedirs(RAG_INDEX_DIR, exist_ok=True)

class VectorStore:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.path = os.path.join(RAG_INDEX_DIR, f"{run_id}.npz")
        self.vectors: list[list[float]] = []
        self.chunks: list[str] = []
        self.sources: list[str] = []

        if os.path.exists(self.path):
            data = np.load(self.path, allow_pickle=True)
            self.vectors = data["vectors"].tolist() if "vectors" in data else []
            self.chunks = data["chunks"].tolist() if "chunks" in data else []
            self.sources = data["sources"].tolist() if "sources" in data else []
            print(f"VECTOR STORE LOADED: {run_id} ({len(self.vectors)} vectors)")

    def add(self, vector: list[float] | None, chunk: str, source_url: str):
        if vector:
            self.vectors.append(vector)
        self.chunks.append(chunk)
        self.sources.append(source_url)

    def save(self):
        np.savez(
            self.path,
            vectors=np.array(self.vectors, dtype=object),
            chunks=np.array(self.chunks, dtype=object),
            sources=np.array(self.sources, dtype=object),
        )
        print(f"VECTOR STORE SAVED: {self.run_id} ({len(self.vectors)} vectors)")

    def search(self, query_vec: list[float] | None, top_k: int):
        if query_vec is None:
            return []
        if not self.vectors:
            return []
        if len(self.vectors) != len(self.chunks):
            return []
        mat = np.array(self.vectors, dtype=np.float32)
        q = np.array(query_vec, dtype=np.float32)
        norms = np.linalg.norm(mat, axis=1)
        q_norm = np.linalg.norm(q)
        norms = np.where(norms == 0, 1e-8, norms)
        q_norm = q_norm if q_norm != 0 else 1e-8
        sims = mat @ q / (norms * q_norm)
        top_idx = np.argsort(-sims)[:top_k]
        results = [(self.chunks[i], self.sources[i], float(sims[i])) for i in top_idx]
        print(f"SEARCH RESULTS: {len(results)} chunks found")
        return results

    def lexical_search(self, question: str, top_k: int):
        if not self.chunks:
            return []
        query_terms = _tokens(question)
        if not query_terms:
            return [(chunk, self.sources[index] if index < len(self.sources) else "", 0.0) for index, chunk in enumerate(self.chunks[:top_k])]
        scored = []
        for index, chunk in enumerate(self.chunks):
            terms = _tokens(chunk)
            if not terms:
                continue
            overlap = query_terms & terms
            score = len(overlap) / max(len(query_terms), 1)
            if score:
                score += min(len(overlap), 6) * 0.05
            scored.append((score, index, chunk))
        scored.sort(reverse=True)
        if not scored or scored[0][0] == 0:
            scored = [(0.0, index, chunk) for index, chunk in enumerate(self.chunks)]
        return [
            (chunk, self.sources[index] if index < len(self.sources) else "", float(score))
            for score, index, chunk in scored[:top_k]
        ]


def _tokens(value: str) -> set[str]:
    stop_words = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
        "is", "it", "of", "on", "or", "the", "this", "to", "with", "what",
        "which", "who", "where", "show", "give", "list",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]{2,}", value.lower())
        if token not in stop_words
    }
