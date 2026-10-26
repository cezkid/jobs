"""Dover (app.dover.com/apply/<employer>/<job uuid>): questions from the posting's own form definition, answers typed into its page.

One page: contact boxes, the employer's questions, Resume, a Cloudflare check, then Apply (never ours).
The "Autofill from resume" box above the form is never used: it sends the resume's text to Dover to be
read. Measured facts and why each rule exists: app/docs/apply/dover.md.
"""
import contextlib
import json
import re
import time
from pathlib import Path

import httpx

from apply.questions import key_from_title, left_on_page, question, signs

NAME = "Dover"
# one host for every employer; freehire adds ?utm_source=freehire.me, Adzuna ?utm_source=adzuna (150 of 150, 2026-10-26)
POSTING_URL = re.compile(r"https?://app\.dover\.com/apply/([^/?#]+)/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
                         r"/?(?=[?#]|$)", re.I)
SOURCES = ("dover",)
EXAMPLES = ("https://app.dover.com/apply/acme/00000000-0000-4000-8000-000000000001",
            "https://app.dover.com/apply/acme/00000000-0000-4000-8000-000000000001?utm_source=freehire.me",
            "https://app.dover.com/apply/Acme/00000000-0000-4000-8000-000000000001/?utm_source=adzuna&utm_medium=adzuna")
HOST = "https://app.dover.com"
# the page's own read of its form: plain JSON GET, public, no key (120 of 120 forms, 2026-10-26)
DEFINITION = HOST + "/api/v1/inbound/application-portal-job/{id}"
QUESTIONS_OVER_HTTP = True
# the page records every visit for PostHog, typed boxes unmasked: what's typed + the resume's file name leave as the
# fill goes (Dover's PostHog settings: maskAllInputs false, no sampling; synthetic values seen in the blocked posts, 2026-10-26)
RECORDED_BY = "PostHog, Dover's analytics company"
# a React page: the boxes come once the definition is read (3 of 3)
READY = 'form [name="firstName"]'
FORM = "form"
# boxes every Dover form has, ahead of the employer's questions (page script + 3 of 3 pages)
FIXED = (("firstName", "First Name", "text", "first_name"), ("lastName", "Last Name", "text", "last_name"),
         ("email", "Email", "email", "email"))
# Dover's own questions: the page's box name, kind, key (question_type in the definition)
OWN = {"LINKEDIN_URL": ("linkedinUrl", "url", "linkedin"), "PHONE_NUMBER": ("phoneNumber", "phone", "phone")}
RESUME = "resume"
BY_INPUT = {"SHORT_ANSWER": "text", "LONG_ANSWER": "longtext", "MULTIPLE_CHOICE": "choice", "MULTIPLE_SELECT": "multichoice"}
# the page's own check of a phone number before it sends (page script, 2026-10-26)
PHONE_OK = re.compile(r"^[+]*[(]{0,1}[0-9]{1,3}[)]{0,1}[-\s./0-9]*$")
# a file name in the resume block: "Resume: <name>", cut after 35 letters + "...<ext>" (page script)
SHOWN_CHARS = 35
IDLE_WAIT_MS, SHOWN_WAIT_MS = 15000, 5000
# the two upload boxes carry no name: the resume one sits in the "Drag and drop file or browse computer" block,
# the autofill one in "Autofill from resume" - never touched (it sends the file's text to be read)
FILE_INPUTS = f"{FORM} input[type=file]"
# named boxes that are no question: the applicant's own "notify me" tick, the Cloudflare check's hidden token (3 of 3)
NOT_QUESTIONS = ["notifyOnView", "cf-turnstile-response"]
AUTOFILL = re.compile(r"autofill", re.I)
# a chosen file shows as "Resume: <name>" + this button, in place of the upload box (measured 2026-10-26)
REMOVE = "Remove"
# the page's own words for a file it refuses (page script; wrong type measured 2026-10-26)
FILE_ERROR = re.compile(r"(?:Invalid file type|File too (?:large|small)|Name too large|Too many files|Error uploading file)[^\n]*")
# a tick box per option, no name on any: found under the question's own words (page script)
GROUP = """(e, title) => { const t = x => (x.textContent || '').replace(/\\s+/g, ' ').trim();
  const head = [...e.querySelectorAll('*')].find(x => !x.children.length && [title, title + ' *'].includes(t(x)));
  if (!head) return null;
  let block = head.parentElement;
  while (block && block !== e && !block.querySelector('input[type=checkbox]')) block = block.parentElement;
  if (!block || block === e) return null;
  const all = [...e.querySelectorAll('input[type=checkbox]')];
  return [...block.querySelectorAll('input[type=checkbox]')].map(b => [all.indexOf(b), t(b.closest('label') || b.parentElement)]); }"""


