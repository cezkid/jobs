"""iCIMS (careers-<co>.icims.com/jobs/<id>/<slug>/job): the start box read off the user's tab, then
whatever page they continue to, read generically (dom) - the pages after the start box are unmeasured.

The start box (.../jobs/<id>/<slug>/login, inside the page's own same-site frame) asks for an email,
on some employers a privacy tick, behind an invisible security check (hCaptcha); the user's own click
on Next sends the email. What Next leads to (sign in, password, new account) is unmeasured. No public
form definition; the job page answers 410 once the posting is gone (closed). Measured facts, and what
isn't measured: app/docs/apply/icims.md.
"""
import contextlib
import re
import time
from urllib.parse import urlsplit

import httpx

import cfg

from apply import answers, browser, dom
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
# the start box's way on (3 of 3 tenants, a submit input in the page's own frame): pressed only with the user's
# continue_on_apply, only there. Later pages' buttons read Submit Profile / Submit (one tenant) and stay theirs
NEXT = "#enterEmailSubmitButton"
# the boxes sit in the page's own frame (?in_iframe=1, 3 of 3 tenants): a main-frame selector never
# sees them - recover waits for them in any readable frame, this only for the frame itself
READY = "iframe[src*='in_iframe=1'], input:not([type=hidden]):visible, select:visible, textarea:visible"
START = "Enter Your Information"
# the start box's email box: name css_loginName on 3 of 3 tenants (2026-10-03); its label and heading vary
LOGIN = "css_loginName"
UNMEASURED = "unmeasured system - check every box"
# a gone posting's start-box link (2 of 2 that answer 410, 2026-10-06): iCIMS's job search, marked
# notFound=1 in its address, its frame saying these words - or the employer's own careers site
NOT_FOUND = re.compile(r"either does not exist or is no longer open", re.I)
GONE_WAIT_MS = 3000
# iCIMS's own list on the pages after the start box (one tenant, 2026-10-12): a <select role=combobox
# icimsdropdown-enabled=1> shown as a link "<id>_icimsDropdown"; its options sit in "<id>_dropdown-results"
# behind a search box. With icimsdropdown-ajax=1 the select holds only the current pick (State, School):
# the rest load as the search box is typed in - select_option alone finds nothing to pick
WIDGET = "icimsdropdown-enabled"
# once the resume was in, the page came back after Next with City + State read off the resume (a past
# job's city) and Zip emptied - one application, 2026-10-12; when it happens (upload or Next) unmeasured
RESUME_READ = ("check City, State and Zip before and after Next - iCIMS may replace them with a place it "
               "reads off your resume (seen once)")
WIDGET_WAIT = 8
# the same list where the select is fully hidden (one tenant, 2026-11-03): only its link reads as a box, an
# <a role=combobox>, named "<select id>_icimsDropdown"
WIDGET_LINK = re.compile(r'^\[id="(.+)_icimsDropdown"\]$')
# a repeating block's box, known only by its block's title + row ("Professional Experience (1)")
ROW = re.compile(r"\(\d+\)\|")
# a chosen resume reloads the form, read off the resume (one tenant, 2026-11-03: address "?uploadResume=1", the
# work history in its rows, boxes typed meanwhile lost): boxes wait for it. How long it takes: unmeasured
RESUME_WAIT = 15
RESUME_QUIET = 1.5


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


def gone_now(page) -> str | None:
    if not HOST.fullmatch(urlsplit(page.url).hostname or ""):
        return "the posting's link now leads to the employer's own careers site, not the posting - it may have closed"
    frames = dom.frames(page)[0]
    if not any("notfound=1" in urlsplit(f.url).query.casefold() for f in frames):
        return None
    for f in frames:
        with contextlib.suppress(Exception):
            if said := NOT_FOUND.search(f.locator("body").inner_text(timeout=2000)):
                return f"the posting says it's closed (\"The job that you were looking for {said.group()}\")"
    return "iCIMS shows its job search marked 'not found' instead of the posting - it may have closed"


