"""Workable (apply.workable.com): questions from its public form definition, answers typed into its widgets.

Measured facts and why each rule exists: app/docs/apply/workable.md.
"""
import re

import httpx

from apply import dom
from apply.questions import question, signs

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
READY = "input[name=firstname]"
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


def questions(url: str) -> list[dict]:
    r = httpx.get(FORM.format(code=parse_url(url)[1]), timeout=30)
    # an unknown shortcode: 404 "Not Found" (2026-10-03); a closed one: unmeasured
    if r.status_code == 404:
        raise ValueError("posting not found - it may have closed")
    r.raise_for_status()
    return from_definition(r.json())


def ids_on_page(page) -> list[str]:
    # ticks are named after their option, files carry no name: only boxes named after a question
    return page.eval_on_selector_all(
        "form input[name], form textarea[name], form select[name]",
        "(es, skip) => [...new Set(es.filter(e => !['hidden', 'checkbox', 'file'].includes(e.type)"
        " && !skip.includes(e.name)).map(e => e.name))]", sorted(HELPERS))


def by_name(page, name: str):
    return page.locator(f'form [name="{name}"]:not([type=hidden])')


def put_resume(page, path: str) -> str:
    i = page.evaluate(RESUME_INPUT)
    if i < 0:
        return "FAIL no resume box on page"
    return dom.put_file(page.locator("input[type=file]").nth(i), path)


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
        return "ASK yours to do on the page - agreeing, consenting or signing"
    if kind == "file":
        if q.get("key") != "resume":
            return f"ASK not the resume box ({q['title']}) - the user uploads their own file there"
        return put_resume(page, resume_file) if value is True and resume_file else "skipped - upload not approved"
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
