import json

import pytest

import tailor_eval


def answered(out_dir, case: str, answer: dict):
    path = tailor_eval.answer_path(out_dir, case)
    path.write_text(json.dumps(answer), encoding="utf-8")
    return path


def golden(case: str) -> dict:
    return json.loads((tailor_eval.CASES / case / "golden.json").read_text(encoding="utf-8"))


def test_every_case_carries_its_files():
    assert tailor_eval.cases() == [
        "finance-lapsed", "nonprofit-hr", "nurse-assisted", "security-associate", "software-staff", "student-degree"]
    for case in tailor_eval.cases():
        assert {p.name for p in (tailor_eval.CASES / case).iterdir()} >= {
            "case.yml", "posting.txt", "extract.json", "traps.yml", "golden.json"}
        assert tailor_eval.case_spec(case)["master"].is_file()


def test_golden_answers_pass_with_no_trap_hits(tmp_path):
    tasks = tailor_eval.prepare(tmp_path)
    for case, task in zip(tailor_eval.cases(), tasks):
        text = task.read_text(encoding="utf-8")
        # the AI's check runs the eval's mini folder, never the user's own job folder
        assert tailor_eval.check_line(tmp_path, case) in text and "jobs.py tailor check" not in text
        answered(tmp_path, case, golden(case))
        assert tailor_eval.check(tmp_path, case) == 0
    rows = tailor_eval.grade(tmp_path)
    assert [(r["case"], r["passed"], r["runs"], r["gates failed"], r["traps"]) for r in rows] == [
        (case, True, 1, [], []) for case in tailor_eval.cases()]


def graphql_bullet(answer: dict) -> None:
    answer["entries"][0]["bullets"].append(
        {"text": "Designed GraphQL schemas for the support platform with Apollo Client", "sources": ["acme-rag-search"]})


def staff_headline(answer: dict) -> None:
    answer["headline_title"] = "Staff Software Engineer"


@pytest.mark.parametrize("mutate, gate, trap", [
    (graphql_bullet, "entries", "graphql-claimed"),
    (staff_headline, "headline_title", "staff-level"),
])
def test_mutated_answer_fails_with_its_gate_named(tmp_path, mutate, gate, trap):
    case = "software-staff"
    tailor_eval.prepare(tmp_path, [case])
    answer = golden(case)
    mutate(answer)
    answered(tmp_path, case, answer)
    assert tailor_eval.check(tmp_path, case) == 1
    [row] = tailor_eval.grade(tmp_path)
    assert not row["passed"] and gate in row["gates failed"], row
    assert trap in row["traps"]


def first_bullet(text: str):
    def mutate(answer: dict) -> None:
        answer["entries"][0]["bullets"][0]["text"] = text
    return mutate


def summary(text: str):
    def mutate(answer: dict) -> None:
        answer["summary"] = text
    return mutate


# Hold-tier slips: a new name (CISSP, P&L) trips the entity gates; an upgraded verb or a lapsed
# exam shown as held passes every gate - its trap is the only flag
@pytest.mark.parametrize("case, mutate, gates, trap", [
    ("nurse-assisted", first_bullet("Led 40+ bedside central line insertions in a 24-bed medical ICU"),
     [], "upgraded-part"),
    ("security-associate", summary("CISSP-certified security analyst writing Splunk detections for a credit union"),
     ["lint unresolved-entity"], "cissp-as-held"),
    ("finance-lapsed", summary("Series 7 registered brokerage operations analyst supporting financial advisors"),
     [], "series7-as-held"),
    ("nonprofit-hr", first_bullet("Owned the P&L for a $1.4M benefits budget and cut premiums 8% at the 2024 renewal"),
     ["entries", "lint unresolved-entity"], "pnl-claimed"),
])
def test_hold_slip_is_flagged(tmp_path, case, mutate, gates, trap):
    tailor_eval.prepare(tmp_path, [case])
    answer = golden(case)
    mutate(answer)
    answered(tmp_path, case, answer)
    assert tailor_eval.check(tmp_path, case) == (1 if gates else 0)
    [row] = tailor_eval.grade(tmp_path)
    assert (row["passed"], row["runs"], row["gates failed"], row["traps"]) == (not gates, 1, gates, [trap]), row


def test_third_failed_run_is_graded_as_stopped(tmp_path, capsys):
    case = "student-degree"
    tailor_eval.prepare(tmp_path, [case])
    answered(tmp_path, case, {"summary": None})
    for _ in range(3):
        assert tailor_eval.check(tmp_path, case) == 1
    assert "STOP" in capsys.readouterr().out
    [row] = tailor_eval.grade(tmp_path)
    assert (row["passed"], row["runs"], row["gates failed"], row["stopped"]) == (
        False, 3, [tailor_eval.SCHEMA_GATE], True)


def test_prepare_refuses_out_dir_inside_checkout():
    inside = tailor_eval.REPO / "app" / "tests" / "eval-out"
    with pytest.raises(SystemExit, match="inside the checkout"):
        tailor_eval.prepare(inside)
    assert not inside.exists()
