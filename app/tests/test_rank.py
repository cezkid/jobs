from datetime import datetime, timezone

import pytest

import cfg
import rank
from conftest import make_job
from resume import knockout

CONFIG = cfg.merge(cfg.load(cfg.PROFILES / "example.yml"), {"blocklist": {
    "categories": ["marketing", "sales"], "title_phrases": ["sales and marketing"]}})


def slugs(jobs):
    return [j["public_slug"] for j in jobs]


def test_blocklist_applies_before_ranking():
    jobs = [
        make_job("ok"),
        make_job("reposter", company_slug="JobGether"),
        make_job("marketing", category="marketing"),
        make_job("sales", category="Sales"),
        make_job("bundled", category="qa", title="Senior Software Engineer, QA, Sales and Marketing"),
    ]
    assert slugs(rank.rank(jobs, CONFIG)) == ["ok"]


NOW = datetime(2026, 9, 15, 12, tzinfo=timezone.utc)


def usd(lo=None, hi=None, period="year"):
    return {"salary_min": lo, "salary_max": hi, "salary_currency": "USD", "salary_period": period}


def test_rank_order_tier_trust_floor_pay_collections_recency():
    jobs = [
        make_job("local-top", tier="local", collections=["fortune500"], **usd(300000)),
        make_job("plain-new", posted_at="2026-09-15T11:00:00Z"),
        make_job("plain-old", posted_at="2026-09-10T11:00:00Z"),
        make_job("priced-low", **usd(40000)),
        make_job("priced-high", **usd(140000)),
        make_job("f500", collections=["fortune500", "us-h1b-sponsor"]),
        make_job("f500-low", collections=["fortune500"], **usd(30000)),
        make_job("ghost", reality={"repost_count": 6}, **usd(500000)),
    ]
    # pay filter off: the order a below-floor job keeps when it is let back
    shown = cfg.merge(CONFIG, {"rank": {"pay_filter": {"hide_below_floor": False}}})
    assert slugs(rank.rank(jobs, shown, NOW)) == [
        "priced-high", "priced-low", "f500-low", "f500", "plain-new", "plain-old", "ghost", "local-top",
    ]


def test_stale_row_sorts_last_in_tier_with_reason():
    jobs = [
        make_job("gone", fetched_at="2026-08-30T00:00:00Z", **usd(200000)),
        make_job("ghost", fetched_at="2026-09-14T00:00:00Z", reality={"repost_count": 9}),
        make_job("live", fetched_at="2026-09-14T00:00:00Z"),
        make_job("local", tier="local", fetched_at="2026-09-14T00:00:00Z"),
    ]
    ranked = rank.rank(jobs, CONFIG, NOW)
    assert slugs(ranked) == ["live", "ghost", "gone", "local"]
    assert rank.reasons(ranked[2], CONFIG, NOW).endswith("may be closed - not seen in 16d")


def test_live_copy_beats_stale_duplicate():
    jobs = [make_job("old-copy", title="Clerk", fetched_at="2026-08-01T00:00:00Z", **usd(50000)),
            make_job("live-copy", title="Clerk", fetched_at="2026-09-14T00:00:00Z")]
    assert slugs(rank.rank(jobs, CONFIG, NOW)) == ["live-copy"]


def test_old_salaried_row_above_old_unsalaried_row():
    old = {"age_days": 95, "class": "stale"}
    jobs = [make_job("unpaid", reality=old, posted_at="2026-09-15T11:00:00Z"),
            make_job("paid", reality=dict(old, age_days=102), **usd(80000, 110000))]
    assert slugs(rank.rank(jobs, CONFIG, NOW)) == ["paid", "unpaid"]


def test_reposted_old_or_evergreen_rows_sort_below_fresh():
    jobs = [
        make_job("reposted", reality={"repost_count": 5, "mass_posting_count": 1}, posted_at="2026-09-15T11:00:00Z"),
        make_job("old", reality={"age_days": 120}, posted_at="2026-09-15T11:00:00Z"),
        make_job("evergreen", reality={"class": "likely-evergreen"}, posted_at="2026-09-15T11:00:00Z"),
        make_job("fresh", reality={"repost_count": 1, "age_days": 3, "class": "fresh"}, posted_at="2026-09-01T00:00:00Z"),
    ]
    assert slugs(rank.rank(jobs, CONFIG, NOW))[0] == "fresh"
    assert "reposted 4x" in rank.reasons(jobs[0], CONFIG, NOW)


def test_duplicates_collapse_keeping_salaried_copy():
    jobs = [
        make_job("first", company="Acme, Inc.", first_fetched_at="2026-09-01T00:00:00Z"),
        make_job("paid", company="ACME", title="senior vue engineer first", first_fetched_at="2026-09-10T00:00:00Z", **usd(90000)),
        make_job("elsewhere", company="Acme", title="Senior Vue Engineer first", work_mode="onsite", cities=["Springfield"]),
    ]
    ranked = rank.rank(jobs, CONFIG, NOW)
    assert sorted(slugs(ranked)) == ["elsewhere", "paid"]
    assert next(j for j in ranked if j["public_slug"] == "paid")["duplicates"] == ["first"]


def test_duplicates_without_pay_keep_earliest_seen():
    jobs = [make_job("later", title="Clerk", first_fetched_at="2026-09-10T00:00:00Z"),
            make_job("earlier", title="Clerk", first_fetched_at="2026-09-01T00:00:00Z")]
    assert slugs(rank.rank(jobs, CONFIG, NOW)) == ["earlier"]


def test_range_reaching_floor_passes():
    assert rank.meets_floor(make_job("r", **usd(55000, 90000)), 60000)
    assert not rank.meets_floor(make_job("r", **usd(40000, 55000)), 60000)
    assert rank.annual_usd(make_job("r", **usd(55000, 90000))) == 72500


def test_missing_period_inferred_and_hourly_shown_per_hour():
    hourly = make_job("h", **usd(25, 35, None))
    assert rank.pay(hourly) == (25, 35, "hour")
    assert rank.pay_label(hourly) == "$25-35/hr"
    assert rank.pay(make_job("m", **usd(5000, None, None)))[2] == "month"
    assert rank.pay(make_job("y", **usd(70000, None, None)))[2] == "year"
    assert rank.pay_label(make_job("y", **usd(70000, 90000))) == "$70k-90k"
    assert rank.annual_usd(make_job("c", salary_min=200000, salary_currency="CAD")) is None


