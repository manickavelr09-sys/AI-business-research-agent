import os
from dataclasses import dataclass
from pathlib import Path


def _default_index_dir() -> str:
    if os.getenv("VERCEL"):
        return "/tmp/research_agent_rag"
    return ".cache/rag_index"


def _index_dir() -> str:
    configured = os.getenv("RAG_INDEX_DIR", "").strip()
    if not configured:
        return _default_index_dir()
    if os.getenv("VERCEL"):
        configured_path = Path(configured)
        if not configured_path.is_absolute() or not configured.startswith("/tmp/"):
            return "/tmp/research_agent_rag"
    return configured


@dataclass(frozen=True)
class RagConfig:
    enabled: bool = os.getenv("RAG_ENABLED", "false").lower() == "true"
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    llm_model: str = os.getenv("OLLAMA_LLM_MODEL", "mistral")
    embed_model: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    chunk_size: int = int(os.getenv("RAG_CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))
    top_k: int = int(os.getenv("RAG_TOP_K", "6"))
    index_dir: str = _index_dir()

rag_config = RagConfig()
