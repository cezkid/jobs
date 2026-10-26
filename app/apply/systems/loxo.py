"""Loxo (app.loxo.co/job/<id>, a recruiting firm's own job page): questions read off the posting's form page, answers typed into it.

Measured facts and why each rule exists: app/docs/apply/loxo.md.
"""
import contextlib
import re
import time
from html.parser import HTMLParser
from pathlib import Path

import httpx

from apply.questions import key_from_title, left_on_page, question, signs

NAME = "Loxo"
# one host for every recruiting firm, or the firm's own label before it (<firm>.app.loxo.co); the id is
# base64 of "<agency number>-<16 letters + digits>" (50 of 50 newest US links, 2026-10-26), so never a / or +;
# freehire adds ?utm_source=freehire.me; the form is the posting + /form
POSTING_URL = re.compile(r"https?://((?:[\w-]+\.)?app\.loxo\.co)/job/([A-Za-z0-9]+(?:=|%3D){0,2})(?:/form)?/?(?=[?#]|$)", re.I)
SOURCES = ("loxo",)
# (the shared host app.loxo.co/job/<id> is the usual shape - test_apply_loxo; examples carry the firm label for anonymity)
EXAMPLES = ("https://acme.app.loxo.co/job/MTIzNDUtYWJjZGVmZ2hpamtsbW5vcA==",
            "https://acme.app.loxo.co/job/MTIzNDUtYWJjZGVmZ2hpamtsbW5vcA==?utm_source=freehire.me",
            "https://acme.app.loxo.co/job/MTIzNDUtYWJjZGVmZ2hpamtsbW5vcA==/form?source_type=app")
# the form is server-rendered in its own page (6 of 6 postings, 5 firms, 2026-10-26): a plain GET, no browser
QUESTIONS_OVER_HTTP = True
# the posting's own "Apply for this job" links carry ?source_type=app (2 of 2 on each posting page)
FORM_PATH = "/form?source_type=app"
# the only form on the page posts to /job/<id>/finish
FORM = 'form[action*="/finish"]'
READY = f'{FORM} [name="email"]'
# the three contact boxes: placeholder only, no label, no required mark (6 of 6); full name in one box
CONTACT = {"name": ("text", "name"), "email": ("email", "email"), "phone": ("phone", "phone")}
# the resume box: a custom element with an open shadow root (better_file_input.js, read 2026-10-26)
FILE_HOST = "better-file-input"
# the text-message opt-in under every form (6 of 6), never required
CONSENT = "contact_consent"
# employer questions: name custom_question_<n> (checkboxes custom_question_<n>[])
CUSTOM = re.compile(r"^(custom_question_\d+)(?:\[\])?$")
# the page marks a required question with a red asterisk beside or inside its label
ASTERISK = "*"
# a removed chip's button + the chips' own words: font-awesome class names, never the generated ones
CHIP = "button.fa-times-circle"
GONE = (404, 410)
IDLE_WAIT_MS, SHOWN_WAIT_MS = 15000, 5000


def matches(url: str) -> bool:
    return bool(POSTING_URL.match(url.strip()))


def parse_url(url: str) -> tuple[str, str]:
    """(host, posting id)."""
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not a Loxo posting link: {url}")
    return m.group(1).casefold(), m.group(2).replace("%3D", "=").replace("%3d", "=")


def application_url(url: str) -> str:
    host, id = parse_url(url)
    return f"https://{host}/job/{id}{FORM_PATH}"


def norm(s) -> str:
    return " ".join(str(s).split())