def test_copies_open_at_once_are_not_reposts():
    """repost_count counts open copies too: 3 of 3 open = one role in 3 places, never relisted."""
    copies = make_job("copies", reality={"repost_count": 3, "mass_posting_count": 3, "class": "fresh"},
                      posted_at="2026-09-15T11:00:00Z")
    relisted = make_job("relisted", reality={"repost_count": 6, "mass_posting_count": 3},
                        posted_at="2026-09-15T11:00:00Z")
    assert "reposted" not in rank.reasons(copies, CONFIG, NOW)
    assert rank.doubts(copies, CONFIG["rank"]) == []
    assert rank.doubts(relisted, CONFIG["rank"]) == ["reposted 3x"]
    assert slugs(rank.rank([relisted, copies], CONFIG, NOW)) == ["copies", "relisted"]


def test_ghost_signals_count_once():
    """old + reposted + evergreen is one doubt about the posting, not three: pay decides between
    it and a job w/ one other demerit."""
    config = level_config(career_level="entry")
    ghost = make_job("ghost", title="Accountant", reality={"repost_count": 9, "mass_posting_count": 1,
                                                          "age_days": 200, "class": "likely-evergreen"}, **usd(120000))
    senior = make_job("senior", title="Senior Accountant", **usd(60000))
    assert len(rank.doubts(ghost, config["rank"])) == 3
    assert slugs(rank.rank([senior, ghost], config, NOW)) == ["ghost", "senior"]


def test_clearance_named_demoted_only_when_cannot_hold():
    cleared = make_job("cleared", title="Systems Analyst", requires_clearance=True, **usd(150000))
    plain = make_job("plain", title="Data Analyst", **usd(90000))
    assert "needs a security clearance" in rank.reasons(cleared, CONFIG, NOW)
    assert slugs(rank.rank([plain, cleared], CONFIG, NOW)) == ["cleared", "plain"]
    for answer in ({"can_hold_clearance": False}, {"citizen_or_permanent_resident": False}):
        config = cfg.merge(CONFIG, {"work_authorization": answer})
        assert slugs(rank.rank([cleared, plain], config, NOW)) == ["plain", "cleared"], answer
    green_card = cfg.merge(CONFIG, {"work_authorization": {"citizen_or_permanent_resident": True}})
    assert rank.can_hold_clearance(green_card) is None


# a staffing firm's posting says so and sorts below the employers' own; keep = named only; hidden on their yes
def test_staffing_firm_named_sorted_lower_kept_or_hidden():
    firm = dict(make_job("firm", title="IT Project Manager", company="System One", **usd(150000)), company_staffing=1)
    direct = make_job("direct", title="IT Project Manager", company="Vanguard", **usd(120000))
    assert "staffing firm" in rank.reasons(firm, CONFIG, NOW) and "staffing firm" not in rank.reasons(direct, CONFIG, NOW)
    assert slugs(rank.rank([firm, direct], CONFIG, NOW)) == ["direct", "firm"]
    keep = level_config(staffing="keep")
    assert slugs(rank.rank([firm, direct], keep, NOW)) == ["firm", "direct"]
    assert "staffing firm" in rank.reasons(firm, keep, NOW)
    hide = cfg.merge(CONFIG, {"blocklist": {"staffing": True}})
    assert slugs(rank.rank([firm, direct], hide, NOW)) == ["direct"]


# no record says it: the firm's own name, or contract terms only a third party writes
@pytest.mark.parametrize("company, text, expected", [
    ("Burnetts Staffing", "", True), ("Motion Recruitment", "", True), ("TalentOla", "", True),
    ("murphysfamilystaffing.zohorecruit.com", "", True), ("acme.zohorecruit.com", "", False),
    ("Sapear Inc", "Rate-$60/per hr. on C2C all inclusive", True), ("ASK Consulting", "Pay rate: $75/hr. On W2", True),
    ("ektello", "<p>W2 contract, 4 months</p>", True), ("Silicon Beach Solutions", "structured as a Corp-to-Corp engagement", True),
    ("Acme", "Full-time role. No C2C or third parties.", False), ("Satsyil", "Employment: Full-Time, W2", False),
    ("AmazonWebServices", "please contact your Recruiting Partner", False), ("Vanguard", "We value talent.", False),
    # one word, no edge to find (2026-10-27); founding-engineer posts for a startup the poster won't name
    ("recruitingfromscratch", "", True), ("decircletalentpartner", "", True),
    ("mlabs", "<p>Our client, an innovative venture-backed fintech start-up, is building</p>", True),
    ("David Joseph & Company", "<h2>About the Company</h2><p>Our client is a seed-stage AI company</p>", True),
    ("Raydar", "Raydar is recruiting for this role on behalf of our client.", True),
    ("Clera", "<h3>About the Role</h3><p>Join an early-stage financial technology team building AI", True),
    ("Accenture Federal", "We help our clients modernize. Our client is the Department of Veterans Affairs.", False),
    ("CalCPA", "strengthen our client, employer, public and government trust", False),
    ("Scope Labs", "<h3>About the Role</h3><p>You will join our team", False)])
def test_staffing_firm_by_name_or_terms(company, text, expected):
    assert rank.staffing_firm(make_job("j", company=company, description=text)) is expected


# a staffing firm the record files as a nonprofit is never named a nonprofit employer
def test_staffing_firm_never_named_nonprofit():
    firm = dict(make_job("firm", description="We place talent."), company_nonprofit=1, company_staffing=1)
    assert rank.posting_says(firm, level_config(posting_says=["nonprofit"])["rank"]) == []


def level_config(**rank_over):
    return cfg.merge(CONFIG, {"rank": rank_over})


def test_seniority_mismatch_demoted_nulls_untouched():
    config = level_config(career_level="entry", employment_types=["full_time"])
    jobs = [
        make_job("director", title="Director of Accounting", posted_at="2026-09-15T11:00:00Z"),
        make_job("contract", title="Accountant II", employment_type="contract", posted_at="2026-09-15T11:00:00Z"),
        make_job("no-level", title="Accountant", employment_type=None, posted_at="2026-09-01T00:00:00Z"),
        make_job("staff", title="Staff Accountant", posted_at="2026-09-01T00:00:00Z"),
    ]
    assert slugs(rank.rank(jobs, config, NOW)) == ["no-level", "staff", "director", "contract"]
    senior = level_config(career_level="senior")
    assert rank.mismatches(make_job("i", title="Audit Intern"), senior["rank"]) == ["title below your level"]
    assert rank.mismatches(make_job("i", title="Internal Auditor"), senior["rank"]) == []