def matches(url: str) -> bool:
    return bool(POSTING_URL.match(url.strip()))


def parse_url(url: str) -> tuple[str, str]:
    """(employer, job uuid)."""
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not a Dover posting link: {url}")
    return m.group(1), m.group(2).lower()


def application_url(url: str) -> str:
    co, job = parse_url(url)
    return f"{HOST}/apply/{co}/{job}"


def norm(s) -> str:
    return " ".join(str(s or "").split())


def yes_no(options: list[str]) -> bool:
    return sorted(o.casefold() for o in options) == ["no", "yes"]


def from_definition(data: dict) -> list[dict]:
    """Questions in the page's order: the fixed boxes, then Dover's own + the employer's by order_index
    (none = last), the resume box at the foot. A hidden one never shows on the page."""
    out = [question(id, title, kind, True, (), key, f"dover:{id}") for id, title, kind, key in FIXED]
    qs = [q for q in data.get("application_questions") or [] if not q.get("hidden")]
    qs.sort(key=lambda q: (q.get("order_index") is None, q.get("order_index") or 0))
    resume = None
    for q in qs:
        title, required, qtype = norm(q.get("question")), bool(q.get("required")), q.get("question_type")
        if qtype == "RESUME":
            resume = question(RESUME, "Resume", "file", required, (), "resume", "dover:resume")
        elif qtype == "LINKEDIN_URL":
            id, kind, key = OWN[qtype]
            # a posting may ask for it whatever the question says (require_linkedin_profile_url, 0 of 120)
            out.append(question(id, title or "LinkedIn Profile URL", kind, required or bool(data.get("require_linkedin_profile_url")),
                                (), key, f"dover:{id}"))
        elif qtype in OWN:
            id, kind, key = OWN[qtype]
            out.append(question(id, title, kind, required, (), key, f"dover:{id}"))
        else:  # CUSTOM: the employer's own, named on the page by its id
            input_type = q.get("input_type")
            options = [norm(o) for o in q.get("multiple_choice_options") or []]
            kind = BY_INPUT.get(input_type, "text")
            if kind in ("choice", "multichoice") and not options:
                continue  # the page draws nothing for a list with no options (page script)
            if kind == "choice" and yes_no(options):
                kind = "yesno"
            native = {"choice": "dover:radio", "yesno": "dover:radio", "multichoice": "dover:checkbox"}.get(kind, "dover:text")
            out.append(question(str(q["id"]), title, kind, required, options,
                                key_from_title(title, kind) if kind in ("text", "longtext") else None, native))
    return out + ([resume] if resume else [])


def definition(url: str) -> httpx.Response:
    return httpx.get(DEFINITION.format(id=parse_url(url)[1]), timeout=30, follow_redirects=True)


def questions(url: str) -> list[dict]:
    r = definition(url)
    # unknown or taken down: 404 {"detail": "Not found."}; the page then says "It may have been filled or deactivated."
    if r.status_code == 404:
        raise ValueError("posting not found on Dover - it may have been filled or deactivated")
    r.raise_for_status()
    data = r.json()
    if data.get("active") is False:
        raise ValueError("Dover lists the posting as no longer active - it may have closed")
    return from_definition(data)


def closed(url: str) -> str | None:
    """Why the form isn't there (form.closed, when the page shows no form): None = Dover still has it."""
    try:
        r = definition(url)
    except httpx.HTTPError as e:
        return f"can't tell if the posting is open - Dover didn't answer ({type(e).__name__})"
    if r.status_code == 404:
        return "posting not found on Dover - it may have been filled or deactivated"
    if r.status_code != 200:
        return f"can't tell if the posting is open - Dover answered {r.status_code}"
    with contextlib.suppress(ValueError):
        if r.json().get("active") is False:
            return "Dover lists the posting as no longer active - it may have closed"
    return None


