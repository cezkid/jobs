"""iCIMS (careers-<co>.icims.com/jobs/<id>/<slug>/job): the start box read off the user's tab, then
whatever page they continue to, read generically (dom) - the pages after the start box are unmeasured.

The start box (.../jobs/<id>/<slug>/login, inside the page's own same-site frame) asks for an email,
on some employers a privacy tick, behind an invisible security check (hCaptcha); the user's own click
on Next sends the email. What Next leads to (sign in, password, new account) is unmeasured. No public
form definition. Measured facts, and what isn't measured: app/docs/apply/icims.md.
"""
import re
import time
from urllib.parse import urlsplit

from apply import browser, dom
from apply.questions import signs

NAME = "iCIMS"
# every freehire `icims` link on icims.com (296 of 300 newest US, 2026-10-03): careers-<co>, also
# uscareers-, dcacareers-, general-careers-, <x>-<co>careers. The other 4 sit on an employer's own
# domain without iCIMS's path shape - out of scope, not matched
HOST = re.compile(r"(?:[a-z0-9-]+\.)*icims\.com", re.I)
PATH = re.compile(r"/jobs/(\d+)(?:/([^/?#]+))?(?:/|$)", re.I)
# freehire `source` whose links land here (test_systems_live.py); link shapes, anonymised
SOURCES = ("icims",)
EXAMPLES = ("https://careers-acme.icims.com/jobs/12345/test-job/job?utm_source=x",
            "https://uscareers-acme.icims.com/jobs/678/test-job/job?lang=en",
            "https://careers-acme.icims.com/jobs/12345/test-job/login")
PER_PAGE = True
# the boxes sit in the page's own frame (?in_iframe=1, 3 of 3 tenants): a main-frame selector never
# sees them - recover waits for them in any readable frame, this only for the frame itself
READY = "iframe[src*='in_iframe=1'], input:not([type=hidden]):visible, select:visible, textarea:visible"
START = "Enter Your Information"
# the start box's email box: name css_loginName on 3 of 3 tenants (2026-10-03); its label and heading vary
LOGIN = "css_loginName"
UNMEASURED = "unmeasured system - check every box"


def parse_url(url: str) -> tuple[str, str, str]:
    """(host, job id, slug). Job ids are per employer (host); the slug may be missing."""
    u = urlsplit(url.strip())
    m = PATH.match(u.path)
    if u.scheme not in ("http", "https") or not u.hostname or not HOST.fullmatch(u.hostname) or not m:
        raise ValueError(f"not an iCIMS posting link: {url}")
    return u.hostname.casefold(), m.group(1), m.group(2) or ""


def matches(url: str) -> bool:
    try:
        parse_url(url)
    except ValueError:
        return False
    return True


def application_url(url: str) -> str:
    """The start box's own link: .../jobs/<id>/<slug>/login opens it straight (3 tenants, 2026-10-03).
    A link without a slug: .../jobs/<id>/login - unmeasured."""
    host, job, slug = parse_url(url)
    slug = "" if slug.casefold() in ("job", "login") else slug
    return f"https://{host}/jobs/{job}/{slug + '/' if slug else ''}login"


def on_tab(url: str, tab_url: str) -> bool:
    """This employer's job: same host + job id (job page, start box). Pages after Next: unmeasured -
    assumed to stay under /jobs/<id>/ (iCIMS's own route shape)."""
    try:
        return parse_url(tab_url)[:2] == parse_url(url)[:2]
    except ValueError:
        return False


def boxes(page) -> bool:
    return any(c["visible"] for c in dom.snapshot(page)["controls"])


def recover(page, url: str, wait: float = 30) -> None:
    """Tab still on the job page (no box shows, 1 of 1 measured) -> open the start box's link, a read;
    nothing is clicked. Then wait for a box in the page's frame (main-frame READY can't see it)."""
    if not boxes(page) and not urlsplit(page.url).path.rstrip("/").endswith("/login"):
        page.goto(application_url(url), wait_until="load")
    end = time.monotonic() + wait
    while not boxes(page) and time.monotonic() < end:
        page.wait_for_timeout(500)


def start_box(snap: dict) -> bool:
    """The start box: its email box shows."""
    return any(c["visible"] and c["name"] == LOGIN for c in snap["controls"])


def from_snapshot(snap: dict) -> list[dict]:
    """Questions off the page as read; the start box named as one page whatever its heading (3 tenants,
    2 headings), any other by its first heading. The Next button is no question."""
    snap = snap | {"controls": [c for c in snap["controls"] if c["type"] not in ("submit", "button")]}
    heading = next((c["section"] for c in snap["controls"] if c["visible"] and c["section"]), "") or "after the start box"
    return dom.questions(snap, page=START if start_box(snap) else heading)


def steps(snap: dict) -> list[str]:
    """The applicant's own steps on this page, in plain words - never done by us."""
    said = [q["title"] for q in dom.questions(snap) if signs(q["title"])]
    out = [f"tick '{t}' yourself (agreeing or consenting)" for t in said]
    out += dom.user_steps(snap)
    if start_box(snap):
        out.append("click Next yourself - your email goes to this employer then. What follows (sign in, a "
                   "password, a new account with them) is unmeasured - every password and account is yours")
    return out


def read(page) -> list[dict]:
    """The page the user is on: the start box, or the page they continued to (read generically)."""
    snap = dom.snapshot(page)
    if not any(c["visible"] for c in snap["controls"]):
        raise SystemExit("iCIMS shows no boxes yet: the user clicks Apply on the job page (the box asking for "
                         "their email opens), then run prepare again")
    if not start_box(snap):
        print(f"{NAME}: {UNMEASURED} - this page is read as plain boxes, nothing about it measured yet")
    for step in steps(snap):
        print(f"  the applicant's own step: {step}")
    return from_snapshot(snap)


def questions(url: str) -> list[dict]:
    with browser.page_at(application_url(url), match=lambda tab: on_tab(url, tab)) as page:
        recover(page, url)
        return read(page)


def ids_on_page(page) -> list[str]:
    return [c["hook"] for c in dom.snapshot(page)["controls"]
            if c["visible"] and not c["password"] and c["type"] not in ("submit", "button")]


def fill(page, q: dict, resume_file: str | None) -> str:
    return dom.fill(page, q, resume_file, later=True)
