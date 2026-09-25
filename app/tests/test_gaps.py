import yaml

from resume import facts, gaps, schema

DETAILS = """
contact: {name: Ada Lovelace, email: ada@example.com, location: "Austin, TX"}
roles:
- company: Acme Inc.
  title: Software Engineer
  start: 2023-02
  end: present
  bullets:
  - Cut checkout time 40% by moving work off the main thread.
  - Wrote Jest tests for the checkout screens.
- company: Beta LLC
  title: Web Developer
  start: 2019-06
  end: 2022-11
  bullets:
  - Built the ordering screen in Vue.
"""


def setup(tmp_path):
    path, notes = tmp_path / "Resume details.yml", tmp_path / "data" / "resume-index.yml"
    path.write_text(DETAILS, encoding="utf-8")
    return path, notes


def test_asks_about_every_line_without_a_number_and_leadership_per_recent_job(tmp_path):
    path, notes = setup(tmp_path)
    asked = gaps.questions(schema.load(path, notes))
    assert [(q["kind"], q["line"]) for q in asked] == [
        ("number", "Wrote Jest tests for the checkout screens."), ("number", "Built the ordering screen in Vue."),
        ("leadership", None), ("leadership", None)]
    assert "Acme Inc." in asked[2]["ask"] and asked[2]["already"][0].startswith("Cut checkout")


def test_only_answered_questions_change_the_file_and_a_backup_is_kept(tmp_path):
    path, notes = setup(tmp_path)
    master = schema.load(path, notes)
    master["roles"][0]["bullets"][1]["stack"] = ["Jest"]
    facts.write(master, notes)
    asked = gaps.questions(schema.load(path, notes))
    answers = [{"id": "q1", "said": "about 120 tests", "claim": "Wrote about 120 Jest tests for the checkout screens."},
               {"id": "q2", "said": None, "claim": None},
               {"id": "q3", "said": "I mentored 2 interns", "claim": "Mentored 2 interns on the checkout code."},
               {"id": "q4", "said": None, "claim": None}]
    assert gaps.problems(asked, answers, schema.load(path, notes)) == []
    changed, added, backup = gaps.merge(path, asked, answers, notes)
    assert (changed, added) == (1, 1) and yaml.safe_load(backup.read_text()) == yaml.safe_load(DETAILS)
    after = schema.load(path, notes)
    assert [b["claim"] for b in after["roles"][0]["bullets"]] == [
        "Cut checkout time 40% by moving work off the main thread.",
        "Wrote about 120 Jest tests for the checkout screens.", "Mentored 2 interns on the checkout code."]
    assert after["roles"][0]["bullets"][1]["stack"] == ["Jest"]
    assert after["roles"][1]["bullets"][0]["claim"] == "Built the ordering screen in Vue."


def test_a_number_the_user_never_said_is_refused(tmp_path):
    path, notes = setup(tmp_path)
    master = schema.load(path, notes)
    asked = gaps.questions(master)
    found = gaps.problems(asked, [
        {"id": "q1", "said": "a lot of tests", "claim": "Wrote 300 Jest tests for the checkout screens."},
        {"id": "q2", "said": None, "claim": "Built the ordering screen in Vue for 5 teams."},
    ], master)
    assert "['300'] in neither" in found[0] and "only the user's answer" in found[1]


def test_nothing_answered_leaves_the_file_alone(tmp_path):
    path, notes = setup(tmp_path)
    asked = gaps.questions(schema.load(path, notes))
    assert gaps.merge(path, asked, [{"id": q["id"], "said": None, "claim": None} for q in asked], notes)[:2] == (0, 0)
    assert path.read_text(encoding="utf-8") == DETAILS
