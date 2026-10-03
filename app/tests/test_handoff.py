import json

import pytest

from resume import handoff

SCHEMA = handoff.obj(name=handoff.STRING, note=handoff.NULLABLE, n={"type": "integer"},
                     tags=handoff.STRINGS, rows=handoff.array(handoff.obj(ok={"type": "boolean"})))
GOOD = {"name": "x", "note": None, "n": 3, "tags": ["a"], "rows": [{"ok": True}]}


def test_valid_answer_has_no_violations():
    assert handoff.violations(GOOD, SCHEMA, "answer") == []


@pytest.mark.parametrize("change, expected", [
    ({"name": None}, "answer.name: expected string"),
    ({"n": True}, "answer.n: expected integer, got bool"),
    ({"tags": ["a", 2]}, "answer.tags[1]: expected string"),
    ({"rows": [{}]}, "answer.rows[0]: missing 'ok'"),
    ({"extra": 1}, "answer: unknown key 'extra'"),
])
def test_violations_name_path(change, expected):
    assert any(expected in v for v in handoff.violations({**GOOD, **change}, SCHEMA, "answer"))


def test_write_task_clears_stale_answer(tmp_path, capsys):
    task, answer = tmp_path / "t" / "task.md", tmp_path / "t" / "answer.json"
    task.parent.mkdir()
    answer.write_text("{}")
    handoff.write_task(task, answer, "RULES", SCHEMA, "INPUT", "uv run app/jobs.py x")
    assert not answer.exists()
    body = task.read_text(encoding="utf-8")
    assert "RULES" in body and "INPUT" in body and str(answer) in body and '"required"' in body
    assert "then run: uv run app/jobs.py x" in capsys.readouterr().out


def test_read_answer_rejects_missing_bad_json_and_schema_mismatch(tmp_path):
    answer = tmp_path / "answer.json"
    with pytest.raises(SystemExit, match="AI step not done"):
        handoff.read_answer(answer, SCHEMA)
    answer.write_text("{not json")
    with pytest.raises(SystemExit, match="not valid JSON"):
        handoff.read_answer(answer, SCHEMA)
    answer.write_text(json.dumps({**GOOD, "n": "3"}))
    with pytest.raises(SystemExit, match="answer.n: expected integer"):
        handoff.read_answer(answer, SCHEMA)
    answer.write_text(json.dumps(GOOD))
    assert handoff.read_answer(answer, SCHEMA) == GOOD


def test_failed_checks_counted_per_task_reset_by_new_task(tmp_path, capsys):
    task, answer = tmp_path / "task.md", tmp_path / "answer.json"
    other = tmp_path / "other.json"
    handoff.write_task(task, answer, "RULES", SCHEMA, "INPUT", "x", "FALLBACK")
    handoff.write_task(tmp_path / "other.md", other, "RULES", SCHEMA, "INPUT", "x")
    assert handoff.failed(answer) == "" and handoff.failed(answer) == ""
    assert handoff.read_fails(answer)["fails"] == 2
    assert handoff.read_fails(other)["fails"] == 0  # its own count
    handoff.write_task(task, answer, "RULES", SCHEMA, "INPUT", "x", "FALLBACK")
    assert handoff.read_fails(answer)["fails"] == 0
    handoff.failed(answer)
    handoff.passed(answer)
    assert handoff.read_fails(answer)["fails"] == 0


@pytest.mark.parametrize("ai_name, said", [
    ("copilot", "Copilot's automatic model couldn't meet the page rules. With Copilot Pro you can pick a "
                "stronger model in the chat box, then ask again."),
    ("claude", "The AI couldn't meet the page rules after 3 tries."),
    ("chatgpt", "The AI couldn't meet the page rules after 3 tries."),
    (None, "The AI couldn't meet the page rules after 3 tries."),
])
def test_third_failure_prints_ai_worded_stop_and_fallback(tmp_path, capsys, monkeypatch, ai_name, said):
    import ai
    monkeypatch.setattr(ai, "current", lambda: ai_name)
    answer = tmp_path / "answer.json"
    handoff.write_task(tmp_path / "task.md", answer, "RULES", SCHEMA, "INPUT", "x", "Your resume: r.pdf")
    capsys.readouterr()
    handoff.failed(answer)
    handoff.failed(answer)
    assert capsys.readouterr().out == ""  # nothing before the 3rd
    handoff.failed(answer)
    out = capsys.readouterr().out
    assert "STOP" in out and said in out and "Your resume: r.pdf" in out


def test_bad_answer_counts_and_third_carries_stop(tmp_path, monkeypatch):
    import ai
    monkeypatch.setattr(ai, "current", lambda: "copilot")
    answer = tmp_path / "answer.json"
    handoff.write_task(tmp_path / "task.md", answer, "RULES", SCHEMA, "INPUT", "x", "FALLBACK",
                       "the rules for reading your resume")
    with pytest.raises(SystemExit, match="AI step not done"):  # not written yet: no failed check
        handoff.read_answer(answer, SCHEMA)
    for _ in range(2):
        answer.write_text("{not json")
        with pytest.raises(SystemExit) as e:
            handoff.read_answer(answer, SCHEMA)
        assert "STOP" not in str(e.value)
    answer.write_text(json.dumps({**GOOD, "n": "3"}))
    with pytest.raises(SystemExit) as e:
        handoff.read_answer(answer, SCHEMA)
    assert "couldn't meet the rules for reading your resume" in str(e.value) and "FALLBACK" in str(e.value)