def test_no_sponsorship_demoted_only_for_a_user_who_needs_it():
    jobs = [
        make_job("no-sponsor", enrichment={"visa_sponsorship": False}, **usd(200000)),
        make_job("unsaid", enrichment={}, **usd(100000)),
        make_job("sponsors", enrichment={"visa_sponsorship": True}, **usd(90000)),
    ]
    needs = cfg.merge(CONFIG, {"work_authorization": {"needs_sponsorship": True}})
    assert slugs(rank.rank(jobs, needs, NOW)) == ["unsaid", "sponsors", "no-sponsor"]
    assert rank.reasons(jobs[0], needs, NOW).endswith("says no visa sponsorship")
    # citizen, green card, or not asked: the label changes nothing
    for answer in (False, None):
        config = cfg.merge(CONFIG, {"work_authorization": {"needs_sponsorship": answer}})
        assert slugs(rank.rank(jobs, config, NOW)) == ["no-sponsor", "unsaid", "sponsors"]
        assert "sponsorship" not in rank.reasons(jobs[0], config, NOW)


def test_title_phrase_matches_whole_words_only():
    config = cfg.merge(CONFIG, {"blocklist": {"title_phrases": ["intern"]}})
    jobs = [make_job("aud", title="Internal Auditor"), make_job("tax", title="Tax Intern (Summer)")]
    assert slugs(rank.rank(jobs, config, NOW)) == ["aud"]
    assert slugs(rank.would_hide(jobs, "intern", CONFIG["blocklist"])) == ["tax"]


def test_title_keep_spares_phrase_inside_wider_title():
    blocklist = {"title_phrases": ["staff"],
                 "title_keep": ["member of technical staff", "senior/staff", "senior, staff"]}
    config = cfg.merge(CONFIG, {"blocklist": blocklist})
    jobs = [make_job("staff", title="Staff Frontend Engineer"),
            make_job("above", title="Senior Staff Engineer"),
            make_job("mts", title="Member of Technical Staff, Product"),
            make_job("either", title="Senior / Staff Full Stack Engineer"),
            make_job("paren", title="Software Engineer (Senior, Staff+)"),
            make_job("mts-staff", title="Staff Member of Technical Staff")]
    assert slugs(rank.rank(jobs, config, NOW)) == ["mts", "either", "paren"]
    hidden = rank.would_hide(jobs, "staff", {"title_keep": blocklist["title_keep"]})
    assert slugs(hidden) == ["staff", "above", "mts-staff"]


def test_company_blocklist_matches_name_as_well_as_slug():
    config = cfg.merge(CONFIG, {"blocklist": {"companies": ["Staffing Pros"]}})
    jobs = [make_job("a", company="Staffing Pros LLC", company_slug="staffingpros-2"), make_job("b")]
    assert slugs(rank.rank(jobs, config, NOW)) == ["b"]


def test_reasons_say_why_in_plain_words():
    job = make_job("r", collections=["fortune500"], posted_at="2026-09-12T10:00:00Z",
                   reality={"repost_count": 3, "mass_posting_count": 1}, **usd(70000, 90000))
    assert rank.reasons(job, CONFIG, NOW) == (
        "remote · $70k-90k (meets your pay) · Fortune 500 · first seen 3d ago · reposted 2x")
    local = make_job("l", work_mode="onsite", cities=["Springfield"], posted_at="2026-09-15T10:00:00Z")
    assert rank.reasons(local, CONFIG, NOW) == "Springfield · pay not listed · first seen today"
    # posted_at restamped on recrawl; freehire's own age wins
    refreshed = make_job("f", posted_at="2026-09-15T10:00:00Z", reality={"age_days": 120, "fake_freshness": True})
    assert rank.reasons(refreshed, CONFIG, NOW) == "remote · pay not listed · first seen 120d ago · old listing"


def test_suspects_flags_category_spread():
    jobs = [make_job(str(i), company_slug="spray", category=c) for i, c in enumerate(["design", "sre", "ml_ai"])]
    jobs.append(make_job("x", company_slug="focused", category="frontend"))
    assert [c for c, _ in rank.suspects(jobs, 3)] == ["spray"]


def test_row_leads_with_job_number_and_carries_real_link_before_slug():
    job = {**make_job("j1", url="https://job-boards.greenhouse.io/acme/jobs/42"), "seen": False, "num": 7}
    fields = rank.row(job, CONFIG, NOW).split()
    assert fields[0] == "#7"
    assert fields[-2:] == ["https://job-boards.greenhouse.io/acme/jobs/42", "j1"]


def test_blocklist_hides_by_type_and_clearance_never_untagged():
    block = {**CONFIG["blocklist"], "employment_types": ["part_time", "contract"], "clearance": True}
    assert rank.blocked(make_job("p", employment_type="part_time"), block)
    assert rank.blocked(make_job("c", requires_clearance=True), block)
    assert not rank.blocked(make_job("u", employment_type=None), block)
    assert not rank.blocked(make_job("c", requires_clearance=True), CONFIG["blocklist"])


def test_max_age_days_hides_older_first_seen_keeps_unknown():
    config = cfg.merge(CONFIG, {"rank": {"max_age_days": 7}})
    jobs = [
        make_job("fresh", reality={"age_days": 7}),
        make_job("old", reality={"age_days": 8}),
        make_job("restamped", posted_at="2026-09-15T11:00:00Z", reality={"age_days": 40}),
        make_job("unknown", posted_at=None),
    ]
    assert sorted(slugs(rank.rank(jobs, config, NOW))) == ["fresh", "unknown"]
    assert len(rank.rank(jobs, CONFIG, NOW)) == 4


def test_rank_hidden_counts_per_rule_with_samples_in_window():
    config = pay_config(relax_under_new_per_week=0)
    config = cfg.merge(config, {"blocklist": {"title_phrases": ["intern"]}})
    jobs = [week_job("ok", 1, **usd(120000, 130000)),
            *[week_job(f"i{n}", 2, title=f"Intern {n}", **usd(120000, 130000)) for n in range(7)],
            week_job("m", 1, category="marketing", **usd(120000, 130000)),
            week_job("low", 3, **usd(50000, 60000)),
            week_job("oldintern", 14, title="Intern old")]
    out = rank.hidden_report(jobs, config, NOW)
    assert out[0] == "settings hid 9 of 10 jobs listed in the last 7 days"
    assert "title phrase hidden: 7" in out
    assert sum(1 for l in out if l.startswith("  Intern")) == 5
    assert "category hidden: 1" in out and "under your pay floor: 1" in out
    assert not any("old" in l for l in out)


