"""Workable (apply.workable.com): questions from its public form definition, answers typed into its widgets.

Measured facts and why each rule exists: app/docs/apply/workable.md.
"""
import contextlib
import re
import time
from pathlib import Path

import httpx

from apply import dom
from apply.questions import left_on_page, question, signs

NAME = "Workable"
# freehire serves the short /j/<code>?utm_source=freehire.me; the page itself moves to /<account>/j/<code>/
POSTING_URL = re.compile(r"https?://apply\.workable\.com/(?:(?!j/|api/)([\w-]+)/)?j/([0-9A-F]{6,16})"
                         r"(?:/apply)?/?(?:[?#].*)?$", re.I)
SOURCES = ("workable",)
# the short /j/ links carry no account to anonymise: tested in test_apply_workable.py
EXAMPLES = ("https://apply.workable.com/acme/j/1A2B3C4D5E/",
            "https://apply.workable.com/acme/j/1A2B3C4D5E?utm_source=freehire.me",
            "https://apply.workable.com/acme/j/1A2B3C4D5E/apply/")
# questions() is one plain GET of the form definition, no browser: the live test runs it
QUESTIONS_OVER_HTTP = True
FORM = "https://apply.workable.com/api/v1/jobs/{code}/form"
# the employer's public job list (shortcodes of what it has open), by the account the short link 301s to
SHORT = "https://apply.workable.com/j/{code}"
BOARD = "https://apply.workable.com/api/v1/widget/accounts/{account}"
READY = "input[name=firstname]"
# a chosen resume POSTs to Workable's storage at once, before Submit (workable.md)
FILE_ON_CHOICE = True
# employer question type -> shared kind (123 fields, 17 forms, 2026-10-03); a type missing here is asked as text
KIND = {"boolean": "yesno", "paragraph": "longtext", "text": "text", "number": "number", "date": "date",
        "dropdown": "choice", "file": "file"}
# Workable's own boxes, by id: (kind, key). headline / summary are the applicant's own words, no shared key
STANDARD = {"firstname": ("text", "first_name"), "lastname": ("text", "last_name"), "email": ("email", "email"),
            "phone": ("phone", "phone"), "address": ("location", "location"), "resume": ("file", "resume"),
            "cover_letter": ("longtext", "cover_letter"), "headline": ("text", None), "summary": ("longtext", None)}
# avatar = a photo (AGENTS.md: never), never required (6 of 6); education / experience = entries
# added by a click, never required (17 of 17), adding them unmeasured: neither is a question
SKIP = {"avatar", "education", "experience"}
# address prefilled from the requester's internet address on 16 of 16: never the user's answer
PREFILLED = "Address (the page fills this itself from your internet address - check it)"
# the address box's helpers, empty on load, never required (4 of 4): not questions
HELPERS = {"city", "postcode", "country"}
# headless Chrome reads an option icon's fallback text into its label (2026-10-03)
SVG = "SVGs not supported by this browser."
# a `multiple` option's [role=radio] holds no text, its words sit beside it (2026-10-03, 1 tenant): read the
# widest box around it that holds no other option
OPTION_TEXT = """e => { let b = e;
  while (b.parentElement && b.parentElement.querySelectorAll('[role=radio]').length === 1) b = b.parentElement;
  return (b.innerText || b.textContent || '').split(%r).join('').replace(/\\s+/g, ' ').trim(); }""" % SVG
# the resume's file input has a new random id every load and no name (4 of 4): found by the words
# around it - the nearest ancestor naming resume / CV or photo says which box it is
RESUME_INPUT = """() => [...document.querySelectorAll('input[type=file]')].findIndex(e => {
  for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) {
    const t = p.innerText || '';
    if (/\\bphoto\\b|avatar/i.test(t)) return false;
    if (/\\b(resume|r\u00e9sum\u00e9|cv)\\b/i.test(t)) return true;
  }
  return false; })"""
