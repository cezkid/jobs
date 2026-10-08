"""Teamtailor (<employer>.teamtailor.com or the employer's own domain, /jobs/<id>-<slug>): questions read off the
form page itself, answers typed into it.

Measured facts and why each rule exists: app/docs/apply/teamtailor.md.
"""
import contextlib
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from apply.questions import key_from_title, left_on_page, question, signs

NAME = "Teamtailor"
# any host: 6 of 10 owner links sit on the employer's own domain (jobs.<x>.com, people.<x>.com), so the path is
# the tell - /jobs/<5-8 digits>-<slug> at the root - and the page's Teamtailor assets confirm it (questions, closed)
POSTING_URL = re.compile(r"(https?)://([\w.-]+)/jobs/(\d{5,8})-([\w-]+?)(?:/applications/new)?/?(?=[?#]|$)", re.I)
SOURCES = ("teamtailor",)
EXAMPLES = ("https://acme.na.teamtailor.com/jobs/700001-software-engineer",
            "https://acme.na.teamtailor.com/jobs/700001-software-engineer?utm_source=freehire.me",
            "https://jobs.acme.com/jobs/8400001-software-engineer/applications/new")
QUESTIONS_OVER_HTTP = True
# the resume goes to Teamtailor's storage as soon as it is chosen (presigned upload, before Submit)
FILE_ON_CHOICE = True
# the address box asks the employer's Teamtailor site for places after 3 letters (location_suggestions)
SEARCHED_AS_TYPED = ("location",)
# every Teamtailor page loads its scripts from here, own domain or not (10 of 10, 2026-10-07)
CDN = "teamtailor-cdn.com"
FORM = "form#job-application-form"
READY = f'{FORM} input[name="candidate[first_name]"]'
FRAME = {"Turbo-Frame": "application_form"}
# a taken-down posting: the posting page, no form, "no longer active" (1 of 10, 2026-10-07)
CLOSED = re.compile(r"no longer (?:active|available|accepting applications|open)[^<.]*", re.I)
STANDARD = {"candidate[first_name]": ("text", "first_name"), "candidate[last_name]": ("text", "last_name"),
            "candidate[email]": ("email", "email"), "candidate[phone]": ("phone", "phone"),
            "candidate[location][query]": ("location", "location")}
ANSWER = re.compile(r"candidate\[answers_attributes\]\[\d+\]\[(\w+)\]")
# upload boxes by their label's `for`: Dropzone draws the file box (no name), the link box sits in a template
FILES = {"candidate_resume_remote_url": "candidate[resume_remote_url]",
         "candidate_file_remote_url": "candidate[file_remote_url]"}
RESUME = "candidate[resume_remote_url]"
UPLOAD = "forms--inputs--upload"
# the slider's own number box (no label, synced to the slider) and LinkedIn's sign-in boxes: never questions
NOT_QUESTIONS = ("range-custom_number",)
TICKS = ("teamtailor:boolean", "teamtailor:qualifying", "teamtailor:choice", "teamtailor:choices")
QUALIFY_MESSAGE = '[data-careersite--form-target="qualifyingMessageWrapper"]'
RESUME_BOX = "#upload_resume_field"
PREVIEW = f'{RESUME_BOX} [data-forms--inputs--upload-target="previewsContainer"]'
ERROR = f'{RESUME_BOX} [data-forms--inputs--upload-target="errorContainer"]'
SUGGESTIONS = '[data-forms--inputs--location-target="suggestionsList"] [role=option]'
PLACES_ERROR = '[data-forms--inputs--location-target="errorText"]'
IDLE_WAIT_MS, SHOWN_WAIT_MS, PLACES_WAIT_MS = 15000, 15000, 8000
VOID = {"input", "br", "img", "meta", "link", "hr", "source", "area", "base", "col", "embed", "wbr", "track", "param"}


def matches(url: str) -> bool:
    return bool(POSTING_URL.match(url.strip()))


def parse_url(url: str) -> tuple[str, str, str]:
    """(scheme://host, posting id, slug)."""
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not a Teamtailor posting link: {url}")
    return f"https://{m.group(2).lower()}", m.group(3), m.group(4)


def application_url(url: str) -> str:
    origin, id, slug = parse_url(url)
    return f"{origin}/jobs/{id}-{slug}/applications/new"


