import os
import numpy as np
from .config import rag_config

RAG_INDEX_DIR = rag_config.index_dir
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
            self.vectors = data["vectors"].tolist()
            self.chunks = data["chunks"].tolist()
            self.sources = data["sources"].tolist()
            print(f"VECTOR STORE LOADED: {run_id} ({len(self.vectors)} vectors)")

    def add(self, vector: list[float], chunk: str, source_url: str):
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

    def search(self, query_vec: list[float], top_k: int):
        if not self.vectors:
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
