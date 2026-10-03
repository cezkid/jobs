"""Every system's links still look the way it expects: the newest US postings freehire lists for
each of its SOURCES, matched live. A system whose questions() is a plain HTTP read
(QUESTIONS_OVER_HTTP) reads one open posting's form, contact boxes found. Hits freehire.me + the
system's own job board (a read; only the listing id goes out)."""
import httpx
import pytest

from apply import systems

SEARCH = "https://freehire.me/api/v1/jobs/search"
CONTACT = {"email", "name", "first_name", "resume"}


def newest(source: str) -> list[str]:
    r = httpx.get(SEARCH, params={"countries": "us", "source": source, "limit": 10, "sort": "posted_at",
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
