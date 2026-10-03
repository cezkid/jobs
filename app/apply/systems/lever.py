"""Lever (jobs.lever.co): questions read off its public /apply page, answers typed into its plain HTML form.

Measured facts and why each rule exists: app/docs/apply/lever.md.
"""
import html
import json
import re
from html.parser import HTMLParser

import httpx

from apply import dom
from apply.questions import key_from_title, question, signs

NAME = "Lever"
# EU host too; freehire's links carry ?utm_source=freehire.me, the form is the same link + /apply
POSTING_URL = re.compile(r"https?://jobs\.(eu\.)?lever\.co/([\w.-]+)/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
                         r"(?:/apply)?/?(?:[?#].*)?$", re.I)
SOURCES = ("lever",)
EXAMPLES = ("https://jobs.lever.co/acme/1b2c3d4e-5f60-4718-9a0b-1c2d3e4f5a6b",
            "https://jobs.lever.co/acme/1b2c3d4e-5f60-4718-9a0b-1c2d3e4f5a6b?utm_source=freehire.me",
            "https://jobs.lever.co/acme/1b2c3d4e-5f60-4718-9a0b-1c2d3e4f5a6b/apply",
            "https://jobs.eu.lever.co/acme/1b2c3d4e-5f60-4718-9a0b-1c2d3e4f5a6b")
# questions() is one plain GET of the /apply page, no browser: the live test runs it
QUESTIONS_OVER_HTTP = True
READY = "#application-form input[name=name]"
# card field type -> shared kind (51 fields, 4 tenants, 2026-10-03); a type missing here is asked as text
KIND = {"text": "text", "textarea": "longtext", "multiple-choice": "choice", "dropdown": "choice",
        "multiple-select": "multichoice"}
# Lever's own boxes, by name: (title when the page label is blank, kind, key)
STANDARD = {"resume": ("Resume/CV", "file", "resume"), "name": ("Full name", "text", "name"),
            "email": ("Email", "email", "email"), "phone": ("Phone", "phone", "phone"),
            "location": ("Current location", "location", "location"), "org": ("Current company", "text", None),
            "urls[LinkedIn]": ("LinkedIn URL", "url", "linkedin"), "urls[GitHub]": ("GitHub URL", "url", "github"),
            "urls[Portfolio]": ("Portfolio URL", "url", "website"), "urls[Twitter]": ("Twitter URL", "url", None),
            "urls[Other]": ("Other website", "url", None)}
# the disability form's signature boxes are labelled plain "Name" / "Date" (tenant A): the applicant signs, never a name box
SIGNATURE = {"eeo[disabilitySignature]": "Disability form signature (your full name)",
             "eeo[disabilitySignatureDate]": "Disability form signature date"}
# marketing consent's own text names the employer: one fixed title, the applicant's tick
CONSENT = "Consent to be contacted about future job opportunities"
# Lever's own fields and the captcha: never questions
SKIP = {"selectedLocation", "h-captcha-response", "resumeStorageId", "timezone", "source", "origin", "referer",
        "accountId", "linkedInData", "socialReferralKey", "socialSource"}
# home address as an employer's own text cards (tenant C: "Current Address (Line 1)", City, State, Zip Code)
ADDRESS = (("street", r"(?:current |home |street )?address(?: \(?line ?1\)?)?:?"), ("city", r"city:?"),
           ("state", r"state:?"), ("zip", r"(?:zip|postal)(?: code)?:?"))
FIELD = re.compile(r"^(cards|surveysResponses)\[([\w-]+)\](?:\[responses\])?\[field(\d+)\]$")
TEMPLATE = re.compile(r"^(cards|surveysResponses)\[([\w-]+)\]\[baseTemplate\]$")


def matches(url: str) -> bool:
    return bool(POSTING_URL.match(url.strip()))


def parse_url(url: str) -> tuple[str, str, str]:
    """(host suffix "" or "eu.", company, posting id)."""
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not a Lever posting link: {url}")
    return m.group(1) or "", m.group(2), m.group(3)


def application_url(url: str) -> str:
    eu, co, id = parse_url(url)
    return f"https://jobs.{eu}lever.co/{co}/{id}/apply"


