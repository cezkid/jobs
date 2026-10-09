from datetime import date

import pytest

from resume import knockout

TODAY = date(2026, 10, 1)


@pytest.mark.parametrize("text, years", [
    ("5+ years of experience in software development", 5),
    ("10-15 years of progressive experience in FP&A", 10),
    ("At least five years of experience building production software", 5),
    ("5+ years accounting experience within an e-commerce, retail or CPG environment", 5),
    ("8+ years in manufacturing or hardware cost accounting.", 8),
    ("Minimum of one year post-graduate clinical experience", 1),
    ("Must be at least 18 years of age.", None),
    ("Must be at least 16 years old", None),
    ("CPMA certification a plus (must be obtained within 1 year of hire).", None),
    ("Strong communication skills", None),
    # school, not work (a student's internship asks): "work" inside "coursework", "of" after the years
    ("Completed at least 2 years of undergraduate study", None),
    ("Completed 2 years of coursework in accounting", None),
    ("Two years of college or equivalent", None),
    ("Completed at least two years of a four-year degree program", None),
    ("2+ years of work experience in retail", 2),
    ("Enrolled in a Bachelor's degree program and 3 years of experience in sales", 3),
    ("Must be enrolled and have at least finished one year of a Master's or PhD degree in Chemical Engineering", None),
    ("Completion of one to two years of a BS in Mechanical or Aerospace Engineering program", None),
    ("Recent graduate or up to 2 years of engineering experience through internships", None),
    ("5 years of experience after your degree in accounting", 5),
    # live lines a first try read as school (2026-10-07): the experience said later wins
    ("Minimum 5+ years of high school and/or club basketball coaching experience", 5),
    ("5+ years of enterprise sales and/or relevant consulting or program management experience", 5),
    ("Three years of full-time teaching in a public school", 3),
])
def test_years_asked_reads_the_lower_bound_never_age_or_deadlines(text, years):
    assert knockout.years_asked(text) == years


@pytest.mark.parametrize("text, level", [
    ("Bachelor's degree in Accounting, Finance, or related field required", "bachelor's"),
    ("Bachelor's or Master's degree in Computer Science", "bachelor's"),
    ("Master's or Doctorate degree in construction management", "master's"),
    ("A Ph.D. in a relevant humanities discipline", "doctorate"),
    ("CPA required; MBA a plus", None),
    ("Eager to master specialized vein procedures rapidly", None),
    ("Currently pursuing an undergraduate degree in Finance", None),
    ("Bachelor's degree in Computer Science, Engineering, or equivalent practical experience.", None),
    ("Bachelor's degree required, or demonstrated equivalent combination of education and training", None),
    ("MD or DO degree; board certification in your specialty", None),
    ("High school diploma", "high school"),
])
def test_degree_asked_is_the_lowest_level_named_and_skips_what_says_nothing(text, level):
    assert knockout.degree_asked(text) == level


def test_degree_held_reads_written_or_short_forms():
    held = [knockout.degree_held({"degree": d}) for d in ("BS", "B.S.", "Associate of Applied Science", "MBA",
                                                          "PhD", "Juris Doctor", "Certificate in Welding",
                                                          "B.S. in Computer Science", "BA Economics")]
    assert held == ["bachelor's", "bachelor's", "associate's", "master's", "doctorate", None, None,
                    "bachelor's", "bachelor's"]


def master(years_worked: int, degree: str | None) -> dict:
    return {"roles": [{"start": f"{2026 - years_worked}-01", "end": "present", "bullets": []}],
            "education": [{"institution": "State College", "degree": degree}] if degree else []}


def test_only_a_visible_shortfall_is_said_quoting_the_posting():
    job = {"requirements": [
        {"text": "5+ years of experience in customer support", "priority": "required"},
        {"text": "Bachelor's degree in Business", "priority": "required"},
        {"text": "10+ years of experience leading teams", "priority": "preferred"}]}
    assert knockout.shortfalls(master(3, "AA"), job, TODAY) == [
        'Asks 5+ years ("5+ years of experience in customer support"). Your dated jobs add up to 3.',
        "Asks a bachelor's degree (\"Bachelor's degree in Business\"). Your highest in your resume details: associate's."]
    assert knockout.shortfalls(master(9, "BS"), job, TODAY) == []
    assert "none listed" in knockout.shortfalls(master(9, None), job, TODAY)[0]


def test_an_education_entry_it_cannot_read_says_nothing_about_degrees():
    job = {"requirements": [{"text": "Master's degree in Social Work", "priority": "required"}]}
    assert knockout.shortfalls(master(9, "Juris Doctor"), job, TODAY) == []


