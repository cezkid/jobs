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
    assert slugs(rank.rank(jobs, CONFIG, NOW)) == [
        "priced-high", "priced-low", "f500-low", "f500", "plain-new", "plain-old", "ghost", "local-top",
    ]


def test_stale_row_excluded_fresh_kept():
    jobs = [make_job("gone", fetched_at="2026-08-30T00:00:00Z"), make_job("live", fetched_at="2026-09-14T00:00:00Z")]
    assert slugs(rank.rank(jobs, CONFIG, NOW)) == ["live"]


def test_reposted_old_or_evergreen_rows_sort_below_fresh():
    jobs = [
        make_job("reposted", reality={"repost_count": 4}, posted_at="2026-09-15T11:00:00Z"),
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


def test_title_phrase_matches_whole_words_only():
    config = cfg.merge(CONFIG, {"blocklist": {"title_phrases": ["intern"]}})
    jobs = [make_job("aud", title="Internal Auditor"), make_job("tax", title="Tax Intern (Summer)")]
    assert slugs(rank.rank(jobs, config, NOW)) == ["aud"]
    assert slugs(rank.would_hide(jobs, "intern", CONFIG["blocklist"])) == ["tax"]


def test_company_blocklist_matches_name_as_well_as_slug():
    config = cfg.merge(CONFIG, {"blocklist": {"companies": ["Staffing Pros"]}})
    jobs = [make_job("a", company="Staffing Pros LLC", company_slug="staffingpros-2"), make_job("b")]
    assert slugs(rank.rank(jobs, config, NOW)) == ["b"]


def test_reasons_say_why_in_plain_words():
    job = make_job("r", collections=["fortune500"], posted_at="2026-09-12T10:00:00Z",
                   reality={"repost_count": 2}, **usd(70000, 90000))
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
