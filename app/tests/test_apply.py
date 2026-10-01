import copy
import shutil
import subprocess

import pytest

from apply import profile
from resume import schema

EXAMPLE = profile.cfg.APP / "resume" / "master.example.yml"


@pytest.fixture
def master() -> dict:
    return copy.deepcopy(schema.load(EXAMPLE))


def test_degree_tries_the_spelled_out_name_then_the_generic_entry():
    assert profile.degree("BA") == ["Bachelor of Arts", "BA", "Bachelor's degree"]
    assert profile.degree("Associate of Arts") == ["Associate of Arts", "Associate's degree"]
    assert profile.degree("GED") == ["GED"]


def test_field_of_study_shortens_from_the_end_without_dangling_joiners():
    assert profile.field_of_study("Music Performance in Jazz and Studio") == [
        "Music Performance in Jazz and Studio", "Music Performance in Jazz", "Music Performance"]
    assert profile.field_of_study("Nursing") == ["Nursing"]
    assert profile.field_of_study(None) == []


@pytest.mark.parametrize("line, levels", [
    ("Spanish (Native)", ["Native", "Fluent"]), ("French (Fluent)", ["Fluent"]),
    ("German (Professional working proficiency)", ["Professional", "Advanced"]),
    ("Italian (Conversational)", ["Conversational", "Intermediate"]), ("Korean (B2)", ["B2"]), ("Spanish", []),
])
def test_language_level_falls_back_only_within_its_tier(line, levels):
    assert profile.language(line)["levels"] == levels


def test_answers_use_tailored_bullets_when_the_job_has_them(master):
    data = profile.answers(master)
    first = master["roles"][0]
    assert data["work"][0]["description"].startswith(profile.BULLET + first["bullets"][0]["claim"])
    assert data["work"][0]["current"] and data["work"][0]["end"] == ""
    tailored = {"entries": [{"id": first["id"], "bullets": [{"text": "Shipped one thing."}]}],
                "skills": [{"group": "x", "items": ["Go", "Go", "SQL"]}]}
    data = profile.answers(master, tailored)
    assert data["work"][0]["description"] == "• Shipped one thing."
    assert data["skills"] == ["Go", "SQL"]
    assert data["work"][1]["description"].startswith(profile.BULLET)  # role left out of tailoring: own bullets


def test_hidden_graduation_year_stays_off_the_form(master):
    master["education"][0]["hide_year"] = True
    assert profile.answers(master)["education"][0]["end"] == ""


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_script_is_valid_javascript(master, tmp_path):
    out = tmp_path / "apply.js"
    out.write_text(profile.script(profile.answers(master)), encoding="utf-8")
    assert subprocess.run(["node", "--check", str(out)], capture_output=True).returncode == 0


def test_work_authorization_reads_setup_answers_and_never_guesses_unset():
    said = profile.work_authorization({"work_authorization": {
        "authorized_us": True, "needs_sponsorship": False, "citizen_or_permanent_resident": True}})
    assert said == ("authorized to work in the US: yes; needs visa sponsorship: no; "
                    "US citizen or permanent resident: yes")
    assert profile.work_authorization(profile.cfg.defaults()) == (
        "authorized to work in the US: not set - ask them; needs visa sponsorship: not set - ask them; "
        "US citizen or permanent resident: not set - ask them")


def test_workday_script_takes_only_the_jobs_it_is_given(master):
    first = master["roles"][:1]
    assert [w["company"] for w in profile.answers(master, None, first)["work"]] == [first[0]["company"]]
    assert len(profile.answers(master)["work"]) == len(master["roles"])


def test_workday_apply_asks_which_jobs_before_writing_a_script(master, tmp_path, monkeypatch, capsys):
    # tailored page left the oldest job off, no choice saved: the ask is printed, no script to send
    job = tmp_path / "Acme - Clerk"
    (job / profile.tailor.JOB_DATA).mkdir(parents=True)
    kept = [{"id": r["id"], "bullets": []} for r in master["roles"][:-1]]
    (job / profile.tailor.JOB_DATA / "tailored.json").write_text(profile.json.dumps({"entries": kept, "skills": []}))
    stale = job / profile.tailor.JOB_DATA / "apply.js"
    stale.write_text("old")
    monkeypatch.setattr(profile.cfg, "load", lambda: {})
    monkeypatch.setattr(profile.cfg, "resume_path", lambda config, key: tmp_path)
    monkeypatch.setattr(profile.schema, "load", lambda path: master)
    monkeypatch.setattr(profile.tailor, "find_job_dir", lambda jobs, slug: job)
    monkeypatch.setattr(profile.tailor, "by_number", lambda config, ref: ref)
    monkeypatch.setattr(profile.sys, "argv", ["apply", "acme-clerk"])
    profile.main()
    assert capsys.readouterr().out.startswith("ASK") and not stale.exists()
    master["contact"]["form_jobs"] = "page"
    profile.main()
    assert f"({len(kept)} jobs," in capsys.readouterr().out and stale.exists()
    monkeypatch.setattr(profile.sys, "argv", ["apply", "acme-clerk", "--complete-history"])
    profile.main()
    assert f"({len(master['roles'])} jobs," in capsys.readouterr().out
