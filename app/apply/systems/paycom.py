"""Paycom (paycomonline.net/v4/ats): the start box read off the user's tab, then whatever page they
continue to, read generically (dom) - the pages after the start box are unmeasured.

Apply opens a "Getting You Started" box (legal name, email twice, phone, SMS consent); the user's
own click on Continue To Application creates their applicant record. No public form definition.
Measured facts, and what isn't measured: app/docs/apply/paycom.md.
"""
import re
from urllib.parse import urlsplit

from apply import browser, dom
from apply.questions import question, signs

NAME = "Paycom"
# current portal link; the older one carries the same key + job in its query
PORTAL_URL = re.compile(r"https?://(?:www\.)?paycomonline\.net/v4/ats/web\.php/portal/([0-9a-z]+)/jobs/(\d+)", re.I)
OLD_URL = re.compile(r"https?://(?:www\.)?paycomonline\.net/v4/ats/web\.php/jobs/ViewJobDetails\?"
                     r"(?=(?:[^#]*&)?job=(\d+))(?=(?:[^#]*&)?clientkey=([0-9a-z]+))", re.I)
# freehire `source` whose links land here (test_systems_live.py); link shapes, anonymised
SOURCES = ("paycom",)
EXAMPLES = ("https://www.paycomonline.net/v4/ats/web.php/portal/acme0000000000000000000000000000/jobs/123456",
            "https://www.paycomonline.net/v4/ats/web.php/portal/acme0000000000000000000000000000/jobs/123456?utm_source=x",
            "https://www.paycomonline.net/v4/ats/web.php/jobs/ViewJobDetails?job=123456&clientkey=ACME0000000000000000000000000000")
PER_PAGE = True
# the job page itself has no form controls (measured, 3 tenants): a box shows only once Apply opened one
READY = "input:not([type=hidden]), select, textarea"
START = "Getting You Started"
# start-box boxes by label (seen 2026-10-03, one tenant): Email / Phone may not be typed as such
START_KIND = {"email": "email", "confirm email": "email", "primary phone": "phone"}
UNMEASURED = "unmeasured system - check every box"


def matches(url: str) -> bool:
    url = url.strip()
    return bool(PORTAL_URL.match(url) or OLD_URL.match(url))


def parse_url(url: str) -> tuple[str, str]:
    """(portal key, job id). One job id names different jobs at two employers (two tenants'
    newest postings shared one, 2026-10-03): the key is what tells them apart."""
    url = url.strip()
    if m := PORTAL_URL.match(url):
        return m.group(1).casefold(), m.group(2)
    if m := OLD_URL.match(url):
        return m.group(2).casefold(), m.group(1)
    raise ValueError(f"not a Paycom posting link: {url}")


def application_url(url: str) -> str:
    key, job = parse_url(url)
    return f"https://www.paycomonline.net/v4/ats/web.php/portal/{key}/jobs/{job}"


def on_tab(url: str, tab_url: str) -> bool:
    """This employer's job, wherever the tab went after it (start box, the form behind it): one
    host serves every employer, so the key + job id decide - never the host alone."""
    key, job = parse_url(url)
    tab = urlsplit(tab_url)
    if (tab.hostname or "").casefold() not in ("www.paycomonline.net", "paycomonline.net"):
        return False
    try:
        return parse_url(tab_url) == (key, job)
    except ValueError:  # the application pages after Continue: same portal, path unmeasured
        return f"/portal/{key}/" in tab.path.casefold()


def start_box(snap: dict) -> bool:
    shown = {dom.title(c["label"]).casefold() for c in snap["controls"] if c["visible"]}
    return {"legal first name", "confirm email"} <= shown


def from_snapshot(snap: dict) -> list[dict]:
    """Questions off the page as read; the start box's boxes typed by their labels, its page named."""
    start = start_box(snap)
    # a page after the start box: named by its heading, so prepare keeps the start box's answers
    heading = next((c["section"] for c in snap["controls"] if c["visible"] and c["section"]), "") or "after the start box"
    out = []
    for q in dom.questions(snap, page=START if start else heading):
        kind = START_KIND.get(q["title"].casefold()) if start else None
        out.append(question(q["id"], q["title"], kind, q["required"], q["options"], kind, q["native"], page=START)
                   if kind else q)
    return out


def steps(snap: dict) -> list[str]:
    """The applicant's own steps on this page, in plain words - never done by us."""
    said = [q["title"] for q in dom.questions(snap) if signs(q["title"])]
    out = [f"answer '{t}' yourself (agreeing or consenting)" for t in said]
    out += dom.user_steps(snap)
    if start_box(snap):
        out.append("click Continue To Application yourself - it makes your applicant record at this employer "
                   "(name, email, phone go to them then); or Sign In if you already have an account")
    return out


def read(page) -> list[dict]:
    """The page the user is on: the start box, or the page they continued to (read generically)."""
    snap = dom.snapshot(page)
    if not any(c["visible"] for c in snap["controls"]):
        raise SystemExit("Paycom shows no boxes yet: the user clicks Apply on the job page (the 'Getting You "
                         "Started' box opens), then run prepare again")
    if not start_box(snap):
        print(f"{NAME}: {UNMEASURED} - this page is read as plain boxes, nothing about it measured yet")
    for step in steps(snap):
        print(f"  the applicant's own step: {step}")
    return from_snapshot(snap)


def questions(url: str) -> list[dict]:
    with browser.page_at(application_url(url), match=lambda tab: on_tab(url, tab)) as page:
        return read(page)


def ids_on_page(page) -> list[str]:
    return [c["hook"] for c in dom.snapshot(page)["controls"] if c["visible"] and not c["password"]]


def fill(page, q: dict, resume_file: str | None) -> str:
    return dom.fill(page, q, resume_file, later=True)
