from app.services.citation_validator import repair_missing_citations, validate_answer_citations


def test_validate_requires_each_unit_has_citation():
    assert validate_answer_citations("一句话[1]", max_index=1) is True
    assert validate_answer_citations("第一句[1]\n第二句[1]", max_index=1) is True
    assert validate_answer_citations("第一句\n第二句[1]", max_index=1) is False


def test_validate_rejects_out_of_range():
    assert validate_answer_citations("ok[2]", max_index=1) is False


def test_repair_appends_fallback():
    repaired = repair_missing_citations("第一句\n第二句[1]", fallback_index=1)
    assert "[1]" in repaired.splitlines()[0]
    assert validate_answer_citations(repaired, max_index=1) is True

