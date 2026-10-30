"""Recruiterflow (recruiterflow.com/<firm>/jobs/<id>, a recruiting firm's own job page): questions from the form
definition inside the posting page, answers put in its React form - by each box's own name, an employer
question by its label.

Measured facts and why each rule exists: app/docs/apply/recruiterflow.md.
"""
import json
import re

import httpx

from apply import dom
from apply.questions import key_from_title, left_on_page, question, signs

NAME = "Recruiterflow"
# firm, posting id; freehire adds ?utm_source=freehire.me (8 of 8 links on the list, 3 firms, 2026-10-30)
POSTING_URL = re.compile(r"https?://(?:www\.)?recruiterflow\.com/([\w-]+)/jobs/(\d+)/?(?:[?#].*)?$", re.I)
SOURCES = ("recruiterflow",)
EXAMPLES = ("https://recruiterflow.com/acme/jobs/5992",
            "https://recruiterflow.com/acme/jobs/5992?utm_source=freehire.me")
# questions() is one plain GET of the posting page, no browser: the live test runs it
QUESTIONS_OVER_HTTP = True
# the resume goes to Recruiterflow as soon as it is chosen (generate-file-id + upload POSTs), then is read to
# fill name, email, phone + LinkedIn (recruiterflow.md "Resume")
FILE_ON_CHOICE = True
# the definition: `var convertedToJSON = {...}` in an inline script, handed to the page as window.applyJobData
DATA = re.compile(r"var convertedToJSON\s*=\s*")
# the resume drop area or a name box, whichever comes first - never the file input itself (hidden: never "visible")
READY = 'form .rf-careers-dnd-file-container-handler-wrapper, form input[name^="personal_info."]'
# the firm's own boxes, by the definition's key: (kind, shared key); the page's box is name=personal_info.<key>
PERSONAL = {"email": ("email", "email"), "phone": ("phone", "phone"), "linkedin_profile": ("url", "linkedin")}
NAMES = (("first_name", "First name", "first_name"), ("last_name", "Last name", "last_name"))
# Location: city, state, zip boxes by name + a Country list (home_address in search settings)
ADDRESS = (("city", "Location - city", "city"), ("state", "Location - state", "state"),
           ("postal_code", "Location - zip code", "zip"))
COUNTRY = "personal_info.location.country"
# Experience + Education: rows added by "+Add ..." with date pickers - unmeasured filling, the user's on the page
SECTIONS = {"experience": "Experience - add your jobs on the page (+Add Experience)",
            "education": "Education - add your schools on the page (+Add Education)"}
# employer question view field -> shared kind (the page's own APPLICATION_FORM_VIEW_FIELD table, read 2026-10-30)
KIND = {1: "text", 2: "longtext", 3: "longtext", 4: "number", 5: "number", 6: "date", 9: "yesno", 10: "choice",
        11: "multichoice", 14: "file", 19: "choice"}
# two boxes, Min + Max: money range (12), number range (13)
RANGES = (12, 13)
# what an unpicked list shows (every dropdown read, 3 firms) + the Country list's own
PLACEHOLDERS = ("Click to view options", "Country")
# the resume read fills the name boxes some seconds after the file is chosen: waited for, so typed names come after
PARSE_MS = 15000
SHOWN_MS = 20000


def matches(url: str) -> bool:
    return bool(POSTING_URL.match(url.strip()))


def parse_url(url: str) -> tuple[str, str]:
    """(firm, posting id)."""
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not a Recruiterflow posting link: {url}")
    return m.group(1), m.group(2)


def application_url(url: str) -> str:
    firm, id = parse_url(url)
    return f"https://recruiterflow.com/{firm}/jobs/{id}"


def norm(s) -> str:
    return " ".join(str(s).split())


def choices(q: dict) -> list[str]:
    """The options as the page offers them: blanks dropped, and a link - one firm's list held another
    applicant's file link (2026-10-30), never offered as an answer."""
    out = []
    for c in q.get("choices") or []:
        c = norm(c)
        if c and not re.match(r"https?://", c, re.I) and c not in out:
            out.append(c)
    return out


