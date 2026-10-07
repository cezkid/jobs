"""ADP Workforce Now (workforcenow.adp.com recruitment pages): the start box read off the user's tab,
then whatever page they continue to, read generically (dom) - the pages after the start box are
unmeasured.

Apply opens a "Tell us about yourself" box (first + last name, email, mobile number); the user's own
click on Continue sends them to the employer - the page calls it a verification. Social sign-in
(LinkedIn, Google, Facebook) is theirs too. No public form definition.
Measured facts, and what isn't measured: app/docs/apply/adp.md.
"""
import re
import time
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx

from apply import browser, dom
from apply.questions import question, signs

NAME = "ADP Workforce Now"
HOST = "workforcenow.adp.com"
PATH = "/mascsr/default/mdf/recruitment/recruitment.html"
# freehire `source` whose links land here (test_systems_live.py); link shapes, anonymised
SOURCES = ("adp",)
EXAMPLES = ("https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=00000000-acme-0000-0000-000000000000&ccId=19000101_000001&jobId=9200000000001_1",
            "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?ccId=19000101_000001&cid=00000000-acme-0000-0000-000000000000&jobId=9200000000001_1&lang=en_US&utm_source=x")
PER_PAGE = True
# the job page's button that opens the start box (measure.py raw clicks it once; recover() too)
APPLY = "Apply"
# the posting's record, the one the job page itself reads (plain GET, signed out, 2026-10-07)
RECORD = ("https://" + HOST + "/mascsr/default/careercenter/public/events/staffing/v1/job-requisitions/{job}"
          "?cid={cid}&timeStamp={ms}&lang=en_US&ccId={cc}&locale=en_US")
# the job page's only controls are the hidden cookie panel's (measured, 3 tenants): a box shows
# only once Apply opened one
READY = "input:not([type=hidden]):visible, select:visible, textarea:visible"
START = "Tell us about yourself"
START_LABELS = {"first name", "last name", "email", "mobile number"}
# start-box boxes by label (2026-10-03, one tenant): Email is a plain text input; the phone is
# required by the employer's settings (3 of 3 tenants) though the box itself isn't marked
START_KIND = {"email": "email", "mobile number": "phone"}
UNMEASURED = "unmeasured system - check every box"
# the cookie panel's own boxes, hidden on every page (OneTrust, 3 of 3 tenants, 2026-10-03): cookie
# choices are the applicant's consent - never a question, never ticked (try ticked them before this)
COOKIE_LABELS = {"functional", "analytics", "advertising", "performance", "targeting", "checkbox label",
                 "cookie list search"}
COOKIE_IDS = re.compile(r'^\[id="(?:vendor-search-handler|chkbox-id|select-all-[\w-]+)"\]$')


def parse_url(url: str) -> tuple[str, str]:
    """(cid, job id). One job id was listed under two employers' cids (2026-10-03): the cid tells
    them apart. Params come in any order, with or without ccId / lang / utm_*."""
    u = urlsplit(url.strip())
    if (u.scheme not in ("http", "https") or (u.hostname or "").casefold() != HOST
            or u.path.casefold() != PATH):
        raise ValueError(f"not an ADP Workforce Now posting link: {url}")
    q = {k.casefold(): v[0] for k, v in parse_qs(u.query).items()}
    if not q.get("cid") or not q.get("jobid"):
        raise ValueError(f"not an ADP Workforce Now posting link (no cid + jobId): {url}")
    return q["cid"].casefold(), q["jobid"]


def matches(url: str) -> bool:
    try:
        parse_url(url)
    except ValueError:
        return False
    return True


def application_url(url: str) -> str:
    cid, job = parse_url(url)
    cc = {k.casefold(): v[0] for k, v in parse_qs(urlsplit(url.strip()).query).items()}.get("ccid")
    # English labels: the start box is recognised by them
    params = {"cid": cid, **({"ccId": cc} if cc else {}), "jobId": job, "lang": "en_US"}
    return f"https://{HOST}{PATH}?{urlencode(params)}"


