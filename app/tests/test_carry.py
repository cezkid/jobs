import copy

import pytest
import yaml

from resume import carry, facts, handoff, import_pdf, schema, tidy
from test_import_pdf import MAPPED

NEW = {
    "contact": {"name": "Jane Doe", "email": "jane@example.com", "location": "Austin, TX"},
    "roles": [
        {"company": "Acme Inc.", "title": "Software Engineer", "start": "2023-02", "end": "present",
         "bullets": ["Cut checkout time 40% by moving work off the main thread.",
                     "Wrote Jest tests for the checkout screens."]},
        {"company": "Beta LLC", "title": "Web Developer", "start": "2019-06", "end": "2022-11",
         "bullets": ["Built the ordering screen in Vue."]},
    ],
    "skills": [{"group": "Frontend", "items": ["Vue", "Jest"]}],
    "education": [{"institution": "State University", "degree": "BS", "end": "2004-05"}],
    "languages": ["Spanish"],
}


def old_file() -> dict:
    old = copy.deepcopy(NEW)
    old["contact"] |= {"legal_first": "Jane", "legal_last": "Doe"}
    acme = old["roles"][0]
    acme["bullets"][1] = "Wrote about 120 Jest tests for the checkout screens."  # gaps answer
    acme["bullets"].append("Mentored 2 interns on the checkout code.")
    acme["blurb"] = "Online checkout for 300 stores"
    old["roles"][1]["title"] = "Front-End Developer"  # corrected by hand after the first import
    old["roles"].append({"company": "Gamma Co", "title": "Intern", "start": "2018-06", "end": "2018-09",
                         "bullets": ["Fixed 30 layout bugs."]})
    old["career_break"] = [{"start": "2022-12", "end": "2023-01", "reason": "Family care"}]
    old["education"][0]["hide_year"] = True
    old["languages"] = ["Spanish (Fluent)"]
    old["skills"][0]["items"].append("Playwright")
    return old


def test_claim_key_keeps_numbers():
    assert carry.claim_key("Cut load time 20s to 1s.") == carry.claim_key("cut load-time 20s to 1s")
    assert carry.claim_key("Cut load time 20s to 1s.") != carry.claim_key("Cut load time 30s to 1s.")


def test_left_behind_sorts_what_the_new_pdf_lacks():
    left = carry.left_behind(old_file(), NEW)
    says = {g: [i["say"] for i in items] for g, items in left.items()}
    assert says["lines"] == ["Wrote about 120 Jest tests for the checkout screens.",
                             "Mentored 2 interns on the checkout code.", "skill Playwright"]
    assert says["entries"] == ["Intern at Gamma Co (2018-06)", "break 2022-12 - 2023-01"]
    assert sorted(says["details"]) == sorted(["contact legal_first", "contact legal_last",
                                              "blurb on Software Engineer at Acme Inc. (2023-02)",
                                              "hide_year on State University", "language Spanish (Fluent)"])


def test_title_fixed_by_hand_still_matches_its_job():
    """Same employer (legal suffix aside), same start: the hand-fixed title is the same job."""
    left = carry.left_behind(old_file(), NEW)
    assert not [i for i in left["entries"] if "Beta" in i["say"]]
    assert carry.company("Beta LLC") == carry.company("beta")


def test_keep_carries_only_ticked_groups_and_reworded_line_replaces():
    left = carry.left_behind(old_file(), NEW)
    out = carry.carry(NEW, left, carry.kept("lines,details", left))
    acme = out["roles"][0]
    assert acme["bullets"] == ["Cut checkout time 40% by moving work off the main thread.",
                               "Wrote about 120 Jest tests for the checkout screens.",
                               "Mentored 2 interns on the checkout code."]
    assert acme["blurb"] == "Online checkout for 300 stores" and out["contact"]["legal_last"] == "Doe"
    assert out["languages"] == ["Spanish (Fluent)"] and out["education"][0]["hide_year"] is True
    assert [r["company"] for r in out["roles"]] == ["Acme Inc.", "Beta LLC"]  # entries not ticked
    assert NEW["roles"][0]["bullets"][1] == "Wrote Jest tests for the checkout screens."  # input untouched
    every = carry.carry(NEW, left, carry.kept("all", left))
    assert [r["company"] for r in every["roles"]] == ["Acme Inc.", "Beta LLC", "Gamma Co"]
    assert carry.kept("none", left) == set()
    with pytest.raises(SystemExit):
        carry.kept("jobs", left)


