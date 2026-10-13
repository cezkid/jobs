from datetime import datetime, timedelta, timezone

import best
import cfg
import rank
import store
import today
from conftest import make_job
from resume import knockout

CONFIG = cfg.load(cfg.PROFILES / "example.yml")
NOW = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)
RESUME = """contact: {name: Your Name, email: your.name@example.com, location: "Springfield, IL"}
summary: Accountant with six years of month-end close and reconciliations.
roles:
  - company: Example Co
    title: Senior Accountant
    start: "2020-01"
    end: present
    bullets:
      - Ran the month-end close in NetSuite and built account reconciliations in Excel.
skills:
  - group: Tools
    items: [Excel, NetSuite]
education:
  - institution: State University
    degree: Bachelor of Science
    field: Accounting
    end: "2019-05"
"""
STRONG = ["Bachelor's degree in Accounting", "3+ years of accounting experience", "Month-end close",
          "Account reconciliations", "Advanced Excel"]
WEAK = ["CPA license", "Experience with SAP", "Payroll tax filings", "Garnishments processing", "5+ years of audit"]


def facts():
    """What resume_facts reads off RESUME (test_resume_file_read_and_match_said reads the file)."""
    return {"stems": best.stems(RESUME), "years": 6, "degree": knockout.LADDER.index("bachelor's")}


def job(slug, asks=(), days=1, **over):
    return make_job(slug, **{"posted_at": (NOW - timedelta(days=days)).strftime(store.ISO), "seniority": None,
                             "enrichment": {"requirements": [{"text": t, "priority": "required"} for t in asks]}, **over})


def order(jobs, resume=None, config=CONFIG):
    return [j["public_slug"] for j in best.score(jobs, config, NOW, resume)]


# a posting the user can't back sat above one they fit: wasted tailoring on a likely no
def test_strong_match_beats_weak():
    f = facts()
    strong, weak = job("strong", STRONG), job("weak", WEAK)
    assert best.match(strong, f)[1] == (5, 5)
    assert best.match(weak, f)[0] < 0.5
    assert order([weak, strong], f) == ["strong", "weak"]


# "Fluent in Spanish" never matched a native speaker: Languages wasn't read (2026-10-08, 88 of
# 1,966 live required lines name a language)
def test_language_ask_backed_only_by_a_working_level_language():
    f = {**facts(), "languages": best.languages("Spanish Mandarin")}
    assert best.backed("Bilingual English/Spanish required", f) is True
    assert best.backed("Fluency in both Mandarin Chinese and English.", f) is True
    # English they share doesn't back the other half
    assert best.backed("Professional fluency in English and Korean", f) is False
    assert best.backed("Must be fluent in English", f) is None
    assert best.backed("Fluent in Spanish", facts()) is False


def test_resume_languages_below_working_level_back_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "ROOT", tmp_path)
    path = cfg.resume_path(CONFIG, "master")
    path.parent.mkdir(parents=True)
    path.write_text(RESUME + "languages: [English (Native), Spanish (Fluent), French (Conversational), Portuguese]\n",
                    encoding="utf-8")
    assert best.resume_facts(CONFIG, NOW.date())["languages"] == {"english", "spanish", "portuguese"}


# a 15-line list of duties ranked like a 4-line one (owner: "some ask a lot")
def test_heavy_asks_score_lower_and_say_so():
    light = job("light", ["Excel", "Month-end close", "Reconciliations", "Journal entries"])
    heavy = job("heavy", [f"Lead the {w} program" for w in "abcdefghijklmno"])
    bn = CONFIG["rank"]["best_next"]
    assert best.asks(light, CONFIG, bn)[0] == 1.0 and best.asks(heavy, CONFIG, bn)[0] == 0.0
    assert order([heavy, light]) == ["light", "heavy"]
    why = best.reasons(best.score([heavy], CONFIG, NOW, None)[0], CONFIG, NOW)
    assert "Asks a lot: 15 requirements, 15 to lead or manage" in why


# a head of HR saw every director posting called heavy for asking them to lead - leading is the job
def test_leader_lead_duties_count_once():
    posting = job("vp", [f"Lead the {w} program" for w in "abcdefghij"])
    bn = CONFIG["rank"]["best_next"]
    leader = cfg.merge(CONFIG, {"rank": {"career_level": "leader"}})
    assert best.asks(posting, CONFIG, bn)[1:] == (10, 10) and best.asks(posting, CONFIG, bn)[0] == 0.0
    assert best.asks(posting, leader, bn) == (0.75, 10, 0)
    assert "to lead or manage" not in best.reasons(best.score([posting], leader, NOW, None)[0], leader, NOW)


