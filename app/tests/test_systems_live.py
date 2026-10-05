"""Every system's links still look the way it expects: the newest US postings freehire lists for
each of its SOURCES, matched live. A system whose questions() is a plain HTTP read
(QUESTIONS_OVER_HTTP) reads one open posting's form, contact boxes found. Hits freehire.me + the
system's own job board (a read; only the listing id goes out)."""
from urllib.parse import urlsplit

import httpx
import pytest

from apply import systems

SEARCH = "https://freehire.me/api/v1/jobs/search"
CONTACT = {"email", "name", "first_name", "resume"}


def newest(source: str) -> list[str]:
    # 50, not 10: one employer posting a batch can fill the newest 10 alone, all on its own careers
    # domain (17 Roku links on www.weareroku.com in a row on Greenhouse, 2026-10-03)
    r = httpx.get(SEARCH, params={"countries": "us", "source": source, "limit": 50, "sort": "posted_at",
                                  "order": "desc"}, timeout=30)
    r.raise_for_status()
    return [row["url"] for row in r.json()["data"]]


@pytest.mark.parametrize("system", systems.SYSTEMS, ids=lambda s: s.__name__.rsplit(".", 1)[-1])
def test_newest_postings_match_and_forms_read(system):
    for source in system.SOURCES:
        links = newest(source)
        hits = [u for u in links if system.matches(u)]
        print(f"coverage {system.NAME} / {source}: {len(hits)} of {len(links)} newest US links match")
        assert hits, f"no {source} link matches {system.NAME}: {links[:3]}"
        if not getattr(system, "QUESTIONS_OVER_HTTP", False):
            continue
        for link in hits:
            try:
                got = system.questions(link)
            except ValueError:  # closed since freehire last looked
                continue
            assert CONTACT & {q["key"] for q in got}, f"no contact box read off {system.NAME} form"
            break
        else:
            pytest.fail(f"every {source} posting tried was closed")


# employer's own careers page w/ the form embedded (?gh_jid=): 10-17 of the newest 50 Greenhouse links
# (2026-10) - board looked up, the form read like any other
def test_greenhouse_employer_site_links_read():
    from apply.systems import greenhouse
    # greenhouse.io links carry gh_jid too - only the employer's own host counts
    links = [u for u in newest("greenhouse") if greenhouse.EMPLOYER_URL.match(u)
             and not (urlsplit(u).hostname or "").endswith("greenhouse.io")]
    print(f"coverage Greenhouse employer-site links: {len(links)} of 50 newest US links")
    if not links:
        pytest.skip("no employer-site link among the newest 50 today")
    for link in links:
        try:
            got = greenhouse.questions(link)
        except ValueError:  # closed since freehire last looked
            continue
        assert CONTACT & {q["key"] for q in got}, "no contact box read off an employer-site Greenhouse form"
        return
    pytest.fail("every employer-site Greenhouse posting tried was closed")
