"""JazzHR (<co>.applytojob.com): questions read off the posting page's own form, answers typed into it.

Measured facts and why each rule exists: app/docs/apply/jazzhr.md.
"""
import contextlib
import re
from html.parser import HTMLParser
from pathlib import Path

import httpx

from apply.questions import key_from_title, left_on_page, question, signs

NAME = "JazzHR"
# /apply/<id>/<slug>; freehire adds ?utm_source=freehire.me. /apply/job/<id>/stage-one is a form's POST target
POSTING_URL = re.compile(r"https?://([\w-]+)\.applytojob\.com/apply/(?!jobs?/)([A-Za-z0-9]{6,})(?:/([^/?#]*))?", re.I)
SOURCES = ("jazzhr",)
EXAMPLES = ("https://acme.applytojob.com/apply/AbCdE00001/Test-Role",
            "https://acme.applytojob.com/apply/AbCdE00001/Test-Role?utm_source=freehire.me",
            "https://acme.applytojob.com/apply/AbCdE00001")
# the form is in the posting page's HTML (4 of 4 tenants, 2026-10-03): a plain GET, no browser
QUESTIONS_OVER_HTTP = True
FORM = "form_submit_new_resume"
READY = f"#{FORM}"
# system fields by the middle of their id (resumator-<field>-value) -> shared key / kind
SYSTEM_KEY = {"firstname": "first_name", "lastname": "last_name", "email": "email", "phone": "phone",
              "address": "street", "city": "city", "state": "state", "postal": "zip", "resume": "resume"}
SYSTEM_KIND = {"email": "email", "phone": "phone", "resume": "file", "start": "date"}
# City / State / Postal carry no label, only a placeholder; one "Address" label (asterisk or not) is over all four
ADDRESS_PARTS = ("city", "state", "postal")
# the paste-in alternative to the upload, and a script-only box (class none): never questions
SKIP = {"resumator-resumetext-value", "resumator-xml-value"}
# a select's first option = no answer: employer questions / system fields (4 of 4)
NO_ANSWER = {"resumator_no_selection", "0"}
FIELD = re.compile(r"^resumator-(.+)-value$")
CHECK_ANSWER = "resumator-questionnaire-checkbox-answer"
ATTACH = "#resumator-choose-upload"
# the page's own words over the file box: "Attach resume as .pdf, .doc, ... (limit 5MB)" (4 of 4)
UPLOAD_TEXT = "#resumator-resume-upload-wrapper .resumator-resume-text"
LIMIT = re.compile(r"\blimit\s*(\d+(?:\.\d+)?)\s*MB\b", re.I)
# what JazzHR's own script writes on a failed check (only at Submit: submit-resume.js, 2026-10-06)
PAGE_ERROR = "#resumator-resume .resumator_label_error, #resumator-resume .dv_error"
# a taken-down posting: 410 + the careers page + the posting's own words, no form (16 of 16, 2026-10-06)
SAID_GONE = re.compile(r"this position is no longer available|hiring for this position has been put on hold", re.I)
GONE = (404, 410)
IDLE_WAIT_MS = 15000


def matches(url: str) -> bool:
    return bool(POSTING_URL.match(url.strip()))


def parse_url(url: str) -> tuple[str, str]:
    """(tenant, posting id)."""
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not a JazzHR posting link: {url}")
    return m.group(1), m.group(2)


def application_url(url: str) -> str:
    # the form posts back to the posting link itself; the tracking tail is dropped
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not a JazzHR posting link: {url}")
    return m.group(0)


def norm(s: str) -> str:
    return " ".join(s.split())


