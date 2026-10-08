"""Breezy HR (<employer>.breezy.hr/p/<id>-<slug>): questions from the definition in the apply page itself, answers typed into it.

Measured facts and why each rule exists: app/docs/apply/breezy.md.
"""
import contextlib
import html
import json
import re
import time
from pathlib import Path

import httpx

from apply.questions import key_from_title, left_on_page, question, signs

NAME = "Breezy"
# one subdomain per employer; posting id = 12-14 hex, then the title slug; freehire adds ?utm_source=freehire.me
POSTING_URL = re.compile(r"https?://([\w-]+)\.breezy\.hr/p/([0-9a-f]{8,}(?:-[\w-]*)?)(?:/apply)?/?(?=[?#]|$)", re.I)
SOURCES = ("breezy",)
EXAMPLES = ("https://acme.breezy.hr/p/0a1b2c3d4e5f-software-engineer",
            "https://acme.breezy.hr/p/0a1b2c3d4e5f-software-engineer?utm_source=freehire.me",
            "https://acme.breezy.hr/p/0a1b2c3d4e5f-software-engineer/apply")
QUESTIONS_OVER_HTTP = True
# the resume goes to Breezy as soon as it is chosen, then Breezy reads it (portal.js onFileSelect)
FILE_ON_CHOICE = True
# the address box is Google Places: each letter goes to Google as it is typed
SEARCHED_AS_TYPED = ("location",)
SEARCHED_WITH = "Google"
FORM = "form[name=form]"
READY = f"{FORM} input[name=cName]"
CLOSED = "Position Closed"
# two page builds carry the same position JSON (9 of 9, 2026-10-07): Angular in an attribute, React in a script
ANGULAR = re.compile(r'data-position="([^"]*)"')
QUESTIONS = re.compile(r'<input[^>]*\bid="questions"[^>]*>')
VALUE = re.compile(r'\bvalue="([^"]*)"')
REACT = re.compile(r'<script id="portal-data" type="application/json">(.*?)</script>', re.S)
# the standard boxes, by application_form key: page name, English heading (translate.breezy.js), kind, key
STANDARD = (("resume", "cResume", "Resume", "file", "resume"),
            ("name", "cName", "Full Name", "text", "name"),
            ("email_address", "cEmail", "Email Address", "email", "email"),
            ("phone_number", "cPhoneNumber", "Phone Number", "phone", "phone"),
            ("address", "cAddress", "Address", "location", "location"))
LONG = (("summary", "cSummary", "Experience Summary"), ("cover_letter", "cCoverLetter", "Cover Letter"))
REPEATERS = (("work_history", "Work History"), ("education", "Education"))
PERIODS = ["Hourly", "Weekly", "Monthly", "Yearly"]
PER = "cSalary:per"
# the pay's per-list has no name of its own: the list right after the pay box (portal template), else the
# form's list offering Yearly (first live try found none under div.desired-salary, 2026-10-07)
PER_BOX = f'{FORM} [name="cSalary"] ~ select:not([name]), {FORM} [name="cSalary"] ~ select[name=""]'
BY_TYPE = {"text": "text", "paragraph": "longtext", "date": "date", "file": "file"}
# voluntary self-identification, drawn when application_form.eeoc is on; option words = translate.breezy.js (English)
EEO = (("race_ethnicity", "Race or Ethnicity",
        ["White (not Hispanic or Latino)", "Black or African-American (not Hispanic or Latino)",
         "Asian (not Hispanic or Latino)", "American Indian or Alaskan Native (not Hispanic or Latino)",
         "Native Hawaiian or other Pacific islander (not Hispanic or Latino)",
         "Two or more races/ethnicities (not Hispanic or Latino)",
         "Hispanic or Latino (including Black individuals whose origins are Hispanic)", "I don't wish to answer"]),
       ("gender", "Gender", ["Male", "Female", "I don't wish to answer"]),
       ("eeoc.veteran_status", "Veteran status",
        ["I IDENTIFY AS ONE OR MORE OF THE CLASSIFICATIONS OF PROTECTED VETERAN LISTED ABOVE",
         "I AM NOT A PROTECTED VETERAN", "I CHOOSE NOT TO SELF-IDENTIFY MY PROTECTED VETERAN STATUS"]))