# a level far above theirs listed as an easy pick
def test_seniority_two_rungs_up_halves_asks():
    config = cfg.merge(CONFIG, {"rank": {"career_level": "mid"}})
    bn = config["rank"]["best_next"]
    lead, senior = job("lead", ["Excel"], seniority="director"), job("senior", ["Excel"], seniority="senior")
    assert best.asks(lead, config, bn)[0] == 0.5 and best.asks(senior, config, bn)[0] == 1.0
    assert "director level, above yours" in best.reasons(best.score([lead], config, NOW, None)[0], config, NOW)


# their "remote first" ignored: an onsite job topped the list
def test_where_follows_their_own_tier_order():
    remote, local = job("remote"), job("local", tier="local", work_mode="onsite", cities=["Springfield"])
    assert best.where(remote, cfg.tier_order(CONFIG)) == 1.0 and best.where(local, cfg.tier_order(CONFIG)) == 0.0
    assert order([local, remote]) == ["remote", "local"]
    flipped = cfg.merge(CONFIG, {"passes": list(reversed(CONFIG["passes"]))})
    assert order([remote, local], config=flipped) == ["local", "remote"]


# a 20-day-old posting (likely filled) above one from yesterday (owner: "newer jobs are better")
def test_fresh_beats_twenty_days_old():
    new, old = job("new", days=1), job("old", days=20)
    assert best.fresh(new, NOW, 21) > 0.9 and best.fresh(old, NOW, 21) < 0.1
    assert order([old, new]) == ["new", "old"]
    assert "posted 20 days ago" in best.reasons(best.score([old], CONFIG, NOW, None)[0], CONFIG, NOW)


# top picks 5-7 days old while 19 went up in the last day (owner 2026-10-08): last day first,
# widened only when it holds too few
def test_last_day_first_widens_when_too_few():
    pay = dict(salary_min=250000, salary_max=250000, salary_currency="USD", salary_period="year")
    week = [job(f"week{i}", STRONG, days=6, **pay) for i in range(5)]
    day = [job(f"day{i}", days=1) for i in range(5)]
    assert order(week + day, facts())[:5] == [f"day{i}" for i in range(5)]
    # only 2 from the last day: widen to 2, 3, 5, 7 days until 5 => the strong week-old ones join, by score
    assert set(best.windows(week + day[:2], NOW, [1, 2, 3, 5, 7, 14, 21], 5).values()) == {0}
    assert order(week + day[:2], facts())[:5] == [f"week{i}" for i in range(5)]
    # age unknown => after every dated group
    assert best.windows(day + [job("undated", posted_at=None)], NOW, [1, 2], 5)["undated"] == 1


# pay below their floor ranked like pay above it
def test_pay_higher_first_floor_halves():
    pay = lambda lo: dict(salary_min=lo, salary_max=lo, salary_currency="USD", salary_period="year")
    hi, mid, low, none = job("hi", **pay(150000)), job("mid", **pay(90000)), job("low", **pay(40000)), job("none")
    assert order([none, low, mid, hi]) == ["hi", "mid", "none", "low"]
    assert "(below your pay)" in best.reasons(best.score([low], CONFIG, NOW, None)[0], CONFIG, NOW)


# the same list read in a different order each time: "job 3 was first a minute ago"
def test_ties_by_listing_id():
    assert order([job("b"), job("c"), job("a")]) == ["a", "b", "c"]


# no resume yet: a guess at fit would be a made-up number => match neutral + the page says why
def test_no_resume_match_neutral_and_said(conn, tmp_path, monkeypatch):
    assert best.match(job("x", STRONG), None) == (0.5, None)
    assert best.match(job("x"), facts()) == (0.5, None)
    monkeypatch.setattr(cfg, "ROOT", tmp_path)
    assert best.resume_facts(CONFIG, NOW.date()) is None
    store.upsert(conn, [job("x", STRONG)], "2026-10-04T11:00:00Z")
    rows, has_resume = today.best_rows(conn, CONFIG, NOW)
    assert not has_resume and today.best_section(conn, CONFIG, rows, has_resume)["note"] == today.NO_RESUME_NOTE
    assert "Matches" not in rows[0]["why"]


