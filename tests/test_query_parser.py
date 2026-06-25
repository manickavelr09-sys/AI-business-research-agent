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


def test_parse_corrects_common_category_typos() -> None:
    query = parse_user_query("cardialagist in thanjavur")
    assert query.category == "cardiologists"
    assert query.location == "thanjavur"


def test_parse_region_first_query_without_in() -> None:
    query = parse_user_query("kerala dentists")
    assert query.category == "dentists"
    assert query.location == "kerala"


def test_parse_region_last_query_without_in() -> None:
    query = parse_user_query("dentists kerala")
    assert query.category == "dentists"
    assert query.location == "kerala"


def test_parse_multi_word_region_first_query_without_in() -> None:
    query = parse_user_query("west bengal dentists")
    assert query.category == "dentists"
    assert query.location == "west bengal"