def test_rank_hidden_says_nothing_hidden():
    out = rank.hidden_report([week_job("a", 1)], CONFIG, NOW)
    assert out == ["settings hid 0 of 1 jobs listed in the last 7 days - nothing"]


def week_job(slug, days_ago, **over):
    """Reached their list days_ago days before NOW."""
    return make_job(slug, first_fetched_at=f"2026-09-{15 - days_ago:02d}T10:00:00Z", **over)


def pay_config(**pf):
    return cfg.merge(CONFIG, {"rank": {"salary_floor_usd": 100000, "pay_filter": pf}})


# a job under their lowest pay showed on every list (owner: "we shouldn't be showing jobs if below desired pay")
def test_below_floor_hidden_unlisted_kept_by_default():
    jobs = [make_job("meets", **usd(90000, 120000)), make_job("below", **usd(60000, 80000)), make_job("none")]
    config = pay_config(relax_under_new_per_week=0)
    assert slugs(rank.rank(jobs, config, NOW)) == ["meets", "none"]
    assert slugs(rank.rank(jobs, pay_config(hide_unlisted=True, relax_under_new_per_week=0), NOW)) == ["meets"]
    # no floor set: nothing hidden, whatever the switches say
    no_floor = cfg.merge(config, {"rank": {"salary_floor_usd": 0, "pay_filter": {"hide_unlisted": True}}})
    assert len(rank.rank(jobs, no_floor, NOW)) == 3
    # switched off: shown again, below-floor sorted under the ones that meet it
    assert slugs(rank.rank(jobs, pay_config(hide_below_floor=False), NOW)) == ["meets", "below", "none"]


# a thin week left the user with almost nothing to apply to while near-floor jobs sat hidden
def test_thin_week_brings_back_closest_first_marked():
    jobs = [week_job("meets", 1, **usd(110000)),
            week_job("near", 2, **usd(90000, 95000)), week_job("far", 1, **usd(50000)),
            week_job("none-new", 1), week_job("none-old", 5),
            week_job("last-week", 9, **usd(99000))]  # outside the 7 days: stays hidden
    config = pay_config(hide_unlisted=True, relax_under_new_per_week=4)
    shown = rank.rank(jobs, config, NOW)
    assert sorted(slugs(shown)) == ["far", "meets", "near", "none-new"]
    by = {j["public_slug"]: j for j in shown}
    assert "below your pay: $90k-95k (few new jobs this week)" in rank.reasons(by["near"], config, NOW)
    assert "pay not listed (few new jobs this week)" in rank.reasons(by["none-new"], config, NOW)
    assert "few new jobs" not in rank.reasons(by["meets"], config, NOW)
    # enough this week: none brought back
    assert slugs(rank.rank(jobs, pay_config(hide_unlisted=True, relax_under_new_per_week=1), NOW)) == ["meets"]


# a stale (likely filled) job counted as this week's supply and kept the closest ones hidden
def test_relax_counts_only_live_jobs_this_week():
    jobs = [week_job("gone", 1, fetched_at="2026-08-01T00:00:00Z", **usd(120000)),
            week_job("near", 1, **usd(95000))]
    assert "near" in slugs(rank.rank(jobs, pay_config(relax_under_new_per_week=1), NOW))


# setup saved a pay floor without telling the user how many jobs it would hide
def test_pay_probe_counts_before_saving():
    jobs = [week_job("meets", 1, **usd(120000)), week_job("below", 2, **usd(60000)),
            week_job("none", 1), make_job("old-below", **usd(50000))]
    out = rank.pay_probe(jobs, CONFIG, 100000, False, NOW).splitlines()
    assert out[0] == "open: 4 - keeps 2, hides 2 below $100,000 (no pay listed, kept: 1)"
    assert out[1] == "reached your list in the last 7 days: 3 - keeps 2, hides 1 below $100,000 (no pay listed, kept: 1)"
    assert rank.pay_probe(jobs, CONFIG, 100000, True, NOW).startswith(
        "open: 4 - keeps 1, hides 2 below $100,000 + 1 with no pay listed")


def test_posting_says_named_only_when_asked_never_hides_or_sorts():
    school = make_job("school", title="Math Teacher", description="<p>St. Mary <b>Catholic</b> High School seeks ...</p>")
    drone = make_job("drone", title="Designer", description="Anduril is a defense technology company ...")
    plain = make_job("plain", title="Designer", description="We build tools for warehouses.")
    vets = make_job("vets", title="Designer", description="Military veterans encouraged to apply. National security matters.")
    assert all("posting says" not in rank.reasons(j, CONFIG, NOW) for j in (school, drone))
    asked = level_config(posting_says=["faith", "defense"])
    assert "posting says: religious employer" in rank.reasons(school, asked, NOW)
    assert "posting says: defense or military work" in rank.reasons(drone, asked, NOW)
    assert all("posting says" not in rank.reasons(j, asked, NOW) for j in (plain, vets))
    faith_only = level_config(posting_says=["faith"])
    assert "posting says" not in rank.reasons(drone, faith_only, NOW)
    jobs = [school, drone, plain, vets]
    assert slugs(rank.rank(jobs, asked, NOW)) == slugs(rank.rank(jobs, CONFIG, NOW))


# a head of HR at a nonprofit wants to see which employers are nonprofits - the posting's own words or the
# job search's company record; an ask for nonprofit experience or a nonprofit client is no such word
def test_nonprofit_employer_named_from_its_own_words_or_the_record():
    says = make_job("ymca", title="VP, People", description="<p>About us</p><p>The YMCA of Metro Denver is a "
                    "501(c)(3) nonprofit organization serving ...</p>")
    comma = make_job("hospice", title="HR Director", description="As a Benefit of working at Kansas City Hospice and "
                     "Palliative Care, a qualified employer non-profit organization, you may ...")
    ask = make_job("ask", title="HR Director", description="Nonprofit experience preferred. Experience in a nonprofit, "
                   "advocacy or mission-driven organization a plus.")
    client = make_job("client", title="HR Director", description="Whether our clients run a coffee shop, a large "
                      "nonprofit, or a government agency, they depend on us.")
    record = dict(make_job("record", title="Chief People Officer", description="We help kids."), company_nonprofit=1)
    asked = level_config(posting_says=["nonprofit"])
    assert "posting says: nonprofit employer" in rank.reasons(says, asked, NOW)
    assert "posting says: nonprofit employer" in rank.reasons(comma, asked, NOW)
    assert all("nonprofit" not in rank.reasons(j, asked, NOW) for j in (ask, client))
    assert "listed as a nonprofit employer" in rank.reasons(record, asked, NOW)
    assert "nonprofit" not in rank.reasons(record, CONFIG, NOW)
    both = dict(says, company_nonprofit=1)
    assert rank.reasons(both, asked, NOW).count("nonprofit") == 1