def from_definition(data: dict) -> list[dict]:
    """The shared questions, in page order: resume, the firm's own boxes, profile sections, its questions."""
    form = data.get("application_form") or {}
    if data.get("job_visibility_id") not in data.get("ACTIVE_JOB_VISIBILITY", [data.get("job_visibility_id")]):
        raise ValueError("Recruiterflow says the posting is closed")
    if not form or form.get("is_empty"):
        raise ValueError("the posting shows no application form - it may have closed")
    on = lambda f: f.get("requirement_type") != "off"
    must = lambda f: f.get("requirement_type") == "mandatory"
    profile = {f["key"]: f for f in form.get("candidate_profile") or [] if on(f)}
    out = []
    for key in ("resume", "cover_letter"):
        if f := profile.get(key):
            out.append(question(key, norm(f.get("display_name")) or key, "file", must(f), (), key, f"profile:{key}"))
    for f in form.get("personal_info") or []:
        if not on(f):
            continue
        key, title = f["key"], norm(f.get("display_name"))
        if key == "name":
            out += [question(f"personal_info.{id}", label, "text", must(f), (), k, "personal") for id, label, k in NAMES]
        elif key == "address":
            out += [question(f"personal_info.location.{id}", label, "text", must(f), (), k, "personal")
                    for id, label, k in ADDRESS]
            out.append(question(COUNTRY, "Location - country", "text", must(f), (), None, "country"))
        else:
            kind, k = PERSONAL.get(key, ("text", None))
            out.append(question(f"personal_info.{key}", title, kind, must(f), (), k or key_from_title(title, kind),
                                "personal"))
    for key, f in profile.items():
        if key == "summary":
            out.append(question("candidate_profile.summary", norm(f.get("display_name")) or "Summary", "longtext",
                                must(f), (), None, "summary"))
        elif key in SECTIONS:
            out.append(question(f"candidate_profile.{key}", SECTIONS[key], "text", must(f), (), None, "section"))
    for q in sorted(form.get("questions") or [], key=lambda q: q.get("rank") or 0):
        view = q.get("view_field_id") or q.get("custom_field_view_field_id")
        title, required, id = norm(q.get("question_text") or q.get("display_name")), must(q), f"q{q['question_id']}"
        if view in RANGES:
            out += [question(f"{id}.min", f"{title} - minimum", "number", required, (), None, f"view:{view}:min"),
                    question(f"{id}.max", f"{title} - maximum", "number", required, (), None, f"view:{view}:max")]
            continue
        kind = KIND.get(view, "text")
        options = ["Yes", "No"] if kind == "yesno" else choices(q) if kind in ("choice", "multichoice") else ()
        out.append(question(id, title, kind, required, options, key_from_title(title, kind), f"view:{view}"))
    return out


def page_data(html: str) -> dict:
    m = DATA.search(html or "")
    if not m:
        raise ValueError("no application form on the posting page - it may have closed")
    return json.JSONDecoder().raw_decode(html[m.end():])[0]


def posting_page(url: str):
    r = httpx.get(application_url(url), timeout=30, follow_redirects=True)
    if r.status_code in (404, 410):
        raise ValueError("posting not found on Recruiterflow - it may have closed")
    r.raise_for_status()
    return r


def questions(url: str) -> list[dict]:
    return from_definition(page_data(posting_page(url).text))


def closed(url: str) -> str | None:
    """Why the form isn't there (form.closed): None = Recruiterflow still shows the posting's form."""
    try:
        from_definition(page_data(posting_page(url).text))
    except ValueError as e:
        return str(e)
    except httpx.HTTPError as e:
        return f"can't tell if the posting is open - Recruiterflow didn't answer ({type(e).__name__})"
    return None


def ids_on_page(page) -> list[str]:
    """Question ids the page shows: the definition the page itself was drawn from (window.applyJobData)."""
    data = page.evaluate("() => window.applyJobData || null")
    return [q["id"] for q in from_definition(data)] if data else []


def block(page, title: str):
    """A question's block: the div holding its label paragraph (`p.form-label`, then `span.required` "*" when
    required - every widget in the page's bundle draws it so), matched on the label's whole words."""
    words = r"\s+".join(re.escape(w) for w in norm(title).split())
    label = page.locator("p.form-label", has_text=re.compile(rf"^\s*{words}\s*\*?\s*$"))
    return page.locator("form div:has(> p.form-label)").filter(has=label).first


