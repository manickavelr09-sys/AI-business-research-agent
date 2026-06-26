import os
import sqlite3
import numpy as np
from datetime import datetime
from .config import rag_config

RAG_INDEX_DIR = rag_config.index_dir
DB_PATH = os.path.join(RAG_INDEX_DIR, "index.db")
MAX_SESSIONS = 3

os.makedirs(RAG_INDEX_DIR, exist_ok=True)

# ── DATABASE SETUP ────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rag_sessions (
            run_id      TEXT PRIMARY KEY,
            query       TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            last_used   TEXT NOT NULL,
            access_count INTEGER DEFAULT 1,
            chunk_count  INTEGER DEFAULT 0,
            npz_path    TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print("RAG LRU DB initialized")

init_db()

# ── NPZ PATH ─────────────────────────────
def get_npz_path(run_id: str) -> str:
    return os.path.join(RAG_INDEX_DIR, f"{run_id}.npz")

# ── LRU CORE LOGIC ───────────────────────
def _evict_lru_if_needed(conn):
    """Evict least recently used session if cache is full"""
    rows = conn.execute("""
        SELECT run_id, query, npz_path 
        FROM rag_sessions 
        ORDER BY last_used ASC
    """).fetchall()

    while len(rows) >= MAX_SESSIONS:
        oldest = rows[0]
        rows = rows[1:]

        # Delete .npz file
        if os.path.exists(oldest["npz_path"]):
            os.remove(oldest["npz_path"])
            print(f"LRU EVICTED .npz: {oldest['npz_path']}")

        # Delete from SQLite
        conn.execute(
            "DELETE FROM rag_sessions WHERE run_id = ?",
            (oldest["run_id"],)
        )
        print(f"LRU EVICTED: '{oldest['query']}' → {oldest['run_id']}")

# ── PUBLIC API ────────────────────────────
def register_session(run_id: str, query: str, chunk_count: int = 0):
    """Register new search session in LRU cache"""
    conn = get_db()
    now = datetime.utcnow().isoformat()
    npz_path = get_npz_path(run_id)

    # Check if query already exists — update it
    existing = conn.execute(
        "SELECT run_id FROM rag_sessions WHERE query = ?",
        (query.lower().strip(),)
    ).fetchone()

    if existing:
        conn.execute("""
            UPDATE rag_sessions 
            SET run_id=?, last_used=?, access_count=access_count+1,
                chunk_count=?, npz_path=?
            WHERE query=?
        """, (run_id, now, chunk_count, npz_path, query.lower().strip()))
        print(f"LRU UPDATED: '{query}' → {run_id}")
    else:
        _evict_lru_if_needed(conn)
        conn.execute("""
            INSERT INTO rag_sessions 
            (run_id, query, created_at, last_used, access_count, chunk_count, npz_path)
            VALUES (?, ?, ?, ?, 1, ?, ?)
        """, (run_id, query.lower().strip(), now, now, chunk_count, npz_path))
        print(f"LRU REGISTERED: '{query}' → {run_id}")

    conn.commit()
    conn.close()
    _print_cache_state()

def touch_session(run_id: str):
    """Update last_used timestamp — called when user asks a question"""
    conn = get_db()
    now = datetime.utcnow().isoformat()
    conn.execute("""
        UPDATE rag_sessions 
        SET last_used=?, access_count=access_count+1
        WHERE run_id=?
    """, (now, run_id))
    conn.commit()
    conn.close()
    print(f"LRU TOUCHED: {run_id}")

def get_run_id_for_query(query: str) -> str | None:
    """Check if query has cached session — return run_id if found"""
    conn = get_db()
    row = conn.execute(
        "SELECT run_id FROM rag_sessions WHERE query=?",
        (query.lower().strip(),)
    ).fetchone()
    conn.close()
    if row:
        touch_session(row["run_id"])
        print(f"LRU CACHE HIT: '{query}' → {row['run_id']}")
        return row["run_id"]
    print(f"LRU CACHE MISS: '{query}'")
    return None

def get_current_run_id() -> str | None:
    """Get most recently used run_id"""
    conn = get_db()
    row = conn.execute("""
        SELECT run_id FROM rag_sessions 
        ORDER BY last_used DESC LIMIT 1
    """).fetchone()
    conn.close()
    return row["run_id"] if row else None

def get_all_sessions() -> list:
    """Get all cached sessions ordered by last used"""
    conn = get_db()
    rows = conn.execute("""
        SELECT run_id, query, created_at, last_used, 
               access_count, chunk_count
        FROM rag_sessions 
        ORDER BY last_used DESC
    """).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def clear_all():
    """Clear entire LRU cache"""
    conn = get_db()
    rows = conn.execute("SELECT npz_path FROM rag_sessions").fetchall()
    for row in rows:
        if os.path.exists(row["npz_path"]):
            os.remove(row["npz_path"])
    conn.execute("DELETE FROM rag_sessions")
    conn.commit()
    conn.close()
    print("LRU CACHE CLEARED")

def _print_cache_state():
    """Debug — print current cache state"""
    sessions = get_all_sessions()
    print(f"\n── LRU CACHE STATE ({len(sessions)}/{MAX_SESSIONS}) ──")
    for i, s in enumerate(sessions):
        print(f"  {i+1}. '{s['query']}' | used:{s['access_count']}x | last:{s['last_used'][:19]}")
    print("─────────────────────────────────\n")