CCPA = ("ccpaAgreement", "I've read the Privacy Notice below and consent the processing of my data as part of my job application.")
# boxes no question names: the applicant's own SMS yes, the bot trap (must stay empty), a reference's own boxes
NOT_QUESTIONS = ("hp_7f2b", "smsConsent")
# the resume box: name shown once Breezy has the file, spinner while it goes, the page's own error words (template)
RESUME_BOX = f"{FORM} .section-header .file-input-container"
UPLOADING = "Uploading Resume"
IDLE_WAIT_MS, SHOWN_WAIT_MS = 15000, 15000


def matches(url: str) -> bool:
    return bool(POSTING_URL.match(url.strip()))


def parse_url(url: str) -> tuple[str, str]:
    """(employer, posting id + slug)."""
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not a Breezy posting link: {url}")
    return m.group(1), m.group(2)


def application_url(url: str) -> str:
    co, posting = parse_url(url)
    return f"https://{co}.breezy.hr/p/{posting}/apply"


def norm(s) -> str:
    return " ".join(str(s).split())


def yes_no(options: list[str]) -> bool:
    return sorted(o.casefold() for o in options) == ["no", "yes"]


def definition(page: str) -> tuple[dict, list]:
    """(position, questionnaire sections) from either build of the apply page."""
    if m := REACT.search(page):
        data = json.loads(m.group(1)).get("data") or {}
        position = data.get("position") or {}
        form = position.setdefault("application_form", {})
        for flag, key in (("eeocEnabled", "eeoc"), ("ccpaEnabled", "ccpa")):
            if data.get(flag) and form.get(key) in (None, "hidden"):
                form[key] = "optional"
        return position, data.get("questions") or []
    if m := ANGULAR.search(page):
        position = json.loads(html.unescape(m.group(1)))
        box = QUESTIONS.search(page)  # absent when the posting asks no questions of its own (2 of 9)
        value = VALUE.search(box.group(0)) if box else None
        return position, json.loads(html.unescape(value.group(1))) if value and value.group(1) else []
    raise ValueError("no application form on the Breezy page - the posting may have closed")


def currencies(form: dict) -> list[str]:
    """The currency list's options as the page words them; [] = Breezy's whole list (not in the page)."""
    return [f"{c['name']} ({c.get('symbolNative') or c.get('symbol') or ''})" for c in form.get("salary_currency") or []]


def from_definition(position: dict, sections: list) -> list[dict]:
    form = position.get("application_form") or {}
    shown = lambda key: form.get(key) in ("required", "optional")  # noqa: E731
    out = []
    for key, id, title, kind, qkey in STANDARD:
        if shown(key):
            out.append(question(id, title, kind, form[key] == "required", (), qkey, f"breezy:{key}"))
    if shown("salary"):
        req, cur = form["salary"] == "required", currencies(form)
        out.append(question("cSalary", "Desired Salary", "number", req, (), None, "breezy:salary"))
        if len(cur) != 1:  # one currency = words on the page, no list (tenant B)
            out.append(question("salaryCurrency", "Desired Salary - currency", "choice", False, cur, None, "breezy:select"))
        out.append(question(PER, "Desired Salary - per", "choice", req, PERIODS, None, "breezy:select"))
    if shown("preferred_location"):
        names = [norm(loc.get("name") or "") for loc in position.get("locations") or []]
        out.append(question("cLocation", "Which location are you applying for", "choice",
                            form["preferred_location"] == "required", names, None, "breezy:select"))
    for key, id, title in LONG:
        if shown(key):
            out.append(question(id, title, "longtext", form[key] == "required", (), None, "breezy:text"))
    for key, title in REPEATERS:
        if shown(key):
            out.append(question(key, title, "longtext", form[key] == "required", (), None, "breezy:repeater"))
    for section in sections:
        for i, q in enumerate(section.get("questions") or []):
            out.append(employer_question(f"section_{section['_id']}_question_{i}", q))
    if shown("eeoc"):
        out += [question(id, title, "choice", False, options, None, "breezy:radio") for id, title, options in EEO]
    if shown("ccpa"):
        out.append(question(CCPA[0], CCPA[1], "yesno", True, ["Yes", "No"], None, "breezy:tick"))
    return out


