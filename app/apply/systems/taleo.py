"""Oracle Taleo career sections (<tenant>.taleo.net/careersection/<section>/jobapply.ftl?job=<id>): each
step of the signed-in application read off the user's tab, answers typed into its boxes, the resume
attached and ticked as the one Resume / CV, work history + education on the step that holds them made to
match the resume.

No public form definition: the steps show only after the user accepts the employer's privacy agreement
and signs in (their own account, never typed by us). One page per step (Attachments, About You,
Education and Experience, Job Profile Questions, eSignature, Review and Submit); the user clicks Save
and Continue on each - never us. Measured on one tenant, one application, 2026-10-12 - read through the
Claude Chrome extension while the user applied, never saved as a page; what wasn't seen is marked
unmeasured. Facts and why each rule exists: app/docs/apply/taleo.md.
"""
import contextlib
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from apply import answers, browser, dom
from apply.questions import (asks_complete_history, degree_option, form_roles, key_from_title, left_on_page, LATER,
                             question, signs)
from resume import schema

NAME = "Taleo"
HOST = re.compile(r"[a-z0-9-]+\.taleo\.net", re.I)
# the posting's apply link; jobdetail.ftl is its posting page on Taleo's own job search (unmeasured: the
# measured employer showed postings on its own careers site, Apply pointing here)
PATH = re.compile(r"/careersection/([^/]+)/(?:jobapply|jobdetail)\.ftl$", re.I)
# the steps after the first Save and Continue: one address for every step and every job (measured)
FLOW = "/careersection/careersection/candidateacquisition/flow.jsf"
# freehire `source` whose links land here (test_systems_live.py): 50 of the newest 50 US, 17 tenants
# (2026-10-12). Some employers are listed under their own careers site instead (radancy), whose Apply
# leads here (apply/careers_page.py)
SOURCES = ("taleo",)
EXAMPLES = ("https://acme.taleo.net/careersection/10000/jobapply.ftl?job=246810",
            "https://acme.taleo.net/careersection/100/jobdetail.ftl?job=12345&lang=en")
PER_PAGE = True
# the resume goes to the employer when it is attached (Attach, after the user's yes) - before Submit
FILE_ON_CHOICE = True
READY = "input:not([type=hidden]), select, textarea"
UNMEASURED = "unmeasured step - check every box"
# document.title of each step (measured); the step names the page each question is on
ATTACHMENTS, ABOUT, HISTORY, QUESTIONS, SIGNATURE, REVIEW = (
    "Attachments", "About You", "Education and Experience", "Job Profile Questions", "eSignature", "Review and Submit")
PRIVACY = "Privacy Agreement"
DONE = re.compile(r"Process completed", re.I)
APPLYING = re.compile(r"Applying for:\s*(.+?)\s*\(Job Number:\s*([\w-]+)\)", re.I)
# Taleo's own marks inside a label (read as text: "First Name . Required", "Area of Study Limit answer to
# 50 characters . Required", "... [COI1A]", "1. Please indicate ... (EDU05)"). Required = a dot, then the
# word; the dot sits on the word before when no space came between
REQUIRED = re.compile(r"\s*\.\s*Required(?=\s|$)|\s+Required$")
LIMIT = re.compile(r"\s*Limit answer to (\d+) characters\s*", re.I)
HINTS = re.compile(r"\s*Choose all applicable fields\s*", re.I)
CODE = re.compile(r"\s*[\[(][A-Z]{2,6}\d{1,4}[A-Z]?[\])]\s*$")
NUMBER = re.compile(r"^\d{1,3}\.\s+")
# a select's empty pick, never an answer (measured: Source Type, phone type, opt-ins, Yes/No questions,
# Month / Year of each job)
PLACEHOLDERS = {"Select One...", "Not Specified", "Month", "Year", "Select"}
BUTTONS = ("button", "submit", "reset", "image")
FULL_LEGAL_NAME = re.compile(r"\bfull legal name\b", re.I)
LEGAL = {"First Name": "legal_first", "Middle Name": "legal_middle", "Last Name": "legal_last"}
# About You's contact boxes are plain text boxes - no type or autocomplete to go by (measured) - so known
# by their words: (kind, key). The resume's phone goes in the cell box, its hint's shape (xxx-xxx-xxxx)
CONTACT = {"Email Address": ("email", "email"), "Cellular Number xxx-xxx-xxxx": ("phone", "phone"),
           "Street Address (line 1)": ("text", "street"), "City": ("text", "city"), "Zip/Postal Code": ("text", "zip"),
           "State/Province": (None, "state")}