# their resume file read: why line says how many asks it backs
def test_resume_file_read_and_match_said(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "ROOT", tmp_path)
    path = cfg.resume_path(CONFIG, "master")
    path.parent.mkdir(parents=True)
    path.write_text(RESUME, encoding="utf-8")
    f = best.resume_facts(CONFIG, NOW.date())
    assert f["years"] >= 6 and f["degree"] == 2
    top = best.score([job("strong", STRONG, title="Staff Accountant")], CONFIG, NOW, f)[0]
    assert best.reasons(top, CONFIG, NOW).startswith("Matches 5 of 5 asks · pay not listed · remote · posted 1 day ago")


# "Active CAMS certification" counted as backed by any certificate ("certification" = half its
# words), and Series 63 backed Series 24 - numbers never read (2026-10-09)
def test_a_licence_or_certification_ask_is_backed_only_by_that_one():
    f = {**facts(), "stems": best.stems(RESUME + " Certified Fraud Examiner (CFE) certification. FINRA Series 63"),
         "credentials": knockout.credential_text({"certifications": [{"name": "Certified Fraud Examiner (CFE)"},
                                                                     {"name": "FINRA Series 63"}]})}
    assert best.backed("Active CAMS certification", f) is False
    assert best.backed("FINRA Series 24 license", f) is False
    assert best.backed("FINRA Series 63 license", f) is True
    assert best.backed("CAMS, CFE, or CRCM certification", f) is True
    assert best.backed("Bachelor's degree in Accounting and an active CFE designation", f) is True


# three lines asking CPA took -0.45 off and said it three times (2026-10-10): once per credential
def test_a_missing_credential_is_one_demerit_however_many_lines_ask_it():
    cpa = job("cpa", ["Active CPA license required", "Must hold CPA certification", "CPA required"])
    beyond = rank.asks_beyond(cpa, CONFIG, None, NOW.date(), knockout.credential_text({}))
    assert beyond == ["asks CPA, not in your resume"]
    assert best.demerits(dict(cpa, beyond=beyond), CONFIG) == 1


# 2026-10-09, 3,828 video / editor / motion required lines: "Adobe" or "Pro" on a resume (Photoshop,
# Final Cut Pro) backed 60+ asks for Premiere Pro or After Effects; "sound effects" backed After
# Effects; "editing" never met "edited" (6-letter stems); a portfolio ask counted against everyone
def test_video_asks_read_by_tool_word_ending_and_portfolio_link():
    f = {**facts(), "stems": best.stems("Edited videos in Final Cut Pro; retouched in Adobe Photoshop; "
                                        "sound effects; resolved tickets; Microsoft Word; 30-bed unit")}
    assert best.backed("Expert in Adobe Premiere Pro", f) is False
    assert best.backed("Advanced After Effects skills", f) is False
    assert best.backed("Experience in DaVinci Resolve", f) is False
    assert best.backed("Must know Final Cut Pro", f) is True
    assert best.backed("Proficiency in the Adobe Creative Suite", f) is True
    assert best.backed("Good knowledge of Microsoft Office and Adobe Suites", f) is True
    assert best.backed("Experience editing video", f) is True
    assert best.backed("Legal authorization to work in the United States", f) is None  # the form's
    asks = "Strong portfolio or demo reel showcasing commercial editing"
    assert best.backed(asks, {**f, "portfolio": True}) is True
    assert best.backed(asks, {**f, "portfolio": False}) is False
    assert best.backed(asks, f) is None  # resume details not read: can't tell


def test_resume_facts_reads_a_portfolio_link(tmp_path, monkeypatch):
    path = tmp_path / "Resume details.yml"
    path.write_text(RESUME.replace("location:", "links: [vimeo.com/yourname], location:"))
    monkeypatch.setattr(cfg, "resume_path", lambda config, key: path)
    assert best.resume_facts(CONFIG, NOW.date())["portfolio"] is True
    path.write_text(RESUME)
    assert best.resume_facts(CONFIG, NOW.date())["portfolio"] is False


