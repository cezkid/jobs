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