def test_overlapping_jobs_count_once():
    m = {"roles": [{"start": "2020-01", "end": "2022-12"}, {"start": "2021-06", "end": "2023-12"}]}
    assert knockout.dated_years(m, TODAY) == 4


GRAD_TODAY = date(2026, 10, 7)


@pytest.mark.parametrize("text, label", [
    # real required lines, 2026-10-07 (intern / new grad rows)
    ("Anticipated graduation date from an undergraduate program in December 2027 - June 2028", "Dec 2027 - Jun 2028"),
    ("Currently enrolled in a U.S. undergraduate or graduate degree program with a graduation date of December 2027 or later",
     "Dec 2027 or later"),
    ("Rising Junior or Senior graduating in 2027 or 2028", "2027-2028"),
    ("Undergraduate with graduation date of December 2027, May, or June 2028", "Dec 2027 - Jun 2028"),
    ("Graduating between Fall 2027 and Summer 2028", "Sep 2027 - Aug 2028"),
    ("Graduating in the 2028 calendar year", "2028"),
    ("Pursuing a degree in Computer Science, graduating by Summer 2029", "by Aug 2029"),
    ("Bachelor's or Master's degree in Computer Science, graduating before July 2026", "by Jun 2026"),
    ("Graduating in Spring 2027 or sooner and interested in a full-time position", "by Jun 2027"),
    ("To be eligible for this role, you need to graduate by Dec 2026 and be able to start FTE by January/February 2027.",
     "by Dec 2026"),
    ("MBA degree with planned graduation in May/June of 2027, with 4-7 years prior work experience preferred",
     "May 2027 - Jun 2027"),
    ("Graduation date of Spring 2028/2029 or Fall 2029", "Mar 2028 - Dec 2029"),
    ("Currently pursuing a degree in Marketing or a related field (2027 or 2028 graduates)", "2027-2028"),
    ("Graduating in Fall 2025 or graduated within the past two years.", "Oct 2024 - Oct 2026"),
    ("Expected completion of a BS degree in Civil Engineering in May 2027", "May 2027"),
    # the source cut off mid-date: the late end stays open, never read short
    ("Currently pursuing a degree in design with expected graduation in Fall 2027 or Spring/Summ", "Sep 2027 or later"),
])
def test_graduation_window_reads_the_widest_span_a_line_accepts(text, label):
    assert knockout.window_label(knockout.graduation_window(text, GRAD_TODAY)) == label


@pytest.mark.parametrize("text", [
    "You must be enrolled in an advanced degree program if graduating before June 2027.",  # a condition
    "Open exclusively to current Co-Op students (work period January-June 2027, 40 hrs/week)",  # no graduation
    "Bachelor's degree from an accredited university",
    "Graduate degree preferred",
    "Can start full-time in Summer 2027",
])
def test_graduation_window_says_nothing_without_a_graduation_date(text):
    assert knockout.graduation_window(text, GRAD_TODAY) is None


def test_only_a_graduation_clearly_outside_the_window_is_said():
    job = {"requirements": [{"text": "Graduating between December 2027 and June 2028", "priority": "required"}]}
    asked = knockout.graduation_asked
    assert asked(job, "2027-05", GRAD_TODAY) == ("Dec 2027 - Jun 2028", "Graduating between December 2027 and June 2028")
    assert asked(job, "2028-05", GRAD_TODAY) is None
    # a year alone spans its months: 2027 may be December 2027
    assert asked(job, "2027", GRAD_TODAY) is None
    assert asked(job, None, GRAD_TODAY) is None
    preferred = {"requirements": [{"text": "Graduating in 2030", "priority": "preferred"}]}
    assert asked(preferred, "2027-05", GRAD_TODAY) is None


def test_student_shortfalls_name_the_window_and_the_level_they_study_for():
    master = {"roles": [], "education": [{"institution": "Columbus State Community College", "degree": "AA",
                                          "end": "2027-05"}]}
    job = {"requirements": [
        {"text": "Currently pursuing a Bachelor's degree in Business", "priority": "required"},
        {"text": "Graduating between December 2027 and June 2028", "priority": "required"}]}
    assert knockout.shortfalls(master, job, GRAD_TODAY) == [
        'Asks to be studying for a bachelor\'s degree ("Currently pursuing a Bachelor\'s degree in Business"). '
        "Yours in progress: associate's.",
        'Asks graduating Dec 2027 - Jun 2028 ("Graduating between December 2027 and June 2028"). '
        "Your resume details say May 2027."]
    master["education"][0]["degree"] = "BS"
    master["education"][0]["end"] = "2028-05"
    assert knockout.shortfalls(master, job, GRAD_TODAY) == []


