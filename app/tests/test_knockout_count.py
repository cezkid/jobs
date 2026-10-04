"""app/web/knockout_count.py: the count behind /research/knockout-questions-2026-10/ (no network)."""

import csv
import importlib.util
import io
import json

import cfg

spec = importlib.util.spec_from_file_location("knockout_count", cfg.APP / "web" / "knockout_count.py")
count = importlib.util.module_from_spec(spec)
spec.loader.exec_module(count)


def form(questions=(), basics=("First Name", "Email", "Resume")):
    return {"data": {"provider": "workable", "basics": list(basics), "questions": [{"text": q} for q in questions]}}


def rows(tmp_path, jobs):
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"sales": {"jobs": [{"slug": f"s{n}", "company": c, "form": f}
                                                  for n, (c, f) in enumerate(jobs)]}}))
    out = io.StringIO()
    count.table(str(raw), out)
    return list(csv.DictReader(io.StringIO(out.getvalue())))


def test_employer_questions_listed_among_the_basics_are_counted(tmp_path):
    # Workable lists some employers' own questions next to name + email (review 2026-10-04, F1)
    got = rows(tmp_path, [("acme", form(basics=["First Name", "Email", "Are you legally authorized to work in the United States?",
                                                  "Florida Bar Status, please select the option that best describes your status."]))])
    assert got[0]["work_permit"] == got[0]["license_certificate"] == got[0]["any_knockout"] == "1"
    assert got[0]["questions_beyond_basics"] == "2" and got[0]["form_system"] == "Workable"


def test_resignation_clearance_letter_and_address_boxes_are_not_screens(tmp_path):
    got = rows(tmp_path, [("acme", form(["Address", "Zip Code", "Are you willing to provide Clearance/Resignation letter (Form 6)"])),
                          ("acme", form(["Are you willing to relocate?"])), ("beta", form())])
    assert [r["security_clearance"] for r in got] == ["0", "0", "0"]
    assert [r["location_screen"] for r in got] == ["0", "1", "0"]
    assert [r["employer"] for r in got] == ["A", "A", "B"] and got[2]["questions_beyond_basics"] == "0"


def test_employer_letters_run_past_z():
    assert [count.letters(n) for n in (0, 25, 26, 27, 701, 702)] == ["A", "Z", "AA", "AB", "ZZ", "AAA"]


def test_published_file_is_what_the_count_made():
    text = (cfg.APP / "web" / "research" / "knockout-questions-2026-10.csv").read_text(encoding="utf-8")
    data = list(csv.DictReader(io.StringIO(text)))
    assert list(data[0]) == count.COLUMNS and len(data) == 143
    assert sum(r["any_knockout"] == "1" for r in data) == 109