def on_tab(url: str, tab_url: str) -> bool:
    """Same host + same posting id; the slug may change (a renamed posting redirects to its new slug)."""
    origin, id, _ = parse_url(url)
    tab = urlsplit(tab_url)
    return f"https://{tab.hostname}" == origin and tab.path.startswith(f"/jobs/{id}-")


def norm(s) -> str:
    return " ".join(str(s).split())


# --- the form page, read without a browser ---

class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.children, self.parent = tag, attrs, [], parent

    def get(self, key, default=""):
        return self.attrs.get(key, default)

    def classes(self) -> list[str]:
        return self.get("class").split()


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = self.at = Node("#root", {}, None)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {k: v or "" for k, v in attrs}, self.at)
        self.at.children.append(node)
        if tag not in VOID:
            self.at = node

    def handle_startendtag(self, tag, attrs):
        self.at.children.append(Node(tag, {k: v or "" for k, v in attrs}, self.at))

    def handle_endtag(self, tag):
        node = self.at
        while node is not self.root and node.tag != tag:
            node = node.parent
        if node is not self.root:
            self.at = node.parent

    def handle_data(self, data):
        self.at.children.append(data)


def walk(node):
    """Elements under node in page order; never inside a <template> (Teamtailor's upload preview copy)."""
    for child in node.children:
        if isinstance(child, Node) and child.tag != "template":
            yield child
            yield from walk(child)


def text(node) -> str:
    """Words shown, without the asterisk and the screen-reader "Required"."""
    out = []
    for child in node.children:
        if isinstance(child, str):
            out.append(child)
        elif child.tag not in ("sup", "script", "style", "template") and "sr-only" not in child.classes():
            out.append(" " + text(child) + " ")
    return norm("".join(out))


def starred(node) -> bool:
    return any(n.tag == "sup" and n.get("data-asterisk") == "true" for n in walk(node))


def has_control(node) -> bool:
    return any(n.tag in ("input", "textarea", "select") for n in walk(node))


def element_siblings_after(node):
    seen = False
    for child in node.parent.children:
        if child is node:
            seen = True
        elif seen and isinstance(child, Node):
            yield child


def label_title(label) -> str:
    """The label's words, then the line under it when it has one (the question often sits there)."""
    title = text(label)
    after = next(element_siblings_after(label), None)
    if after is not None and after.tag == "div" and not has_control(after) and (more := text(after)):
        title = f"{title} - {more}"
    return title


def legend_title(legend) -> str:
    return " - ".join(t for t in (text(c) for c in legend.children if isinstance(c, Node)) if t)


def ancestor(node, test):
    while node is not None and not test(node):
        node = node.parent
    return node


def form_of(page: str):
    tree = Tree()
    tree.feed(page)
    form = next((n for n in walk(tree.root) if n.tag == "form" and n.get("id") == "job-application-form"), None)
    if form is None:
        if CDN not in page:
            raise ValueError("not a Teamtailor form - the page has no Teamtailor application")
        if said := CLOSED.search(page):
            raise ValueError(f"posting closed on Teamtailor - it says '{norm(said.group(0))}'")
        raise ValueError("no application form on the Teamtailor page - the posting may have closed")
    return form


def read_form(page: str) -> list[dict]:
    form = form_of(page)
    labels = {n.get("for"): n for n in walk(form) if n.tag == "label" and n.get("for")}
    out, seen = [], set()
    for n in walk(form):
        if n.tag == "div" and UPLOAD in n.get("data-controller").split():
            label = next((x for x in walk(n) if x.tag == "label"), None)
            target = label.get("for") if label else n.get("id")
            id = FILES.get(target, f"upload:{target}")
            if id not in seen:
                seen.add(id)
                title = text(label) if label else "File"
                key = "resume" if id == RESUME else key_from_title(title, "file")
                out.append(question(id, title, "file", starred(label) if label else False, (), key, "teamtailor:upload"))
            continue
        if n.tag not in ("input", "textarea", "select"):
            continue
        name, typ = n.get("name"), n.get("type", "text").lower()
        if (not name or name in seen or name in NOT_QUESTIONS or name.startswith("candidate[location][") and name != "candidate[location][query]"
                or n.tag == "input" and typ in ("hidden", "submit", "button", "file")):
            continue
        seen.add(name)
        if q := control(form, n, name, typ, labels):
            out.append(q)
    return out