def employer_question(id: str, q: dict) -> dict:
    title, required = norm(q.get("text") or ""), bool(q.get("required"))
    typ = (q.get("type") or {}).get("id") or "text"
    options = [norm(o.get("text") or "") for o in q.get("options") or []]
    if typ in ("dropdown", "multiplechoice"):
        kind = "yesno" if yes_no(options) else "choice"
        return question(id, title, kind, required, options, None, "breezy:select" if typ == "dropdown" else "breezy:radio")
    if typ == "checkboxes":
        kind = "yesno" if yes_no(options) or len(options) == 1 else "multichoice"
        return question(id, title, kind, required, options, None, "breezy:checkbox")
    if typ in BY_TYPE:
        kind = BY_TYPE[typ]
        return question(id, title, kind, required, (), key_from_title(title, kind), f"breezy:{typ}")
    # a reference's details, a recorded video, the emailed code: the user's own on the page
    return question(id, title, "text", required, (), None, f"breezy:{typ}")


def apply_page(url: str) -> str:
    r = httpx.get(application_url(url), timeout=30, follow_redirects=True)
    if r.status_code == 404:
        raise ValueError("posting not found on Breezy - it may have closed")
    r.raise_for_status()
    # a taken-down posting answers 200 with "Position Closed" and no form (6 of 16, 2026-10-07)
    if CLOSED in r.text and not (ANGULAR.search(r.text) or REACT.search(r.text)):
        raise ValueError("posting closed on Breezy - it says 'Position Closed'")
    return r.text


def questions(url: str) -> list[dict]:
    return from_definition(*definition(apply_page(url)))


def closed(url: str) -> str | None:
    """Why the form isn't there (form.closed, when the page shows no form): None = Breezy still has it."""
    try:
        definition(apply_page(url))
    except httpx.HTTPStatusError as e:
        return f"can't tell if the posting is open - Breezy answered {e.response.status_code}"
    except httpx.HTTPError as e:
        return f"can't tell if the posting is open - Breezy didn't answer ({type(e).__name__})"
    except ValueError as e:
        return str(e)
    return None


def ids_on_page(page) -> list[str]:
    """Boxes by name; the pay's unnamed per-list as cSalary:per. Never the SMS yes or the bot trap, nor a
    reference's own boxes (one question on the file)."""
    names = page.eval_on_selector_all(
        f"{FORM} input[name], {FORM} select[name], {FORM} textarea[name]",
        "es => [...new Set(es.filter(e => e.type !== 'hidden').map(e => e.name))]")
    names = [n for n in names if n and n not in NOT_QUESTIONS and not n.startswith("reference.")]
    if per_box(page).count():
        names.insert(names.index("cSalary") + 1 if "cSalary" in names else len(names), PER)
    return names


def per_box(page):
    near = page.locator(PER_BOX)
    if near.count():
        return near.first
    yearly = page.locator("option", has_text=re.compile(r"^\s*Yearly\s*$"))
    return page.locator(f"{FORM} select:not([name=salaryCurrency]):not([name=cLocation])").filter(has=yearly).first


def locate(page, q: dict):
    if q["id"] == PER:
        return per_box(page)
    return page.locator(f'{FORM} [name="{q["id"]}"]').first


