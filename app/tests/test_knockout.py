import time
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
    ("Required certifications: ACLS, BLS, NIHSS, TN active RN license.", ["RN", "ACLS", "BLS", "NIHSS"], True),
    ("BLS, ACLS, and PALS certification (as required by individual ASC policy)", ["BLS", "ACLS", "PALS"], False),
    # risk management (2026-10-09): no credential word, a capital C, a menu with "and" inside a name
    ("CPA required", ["CPA"], False),
    ("Active CPA.", ["CPA"], False),
    ("A certification as CPA or CIA is required", ["CPA", "CIA"], True),
    ("Professional Certification, such as CIA or CPA required", ["CIA", "CPA"], True),
    ("SIE, Series 7, Series 57 required", ["Series 7", "Series 57", "SIE"], False),
    ("Certified in Risk and Information Systems Control (CRISC), Certified Information Security Manager (CISM), "
     "Certified Internal Auditor (CIA), Certified Information Systems Security Professional (CISSP),",
     ["CRISC", "CISM", "CIA", "CISSP"], True),
    # project + program management (2026-10-09): mixed-case short forms, the name in brackets, a bare line
    ("PMP (Project Management Professional) certification", ["PMP"], False),
    ("PMP", ["PMP"], False),
    ("Current PMI Project Management Professional (PMP) or Program Management Professional (PgMP) certification",
     ["PMP", "PgMP"], True),
    ("• Scaled Agile Framework (SAFe) Certification", ["SAFe"], False),
    ("Active ITILv4 certification", ["ITILv4"], False),
    ("Licensures and Certifications - PMP, ITILF.", ["PMP", "ITILF"], False),
    # the issuing body in brackets is not the ask; both spelled-out names are
    ("2. Current BLS (ARC/AHA) certificate upon hire and maintain current.", ["BLS"], True),
    ("Basic Life Support (BLS) and Advanced Cardiovascular Life Support (ACLS) certifications required",
     ["BLS", "ACLS"], False),
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
    # risk management sample: a shouted heading, years of the work, an issuing body, a sales system
    "REQUIRED CERTIFICATES, LICENSES, REGISTRATIONS",
    "7 years of RN or clinical professional experience, 5 yrs of risk management experience required",
    "· Regulatory Affairs Certification (RAPS).",
    "· Regulatory Affairs Certification (RAC) (Optional)",
    "CRM experience required; Salesforce experience preferred.",
    "Relevant certifications (CISA, CISM, CRISC, or CISSP) are beneficial",
    "Degree in a quantitative discipline required; professional designations such as CFA or FRM preferred.",
    # project management sample: a recommendation, an either-or w/ experience, a course after hire
    "Recommended certification: CSM, PSM, PMI-ACP, SAFe, or comparable Agile delivery credential.",
    "Active PMP certification (or equivalent program management credential)",
    "Upon hire: National Institutes of Health Stroke Scale Certificate - NIH Stroke Scale Training Course",
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


# a long list of short forms failed in hours, not microseconds: every rank stalled on one such line
def test_a_long_list_of_short_forms_reads_at_once():
    states = ", ".join("AL AR AZ CA CO CT DC FL GA IL KS KY MA MD ME MI MN MO NC NH NJ NV NY OH OR PA SC TN TX UT "
                       "VA WA WI".split())
    started = time.perf_counter()
    assert knockout.credentials_asked(f"Must reside in one of Point's states of operation ({states})") is None
    assert time.perf_counter() - started < 0.5


def test_a_spelled_out_certification_holds_its_initials_unless_it_names_its_own():
    have = knockout.credential_text({"certifications": [{"name": "Project Management Professional"},
                                                        {"name": "Program Management Professional (PgMP)"}]})
    assert knockout.credentials_missing("Active PMP certification", have) == []
    assert knockout.credentials_missing("PgMP certification required", have) == []
    have = knockout.credential_text({"certifications": [{"name": "Program Management Professional (PgMP)"}]})
    assert knockout.credentials_missing("Active PMP certification", have) == ["PMP"]


# an exam part passed or a candidacy is on the way to the credential, not the credential
def test_an_exam_part_or_candidacy_does_not_hold_the_credential():
    have = knockout.credential_text({"certifications": [{"name": "FRM Part I (passed 2025)"},
                                                        {"name": "CFA Level II Candidate"}, {"name": "CPA"}]})
    assert knockout.credentials_missing("FRM certification required", have) == ["FRM"]
    assert knockout.credentials_missing("Active CFA charterholder", have) == ["CFA"]
    assert knockout.credentials_missing("CPA required", have) == []


