"""Manatal (www.careers-page.com/<employer>/job/<hash>): questions from the posting's own form definition, answers typed into its page.

Measured facts and why each rule exists: app/docs/apply/manatal.md.
"""
import contextlib
import re
import time
from pathlib import Path

import httpx

from apply.questions import key_from_title, left_on_page, question, signs

NAME = "Manatal"
# one host for every employer; freehire adds ?utm_source=freehire.me (58 of 58, 2026-10-06); the form is at + /apply
POSTING_URL = re.compile(r"https?://(?:www\.)?careers-page\.com/([\w.-]+)/job/([A-Za-z0-9]+)(?:/apply)?/?(?=[?#]|$)", re.I)
SOURCES = ("manatal",)
EXAMPLES = ("https://www.careers-page.com/acme/job/AB12CD34",
            "https://www.careers-page.com/acme/job/AB12CD34?utm_source=freehire.me",
            "https://www.careers-page.com/acme/job/AB12CD34/apply")
HOST = "https://www.careers-page.com"
# the apply page names its posting in a script const; the definition is a plain JSON GET by it (47 of 47, 2026-10-06)
JOB_ID = re.compile(r"""\bselectedJobId\s*=\s*["'](\d+)["']""")
DEFINITION = HOST + "/api/v1.0/jobs/{id}/application-form/"
CURRENCIES = HOST + "/api/v1.0/currencies/"
QUESTIONS_OVER_HTTP = True
# #app stays hidden until Vue mounts; the boxes come once the definition is read (3 of 3)
READY = '#app form [id^="field"]'
FORM = "#app form"
# a pay box is a number + two lists of its own: currency (Manatal's list, first = no default) + how often
SALARY = {"expected_salary": "expected", "current_salary": "current"}
FREQUENCIES = ["Hourly", "Daily", "Weekly", "Monthly", "Yearly"]
# employer lists on the page, by the definition's field type (the page's template, 2026-10-06)
LISTS = {"dropdown": ("choice", "select"), "multiple_select_dropdown": ("multichoice", "multiselect"),
         "checkbox": ("multichoice", "checkbox"), "multiple_choice": ("choice", "radio")}
# Manatal's own lists, options loaded by the page from its own lists (unmeasured on a live form)
OWN_LISTS = {"gender": ("choice", "select", ["Male", "Female", "Other"]), "current_notice_period": ("choice", "select", []),
             "years_of_experience": ("choice", "select", []), "nationalities": ("multichoice", "multiselect", []),
             "languages": ("multichoice", "multiselect", []), "industries": ("multichoice", "multiselect", [])}
BY_RESPONSE = {"char": "text", "longtext": "longtext", "integer": "number", "boolean": "yesno", "datetime": "date"}
# LinkedIn = social_media 3 (14 of 14)
SOCIAL = {3: "linkedin"}
# the page's own words under the resume box after a file is chosen (form script, 2026-10-06)
FILE_ERROR = ".custom-file small.text-danger"
FILE_LABEL = ".custom-file-label"
NO_FILE = "Choose file"
IDLE_WAIT_MS, SHOWN_WAIT_MS = 15000, 5000


def matches(url: str) -> bool:
    return bool(POSTING_URL.match(url.strip()))


def parse_url(url: str) -> tuple[str, str]:
    """(employer, posting hash)."""
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not a Manatal posting link: {url}")
    return m.group(1), m.group(2)


def application_url(url: str) -> str:
    co, hash = parse_url(url)
    return f"{HOST}/{co}/job/{hash}/apply"


def norm(s) -> str:
    return " ".join(str(s).split())


def yes_no(options: list[str]) -> bool:
    return sorted(o.casefold() for o in options) == ["no", "yes"]