def control(form, n, name: str, typ: str, labels: dict) -> dict | None:
    label = labels.get(n.get("id"))
    title = label_title(label) if label else ""
    required = starred(label) if label else "required" in n.attrs
    if name in STANDARD:
        kind, key = STANDARD[name]
        return question(name, text(label) if label else name, kind, required, (), key, "teamtailor:standard")
    if name.endswith("[cover_letter]"):
        return question(name, title or "Cover letter", "longtext", required, (), None, "teamtailor:text")
    if name.startswith("candidate[consent_given"):
        return question(name, title, "yesno", required, ["Yes", "No"], None, "teamtailor:consent")
    m = ANSWER.fullmatch(name.removesuffix("[]"))
    if not m and typ in ("radio", "checkbox"):  # the form's own pick lists ("Locations": the offices to apply for)
        field = "choice"
    elif not m:  # a box no question names: the user's own on the page
        return question(name, title, "text", required, (), None, "teamtailor:other")
    else:
        field = m.group(1)
    box = ancestor(n, lambda a: a.get("data-question-mandatory") or a.get("data-careersite--form-target") == "qualifyingAnswers")
    qualifying = box is not None and box.get("data-careersite--form-target") == "qualifyingAnswers"
    required = required or qualifying or (box is not None and box.get("data-question-mandatory") == "true")
    if field in ("boolean", "choice"):
        fieldset = ancestor(n, lambda a: a.tag == "fieldset")
        legend = next((c for c in fieldset.children if isinstance(c, Node) and c.tag == "legend"), None) if fieldset else None
        title = legend_title(legend) if legend else title
        if legend is not None:
            required = required or starred(legend)
    if field == "boolean":
        return question(name, title, "yesno", required, ["Yes", "No"], None,
                        "teamtailor:qualifying" if qualifying else "teamtailor:boolean")
    if field == "choice":
        if n.tag == "select":
            options = [text(o) for o in walk(n) if o.tag == "option" and o.get("value")]
            return question(name, title, "choice", required, options, None, "teamtailor:select")
        group = [x for x in walk(form) if x.tag == "input" and x.get("name") == name]
        options = [text(labels[x.get("id")]) if x.get("id") in labels else x.get("value") for x in group]
        multi = typ == "checkbox"
        return question(name, title, "multichoice" if multi else "choice", required, options, None,
                        "teamtailor:choices" if multi else "teamtailor:choice")
    if field == "text":
        kind = "longtext" if n.tag == "textarea" else "text"
        return question(name, title, kind, required, (), key_from_title(title, kind), "teamtailor:text")
    if field == "number":
        return question(name, title, "number", required, (), None, "teamtailor:number")
    if field == "range":
        unit = f" {n.get('data-unit')}" if n.get("data-unit") else ""
        scale = f"{n.get('min', '0')} to {n.get('max', '100')}{unit}, steps of {n.get('step', '1')}"
        return question(name, f"{title} ({scale})", "number", required, (), None, "teamtailor:range")
    return question(name, title, "text", required, (), None, f"teamtailor:{field}")


def form_page(url: str) -> str:
    """The form as the posting's lazy frame asks for it (whole form, no page around it)."""
    r = httpx.get(application_url(url), headers=FRAME, timeout=30, follow_redirects=True)
    if r.status_code in (404, 410):
        raise ValueError("posting not found on Teamtailor - it may have closed")
    r.raise_for_status()
    return r.text


def questions(url: str) -> list[dict]:
    return read_form(form_page(url))


def closed(url: str) -> str | None:
    """Why the form isn't there (form.closed, when the page shows no form): None = Teamtailor still has it."""
    try:
        form_of(form_page(url))
    except httpx.HTTPStatusError as e:
        return f"can't tell if the posting is open - Teamtailor answered {e.response.status_code}"
    except httpx.HTTPError as e:
        return f"can't tell if the posting is open - Teamtailor didn't answer ({type(e).__name__})"
    except ValueError as e:
        return str(e)
    return None


# --- the page in the browser ---

