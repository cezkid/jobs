"""Oracle Recruiting Cloud (<pod>.fa.<dc>.oraclecloud.com/hcmUI/CandidateExperience): the start box read
off the user's tab, then whatever page they continue to, read generically (dom) - the pages after the
start box are unmeasured.

The start box ("Job application form", .../job/<id>/apply/email) asks for an email and a terms tick;
the user's own click on Next sends the email and creates their candidate profile (the page's words).
No public form definition. Measured facts, and what isn't measured: app/docs/apply/oracle.md.
"""
import re
from urllib.parse import urlsplit

from apply import browser, dom
from apply.questions import signs

NAME = "Oracle Recruiting Cloud"
# every freehire `oracle` link (300 of 300 newest US, 2026-10-03): <lang>, <site>, <job id> vary; the
# host is a pod on oraclecloud.com, or (1 of 300) the employer's own domain - the path is Oracle's
PATH = re.compile(r"/hcmUI/CandidateExperience/[^/]+/sites/([^/]+)/job/([^/?#]+)(?:/|$)", re.I)
# freehire `source` whose links land here (test_systems_live.py); link shapes, anonymised
SOURCES = ("oracle",)
EXAMPLES = ("https://acme.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/12345?utm_source=x",
            "https://fa-acme-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/jobsearch/job/REQ_123",
            "https://acme.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/es/sites/AcmeCareers/job/678/apply/email")
PER_PAGE = True
READY = "input:not([type=hidden]):visible, select:visible, textarea:visible"
START = "Job application form"
UNMEASURED = "unmeasured system - check every box"
# a box every start box carries, read as shown (4 of 4 tenants, 2026-10-03) but meant for bots only:
# typing in it marks the applicant a bot - never a question, never filled. Its id swaps with the
# email box's between employers (honey-pot-0 / primary-email-1): dom.fill's label check catches a stale hook
TRAP = re.compile(r"honey-?pot", re.I)
# the hidden digital-assistant box on every page (oda-work-summary-text-area, 4 of 4): not the form's
ASSISTANT = re.compile(r'^\[id="oda-')


def parse_url(url: str) -> tuple[str, str, str]:
    """(host, site, job id). Job ids are per employer (pod) and may carry letters (REQ_814278)."""
    u = urlsplit(url.strip())
    m = PATH.match(u.path)
    if u.scheme not in ("http", "https") or not u.hostname or not m:
        raise ValueError(f"not an Oracle Recruiting Cloud posting link: {url}")
    return u.hostname.casefold(), m.group(1), m.group(2)


def matches(url: str) -> bool:
    try:
        parse_url(url)
    except ValueError:
        return False
    return True


def application_url(url: str) -> str:
    """The start box's own link: it opens straight from it (4 tenants, 2026-10-03), in English - the
    start box is recognised by its boxes, the steps printed by their English words."""
    host, site, job = parse_url(url)
    return f"https://{host}/hcmUI/CandidateExperience/en/sites/{site}/job/{job}/apply/email"


def on_tab(url: str, tab_url: str) -> bool:
    """This employer's job: same host + site + job id in the path (job page, start box). Pages after
    Next: unmeasured - assumed to stay under .../job/<id>/apply (Oracle's own route shape)."""
    try:
        return tuple(map(str.casefold, parse_url(tab_url))) == tuple(map(str.casefold, parse_url(url)))
    except ValueError:
        return False


def recover(page, url: str) -> None:
    """Tab still on the job page (no box shows) -> open the start box's link, the page Apply Now
    leads to; a read, nothing sent. Nothing is clicked."""
    if not page.locator(READY).count() and "/apply/" not in urlsplit(page.url).path:
        page.goto(application_url(url), wait_until="load")


def trap(c: dict) -> bool:
    return bool(TRAP.search(c["hook"]) or TRAP.search(c["name"]) or TRAP.search(c["label"]))


def page_only(snap: dict) -> dict:
    """The snapshot without the bot trap and the assistant's box."""
    return snap | {"controls": [c for c in snap["controls"] if not (trap(c) or ASSISTANT.match(c["hook"]))]}


def start_box(snap: dict) -> bool:
    """The start box: its email box (name primary-email, 4 of 4 tenants) shows."""
    return any(c["visible"] and c["name"] == "primary-email" for c in snap["controls"])


def from_snapshot(snap: dict) -> list[dict]:
    """Questions off the page as read, the page named: the start box, else the page's first heading."""
    heading = next((c["section"] for c in snap["controls"] if c["visible"] and c["section"]), "") or "after the start box"
    return dom.questions(snap, page=START if start_box(snap) else heading)


def steps(snap: dict) -> list[str]:
    """The applicant's own steps on this page, in plain words - never done by us."""
    said = [q["title"] for q in dom.questions(snap) if signs(q["title"])]
    out = [f"tick '{t}' yourself (agreeing or consenting)" for t in said]
    out += dom.user_steps(snap)
    if start_box(snap):
        out.append("click Next yourself - your email goes to this employer then and your profile with them "
                   "is created (the page's words); a code by email may follow - unmeasured. Later pages may ask "
                   "you to type your name as an e-signature - yours to type")
    return out


def read(page) -> list[dict]:
    """The page the user is on: the start box, or the page they continued to (read generically)."""
    snap = page_only(dom.snapshot(page))
    if not any(c["visible"] for c in snap["controls"]):
        raise SystemExit("Oracle shows no boxes yet: the user clicks Apply Now on the job page (the 'Job "
                         "application form' page opens), then run prepare again")
    if not start_box(snap):
        print(f"{NAME}: {UNMEASURED} - this page is read as plain boxes, nothing about it measured yet")
    for step in steps(snap):
        print(f"  the applicant's own step: {step}")
    return from_snapshot(snap)


def questions(url: str) -> list[dict]:
    with browser.page_at(application_url(url), match=lambda tab: on_tab(url, tab)) as page:
        recover(page, url)
        page.locator(READY).first.wait_for(timeout=30000)
        return read(page)


def ids_on_page(page) -> list[str]:
    return [c["hook"] for c in page_only(dom.snapshot(page))["controls"] if c["visible"] and not c["password"]]


def fill(page, q: dict, resume_file: str | None) -> str:
    if TRAP.search(q["id"]) or TRAP.search(q["title"]):
        return "FAIL a box meant for bots only - never filled"
    return dom.fill(page, q, resume_file, later=True)
