"""A job board that copies postings from employers' careers pages (EchoJobs: freehire `source` echojobs) -
the job list's link is that board's page, not the form, and the board shows the employer's Apply link only
to its own signed-in users ("Sign in to apply", measured 2026-10-22). The job search usually lists the
same posting from the employer's own system too: found by the original title + the posting's text, its
link is where the form is.

Measured 2026-10-22 on 180 US EchoJobs rows: every description opens with the employer's own title as
<h1> (180 of 180). Searching the job search for that title, then keeping rows of another source whose
text starts the same (word overlap >= 0.6 of the first 150 words): 96 one copy, 23 several (other
boards copying the same posting - Workday + a board, two Workday copies of one job in two cities),
61 none (the title alone matched other employers' jobs, overlap 0.0-0.35). Of the 96: Workday 53,
Greenhouse 17, Ashby 14, Lever 3, Rippling 3, others 1 each. The board's company name can carry a
slogan ("<Brand>: <tagline>") that never matches the employer's own slug, so the company is not used.

Built In (freehire `source` builtin, `builtin.com/job/...`): the row keeps the employer's own title, the
description has no <h1> - same search by the row's title, the whole description as the text. Measured
2026-10-29 on 41 US Built In rows: 19 resolved to a system here (Workday 8, Ashby 2, Gem 2,
SmartRecruiters 2, Greenhouse, Zoho Recruit, JazzHR, Workable, Oracle 1 each), the rest none (best
overlap 0.0-0.52, or a system not here: Dayforce). One with none ran Apply on Built In itself (`isApplyFormEnabled` in its page): a
Built In account's form, filled by the user.
"""
import html
import re

import httpx

from apply import systems

LINK = re.compile(r"https?://(?:www\.)?(?:echojobs\.io|builtin\.com)/job/", re.I)
SOURCES = ("echojobs", "builtin")
TITLED = ("builtin",)  # boards whose row title is the employer's own (no <h1> in the description)
TITLE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
TAG = re.compile(r"<[^>]+>")
SAME = 0.6
WORDS = 150


def matches(url: str) -> bool:
    return bool(LINK.match(url.strip()))


def words(text: str | None) -> set[str]:
    plain = html.unescape(TAG.sub(" ", text or "")).casefold()
    return set(re.findall(r"[a-z0-9]+", plain)[:WORDS])


def overlap(a: str | None, b: str | None) -> float:
    wa, wb = words(a), words(b)
    return len(wa & wb) / max(1, min(len(wa), len(wb)))


def original(description: str | None) -> tuple[str, str] | None:
    """(the employer's own title, the text after it) off the copy's description, None without one."""
    m = TITLE.search(description or "")
    if not m:
        return None
    title = " ".join(html.unescape(TAG.sub(" ", m.group(1))).split())
    return (title, description[m.end():]) if title else None


def plain_link(url: str) -> str:
    return url.split("?utm_source=")[0].split("&utm_source=")[0]


def apply_link(description: str | None, base: str, get=httpx.get, title: str | None = None) -> str | None:
    """The employer's own posting link for a copied posting: the job search's row of another source with
    the same title and the same opening text whose link a system here fills (or Workday's), the closest
    first -> that link; none -> None. `title`: the row's own, for a board that keeps it (TITLED)."""
    found = (" ".join(title.split()), description or "") if title and title.strip() else original(description)
    if not found:
        return None
    title, text = found
    try:
        r = get(f"{base}/agent/jobs/search", params={"q": f'"{title.replace(chr(34), "")}"', "q_fields": "title",
                                                     "limit": 50}, timeout=30)
        rows = r.json().get("data") or []
    except (httpx.HTTPError, ValueError):
        return None
    hits = sorted(((overlap(text, row.get("description")), plain_link(row.get("url") or ""))
                   for row in rows
                   if row.get("source") not in SOURCES and " ".join((row.get("title") or "").split()).casefold() == title.casefold()),
                  reverse=True)
    return next((link for score, link in hits
                 if score >= SAME and link and (systems.for_url(link) or systems.elsewhere(link))), None)