@pytest.fixture
def import_env(tmp_path, monkeypatch):
    """finish() w/ the PDF read + AI answer faked: the mapped fixture stands in for both."""
    config = {"resume": {"input_pdf": "My Resume/Original resume.pdf", "master": "My Resume/Resume details.yml"}}
    monkeypatch.setattr(import_pdf.cfg, "resume_path", lambda c, key: tmp_path / c["resume"][key])
    monkeypatch.setattr(import_pdf.cfg, "DATA", tmp_path / ".data")
    monkeypatch.setattr(carry.cfg, "DATA", tmp_path / ".data")
    monkeypatch.setattr(facts, "PATH", tmp_path / ".data" / "resume-index.yml")
    monkeypatch.setattr(import_pdf, "extract", lambda pdf: "")
    monkeypatch.setattr(handoff, "read_answer", lambda answer, schema_: copy.deepcopy(MAPPED))
    monkeypatch.setattr(import_pdf, "untraced", lambda mapped, source: [])
    monkeypatch.setattr(import_pdf, "recovery", lambda mapped, source: (1.0, []))
    return config, tmp_path / config["resume"]["master"]


def test_first_import_never_asks(import_env):
    config, master_path = import_env
    import_pdf.finish(config)
    assert schema.load(master_path)["contact"]["name"] == MAPPED["contact"]["name"]


def test_reimport_writes_nothing_until_asked_then_keeps_the_ticked_groups(import_env, capsys):
    config, master_path = import_env
    import_pdf.finish(config)
    mine = yaml.safe_load(master_path.read_text(encoding="utf-8"))
    mine["contact"] |= {"legal_first": "Pat", "legal_last": "Quinn"}
    mine["roles"][0]["bullets"].append("Mentored 2 interns on the release process.")
    master_path.write_text(tidy.dump(mine), encoding="utf-8")
    before = master_path.read_text(encoding="utf-8")
    with pytest.raises(SystemExit) as stop:
        import_pdf.finish(config)
    out = capsys.readouterr().out
    assert stop.value.code == 2 and master_path.read_text(encoding="utf-8") == before
    assert "lines (1)" in out and "details (2)" in out and "--keep" in out
    import_pdf.finish(config, "details")
    after = schema.load(master_path)
    assert after["contact"]["legal_first"] == "Pat"
    assert "Mentored 2 interns on the release process." not in [b["claim"] for b in after["roles"][0]["bullets"]]
    kept = sorted((master_path.parent.parent / ".data").glob("Resume details before import *.yml"))
    assert kept and yaml.safe_load(kept[-1].read_text(encoding="utf-8"))["contact"]["legal_first"] == "Pat"


def test_old_activities_lines_and_gpa_details_are_not_reported_lost_once_read_into_their_fields():
    from resume import carry
    old = {"contact": {}, "roles": [], "education": [{"institution": "State U", "degree": "BS", "details": "GPA: 3.62"}],
           "other": [{"heading": "Activities", "lines": ["Treasurer, Black Student Union, Sep 2024 - Present",
                                                         "Managed a $12,000 budget for 30 events"]}]}
    new = {"contact": {}, "roles": [], "education": [{"institution": "State U", "degree": "BS", "gpa": "3.62"}],
           "projects": [{"name": "Black Student Union", "role": "Treasurer", "start": "2024-09", "end": "present",
                         "bullets": [{"claim": "Managed a $12,000 budget for 30 events"}]}]}
    left = carry.left_behind(old, new)
    assert left["entries"] == [] and left["details"] == []
    gone = {**new, "projects": []}
    assert [e["say"] for e in carry.left_behind(old, gone)["entries"]] == ["Activities"]