# radios: the input under each option only mirrors the pick - ticked by script it doesn't stay, its
# label isn't clickable (2026-10-03, every YES / NO on 1 page). The clickable part is the [role=radio]
# beside it in the question's fieldset (role=radiogroup), its pick in aria-checked (measure, 4 of 4)
OPTIONS = 'fieldset:has(input[name="{id}"]) [role=radio]'
# the resume box's words: its field = the child of `[data-ui=section-fields]` around the file input, which
# carries `data-ui="resume"` itself - no text of its own (live, writes blocked, 1 tenant, 2026-10-07; the
# 2026-10-06 reading of the script put it on a wrapper: every live read was empty -> ASK, plan-k8n.33). The
# input gone (the box may draw a new one): the field its label names resume / CV
RESUME_BOX = """() => { const fields = [...document.querySelectorAll('[data-ui="section-fields"] > *')];
  const input = document.querySelector('input[type=file][data-ui="resume"]');
  const w = (input && fields.find(f => f.contains(input)))
    || fields.find(f => /^[\\s*]*(resume|r\u00e9sum\u00e9|cv)\\b/i.test(f.innerText || ''));
  return w ? (w.innerText || '').replace(/\\s+/g, ' ').trim() : null; }"""
# what Workable's form script writes in the resume box when a file isn't kept (2026-10-06): too big
# (checked by the page before anything goes), the upload failed, a type it doesn't take
UPLOAD_ERRORS = re.compile(r"File is too big\.?|Something went wrong\. We are working on this, please try again later\."
                           r"|Please use a different file\.", re.I)
# the file's name shows only once Workable's storage has it (its script sets name + url together)
FILE_SHOWN = re.compile(r"\S\.(pdf|docx?|odt|rtf)\b", re.I)
IDLE_WAIT_MS, SHOWN_WAIT_MS, ERROR_WAIT_MS = 15000, 20000, 2000
# what a dropdown shows as its pick, read off its wrapper: a box's value or a line of text (which: unmeasured)
SHOWN = """w => [...new Set([...w.querySelectorAll('input, span, div')].filter(c => !c.closest('[role=listbox]')
  && (c.tagName === 'INPUT' || !c.children.length)).map(c => (c.value || c.innerText || '').trim()).filter(Boolean))]"""
# a person's ways to open a list: a click, Down on it focused, a click where it sits (whatever is on top
# takes it). Plain clicks timed out on 8 of 8 (2026-10-03) - something sits over the box
OPEN = (("click", lambda e: e.click(timeout=2000)), ("down", lambda e: (e.focus(), e.press("ArrowDown"))),
        ("click on top", lambda e: e.click(force=True, timeout=2000)))
# a person's ways to pick one, in order: a click, a click where it sits (whatever is on top takes it),
# Space on it focused - the first that ticks wins
CLICKS = (("click", lambda e: e.click(timeout=3000)), ("click on top", lambda e: e.click(force=True, timeout=3000)),
          ("space", lambda e: (e.focus(), e.press("Space"))))


def matches(url: str) -> bool:
    return bool(POSTING_URL.match(url.strip()))


def parse_url(url: str) -> tuple[str, str]:
    """(account or "", shortcode)."""
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not a Workable posting link: {url}")
    return m.group(1) or "", m.group(2).upper()


def application_url(url: str) -> str:
    # /j/<code>/apply 301s to the account's own path (5 of 5): no account needed
    account, code = parse_url(url)
    return f"https://apply.workable.com/{account + '/' if account else ''}j/{code}/apply/"