def from_definition(fields: list[dict], currencies: list[str] = ()) -> list[dict]:
    out = []
    for f in fields:
        id, title, required = str(f["id"]), norm(f.get("label") or ""), bool(f.get("is_required"))
        ftype, slug, response = f.get("field_type"), f.get("client_field_slug") or "", f.get("response_type")
        options = [norm(o) for o in f.get("client_field_answer_choices") or []]
        if ftype == "resume":
            out.append(question(id, title, "file", required, (), "resume", "manatal:resume"))
        elif ftype == "attachment":
            out.append(question(id, title, "file", required, (), None, "manatal:attachment"))
        elif ftype in ("educations", "experiences"):  # entries added one by one on the page (0 of 47 forms)
            out.append(question(id, title, "longtext", required, (), None, f"manatal:{ftype}"))
        elif ftype == "social_media":
            out.append(question(id, title, "url", required, (), SOCIAL.get(f.get("social_media")) or key_from_title(title, "url"),
                                "manatal:text"))
        elif slug == "full_name":  # one box, never split (47 of 47)
            out.append(question(id, title, "text", required, (), key_from_title(title, "text") or "name", "manatal:text"))
        elif slug == "email":
            out.append(question(id, title, "email", required, (), "email", "manatal:text"))
        elif slug == "phone_number":
            out.append(question(id, title, "phone", required, (), "phone", "manatal:text"))
        elif ftype == "candidate_field" and slug in SALARY:
            which = SALARY[slug]
            out.append(question(id, title, "number", required, (), None, "manatal:number"))
            out.append(question(f"{id}:currency", f"{title} - currency", "choice", required, currencies, None,
                                f"manatal:currency:{which}"))
            out.append(question(f"{id}:frequency", f"{title} - per", "choice", required, FREQUENCIES, None,
                                f"manatal:frequency:{which}"))
        elif ftype == "candidate_field" and slug in OWN_LISTS:
            kind, widget, opts = OWN_LISTS[slug]
            out.append(question(id, title, kind, required, opts, None, f"manatal:{widget}"))
        elif ftype == "candidate_field" and f.get("client_field_field_type") in LISTS:
            kind, widget = LISTS[f["client_field_field_type"]]
            if widget in ("checkbox", "radio") and (yes_no(options) or (widget == "checkbox" and len(options) == 1)):
                kind = "yesno"
            out.append(question(id, title, kind, required, options, None, f"manatal:{widget}"))
        else:  # by what the box holds: Yes / No questions often come as plain char boxes (manatal.md)
            kind = BY_RESPONSE.get(response, "text")
            native = {"yesno": "manatal:boolean", "date": "manatal:date", "number": "manatal:number"}.get(kind, "manatal:text")
            out.append(question(id, title, kind, required, ["Yes", "No"] if kind == "yesno" else (),
                                key_from_title(title, kind), native))
    return out


def job_id(html: str) -> str:
    m = JOB_ID.search(html or "")
    if not m:
        raise ValueError("no application form on the posting page - it may have closed")
    return m.group(1)


def challenged(r) -> bool:
    """AWS WAF asks for a browser check instead of answering (page script; 0 of 47 plain reads)."""
    return r.headers.get("x-amzn-waf-action") == "challenge"


def currency_names() -> list[str]:
    """Manatal's own currency list (what the page's currency box offers); [] if it doesn't answer."""
    with contextlib.suppress(httpx.HTTPError, ValueError):
        r = httpx.get(CURRENCIES, timeout=30, follow_redirects=True)
        if r.status_code == 200 and not challenged(r):
            return [norm(c.get("name") or "") for c in r.json() if c.get("name")]
    return []


def apply_page(url: str):
    r = httpx.get(application_url(url), timeout=30, follow_redirects=True)
    # a taken-down posting: 404 "The page you requested was not found." (12 of 12, 2026-10-06)
    if r.status_code == 404:
        raise ValueError("posting not found on Manatal - it may have closed")
    r.raise_for_status()
    return r


def questions(url: str) -> list[dict]:
    r = httpx.get(DEFINITION.format(id=job_id(apply_page(url).text)), timeout=30, follow_redirects=True)
    if challenged(r):
        raise ValueError("Manatal asked for a browser check before showing the form's questions")
    r.raise_for_status()
    fields = r.json()
    salary = any(f.get("client_field_slug") in SALARY for f in fields)
    return from_definition(fields, currency_names() if salary else [])


