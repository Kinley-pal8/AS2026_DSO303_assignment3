from decimal import Decimal

import pytest

import core

QUESTIONS = core.validate_questions([
    {"id": "q1", "type": "mcq", "text": "2 + 2?", "options": ["3", "4"], "answer": 1, "marks": 2},
    {"id": "q2", "type": "mcq", "text": "Capital of Bhutan?", "options": ["Paro", "Thimphu", "Punakha"], "answer": 1},
    {"id": "q3", "type": "short", "text": "Explain Multi-AZ.", "marks": 5},
])


def test_mark_scores_mcq_and_leaves_short_answers():
    assert core.mark(QUESTIONS, {"q1": 1, "q2": 0, "q3": "text"}) == {"mcq_score": 2, "mcq_max": 3, "sa_max": 5}


def test_mark_ignores_bool_and_missing_answers():
    assert core.mark(QUESTIONS, {"q1": True})["mcq_score"] == 0


def test_public_paper_hides_answers():
    assert all("answer" not in q for q in core.public_paper(QUESTIONS))


@pytest.mark.parametrize("bad", [
    [],
    [{"id": "q1", "type": "mcq", "text": "x", "options": ["a"], "answer": 0}],
    [{"id": "q1", "type": "mcq", "text": "x", "options": ["a", "b"], "answer": 5}],
    [{"id": "q1", "type": "essay", "text": "x"}],
    [{"id": "q1", "type": "short", "text": "x"}, {"id": "q1", "type": "short", "text": "y"}],
])
def test_validate_questions_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        core.validate_questions(bad)


def test_validate_answers_filters_unknown_questions_and_limits_length():
    assert core.validate_answers({"q1": 1, "zz": 0}, QUESTIONS) == {"q1": 1}
    with pytest.raises(ValueError):
        core.validate_answers({"q3": "x" * (core.MAX_SHORT_ANSWER + 1)}, QUESTIONS)


def test_normalize_decimals():
    assert core.normalize({"a": Decimal("2"), "b": [Decimal("1.5")]}) == {"a": 2, "b": [1.5]}


def test_parse_groups_formats():
    assert core.parse_groups("[students tutors]") == ["students", "tutors"]
    assert core.parse_groups(["admins", "hackers"]) == ["admins"]
    assert core.parse_groups(None) == []


@pytest.mark.parametrize("name,expected", [
    ("Report Final.pdf", "Report_Final.pdf"),
    ("../../etc/passwd.ZIP", "passwd.zip"),
    ("C:\\Users\\me\\work.pdf", "work.pdf"),
])
def test_sanitize_filename(name, expected):
    assert core.sanitize_filename(name) == expected


def test_sanitize_filename_rejects_other_types():
    with pytest.raises(ValueError):
        core.sanitize_filename("virus.exe")


def test_upload_key_roundtrip():
    aid = "0b6f1f4e-5d0a-4a43-9a4c-1f2e3d4c5b6a"
    key = core.build_upload_key(aid, "abc-123", "my essay.pdf")
    parsed = core.parse_upload_key(key)
    assert parsed["assignment_id"] == aid and parsed["student_id"] == "abc-123"
    assert parsed["filename"] == "my_essay.pdf"
    assert core.parse_upload_key("other/thing.pdf") is None


def test_sniff():
    assert core.sniff_ok(b"%PDF-1.7", "a.pdf")
    assert core.sniff_ok(b"PK\x03\x04xx", "a.zip")
    assert not core.sniff_ok(b"MZ\x90\x00", "a.pdf")