# a head of HR saw HR Generalist, Coordinator and Assistant jobs as high as Director ones (1,301 of
# 3,341 HR titles, 2026-10-09): below their level now, never hidden; a title that also leads stays
@pytest.mark.parametrize("title, below", [
    ("Human Resources Generalist", True), ("People Operations Coordinator", True),
    ("Talent Acquisition Specialist I", True), ("Executive Assistant to the Chief Human Resources Officer (CHRO)", True),
    ("Chief Executive Assistant", True), ("HR Business Partner", False), ("Assistant Director of Human Resources", False),
    ("Associate Director, Human Resources Business Partner", False), ("Founding Senior HR Generalist / People Operations Lead", False),
    ("Vice President, Human Resources", False), ("Chief People Officer", False), ("Director of Human Resources", False)])
def test_leader_sorts_support_and_individual_titles_lower(title, below):
    job = make_job("j", title=title)
    assert ("title below your level" in rank.mismatches(job, {"career_level": "leader"})) is below
    assert "title below your level" not in rank.mismatches(job, {"career_level": "senior"}) or "Intern" in title \
        or rank.first_rung(title)


def test_posting_says_kinds_match_the_defaults_comment():
    assert set(rank.POSTING_SAYS) == {"faith", "defense", "nonprofit"}
    assert cfg.defaults()["rank"]["posting_says"] == []


# --- students (plan-students) ---------------------------------------------------------------

def req(*lines):
    return {"requirements": [{"text": t, "priority": "required"} for t in lines]}


def test_internship_tagged_full_time_is_kept_and_not_demoted_for_an_internship_search():
    # 87 of 300 real internships carry the full_time tag (summer hours), 2026-10-07
    config = cfg.merge(CONFIG, {"blocklist": {"employment_types": ["full_time", "part_time", "contract"]},
                                "rank": {"employment_types": ["internship"]}})
    jobs = [make_job("summer", title="Data Analyst Intern (Summer 2027)", employment_type="full_time"),
            make_job("coop", title="Engineering Co-op", employment_type="full_time"),
            make_job("job", title="Data Analyst", employment_type="full_time")]
    ranked = rank.rank(jobs, config, NOW)
    assert slugs(ranked) == ["summer", "coop"]
    assert all("you asked" not in rank.reasons(j, config, NOW) for j in ranked)


def test_internships_only_sorts_lower_an_ordinary_job_tagged_intern():
    # 117 of 442 intern-tagged business rows were ordinary jobs, 2026-10-08
    config = cfg.merge(CONFIG, {"rank": {"career_level": "entry", "employment_types": ["internship"]}})
    jobs = [make_job("fa", title="Financial Analyst", seniority="intern", employment_type=None, category="finance"),
            make_job("int", title="Payroll Intern", seniority="intern", employment_type="internship", category="finance"),
            make_job("prog", title="2027 Summer Analyst Program - Sales", seniority="intern", employment_type=None,
                     category="finance"),
            make_job("rot", title="Finance & Accounting Rotational Program - May 2027 Grads", category="finance",
                     employment_type="internship"),
            make_job("fel", title="Integrated Marketing Fellowship (Spring 2027)", employment_type="internship",
                     category="finance")]
    ranked = rank.rank(jobs, config, NOW)
    assert slugs(ranked)[-1] == "fa" and len(ranked) == 5
    assert "title doesn't say internship" in rank.reasons(ranked[-1], config, NOW)
    assert all(rank.mismatches(j, config["rank"]) == [] for j in ranked[:-1])
    # full-time jobs wanted too: an analyst title is what they asked for
    both = cfg.merge(config, {"rank": {"employment_types": ["internship", "full_time"]}})
    assert rank.mismatches(jobs[0], both["rank"]) == []


def test_title_never_hides_a_job_its_tag_keeps():
    config = cfg.merge(CONFIG, {"blocklist": {"employment_types": ["internship"]}})
    jobs = [make_job("pm", title="Intern Program Manager", employment_type="full_time"),
            make_job("intern", title="Audit Intern", employment_type="internship")]
    assert slugs(rank.rank(jobs, config, NOW)) == ["pm"]


def test_mid_level_user_gets_one_doubt_for_an_intern_title_not_two():
    config = cfg.merge(CONFIG, {"rank": {"career_level": "mid", "employment_types": ["full_time"]}})
    assert rank.mismatches(make_job("i", title="Finance Interns", employment_type="internship"),
                           config["rank"]) == ["title below your level"]


def test_entry_level_sorts_a_3_plus_years_ask_lower_never_hides_it():
    config = cfg.merge(CONFIG, {"rank": {"career_level": "entry"}})
    jobs = [make_job("asks", enrichment=req("5+ years of experience in financial analysis"), **usd(120000)),
            make_job("fits", enrichment=req("0-2 years of experience; new graduates welcome"), **usd(60000)),
            make_job("lead", title="Shift Lead", enrichment=req("Customer service skills"), **usd(65000))]
    ranked = rank.rank(jobs, config, NOW)
    assert slugs(ranked) == ["lead", "fits", "asks"]
    assert "asks 5+ years" in rank.reasons(ranked[2], config, NOW)
    mid = cfg.merge(CONFIG, {"rank": {"career_level": "mid"}})
    assert slugs(rank.rank(jobs[:2], mid, NOW))[0] == "asks"


def test_graduation_window_their_date_misses_sorts_lower_and_says_both(monkeypatch):
    monkeypatch.setattr(rank, "student_graduation", lambda config, today: "2027-05")
    jobs = [make_job("later", enrichment=req("Graduating between December 2027 and June 2028"), **usd(90000)),
            make_job("fits", enrichment=req("Graduating May/June 2027"), **usd(60000))]
    ranked = rank.rank(jobs, CONFIG, NOW)
    assert slugs(ranked) == ["fits", "later"]
    assert "asks graduating Dec 2027 - Jun 2028; yours May 2027" in rank.reasons(ranked[1], CONFIG, NOW)