def ids_on_page(page) -> list[str]:
    """Boxes by name (radios once), the upload boxes by their link box's name; never the slider's own
    number box or a hidden one."""
    return page.evaluate(f"""() => {{
        const form = document.querySelector('{FORM}');
        if (!form) return [];
        const out = [];
        for (const e of form.querySelectorAll('input, select, textarea, [data-controller~="{UPLOAD}"]')) {{
            let name = e.name;
            if (e.matches('[data-controller~="{UPLOAD}"]')) {{
                const l = e.querySelector('label[for]');
                const f = l ? l.htmlFor : e.id;
                name = {{{", ".join(f'"{k}": "{v}"' for k, v in FILES.items())}}}[f] || 'upload:' + f;
            }} else if (!name || ['hidden', 'submit', 'button', 'file'].includes(e.type) || name === 'range-custom_number'
                       || (name.startsWith('candidate[location][') && name !== 'candidate[location][query]')) continue;
            if (!out.includes(name)) out.push(name);
        }}
        return out; }}""")


def locate(page, q: dict):
    return page.locator(f'{FORM} [name="{q["id"]}"]').first


def digits(s) -> str:
    return re.sub(r"\D", "", str(s))


def e164(value) -> str | None:
    """The phone as the box keeps it (intl-tel-input, international form): +<country><number>."""
    v, d = str(value).strip(), digits(value)
    if v.startswith("+") and len(d) >= 8:
        return "+" + d
    if len(d) == 10:
        return "+1" + d
    if len(d) == 11 and d.startswith("1"):
        return "+" + d
    return None


def number(value) -> str:
    return re.sub(r"[^\d.]", "", str(value))


def wanted(q: dict) -> set[str]:
    """What the radios / ticks show for the answer: boolean radios by value, choices by their words."""
    value = q["answer"]
    if q["kind"] == "yesno":
        return {"true" if str(value).casefold() in ("yes", "true") else "false"}
    return {norm(v).casefold() for v in (value if isinstance(value, list) else [value])}


# each radio / tick: [its value, its words (label for=id), checked]
OPTIONS = """bs => bs.map(b => {
    const l = b.id && document.querySelector(`label[for="${b.id}"]`);
    return [b.value, (l ? l.innerText : b.value).replace(/\\s+/g, ' ').trim(), b.checked]; })"""


def ticks(page, q: dict) -> tuple[list, object]:
    """(what wanted() compares, checked) per radio / tick: boolean by value, the rest by words."""
    boxes = page.locator(f'{FORM} input[name="{q["id"]}"], {FORM} input[name="{q["id"]}[]"]')
    by_value = q.get("native") in ("teamtailor:boolean", "teamtailor:qualifying")
    return [((v if by_value else t).casefold(), on) for v, t, on in boxes.evaluate_all(OPTIONS)], boxes


def qualify_message(page) -> str:
    box = page.locator(QUALIFY_MESSAGE).first
    # shown by dropping its "hidden" class; its aria-hidden stays "true" (live, 2026-10-07)
    if not box.count() or "hidden" in (box.get_attribute("class") or "").split() or not box.is_visible():
        return ""
    return norm(box.locator("p").first.inner_text() if box.locator("p").count() else box.inner_text())


def put_ticks(page, q: dict) -> str:
    """Click the one(s) the answer names, unclick the rest (ticks only); read them back. A requirement
    answered no shows the form's own message: the answer stays the user's, never changed to get past."""
    got, boxes = ticks(page, q)
    want = wanted(q)
    if missing := want - {k for k, _ in got}:
        offered = ", ".join(t for _, t, _ in boxes.evaluate_all(OPTIONS))
        return f"ASK no option '{sorted(missing)[0]}'; offered: {offered}"
    for box, (k, on) in zip(boxes.all(), got):
        if (k in want) != on and (k in want or q.get("native") == "teamtailor:choices"):
            box.evaluate("e => e.click()")  # like a person's click: the form's own handlers run
    got, _ = ticks(page, q)
    if wrong := [k for k, on in got if (k in want) != on]:
        return f"FAIL '{wrong[0]}' shows the wrong choice"
    if q.get("native") == "teamtailor:qualifying" and (said := qualify_message(page)):
        return (f"ASK the form says '{said}' - this answer is the user's and stays as given, never changed "
                "to get past it; the user decides whether to apply")
    return "ok"


def write(field, v: str, events=("input", "change", "blur", "focusout")) -> None:
    """Type the value; when the cookie notice opens as a takeover box it holds the keyboard (focus trap: 2 of 10
    postings, 2026-10-07) and the typing lands nowhere - then set it the way the page's own input would, with its
    events. The cookie notice itself stays the user's (never clicked)."""
    field.fill(v)
    field.blur()
    if field.input_value() != v:
        field.evaluate("""(e, [v, events]) => {
            Object.getOwnPropertyDescriptor(Object.getPrototypeOf(e), 'value').set.call(e, v);
            for (const t of events) e.dispatchEvent(new Event(t, {bubbles: t !== 'blur'})); }""", [v, list(events)])