RESUME = "taleo-resume"
PROFILE = "taleo-history"
WORK, SCHOOL, LICENCE = "Current Job", "Name of Educational Institution", "Licensure/Certification"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
LEGAL_ENDINGS = {"inc", "llc", "ltd", "corp", "corporation", "co", "company", "lp", "llp", "plc", "pllc"}
ATTACH_WAIT, ADD_WAIT = 30, 30
# Attachments: "Each file must not exceed 1024 kilobytes" above the box, "You cannot attach a file that
# exceeds the allocated limit of 2048 kilobytes" in its help (both on one page, measured): the smaller wins
SIZE_LIMIT = re.compile(r"(?:must not exceed|limit of)\s+([\d,]+)\s*kilobytes", re.I)
MAX_FILES = re.compile(r"(?:attach up to|maximum of)\s+(\d+)\s+(?:documents|files)", re.I)

# a radio / checkbox set's question: Taleo names neither with a legend nor an aria label (its JSF id is
# the only name) - the words in the smallest block holding the set and no other box, its options' own
# labels taken out. A box with no label of its own the same way (unmeasured whether Taleo has one).
# Runs with dom's LIB, so hooks match dom.snapshot's
TITLES = """() => { %s
  const groupText = c => { const ms = c.members;
    for (let a = ms[0].parentElement; a && a !== document.body; a = a.parentElement) {
      if (!ms.every(m => a.contains(m))) continue;
      if ([...a.querySelectorAll('input:not([type=hidden]), select, textarea')]
          .some(e => !ms.includes(e) && !/^(button|submit|reset|image)$/.test(e.type))) return '';
      const k = a.cloneNode(true);
      for (const m of ms) if (m.id) for (const l of k.querySelectorAll(`label[for="${CSS.escape(m.id)}"]`)) l.remove();
      const t = textOf(k);
      if (t.replace(/(^|\\s)\\.?\\s*Required(\\s|$)/g, ' ').trim()) return t; }
    return ''; };
  const cs = controls(), hs = hooks(cs);
  // a set, or a box with no label of its own (its name only): the words around it
  return cs.map((c, i) => { const raw = labelOf(c), e = first(c);
    return {hook: hs[i], raw, group: c.kind === 'radio' || c.kind === 'checkboxes' || !raw || raw === e.name ? groupText(c) : ''}; }); }"""

# Attachments: one row per file on the account, its two ticks by their id endings (measured:
# <block>:<n>:selectionid = Relevant Files, <block>:<n>:resumeselectionid = Resume / CV)
ROWS = """() => [...document.querySelectorAll('input[type=checkbox][id$=":resumeselectionid"]')].map(r => {
  const base = r.id.slice(0, -':resumeselectionid'.length), rel = document.getElementById(base + ':selectionid');
  const tr = r.closest('tr'), cells = tr ? [...tr.cells].map(td => (td.innerText || '').trim()) : [];
  return {id: r.id, rel: rel ? rel.id : '', name: cells.find(t => /\\.[A-Za-z0-9]{2,5}$/.test(t)) || '',
    date: cells.find(t => /^\\d{1,2}\\/\\d{1,2}\\/\\d{2,4}$/.test(t)) || '', resume: r.checked, relevant: !!(rel && rel.checked)}; })"""

# Education and Experience: every shown box in page order with its own label (label[for], measured on each)
BOXES = """() => [...document.querySelectorAll('input:not([type=hidden]), select, textarea')]
  .filter(e => !/^(button|submit|reset|image)$/.test(e.type) && (e.checkVisibility ? e.checkVisibility() : e.getClientRects().length))
  .map(e => { const l = e.id && document.querySelector(`label[for="${CSS.escape(e.id)}"]`);
    return {id: e.id, tag: e.tagName.toLowerCase(), type: e.type || '', label: l ? (l.innerText || l.textContent || '') : '',
      value: e.tagName === 'SELECT' ? (e.selectedIndex < 0 ? '' : e.options[e.selectedIndex].text.trim()) : (e.value || ''),
      checked: !!e.checked, options: e.tagName === 'SELECT' ? [...e.options].map(o => o.text.trim()) : []}; })"""

