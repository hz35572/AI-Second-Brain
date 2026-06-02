from app.rag.query import build_query_plan, normalize_query, tokenize_query


def test_normalize_query_keeps_technical_tokens() -> None:
    assert normalize_query("  Telegram getMe returned 401 怎么处理？？  ") == "Telegram getMe returned 401 怎么处理"


def test_build_query_plan_adds_keyword_and_intent_variants() -> None:
    plan = build_query_plan("Telegram getMe returned 401")

    assert plan.variants[0] == "Telegram getMe returned 401"
    assert "telegram" in plan.keywords
    assert "401" in plan.keywords
    assert any("修复方法" in variant for variant in plan.variants)


def test_tokenize_query_handles_chinese_and_commands() -> None:
    tokens = tokenize_query("openclaw channels status --probe")

    assert "openclaw" in tokens
    assert "channels" in tokens
    assert "--probe" in tokens
