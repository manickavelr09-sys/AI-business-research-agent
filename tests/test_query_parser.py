from research_agent.query_parser import infer_industry, parse_user_query


def test_parse_category_and_location() -> None:
    query = parse_user_query("Cardiologists in Birmingham")
    assert query.category == "Cardiologists"
    assert query.location == "Birmingham"


def test_parse_near_location() -> None:
    query = parse_user_query("best family lawyers near Chicago")
    assert query.category == "family lawyers"
    assert query.location == "Chicago"


def test_infer_industry() -> None:
    assert infer_industry("Dentists") == "healthcare"
    assert infer_industry("Family lawyers") == "legal"
    assert infer_industry("Roofing contractors") == "trades"