def gone(page, url: str) -> str | None:
    """iCIMS's own sign the posting is gone, read off the page (form.closed, before the form wait: its
    job search shows boxes too). The gone page comes up by a redirect after load: watched GONE_WAIT_MS."""
    end = time.monotonic() + GONE_WAIT_MS / 1000
    while True:
        with contextlib.suppress(Exception):
            page.wait_for_load_state("load", timeout=GONE_WAIT_MS)
        if (said := gone_now(page)) or start_box(dom.snapshot(page)) or time.monotonic() >= end:
            return said
        page.wait_for_timeout(250)


def closed(url: str) -> str | None:
    """Why no box shows (form.closed, after the page's own words): the job page as a plain read - 410
    once iCIMS has taken it down (3 of 19 links, 2026-10-06), 200 while it's up. None = still up."""
    job_page = application_url(url).removesuffix("login") + "job?in_iframe=1"
    try:
        r = httpx.get(job_page, timeout=30, headers={"User-Agent": cfg.USER_AGENT})
    except httpx.HTTPError as e:
        return f"can't tell if the posting is open - iCIMS didn't answer ({type(e).__name__})"
    if r.status_code == 410:
        return "iCIMS says the job either does not exist or is no longer open - it may have closed"
    return None if r.status_code == 200 else f"can't tell if the posting is open - iCIMS answered {r.status_code}"


def recover(page, url: str, wait: float = 30) -> None:
    """Tab still on the job page (no box shows, 1 of 1 measured) -> open the start box's link, a read;
    nothing is clicked. Then wait for a box in the page's frame (main-frame READY can't see it). A gone
    posting's page shows boxes too (its job search): left as is, read says why."""
    if gone_now(page):
        return
    if not boxes(page) and not urlsplit(page.url).path.rstrip("/").endswith("/login"):
        page.goto(application_url(url), wait_until="load")
    end = time.monotonic() + wait
    while not boxes(page) and not gone_now(page) and time.monotonic() < end:
        page.wait_for_timeout(500)


def start_box(snap: dict) -> bool:
    """The start box: its email box shows."""
    return any(c["visible"] and c["name"] == LOGIN for c in snap["controls"])


def next_button(page):
    """Next on the start box, else None. Later pages are never pressed for the user."""
    if not start_box(dom.snapshot(page)):
        return None
    for frame in dom.frames(page)[0]:
        found = frame.locator(NEXT).filter(visible=True)
        if found.count() == 1 and (found.first.get_attribute("value") or "").strip().casefold() == "next":
            return found.first
    return None


def step(page) -> str:
    """Where the form is, for form.go_on: blank while no box shows (the page mid-change)."""
    snap = dom.snapshot(page)
    if not any(c["visible"] for c in snap["controls"]):
        return ""
    return START if start_box(snap) else "after the start box"


def from_snapshot(snap: dict) -> list[dict]:
    """Questions off the page as read; the start box named as one page whatever its heading (3 tenants,
    2 headings), any other by its first heading. The Next button is no question."""
    snap = snap | {"controls": [c for c in snap["controls"] if c["type"] not in ("submit", "button")]}
    heading = next((c["section"] for c in snap["controls"] if c["visible"] and c["section"]), "") or "after the start box"
    return dom.questions(snap, page=START if start_box(snap) else heading)


def steps(snap: dict) -> list[str]:
    """The applicant's own steps on this page, in plain words - never done by us."""
    said = [q["title"] for q in dom.questions(snap) if q["title"].strip() and signs(q["title"])]
    out = [f"tick '{t}' yourself (agreeing or consenting)" for t in said]
    out += dom.user_steps(snap)
    if any(c["visible"] and c["type"] == "file" for c in snap["controls"]):
        out.append(RESUME_READ)
    if start_box(snap):
        out.append("Next: their click, or fill's with continue_on_apply - their email goes to this employer then. What "
                   "follows (sign in, a password, a new account with them) is unmeasured - every password and account "
                   "is yours")
    return out


def read(page) -> list[dict]:
    """The page the user is on: the start box, or the page they continued to (read generically)."""
    if said := gone_now(page):
        raise SystemExit(f"{said} - nothing to read; ask the user, then status set <job> closed if it is")
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


def holds(page, q: dict) -> bool:
    """The answer still shows, read off the page once the form had time to keep it (form.recheck), as
    icims.md "Read back (2026-10)" records it: dom.holds in the start box's own frame - the email box by
    its exact value. The privacy tick is the applicant's (never filled, never read as ours)."""
    if signs(q["title"]):
        return False
    if WIDGET_LINK.match(q["id"]):
        found = dom.find(page, q["id"])
        return bool(found) and dom.norm(found[2][0].inner_text()).casefold() == str(q.get("answer") or "").strip().casefold()
    return dom.holds(page, q)