class Form(HTMLParser):
    """The /apply page's form, read once: each named box in page order (label, type, options,
    required), the card + survey definitions (JSON in a hidden input's value)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.boxes, self.templates = {}, {}
        self.label, self.in_label, self.depth = "", False, 0
        self.select, self.option = None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "application-question" in (a.get("class") or "").split():
            self.label = ""  # a box outside any label (the consent tick) never takes the one above
        if tag == "div":
            self.depth += self.in_label
            if "application-label" in (a.get("class") or "").split():
                self.label, self.in_label, self.depth = "", True, 1
            return
        if tag == "option" and self.select is not None:
            self.option = [a.get("value") or "", ""]
            return
        if tag not in ("input", "select", "textarea"):
            return
        name = a.get("name") or a.get("data-name") or ""
        if m := TEMPLATE.match(a.get("data-name") or name):
            try:
                self.templates[(m.group(1), m.group(2))] = json.loads(html.unescape(a.get("value") or ""))
            except ValueError:  # a broken template: its boxes are read off the page instead
                pass
            return
        type = "select" if tag == "select" else "textarea" if tag == "textarea" else (a.get("type") or "text").lower()
        if not name or type == "hidden" or name in SKIP:
            return
        box = self.boxes.setdefault(name, {"name": name, "type": type, "label": self.label.strip(),
                                           "required": False, "options": []})
        box["required"] |= "required" in a
        if type in ("radio", "checkbox"):
            box["options"].append((a.get("value") or "").strip())
        if tag == "select":
            self.select = box

    def handle_endtag(self, tag):
        if tag == "div" and self.in_label:
            self.depth -= 1
            self.in_label = self.depth > 0
        elif tag == "option" and self.option is not None:
            if self.option[0]:  # "Select ..." has no value
                self.select["options"].append(self.option[1].strip())
            self.option = None
        elif tag == "select":
            self.select = None

    def handle_data(self, data):
        if self.in_label:
            self.label += data
        if self.option is not None:
            self.option[1] += data


def card_key(text: str, kind: str) -> str | None:
    return next((key for key, said in ADDRESS if kind == "text" and re.fullmatch(said, text, re.I)), None) \
        or key_from_title(text, kind)


def title(label: str) -> str:
    return " ".join(label.replace("✱", " ").split())


def from_page(page_html: str) -> list[dict]:
    """The shared questions, in page order. Employer questions take their wording from the card's
    JSON: on the page a text card is labelled only "Type your response" (2026-10-03)."""
    form = Form()
    form.feed(page_html)
    out = []
    for name, box in form.boxes.items():
        required, options = box["required"] or "✱" in box["label"], box["options"]
        if m := FIELD.match(name):
            template = form.templates.get((m.group(1), m.group(2))) or {}
            fields = template.get("fields") or []
            field = fields[int(m.group(3))] if int(m.group(3)) < len(fields) else None
            if field is not None:
                kind = KIND.get(field.get("type"), "text")
                options = [o["text"].strip() for o in field.get("options") or []] or options
                if kind == "choice" and sorted(options) == ["No", "Yes"]:
                    kind = "yesno"
                text = title(field.get("text") or "")
                out.append(question(name, text, kind, bool(field.get("required")), options,
                                    card_key(text, kind), f"{m.group(1)}:{field.get('type')}"))
                continue
        if name in STANDARD:
            text, kind, key = STANDARD[name]
            out.append(question(name, title(box["label"]) or text, kind, required, key=key, native=name))
        elif name in SIGNATURE:
            out.append(question(name, SIGNATURE[name], "text", False, native="eeo:signature"))
        elif name.startswith("consent["):
            out.append(question(name, CONSENT, "yesno", required, native="consent"))
        elif box["type"] in ("select", "radio", "checkbox"):
            kind = "multichoice" if box["type"] == "checkbox" and len(options) > 1 else "choice"
            kind = "yesno" if kind == "choice" and sorted(options) == ["No", "Yes"] else kind
            out.append(question(name, title(box["label"]) or name, kind, required, options,
                                native="eeo" if name.startswith("eeo[") else box["type"]))
        else:
            text = title(box["label"]) or name
            kind = "longtext" if box["type"] == "textarea" else dom.INPUT_KIND.get(box["type"], "text")
            out.append(question(name, text, kind, required, key=key_from_title(text, kind), native=box["type"]))
    return out


def questions(url: str) -> list[dict]:
    r = httpx.get(application_url(url), timeout=30, follow_redirects=False)
    # a closed or unknown posting: 404, or a redirect off the posting (unmeasured beyond 404)
    if r.status_code in (301, 302, 404):
        raise ValueError("posting not found - it may have closed")
    r.raise_for_status()
    return from_page(r.text)


def ids_on_page(page) -> list[str]:
    return page.eval_on_selector_all(
        # the Apply with LinkedIn frame carries a name too (JSON, 2026-10-03): boxes only
        "#application-form input[name], #application-form select[name], #application-form textarea[name]",
        f"(es, skip) => [...new Set(es.filter(e => e.type !== 'hidden' && !/baseTemplate/.test(e.name)"
        f" && !skip.includes(e.name)).map(e => e.name))]", sorted(SKIP))


def boxes(page, name: str):
    return page.locator(f'#application-form [name="{name}"]:not([type=hidden])')


def put_file(page, field, path: str) -> str:
    """Lever reads the resume as soon as it is chosen and fills boxes from it: upload first (fill_page
    does), then wait for its own verdict before anything is typed."""
    field.set_input_files(path)
    if field.evaluate("e => e.files[0] ? e.files[0].name : ''") != path.rsplit("/", 1)[-1]:
        return "ASK upload not confirmed on page - check the box"
    label = page.locator("#application-form .resume-upload-success, #application-form .resume-upload-failure")
    try:
        label.filter(visible=True).first.wait_for(timeout=20000)
    except Exception:
        return "ASK upload not confirmed on page - check the box"
    if page.locator("#application-form .resume-upload-failure").filter(visible=True).count():
        return "ASK Lever says it couldn't take the resume - check the box"
    return "ok"


def put_location(page, field, value: str) -> str:
    """Lever's own place search: type the town, click the result that is the answer (or starts with it)."""
    v = str(value).strip()
    field.click()
    field.fill("")
    field.press_sequentially(v.split(",")[0], delay=50)
    results = page.locator("#application-form .dropdown-results > div")
    try:
        results.first.wait_for(timeout=8000)
    except Exception:
        return f"ASK no place offered for '{v}' - pick it on the page"
    texts = [dom.norm(t) for t in results.all_inner_texts()]
    want = v.casefold()
    hit = next((i for i, t in enumerate(texts) if t.casefold() == want), None)
    if hit is None:
        hit = next((i for i, t in enumerate(texts) if t.casefold().startswith(want)), None)
    if hit is None:
        return f"ASK no place '{v}'; offered: {', '.join(texts[:5])}"
    results.nth(hit).click()
    page.wait_for_timeout(300)
    chosen = page.locator("#selected-location").input_value()
    return "ok" if chosen else f"FAIL '{texts[hit]}' not selected"


