from datetime import datetime, timedelta, timezone

import best
import cfg
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
    top = best.score([job("strong", STRONG)], CONFIG, NOW, f)[0]
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