def from_definition(sections: list[dict]) -> list[dict]:
    out = []
    for section in sections:
        for f in section.get("fields") or []:
            id, type, label = f["id"], f.get("type"), " ".join((f.get("label") or "").split())
            if id in SKIP or type == "group":
                continue
            required = bool(f.get("required"))
            if id in STANDARD:
                kind, key = STANDARD[id]
                title = PREFILLED if id == "address" and f.get("prefilledByLocation") else label or id
                out.append(question(id, title, kind, required, key=key, native=id))
                continue
            options = [" ".join(str(o["value"]).split()) for o in f.get("options") or []]
            kind = KIND.get(type, "text")
            native = f"{id.split('_')[0]}:{type}"
            if type == "multiple":
                kind = "choice" if f.get("singleOption") else "multichoice"
                if kind == "multichoice":  # each tick's name is the option's own name, not the question id
                    native += ":" + ",".join(str(o["name"]) for o in f["options"])
            if kind == "choice" and sorted(options) == ["No", "Yes"]:
                kind = "yesno"
            out.append(question(id, label or id, kind, required, options, native=native))
    return out


def board_says(code: str) -> str:
    """The form read gives 404 for a closed posting and an unknown link alike (workable.md "Closed
    posting"): the short link still names the employer (301) or not (302 to /oops); the employer's own
    job list, read once, tells the rest - never a guess."""
    r = httpx.get(SHORT.format(code=code), timeout=30)
    m = re.match(r"(?:https://apply\.workable\.com)?/([\w-]+)/j/", r.headers.get("location") or "")
    if r.status_code not in (301, 302, 308) or not m:
        return "Workable no longer knows this posting - it may have closed"
    r = httpx.get(BOARD.format(account=m.group(1)), timeout=30)
    if r.status_code != 200:
        return f"can't tell if the posting is open - the employer's Workable job list answered {r.status_code}"
    if any(str(j.get("shortcode")).upper() == code for j in r.json().get("jobs") or []):
        return "can't tell if the posting is open - it is on the employer's Workable job list, but its form didn't load"
    return "the posting is no longer on the employer's Workable job list - it may have closed"


def questions(url: str) -> list[dict]:
    code = parse_url(url)[1]
    r = httpx.get(FORM.format(code=code), timeout=30)
    # unknown or taken down: 404 "Not Found" either way (48 links, 2026-10-06): the job list says which
    if r.status_code == 404:
        raise ValueError(board_says(code))
    r.raise_for_status()
    return from_definition(r.json())


def closed(url: str) -> str | None:
    """Why the form isn't there (form.closed, when the page shows no form): None = Workable still has it."""
    code = parse_url(url)[1]
    try:
        r = httpx.get(FORM.format(code=code), timeout=30)
        if r.status_code == 200:
            return None
        if r.status_code != 404:
            return f"can't tell if the posting is open - Workable answered {r.status_code}"
        return board_says(code)
    except httpx.HTTPError as e:
        return f"can't tell if the posting is open - Workable didn't answer ({type(e).__name__})"


def ids_on_page(page) -> list[str]:
    # ticks are named after their option, files carry no name: only boxes named after a question
    return page.eval_on_selector_all(
        "form input[name], form textarea[name], form select[name]",
        "(es, skip) => [...new Set(es.filter(e => !['hidden', 'checkbox', 'file'].includes(e.type)"
        " && !skip.includes(e.name)).map(e => e.name))]", sorted(HELPERS))


def by_name(page, name: str):
    return page.locator(f'form [name="{name}"]:not([type=hidden])')


def resume_says(page) -> tuple[str, str]:
    """(the resume box's words, its error in Workable's own words or "")."""
    words = page.evaluate(RESUME_BOX) or ""
    said = UPLOAD_ERRORS.search(words)
    return words, said.group() if said else ""


