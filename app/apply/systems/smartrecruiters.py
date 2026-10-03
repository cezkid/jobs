"""SmartRecruiters (jobs.smartrecruiters.com): questions read off its own one-page form app
("oneclick-ui"), answers typed into its Spark widgets (open shadow roots), screening after Next.

No public question list: the form definition is fetched by the page with an internal company id
(plain HTTP -> 403), the documented apply API wants a partner key. So `read` takes the form off
the tab. Measured facts and why each rule exists: app/docs/apply/smartrecruiters.md.
"""
import functools
import re
from pathlib import Path

import httpx

from apply import browser, dom
from apply.questions import LATER, question

NAME = "SmartRecruiters"
# posting: /<Company>/<postingId>-<slug>; the form app: /oneclick-ui/company/<Company>/publication/<uuid>
POSTING_URL = re.compile(r"https?://jobs\.smartrecruiters\.com/(?!oneclick-ui/)([\w.-]+)/(\d{6,})(?:-[^/?#]*)?/?(?:[?#].*)?$", re.I)
FORM_URL = re.compile(r"https?://jobs\.smartrecruiters\.com/oneclick-ui/company/([\w.-]+)/publication/([0-9a-f-]{36})", re.I)
# freehire `source` whose links land here (test_systems_live.py); link shapes, anonymised
SOURCES = ("smartrecruiters",)
EXAMPLES = ("https://jobs.smartrecruiters.com/acme/744000000000001-example-job?utm_source=freehire.me",
            "https://jobs.smartrecruiters.com/acme/744000000000001",
            "https://jobs.smartrecruiters.com/oneclick-ui/company/acme/publication/"
            "00000000-0000-4000-a000-000000000001?dcr_ci=acme")
# one form app, its pages swapped in place: fill works on the user's tab (a fresh one is page 1)
PER_PAGE = True
READY = "#first-name-input"
POSTINGS = "https://api.smartrecruiters.com/v1/companies/{company}/postings/{posting}"
# page names in the answers file: page 1 is always the same contact + resume form (4 of 4 tenants)
PAGE_ONE = "Contact and resume"
PAGE_LATER = "Screening questions"
RESUME = "resume"
COUNTRY = "phone-country"
# boxes on page 1 that are never questions: the photo slot (no photo - AGENTS.md), the phone
# widget's own country search (filled by COUNTRY)
SKIP_LABELS = ("upload profile image", "search by country/region or code")

# the file boxes in page order across shadow roots: two share id + label (resume parsing on top,
# the resume field below the contact boxes, 2026-10-03) - the one after First name is the field
FILES = """() => { const out = [];
  const walk = n => { for (const e of n.children) {
      if (e.id === 'first-name-input') out.push('first');
      else if (e.tagName === 'INPUT' && e.type === 'file' && e.id === 'file-input') out.push(e);
      if (e.shadowRoot) walk(e.shadowRoot);
      walk(e); } };
  walk(document);
  const at = out.indexOf('first');
  return at < 0 ? null : out.slice(at + 1).find(e => e !== 'first') || null; }"""
# text inside an element, its shadow roots included: Spark options + the country button keep
# theirs there, so innerText reads "" (2026-10-03); an uploaded file's name shows in one too
DEEP = """root => { const parts = [];
  const walk = n => { for (const e of n.childNodes) {
      if (e.nodeType === 3) parts.push(e.textContent);
      if (e.shadowRoot) walk(e.shadowRoot);
      if (e.nodeType === 1 && !/^(STYLE|SCRIPT)$/.test(e.tagName)) walk(e); } };
  if (root.shadowRoot) walk(root.shadowRoot);
  walk(root);
  return parts.join(' ').replace(/\\s+/g, ' ').trim(); }"""


def matches(url: str) -> bool:
    url = url.strip()
    return bool(POSTING_URL.match(url) or FORM_URL.match(url))


def parse_url(url: str) -> tuple[str, str]:
    """(company, posting id) for a posting link; (company, publication uuid) for the form app's."""
    url = url.strip()
    m = POSTING_URL.match(url) or FORM_URL.match(url)
    if not m:
        raise ValueError(f"not a SmartRecruiters posting link: {url}")
    return m.group(1), m.group(2)