def put_text(field, value, kind: str) -> str:
    v = number(value) if kind == "number" else str(value)
    if kind == "number" and not v:
        return f"ASK '{value}' is not a number - the box takes digits only"
    write(field, v)
    got = field.input_value()
    return "ok" if got == v else f"FAIL shows '{got}'"


def put_phone(field, value) -> str:
    """The box keeps numbers in international form (+1 ...): a 10-digit number is taken as US / Canada."""
    v = e164(value)
    if not v:
        return f"ASK '{value}' needs its country code (+44 ...) - the phone box takes numbers in international form"
    write(field, v)
    if field.get_attribute("aria-invalid") == "true":
        return f"ASK the page says '{v}' is not a valid number - check the phone number"
    got = field.input_value()
    return "ok" if digits(got) == digits(v) else f"FAIL shows '{got}'"


def put_range(page, q: dict) -> str:
    """A slider: its own number box (hidden until 'Edit number') takes the value and moves the slider."""
    slider = locate(page, q)
    if not slider.count():
        return "FAIL question not on page"
    v = number(q["answer"])
    if not v:
        return f"ASK '{q['answer']}' is not a number - the slider takes one number"
    got = slider.evaluate("""(s, v) => {
        const c = s.closest('[data-controller~="forms--inputs--range"]');
        const box = c && c.querySelector('input[name="range-custom_number"]');
        const e = box || s;
        e.value = v;
        e.dispatchEvent(new Event('input', {bubbles: true}));
        if (!box) e.dispatchEvent(new Event('change', {bubbles: true}));
        return s.value; }""", v)
    if float(got) == float(v):
        return "ok"
    return (f"ASK the slider runs {slider.get_attribute('min')} to {slider.get_attribute('max')} in steps of "
            f"{slider.get_attribute('step') or 1} - it took {got} for {v}; the user sets it on the page")


def place_id(page) -> str:
    box = page.locator(f'{FORM} input[name="candidate[location][place_id]"]')
    return box.first.input_value() if box.count() else ""


def put_location(page, field, value: str) -> str:
    """Type the place, pick the suggestion that names it, read the kept place back."""
    if not value.strip():
        return "ASK no place given - the user types it on the page"
    field.fill("")
    field.press_sequentially(value, delay=60)
    trapped = field.input_value() != value
    if trapped:  # the cookie notice holds the keyboard (see write): the box's own input event
        write(field, value, events=("input",))
    options = page.locator(SUGGESTIONS)
    try:
        options.first.wait_for(timeout=PLACES_WAIT_MS)
    except Exception:
        said = page.locator(PLACES_ERROR)
        said = norm(said.first.inner_text()) if said.count() and said.first.is_visible() else ""
        return f"ASK no place matched '{value}'{f' - the page says {said!r}' if said else ''} - the user picks it on the page"
    texts = [norm(t) for t in options.all_inner_texts()]
    parts = [p.strip().casefold() for p in value.split(",") if p.strip()]
    towns = [i for i, t in enumerate(texts) if t.casefold().startswith(parts[0])]
    # the place naming every part of the answer (Springfield, MO - not the first Springfield), the one with the
    # fewest parts besides; a bare town two places share is the user's pick
    whole = [i for i in towns if all(p in [w.strip() for w in texts[i].casefold().split(",")] for p in parts)] or towns
    sizes = sorted(len(texts[i].split(",")) for i in whole)
    pick = next((i for i in whole if len(texts[i].split(",")) == sizes[0]), None) if sizes[1:2] != sizes[:1] else None
    if pick is None:
        field.fill("")
        return f"ASK no place matches '{value}' alone; offered: {', '.join(texts[:5])}"
    if trapped:  # a click's focus jumps to the notice and the press lands beside the place: the place's own click
        options.nth(pick).dispatch_event("click")
    else:
        options.nth(pick).click()
    for _ in range(50):  # the page asks for the place's details, then keeps them
        if place_id(page):
            return "ok"
        page.wait_for_timeout(100)
    return "FAIL the place was picked but the page didn't keep it"