def put_file(page, path: str) -> str:
    """Page idle first (as Greenhouse, Ashby), then the file chosen - it goes to Workable's storage at
    once (workable.md). Ok = its name shows in the resume box and the page says nothing failed for
    ERROR_WAIT_MS after; the page's own error words -> FAIL; nothing either way -> ASK."""
    with contextlib.suppress(Exception):  # a page that keeps polling never goes idle: the read decides
        page.wait_for_load_state("networkidle", timeout=IDLE_WAIT_MS)
    i = page.evaluate(RESUME_INPUT)
    if i < 0:
        return "FAIL no resume box on page"
    # a file name already in the box (an earlier choose) -> only this file's own name says it took
    named = bool(FILE_SHOWN.search(resume_says(page)[0]))
    page.locator("input[type=file]").nth(i).set_input_files(path)
    name, since = Path(path).name, None
    deadline = time.monotonic() + SHOWN_WAIT_MS / 1000
    while time.monotonic() < deadline:
        words, said = resume_says(page)
        if said:
            return f"FAIL the page says '{said}' - choose the file again on the page, or check the resume box"
        # a name the box shortens still counts on an empty box (shown in full or not: unmeasured)
        if since is None and (name in words or not named and FILE_SHOWN.search(words)):
            since = time.monotonic()
        if since is not None and time.monotonic() - since >= ERROR_WAIT_MS / 1000:
            return "ok"
        page.wait_for_timeout(250)
    return "ASK upload not confirmed on page - check the resume box"


def holds(page, q: dict) -> bool:
    """The answer still shows, read off the page once the form had time to keep it (form.recheck), each
    kind as workable.md "Read back (2026-10)" records it: a box by its value (phone by digits), a radio
    question by the one [role=radio] ticked, ticks each by its own box, a dropdown by what its wrapper
    shows, the resume by a file name in its box and no error. Nothing to read = False."""
    kind, value, id = q["kind"], q["answer"], q["id"]
    if kind == "file":
        words, said = resume_says(page)
        return bool(FILE_SHOWN.search(words)) and not said
    if kind == "multichoice" and str(q.get("native")).count(":") >= 2:
        ticks = [by_name(page, n) for n in q["native"].split(":", 2)[2].split(",")]
        want = {dom.norm(str(v)).casefold() for v in (value if isinstance(value, list) else [value])}
        return all(t.count() for t in ticks) and all(
            (dom.norm(o).casefold() in want) == t.first.is_checked() for o, t in zip(q["options"], ticks))
    field = by_name(page, id)
    if not field.count():
        return False
    type = field.first.evaluate("e => e.tagName === 'SELECT' ? 'select' : e.getAttribute('role') === 'combobox' ? 'combobox' : e.type")
    pick = ("Yes" if dom.yes(value) else "No") if kind == "yesno" else str(value).strip()
    if type == "radio":
        on = [m.evaluate(OPTION_TEXT) for m in page.locator(OPTIONS.format(id=id)).all()
              if m.get_attribute("aria-checked") == "true"]
        return [n.casefold() for n in on] == [pick.casefold()]
    if type == "select":
        return dom.norm(field.first.evaluate("e => e.selectedOptions[0] ? e.selectedOptions[0].text : ''")).casefold() == pick.casefold()
    if type == "combobox" or kind in ("choice", "yesno"):
        wrap = page.locator(f'[data-ui="{id}"]')
        return bool(wrap.count()) and any(dom.norm(s).casefold() == pick.casefold() for s in wrap.first.evaluate(SHOWN))
    got = field.first.input_value()
    if kind == "phone":  # a dialling code the box adds in front is the page's, not a changed answer
        return bool(dom.digits(str(value))) and dom.digits(got).endswith(dom.digits(str(value)))
    return got == str(value)