def label_of(q: dict) -> str:
    """The words above the box: a range's two questions share their question's label."""
    return re.sub(r" - (minimum|maximum)$", "", q["title"])


def phone(value) -> str:
    """Digits only; a US number's leading 1 dropped - the country box already says +1 US."""
    digits = dom.digits(str(value))
    return digits[1:] if len(digits) == 11 and digits.startswith("1") else digits


def wanted(q: dict) -> list[str]:
    value = q["answer"]
    if isinstance(value, list):
        return [norm(v) for v in value]
    return [("Yes" if dom.yes(value) else "No") if q["kind"] == "yesno" else norm(value)]


def shown(combo) -> list[str]:
    """What a react-select list shows: its value container's words (input's grandparent), placeholder dropped."""
    text = combo.evaluate("e => e.parentElement.parentElement.innerText")
    return [t for t in (norm(s) for s in text.split("\n")) if t and t not in PLACEHOLDERS]


def options_of(page, combo):
    """This list's own options: react-select ids them <its input id less -input>-option-<n>, in a menu drawn on
    <body> - the phone box's hidden country list is role=option too (240 of them), so role alone is never enough."""
    base = (combo.get_attribute("id") or "").removesuffix("-input")
    return page.locator(f'[id^="{base}-option-"]')


def options_open(page, combo) -> list[str]:
    opts = options_of(page, combo)
    try:
        opts.first.wait_for(timeout=5000)
    except Exception:
        return []
    return [norm(t) for t in opts.all_inner_texts()]


def put_menu(page, combo, want: list[str], typed: bool = False) -> str:
    """Open the list like a person (click; Country: type its name first), click each answer - never the
    first offered. A multi-select stays open while picking (closeMenuOnSelect off): one open for all."""
    combo.scroll_into_view_if_needed()
    if (have := shown(combo)) == want:
        return "ok"
    if have:  # a different pick already there: cleared by the box's own Clear / Clear All
        clear = combo.locator("xpath=ancestor::div[contains(@class,'common-input-wrapper')][1]").get_by_text(
            re.compile(r"^Clear( All)?$")).first
        if clear.count():
            clear.click()
            page.wait_for_timeout(200)
    for i, w in enumerate(want):
        if i == 0 or not options_of(page, combo).count():
            combo.click()
        if typed:
            combo.fill(w)
        texts = options_open(page, combo)
        if w not in texts:
            page.keyboard.press("Escape")
            return f"ASK no option '{w}'; offered: {', '.join(texts)[:200]}"
        options_of(page, combo).nth(texts.index(w)).click()
        page.wait_for_timeout(200)
    page.keyboard.press("Escape")
    got = shown(combo)
    return "ok" if sorted(got) == sorted(want) else f"FAIL shows '{', '.join(got)}'"


def put_yes_no(box, want: str) -> str:
    """Two buttons, Yes / No; the picked one carries class `selected` (the bundle's yesNo widget)."""
    button = box.locator("button.yes-input" if want == "Yes" else "button.no-input")
    if not button.count():
        return "FAIL no Yes / No buttons"
    if "selected" not in (button.first.get_attribute("class") or "").split():
        button.first.click()
    return "ok" if "selected" in (button.first.get_attribute("class") or "").split() else "FAIL the button didn't stay picked"


def picked(box) -> str | None:
    for cls, word in (("button.yes-input", "Yes"), ("button.no-input", "No")):
        b = box.locator(cls)
        if b.count() and "selected" in (b.first.get_attribute("class") or "").split():
            return word
    return None


def put_file(page, path: str, resume: bool, box=None) -> str:
    """Chosen = sent to Recruiterflow at once. The box then shows the file's name (cut at 35 letters + "...");
    the resume is read and fills name, email, phone + LinkedIn - waited for, so typed answers come after it."""
    name = path.rsplit("/", 1)[-1]
    field = (box or page.locator("form").first).locator("input[type=file]").first
    first = page.locator('[name="personal_info.first_name"]').first
    before = first.input_value() if first.count() else ""
    field.set_input_files(path)
    chip = page.locator(".file-list-item").filter(has_text=name[:35]).first
    try:
        chip.wait_for(timeout=SHOWN_MS)
    except Exception:
        return "ASK upload not confirmed on page - check the resume box shows the file"
    if resume and first.count():
        waited = 0
        while waited < PARSE_MS and first.input_value() == before:
            page.wait_for_timeout(500)
            waited += 500
    page.wait_for_timeout(1500)
    return "ok"