def ids_on_page(page) -> list[str]:
    """Named boxes as question ids (contact boxes by name, employer ones by their id); the resume box
    when its block is there. Tick-box lists carry no name (found by their words); MUI's hidden copy of a
    long box has no name; the "notify me" tick is the applicant's own choice and the Cloudflare check's token box
    the check's own - no questions."""
    ids = page.eval_on_selector_all(
        f"{FORM} input[name], {FORM} textarea[name]",
        "es => [...new Set(es.map(e => e.name).filter(n => n && !SKIP.includes(n)))]".replace("SKIP", json.dumps(NOT_QUESTIONS)))
    return ids + ([RESUME] if resume_box(page) is not None else [])


def locate(page, q: dict):
    return page.locator(f'{FORM} [name="{q["id"]}"]').first


def digits(s) -> str:
    return re.sub(r"\D", "", str(s))


def phone_typed(value) -> str | None:
    """The phone as the page's own check takes it: as given, else its digit groups with spaces
    ("+1 (555) 010-0100" -> "+1 555 010 0100"); None when that would change it (letters, an extension)."""
    v = str(value).strip()
    if PHONE_OK.match(v):
        return v
    if re.search(r"[A-Za-z#,;]", v):
        return None
    spaced = re.sub(r"[^\d+]+", " ", v).strip()
    return spaced if PHONE_OK.match(spaced) and digits(spaced) == digits(v) else None


def put_text(field, value, kind: str) -> str:
    v = str(value)
    if kind == "phone":
        v = phone_typed(value)
        if v is None:
            return f"ASK '{value}' won't pass Dover's phone check (digits, spaces, - . / and one (area code)) - type it on the page"
    field.fill(v)
    field.blur()
    got = field.input_value()
    return "ok" if (digits(got) == digits(v) if kind == "phone" else got == v) else f"FAIL shows '{got}'"


def picks(q: dict) -> set[str]:
    value = q["answer"]
    if q["kind"] == "yesno":
        value = ["Yes" if str(value).casefold() in ("yes", "true") else "No"]
    return {norm(v).casefold() for v in (value if isinstance(value, list) else [value])}


def put_radio(page, q: dict) -> str:
    """Tick the radio whose value is the answer (its value = the option's words, page script); read it back."""
    radios = page.locator(f'{FORM} input[type=radio][name="{q["id"]}"]')
    if not radios.count():
        return "FAIL question not on page"
    values = [norm(v) for v in radios.evaluate_all("es => es.map(e => e.value)")]
    want = picks(q)
    hit = next((i for i, v in enumerate(values) if v.casefold() in want), None)
    if hit is None or len(want) != 1:
        return f"ASK no option '{norm(q['answer'])}'; offered: {', '.join(values)}"
    radio = radios.nth(hit)
    radio.check(force=True)  # MUI hides the native radio under its own circle
    return "ok" if radio.is_checked() else f"FAIL '{values[hit]}' not ticked"


def group(page, q: dict) -> list[tuple[int, str]] | None:
    """[(place among the form's tick boxes, its label)] for the question's own list, or None."""
    form = page.locator(FORM).first
    if not form.count():
        return None
    got = form.evaluate(GROUP, norm(q["title"]))
    return [(i, norm(t)) for i, t in got] if got else None


def put_ticks(page, q: dict) -> str:
    """Tick the boxes whose labels are the answers, untick the rest; read the ticks back. The page
    stops more ticks than its "Select up to N" (greyed out)."""
    boxes = group(page, q)
    if not boxes:
        return "FAIL question not on page"
    want = picks(q)
    labels = [t for _, t in boxes]
    if missing := want - {t.casefold() for t in labels}:
        return f"ASK no option '{sorted(missing)[0]}'; offered: {', '.join(labels)}"
    ticks = page.locator(f"{FORM} input[type=checkbox]")
    for off in (True, False):  # untick first: a full list greys out the rest
        for i, t in boxes:
            box = ticks.nth(i)
            if (t.casefold() in want) != box.is_checked() and box.is_checked() == off:
                box.click(force=True)
    wrong = [t for i, t in boxes if (t.casefold() in want) != ticks.nth(i).is_checked()]
    return "ok" if not wrong else f"FAIL '{wrong[0]}' shows the wrong tick"