def fill(page, q: dict, resume_file: str | None) -> str:
    kind, value, name = q["kind"], q["answer"], q["id"]
    if signs(q["title"]) or q.get("native") in ("consent", "eeo:signature"):
        return "ASK yours to do on the page - agreeing, consenting or signing"
    field = boxes(page, name)
    if not field.count():
        # the disability signature shows only once Disability status is chosen
        return "skipped - not shown for the other answers" if name.startswith("eeo[") else "FAIL question not on page"
    if kind == "file":
        if q.get("key") != "resume":
            return f"ASK not the resume box ({q['title']}) - the user uploads their own file there"
        return put_file(page, field.first, resume_file) if value is True and resume_file else "skipped - upload not approved"
    type = field.first.evaluate("e => e.tagName === 'SELECT' ? 'select' : e.type")
    if type in ("radio", "checkbox"):
        # options are radios / ticks whose value is the option text, often under a styled label
        members = field.all()
        names = [m.get_attribute("value").strip() for m in members]
        want = value if isinstance(value, list) else [("Yes" if dom.yes(value) else "No") if kind == "yesno" else str(value).strip()]
        return dom.put_ticks(members, names, want, role=False, single=type == "radio")
    field = field.first
    field.scroll_into_view_if_needed()
    if type == "select":
        return dom.put_select(field, ("Yes" if dom.yes(value) else "No") if kind == "yesno" else value)
    if kind == "location":
        return put_location(page, field, value)
    return dom.put_text(field, value, kind, editable=False)