class Form(HTMLParser):
    """The application form as read: controls in page order, label text + asterisk by `for`."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.inside, self.controls, self.labels, self.required = False, [], {}, set()
        self.label = None  # `for` of the label being read; a select inside it ends its text
        self.select = self.option = None

    def handle_starttag(self, tag, attrs):
        a = {k: v or "" for k, v in attrs}
        if tag == "form" and a.get("id") == FORM:
            self.inside = True
        if not self.inside:
            return
        if tag == "label" and a.get("for") and "checkbox" not in a.get("class", "").split():
            self.label = a["for"]
            self.labels.setdefault(self.label, "")
        elif tag == "i" and "asterisk" in a.get("class", "").split() and self.label:
            self.required.add(self.label)
        elif tag == "br" and self.label:
            self.labels[self.label] += " "
        elif tag in ("input", "textarea"):
            self.controls.append({"tag": tag, **a})
        elif tag == "select":
            self.select = {"tag": tag, **a, "options": []}
            self.controls.append(self.select)
            self.label = None
        elif tag == "option" and self.select is not None:
            self.option = [a.get("value", ""), ""]
            self.select["options"].append(self.option)

    def handle_endtag(self, tag):
        if tag == "form":
            self.inside = False
        elif tag == "label":
            self.label = None
        elif tag == "select":
            self.select = None
        elif tag == "option":
            self.option = None

    def handle_data(self, data):
        if self.option is not None:
            self.option[1] += data
        elif self.label and not data.strip() == "*":
            self.labels[self.label] += data


def yes_no(options: list[str]) -> bool:
    return sorted(o.casefold() for o in options) == ["no", "yes"]


def from_html(html: str) -> list[dict]:
    form = Form()
    form.feed(html)
    if not form.controls:
        raise ValueError("no application form on the posting page - it may have closed")
    label = lambda id: norm(form.labels.get(id, "")).rstrip("*").strip()
    ticks = {}  # checkbox question number -> option values, in page order
    for c in form.controls:
        if m := re.match(r"resumator-checkbox-(\d+)-\d+$", c.get("id", "")):
            ticks.setdefault(m.group(1), []).append(c.get("value", ""))
    address_required = "resumator-address-value" in form.required
    out = []
    for c in form.controls:
        id, cls, typ = c.get("id", ""), c.get("class", "").split(), c.get("type", "text").casefold()
        if not id or id in SKIP or (c["tag"] == "input" and typ == "checkbox"):
            continue
        if typ == "hidden":
            if CHECK_ANSWER not in cls:
                continue
            # one hidden box per checkbox question; its ticks are the options
            options = ticks.get(id.removeprefix("resumator-questionnaire-q"), [])
            title = label(id)
            kind = "yesno" if yes_no(options) or len(options) == 1 else "multichoice"
            out.append(question(id, title, kind, id in form.required, options, None, "jazzhr:checkboxes"))
            continue
        field = m.group(1) if (m := FIELD.match(id)) else None
        if field in ADDRESS_PARTS:
            title, required = norm(c.get("placeholder", "")) or field.title(), address_required
        else:
            title, required = label(id), id in form.required
        if c["tag"] == "select":
            options = [norm(t) for v, t in c["options"] if v not in NO_ANSWER]
            kind = "yesno" if yes_no(options) else "choice"
            native = "jazzhr:select"
        else:
            options = []
            kind = SYSTEM_KIND.get(field) or ("longtext" if c["tag"] == "textarea" else
                                              {"email": "email", "tel": "phone"}.get(typ, "text"))
            native = f"jazzhr:{'date' if 'resumator-datepicker' in cls else c['tag'] if c['tag'] == 'textarea' else typ}"
        out.append(question(id, title, kind, required, options, SYSTEM_KEY.get(field) or key_from_title(title, kind), native))
    return out


def posting_gone(r) -> str:
    """Why a 404 / 410 posting has no form, in the page's own words when it has them."""
    said = SAID_GONE.search(r.text or "")
    return f"the posting says \"{said.group()}\" - it may have closed" if said else "posting not found - it may have closed"


def questions(url: str) -> list[dict]:
    r = httpx.get(application_url(url), timeout=30, follow_redirects=True)
    # unknown id: 404; taken down: 410 + "This position is no longer available" (jazzhr.md "Closed posting")
    if r.status_code in GONE:
        raise ValueError(posting_gone(r))
    r.raise_for_status()
    return from_html(r.text)


