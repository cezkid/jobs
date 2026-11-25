"""Every system's links still look the way it expects: the newest US postings freehire lists for
each of its SOURCES, matched live. A system whose questions() is a plain HTTP read
(QUESTIONS_OVER_HTTP) reads one open posting's form, contact boxes found. Hits freehire.me + the
system's own job board (a read; only the listing id goes out)."""
import threading
from urllib.parse import urlsplit

import httpx
import pytest

from apply import systems
from ingest import freehire

pytestmark = pytest.mark.live  # reaches the job search API and job sites

BASE = "https://freehire.me/api/v1"
SEARCH = f"{BASE}/jobs/search"
CONTACT = {"email", "name", "first_name", "resume"}


def newest(source: str):
    """The newest US postings' own links, one at a time. 50 rows, not 10: one employer posting a batch can
    fill the newest 10 alone, all on its own careers domain (17 Roku links on www.weareroku.com in a row
    on Greenhouse, 2026-10-03). The job search sends `url` blank since 2026-11-23: each link is asked of
    its pass-through link as the job check does (freehire.own_link, header-only), only as far down the
    list as the test reads - the allowance is 600 asks a minute for the whole run."""
    r = httpx.get(SEARCH, params={"countries": "us", "source": source, "limit": 50, "sort": "posted_at",
                                  "order": "desc"}, timeout=30)
    r.raise_for_status()
    limited = threading.Event()
    with httpx.Client(timeout=30) as client:
        for row in r.json()["data"]:
            if link := row.get("url") or freehire.own_link(client, BASE, row["public_slug"], limited):
                yield link


@pytest.mark.parametrize("system", systems.SYSTEMS, ids=lambda s: s.__name__.rsplit(".", 1)[-1])
def test_newest_postings_match_and_forms_read(system):
    for source in system.SOURCES:
        seen = hits = 0
        for link in newest(source):
            seen += 1
            if not system.matches(link):
                continue
            hits += 1
            if not getattr(system, "QUESTIONS_OVER_HTTP", False):
                break
            try:
                got = system.questions(link)
            except ValueError:  # closed since freehire last looked
                continue
            assert CONTACT & {q["key"] for q in got}, f"no contact box read off {system.NAME} form"
            break
        else:
            assert hits, f"none of the {seen} newest {source} links matches {system.NAME}"
            pytest.fail(f"every {source} posting tried was closed")
        print(f"coverage {system.NAME} / {source}: first match at link {seen} of the newest US links")


# employer's own careers page w/ the form embedded (?gh_jid=): 10-17 of the newest 50 Greenhouse links
# (2026-10) - board looked up, the form read like any other
def test_greenhouse_employer_site_links_read():
    from apply.systems import greenhouse
    seen = 0
    for link in newest("greenhouse"):
        # greenhouse.io links carry gh_jid too - only the employer's own host counts
        if not greenhouse.EMPLOYER_URL.match(link) or (urlsplit(link).hostname or "").endswith("greenhouse.io"):
            continue
        seen += 1
        try:
            got = greenhouse.questions(link)
        except ValueError:  # closed since freehire last looked
            continue
        assert CONTACT & {q["key"] for q in got}, "no contact box read off an employer-site Greenhouse form"
        return
    if not seen:
        pytest.skip("no employer-site link among the newest 50 today")
    pytest.fail("every employer-site Greenhouse posting tried was closed")