class Form(HTMLParser):
    """The application form as read: contact boxes, the resume box, each employer question with its
    label words, required mark, controls + option words, and the opt-in box's words."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.inside = self.in_file = self.in_label = False
        self.contact, self.file, self.blocks = [], None, []
        self.block = self.option = self.select = None
        self.consent = None  # [words] once the opt-in box is seen, until the submit button
        self.textarea = None

    def handle_starttag(self, tag, attrs):
        a = {k: v or "" for k, v in attrs}
        if tag == "form" and "/finish" in a.get("action", ""):
            self.inside = True
        if not self.inside:
            return
        typ = a.get("type", "text").casefold()
        if tag == FILE_HOST:
            self.in_file = True
            self.file = {"name": a.get("name", ""), "required": "required" in a, "title": ""}
            return
        if self.in_file:
            if tag == "input" and typ == "button":
                self.file["title"] = norm(a.get("value", "")).removeprefix("Upload ")
            return
        if tag == "input" and typ == "submit":
            self.inside = False  # the opt-in box's words end at the button
            return
        if tag == "input" and a.get("name") == CONSENT:
            self.consent = []
            return
        if self.consent is not None:
            return
        if tag == "input" and a.get("name") in CONTACT:
            self.contact.append(a)
            return
        if tag == "label":
            self.in_label = True
            if self.block is None or self.block["controls"]:
                self.block = {"words": "", "required": False, "controls": []}
                self.blocks.append(self.block)
            return
        if tag == "br":
            self.option = None
            if self.in_label and self.block:
                self.block["words"] += " "
            return
        if tag in ("input", "textarea", "select") and typ != "hidden" and CUSTOM.match(a.get("name", "")):
            if self.block is None:  # a control with no label words before it: a question with no words
                self.block = {"words": "", "required": False, "controls": []}
                self.blocks.append(self.block)
            c = {"tag": tag, **a, "type": typ if tag == "input" else tag, "text": "", "options": []}
            self.block["controls"].append(c)
            self.option = c if typ in ("radio", "checkbox") else None
            self.select = c if tag == "select" else None
            self.textarea = c if tag == "textarea" else None
            return
        if tag == "option" and self.select is not None:
            self.select["options"].append([a.get("value", ""), ""])
        if tag == "div":
            self.option = None

    def handle_endtag(self, tag):
        if tag == FILE_HOST:
            self.in_file = False
        elif tag == "label":
            self.in_label = False
        elif tag == "select":
            self.select = None
        elif tag == "textarea":
            self.textarea = None
        elif tag == "div":
            self.option = None
        elif tag == "form":
            self.inside = False

    def handle_data(self, data):
        if not self.inside or self.in_file or self.textarea is not None:
            return
        if self.consent is not None:
            self.consent.append(data)
            return
        if self.select is not None and self.select["options"]:
            self.select["options"][-1][1] += data
            return
        if self.block is None:
            return
        if data.strip() == ASTERISK:
            self.block["required"] = True
        elif self.option is not None:
            self.option["text"] += data
        elif self.in_label:
            self.block["words"] += data


def yes_no(options: list[str]) -> bool:
    return sorted(o.casefold() for o in options) == ["no", "yes"]


def from_html(html: str) -> list[dict]:
    form = Form()
    form.feed(html)
    if not form.contact and form.file is None:
        raise ValueError("no application form on the posting page - it may have closed")
    out = []
    for c in form.contact:
        kind, key = CONTACT[c["name"]]
        title = norm(c.get("placeholder") or c.get("title") or c["name"])
        out.append(question(c["name"], title, kind, "required" in c, (), key, "loxo:text"))
    if form.file:
        out.append(question(form.file["name"], form.file["title"] or "Resume/CV", "file", form.file["required"], (),
                            "resume", "loxo:file"))
    for b in form.blocks:
        if not b["controls"]:
            continue
        first = b["controls"][0]
        id = CUSTOM.match(first["name"]).group(1)
        title = norm(b["words"]).removesuffix(ASTERISK).strip()
        required = b["required"] or any("required" in c for c in b["controls"])
        typ = first["type"]
        if typ in ("radio", "checkbox"):
            options = [norm(c["text"]) for c in b["controls"]]
            kind = "yesno" if yes_no(options) or (typ == "checkbox" and len(options) == 1) else \
                "choice" if typ == "radio" else "multichoice"
            out.append(question(id, title, kind, required, options, None, f"loxo:{typ}"))
        elif typ == "select":
            options = [norm(t) for v, t in first["options"] if v != ""]
            out.append(question(id, title, "yesno" if yes_no(options) else "choice", required, options, None, "loxo:select"))
        else:
            kind = {"textarea": "longtext", "number": "number", "email": "email", "tel": "phone", "url": "url",
                    "date": "date"}.get(typ, "text")
            out.append(question(id, title, kind, required, (), key_from_title(title, kind), f"loxo:{typ}"))
    if form.consent is not None:
        # the box's label alone ("Yes, <firm> can contact me about job opportunities.") reads as no
        # agreement: its fine print (texts, Terms of Service) is what it agrees to
        out.append(question(CONSENT, norm(" ".join(form.consent)), "yesno", False, ["Yes"], None, "loxo:consent"))
    return out


def questions(url: str) -> list[dict]:
    r = httpx.get(application_url(url), timeout=30, follow_redirects=True)
    # unknown id: 404 "Page not found" (loxo.md "Closed posting")
    if r.status_code in GONE:
        raise ValueError("posting not found - it may have closed")
    r.raise_for_status()
    return from_html(r.text)


def closed(url: str) -> str | None:
    """Why the form isn't there (form.closed, when the page shows no form and no closed words):
    Loxo's own answer for the posting's form page. None = form there."""
    try:
        r = httpx.get(application_url(url), timeout=30, follow_redirects=True)
    except httpx.HTTPError as e:
        return f"can't tell if the posting is open - Loxo didn't answer ({type(e).__name__})"
    if r.status_code in GONE:
        return "posting not found - it may have closed"
    if r.status_code != 200:
        return f"can't tell if the posting is open - Loxo answered {r.status_code}"
    try:
        from_html(r.text)
    except ValueError as e:
        return str(e)
    return None


def ids_on_page(page) -> list[str]:
    return page.eval_on_selector_all(
        f"{FORM} input[name], {FORM} textarea[name], {FORM} select[name], {FORM} {FILE_HOST}",
        f"""es => [...new Set(es.filter(e => e.tagName === '{FILE_HOST.upper()}' || (e.type !== 'hidden' && e.type !== 'file'
              && e.type !== 'button' && e.type !== 'submit' && !e.closest('{FILE_HOST}')))
              .map(e => e.tagName === '{FILE_HOST.upper()}' ? e.getAttribute('name') : e.getAttribute('name').replace(/\\[\\]$/, '')))]""")


def by_name(page, name: str):
    return page.locator(f'{FORM} [name="{name}"]').first


def digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def put_text(field, value, kind: str) -> str:
    v = str(value)
    field.fill(v)
    field.evaluate("e => { e.dispatchEvent(new Event('change', {bubbles: true})); e.blur(); }")
    got = field.input_value()
    return "ok" if (digits(got) == digits(v) if kind == "phone" else got == v) else f"FAIL shows '{got}'"


# an option's words: the text after its tick up to the next <br> or control (6 of 6 forms)
OPTIONS = """es => es.map(e => { let t = '', n = e.nextSibling;
  while (n && !(n.nodeType === 1 && ['BR', 'INPUT', 'DIV'].includes(n.tagName))) { t += n.textContent || ''; n = n.nextSibling; }
  return [t.replace(/\\s+/g, ' ').trim(), e.checked]; })"""


def wanted(q: dict) -> set[str]:
    """The option words (any case) an answer picks; a lone box ticked = yes."""
    value = q["answer"]
    if q["kind"] == "yesno":
        value = ["Yes" if str(value).casefold() in ("yes", "true") else "No"]
        if len(q["options"]) == 1:
            value = q["options"] if value == ["Yes"] else []
    return {norm(v).casefold() for v in (value if isinstance(value, list) else [value])}


def group(page, q: dict, typ: str):
    name = q["id"] + ("[]" if typ == "checkbox" else "")
    return page.locator(f'{FORM} input[type={typ}][name="{name}"]')


def put_ticks(page, q: dict, typ: str) -> str:
    """Tick the box(es) / the radio whose words are the answer (radios: one), untick the rest; read
    the ticks back."""
    boxes = group(page, q, typ)
    if not boxes.count():
        return "FAIL question not on page"
    words = [w for w, _ in boxes.evaluate_all(OPTIONS)]
    want = wanted(q)
    if missing := want - {w.casefold() for w in words}:
        return f"ASK no option '{sorted(missing)[0]}'; offered: {', '.join(words)[:200]}"
    for box, w in zip(boxes.all(), words):
        if (w.casefold() in want) != box.is_checked():
            box.evaluate("e => e.click()")  # like a person's click: the page's own handlers run
    wrong = [w for w, on in boxes.evaluate_all(OPTIONS) if (w.casefold() in want) != on]
    return "ok" if not wrong else f"FAIL '{wrong[0]}' shows the wrong tick"


def put_select(field, q: dict) -> str:
    want = wanted(q)
    options = field.evaluate("e => [...e.options].map(o => [o.value, o.text])")
    hit = next((v for v, t in options if v != "" and norm(t).casefold() in want), None)
    if hit is None:
        return f"ASK no option '{norm(q['answer'])}'; offered: {', '.join(norm(t) for v, t in options if v)[:200]}"
    field.select_option(value=hit)
    return "ok" if field.evaluate("e => e.value") == hit else f"FAIL shows '{field.evaluate('e => e.value')}'"


# what the resume box shows + what Submit would send: the chips the component draws in its shadow
# root (one per file, its name + a remove button), and the files a FormData of the form holds under
# the box's name - the component adds its own on the form's formdata event, and the hidden light-DOM
# input is a form control too, so a file set there goes as well, unseen. Building a FormData sends nothing.
FILE_STATE = f"""h => {{ const root = h.shadowRoot, name = h.getAttribute('name');
  const chips = root ? [...root.querySelectorAll('{CHIP}')].map(b => (b.parentElement.textContent || '').replace(/\\s+/g, ' ').trim()) : null;
  const form = h.closest('form');
  const sent = form ? new FormData(form).getAll(name).filter(f => f && f.name).map(f => f.name) : [];
  return {{chips, sent, shadow: !!(root && root.querySelector('input[type=file]'))}}; }}"""


def file_state(host) -> dict:
    return host.evaluate(FILE_STATE)


def one_file(state: dict, name: str) -> bool:
    """The box shows this file once and Submit would send it once - nothing else."""
    return state["chips"] == [name] and state["sent"] == [name]


def put_file(page, host, path: str) -> str:
    """Page idle first (as Greenhouse, Ashby), then the file set on the input INSIDE the component's
    shadow root - the one its own drop box opens. Set on the hidden light-DOM input instead, the file
    goes at Submit but the box still says "Upload File" (a user saw that, 2026-10-26). Ok = one chip
    with the file's name and the form would send that file once; the file stays on the computer until
    Submit (native form POST, loxo.md). Run again: a chip already there is kept, never a second copy."""
    with contextlib.suppress(Exception):  # a page that keeps polling never goes idle: the read decides
        page.wait_for_load_state("networkidle", timeout=IDLE_WAIT_MS)
    name = Path(path).name
    state = file_state(host)
    if state["chips"] is None or not state["shadow"]:
        return "ASK the resume box hasn't drawn yet - choose the file in its Upload File box on the page"
    if name not in state["chips"]:
        inner = host.evaluate_handle("h => h.shadowRoot.querySelector('input[type=file]')").as_element()
        inner.set_input_files(path)
        deadline = time.monotonic() + SHOWN_WAIT_MS / 1000
        while time.monotonic() < deadline and name not in file_state(host)["chips"]:
            page.wait_for_timeout(250)
    state = file_state(host)
    if one_file(state, name):
        return "ok"
    if name not in state["chips"]:
        return "ASK upload not confirmed on page - check the resume box shows the file"
    if len(state["chips"]) > 1:
        return (f"ASK the resume box shows {len(state['chips'])} files ({', '.join(state['chips'])[:120]}) - "
                f"remove all but one {name} with its x on the page")
    return (f"ASK the form would send {len(state['sent'])} files ({', '.join(state['sent'])[:120]}), the box shows one - "
            "reload the page, then fill again")


def holds(page, q: dict) -> bool:
    """The answer still shows, read off the page once the form had time to keep it (form.recheck),
    each kind as loxo.md "Read back" records it: a box by its value (phone by digits), radios + ticks by
    each one's own state, a list by the option picked, the resume by its one chip = the one file the form
    would send. Nothing to read =
    False."""
    native, kind = q.get("native") or "", q["kind"]
    if native in ("loxo:radio", "loxo:checkbox"):
        ticks = group(page, q, native.split(":")[1]).evaluate_all(OPTIONS)
        want = wanted(q)
        return bool(ticks) and all((w.casefold() in want) == on for w, on in ticks)
    if kind == "file":
        host = page.locator(f"{FORM} {FILE_HOST}").first
        if not host.count():
            return False
        state = file_state(host)
        return len(state["chips"] or []) == 1 and state["sent"] == state["chips"]
    field = by_name(page, q["id"])
    if not field.count():
        return False
    if native == "loxo:select":
        return field.evaluate("e => e.selectedOptions[0] ? e.selectedOptions[0].text : ''").strip().casefold() in wanted(q)
    got, value = field.input_value(), str(q["answer"])
    return digits(got) == digits(value) if kind == "phone" else got == value


def fill(page, q: dict, resume_file: str | None) -> str:
    native, kind, value = q.get("native") or "", q["kind"], q["answer"]
    # the opt-in box: texts + Terms of Service in its fine print - the applicant's own tick, whatever its words
    if native == "loxo:consent" or signs(q["title"]):
        return left_on_page(q | {"title": q["title"] or "Contact consent - texts, Terms of Service"})
    if kind == "file":
        if q.get("key") != "resume":
            return f"ASK not the resume box ({q['title']}) - the user uploads their own file there"
        host = page.locator(f"{FORM} {FILE_HOST}").first
        if not host.count():
            return "FAIL question not on page"
        return put_file(page, host, resume_file) if value is True and resume_file else "skipped - upload not approved"
    if native in ("loxo:radio", "loxo:checkbox"):
        return put_ticks(page, q, native.split(":")[1])
    field = by_name(page, q["id"])
    if not field.count():
        return "FAIL question not on page"
    field.scroll_into_view_if_needed()
    if native == "loxo:select":
        return put_select(field, q)
    return put_text(field, value, kind)