def closed(url: str) -> str | None:
    """Why the form isn't there (form.closed, when the page shows no form and no closed words the
    shared list knows - "put on hold"): JazzHR's own answer for the posting link. None = form there."""
    try:
        r = httpx.get(application_url(url), timeout=30, follow_redirects=True)
    except httpx.HTTPError as e:
        return f"can't tell if the posting is open - JazzHR didn't answer ({type(e).__name__})"
    if r.status_code in GONE:
        return posting_gone(r)
    if r.status_code != 200:
        return f"can't tell if the posting is open - JazzHR answered {r.status_code}"
    try:
        from_html(r.text)
    except ValueError as e:
        return str(e)
    return None


def ids_on_page(page) -> list[str]:
    return page.eval_on_selector_all(
        f"#{FORM} input[id], #{FORM} select[id], #{FORM} textarea[id]",
        f"""es => es.filter(e => e.type === 'hidden' ? e.classList.contains('{CHECK_ANSWER}')
              : e.type !== 'checkbox' && !e.id.startsWith('g-recaptcha') && !{sorted(SKIP)}.includes(e.id)).map(e => e.id)""")


def by_id(page, id: str):
    return page.locator(f'#{FORM} [id="{id}"]').first


def digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def put_text(field, value, kind: str) -> str:
    v = str(value)
    field.fill(v)
    # the datepicker opens on focus: Escape shuts it, the typed date stays
    if kind == "date":
        field.press("Escape")
    field.evaluate("e => { e.dispatchEvent(new Event('change', {bubbles: true})); e.blur(); }")
    got = field.input_value()
    return "ok" if (digits(got) == digits(v) if kind == "phone" else got == v) else f"FAIL shows '{got}'"


def option_for(options: list[tuple[str, str]], want: str) -> str | None:
    """The value of the option whose text is the answer, any case (YES / NO on tenant B) - never the no-answer one."""
    w = norm(want).casefold()
    return next((v for v, t in options if v not in NO_ANSWER and norm(t).casefold() == w), None)


def put_select(field, value, kind: str) -> str:
    if kind == "yesno":
        value = "Yes" if str(value).casefold() in ("yes", "true") else "No"
    options = field.evaluate("e => [...e.options].map(o => [o.value, o.text])")
    hit = option_for(options, str(value))
    if hit is None:
        offered = ", ".join(norm(t) for v, t in options if v not in NO_ANSWER)
        return f"ASK no option '{value}'; offered: {offered[:200]}"
    field.select_option(value=hit)
    got = field.evaluate("e => e.value")
    return "ok" if got == hit else f"FAIL shows '{got}'"


def put_ticks(page, q: dict) -> str:
    """Tick the checkbox(es) whose value is the answer, untick the rest; read the ticks back -
    the hidden answer box is only joined from them on Submit."""
    n = q["id"].removeprefix("resumator-questionnaire-q")
    boxes = page.locator(f'#{FORM} input[type=checkbox][id^="resumator-checkbox-{n}-"]')
    want = wanted(q)
    values = [norm(b.get_attribute("value") or "") for b in boxes.all()]
    if missing := want - {v.casefold() for v in values}:
        return f"ASK no option '{sorted(missing)[0]}'; offered: {', '.join(values)}"
    for box, v in zip(boxes.all(), values):
        if (v.casefold() in want) != box.is_checked():
            box.evaluate("e => e.click()")  # like a person's click: the page's own handlers run
    wrong = [v for box, v in zip(boxes.all(), values) if (v.casefold() in want) != box.is_checked()]
    return "ok" if not wrong else f"FAIL '{wrong[0]}' shows the wrong tick"


def wanted(q: dict) -> set[str]:
    """The option texts (any case) an answer picks; a lone box ticked = yes."""
    value = q["answer"]
    if q["kind"] == "yesno":
        value = ["Yes" if str(value).casefold() in ("yes", "true") else "No"]
        if q.get("native") == "jazzhr:checkboxes" and len(q["options"]) == 1:
            value = q["options"] if value == ["Yes"] else []
    return {norm(str(v)).casefold() for v in (value if isinstance(value, list) else [value])}