# "HR" in the ask, "Human Resources" on the page (or the reverse); "HRIS" asked of a resume that names Workday
def test_hr_asks_read_both_names_and_the_system_by_name():
    facts = {"stems": best.stems("Vice President, Human Resources. Moved payroll to Workday HCM."), "years": None,
             "degree": None, "languages": set()}
    assert best.backed("Progressive HR leadership", facts)
    assert best.backed("HRIS implementation", facts)
    other = {**facts, "stems": best.stems("Led HR for 4,000 staff")}
    assert best.backed("Human resources leadership", other)
    assert not best.backed("HRIS implementation", other)


# security, 2026-10-09, a made-up director of cyber defense on 12,351 senior security required lines
def test_security_asks_read_by_short_form_tool_clearance_and_never_citizenship():
    resume = ("Ran the SOC on Splunk Enterprise Security and CrowdStrike Falcon; moved identity to Okta; "
              "vaulted admin accounts in CyberArk.")
    f = {**facts(), "stems": best.stems(resume), "languages": set(),
         "credentials": knockout.credential_text({"other": [{"heading": "Security Clearance",
                                                             "lines": ["Active TS/SCI with CI polygraph"]}]})}
    assert best.backed("Experience with identity and access management platforms", f)
    assert best.backed("Hands-on EDR and SIEM experience", f)
    assert best.backed("Privileged access management tooling", f)
    assert best.backed("Experience running a security operations center", f)
    # the folded name adds no words: a SIEM on the page backs no "information systems" degree words
    assert not best.backed("Experience in information systems event planning", f)
    assert best.backed("Active TS/SCI clearance with polygraph", f) is True
    assert best.backed("Active TS/SCI clearance with polygraph", {**f, "credentials": "Active Secret clearance"}) is False
    assert best.backed("Must be a U.S. citizen", f) is None
    assert best.backed("Legal authorization to work in the United States", f) is None


# "Must be at least 18 years of age", a work permit, "lift 50 pounds" counted against everyone: no resume says
# them - the form asks (age 18+ on 12 of 143 forms, a work permit on 70). Age-coded wording sorted by itself
def test_asks_no_resume_answers_never_counted():
    f = facts()
    for ask in ("Must be at least 18 years of age", "Must be 18 years or older", "Must be at least 21",
                "Authorized to work in the US without sponsorship", "Must be eligible to work in the United States",
                "Will not require visa sponsorship now or in the future", "Must be able to lift 50 pounds",
                "Lifting up to 50 lbs regularly", "Ability to stand for long periods", "Recent college graduate",
                "Digital native comfortable with social media", "Young, energetic team player", "Must be under 30"):
        assert best.backed(ask, f) is None, ask
    # same words, a real ask: still read
    assert best.backed("18 years of experience in audit", f) is False
    assert best.backed("Authorized user of SAP", f) is False
    assert best.backed("Lift station maintenance", f) is False
    assert best.backed("Experience working with young children", f) is False
    assert best.backed("Sponsorship sales experience", f) is False
    # a real ask on the same line is read first
    assert best.backed("Authorized to work in the US; 10+ years of accounting experience", f) is False
    posting = job("x", STRONG + ["Must be at least 18 years of age", "Must be able to lift 50 pounds",
                                 "Authorized to work in the US without sponsorship", "Recent college graduate"])
    assert best.match(posting, f)[1] == (5, 5)


def test_resume_facts_read_their_own_sections_but_not_a_clearance_as_words(tmp_path, monkeypatch):
    path = tmp_path / "Resume details.yml"
    path.write_text(RESUME + "other:\n  - heading: Security Clearance\n    lines: [Active TS/SCI with CI polygraph]\n"
                             "  - heading: Awards\n    lines: [Splunk Boss of the SOC winner]\n")
    monkeypatch.setattr(cfg, "resume_path", lambda config, key: path)
    f = best.resume_facts(CONFIG, NOW.date())
    assert best.backed("Splunk administration", f)
    # "CI" in "CI polygraph" is no CI/CD
    assert not best.backed("CI/CD pipelines", f)
    assert best.backed("Active TS/SCI with polygraph", f) is True


# 4 in 10 live postings list no requirements: their "Matches 1 of 1" was the years tag alone, read as
# a perfect match, and filled the top above "8 of 8" (2026-10-11, 1,200 rows, 4 fields)
def test_few_asks_read_near_the_middle():
    f = facts()
    prior = CONFIG["rank"]["best_next"]["match_prior"]
    one = job("one", ["3+ years of accounting experience"])
    five = job("five", STRONG)
    assert best.match(one, f, prior)[0] < best.match(five, f, prior)[0] < 1
    assert best.match(job("none"), f, prior)[0] == 0.5
    assert order([one, five], f) == ["five", "one"]


