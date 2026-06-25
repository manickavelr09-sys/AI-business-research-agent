from fastapi import APIRouter
from pydantic import BaseModel
from . import pipeline
from .lru_cache import (
    get_all_sessions,
    get_current_run_id,
    get_run_id_for_query
)

router = APIRouter(prefix="/rag", tags=["rag"])

class QuestionRequest(BaseModel):
    question: str
    run_id: str | None = None
    query: str | None = None

class SearchQueryRequest(BaseModel):
    query: str

@router.post("/ask")
async def ask(request: QuestionRequest):
    """
    Ask a question about researched businesses.
    Auto-detects session from query or uses most recent.
    """
    run_id = request.run_id

    # Try to find session from query name
    if not run_id and request.query:
        run_id = get_run_id_for_query(request.query)
        if run_id:
            print(f"LRU SESSION FOUND for query: {request.query}")

    # Fall back to most recently used session
    if not run_id:
        run_id = get_current_run_id()
        if run_id:
            print(f"USING CURRENT SESSION: {run_id}")

    if not run_id:
        return {
            "answer": "No active research session found. Please search for businesses first.",
            "sources": [],
            "run_id": None,
            "hint": "Run /research/stream?query=Dentists+in+Austin first"
        }

    result = await pipeline.answer_question(run_id, request.question)
    return result

@router.post("/ask-by-query")
async def ask_by_query(search: SearchQueryRequest, question: str):
    """
    Ask about a specific previous search by query name.
    LRU will find the right session automatically.
    """
    run_id = get_run_id_for_query(search.query)
    if not run_id:
        return {
            "answer": f"No cached session for '{search.query}'. Please search again.",
            "sources": [],
            "run_id": None
        }
    return await pipeline.answer_question(run_id, question)

@router.get("/sessions")
async def get_sessions():
    """View all LRU cached sessions"""
    sessions = get_all_sessions()
    return {
        "active_sessions": len(sessions),
        "max_sessions": 3,
        "sessions": sessions,
        "note": "Last 3 searches kept. LRU evicts least recently used."
    }

@router.get("/current")
async def current_session():
    """Get most recently active session"""
    run_id = get_current_run_id()
    return {
        "current_run_id": run_id,
        "status": "active" if run_id else "no session"
    }