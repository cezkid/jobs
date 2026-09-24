from resume import vmock

# VMock's own page wording, 2026-09-24, with the candidate's name and resume text left out
SUMMARY = """Candidate Dashboard | Resume Module
Resume Feedback
Summary
System Feedback
Overall Score
VMock considers a lot of parameters across 3 core modules. Check how you performed on these parameters
65
/100
21 /40
Impact
Focuses on the quality of content and its impact on recruiters.
Action Oriented
Good Job!
Action verbs help recruiters understand key skills developed during different experiences.
Language
Needs Work!
Use clear, standardized terms and correct grammar to help recruiters accurately evaluate your skills.
9 /20
Presentation
Focuses on whether your resume is in sync with format requirements.
Overall Format
Needs Work!
Follow Resume level guidelines for presentations.
35 /40
Competencies
Assesses how well you have reflected your 5 core competencies.
Leadership
On Track!
It includes leadership by position as well as natural or assumed leadership.
Team Effort
Good Job!
It involves collaborating to achieve a shared goal.
Good Job!
On Track!
Needs Work!
How to improve your Resume?
Steps to Improve Your Score
Fix resume layout
+1
Correct overall format for better readability.
Review spell errors
+1
Spelling mistakes are a strict no. See spell check now!
Help
"""
FORMAT = """Overall Format
You are not meeting the industry format standards.
FAILING CHECKS2
* Hygiene Check
Color Check*
Section Spacing*
PASSING CHECKS 2
Branding Title*
Degree StylingEducation
"""
LANGUAGE = """Language
Overuse
On Track!
Spelling Error
Needs Work!
2 Spelling Error(s)
Grammar
Good Job!
"""


def test_summary_reads_score_modules_checks_and_steps_but_not_the_legend():
    got = vmock.parse_summary(SUMMARY)
    assert got["score"] == 65
    assert {m: (v["score"], v["of"]) for m, v in got["modules"].items()} == {
        "Impact": (21, 40), "Presentation": (9, 20), "Competencies": (35, 40)}
    assert got["modules"]["Competencies"]["checks"] == {"Leadership": "On Track", "Team Effort": "Good Job"}
    assert got["modules"]["Impact"]["checks"]["Language"] == "Needs Work"
    assert got["steps"] == ["Fix resume layout: Correct overall format for better readability.",
                            "Review spell errors: Spelling mistakes are a strict no. See spell check now!"]


def test_section_pages_read_failing_passing_and_status_lines():
    assert vmock.parse_checks(FORMAT) == {"status": {}, "failing": ["Color Check", "Section Spacing"],
                                          "passing": ["Branding Title", "Degree Styling"]}
    assert vmock.parse_checks(LANGUAGE)["status"] == {"Overuse": "On Track", "Spelling Error": "Needs Work",
                                                      "Grammar": "Good Job"}


def test_compare_names_what_moved_since_the_last_read():
    before = vmock.parse_summary(SUMMARY) | {"sections": {"f": vmock.parse_checks(FORMAT)}}
    now = vmock.parse_summary(SUMMARY.replace("65\n/100", "78\n/100").replace("9 /20", "19 /20")
                              .replace("Overall Format\nNeeds Work!", "Overall Format\nGood Job!"))
    now["sections"] = {"f": vmock.parse_checks(FORMAT.replace("Section Spacing*\n", "").replace("PASSING CHECKS 2\n", "PASSING CHECKS 3\nSection Spacing*\n"))}
    before["sections"]["lang"] = vmock.parse_checks(LANGUAGE)
    now["sections"]["lang"] = vmock.parse_checks(LANGUAGE.replace("Grammar\nGood Job!", "Grammar\nNeeds Work!"))
    assert vmock.compare(now, before) == ["Overall score 65 -> 78", "Presentation 9/20 -> 19/20",
                                          "Overall Format: Needs Work -> Good Job", "Grammar: Good Job -> Needs Work",
                                          "Section Spacing: now passing"]
    assert vmock.compare(now, None) == []
    report = vmock.report_md(now | {"read": "2026-09-25", "url": "u"}, vmock.compare(now, before))
    assert "**Overall: 78 out of 100**" in report and "- Color Check" in report


def test_upload_needs_the_users_yes(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["vmock", "upload", "resume.pdf"])
    try:
        vmock.main()
    except SystemExit as e:
        assert "ask them first" in str(e)
    else:
        raise AssertionError("upload ran without --yes")
