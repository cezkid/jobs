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