def application_url(url: str) -> str:
    """Posting + ?oga=true: SmartRecruiters sends it on to the form app (302, 2026-10-03) - the
    posting's own applyUrl. A form app link is the form already."""
    if FORM_URL.match(url.strip()):
        return url.strip()
    company, posting = parse_url(url)
    return f"https://jobs.smartrecruiters.com/{company}/{posting}?oga=true"


@functools.lru_cache(maxsize=32)
def record(url: str) -> dict | None:
    """The posting's public record (no key; only the listing id goes out, as when opening the
    posting): `uuid` = the form app's id, `active`. None when it can't be read."""
    company, posting = parse_url(url)
    try:
        r = httpx.get(POSTINGS.format(company=company, posting=posting), timeout=15)
        return r.json() if r.status_code == 200 else None
    except (httpx.HTTPError, ValueError):
        return None


def publication(url: str) -> str | None:
    """The form app's id for a posting; a form app link carries it."""
    if m := FORM_URL.match(url.strip()):
        return m.group(2)
    return (record(url) or {}).get("uuid")


def is_closed(url: str) -> bool:
    """The record says inactive (a closed posting's own page wording: unmeasured, 2026-10-03)."""
    if FORM_URL.match(url.strip()):
        return False
    return (record(url) or {}).get("active") is False


def on_tab(url: str, tab_url: str) -> bool:
    """This application's tab: the posting itself, or the form app on its publication id. The
    redirect drops the posting id from the address, so the id is looked up once."""
    company, posting = parse_url(url)
    if "jobs.smartrecruiters.com/" not in tab_url:
        return False
    if f"/{posting}" in tab_url:
        return True
    uuid = publication(url) if "/oneclick-ui/" in tab_url else None
    return bool(uuid) and f"/publication/{uuid}" in tab_url


def from_snapshot(snap: dict) -> list[dict]:
    """Shared-shape questions off one step of the form app. Page 1 = contact + resume (known
    boxes, a few fixed up); any other step = whatever it shows, read as plain HTML."""
    first = any(c["id"] == "first-name-input" and c["visible"] for c in snap["controls"])
    page = PAGE_ONE if first else PAGE_LATER
    out = []
    for q in dom.questions(snap, page=page):
        label = q["title"].casefold()
        if q["kind"] == "file" or label in SKIP_LABELS:
            continue  # the two resume boxes share one hook: the field is added below, the photo never
        if first and q["title"] == "City":
            q |= {"kind": "location", "key": "location"}  # a place search, typed + picked like Location
        if first and q["title"] == "Country code":
            # a button showing the chosen country; its options list only opens on click
            q = question(COUNTRY, "Country (of your phone number)", "choice", True, native="country", page=page)
        out.append(q)
    if first:
        # optional on 1 of 4 tenants; the snapshot's required mark is on a hidden input
        out.insert(0, question(RESUME, "Resume", "file", True, key="resume", native="resume", page=page))
    return out


def read(page) -> list[dict]:
    """The step of the form the user's tab shows (prepare reuses it, no second tab)."""
    page.locator(READY).first.wait_for(timeout=30000)
    return from_snapshot(dom.snapshot(page))


def questions(url: str) -> list[dict]:
    if is_closed(url):
        raise ValueError("posting not active - it may have closed")
    with browser.page_at(application_url(url), match=lambda tab: on_tab(url, tab)) as page:
        return read(page)


def ids_on_page(page) -> list[str]:
    return [q["id"] for q in from_snapshot(dom.snapshot(page))]


# Spark list options: <spl-select-option value=... label=...> in the list the box names
# (aria-controls: City) or in the widget around it (phone country); a place's name sits in a
# title="New York, NY, US" inside the option, shown from a shadow root (2026-10-03, 1 tenant).
# -> [{value, label}]; `pick`: that option clicked by script first
MENU = """(box, pick) => {
  const roots = [document]; for (let i = 0; i < roots.length; i++)
    for (const e of roots[i].querySelectorAll('*')) if (e.shadowRoot) roots.push(e.shadowRoot);
  const id = box.getAttribute('aria-controls'), host = box.getRootNode().host;
  const list = (id && roots.map(r => r.querySelector(`[id="${id}"]`)).find(Boolean)) || null;
  const within = el => el ? [...el.querySelectorAll('spl-select-option')] : [];
  const opts = within(list).length ? within(list) : within(host);
  const label = o => o.getAttribute('label') || (o.querySelector('[title]') || {}).title || o.textContent;
  if (pick !== null && opts[pick]) opts[pick].click();
  return {value: host ? host.getAttribute('value') || '' : '',
    options: opts.map(o => ({value: o.getAttribute('value') || '', label: (label(o) || '').replace(/\\s+/g, ' ').trim()}))}; }"""