# a page control by its exact words (Attach, Add Work Experience, Add Education): links, buttons and
# button inputs all measured as clickable by script; the first shown one wins
CLICK = """(words) => { const norm = s => (s || '').replace(/\\s+/g, ' ').trim();
  const e = [...document.querySelectorAll('a, button, input[type=button], input[type=submit]')]
    .find(x => [x.innerText, x.value, x.title].some(t => norm(t) === words) && x.getClientRects().length);
  if (!e) return false; e.click(); return true; }"""


def parse_url(url: str) -> tuple[str, str, str]:
    """(host, career section, job id)."""
    u = urlsplit(url.strip())
    m = PATH.match(u.path)
    job = (parse_qs(u.query).get("job") or [""])[0]
    if u.scheme not in ("http", "https") or not u.hostname or not HOST.fullmatch(u.hostname) or not m or not job:
        raise ValueError(f"not a Taleo posting link: {url}")
    return u.hostname.casefold(), m.group(1), job


def matches(url: str) -> bool:
    try:
        parse_url(url)
    except ValueError:
        return False
    return True


def application_url(url: str) -> str:
    host, section, job = parse_url(url)
    return f"https://{host}/careersection/{section}/jobapply.ftl?job={job}"


def on_tab(url: str, tab_url: str) -> bool:
    """This job's apply link, or the steps after it: those share one address for every job on the site
    (flow.jsf, measured), so a second application open on the same site can't be told apart by address -
    read prints the page's own "Job Number" to check it."""
    host, _, job = parse_url(url)
    tab = urlsplit(tab_url)
    if (tab.hostname or "").casefold() != host:
        return False
    if tab.path == FLOW:
        return True
    try:
        return parse_url(tab_url)[2] == job
    except ValueError:
        return False


def clean(raw: str) -> tuple[str, bool, int | None]:
    """A label as Taleo writes it -> (question words, required, most characters the box takes)."""
    text = " ".join(raw.split())
    required = bool(REQUIRED.search(text))
    text = REQUIRED.sub(" ", text)
    limit = LIMIT.search(text)
    text = " ".join(HINTS.sub(" ", LIMIT.sub(" ", text)).split())
    text = NUMBER.sub("", CODE.sub("", text)).strip()
    return text, required, int(limit.group(1)) if limit else None


def step(page) -> str:
    return " ".join((page.title() or "").split())


def titles(page) -> dict[str, tuple[str, bool, int | None]]:
    """hook -> cleaned (words, required, max characters) for every control on the page."""
    return {t["hook"]: clean(t["group"] or t["raw"]) for t in page.evaluate(TITLES % dom.lib())}


def body(page) -> str:
    with contextlib.suppress(Exception):
        return page.locator("body").inner_text(timeout=5000)
    return ""


def boxes_from(snap: dict, named: dict, on: str, skip=lambda title: False, legal: bool = False) -> list[dict]:
    """Questions off the step. `legal`: the step says "Please provide full legal name" above its name boxes
    (About You, measured) - the words sit outside each label, so its First / Middle / Last are the legal ones."""
    out = []
    for c in snap["controls"]:
        if c["password"] or c["type"] in BUTTONS or not (c["visible"] or c["control"] in ("radio", "checkbox", "checkboxes")):
            continue
        title, required, most = named.get(c["hook"]) or clean(c["label"])
        if skip(title):
            continue
        options = [o for o in c["options"] if o not in PLACEHOLDERS]
        kind = dom.kind_of(c | {"options": options, "label": title})
        known, key = CONTACT.get(title, (None, None))
        kind = known if known and c["control"] == "input" else kind
        key = key or (LEGAL.get(title) if legal else None) or key_from_title(title, kind)
        out.append(question(c["hook"], title, kind, required or c["required"], options, key,
                            f"dom:{c['tag']}:{c['type'] or c['control']}", page=on,
                            max_chars=most if kind in ("text", "longtext") else None))
    return out


def history_box(title: str) -> bool:
    """The boxes of each job, school and licence entry: matched to the resume as one step (PROFILE)."""
    return title in {WORK, "Employer", "Job Title", "Month", "Year", SCHOOL, "Area of Study", "Education Level",
                     "Education Level Completed?", LICENCE, "Number/ID", "Issuing Organization", "Country",
                     "State/Province", "Nearest Metropolitan Area/City"}