def too_big(page, path: str) -> str:
    """The page's own limit ("limit 5MB") against the file: JazzHR checks nothing on choosing - the
    server decides at Submit (unmeasured) - so its stated words are the only check before then."""
    words = norm(" ".join(page.locator(UPLOAD_TEXT).all_inner_texts()))
    if not (m := LIMIT.search(words)):
        return ""
    size = Path(path).stat().st_size
    return words if size > float(m.group(1)) * 1024 * 1024 else ""


def put_file(page, field, path: str) -> str:
    """Page idle first (as Greenhouse, Ashby), then "Attach resume" - a link that only shows the hidden
    file box (href="#") - so the user sees the file chosen; the file goes with the form at Submit (0
    writes on choosing, 4 of 4). Ok = the box holds the file, it fits the page's stated limit, and the
    page shows no error of its own by the resume box."""
    with contextlib.suppress(Exception):  # a page that keeps polling never goes idle: the read decides
        page.wait_for_load_state("networkidle", timeout=IDLE_WAIT_MS)
    attach = page.locator(ATTACH)
    if not field.is_visible() and attach.count() and attach.first.is_visible():
        attach.first.click()
    field.set_input_files(path)
    if field.evaluate("e => e.files[0] ? e.files[0].name : ''") != Path(path).name:
        return "ASK upload not confirmed on page - check the resume box"
    if said := norm(" ".join(page.locator(PAGE_ERROR).all_inner_texts())):
        return f"FAIL the page says '{said}' - check the resume box"
    if said := too_big(page, path):
        return f"FAIL the file is bigger than the page allows ('{said}') - the user picks a smaller file"
    return "ok"


def holds(page, q: dict) -> bool:
    """The answer still shows, read off the page once the form had time to keep it (form.recheck),
    each kind as jazzhr.md "Read back" records it: a box by its value (phone by digits), a dropdown by
    the option text it shows - never the no-answer one -, a checkbox question by each box's own tick
    (not the hidden box JazzHR joins them into at Submit), a file by the name the box holds."""
    field = by_id(page, q["id"])
    if not field.count():
        return False
    kind, value = q["kind"], q["answer"]
    if q.get("native") == "jazzhr:checkboxes":
        n = q["id"].removeprefix("resumator-questionnaire-q")
        ticks = page.locator(f'#{FORM} input[type=checkbox][id^="resumator-checkbox-{n}-"]').evaluate_all(
            "bs => bs.map(b => [b.value, b.checked])")
        want = wanted(q)
        return bool(ticks) and all((norm(v).casefold() in want) == on for v, on in ticks)
    if kind == "file":
        return bool(field.evaluate("e => e.files && e.files[0] ? e.files[0].name : ''"))
    if q.get("native") == "jazzhr:select":
        got, text = field.evaluate("e => [e.value, e.selectedOptions[0] ? e.selectedOptions[0].text : '']")
        return got not in NO_ANSWER and norm(text).casefold() in wanted(q)
    got = field.input_value()
    return digits(got) == digits(str(value)) if kind == "phone" else got == str(value)


def fill(page, q: dict, resume_file: str | None) -> str:
    if signs(q["title"]):
        return left_on_page(q)
    kind, value = q["kind"], q["answer"]
    field = by_id(page, q["id"])
    if not field.count():
        return "FAIL question not on page"
    if kind == "file":
        if q.get("key") != "resume":
            return f"ASK not the resume box ({q['title']}) - the user uploads their own file there"
        return put_file(page, field, resume_file) if value is True and resume_file else "skipped - upload not approved"
    if q.get("native") == "jazzhr:checkboxes":
        return put_ticks(page, q)
    field.scroll_into_view_if_needed()
    if q.get("native") == "jazzhr:select":
        return put_select(field, value, kind)
    return put_text(field, value, kind)