def put_widget(frame, el, value) -> str:
    """iCIMS's own list (WIDGET): opened by its link, the answer typed into its search box, the
    option that IS the answer clicked - as a person picks it. Read back off the select itself."""
    sid, want = el.get_attribute("id"), str(value).strip()
    frame.locator(f'[id="{sid}_icimsDropdown"]').click()
    search = frame.locator(f'[id="{sid}_icimsDropdown_ctnr"] input.dropdown-search')
    search.fill("")
    search.press_sequentially(want[:40], delay=30)
    options = frame.locator(f'[id="{sid}_dropdown-results"] li.result-selectable')
    texts: list[str] = []
    end = time.monotonic() + WIDGET_WAIT
    while time.monotonic() < end:
        texts = [dom.norm(t) for t in options.all_inner_texts()]
        if any(t.casefold() == want.casefold() for t in texts):
            break
        frame.page.wait_for_timeout(250)
    hit = next((i for i, t in enumerate(texts) if t.casefold() == want.casefold()), None)
    if hit is None:
        search.press("Escape")
        offered = [t for t in texts if not t.startswith("—")][:5]
        return f"ASK no option '{want}'; offered: {', '.join(offered) or 'nothing'}"
    options.nth(hit).click()
    frame.page.wait_for_timeout(200)
    got = el.evaluate("e => e.selectedIndex < 0 ? '' : e.options[e.selectedIndex].text.replace(/\\s+/g, ' ').trim()")
    return "ok" if got.casefold() == want.casefold() else f"FAIL shows '{got}'"


def put_resume(page, q: dict, resume_file: str | None) -> str:
    """The resume box, then the wait while the form reloads with what the site read off the file: any box
    typed before that is lost. No reload within RESUME_WAIT: goes on."""
    moved = []

    def note(_frame):
        moved.append(time.monotonic())

    page.on("framenavigated", note)
    try:
        said = dom.fill(page, q, resume_file, later=True)
        if said != "ok":
            return said
        end = time.monotonic() + RESUME_WAIT
        while time.monotonic() < end:
            page.wait_for_timeout(250)
            if moved and time.monotonic() - moved[-1] > RESUME_QUIET and boxes(page):
                break
    finally:
        page.remove_listener("framenavigated", note)
    return said


def shows(el) -> str:
    """What a box holds now; a list's placeholder (no value) is nothing."""
    return dom.norm(el.evaluate("e => !e.value ? '' : e.tagName === 'SELECT' ? e.options[e.selectedIndex].text : e.value"))


def fill(page, q: dict, resume_file: str | None) -> str:
    if q["kind"] == "file" and q.get("key") == "resume" and q.get("answer") is True and resume_file:
        return put_resume(page, q, resume_file)
    if q.get("answer") in (None, "") or signs(q["title"]):
        return dom.fill(page, q, resume_file, later=True)
    found = dom.find(page, q["id"])
    if found is None:
        return dom.fill(page, q, resume_file, later=True)
    frame, info, members = found
    linked = WIDGET_LINK.match(q["id"])
    widget = linked or (q.get("native", "").startswith("dom:select") and members[0].get_attribute(WIDGET) == "1")
    # rows the site filled from the resume come first, in its order: the answer was written for another row
    if ROW.search(q["id"]) and (held := shows(members[0])) and held != dom.norm(str(q["answer"])):
        return f"ASK iCIMS filled this row from the resume (shows '{held}') - left as it is, check it on the page"
    if widget:
        if answers.fold(dom.title(info["label"])) != answers.fold(q["title"]):
            return f"FAIL box label changed ('{dom.title(info['label'])}') - read the page again"
        value = "Yes" if q["kind"] == "yesno" and dom.yes(q["answer"]) else "No" if q["kind"] == "yesno" else q["answer"]
        el = frame.query_selector(f'select[id="{linked.group(1)}"]') if linked else members[0]
        return put_widget(frame, el, value) if el else f"FAIL the list behind '{q['title']}' isn't on the page"
    return dom.fill(page, q, resume_file, later=True)