# "Recent college graduate" is never counted by the resume match (best.NOT_ON_RESUME); the window beside it still is
def test_graduation_window_read_beside_an_age_coded_ask(monkeypatch):
    monkeypatch.setattr(rank, "student_graduation", lambda config, today: "2027-05")
    jobs = [make_job("later", enrichment=req("Recent college graduate", "Graduating between December 2027 and June 2028"),
                     **usd(90000)),
            make_job("fits", enrichment=req("Recent college graduate", "Graduating May/June 2027"), **usd(60000))]
    ranked = rank.rank(jobs, CONFIG, NOW)
    assert slugs(ranked) == ["fits", "later"]
    assert "asks graduating Dec 2027 - Jun 2028; yours May 2027" in rank.reasons(ranked[1], CONFIG, NOW)


def test_graduation_read_only_while_studying_or_just_after(tmp_path, monkeypatch):
    import yaml
    from datetime import date
    path = tmp_path / "Resume details.yml"
    config = cfg.merge(CONFIG, {"resume": {"master": str(path)}})
    monkeypatch.setattr(cfg, "resume_path", lambda c, key: path)
    base = {"contact": {"name": "A B", "email": "a@b.co", "location": "Columbus, OH"}, "roles": []}
    today = date(2026, 10, 7)
    for school, want in (({"end": "2027-05"}, "2027-05"), ({"end": "2025-12"}, "2025-12"),
                         ({"end": "2019-05"}, None), ({"end": "2027-05", "hide_year": True}, None)):
        path.write_text(yaml.safe_dump({**base, "education": [{"institution": "State U", "degree": "BS", **school}]}))
        assert rank.student_graduation(config, today) == want, school


def test_hourly_floor_reads_and_says_its_own_unit():
    assert rank.parse_floor("22/hr") == (45760, "hour")
    assert rank.parse_floor("$17 an hour") == (35360, "hour")
    assert rank.parse_floor("60000") == (60000, "year")
    rc = cfg.merge(CONFIG, {"rank": {"salary_floor_usd": 35360, "salary_floor_unit": "hour"}})["rank"]
    assert rank.floor_words(rc) == "$17/hr"
    # a part-time job listing a yearly sum (hours unknown) is never read as under an hourly floor
    yearly = make_job("pt", title="Part-time Library Assistant", **usd(25000))
    assert rank.pay_hidden(yearly, rc) is None
    assert rank.pay_hidden(make_job("hr", title="Barista", **usd(15, 16, "hour")), rc) == "below"
    assert rank.pay_words(yearly, rc) == "$25k"


def test_two_passes_may_fill_one_tier():
    config = {"passes": [{"tier": "remote"}, {"tier": "remote"}, {"tier": "local"}]}
    assert cfg.tier_order(config) == ["remote", "local"]


# the job search's cities match by name alone: "Washington" brought Seattle into a DC search,
# Arlington TX into Arlington VA (29 of 78 rows, 2026-10-08)
def test_city_tier_drops_rows_naming_only_other_states():
    config = cfg.merge(CONFIG, {"passes": [{"tier": "school", "label": "DC area", "states": ["DC", "MD", "VA"],
                                            "params": {"cities": ["Washington", "Arlington"]}}]})
    place = lambda slug, loc, **kw: make_job(slug, tier="school", location=loc, work_mode=None, **kw)
    jobs = [place("dc", "Washington, District of Columbia, United States"), place("dc2", "Washington DC Office - WASHINGTON, DC 20024"),
            place("va", "Arlington, Virginia"), place("md", "Bethesda, MD"), place("multi", "Chicago; Dallas; Washington, D.C."),
            place("unsure", "Washington, United States"), place("bare", "Wayne"),
            place("sea", "Seattle, Washington, United States"), place("redmond", "United States, Washington, Redmond"),
            place("tx", "Arlington, TX, US"), place("wv", "Charleston, West Virginia"),
            place("au", "Alexandria, New South Wales", countries=["au"]),
            place("remote", "Seattle, Washington")]
    jobs[-1]["work_mode"] = "remote"
    kept = {j["public_slug"] for j in jobs if not rank.far(j, config)}
    assert kept == {"dc", "dc2", "va", "md", "multi", "unsure", "bare", "remote"}
    # a tier with no states is never read this way
    assert not rank.far(dict(jobs[7], tier="remote"), config)


def test_a_required_licence_their_resume_never_names_sorts_lower_and_says_which(monkeypatch):
    have = knockout.credential_text({"certifications": [{"name": "Certified Anti-Money Laundering Specialist (CAMS)"}]})
    monkeypatch.setattr(rank, "resume_credentials", lambda config: have)
    jobs = [make_job("principal", enrichment=req("FINRA Series 7 and Series 24 licenses (required)"), **usd(150000)),
            make_job("aml", enrichment=req("Active CAMS certification"), **usd(90000)),
            make_job("any", enrichment=req("CAMS, CFE, or CRCM certification"), **usd(80000))]
    ranked = rank.rank(jobs, CONFIG, NOW)
    assert slugs(ranked) == ["aml", "any", "principal"]
    assert "asks Series 7 and Series 24, not in your resume" in rank.reasons(ranked[2], CONFIG, NOW)
    # on the page as lapsed: sorted lower all the same, said as it stands
    lapsed = knockout.credential_text({"certifications": [{"name": "Series 7 (passed 2019; not currently registered)"},
                                                          {"name": "Series 24 (lapsed)"}]})
    monkeypatch.setattr(rank, "resume_credentials", lambda config: lapsed)
    assert "asks Series 7 and Series 24, not current on your resume" in rank.reasons(next(j for j in rank.rank(jobs, CONFIG, NOW) if j["public_slug"] == "principal"), CONFIG, NOW)
    # no resume details yet: nothing to compare, nothing said
    monkeypatch.setattr(rank, "resume_credentials", lambda config: None)
    assert slugs(rank.rank(jobs, CONFIG, NOW))[0] == "principal"