def resume_says(page) -> tuple[str, str, str]:
    """(file name the box shows, the link Teamtailor gave it, the page's error words)."""
    error = page.locator(ERROR).first
    words = norm(error.inner_text()) if error.count() and "hidden" not in (error.get_attribute("class") or "").split() else ""
    name = page.locator(f"{PREVIEW} [data-dz-name]")
    link = page.locator(f'{PREVIEW} input[name="{RESUME}"]')
    return (norm(name.first.inner_text()) if name.count() else "",
            link.first.input_value() if link.count() else "", words)


def put_file(page, path: str) -> str:
    """Page idle first (the drop box loads after the form), then the file chosen: it goes to Teamtailor at
    once. Ok = the box shows the file's name and Teamtailor's link for it, no error; the page's own words ->
    FAIL; neither -> ASK."""
    with contextlib.suppress(Exception):  # a page that keeps polling never goes idle: the read decides
        page.wait_for_load_state("networkidle", timeout=IDLE_WAIT_MS)
    chooser = page.locator(f"{RESUME_BOX} input[type=file]")
    with contextlib.suppress(Exception):
        chooser.first.wait_for(state="attached", timeout=5000)
    if not chooser.count():
        return "ASK the resume drop box didn't load - the user chooses the file on the page"
    chooser.first.set_input_files(path)
    name = Path(path).name
    deadline = time.monotonic() + SHOWN_WAIT_MS / 1000
    while time.monotonic() < deadline:
        shown, link, error = resume_says(page)
        if error:
            return f"FAIL the page says '{error}' - choose the file again on the page, or check the resume box"
        if shown == name and link:
            return "ok"
        page.wait_for_timeout(250)
    return "ASK upload not confirmed on page - check the resume box"


def holds(page, q: dict) -> bool:
    """The answer still shows, read off the page once the form had time to keep it (form.recheck): radios +
    ticks by each one's own state, the slider by its value, the place by what the page kept, the phone by
    digits, the resume by name + link with no error. Nothing to read = False."""
    native, kind = q.get("native") or "", q["kind"]
    if native in TICKS:
        got, _ = ticks(page, q)
        want = wanted(q)
        return bool(got) and all((k in want) == on for k, on in got)
    if kind == "file":
        shown, link, error = resume_says(page)
        return bool(shown) and bool(link) and not error
    field = locate(page, q)
    if not field.count():
        return False
    got, value = field.input_value(), str(q["answer"])
    if native == "teamtailor:range":
        return bool(number(value)) and float(got or "nan") == float(number(value))
    if native == "teamtailor:select":
        return norm(field.evaluate("e => e.selectedOptions[0] ? e.selectedOptions[0].text : ''")).casefold() == norm(value).casefold()
    if kind == "location":
        return bool(place_id(page)) and value.split(",")[0].strip().casefold() in got.casefold()
    if kind == "phone":
        return bool(e164(value)) and digits(got) == digits(e164(value))
    return got == (number(value) if kind == "number" else value)


def fill(page, q: dict, resume_file: str | None) -> str:
    native, kind, value = q.get("native") or "", q["kind"], q["answer"]
    if native == "teamtailor:consent" or signs(q["title"]):
        return left_on_page(q)
    if kind == "file":
        if q.get("key") != "resume":
            return f"ASK not the resume box ({q['title']}) - the user uploads their own file there"
        return put_file(page, resume_file) if value is True and resume_file else "skipped - upload not approved"
    if native in TICKS:
        return put_ticks(page, q)
    if native == "teamtailor:range":
        return put_range(page, q)
    if native == "teamtailor:other" or native not in (
            "teamtailor:standard", "teamtailor:text", "teamtailor:number", "teamtailor:select"):
        return f"ASK a box Job Finder doesn't fill ({q['title'] or 'no words'}) - the user answers it on the page"
    field = locate(page, q)
    if not field.count():
        return "FAIL question not on page"
    field.scroll_into_view_if_needed()
    if native == "teamtailor:select":
        options = field.evaluate("e => [...e.options].filter(o => o.value).map(o => [o.value, o.text])")
        hit = next((v for v, t in options if norm(t).casefold() == norm(value).casefold()), None)
        if hit is None:
            return f"ASK no option '{norm(value)}'; offered: {', '.join(norm(t) for _, t in options)[:200]}"
        field.select_option(value=hit)
        return "ok" if holds(page, q) else "FAIL the list shows another option"
    if kind == "location":
        return put_location(page, field, str(value))
    if kind == "phone":
        return put_phone(field, value)
    return put_text(field, value, kind)
