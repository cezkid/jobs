"""app/web/letter_count.py: the count behind /research/cover-letter-boxes-2026-10/ (no network)."""

import csv
import importlib.util
import io
import json
import sys

import cfg

sys.path.insert(0, str(cfg.APP / "web"))  # letter_count imports knockout_count by name, as when run as a script
spec = importlib.util.spec_from_file_location("letter_count", cfg.APP / "web" / "letter_count.py")
count = importlib.util.module_from_spec(spec)
spec.loader.exec_module(count)


def test_box_found_among_questions_or_basics_with_its_flag():
    assert count.box({"questions": [{"text": "Cover Letter", "required": False}]}) == {"required": False}
    assert count.box({"basics": ["First Name", "Cover letter"], "questions": []}) == {"required": None}
    # a question that only mentions a letter is not the box
    assert count.box({"questions": [{"text": "Are you willing to provide a resignation letter?"}]}) is None


def test_cached_flags_make_the_row_and_ask_nothing(tmp_path):
    raw = tmp_path / "raw.json"
    jobs = [{"slug": "a", "company": "acme", "letter_required": True,
             "form": {"data": {"provider": "greenhouse", "basics": ["Cover Letter"], "questions": []}}},
            {"slug": "b", "company": "beta", "form": {"data": {"provider": "lever", "basics": ["Resume"], "questions": []}}}]
    raw.write_text(json.dumps({"sales": {"jobs": jobs}}))
    out = io.StringIO()
    count.count(str(raw), out)
    got = list(csv.DictReader(io.StringIO(out.getvalue())))
    assert [(r["employer"], r["form_system"], r["letter_box"], r["letter_required"]) for r in got] == [
        ("A", "Greenhouse", "1", "1"), ("B", "Lever", "0", "")]


def test_published_file_is_what_the_count_made():
    text = (cfg.APP / "web" / "research" / "cover-letter-boxes-2026-10.csv").read_text(encoding="utf-8")
    data = list(csv.DictReader(io.StringIO(text)))
    assert list(data[0]) == count.COLUMNS and len(data) == 143
    assert sum(r["letter_box"] == "1" for r in data) == 96
    assert [sum(r["letter_required"] == v for r in data if r["letter_box"] == "1") for v in ("0", "1", "")] == [91, 2, 3]
    ko = list(csv.DictReader(io.StringIO((cfg.APP / "web" / "research" / "knockout-questions-2026-10.csv").read_text(encoding="utf-8"))))
    assert [(r["form"], r["employer"], r["job_field"], r["form_system"]) for r in data] == [
        (r["form"], r["employer"], r["job_field"], r["form_system"]) for r in ko]
