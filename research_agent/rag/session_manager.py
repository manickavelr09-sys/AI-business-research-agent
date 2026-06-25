import json
import os
import shutil
from datetime import datetime

SESSION_FILE = "rag/session_store.json"
MAX_SESSIONS = 3
INDEX_DIR = "rag/chroma_db"

def load_sessions() -> list:
    """Load existing sessions from file"""
    if not os.path.exists(SESSION_FILE):
        return []
    try:
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_sessions(sessions: list):
    """Save sessions to file"""
    os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
    with open(SESSION_FILE, "w") as f:
        json.dump(sessions, f, indent=2)

def get_active_run_id(query: str) -> str | None:
    """
    Check if this query already has a stored RAG session.
    If yes — return existing run_id (no re-scraping needed!)
    """
    sessions = load_sessions()
    query_lower = query.lower().strip()
    for session in sessions:
        if session["query"] == query_lower:
            print(f"RAG SESSION HIT: {query} → {session['run_id']}")
            return session["run_id"]
    return None

def register_new_session(query: str, run_id: str):
    """
    Register a new RAG session.
    Keep only last MAX_SESSIONS — delete oldest if exceeded.
    """
    sessions = load_sessions()
    query_lower = query.lower().strip()

    # Check if query already exists — update it
    for i, session in enumerate(sessions):
        if session["query"] == query_lower:
            sessions[i] = {
                "query": query_lower,
                "run_id": run_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            save_sessions(sessions)
            print(f"RAG SESSION UPDATED: {query} → {run_id}")
            return

    # Add new session
    new_session = {
        "query": query_lower,
        "run_id": run_id,
        "timestamp": datetime.utcnow().isoformat()
    }
    sessions.append(new_session)

    # If exceeded MAX_SESSIONS — delete oldest
    if len(sessions) > MAX_SESSIONS:
        oldest = sessions[0]
        sessions = sessions[1:]  # Remove oldest from list

        # Delete oldest vector store file
        old_vector_path = os.path.join(INDEX_DIR, f"{oldest['run_id']}.npz")
        if os.path.exists(old_vector_path):
            os.remove(old_vector_path)
            print(f"DELETED OLD SESSION: {oldest['query']} → {oldest['run_id']}")

    save_sessions(sessions)
    print(f"RAG SESSION REGISTERED: {query} → {run_id}")
    print(f"ACTIVE SESSIONS: {len(sessions)}/{MAX_SESSIONS}")

def get_all_sessions() -> list:
    """Return all active sessions"""
    return load_sessions()

def get_current_run_id() -> str | None:
    """Return the most recent run_id"""
    sessions = load_sessions()
    if not sessions:
        return None
    return sessions[-1]["run_id"]