def group(page, q: dict, typ: str):
    return page.locator(f'{FORM} input[type={typ}][name="{q["id"]}"]')


# each tick's words: its own <label for=id> (EEO), the <label> round it (radios), the words next to it (ticks)
OPTION_TEXTS = """bs => bs.map(b => {
    const l = (b.id && document.querySelector(`label[for="${b.id}"]`)) || b.closest('label');
    const t = l ? l.innerText : (b.nextElementSibling ? b.nextElementSibling.innerText : b.value);
    return [t.replace(/\\s+/g, ' ').trim(), b.checked]; })"""


def digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def number(value) -> str:
    """The pay box keeps digits and a point only (its own stripNonNumeric): "$85,000" -> "85000"."""
    return re.sub(r"[^\d.]", "", str(value))


def wanted(q: dict) -> set[str]:
    """The option texts (any case) an answer picks; a lone box ticked = yes."""
    value = q["answer"]
    if q["kind"] == "yesno":
        yes = str(value).casefold() in ("yes", "true")
        if len(q["options"]) == 1:
            return {q["options"][0].casefold()} if yes else set()
        value = ["Yes" if yes else "No"]
    return {norm(v).casefold() for v in (value if isinstance(value, list) else [value])}


def put_text(field, value, kind: str) -> str:
    v = number(value) if kind == "number" else str(value)
    if kind == "number" and not v:
        return f"ASK '{value}' is not a number - the box takes digits only"
    field.fill(v)
    if kind == "location":  # Google's suggestions shut, never one picked: it would replace what the user gave
        field.press("Escape")
    field.blur()
    got = field.input_value()
    return "ok" if (digits(got) == digits(v) if kind == "phone" else got == v) else f"FAIL shows '{got}'"


def put_ticks(page, q: dict, typ: str) -> str:
    """Tick the one(s) whose words are the answer, untick the rest; read the ticks back. Ticks carry no
    value of their own (checkboxes) or a code (EEO): picked by the words next to them."""
    boxes = group(page, q, typ)
    texts = [t for t, _ in boxes.evaluate_all(OPTION_TEXTS)]
    want = wanted(q)
    if missing := want - {t.casefold() for t in texts}:
        return f"ASK no option '{sorted(missing)[0]}'; offered: {', '.join(texts)}"
    for box, t in zip(boxes.all(), texts):
        if (t.casefold() in want) != box.is_checked():
            box.evaluate("e => e.click()")  # like a person's click: Angular's own handlers run
    wrong = [t for t, on in boxes.evaluate_all(OPTION_TEXTS) if (t.casefold() in want) != on]
    return "ok" if not wrong else f"FAIL '{wrong[0]}' shows the wrong tick"


def chosen(field) -> list[str]:
    """Texts of the options picked - never Angular's empty no-answer one (value "" or "?")."""
    return [norm(t) for t in field.evaluate(
        "e => [...e.selectedOptions].filter(o => o.value !== '' && o.value !== '?').map(o => o.text)")]


def put_select(field, q: dict) -> str:
    """Pick the option whose text is the answer, any case; read the pick back. Angular's lists carry
    their own values (an index, a currency code): matched by text."""
    want = wanted(q)
    options = field.evaluate("e => [...e.options].map(o => [o.value, o.text])")
    hits = [v for v, t in options if v not in ("", "?") and norm(t).casefold() in want]
    if not hits:
        offered = ", ".join(norm(t) for v, t in options if v not in ("", "?"))
        return f"ASK no option '{norm(q['answer'])}'; offered: {offered[:200]}"
    field.select_option(value=hits[:1])
    got = {t.casefold() for t in chosen(field)}
    return "ok" if got == want else f"FAIL shows '{', '.join(chosen(field))}'"


