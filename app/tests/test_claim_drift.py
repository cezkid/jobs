"""app/docs/resume/measure/claim_drift.py: counts over made-up job folders (no network, no AI)."""

import importlib.util
import json
import sys

import yaml

import cfg
from resume import handoff

spec = importlib.util.spec_from_file_location("claim_drift", cfg.APP / "docs" / "resume" / "measure" / "claim_drift.py")
drift = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drift)

MASTER = {
    "summary": "Support engineer who ships tools for support teams.",
    "roles": [{"id": "acme", "company": "Acme Inc.", "title": "Support Engineer", "start": "2022-01", "end": "present",
               "bullets": [
                   {"id": "acme-backlog", "claim": "Cut the ticket backlog by about 120 tickets a month"},
                   {"id": "acme-course", "claim": "Built the onboarding course for new support hires"},
                   {"id": "acme-pipes", "claim": "Wrote Python jobs that move ticket records into the warehouse"},
                   {"id": "acme-docs", "claim": "Rewrote 40 help articles in plain language"},
                   {"id": "acme-help", "claim": "Co-led the help center rewrite"},
               ]}],
    "skills": [{"group": "Tools", "items": ["Python", "Zendesk"]}],
}
JOB = {"title": "Data Engineer", "company": "Beta",
       "description": "You will design and maintain scalable data pipelines for analytics across regions. "
                      "Data quality matters; data is our product.",
       "requirements": [{"index": 0, "priority": "required", "text": "3 years building data pipelines"}]}
DROP = "Cut the ticket backlog by 120 tickets a month"
SUPERLATIVE = "Built the largest onboarding course for new support hires"
COPY = "Wrote Python jobs to design and maintain scalable data pipelines for analytics"
CLEAN = "Rewrote 40 help articles in plain language"


def tailored(bullets: list[tuple[str, list[str]]], summary: str | None = None) -> dict:
    return {"summary": summary, "headline_title": None,
            "entries": [{"id": "acme", "title_mirror": None,
                         "bullets": [{"text": t, "sources": s} for t, s in bullets]}],
            "skills": [{"group": "Tools", "items": ["Python", "Zendesk"]}], "inferences": [], "coverage": []}


def job_folder(root, answer: dict, letter: tuple[dict, dict] | None = None):
    data = root / "My Jobs" / "1 To apply" / "1 - Beta - Data Engineer" / ".data"
    request = {"job": JOB, "budget": {}, "master": MASTER}
    handoff.write_task(data / "task.md", data / "tailored.json", "rules", {"type": "object"},
                       json.dumps(request, indent=1, ensure_ascii=False), "check")
    (data / "tailored.json").write_text(json.dumps(answer), encoding="utf-8")
    if letter:
        handoff.write_task(data / "letter-task.md", data / "letter.json", "rules", {"type": "object"},
                           yaml.safe_dump(letter[0], sort_keys=False), "check")
        (data / "letter.json").write_text(json.dumps(letter[1]), encoding="utf-8")
    return data


def test_task_file_gives_back_the_payload_the_ai_saw(tmp_path):
    data = job_folder(tmp_path, tailored([]), ({"your_words": "I use it daily.", "master": MASTER}, {"paragraphs": []}))
    assert drift.payload(data / "task.md")["master"] == MASTER
    assert drift.payload(data / "letter-task.md") == {"your_words": "I use it daily.", "master": MASTER}


def test_one_drop_one_superlative_one_copy_one_clean_bullet(tmp_path):
    job_folder(tmp_path, tailored([(DROP, ["acme-backlog"]), (SUPERLATIVE, ["acme-course"]),
                                   (COPY, ["acme-pipes"]), (CLEAN, ["acme-docs"])], summary=MASTER["summary"]))
    tally = drift.measure(tmp_path)
    assert {k: v for k, v in tally.n.items() if v} == {
        "tailored": 1, "lines": 5, "a qualifier": 1, "c superlative": 1}
    # "design and maintain scalable data pipelines for analytics": 8 words in a row
    assert dict(tally.runs) == {8: 1}
    # "data": once on the tailored page (the copied line), never in the facts
    assert {k: v for k, v in tally.terms.items() if v} == {"more": 1, "tailored": 1}
    assert tally.lines == []