def read(page) -> list[dict]:
    """The step the user is on. Before the steps (privacy agreement, sign-in) and after them (review,
    confirmation) nothing is the program's to fill: said, and prepare stops or reads nothing."""
    on, text = step(page), body(page)
    if DONE.search(text):
        raise SystemExit("Taleo says the application is sent (\"Process completed\") - nothing to fill; "
                         "record it: status set <job> applied")
    if on == PRIVACY:
        raise SystemExit("Taleo shows the employer's privacy agreement first: the user reads and accepts it, then signs "
                         "in or creates an account there (never typed for them), then run prepare again")
    snap = dom.snapshot(page)
    if any(c["password"] and c["visible"] for c in snap["controls"]):
        raise SystemExit(f"Taleo shows its sign-in page: {dom.sign_in_email(page)}the user types the password and signs "
                         "in or creates an account there (a password is never typed for them), then run prepare again")
    if m := APPLYING.search(text):
        print(f"{NAME}: this tab is applying for '{m.group(1)}', Job Number {m.group(2)} - check it is this job")
    if on == SIGNATURE:
        print("  the applicant's own step: read the statement, type your full name in its box yourself (your "
              "signature), then click Save and Continue yourself")
        return []
    if on == REVIEW:
        print("  the applicant's own step: check every step on this page, then click Submit yourself")
        return []
    named = titles(page)
    if on == ATTACHMENTS:
        # the file box, its comment and the two ticks per row: one step, the resume attached and ticked
        return [question(RESUME, "Resume (attached, then ticked as your Resume / CV)", "file", False, key="resume",
                         native="taleo:attach", page=on)]
    if on == HISTORY:
        rest = boxes_from(snap, named, on, skip=history_box)
        return [question(PROFILE, "Make work history and education here match the resume (fixes names and dates "
                         "on entries that match, adds missing ones; Taleo keeps them on the user's account there "
                         "once Save and Continue is clicked)", "yesno", False, ["Yes", "No"], native="taleo:history",
                         page=on)] + rest
    if on not in (ABOUT, QUESTIONS):
        print(f"{NAME}: {UNMEASURED} - '{on}' is read as plain boxes")
    for s in dom.user_steps(snap):
        print(f"  the applicant's own step: {s}")
    return boxes_from(snap, named, on, legal=bool(FULL_LEGAL_NAME.search(text)))


def questions(url: str) -> list[dict]:
    with browser.page_at(application_url(url), match=lambda tab: on_tab(url, tab)) as page:
        page.locator(READY).first.wait_for(timeout=30000)
        return read(page)


def ids_on_page(page) -> list[str]:
    on = step(page)
    if on in (SIGNATURE, REVIEW, PRIVACY):
        return []
    if on == ATTACHMENTS:
        return [RESUME]
    snap, named = dom.snapshot(page), titles(page)
    rest = [q["id"] for q in boxes_from(snap, named, on, skip=history_box if on == HISTORY else lambda t: False)]
    return ([PROFILE] if on == HISTORY else []) + rest


# --- the resume on Attachments ---

def rows(page) -> list[dict]:
    return page.evaluate(ROWS)


def tick(page, id: str, on: bool) -> None:
    box = page.locator(f'[id="{id}"]')
    if box.is_checked() != on:
        box.evaluate("e => e.click()")


def today_shown(today=None) -> set[str]:
    """Today as the Date column may write it: 10/12/26 measured; 10/12/2026 not seen."""
    d = today or date.today()
    return {f"{d.month}/{d.day}/{d.year % 100:02d}", f"{d.month:02d}/{d.day:02d}/{d.year % 100:02d}",
            f"{d.month}/{d.day}/{d.year}", f"{d.month:02d}/{d.day:02d}/{d.year}"}


def wait_rows(page, before: set[str], wait: float = ATTACH_WAIT) -> list[dict]:
    """Rows once a new one shows - Attach reloads the step (measured), so reads mid-load are retried."""
    end = time.monotonic() + wait
    while time.monotonic() < end:
        with contextlib.suppress(Exception):
            got = rows(page)
            if {r["id"] for r in got} - before:
                return got
        page.wait_for_timeout(500)
    with contextlib.suppress(Exception):
        page.wait_for_load_state("load", timeout=5000)
    return rows(page)


