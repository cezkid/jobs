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


def test_rank_order_tier_collections_salary_has_salary_recency():
    jobs = [
        make_job("local-top", tier="local", collections=["bigtech"], salary_min=300000, salary_currency="USD"),
        make_job("plain-new", posted_at="2026-09-15T11:00:00Z"),
        make_job("plain-old", posted_at="2026-09-10T11:00:00Z"),
        make_job("priced-low", salary_min=40000, salary_currency="USD", salary_period="year"),
        make_job("priced-high", salary_min=140000, salary_currency="USD", salary_period="year"),
        make_job("yc", collections=["yc", "us-h1b-sponsor"]),
        make_job("h1b-only", collections=["us-h1b-sponsor"], posted_at="2026-09-01T00:00:00Z"),
    ]
    assert slugs(rank.rank(jobs, CONFIG)) == [
        "yc", "priced-high", "priced-low", "plain-new", "plain-old", "h1b-only", "local-top",
    ]


def test_annual_usd_min_annualizes_and_ignores_other_currency():
    assert rank.annual_usd_min(make_job("h", salary_min=70, salary_currency="USD", salary_period="hour")) == 145600
    assert rank.annual_usd_min(make_job("n", salary_min=150000, salary_currency="USD")) == 150000
    assert rank.annual_usd_min(make_job("c", salary_min=200000, salary_currency="CAD")) is None


def test_suspects_flags_category_spread():
    jobs = [make_job(str(i), company_slug="spray", category=c) for i, c in enumerate(["design", "sre", "ml_ai"])]
    jobs.append(make_job("x", company_slug="focused", category="frontend"))
    assert [c for c, _ in rank.suspects(jobs, 3)] == ["spray"]