def closed(url: str) -> str | None:
    """Why no box shows (form.closed, after the page's own words): the posting's record. Its job id +
    title -> None (open); an empty record (no id, no title) -> closed: the page then says "We are no
    longer accepting applications for this position." (1 of 6 listed open, measured 2026-10-07); anything
    else -> can't tell - never a guess."""
    parse_url(url)
    q = {k.casefold(): v[0] for k, v in parse_qs(urlsplit(url.strip()).query).items()}
    try:
        r = httpx.get(RECORD.format(job=q["jobid"], cid=q["cid"], cc=q.get("ccid", ""), ms=int(time.time() * 1000)),
                      timeout=30, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return f"can't tell if the posting is open - ADP answered {r.status_code}"
        record = r.json()
    except (httpx.HTTPError, ValueError) as e:
        return f"can't tell if the posting is open - ADP didn't answer ({type(e).__name__})"
    if not isinstance(record, dict):
        return "can't tell if the posting is open - ADP's answer wasn't a posting record"
    if record.get("itemID") == q["jobid"] and record.get("requisitionTitle"):
        return None
    if not record.get("itemID") and not record.get("requisitionTitle"):
        return "ADP says it is no longer accepting applications for this job - it may have closed"
    return "can't tell if the posting is open - ADP's record names another job"


def on_tab(url: str, tab_url: str) -> bool:
    """This employer's job: the start box opens over the job page (same link, 3 tenants); one host
    serves every employer, so cid + job id decide - never the host alone."""
    cid, job = parse_url(url)
    try:
        return parse_url(tab_url) == (cid, job)
    except ValueError:  # pages after Continue: unmeasured - same host + this employer's cid
        tab = urlsplit(tab_url)
        return (tab.hostname or "").casefold() == HOST and cid in tab.query.casefold()


def recover(page, url: str) -> None:
    """Tab still on the job page -> click its Apply once: it opens the start box over the page and
    sent nothing in the click (measured, blocked, 2026-10-03). Nothing else is clicked."""
    if page.locator(READY).count():
        return
    apply = page.get_by_role("button", name=APPLY, exact=True).filter(visible=True)
    if apply.count():
        apply.first.click(timeout=15000)


def page_only(snap: dict) -> dict:
    """The snapshot without the cookie panel's boxes."""
    keep = [c for c in snap["controls"] if not (COOKIE_IDS.match(c["hook"]) or
            (not c["visible"] and dom.title(c["label"]).casefold() in COOKIE_LABELS))]
    return snap | {"controls": keep}


def start_box(snap: dict) -> bool:
    shown = {dom.title(c["label"]).casefold() for c in snap["controls"] if c["visible"]}
    return START_LABELS <= shown


def from_snapshot(snap: dict) -> list[dict]:
    """Questions off the page as read; the start box's boxes typed by their labels, its page named."""
    start = start_box(snap)
    # a page after the start box: named by its heading, so prepare keeps the start box's answers
    heading = next((c["section"] for c in snap["controls"] if c["visible"] and c["section"]), "") or "after the start box"
    out = []
    for q in dom.questions(snap, page=START if start else heading):
        kind = START_KIND.get(q["title"].casefold()) if start else None
        out.append(question(q["id"], q["title"], kind, True, q["options"], kind, q["native"], page=START)
                   if kind else q)
    return out


def steps(snap: dict) -> list[str]:
    """The applicant's own steps on this page, in plain words - never done by us."""
    said = [q["title"] for q in dom.questions(snap) if signs(q["title"])]
    out = [f"answer '{t}' yourself (agreeing or consenting)" for t in said]
    out += dom.user_steps(snap)
    if start_box(snap):
        out.append("click Continue yourself - your name, email and mobile number go to this employer then "
                   "(the page calls it a verification: a code by text or email may follow - unmeasured); "
                   "or sign in with LinkedIn, Google or Facebook yourself")
    return out


def read(page) -> list[dict]:
    """The page the user is on: the start box, or the page they continued to (read generically)."""
    snap = page_only(dom.snapshot(page))
    if not any(c["visible"] for c in snap["controls"]):
        raise SystemExit("ADP shows no boxes yet: the user clicks Apply on the job page (the 'Tell us about "
                         "yourself' box opens), then run prepare again")
    if not start_box(snap):
        print(f"{NAME}: {UNMEASURED} - this page is read as plain boxes, nothing about it measured yet")
    for step in steps(snap):
        print(f"  the applicant's own step: {step}")
    return from_snapshot(snap)


def questions(url: str) -> list[dict]:
    if (why := closed(url)) and not why.startswith("can't tell"):
        raise ValueError(why)  # before any browser: a gone posting never opens a tab for nothing
    with browser.page_at(application_url(url), match=lambda tab: on_tab(url, tab)) as page:
        recover(page, url)
        page.locator(READY).first.wait_for(timeout=30000)
        return read(page)


def ids_on_page(page) -> list[str]:
    return [c["hook"] for c in page_only(dom.snapshot(page))["controls"] if c["visible"] and not c["password"]]


def with_code(page, q: dict) -> dict:
    """The mobile box keeps its country code in front ("+1" prefilled, the picker beside it; 2026-10-03):
    a number typed without one gets the box's own, or the box shows +1 and the digits never match."""
    answer = str(q.get("answer") or "").strip()
    if q["kind"] != "phone" or not answer or answer.startswith("+"):
        return q
    box = page.locator(q["id"])
    code = re.match(r"\s*(\+\d{1,4})", box.first.input_value()) if box.count() else None
    return q | {"answer": f"{code.group(1)} {answer}"} if code else q


def cookie(q: dict) -> bool:
    return bool(COOKIE_IDS.match(q["id"]) or (q["id"].startswith("role=checkbox|") and q["title"].casefold() in COOKIE_LABELS))


def holds(page, q: dict) -> bool:
    """The answer still shows, read off the page once the form had time to keep it (form.recheck), as
    adp.md "Read back (2026-10)" records it: dom.holds on the page without the cookie panel - each box
    by its value, the mobile number by its digits (the box shows its own "+1 " in front). Cookie choices
    and agreeing ticks are the applicant's: never read as ours."""
    if cookie(q) or signs(q["title"]):
        return False
    return dom.holds(page, q, page_only(dom.snapshot(page)))


def fill(page, q: dict, resume_file: str | None) -> str:
    if cookie(q):
        return "ASK yours to do on the page - cookie choices are your own"
    return dom.fill(page, with_code(page, q), resume_file, later=True)