def box_field(page, q: dict):
    """The box a typed answer goes in: the firm's own by name, an employer question's in its block."""
    native = q.get("native") or ""
    if native == "personal":
        return page.locator(f'form [name="{q["id"]}"]').first
    b = block(page, label_of(q))
    if native.endswith(":min") or native.endswith(":max"):
        return b.locator('input[placeholder="Min"]' if native.endswith(":min") else 'input[placeholder="Max"]').first
    return b.locator("textarea, input:not([type=hidden]):not([type=file]):not([role=combobox])").first


def value_of(field) -> str:
    return field.input_value()


def same(q: dict, got: str) -> bool:
    kind, value = q["kind"], str(q["answer"])
    if kind == "phone":
        return dom.digits(got) == phone(value)
    if kind == "number":  # the pay boxes show 180,000 for 180000
        return dom.digits(got) == dom.digits(value)
    return norm(got) == norm(value) if kind == "longtext" else got == value


def country_combo(page):
    """The Country list sits with the zip box in the Location block."""
    return page.locator('form [name="personal_info.location.postal_code"]').first.locator(
        "xpath=ancestor::div[.//input[@role='combobox']][1]").locator("[role=combobox]").first


def holds(page, q: dict) -> bool:
    """The answer still shows, read off the page as a person sees it (form.recheck)."""
    kind, native = q["kind"], q.get("native") or ""
    if kind == "file":
        return q["answer"] is not True or page.locator(".file-list-item").count() > 0
    if native == "country":
        combo = country_combo(page)
        return bool(combo.count()) and shown(combo) == wanted(q)
    if kind in ("yesno", "choice", "multichoice"):
        b = block(page, q["title"])
        if not b.count():
            return False
        if kind == "yesno":
            return picked(b) == wanted(q)[0]
        combo = b.locator("[role=combobox]").first
        return bool(combo.count()) and sorted(shown(combo)) == sorted(wanted(q))
    field = box_field(page, q)
    return bool(field.count()) and same(q, value_of(field))


def fill(page, q: dict, resume_file: str | None) -> str:
    kind, native, value = q["kind"], q.get("native") or "", q["answer"]
    if signs(q["title"]):
        return left_on_page(q)
    if native == "section":
        return f"ASK {q['title']} - Job Finder doesn't fill these rows yet"
    if kind == "file":
        if q.get("key") not in ("resume", "cover_letter"):
            return f"ASK not the resume box ({q['title']}) - the user uploads their own file there"
        if q.get("key") == "cover_letter":
            b = block(page, q["title"])
            if not resume_file:
                return "ASK cover letter box - no letter made for this job (letter prepare), or the user uploads their own"
            if not b.count():
                return "FAIL question not on page"
            return put_file(page, resume_file, False, b) if value is True else "skipped - upload not approved"
        return put_file(page, resume_file, True) if value is True and resume_file else "skipped - upload not approved"
    if native == "country":
        combo = country_combo(page)
        return put_menu(page, combo, wanted(q), typed=True) if combo.count() else "FAIL question not on page"
    if kind in ("yesno", "choice", "multichoice"):
        b = block(page, q["title"])
        if not b.count():
            return "FAIL question not on page"
        if kind == "yesno":
            return put_yes_no(b, wanted(q)[0])
        combo = b.locator("[role=combobox]").first
        return put_menu(page, combo, wanted(q)) if combo.count() else "FAIL no list to pick from"
    if kind == "date":
        return "ASK date box - pick it in the page's calendar"
    field = box_field(page, q)
    if not field.count():
        return "FAIL question not on page"
    field.scroll_into_view_if_needed()
    text = phone(value) if kind == "phone" else dom.digits(str(value)) if kind == "number" else str(value)
    field.fill(text)
    field.evaluate("e => { e.dispatchEvent(new Event('change', {bubbles: true})); e.blur(); }")
    got = value_of(field)
    return "ok" if same(q, got) else f"FAIL shows '{got}'"