def test_co_word_first_placeholder_letter_and_old_ids(tmp_path):
    letter_payload = {"your_words": "I use this product daily.", "master": MASTER}
    paragraphs = [
        {"text": "I use this product daily. I want to join Beta.", "sources": []},
        {"text": "At Acme Inc. I was the only engineer who cut the backlog by 120 tickets a month.",
         "sources": ["acme-backlog"]},
        {"text": "I rewrote the old help center.", "sources": ["gone-id"]},
    ]
    job_folder(tmp_path, tailored([("Led the help center rewrite", ["acme-help"]),
                                   ("First to run [metric] weekly reviews", ["acme-docs"]),
                                   ("Built a course from an older resume", ["gone-id"])]),
               (letter_payload, {"paragraphs": paragraphs}))
    tally = drift.measure(tmp_path)
    assert {k: v for k, v in tally.n.items() if v} == {
        "tailored": 1, "letters": 1, "lines": 4, "skipped": 2,
        "a qualifier": 1, "b co": 1, "c first/only": 2, "f placeholder": 1}
    assert not tally.runs


def test_counts_only_unless_show(tmp_path, capsys, monkeypatch):
    job_folder(tmp_path, tailored([(DROP, ["acme-backlog"]), (SUPERLATIVE, ["acme-course"]),
                                   (COPY, ["acme-pipes"]), (CLEAN, ["acme-docs"])]))
    capsys.readouterr()
    monkeypatch.setattr(sys, "argv", ["claim_drift.py", str(tmp_path)])
    drift.main()
    quiet = capsys.readouterr().out
    assert "(a) number qualifier dropped: 1" in quiet and "8+: 1" in quiet
    claims = [DROP, SUPERLATIVE, COPY, CLEAN, *(b["claim"] for b in MASTER["roles"][0]["bullets"])]
    assert not [c for c in claims if c in quiet]
    assert "largest" not in quiet and "about 120" not in quiet
    monkeypatch.setattr(sys, "argv", ["claim_drift.py", str(tmp_path), "--show"])
    drift.main()
    shown = capsys.readouterr().out
    assert shown.startswith(quiet.rstrip("\n"))
    assert DROP in shown and SUPERLATIVE in shown and COPY in shown and CLEAN not in shown


def test_reads_nothing_outside_my_jobs_and_writes_nothing(tmp_path):
    data = job_folder(tmp_path, tailored([(DROP, ["acme-backlog"])]))
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    drift.measure(tmp_path, show=True)
    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before
    assert drift.measure(data).n["tailored"] == 0


def _kinds(master_bullets, bullets, tmp_path):
    MASTER["roles"][0]["bullets"].extend(master_bullets)
    try:
        job_folder(tmp_path, tailored(bullets))
        return drift.measure(tmp_path, show=True)
    finally:
        del MASTER["roles"][0]["bullets"][-len(master_bullets):]


def test_claim_drift_kind_g_hedge_upgrade(tmp_path):
    tally = _kinds([{"id": "acme-assist", "claim": "Assisted with the billing migration"}],
                   [("Led the billing migration", ["acme-assist"]),
                    ("Assisted with the billing migration", ["acme-assist"]),
                    ("Built the onboarding course", ["acme-course"])], tmp_path)
    assert tally.n["g hedge upgrade"] == 1 and tally.n["lines"] == 3
    assert any("(g)" in line and "Led the billing" in line for line in tally.lines)
    assert "(g) hedged source, stronger verb: 1 of 3 lines" in drift.report(tally)


def test_claim_drift_kind_h_reach(tmp_path):
    tally = _kinds([{"id": "acme-wide", "claim": "Rolled out a macro library across the support team"}],
                   [("Rolled out a company-wide macro library", ["acme-wide"]),
                    ("Rolled out a macro library, adopted by 40 agents", ["acme-wide"]),
                    ("Rolled out a macro library across the support team", ["acme-wide"])], tmp_path)
    assert tally.n["h reach"] == 2 and tally.n["lines"] == 3
    assert "(h) reach no cited fact makes: 2 of 3 lines" in drift.report(tally)


def test_claim_drift_kind_i_vendor_credit(tmp_path):
    tally = _kinds([{"id": "acme-vendor", "claim": "Managed a vendor who built the ticket dashboard"}],
                   [("Built the ticket dashboard", ["acme-vendor"]),
                    ("Managed a vendor that built the ticket dashboard", ["acme-vendor"]),
                    ("Built the onboarding course", ["acme-course"])], tmp_path)
    assert tally.n["i vendor credit"] == 1 and tally.n["lines"] == 3
    assert any("(i)" in line for line in tally.lines)
