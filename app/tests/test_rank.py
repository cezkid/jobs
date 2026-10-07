from datetime import datetime, timezone

import cfg
import rank
from conftest import make_job

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


def test_posting_says_kinds_match_the_defaults_comment():
    assert set(rank.POSTING_SAYS) == {"faith", "defense"}
    assert cfg.defaults()["rank"]["posting_says"] == []