# 63 freelance / temporary titles on 3,000 newest rows of 6 fields: tagged contract 38, part time 15,
# full time 5, internship 4 (2026-10-09) - the title says what the job is
def test_freelance_or_temporary_title_reads_as_contract():
    full_time_only = cfg.merge(CONFIG, {"rank": {"employment_types": ["full_time"]}})
    gig = make_job("gig", title="YouTube Editor - Freelance", employment_type="full_time")
    temp = make_job("temp", title="Assistant Video Editor, Temporary", employment_type="full_time")
    staff = make_job("staff", title="Video Editor", employment_type="full_time")
    assert rank.job_type(gig) == rank.job_type(temp) == "contract"
    assert rank.mismatches(gig, full_time_only["rank"]) == ["contract, you asked full time"]
    assert rank.mismatches(staff, full_time_only["rank"]) == []
    assert rank.title_type(make_job("t", title="Temperature Controls Technician")) is None
    # contract work wanted: a freelance gig the job search tagged part time is kept
    contract_only = cfg.merge(CONFIG, {"blocklist": {"employment_types": ["part_time", "full_time"]}})
    part = make_job("part", title="Freelance Video Editor", employment_type="part_time")
    assert slugs(rank.rank([part], contract_only, NOW)) == ["part"]


# a numbered first rung ("Information Security Analyst I", "Tier 1 SOC Analyst"): 85 of 5,248 US security
# rows, 2026-10-09 - below a senior or leader list, never a DoD cert level or a title that also says senior
@pytest.mark.parametrize("title, below", [
    ("Information Security Analyst I", True), ("Tier 1 SOC Analyst", True), ("Help Desk Level 1", True),
    ("Cybersecurity Engineer I", True), ("Sr. Cybersecurity Engineer I (6861)", False), ("Security Analyst II", False),
    ("Cyber Analyst - IAT Level I", False), ("Phase I Program Analyst", False), ("Chief Information Security Officer", False)])
def test_first_rung_titles_below_senior(title, below):
    job = make_job("j", title=title)
    assert ("title below your level" in rank.mismatches(job, {"career_level": "senior"})) is below
    assert "title below your level" not in rank.mismatches(job, {"career_level": "mid"})


# "senior jobs are hard to get ... software engineer 1, 2, 3 preferred" (owner 2026-10-26): a mid-level list was
# topped by Senior titles. Level words that name no level stay put
@pytest.mark.parametrize("title, above", [
    ("Senior Software Engineer", True), ("Sr. Frontend Engineer", True), ("Lead Software Engineer", True),
    ("Staff Engineer", True), ("Principal Engineer", True), ("Director of Engineering", True),
    ("Software Engineer II", False), ("Software Engineer III", False), ("Software Engineer I", False),
    ("Frontend Engineer", False), ("Member of Technical Staff", False), ("Staff Accountant", False),
    ("Senior Living Coordinator", False), ("Shift Lead", False), ("Lead Generation Specialist", False)])
def test_mid_level_sorts_senior_titles_lower(title, above):
    assert ("title above your level" in rank.mismatches(make_job("j", title=title), {"career_level": "mid"})) is above


def reqs(*lines):
    return {"requirements": [{"text": t, "priority": "required"} for t in lines]}


# the job search's clearance flag is yes / no: a Secret holder's list read the same as a TS/SCI one's
def test_an_active_clearance_above_theirs_is_said_and_sorted_lower():
    config = {**CONFIG, "rank": {**CONFIG["rank"]}, "work_authorization": {"can_hold_clearance": True}}
    job = make_job("ts", requires_clearance=True, enrichment=reqs("Active TS/SCI clearance with CI polygraph"))
    assert rank.asks_beyond(job, config, None, NOW.date(), "Security Clearance\nActive Secret") == \
        ["asks an active TS/SCI clearance with a polygraph, your resume shows a Secret clearance"]
    assert rank.asks_beyond(job, config, None, NOW.date(), "Active TS/SCI with CI polygraph") == []
    getting = make_job("get", enrichment=reqs("Ability to obtain a Secret clearance post start"))
    assert rank.asks_beyond(getting, config, None, NOW.date(), "") == []
    # one who can't hold any: the clearance demerit already says it, once
    cannot = {**config, "work_authorization": {"can_hold_clearance": False}}
    assert rank.asks_beyond(job, cannot, None, NOW.date(), "") == []


# "Active CPA license required" / "Must hold CPA certification" / "CPA required" were 3 entries, -0.45 and
# said three times (2026-10-10): one verdict told several ways counts once
def test_a_missing_credential_counts_once_per_posting():
    cpa = make_job("cpa", enrichment=reqs("Active CPA license required", "Must hold CPA certification", "CPA required"))
    assert rank.asks_beyond(cpa, CONFIG, None, NOW.date(), "") == ["asks CPA, not in your resume"]
    series = make_job("series", enrichment=reqs("Series 7 and Series 63 required", "Series 7 required"))
    assert rank.asks_beyond(series, CONFIG, None, NOW.date(), "") == ["asks Series 7 and Series 63, not in your resume"]
    # two different credentials stay two; one held drops out of the other line
    both = make_job("both", enrichment=reqs("CPA required", "Series 7 required"))
    assert len(rank.asks_beyond(both, CONFIG, None, NOW.date(), "")) == 2
    assert rank.asks_beyond(series, CONFIG, None, NOW.date(), "Series 7") == ["asks Series 63, not in your resume"]
    # an either/or line getting the other ask's credential answers drops; one it doesn't stays
    menu = make_job("menu", enrichment=reqs("CISSP required", "CISSP, CISA, or CISM certification"))
    assert rank.asks_beyond(menu, CONFIG, None, NOW.date(), "") == ["asks CISSP, not in your resume"]


def test_a_required_clearance_line_names_it_when_the_flag_is_missing():
    assert rank.clearance(make_job("a", enrichment=reqs("Active Secret clearance required"))) == ["needs a security clearance"]
    assert rank.clearance(make_job("b", enrichment=reqs("Some assignments may require a Secret clearance"))) == []
    assert rank.clearance(make_job("c", enrichment=reqs("Customs clearance experience required"))) == []


def _asking(slug, *lines, skills=()):
    return make_job(slug, skills=list(skills),
                    enrichment={"requirements": [{"priority": "required", "text": t} for t in lines]})


@pytest.mark.parametrize("lines, skills, reason", [
    (["5+ years building web applications with Java and Spring Boot"], (), ["asks Java"]),
    (["Strong background in Java-based web development"], (), ["asks Java"]),
    # JavaScript is never Java, however it's written
    (["Strong JavaScript, TypeScript and React"], ("javascript",), []),
    (["Expert in Java Script and HTML"], (), []),
    # one choice of several, or a wish: not asked
    (["Server-side languages such as Python, Node.js, or Java"], ("java",), []),
    (["Proficient in React; Java a plus"], (), []),
    # requirements listed, none naming it: the tag alone (a nice-to-have somewhere) doesn't count
    (["5+ years of React"], ("java", "react"), []),
    # no requirements listed: the job search's tags
    ([], ("java", "react"), ["lists Java"]),
])
def test_avoided_skill_sorts_lower_with_reason(lines, skills, reason):
    assert rank.avoided(_asking("a", *lines, skills=skills), ["Java"]) == reason