# 4 in 10 postings list no requirements: the why line said "Matches 1 of 1 asks" when the one ask was
# the job search's years tag - read as a perfect match (2026-10-12)
def test_years_tag_alone_said_as_years():
    f = facts()
    tag = lambda years, **over: job("t", title="Staff Accountant", enrichment={"requirements": [],
                                                                               "experience_years_min": years}, **over)
    met, short = best.score([tag(5)], CONFIG, NOW, f)[0], best.score([tag(8)], CONFIG, NOW, f)[0]
    assert best.reasons(met, CONFIG, NOW).startswith("Asks 5+ years, you have them · ")
    assert best.reasons(short, CONFIG, NOW).startswith("Asks 8+ years, you have 6 · ")
    # a real line counted too: the share, as before
    both = job("b", ["Account reconciliations"], title="Staff Accountant")
    both["enrichment"]["experience_years_min"] = 5
    assert best.reasons(best.score([both], CONFIG, NOW, f)[0], CONFIG, NOW).startswith("Matches 2 of 2 asks")


# one employer held 2-4 of the top 10; the same posting sat twice under two company names
def test_employers_spread_and_copies_sink():
    f = facts()
    a1, a2 = job("a1", STRONG, company_slug="acme"), job("a2", STRONG, company_slug="acme")
    b = job("b", STRONG[:4], company_slug="beta")
    assert order([a1, a2, b], f) == ["a1", "b", "a2"]
    # same posting, markup aside, under a brand + its parent: below a weaker job
    copy = dict(title="Tableau Developer", description="<p>Why Sony?</p><p>Build dashboards.</p>")
    s1 = job("s1", STRONG, company_slug="playstation", **copy)
    s2 = job("s2", STRONG, company_slug="sony", title="Tableau  developer", description="<div><p>Why Sony?</p> <p>Build dashboards.</p></div>")
    c = job("c", STRONG[:3] + WEAK[:1], company_slug="gamma")
    assert order([s1, s2, c], f) == ["s1", "c", "s2"]
    # never hidden, and `best` stays as scored
    assert {j["public_slug"]: j["best"] for j in best.score([s2], CONFIG, NOW, f)}["s2"] == \
        {j["public_slug"]: j["best"] for j in best.score([s1, s2], CONFIG, NOW, f)}["s2"]


# an HR director's top 10 held "Tableau Developer"; nothing compared the posting's title w/ their work
def test_title_like_their_work_scores_higher():
    f = facts()
    assert best.title_fit(job("a", title="Senior Accountant II (Remote)"), f) == 1.0
    assert best.title_fit(job("b", title="Tableau Developer"), f) == 0.0
    # level words alone say nothing about the work
    assert best.title_fit(job("c", title="Senior Manager"), f) == 0.5
    assert best.title_fit(job("d", title="Tableau Developer"), None) == 0.5
    near, far = job("near", STRONG, title="Staff Accountant"), job("far", STRONG, title="Tableau Developer")
    assert order([far, near], f) == ["near", "far"]
    assert "title unlike your past work" in best.reasons(best.score([far], CONFIG, NOW, f)[0], CONFIG, NOW)
    assert "unlike" not in best.reasons(best.score([near], CONFIG, NOW, f)[0], CONFIG, NOW)


# "Front-End Engineer" on the resume met no word of "Frontend Developer" (9 of 74 same-field titles)
def test_front_end_spellings_meet():
    f = {**facts(), "stems": best.stems("Front-End Engineer; full stack work")}
    assert best.title_fit(job("a", title="Frontend Engineer"), f) == 1.0
    assert best.title_fit(job("b", title="Fullstack Engineer"), f) == 1.0


# "Knowledge of the Uniform System of Accounts for the Lodging Industry (USALI)" was backed by "Accounts"
# alone on any accounting resume: each capitalised word read as a tool of its own
def test_a_name_of_several_words_needs_half_its_words():
    f = facts()
    assert best.backed("Knowledge of the Uniform System of Accounts for the Lodging Industry (USALI)", f) is False
    assert best.backed("Advanced proficiency in Excel/Google Sheets", f) is True
    assert best.backed("Expertise in building Excel-based financial models", f) is True
    assert best.named("Experience with Excel/Google Sheets and the Uniform System of Accounts") == \
        [["excel"], ["google", "sheets"], ["uniform", "system", "accounts"]]