def put_options(page, q: dict, value) -> str:
    """Radios (boolean YES / NO, single `multiple`) by the text on each option, case-insensitive."""
    members = page.locator(OPTIONS.format(id=q["id"])).all()
    if not members:
        return "FAIL question not on page"
    # an option's text can carry the question before it (its accessible name): the option is what follows
    names = [m.evaluate(OPTION_TEXT) for m in members]
    want = ("Yes" if dom.yes(value) else "No") if q["kind"] == "yesno" else str(value).strip()
    hit = next((i for i, n in enumerate(names) if n.casefold() == want.casefold()), None)
    if hit is None:
        return f"ASK no option '{want}'; offered: {', '.join(names)[:200]}"
    el, tried = members[hit], []
    for how, act in CLICKS:
        if el.get_attribute("aria-checked") == "true":
            return "ok"
        try:
            el.scroll_into_view_if_needed(timeout=3000)
            act(el)
            el.page.wait_for_timeout(150)
        except Exception as e:
            tried.append(f"{how}: {str(e).splitlines()[0][:80]}")
    if el.get_attribute("aria-checked") == "true":
        return "ok"
    return f"FAIL '{names[hit]}' didn't take ({'; '.join(tried) or 'no error, no tick'})"


def put_dropdown(page, id: str, value) -> str:
    """A `dropdown`: the box named after the question takes no typed value; the list opens from the
    [role=combobox] in the question's wrapper (2026-10-03, 8 of 8 on 1 page). Opened like a person
    would, the option that is the answer clicked - never the first offered."""
    want = str(value).strip()
    wrap = page.locator(f'[data-ui="{id}"]')
    box = wrap.locator("[role=combobox]").first
    if not box.count():
        return "FAIL question not on page"
    options, tried = page.locator("[role=option]:visible"), []
    for how, act in OPEN:
        try:
            act(box)
            options.first.wait_for(timeout=3000)
            break
        except Exception as e:
            tried.append(f"{how}: {str(e).splitlines()[0][:60]}")
    else:
        return f"FAIL list didn't open ({'; '.join(tried)})"
    texts = [dom.norm(t) for t in options.all_inner_texts()]
    hit = next((i for i, t in enumerate(texts) if t.casefold() == want.casefold()), None)
    if hit is None:
        page.keyboard.press("Escape")
        return f"ASK no option '{want}'; offered: {', '.join(texts)[:200]}"
    try:
        options.nth(hit).click(timeout=3000)
    except Exception:  # a click can be covered like the box's: the option's own handler takes a dispatched one
        options.nth(hit).dispatch_event("click")
    page.wait_for_timeout(200)
    shown = wrap.evaluate(SHOWN)
    return "ok" if any(texts[hit].casefold() == dom.norm(s).casefold() for s in shown) else \
        f"FAIL '{texts[hit]}' not shown (shows {shown[:3]})"


def put_ticks(page, q: dict, value) -> str:
    """Checkboxes named after each option (definition `options[].name`), never the question id."""
    names = q["native"].split(":", 2)[2].split(",")
    members = [by_name(page, n) for n in names]
    if not all(m.count() for m in members):
        return "FAIL question not on page"
    want = value if isinstance(value, list) else [value]
    return dom.put_ticks([m.first for m in members], q["options"], [str(v).strip() for v in want],
                         role=False, single=False)


def fill(page, q: dict, resume_file: str | None) -> str:
    kind, value, id = q["kind"], q["answer"], q["id"]
    if signs(q["title"]):
        return left_on_page(q)
    if kind == "file":
        if q.get("key") != "resume":
            return f"ASK not the resume box ({q['title']}) - the user uploads their own file there"
        return put_file(page, resume_file) if value is True and resume_file else "skipped - upload not approved"
    if kind == "multichoice" and str(q.get("native")).count(":") >= 2:
        return put_ticks(page, q, value)
    field = by_name(page, id)
    if not field.count():
        return "FAIL question not on page"
    type = field.first.evaluate("e => e.tagName === 'SELECT' ? 'select' : e.getAttribute('role') === 'combobox' ? 'combobox' : e.type")
    if type == "radio":
        return put_options(page, q, value)
    field = field.first
    field.scroll_into_view_if_needed()
    pick = ("Yes" if dom.yes(value) else "No") if kind == "yesno" else value
    if type == "select":
        return dom.put_select(field, pick)
    if type == "combobox" or kind in ("choice", "yesno"):
        return put_dropdown(page, id, pick)
    return dom.put_text(field, value, kind, editable=False)