def deep_text(el) -> str:
    return el.evaluate(DEEP)


def page_text(page) -> str:
    return page.evaluate(f"() => ({DEEP})(document.body)")


def put_file(page, path: str) -> str:
    box = page.evaluate_handle(FILES).as_element()
    if box is None:
        return f"{LATER} on another page of the form" if not page.locator("#first-name-input").count() \
            else "ASK resume box not found - upload it by hand"
    # never the box above the name: that one reads the file and fills the boxes from it
    box.set_input_files(path)
    name = Path(path).name
    for _ in range(40):
        if name in page_text(page):
            return "ok"
        page.wait_for_timeout(500)
    return "ASK upload not confirmed on page - check the resume box"


def menu(box, pick: int | None = None) -> dict:
    """{value: the widget's current pick, options: [{value, label}]} - one read per call: the
    country list (200+ options) re-filters while typed into; read one by one they went stale."""
    return box.evaluate(MENU, pick)


def choose(page, box, want: str) -> tuple[str | None, list[str]]:
    """Click the option whose label starts with `want` (never the first offered) -> (its label or
    None, labels offered). By script, never a pointer click: on City / the phone's country those
    waited 30s and failed (2026-10-03, 2 tenants) - the bottom of the form sat under another layer."""
    labels = []
    for _ in range(16):  # the place search answers after a pause in typing
        page.wait_for_timeout(500)
        if labels := [o["label"] for o in menu(box)["options"]]:
            break
    hit = next((i for i, t in enumerate(labels) if t.casefold().startswith(want.casefold())), None)
    if hit is None:
        return None, labels
    menu(box, hit)
    page.wait_for_timeout(300)
    return labels[hit], labels


def offered(labels: list[str]) -> str:
    return f"offered: {', '.join(labels[:5])}" if labels else "no list opened"


def put_city(page, q: dict) -> str:
    found = dom.find(page, q["id"])
    if found is None:
        return f"{LATER} on another page of the form"
    box = found[2][0]
    value = str(q["answer"]).strip()
    box.scroll_into_view_if_needed()
    box.focus()
    box.fill("")
    box.type(value.split(",")[0], delay=40)
    chosen, labels = choose(page, box, value.split(",")[0])
    if chosen is None:
        box.press("Escape")
        return f"ASK no place on the list starts with '{value}' ({offered(labels)}) - pick it by hand"
    got = box.input_value()
    return "ok" if got.split(",")[0].casefold() == chosen.split(",")[0].casefold() else f"FAIL shows '{got}'"


def country_shown(button) -> str:
    """The phone country picked: the widget keeps its code as value (US), the name as an option label."""
    got = menu(button)
    return next((o["label"] for o in got["options"] if o["value"] == got["value"]), got["value"])


def put_country(page, value: str) -> str:
    """The phone's country: a button over a search box + list; it comes set already (US on 4 of 4
    US postings, 2026-10-03) - then left as it is."""
    button = page.get_by_role("combobox", name="Country code").first
    if not button.count():
        return f"{LATER} on another page of the form"
    want = str(value).strip()
    if country_shown(button).casefold() == want.casefold():
        return "ok"
    button.focus()
    button.press("Enter")  # opens the list (a pointer click never reached it)
    search = page.get_by_role("combobox", name="Search by country/region or code").first
    search.fill(want, timeout=5000)
    chosen, labels = choose(page, button, want)
    if chosen is None:
        search.press("Escape")
        return f"ASK no country '{want}' on the list ({offered(labels)}) - pick it by hand"
    shown = country_shown(button)
    return "ok" if shown.casefold() == chosen.casefold() else f"FAIL country shows '{shown}'"


def fill(page, q: dict, resume_file: str | None) -> str:
    if q["id"] == RESUME:
        return put_file(page, resume_file) if q["answer"] is True and resume_file else "skipped - upload not approved"
    if q["id"] == COUNTRY:
        return put_country(page, q["answer"])
    if q["kind"] == "location":
        return put_city(page, q)
    return dom.fill(page, q, resume_file, later=True)