# a licence the resume says lapsed holds nothing now: job-tailor writes "Series 7 (passed 2019; not currently
# registered)"; before this the ranking read it as held (plan-2tk)
def test_a_lapsed_licence_is_on_the_resume_but_not_held():
    have = knockout.credential_text({"certifications": [
        {"name": "Series 7 (passed 2019; not currently registered)"}, {"name": "CPA (inactive)"},
        {"name": "CAMS - expired 2022"}, {"name": "Series 63"}],
        "summary": "Series 66 and 65 holder; Series 24 lapsed.",
        "roles": [{"bullets": ["Cut expired-document backlog 40% for CISA audits"]}]})
    assert knockout.credentials_missing("FINRA Series 7 and Series 24 licenses (required)", have) == ["Series 7", "Series 24"]
    assert knockout.credentials_missing("Active CPA license required.", have) == ["CPA"]
    assert knockout.credentials_missing("Active CAMS certification", have) == ["CAMS"]
    assert knockout.credentials_missing("Series 63 license", have) == []
    assert knockout.credentials_missing("Series 66 license required", have) == []
    # a lapse word further along a bullet is no lapse of the credential
    assert knockout.credentials_missing("CISA certification required", have) == []
    assert knockout.lapsed("Series 7", have) and not knockout.lapsed("FRM", have)
    assert knockout.missing_words(["Series 7", "Series 24"], have) == "not current on your resume"
    assert knockout.missing_words(["Series 7", "FRM"], have) == "not in your resume"
    job = {"requirements": [{"text": "Active CPA license required.", "priority": "required"}]}
    assert knockout.shortfalls({"certifications": [{"name": "CPA (inactive)"}]}, job, TODAY) == [
        'Asks CPA ("Active CPA license required."). Your resume details show it as no longer current - '
        "said that way on the page, never as held now."]


def test_a_credential_shortfall_is_said_quoting_the_posting_only_with_resume_details():
    job = {"requirements": [{"text": "FINRA Series 7 and Series 24 licenses (required)", "priority": "required"},
                            {"text": "CAMS certification preferred", "priority": "preferred"}]}
    assert knockout.shortfalls(master(9, "BS"), job, TODAY) == [
        'Asks Series 7 and Series 24 ("FINRA Series 7 and Series 24 licenses (required)"). '
        "Not in your resume details - if you hold them, they can go in there."]
    assert knockout.shortfalls({}, job, TODAY) == []


# 204 of 551 video postings w/ requirements ask to see work; "portfolio" is also money and "Reels"
# Instagram's (2026-10-09, required lines of 6 fields read by hand)
def test_portfolio_asked_reads_work_samples_not_money_or_instagram():
    asked = ["Strong portfolio or demo reel showcasing cinematic storytelling", "Please include a link to your reel",
             "Portfolio of 3-5 edited and published clips", "A portfolio or examples of previous video editing work",
             "Evidence of exceptional ability (prior projects, portfolio of work, completed products, etc)"]
    not_asked = ["Experience managing complex banking structures and global cash portfolios",
                 "Have owned the accounting for a portfolio of minority/strategic investments",
                 "messaging frameworks for a dedicated product line or enterprise portfolio.",
                 "Familiarity with TODAY, NBC News and the NBCUniversal portfolio",
                 "Strong understanding of EGM-specific animation elements (reel spins, transitions)",
                 "Experience editing TikTok, Instagram Reels and YouTube Shorts",
                 "3+ years drafting and prosecuting patents, managing portfolios"]
    assert [knockout.portfolio_asked(t) for t in asked] == [True] * len(asked)
    assert [knockout.portfolio_asked(t) for t in not_asked] == [False] * len(not_asked)


def test_a_portfolio_ask_without_a_link_is_said_once():
    job = {"requirements": [{"text": "Portfolio or reel required", "priority": "required"},
                            {"text": "Reel and portfolio of work", "priority": "required"},
                            {"text": "A strong portfolio", "priority": "preferred"}]}
    short = knockout.shortfalls(master(9, "BS"), job, TODAY)
    assert len(short) == 1 and short[0].startswith('Asks to see your work - a portfolio or reel ("Portfolio or reel required")')
    linked = {**master(9, "BS"), "contact": {"links": ["linkedin.com/in/you", "vimeo.com/you"]}}
    assert knockout.shortfalls(linked, job, TODAY) == []
    profile_only = {**master(9, "BS"), "contact": {"links": ["linkedin.com/in/you"]}}
    assert len(knockout.shortfalls(profile_only, job, TODAY)) == 1


# a head of HR w/ SHRM-SCP + SPHR was told a posting asks SHRM-CP or PHR they lack (2026-10-09)
@pytest.mark.parametrize("line", ["SHRM-CP or PHR certification for CALIFORNIA required",
                                  "Professional in Human Resources Certification (PHR)",
                                  "PHR/SPHR or SHRM-CP/SCP certification, or related certification(s).",
                                  "SHRM and/or HRCI certification."])
def test_senior_hr_credential_answers_its_junior_one(line):
    have = "SHRM Senior Certified Professional (SHRM-SCP)\nSenior Professional in Human Resources (SPHR)"
    assert knockout.credentials_missing(line, have) == []
    assert knockout.credentials_missing(line, "PMP")