def put_attach(page, path: str) -> str:
    """Attach the tailored PDF, then tick it as Relevant + Resume / CV and untick Resume / CV on every
    other row. Files from earlier applications stay on the account (measured: one from 2022, ticked as the
    resume); an older copy with this file's name is an earlier job's resume - unticked both ways."""
    name, text = Path(path).name, body(page)
    limits = [int(n.replace(",", "")) for n in SIZE_LIMIT.findall(text)]
    size_kb = Path(path).stat().st_size / 1024
    if limits and size_kb > min(limits):
        return f"FAIL the resume is {size_kb:.0f} KB; this page takes files up to {min(limits)} KB"
    have = rows(page)
    new = next((r for r in have if r["name"] == name and r["date"] in today_shown()), None)
    if new is None:
        most = MAX_FILES.search(text)
        if most and len(have) >= int(most.group(1)):
            return (f"FAIL Taleo keeps at most {most.group(1)} files and {len(have)} are on the account - the user "
                    "deletes an old one on the page (its Delete), then fill again")
        box = page.locator("input[type=file]").first
        if not box.count():
            return "ASK no file box on this page - attach the resume by hand"
        box.set_input_files(path)
        if not page.evaluate(CLICK, "Attach"):
            return "ASK the file is chosen but no Attach button was found - click Attach yourself"
        before = {r["id"] for r in have}
        got = wait_rows(page, before)
        added = [r for r in got if r["id"] not in before]
        new = next((r for r in added if r["name"] == name), None)
        if new is None:
            words = next((line for line in body(page).splitlines() if re.search(r"error|cannot|exceed|invalid", line, re.I)), "")
            return (f"FAIL the page says '{words.strip()[:160]}'" if words else
                    "ASK the resume didn't show in the attached list - check the page, attach it by hand")
        have = got
    others = []
    for r in have:
        if r["id"] == new["id"]:
            tick(page, r["id"], True)
            if r["rel"]:
                tick(page, r["rel"], True)
            continue
        tick(page, r["id"], False)
        if r["name"] == name and r["rel"]:
            tick(page, r["rel"], False)
        elif r["relevant"]:
            others.append(r["name"])
    now = {r["id"]: r for r in rows(page)}
    mine = now.get(new["id"])
    if not mine or not mine["resume"] or (mine["rel"] and not mine["relevant"]):
        return "FAIL the resume is attached but not ticked as Resume / CV - tick it on the page"
    if wrong := [r["name"] for r in now.values() if r["id"] != new["id"] and r["resume"]]:
        return f"FAIL another file still ticked as Resume / CV ({wrong[0]}) - untick it on the page"
    if others:
        return (f"ASK also ticked as Relevant from earlier: {', '.join(others)} - those go with this application "
                "too; untick Relevant Files on the page if they shouldn't")
    return "ok"


# --- work history + education on Education and Experience ---

def company_key(name: str) -> str:
    words = re.findall(r"[a-z0-9]+", name.casefold())
    while words and words[-1] in LEGAL_ENDINGS:
        words.pop()
    return " ".join(words[1:] if words[:1] == ["the"] else words)