# required lines from live compliance, healthcare, finance and security postings (2026-10-09)
@pytest.mark.parametrize("text, named, any_one", [
    ("FINRA Series 7 and Series 24 licenses (required)", ["Series 7", "Series 24"], False),
    ("FINRA Series 24, 7 and 63 licenses", ["Series 24", "Series 7", "Series 63"], False),
    ("Active SIE, Series 7, and Series 24 licenses", ["Series 7", "Series 24", "SIE"], False),
    ("FINRA Series 14 or 24", ["Series 14", "Series 24"], True),
    ("Active CAMS certification", ["CAMS"], False),
    ("Active CPA license required.", ["CPA"], False),
    ("Bachelor's degree in Accounting, Finance, or related field and an active Certified Internal Auditor (CIA) designation",
     ["CIA"], True),
    ("CISSP, CRISC, CISM, or CISA certification", ["CISSP", "CRISC", "CISM", "CISA"], True),
    ("Current CMMC certification required: RP, CCP, or CCA.", ["CMMC"], True),
    ("Current Texas Registered Nurse (RN) with at least four (4) years of full-time emergency care experience "
     "and an active Texas RN license.", ["RN"], False),
    ("Required certifications: ACLS, BLS, NIHSS, TN active RN license.", ["RN", "ACLS", "BLS", "NIHSS"], False),
])
def test_credentials_asked_reads_what_a_line_asks_to_hold(text, named, any_one):
    got = knockout.credentials_asked(text)
    assert (got[0], got[2]) == (named, any_one)


# each a first try misread: a firm, a duty, a tool, a level, a topic, a wish, a category, a later step
@pytest.mark.parametrize("text", [
    "At least two (2) years of direct compliance experience working for, or providing dedicated compliance "
    "support to, a Registered Investment Adviser (RIA).",
    "Support critical day-to-day responsibilities including IAR registrations, communication reviews, OBA's, "
    "and regulatory filings (ADV's).",
    "Claude Code: System prompt construction, tool-use permission hardening, CLI credential isolation",
    "DoD 8570/8140 IAM Level II certification",
    "Direct experience preparing, reviewing, and submitting spacecraft and/or ground station FCC and NOAA "
    "license applications to tight timelines.",
    "TLS/SSL certificates and public key infrastructure fundamentals",
    "It's an asset if you hold a Certified Anti-Money Laundering Specialist (CAMS) certification",
    "Additional certifications like RAC (Regulatory Affairs Certification) advantageous",
    "Relevant certifications (CISA, CISSP, CISM, CIPP, etc.) are helpful but not required",
    "Professional designation such as CPA, CIA, CISA, etc. or progress towards designation",
    "Active SIE, Series 7, 24, and 63 or 66 licenses, or attainment of required licenses within the first year",
    "Series 65 license must be obtained within 90 days of hire",
    "Working knowledge of HIPAA security requirements, ISO 27001:2022 (including recertification audits), and PCI DSS.",
    "Valid driver's license and satisfactory driving record",
])
def test_credentials_asked_skips_lines_that_ask_no_credential_held_now(text):
    assert knockout.credentials_asked(text) is None


def test_a_credential_is_held_by_its_short_form_anywhere_or_a_certifications_initials():
    have = knockout.credential_text({"contact": {"name": "Jane Doe, CPA"},
                                     "certifications": [{"name": "Certified Internal Auditor"},
                                                        {"name": "FINRA Series 7, 63"}],
                                     "skills": [{"group": "Tools", "items": ["CISA"]}]})
    assert knockout.credentials_missing("Active CPA license required.", have) == []
    assert knockout.credentials_missing("Active CIA designation required.", have) == []
    assert knockout.credentials_missing("CISSP, CRISC, CISM, or CISA certification", have) == []
    assert knockout.credentials_missing("FINRA Series 7 and Series 24 licenses (required)", have) == ["Series 24"]
    assert knockout.credentials_missing("Series 63 license", have) == []
    assert knockout.credentials_missing("Active CAMS certification", have) == ["CAMS"]
    assert knockout.credentials_missing("5+ years of compliance experience", have) is None


def test_a_credential_shortfall_is_said_quoting_the_posting_only_with_resume_details():
    job = {"requirements": [{"text": "FINRA Series 7 and Series 24 licenses (required)", "priority": "required"},
                            {"text": "CAMS certification preferred", "priority": "preferred"}]}
    assert knockout.shortfalls(master(9, "BS"), job, TODAY) == [
        'Asks Series 7 and Series 24 ("FINRA Series 7 and Series 24 licenses (required)"). '
        "Not in your resume details - if you hold them, they can go in there."]
    assert knockout.shortfalls({}, job, TODAY) == []
