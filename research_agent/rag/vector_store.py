import json, os
import numpy as np
from .config import rag_config

class VectorStore:
    def __init__(self, run_id: str):
        self.path = os.path.join(rag_config.index_dir, f"{run_id}.npz")
        os.makedirs(rag_config.index_dir, exist_ok=True)
        self.vectors: list[list[float]] = []
        self.chunks: list[str] = []
        self.sources: list[str] = []
        if os.path.exists(self.path):
            data = np.load(self.path, allow_pickle=True)
            self.vectors = data["vectors"].tolist()
            self.chunks = data["chunks"].tolist()
            self.sources = data["sources"].tolist()

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
    #test
    def search(self, query_vec: list[float], top_k: int):

        print("VECTOR COUNT:", len(self.vectors))

        if not self.vectors:
            return []

        mat = np.array(self.vectors, dtype=np.float32)
        ''' def search(self, query_vec: list[float], top_k: int) -> list[tuple[str, str, float]]:
        if not self.vectors:
            return []
        vectors=np.array(self.vectors, dtype=object)
        q = np.array(query_vec)
        sims = mat @ q / (np.linalg.norm(mat, axis=1) * np.linalg.norm(q) + 1e-8)
        top_idx = np.argsort(-sims)[:top_k]
        return [(self.chunks[i], self.sources[i], float(sims[i])) for i in top_idx] '''

    