def resume_box(page):
    """The resume's upload box - never the autofill one above the form."""
    boxes = page.locator(FILE_INPUTS)
    places = [i for i, words in enumerate(boxes.evaluate_all("es => es.map(e => (e.parentElement || e).innerText || '')"))
              if not AUTOFILL.search(words)]
    return boxes.nth(places[-1]) if places else None


def shown_name(name: str) -> str:
    """The name as the block prints it: over 35 letters -> cut + "...<ext>" (page script)."""
    return name if len(name) <= SHOWN_CHARS else name[:SHOWN_CHARS] + "..." + name.rsplit(".", 1)[-1]


def resume_says(page) -> str:
    return norm(" ".join(page.locator(FORM).first.all_inner_texts())) if page.locator(FORM).count() else ""


def remove_shown(page) -> bool:
    """A file already in the resume block (an earlier fill, the user's own pick): its Remove button brings the
    upload box back (measured 2026-10-26: the box is gone while a file shows)."""
    remove = page.locator(f'{FORM} button[aria-label="{REMOVE}"]')
    if not remove.count():
        return False
    remove.last.click()
    deadline = time.monotonic() + SHOWN_WAIT_MS / 1000
    while resume_box(page) is None and time.monotonic() < deadline:
        page.wait_for_timeout(250)
    return resume_box(page) is not None


def put_file(page, path: str) -> str:
    """Page idle first (as Manatal), then the file chosen in the resume box - it stays in the page until
    Apply (measured: 0 requests on choosing). Ok = the block shows "Resume: <name>"; the page's own error
    words (a note: "Invalid file type. Accepted file types: .pdf.") -> FAIL; neither -> ASK."""
    with contextlib.suppress(Exception):  # a page that keeps polling never goes idle: the read decides
        page.wait_for_load_state("networkidle", timeout=IDLE_WAIT_MS)
    want = f"Resume: {shown_name(Path(path).name)}"
    box = resume_box(page)
    if box is None and want in resume_says(page):
        return "ok"  # this file already in the block
    if box is None and not remove_shown(page):
        return "FAIL resume box not on page"
    resume_box(page).set_input_files(path)
    deadline = time.monotonic() + SHOWN_WAIT_MS / 1000
    while time.monotonic() < deadline:
        if want in resume_says(page):
            return "ok"
        if said := FILE_ERROR.search(page.locator("body").inner_text()):
            return f"FAIL the page says '{norm(said.group())}' - choose the file again on the page"
        page.wait_for_timeout(250)
    return "ASK upload not confirmed on page - check the resume box"


def holds(page, q: dict) -> bool:
    """The answer still shows, read off the page once the form had time to keep it (form.recheck), as
    dover.md "Read back" records it: a box by its value (phone by digits), radios + tick boxes by their
    ticks, the resume by "Resume: <name>" in its block. Nothing to read = False."""
    native, kind = q.get("native") or "", q["kind"]
    if kind == "file":
        return bool(re.search(r"Resume: \S", resume_says(page)))
    if native == "dover:radio":
        radios = page.locator(f'{FORM} input[type=radio][name="{q["id"]}"]')
        ticked = [norm(v).casefold() for v, on in radios.evaluate_all("es => es.map(e => [e.value, e.checked])") if on]
        return bool(ticked) and set(ticked) == picks(q)
    if native == "dover:checkbox":
        boxes = group(page, q)
        if not boxes:
            return False
        ticks = page.locator(f"{FORM} input[type=checkbox]")
        return {t.casefold() for i, t in boxes if ticks.nth(i).is_checked()} == picks(q)
    field = locate(page, q)
    if not field.count():
        return False
    got, value = field.input_value(), str(q["answer"])
    if kind == "phone":
        return bool(digits(value)) and digits(got) == digits(value)
    return got == value


def fill(page, q: dict, resume_file: str | None) -> str:
    if signs(q["title"]):
        return left_on_page(q)
    native, kind, value = q.get("native") or "", q["kind"], q["answer"]
    if kind == "file":
        return put_file(page, resume_file) if value is True and resume_file else "skipped - upload not approved"
    if native == "dover:radio":
        return put_radio(page, q)
    if native == "dover:checkbox":
        return put_ticks(page, q)
    field = locate(page, q)
    if not field.count():
        return "FAIL question not on page"
    field.scroll_into_view_if_needed()
    return put_text(field, value, kind)
