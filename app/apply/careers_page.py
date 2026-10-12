"""An employer's own careers site that shows the posting and sends Apply to a hiring system (Radancy's
TalentBrew sites: freehire `source` radancy). The posting link on the job list is that page, not the form;
its Apply link names the system - read off the page, a plain GET of the public posting (as opening it).

Measured 2026-10-12 on 4 employers' TalentBrew pages (5 links): the Apply anchors carry
data-selector-name="job-apply-link" with the system's link in data-apply-url and href - Taleo, UKG and
Avature seen. The same page holds an employees-only Apply (class *internal-apply*, another career section):
never taken. A gone posting's link answered by sending the visitor to the site's job search (/search-jobs,
1 of 1): said, nothing filled.
"""
import html
import re
from urllib.parse import urlsplit

import httpx

from apply import systems

ANCHOR = re.compile(r"<a\b[^>]*>", re.I)
APPLY = re.compile(r"""data-selector-name\s*=\s*["']job-apply-link["']""", re.I)
ATTR = re.compile(r"""\b(data-apply-url|href)\s*=\s*["']([^"']+)["']""", re.I)
SEARCH = re.compile(r"/search-jobs(?:/|$)", re.I)


def links(page_html: str) -> list[str]:
    """The Apply anchors' links in page order: data-apply-url before href, each once."""
    out = []
    for a in ANCHOR.findall(page_html):
        if not APPLY.search(a):
            continue
        found = dict((k.casefold(), html.unescape(v).strip()) for k, v in ATTR.findall(a))
        for k in ("data-apply-url", "href"):
            if (v := found.get(k, "")).startswith(("http://", "https://")) and v not in out:
                out.append(v)
    return out


def apply_link(url: str, get=httpx.get) -> str | None:
    """The hiring system's link behind a careers page's Apply, when a system here fills it (or Workday's
    route) -> that link; a careers page with no such Apply -> None. A posting page that now sends the
    visitor to the job search -> ValueError saying it may have closed."""
    try:
        r = get(url, timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
    except httpx.HTTPError:
        return None
    asked, landed = urlsplit(url), urlsplit(str(r.url))
    if SEARCH.search(landed.path) and not SEARCH.search(asked.path):
        raise ValueError("the posting's page now opens the employer's job search instead - it may have closed")
    if r.status_code != 200:
        return None
    return next((link for link in links(r.text) if systems.for_url(link) or systems.elsewhere(link)), None)