def closed(url: str) -> str | None:
    """Why the form isn't there (form.closed, when the page shows no form): None = Manatal still has it."""
    try:
        r = httpx.get(application_url(url), timeout=30, follow_redirects=True)
    except httpx.HTTPError as e:
        return f"can't tell if the posting is open - Manatal didn't answer ({type(e).__name__})"
    if r.status_code == 404:
        return "posting not found on Manatal - it may have closed"
    if r.status_code != 200:
        return f"can't tell if the posting is open - Manatal answered {r.status_code}"
    try:
        job_id(r.text)
    except ValueError as e:
        return str(e)
    return None


def ids_on_page(page) -> list[str]:
    """Boxes named by their definition id; a pay box's two lists share its name (told apart by their own
    ids). The terms box is the applicant's own, no question."""
    return page.eval_on_selector_all(
        f"{FORM} input[name], {FORM} select[name], {FORM} textarea[name]",
        """es => [...new Set(es.filter(e => /^\\d+$/.test(e.name)).map(e =>
              /_currency$/.test(e.id) ? e.name + ':currency' : /_frequency$/.test(e.id) ? e.name + ':frequency' : e.name))]""")


def field_id(q: dict) -> str:
    return q["id"].split(":")[0]


def locate(page, q: dict):
    native = q.get("native") or ""
    if native.startswith(("manatal:currency:", "manatal:frequency:")):
        part, which = native.split(":")[1:]
        return page.locator(f"{FORM} select#{which}_{part}").first
    return page.locator(f'{FORM} [id="field{field_id(q)}"]').first


def group(page, q: dict, typ: str):
    return page.locator(f'{FORM} input[type={typ}][name="{field_id(q)}"]')


def digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def number(value) -> str:
    """A pay box takes a plain number: "$85,000" -> "85000"."""
    return re.sub(r"[^\d.]", "", str(value))


def wanted(q: dict) -> set[str]:
    """The option texts (any case) an answer picks; a lone box ticked = yes."""
    value = q["answer"]
    if q["kind"] == "yesno":
        yes = str(value).casefold() in ("yes", "true")
        if q.get("native") == "manatal:checkbox" and len(q["options"]) == 1:
            return {q["options"][0].casefold()} if yes else set()
        value = ["Yes" if yes else "No"]
    return {norm(v).casefold() for v in (value if isinstance(value, list) else [value])}


def put_text(field, value, kind: str) -> str:
    v = number(value) if kind == "number" else str(value)
    if kind == "number" and not v:
        return f"ASK '{value}' is not a number - the box takes digits only"
    field.fill(v)
    field.blur()
    got = field.input_value()
    return "ok" if (digits(got) == digits(v) if kind == "phone" else got == v) else f"FAIL shows '{got}'"


def put_ticks(page, q: dict, typ: str) -> str:
    """Tick the box(es) / radio whose value is the answer, untick the rest; read the ticks back. Each
    box's id is the same literal on every one (manatal.md): picked by value."""
    boxes = group(page, q, typ)
    values = [norm(b.get_attribute("value") or "") for b in boxes.all()]
    want = wanted(q)
    if missing := want - {v.casefold() for v in values}:
        return f"ASK no option '{sorted(missing)[0]}'; offered: {', '.join(values)}"
    if "other" in want:
        return "ASK 'Other' opens a box of its own - the user types it on the page"
    for box, v in zip(boxes.all(), values):
        if (v.casefold() in want) != box.is_checked():
            box.evaluate("e => e.click()")  # like a person's click: the page's own handlers run
    wrong = [v for box, v in zip(boxes.all(), values) if (v.casefold() in want) != box.is_checked()]
    return "ok" if not wrong else f"FAIL '{wrong[0]}' shows the wrong tick"


def put_boolean(field, q: dict) -> str:
    yes = str(q["answer"]).casefold() in ("yes", "true")
    if field.is_checked() != yes:
        field.evaluate("e => e.click()")
    return "ok" if field.is_checked() == yes else f"FAIL the box shows {'un' if yes else ''}ticked"


def chosen(field) -> list[str]:
    """Texts of the options picked - never the "Select ..." no-answer one (value "")."""
    return [norm(t) for t in field.evaluate("e => [...e.selectedOptions].filter(o => o.value !== '').map(o => o.text)")]