# a name of two words was met by its common half: "NIST SP 800-53" by NIST CSF, "Full Stack Developer" by any
# developer, "Node.js" by Next.js (the "js"), "US payroll regulatory requirements" by US GAAP (2026-10-12,
# 540 required lines labelled by an AI against 9 resumes: agreement 0.741 => 0.765)
def test_a_name_of_two_words_needs_both():
    f = {"stems": best.stems("Splunk, NIST CSF, React, Next.js, US GAAP, HR. Web Developer."), "years": 6, "degree": 2}
    assert best.backed("Working knowledge of NIST SP 800-53 security controls", f) is False
    assert best.backed("Manage a Full Stack Developer team", f) is False
    assert best.backed("Experience with Node.js or Express.js", f) is False
    assert best.backed("Strong knowledge of US payroll regulatory requirements", f) is False
    # the name's own word, any "kind of thing" word left out
    assert best.backed("Hands-on expertise with React.js", f) is True
    assert best.backed("Support cybersecurity per NIST Framework", f) is True
    assert best.backed("Broad HR Expertise", f) is True
    assert best.backed("Experience with US GAAP", f) is True


# 1 in 8 finance lines tagged required said "preferred" or "a plus": counted for and against everyone
def test_wishes_cut_out_of_required_lines():
    assert best.asked("Bachelor's degree in Accounting, Finance, or a related field is preferred.") == ""
    assert best.asked("6+ years of software engineering experience (healthcare experience a plus)") == \
        "6+ years of software engineering experience"
    assert best.asked("5+ years of payroll experience; CPA preferred") == "5+ years of payroll experience"
    assert best.asked("Experience with After Effects (required or strongly valued)").endswith("(required or strongly valued)")
    # never "5 plus years", "competitive advantage"
    assert best.asked("5 plus years of SQL") == "5 plus years of SQL"
    assert best.asked("Turn data into a competitive advantage") == "Turn data into a competitive advantage"
    j = job("w", ["MBA or CPA a plus.", "Month-end close"])
    assert best.required(j) == ["Month-end close"]


# when + where they work, travel, an employer's own statement: no resume answers them either way
def test_schedule_place_and_statements_not_counted():
    f = facts()
    for t in ("Ability to travel up to 10%", "Must be based in the US", "Available during Eastern Time hours",
              "Must be able to work on-site in our New York City office", "We are an Equal Opportunity Employer",
              "Time commitment of at least 5 hours a week"):
        assert best.backed(t, f) is None, t
    # a travel skill is still asked
    assert best.backed("Experience processing travel and expense reports", f) is not None


# a 5-day-old perfect fit sat at #152 under 60 weaker last-day posts: only the first picks are freshest-first
def test_first_picks_freshest_then_by_score():
    f = facts()
    fresh = [job(f"day{i}", WEAK, days=0, company_slug=f"d{i}") for i in range(7)]
    older = job("older", STRONG, days=4, title="Staff Accountant", company_slug="o")
    got = order(fresh + [older], f)
    assert got[:5] == sorted(got[:5]) and set(got[:5]) <= {j["public_slug"] for j in fresh}
    assert got[5] == "older"
    off = cfg.merge(CONFIG, {"rank": {"best_next": {"fresh_first": None}}})
    assert order(fresh + [older], f, off)[-1] == "older"


# "3+ years managing OneTrust" was met by any 3 years of work: the years' subject must be backed too
def test_years_ask_needs_what_they_are_years_of():
    f = facts()
    assert best.backed("3+ years of accounting experience", f) is True
    assert best.backed("5+ years of experience", f) is True
    assert best.backed("3+ years hands-on experience building out and managing OneTrust", f) is False
    assert best.backed("10+ years of accounting experience", f) is False


# "Sr. IT Compliance Analyst": "IT" read as the filler "it", so the title fit any compliance resume
def test_it_in_capitals_is_information_technology():
    assert "infotech" in best.words_of("Sr. IT Compliance Analyst")
    assert "infotech" in best.words_of("degree in Information Technology")
    assert best.words_of("make it work") == ["make"]
