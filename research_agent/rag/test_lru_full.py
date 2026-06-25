# test_lru_full.py
from lru_cache import (
    register_session, touch_session,
    get_run_id_for_query, get_all_sessions,
    get_current_run_id, clear_all
)
import time

print("=== LRU CACHE FULL TEST ===\n")

# Clear first
clear_all()

# Register 3 searches
register_session("run_001", "Dentists in Austin", chunk_count=45)
time.sleep(0.1)
register_session("run_002", "Plumbers in Houston", chunk_count=38)
time.sleep(0.1)
register_session("run_003", "Lawyers in Chicago", chunk_count=52)

print("\n--- After 3 searches ---")

# Access Austin (moves to recently used!)
time.sleep(0.1)
touch_session("run_001")
print("Touched run_001 (Dentists in Austin)")

# Add 4th search — should evict LEAST recently used
# Houston (run_002) should be evicted since Austin was just touched!
time.sleep(0.1)
register_session("run_004", "Doctors in Thanjavur", chunk_count=29)

print("\n--- After 4th search ---")
sessions = get_all_sessions()
queries = [s['query'] for s in sessions]
print(f"Remaining: {queries}")

assert "plumbers in houston" not in queries, "Houston should be evicted!"
assert "dentists in austin" in queries, "Austin should still be here!"
print("\n✅ LRU eviction correct — Houston evicted, Austin kept!")

# Test cache hit
hit = get_run_id_for_query("Lawyers in Chicago")
print(f"\nCache hit for Chicago: {hit}")
assert hit == "run_003"
print("✅ Cache hit working!")

print(f"\nCurrent (most recent): {get_current_run_id()}")
print("\n=== LRU FULL TEST PASSED! ===")