def test_short_skill_read_off_tags_only():
    job = _asking("a", "Go to market with the product team", skills=("react",))
    assert rank.avoided(job, ["Go"]) == []
    assert rank.avoided(dict(job, skills=["go"]), ["Go"]) == ["lists Go"]


def test_avoided_skill_ranks_below_and_says_why():
    config = cfg.load(cfg.PROFILES / "frontend.yml")
    config["rank"]["avoid_skills"] = ["Java"]
    java = _asking("java", "Strong Java and Spring Boot")
    java.update(salary_min=300000, salary_currency="USD", salary_period="year")
    ranked = rank.rank([java, _asking("react", "Strong React")], config)
    assert [j["public_slug"] for j in ranked] == ["react", "java"]
    assert "asks Java" in rank.reasons(ranked[1], config)


def gap_facts(**over):
    return {"stems": set(), "titles": set(), "years": 10, "credentials": knockout.credential_text({}),
            "portfolio": False, "degree": 2, "languages": set(), **over}


def test_rank_gaps_counts_each_ask_once_per_job_grouped_by_kind():
    facts = gap_facts()
    jobs = [make_job("a", enrichment=req("FINRA Series 7 license (required)", "Series 7 required")),
            make_job("b", enrichment=req("Series 7 required")),
            make_job("c", enrichment=req("Must be a U.S. citizen"))]
    assert len([g for g in rank.job_gaps(jobs[0], facts) if g[0] == "credential"]) == 1
    assert rank.job_gaps(jobs[2], facts) == set()
    lines = rank.gaps_report(jobs, [jobs[1]], facts, 10)
    assert lines[0] == "Licences and certifications:"
    assert "  Series 7 - 2 of 3 open jobs ask it; not on your resume." in lines
    assert any(l.startswith("Jobs you chose not to send (1)") for l in lines)
    assert any("small numbers" in l for l in lines)


def test_rank_gaps_years_once_per_job_and_language():
    facts = gap_facts(years=2)
    job = make_job("a", enrichment=req("5+ years of experience", "7+ years of experience", "Fluent in Spanish"))
    found = rank.job_gaps(job, facts)
    assert [w for k, w in found if k == "years"] == ["7+ years"]
    assert ("language", "Spanish") in found


def test_rank_gaps_years_tool():
    job = make_job("a", enrichment=req("5+ years of OneTrust"))
    found = rank.job_gaps(job, gap_facts(years=10))
    assert ("tool", "Onetrust") in {(k, w.title()) for k, w in found}
    assert not [g for g in found if g[0] == "years"]
    short = rank.job_gaps(job, gap_facts(years=2))
    assert ("years", "5+ years") in short


OTHER_LINES = ["Ran month-end close and account reconciliations in NetSuite", "Built payroll audits in Excel"]


def other_facts(**over):
    import best
    return gap_facts(stems=best.stems(" ".join(OTHER_LINES)), titles=best.stems("Accountant"), lines=OTHER_LINES, **over)


def test_rank_other_titles_carry_backing_line_and_local_count():
    facts = other_facts()
    jobs = [make_job(s, title="Reconciliation Specialist", enrichment=req("Account reconciliations in NetSuite"))
            for s in "ab"]
    found = rank.other_titles(jobs, CONFIG, facts)
    assert [(g["title"], g["count"], g["backing"]) for g in found] == \
        [("Reconciliation Specialist", 2, OTHER_LINES[0])]
    assert "2 open jobs" in "\n".join(rank.other_titles_report(jobs, CONFIG, facts))


def test_rank_other_titles_skip_a_level_or_licence_reach():
    facts = other_facts()
    ask = req("Account reconciliations in NetSuite")
    ok = make_job("a", title="Reconciliation Specialist", enrichment=ask, seniority="junior")
    licence = make_job("b", title="Reconciliation Specialist", seniority="junior",
                       enrichment=req("Account reconciliations", "Series 7 required"))
    config = cfg.merge(CONFIG, {"rank": {"career_level": "entry"}})
    above = make_job("c", title="Reconciliation Specialist", enrichment=ask, seniority="director")
    assert [g["count"] for g in rank.other_titles([ok, licence, above], config, facts)] == [1]


def test_job_board_link_past_its_life_sorts_with_stale_rows():
    """WhatJobs links open its home page about a week after first seen while the job search still
    lists the job (rank.link_days)."""
    jobs = [
        make_job("dead", source="whatjobs", first_fetched_at="2026-09-05T00:00:00Z",
                 fetched_at="2026-09-14T00:00:00Z", **usd(200000)),
        make_job("fresh", source="whatjobs", first_fetched_at="2026-09-12T00:00:00Z",
                 fetched_at="2026-09-14T00:00:00Z", **usd(150000)),
        make_job("other-board", first_fetched_at="2026-09-01T00:00:00Z", fetched_at="2026-09-14T00:00:00Z"),
        make_job("dead-edition", source="whatjobs-ca", first_fetched_at="2026-09-05T00:00:00Z",
                 fetched_at="2026-09-14T00:00:00Z"),
    ]
    ranked = rank.rank(jobs, CONFIG, NOW)
    assert slugs(ranked) == ["fresh", "other-board", "dead", "dead-edition"]
    assert rank.reasons(ranked[2], CONFIG, NOW).endswith("link likely dead - seen 10d ago, this job board's links stop within a week")


def test_hidden_board_hides_its_country_editions():
    jobs = [make_job("us", source="whatjobs"), make_job("ca", source="whatjobs-ca"),
            make_job("near-name", source="whatjobsplus"), make_job("other")]
    hide = cfg.merge(CONFIG, {"blocklist": {"sources": ["WhatJobs"]}})
    assert slugs(rank.rank(jobs, hide, NOW)) == ["near-name", "other"]


def test_age_counts_on_from_the_fetch_that_stored_it():
    """age_days is the job search's as of that fetch; 12 days later it read "first seen 1d ago"."""
    job = make_job("j", reality={"age_days": 1}, fetched_at="2026-09-03T12:00:00Z")
    assert rank.age(job, NOW) == 13
    assert rank.age(make_job("unfetched", reality={"age_days": 1}), NOW) == 1