def plain(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", re.sub(r"\(.*?\)", " ", text.casefold())))


def entries(page) -> list[dict]:
    """Each job, school and licence block in page order: {kind, boxes: {label: box}, months, years}.
    A block starts at its first box (Current Job, Name of Educational Institution, Licensure/Certification -
    measured order); Month / Year come start first, then end."""
    out, cur = [], None
    for b in page.evaluate(BOXES):
        label = clean(b["label"])[0]
        if label in (WORK, SCHOOL, LICENCE):
            cur = {"kind": {WORK: "work", SCHOOL: "school", LICENCE: "licence"}[label], "boxes": {}, "months": [], "years": []}
            out.append(cur)
        if cur is None:
            continue
        if label == "Month":
            cur["months"].append(b)
        elif label == "Year":
            cur["years"].append(b)
        elif label not in cur["boxes"]:
            cur["boxes"][label] = b
    return out


def value(e: dict, label: str) -> str:
    b = e["boxes"].get(label)
    return "" if not b else b["value"] if b["value"] not in PLACEHOLDERS else ""


def empty(e: dict) -> bool:
    return not any(value(e, k) for k in e["boxes"] if k != WORK) and \
        not any(b["value"] and b["value"] not in PLACEHOLDERS for b in e["months"] + e["years"])


def set_box(page, b: dict | None, want: str) -> str | None:
    """One box to `want` -> None when it took, else why. Text: typed + change + blur (Taleo reads on change);
    a list: the option with that exact text."""
    if b is None:
        return "box not on page"
    box = page.locator(f'[id="{b["id"]}"]')
    if b["tag"] == "select":
        if want not in b["options"]:
            return f"no option '{want}'"
        if b["value"] != want:
            box.select_option(label=want)
        return None if box.evaluate("e => e.options[e.selectedIndex].text.trim()") == want else "didn't take"
    if b["value"] != want:
        box.fill(want)
        box.evaluate("e => { e.dispatchEvent(new Event('change', {bubbles: true})); e.blur(); }")
    return None if box.input_value() == want else "didn't take"


def month_year(when: str | None) -> tuple[str, str] | None:
    if not when or str(when).casefold() == "present":
        return None
    year, _, month = str(when).partition("-")
    return (MONTHS[int(month) - 1] if month else "", year)


def role_wants(role: dict) -> dict:
    current = str(role.get("end") or "").casefold() == "present"
    return {"Employer": role["company"], "Job Title": role["title"], "current": current,
            "start": month_year(role.get("start")), "end": None if current else month_year(role.get("end"))}


def role_differs(e: dict, want: dict) -> bool:
    current = e["boxes"].get(WORK)
    dates = [("start", 0), ("end", 1)]
    return (value(e, "Employer") != want["Employer"] or value(e, "Job Title") != want["Job Title"]
            or bool(current and current["checked"]) != want["current"]
            or any(want[side] and (len(e["months"]) <= i or len(e["years"]) <= i
                                   or (want[side][0] and e["months"][i]["value"] != want[side][0])
                                   or e["years"][i]["value"] != want[side][1]) for side, i in dates))


def put_role(page, e: dict, want: dict) -> list[str]:
    bad = []
    for label in ("Employer", "Job Title"):
        if why := set_box(page, e["boxes"].get(label), want[label]):
            bad.append(f"{label}: {why}")
    if box := e["boxes"].get(WORK):
        tick(page, box["id"], want["current"])
    for side, i in (("start", 0), ("end", 1)):
        if not want[side]:
            continue
        month, year = want[side]
        if not month:
            bad.append(f"{side} month not on the resume - pick it on the page")
        elif why := set_box(page, e["months"][i] if len(e["months"]) > i else None, month):
            bad.append(f"{side} month: {why}")
        if why := set_box(page, e["years"][i] if len(e["years"]) > i else None, year):
            bad.append(f"{side} year: {why}")
    return bad


def pair(found: list[tuple[str, str]], wanted: list[tuple[str, str]], blank: list[bool]) -> tuple[dict, list]:
    """Each wanted (name, title) -> index of the page's entry for it: same name + title; else the one left
    with that name when only one is left on each side; else a blank entry, in order. -> (pairs, page
    entries left over). Unpaired wanted ones get added."""
    taken, out = set(), {}
    for i, w in enumerate(wanted):
        hit = next((j for j, f in enumerate(found) if j not in taken and f == w), None)
        if hit is not None:
            taken.add(hit)
            out[i] = hit
    for i, (name, _) in enumerate(wanted):
        if i in out:
            continue
        same = [j for j, f in enumerate(found) if j not in taken and f[0] == name]
        if len(same) == 1 and sum(1 for k, v in enumerate(wanted) if k not in out and v[0] == name) == 1:
            taken.add(same[0])
            out[i] = same[0]
    blanks = [j for j in range(len(found)) if j not in taken and blank[j]]
    for i in range(len(wanted)):
        if i not in out and blanks:
            out[i] = blanks.pop(0)
            taken.add(out[i])
    return out, [j for j in range(len(found)) if j not in taken]


def add_entry(page, words: str, kind: str) -> dict | None:
    """Click the page's own Add button, wait for the new blank block (the step reloads, measured: what was
    typed before it stays) -> that block, or None."""
    before = sum(1 for e in entries(page) if e["kind"] == kind)
    if not page.evaluate(CLICK, words):
        return None
    end = time.monotonic() + ADD_WAIT
    while time.monotonic() < end:
        page.wait_for_timeout(500)
        with contextlib.suppress(Exception):
            got = [e for e in entries(page) if e["kind"] == kind]
            if len(got) > before:
                return got[-1]
    return None


def school_wants(school: dict, options: list[str]) -> dict:
    return {"Area of Study": school.get("field") or "",
            "Education Level": degree_option(school.get("degree") or "", [o for o in options if o not in PLACEHOLDERS]),
            "Education Level Completed?": "No" if schema.in_progress(school, date.today()) else "Yes"}


def work_pairs(work: list[dict], wants: list[dict]) -> tuple[dict, list]:
    return pair([(company_key(value(e, "Employer")), plain(value(e, "Job Title"))) for e in work],
                [(company_key(w["Employer"]), plain(w["Job Title"])) for w in wants], [empty(e) for e in work])


def school_pairs(mine: list[dict], schools: list[dict]) -> tuple[dict, list]:
    return pair([(plain(value(e, SCHOOL)), "") for e in mine], [(plain(s.get("institution") or ""), "") for s in schools],
                [empty(e) for e in mine])


def put_school(page, e: dict, school: dict, fresh: bool) -> list[str]:
    bad = []
    if fresh and (why := set_box(page, e["boxes"].get(SCHOOL), school["institution"])):
        bad.append(f"school: {why}")
    level = e["boxes"].get("Education Level")
    want = school_wants(school, level["options"] if level else [])
    field_box = e["boxes"].get("Area of Study")
    most = clean(field_box["label"])[2] if field_box else None
    if want["Area of Study"] and most and len(want["Area of Study"]) > most:
        bad.append(f"area of study '{want['Area of Study']}' is longer than its {most}-character box - shorten it on the page")
    elif want["Area of Study"] and (why := set_box(page, field_box, want["Area of Study"])):
        bad.append(f"area of study: {why}")
    if not want["Education Level"]:
        bad.append(f"degree '{school.get('degree')}' not in its list - pick it on the page")
    elif why := set_box(page, level, want["Education Level"]):
        bad.append(f"education level: {why}")
    if why := set_box(page, e["boxes"].get("Education Level Completed?"), want["Education Level Completed?"]):
        bad.append(f"completed: {why}")
    return bad


def school_differs(e: dict, school: dict) -> bool:
    level = e["boxes"].get("Education Level")
    want = school_wants(school, level["options"] if level else [])
    return any(w and value(e, k) != w for k, w in want.items())


def resume_facts(resume_file: str | None) -> tuple[dict, dict]:
    from apply.systems import ukg
    return ukg.resume_facts(resume_file)


def plan(page, resume_file: str | None) -> tuple[list, list, list, list, str | None]:
    """(jobs, their page blocks, schools, theirs, note) - what the step should hold, read fresh."""
    master, tailored = resume_facts(resume_file)
    roles, note = form_roles(master, tailored, asks_complete_history(body(page)))
    found = entries(page)
    return roles, found, master.get("education") or [], master.get("certifications") or [], note


def put_history(page, resume_file: str | None) -> str:
    roles, found, schools, certs, note = plan(page, resume_file)
    if note and note.startswith("ASK"):
        return note
    report = []
    work = [e for e in found if e["kind"] == "work"]
    wants = [role_wants(r) for r in roles]
    by, extra = work_pairs(work, wants)
    for i, want in enumerate(wants):
        if i in by:
            e = work[by[i]]
            if role_differs(e, want):
                bad = put_role(page, e, want)
                report.append(f"{want['Job Title']}, {want['Employer']}: " + ("; ".join(bad) or "fixed"))
    for i, want in enumerate(wants):
        if i in by:
            continue
        e = add_entry(page, "Add Work Experience", "work")
        if e is None:
            report.append(f"{want['Job Title']}, {want['Employer']}: ASK couldn't add it - Add Work Experience on the page")
            continue
        bad = put_role(page, e, want)
        report.append(f"{want['Job Title']}, {want['Employer']}: " + ("; ".join(bad) or "added"))
    for j in extra:
        e = work[j]
        if not empty(e):
            report.append(f"ASK on the account, not on this resume: {value(e, 'Job Title')}, {value(e, 'Employer')} - "
                          "left as is; remove it on the page if it shouldn't go")
    found = entries(page)  # after any Add the step reloaded
    mine = [e for e in found if e["kind"] == "school"]
    sby, sextra = school_pairs(mine, schools)
    for i, school in enumerate(schools):
        fresh = i not in sby
        e = mine[sby[i]] if not fresh else add_entry(page, "Add Education", "school")
        if e is None:
            report.append(f"{school['institution']}: ASK couldn't add it - Add Education on the page")
            continue
        if fresh or school_differs(e, school):
            bad = put_school(page, e, school, fresh)
            report.append(f"{school['institution']}: " + ("; ".join(bad) or ("added - check its other boxes" if fresh else "fixed")))
    for j in sextra:
        if not empty(mine[j]):
            report.append(f"ASK on the account, not on this resume: {value(mine[j], SCHOOL)} - left as is")
    if certs:
        report.append(f"ASK {len(certs)} licence(s) or certification(s) on the resume - add each on the page "
                      "(Add Licensure/Certification); not filled by the program yet")
    if note:
        report.append(note)
    asks = [r for r in report if r.startswith("ASK") or ": ASK" in r or "didn't take" in r or "no option" in r
            or "pick it" in r or "shorten" in r or "check its" in r]
    return ("ASK " if asks else "ok - ") + ("; ".join(report) or "already matches the resume")


def holds_history(page, resume_file: str | None) -> bool:
    """Every resume job and school on the step, as the resume says it."""
    roles, found, schools, _, note = plan(page, resume_file)
    if note and note.startswith("ASK"):
        return False
    work = [e for e in found if e["kind"] == "work"]
    wants = [role_wants(r) for r in roles]
    by, _ = work_pairs(work, wants)
    if len(by) < len(wants) or any(role_differs(work[by[i]], w) for i, w in enumerate(wants)):
        return False
    mine = [e for e in found if e["kind"] == "school"]
    sby, _ = school_pairs(mine, schools)
    return len(sby) == len(schools) and not any(school_differs(mine[sby[i]], s) for i, s in enumerate(schools))


# --- every other box: dom's filler, the label checked as Taleo words it ---

def found_box(page, q: dict) -> tuple[dict | None, str | None]:
    """(the control as dom reads it, why not) - still the same question by Taleo's words, cleaned: dom's own
    check reads the raw label ("First Name . Required", a radio set's JSF name), so it is told it's done."""
    snap = dom.snapshot(page)
    c = next((c for c in snap["controls"] if c["hook"] == q["id"]), None)
    if c is None:
        return None, f"{LATER} on another step of the form"
    words = (titles(page).get(q["id"]) or clean(c["label"]))[0]
    if answers.fold(words) != answers.fold(q["title"]):
        return None, f"FAIL box label changed ('{words}') - read the page again"
    return c, None


# the resume fill was given: form.recheck reads holds(page, q) back without it, and the jobs a form gets
# depend on the tailored page beside it (questions.form_roles)
FILLED_WITH: dict[str, str | None] = {}


def holds(page, q: dict) -> bool:
    if q["native"] == "taleo:history":
        return not dom.yes(q["answer"]) or (step(page) == HISTORY and holds_history(page, FILLED_WITH.get("resume")))
    if q["native"] == "taleo:attach":  # one file ticked as Resume / CV, this one
        name = Path(FILLED_WITH.get("resume") or "").name
        ticked = [r for r in rows(page) if r["resume"]] if step(page) == ATTACHMENTS else []
        return len(ticked) == 1 and ticked[0]["name"] == name
    c, _ = found_box(page, q)
    return c is not None and dom.holds(page, q, worded=True)


def fill(page, q: dict, resume_file: str | None) -> str:
    FILLED_WITH["resume"] = resume_file
    if q["native"] == "taleo:attach":
        if step(page) != ATTACHMENTS:
            return f"{LATER} on the Attachments step"
        return put_attach(page, resume_file) if q["answer"] is True and resume_file else "skipped - upload not approved"
    if q["native"] == "taleo:history":
        if step(page) != HISTORY:
            return f"{LATER} on the Education and Experience step"
        return put_history(page, resume_file) if dom.yes(q["answer"]) else "skipped - user said no"
    if signs(q["title"]):
        return left_on_page(q)
    c, why = found_box(page, q)
    if c is None:
        return why
    if q["kind"] == "phone" and len(d := dom.digits(str(q["answer"])).removeprefix("1")) == 10:
        q = q | {"answer": f"{d[:3]}-{d[3:6]}-{d[6:]}"}
    return dom.fill(page, q, resume_file, later=True, worded=True)
