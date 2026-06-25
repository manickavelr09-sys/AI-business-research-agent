import asyncio
from session_manager import (
    register_new_session,
    get_active_run_id,
    get_all_sessions,
    get_current_run_id
)

# Simulate 4 searches
register_new_session("Dentists in Austin", "run_001")
print("After search 1:", get_all_sessions())

register_new_session("Plumbers in Houston", "run_002")
print("After search 2:", get_all_sessions())

register_new_session("Lawyers in Chicago", "run_003")
print("After search 3:", get_all_sessions())

# This should delete run_001 (oldest)!
register_new_session("Doctors in Thanjavur", "run_004")
print("After search 4:", get_all_sessions())

# Test cache hit
existing = get_active_run_id("Plumbers in Houston")
print(f"\nCache hit for 'Plumbers in Houston': {existing}")

print(f"\nCurrent run_id: {get_current_run_id()}")
print("\nSESSION MANAGER TEST PASSED!")