def resume_says(page) -> tuple[str, bool, str]:
    """(file name the box shows, still sending, the page's error words beside it)."""
    box = page.locator(RESUME_BOX).first
    if not box.count():
        return "", False, ""
    name = norm(" ".join(box.locator("a.bzyLinkColor").all_inner_texts()))
    sending = page.locator(f"{FORM} .apply-buttons", has_text=UPLOADING).count() > 0
    error = norm(" ".join(box.locator(".error-container:not(.ng-hide) span.error").all_inner_texts()))
    return name, sending, error


def put_file(page, field, path: str) -> str:
    """Page idle first, then the file chosen: Breezy takes it at once and reads it, refilling summary +
    work history (form.fill_page puts files first, so typed answers land after). Ok = the box shows the
    file's name, nothing still sending, no error words; the page's own words -> FAIL; neither -> ASK."""
    with contextlib.suppress(Exception):  # a page that keeps polling never goes idle: the read decides
        page.wait_for_load_state("networkidle", timeout=IDLE_WAIT_MS)
    field.set_input_files(path)
    name = Path(path).name
    deadline = time.monotonic() + SHOWN_WAIT_MS / 1000
    while time.monotonic() < deadline:
        shown, sending, error = resume_says(page)
        if error:
            return f"FAIL the page says '{error}' - choose the file again on the page, or check the resume box"
        if shown == name and not sending:
            return "ok"
        page.wait_for_timeout(250)
    return "ASK upload not confirmed on page - check the resume box"


def holds(page, q: dict) -> bool:
    """The answer still shows, read off the page once the form had time to keep it (form.recheck), each
    kind as breezy.md "Read back" records it: a box by its value (phone by digits, pay by its number), ticks
    + radios by each one's own state against its words, a list by the option picked, the resume by the
    name the box shows with nothing sending and no error. Nothing to read = False."""
    native, kind = q.get("native") or "", q["kind"]
    if native in ("breezy:checkbox", "breezy:radio"):
        typ = "checkbox" if native == "breezy:checkbox" else "radio"
        ticks = group(page, q, typ).evaluate_all(OPTION_TEXTS)
        want = wanted(q)
        return bool(ticks) and all((t.casefold() in want) == on for t, on in ticks)
    field = locate(page, q)
    if not field.count():
        return False
    if kind == "file":
        shown, sending, error = resume_says(page)
        return bool(shown) and not sending and not error
    if field.evaluate("e => e.tagName") == "SELECT":
        return {t.casefold() for t in chosen(field)} == wanted(q)
    got, value = field.input_value(), str(q["answer"])
    if kind == "phone":
        return bool(digits(value)) and digits(got) == digits(value)
    return got == (number(value) if kind == "number" else value)


def fill(page, q: dict, resume_file: str | None) -> str:
    if signs(q["title"]):
        return left_on_page(q)
    native, kind, value = q.get("native") or "", q["kind"], q["answer"]
    if native == "breezy:repeater":
        return f"ASK the {q['title']} section takes entries one by one - the user adds them on the page (the resume upload may fill it)"
    if kind == "file" and q.get("key") != "resume":
        return f"ASK not the resume box ({q['title']}) - the user uploads their own file there"
    if native in ("breezy:referencecheck", "breezy:video", "breezy:verification_code"):
        return f"ASK {native.split(':')[1].replace('_', ' ')} ({q['title']}) - the user does this on the page"
    if native == "breezy:date" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value)):
        return f"ASK date box ({q['title']}) - the user picks the date on the page's calendar"
    if native in ("breezy:checkbox", "breezy:radio"):
        return put_ticks(page, q, "checkbox" if native == "breezy:checkbox" else "radio")
    field = locate(page, q)
    if not field.count():
        return "FAIL question not on page"
    if kind == "file":
        return put_file(page, field, resume_file) if value is True and resume_file else "skipped - upload not approved"
    field.scroll_into_view_if_needed()
    if field.evaluate("e => e.tagName") == "SELECT":
        return put_select(field, q)
    return put_text(field, value, kind)
