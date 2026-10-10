import pytest

from apply import answers, questions


@pytest.fixture(autouse=True)
def file(tmp_path, monkeypatch):
    monkeypatch.setattr(answers, "FILE", tmp_path / "Saved answers.yml")
    monkeypatch.setattr(answers.cfg, "DATA", tmp_path)


def q(title, kind="text", options=(), answer=None, source=""):
    return {**questions.question("q1", title, kind, True, options), "answer": answer, "source": source}


def test_salary_phrasings_share_a_topic_current_pay_never_kept():
    assert answers.topic("What are your salary expectations?") == answers.topic("Desired compensation") == "expected pay"
    assert answers.key(q("What is your current salary?")) is None


def test_age_gate_apart_from_an_age_range_and_how_you_heard_one_topic():
    assert answers.topic("Are you 18 or older?") == "18 or older"
    assert answers.topic("What is your age range?") is None
    assert answers.topic("How did you hear about this job?") == answers.topic("Where did you hear about us?")


def test_work_permit_sensitive_and_demographics_never_kept():
    for title in ("Are you authorized to work in the United States?", "Will you require visa sponsorship?",
                  "What is your date of birth?", "What is your gender?", "Where are you currently located?",
                  "Do you have an active TS/SCI clearance?", "What level of security clearance do you hold?",
                  "Have you completed a polygraph?"):
        assert answers.key(q(title)) is None, title


def test_consent_and_signature_never_kept():
    for title in ("I agree to the Terms and Conditions", "SMS consent", "Electronic Signature",
                  "I certify that the information above is true"):
        assert answers.key(q(title, "yesno")) is None, title
    assert answers.keep([q("I agree to the Terms and Conditions", "yesno", answer="Yes", source=questions.USER_SAID)],
                        "Job 5", "Acme", "2026-10-03") == 0
    assert answers.recall([{"key": "i agree to the terms and conditions", "question": "I agree to the Terms and "
                            "Conditions", "answer": "Yes", "job": "Job 5", "on": "2026-10-03"}],
                          q("I agree to the Terms and Conditions", "yesno")) is None


def test_only_the_users_own_words_are_kept_and_named_when_recalled():
    asked = [q("How did you hear about this job?", answer="Company website", source=questions.USER_SAID),
             q("Why us?", "longtext", answer="Drafted by the AI", source="ask the user")]
    assert answers.keep(asked, "Job 5", "Acme", "2026-09-12") == 1
    mode, hit = answers.recall(answers.load(), q("How did you find out about this role?"))
    assert mode == "fill" and answers.named(hit) == "your answer from Job 5's form, 2026-09-12"


def test_pay_offered_never_filled_and_a_choice_filled_only_when_offered():
    answers.keep([q("Desired salary?", answer="$95,000", source=questions.USER_SAID),
                  q("Are you at least 18?", "choice", ("Yes", "No"), answer="Yes", source=questions.USER_SAID)],
                 "Job 5", "Acme", "2026-09-12")
    drafted = questions.draft([q("What are your salary expectations?"), q("Are you over the age of 18?", "choice", ("Yes", "No"))],
                              {"name": "Jane Doe"}, saved=answers.load())
    assert drafted[0]["answer"] is None and "offer saved answer '$95,000'" in drafted[0]["source"]
    assert drafted[1]["answer"] == "Yes" and drafted[1]["source"].startswith(questions.SAVED)


def test_compound_question_asks_and_forget_removes_only_that_one():
    assert answers.key(q("Are you 18 or older and how did you hear about us?")) is None
    answers.keep([q("Notice period?", answer="2 weeks", source=questions.USER_SAID),
                  q("Start date?", answer="Nov 1", source=questions.USER_SAID)], "Job 7", "Initech", "2026-10-01")
    saved = answers.load()
    saved.pop(0)
    answers.write(saved)
    assert [s["key"] for s in answers.load()] == ["start date"]


def test_a_students_status_and_permit_are_never_kept():
    for title in ("Are you currently enrolled in a degree program?", "What is your cumulative GPA?",
                  "Expected graduation date", "Are you currently on F-1 OPT?", "Do you have an EAD card?",
                  "Are you a current student?"):
        assert answers.key(q(title)) is None, title
    said = [q("Anything else we should know?", answer="I'm on F-1 OPT until June 2028", source=questions.USER_SAID)]
    assert answers.keep(said, "Job 5", "Acme", "2026-10-07") == 0
