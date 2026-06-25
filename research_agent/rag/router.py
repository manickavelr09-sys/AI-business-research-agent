from fastapi import APIRouter
from pydantic import BaseModel
from . import pipeline
from .lru_cache import get_all_sessions, get_current_run_id, get_run_id_for_query

router = APIRouter(prefix="/rag", tags=["rag"])

class QuestionRequest(BaseModel):
    question: str
    run_id: str | None = None
    query: str | None = None

@router.post("/ask")
async def ask(request: QuestionRequest):
    run_id = request.run_id

    # Auto-detect from query if provided
    if not run_id and request.query:
        run_id = get_run_id_for_query(request.query)

    # Fall back to most recent session
    if not run_id:
        run_id = get_current_run_id()

    if not run_id:
        return {
            "answer": "No active session. Please search for businesses first.",
            "sources": [],
            "run_id": None
        }

    return await pipeline.answer_question(run_id, request.question)

@router.get("/sessions")
async def get_sessions():
    sessions = get_all_sessions()
    return {
        "active_sessions": len(sessions),
        "max_sessions": 3,
        "sessions": sessions
    }

@router.get("/current")
async def current_session():
    run_id = get_current_run_id()
    return {"current_run_id": run_id}