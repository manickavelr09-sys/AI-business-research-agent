from research_agent.orchestrator import _candidate_collection_goal, _enrichment_collection_goal


def test_small_requested_limit_overcollects_before_dedupe() -> None:
    assert _candidate_collection_goal(5) == 60
    assert _candidate_collection_goal(10) == 120


def test_larger_requested_limit_still_scales() -> None:
    assert _candidate_collection_goal(25) == 300
    assert _candidate_collection_goal(200) == 1000
    assert _candidate_collection_goal(250) == 1250


def test_enrichment_is_capped_for_speed() -> None:
    assert _enrichment_collection_goal(5) == 5
    assert _enrichment_collection_goal(50) == 40
    assert _enrichment_collection_goal(200) == 80
