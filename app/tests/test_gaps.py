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


HEDGED = DETAILS.replace("  - Wrote Jest tests for the checkout screens.", "  - Helped migrate the checkout to Vue 3.")


def test_hedged_line_asks_part_not_number(tmp_path):
    """A 'helped' or 'we' line leaves the reader guessing whose work it was: that's asked first."""
    path, notes = setup(tmp_path)
    path.write_text(HEDGED, encoding="utf-8")
    asked = gaps.questions(schema.load(path, notes))
    assert (asked[0]["kind"], asked[0]["line"]) == ("part", "Helped migrate the checkout to Vue 3.")
    assert '"Helped"' in asked[0]["ask"] and [q["kind"] for q in asked].count("part") == 1


def test_part_answer_cannot_upgrade_helped(tmp_path):
    path, notes = setup(tmp_path)
    path.write_text(HEDGED, encoding="utf-8")
    master = schema.load(path, notes)
    asked = gaps.questions(master)
    found = gaps.problems(asked, [{"id": "q1", "said": "I moved the cart and payment screens",
                                   "claim": "Led the checkout migration to Vue 3."}], master)
    assert "'Led' claims more" in found[0]
    ok = [{"id": "q1", "said": "I moved the cart and payment screens myself",
           "claim": "Moved the cart and payment screens to Vue 3."}]
    assert gaps.problems(asked, ok, master) == []
    gaps.merge(path, asked, ok, notes)
    assert schema.load(path, notes)["roles"][0]["bullets"][1]["claim"] == "Moved the cart and payment screens to Vue 3."


def test_negated_answer_refused(tmp_path):
    """'I have not mentored 3 interns' contains '3 interns' - it never goes in."""
    path, notes = setup(tmp_path)
    master = schema.load(path, notes)
    asked = gaps.questions(master)
    found = gaps.problems(asked, [{"id": "q3", "said": "No, I never mentored the 3 interns",
                                   "claim": "Mentored 3 interns on the checkout code."}], master)
    assert "denies '3'" in found[0]
    assert "says no" in gaps.problems(asked, [{"id": "q3", "said": "Not really.", "claim": "Mentored people."}], master)[0]


def test_contrast_clause_not_a_negation(tmp_path):
    path, notes = setup(tmp_path)
    master = schema.load(path, notes)
    asked = gaps.questions(master)
    said = "I didn't lead the team, but I trained 2 new hires on the checkout code"
    assert gaps.problems(asked, [{"id": "q3", "said": said, "claim": "Trained 2 new hires on the checkout code."}], master) == []


def test_fact_from_practice_goes_in_their_words_only_once(tmp_path):
    """Interview practice: a stated fact lands under its job, never one they didn't say."""
    path, notes = setup(tmp_path)
    master = schema.load(path, notes)
    asked = gaps.fact_questions(master)
    assert [q["kind"] for q in asked] == ["fact", "fact"] and "Software Engineer at Acme Inc." in asked[0]["ask"]
    ok = [{"id": "q1", "said": "I cut checkout errors from 30 a week to 5", "claim": "Cut checkout errors from 30 a week to 5."},
          {"id": "q2", "said": None, "claim": None}]
    assert gaps.problems(asked, ok, master) == []
    invented = [{"id": "q1", "said": "I cut checkout errors a lot", "claim": "Cut checkout errors 80%."}]
    assert "['80'] in neither" in gaps.problems(asked, invented, master)[0]
    again = [{"id": "q1", "said": "I wrote Jest tests for the checkout screens", "claim": "Wrote Jest tests for the checkout screens."}]
    assert "already a line" in gaps.problems(asked, again, master)[0]
    gaps.merge(path, asked, ok, notes)
    assert schema.load(path, notes)["roles"][0]["bullets"][-1]["claim"] == "Cut checkout errors from 30 a week to 5."


def test_a_line_whose_only_digits_name_a_camera_or_a_date_is_asked_for_a_number(tmp_path):
    path = tmp_path / "Resume details.yml"
    path.write_text("""
contact: {name: Sam Rivera, email: sam@example.com, location: "Los Angeles, CA"}
roles:
- company: Self-employed
  title: Freelance Video Editor
  start: 2021-04
  end: present
  bullets:
  - "Kestrel Studios (Jan 2022 - Jun 2023): Assistant Editor on the feature documentary The Long Water"
  - Shot interviews on Sony FX6 for 30+ clients
  - Color corrected footage shot on Sony FX3
""", encoding="utf-8")
    asked = gaps.questions(schema.load(path, tmp_path / "data" / "resume-index.yml"))
    assert [q["line"] for q in asked if q["kind"] == "number"] == [
        "Kestrel Studios (Jan 2022 - Jun 2023): Assistant Editor on the feature documentary The Long Water",
        "Color corrected footage shot on Sony FX3"]
