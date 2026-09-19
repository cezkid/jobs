import pytest

import store


def make_job(slug: str, **over) -> dict:
    job = {c: None for c in store.COLS}
    job.update(
        public_slug=slug,
        tier="remote",
        title=f"Senior Vue Engineer {slug}",
        company="Acme",
        company_slug="acme",
        url=f"https://boards.greenhouse.io/acme/jobs/{slug}",
        source="greenhouse",
        work_mode="remote",
        countries=["us"],
        cities=[],
        skills=["vue"],
        collections=[],
        employment_type="full_time",
        seniority="senior",
        category="frontend",
        posted_at="2026-09-15T10:00:00Z",
        enrichment={},
        reality={},
    )
    job.update(over)
    return job


@pytest.fixture
def conn():
    c = store.connect(":memory:")
    yield c
    c.close()