def put_select(field, q: dict) -> str:
    """Pick the option(s) whose text is the answer, any case; read the pick back. Lists the page fills
    itself (currency, notice period) are matched by their own text. A select2 list keeps the native
    one underneath, which is what the form script reads."""
    want = wanted(q)
    options = field.evaluate("e => [...e.options].map(o => [o.value, o.text])")
    hits = [v for v, t in options if v != "" and norm(t).casefold() in want]
    if len(hits) < len(want):
        offered = ", ".join(norm(t) for v, t in options if v != "")
        return f"ASK no option '{norm(q['answer'])}'; offered: {offered[:200]}"
    field.select_option(value=hits)
    field.evaluate("e => { e.dispatchEvent(new Event('change', {bubbles: true})); if (window.jQuery) jQuery(e).trigger('change'); }")
    got = {t.casefold() for t in chosen(field)}
    return "ok" if got == want else f"FAIL shows '{', '.join(chosen(field))}'"


def file_says(field) -> tuple[str, str]:
    """(the name the box's label shows, the page's error words under it)."""
    box = field.locator("xpath=ancestor::div[contains(@class,'custom-file')][1]")
    if not box.count():
        return "", ""
    label = norm(" ".join(box.locator(FILE_LABEL).all_inner_texts()))
    return label, norm(" ".join(box.locator("small.text-danger").all_inner_texts()))


def put_file(page, field, path: str) -> str:
    """Page idle first (as Greenhouse, Ashby), then the file chosen - it stays on the computer until
    Submit (form script: presigned upload only then). Ok = the box's label shows the file's name and the
    page writes no error under it; the page's own error words -> FAIL; neither -> ASK."""
    with contextlib.suppress(Exception):  # a page that keeps polling never goes idle: the read decides
        page.wait_for_load_state("networkidle", timeout=IDLE_WAIT_MS)
    field.set_input_files(path)
    name = Path(path).name
    deadline = time.monotonic() + SHOWN_WAIT_MS / 1000
    while time.monotonic() < deadline:
        label, error = file_says(field)
        if error:
            return f"FAIL the page says '{error}' - choose the file again on the page, or check the resume box"
        if label == name:
            return "ok"
        page.wait_for_timeout(250)
    return "ASK upload not confirmed on page - check the resume box"


def holds(page, q: dict) -> bool:
    """The answer still shows, read off the page once the form had time to keep it (form.recheck), each
    kind as manatal.md "Read back" records it: a box by its value (phone by digits), ticks + radios by
    each one's own state, a list by the option(s) picked, the yes box by its tick, the resume by the name
    its label shows with no error under it. Nothing to read = False."""
    native, kind = q.get("native") or "", q["kind"]
    if native in ("manatal:checkbox", "manatal:radio"):
        typ = "checkbox" if native == "manatal:checkbox" else "radio"
        ticks = group(page, q, typ).evaluate_all("bs => bs.map(b => [b.value, b.checked])")
        want = wanted(q)
        return bool(ticks) and all((norm(v).casefold() in want) == on for v, on in ticks)
    field = locate(page, q)
    if not field.count():
        return False
    if kind == "file":
        label, error = file_says(field)
        return bool(label) and label != NO_FILE and not error and bool(field.evaluate("e => e.files && e.files.length"))
    if native == "manatal:boolean":
        return field.is_checked() == (str(q["answer"]).casefold() in ("yes", "true"))
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
    if native in ("manatal:educations", "manatal:experiences"):
        return f"ASK the {q['title']} section takes entries one by one - the user adds them on the page"
    if kind == "file":
        if q.get("key") != "resume":
            return f"ASK not the resume box ({q['title']}) - the user uploads their own file there"
    if native == "manatal:date":
        return f"ASK date box ({q['title']}) - the user picks the date on the page's calendar"
    if native in ("manatal:checkbox", "manatal:radio"):
        return put_ticks(page, q, "checkbox" if native == "manatal:checkbox" else "radio")
    field = locate(page, q)
    if not field.count():
        return "FAIL question not on page"
    if kind == "file":
        return put_file(page, field, resume_file) if value is True and resume_file else "skipped - upload not approved"
    field.scroll_into_view_if_needed()
    if native == "manatal:boolean":
        return put_boolean(field, q)
    if field.evaluate("e => e.tagName") == "SELECT":
        return put_select(field, q)
    return put_text(field, value, kind)
