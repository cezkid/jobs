"""Ashby (jobs.ashbyhq.com): questions from its public job board, answers typed into its widgets.

Measured facts and why each rule exists: app/docs/apply/ashby.md.
"""
import contextlib
import re
import time
from pathlib import Path
from urllib.parse import quote, unquote

import httpx

from apply.questions import MONTHS, key_from_title, question
from text import html_to_text

NAME = "Ashby"
GRAPHQL = "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobPosting"
QUERY = """query ApiJobPosting($organizationHostedJobsPageName: String!, $jobPostingId: String!) {
  jobPosting(organizationHostedJobsPageName: $organizationHostedJobsPageName, jobPostingId: $jobPostingId) {
    title applicationForm { sections { fieldEntries { ... on FormFieldEntry { isRequired descriptionHtml field } } } }
    surveyForms { sections { fieldEntries { ... on FormFieldEntry { isRequired descriptionHtml field } } } } } }"""
# the employer's public job list: says whether a posting the question read can't find was taken down
BOARD = "https://api.ashbyhq.com/posting-api/job-board/{org}"
POSTING_URL = re.compile(r"https?://jobs\.ashbyhq\.com/([^/?#]+)/([0-9a-f-]{36})", re.I)
# freehire `source` whose links land here (test_systems_live.py); link shapes, anonymised
SOURCES = ("ashby",)
EXAMPLES = ("https://jobs.ashbyhq.com/acme/45bdb7e5-14a8-494f-8fcb-30e42f0be67a",
            "https://jobs.ashbyhq.com/acme/45bdb7e5-14a8-494f-8fcb-30e42f0be67a/application?utm_source=x")
# questions() is a plain HTTP read, no browser: the live test runs it
QUESTIONS_OVER_HTTP = True
READY = "[data-field-path]"
# Ashby type -> shared kind; a type missing here is asked as text and flagged by the contract test
# (types on 111 open forms, 2026-10-05: ashby.md "Kinds on real forms")
KIND = {"String": "text", "LongText": "longtext", "Email": "email", "Phone": "phone", "Number": "number",
        "Date": "date", "Location": "location", "Boolean": "yesno", "ValueSelect": "choice",
        "MultiValueSelect": "multichoice", "File": "file", "Url": "url", "EducationHistory": "text"}
# Education History (ashby.md "Education History"): one block of boxes per school, the same ids in each
# block (block i = the i-th match on the page); the definition says which boxes show and which are required.
# Per box: definition name, page id suffix, title, shared key, kind
EDUCATION_PATH = "_systemfield_education_history"
EDUCATION_BOXES = (("schoolName", "school", "School", "school", "choice"),
                   ("degree", "degree", "Degree", "degree", "text"),
                   ("major", "major", "Field of Study", "discipline", "text"),
                   ("startDate", "startDate", "Start date month", "school_start_month", "choice"),
                   ("startDate", "startDate", "Start date year", "school_start_year", "number"),
                   ("endDate", "endDate", "End date month", "school_end_month", "choice"),
                   ("endDate", "endDate", "End date year", "school_end_year", "number"))
# questions(url, schools): one block per school on the resume, through the page's own "+ Add Education"
EDUCATION_ENTRIES = True
ADD_SCHOOL = re.compile(r"add education", re.I)
# how long the school search gets to offer its list
LIST_WAIT_MS = 8000
# what leaves when (ashby.md "What leaves the computer, when", 3 employers, 2026-10-05): the resume's
# upload starts the moment it is chosen; Location searches Ashby's place list with each key typed, the
# Education History school box its school list (ashby.md "Education History")
FILE_ON_CHOICE = True
SEARCHED_AS_TYPED = ("location", "school")
# page quiet before the file is chosen (as Greenhouse); how long the name gets to show; a failed upload
# shows its name too, so the page gets this long after the name to say it failed (ashby.md "Upload errors")
IDLE_WAIT_MS, SHOWN_WAIT_MS, ERROR_WAIT_MS = 15000, 20000, 3000
UPLOAD_FAILED = re.compile(r"failed to upload", re.I)
SYSTEM_KEY = {"_systemfield_name": "name", "_systemfield_email": "email",
              "_systemfield_location": "location", "_systemfield_resume": "resume"}


def matches(url: str) -> bool:
    return bool(POSTING_URL.match(url.strip()))


def parse_url(url: str) -> tuple[str, str]:
    """(org, posting); org as Ashby names it - a link spells a space in it %20, and the question read
    finds nothing under the %20 spelling (ashby.md "Closed posting")."""
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not a jobs.ashbyhq.com posting link: {url}")
    return unquote(m.group(1)), m.group(2)


def application_url(url: str) -> str:
    org, posting = parse_url(url)
    return f"https://jobs.ashbyhq.com/{quote(org, safe='')}/{posting}/application"


def education(f: dict, required: bool, schools: int) -> list[dict]:
    """Education History's boxes, one block per school on the resume. Start dates only when required:
    the resume has none."""
    out = []
    for i in range(max(1, schools)):
        for name, suffix, title, key, kind in EDUCATION_BOXES:
            level = f.get(name)
            if level not in ("optional", "required") or (key.startswith("school_start") and level != "required"):
                continue
            # no school name in the title: it would read as the question's topic (questions.TOPICS)
            out.append(question(f"{f['path']}--{key}--{i}", f"Education {i + 1}: {title}", kind,
                                required and level == "required", MONTHS if key.endswith("_month") else [],
                                key, f["type"], entry=i))
    return out


def from_form(job: dict, schools: int = 1) -> list[dict]:
    out = []
    # voluntary disclosure (gender, race, veteran) comes as surveyForms beside the application form
    forms = [job["applicationForm"], *(job.get("surveyForms") or [])]
    for section in (sec for form in forms for sec in form["sections"]):
        for entry in section["fieldEntries"]:
            f = entry.get("field")
            if not f or f.get("isDeactivated"):
                continue
            if f["type"] == "EducationHistory":
                out += education(f, bool(entry.get("isRequired")), schools)
                continue
            kind = KIND.get(f["type"], "text")
            # untitled box (a consent tick, ashby.md): its words are the entry's description - the page shows them
            title = f["title"].strip() or " ".join(html_to_text(entry.get("descriptionHtml")).split())
            out.append(question(
                f["path"], title, kind, bool(entry.get("isRequired")),
                [v["label"] for v in f.get("selectableValues") or [] if not v.get("isArchived")],
                SYSTEM_KEY.get(f["path"]) or key_from_title(title, kind), f["type"]))
    return out


def job_posting(org: str, posting: str) -> dict | None:
    r = httpx.post(GRAPHQL, timeout=30, json={
        "operationName": "ApiJobPosting", "query": QUERY,
        "variables": {"organizationHostedJobsPageName": org, "jobPostingId": posting}})
    r.raise_for_status()
    return (r.json().get("data") or {}).get("jobPosting")


def board_says(org: str, posting: str) -> str:
    """The question read gives null for a closed posting and a wrong link alike (ashby.md "Closed
    posting"): the employer's public job list, read once, tells which - never a guess."""
    r = httpx.get(BOARD.format(org=quote(org, safe="")), timeout=30)
    if r.status_code == 404:
        return "can't tell if the posting is open - the employer's Ashby board wasn't found (board moved?)"
    r.raise_for_status()
    if any(j.get("id") == posting for j in r.json().get("jobs") or []):
        return "can't tell if the posting is open - it is on the employer's Ashby board, but its form didn't load"
    return "the posting is no longer on the employer's Ashby board - it may have closed"


def closed(url: str) -> str | None:
    """Why the form isn't there (form.closed, when the page shows no form): None = Ashby still has it."""
    org, posting = parse_url(url)
    try:
        return None if job_posting(org, posting) else board_says(org, posting)
    except httpx.HTTPError as e:
        return f"can't tell if the posting is open - Ashby didn't answer ({type(e).__name__})"


def questions(url: str, schools: int = 1) -> list[dict]:
    org, posting = parse_url(url)
    job = job_posting(org, posting)
    if not job:
        raise ValueError(board_says(org, posting))
    return from_form(job, schools)


def ids_on_page(page) -> list[str]:
    # Education History's boxes are in the file once per school (path--key--i), never an extra
    return [i for i in page.eval_on_selector_all(READY, "es => es.map(e => e.dataset.fieldPath)") if i != EDUCATION_PATH]


def school_box(page, q: dict):
    """One Education History box's own wrapper in block q["entry"]: the school search's container, a text
    box's label + input, a date's month + year selects."""
    suffix = next(s for _, s, _, key, _ in EDUCATION_BOXES if key == q["key"])
    css = {"school": f'label[for="{EDUCATION_PATH}-school"] + div',
           "degree": f'div:has(> [id="{EDUCATION_PATH}-degree"])',
           "major": f'div:has(> [id="{EDUCATION_PATH}-major"])'}.get(suffix, f'[id="{EDUCATION_PATH}-{suffix}"]')
    return page.locator(css).nth(q.get("entry") or 0)


def box_of(page, q: dict):
    """The question's wrapper: one per form-definition path (try reads how each shows its answer)."""
    if q.get("native") == "EducationHistory":
        return school_box(page, q)
    return page.locator(f'[data-field-path="{q["id"]}"]').first


def digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def fold(s: str) -> str:
    return " ".join(str(s).split()).casefold()


def wanted(value) -> list[str]:
    return [str(v) for v in (value if isinstance(value, list) else [value])]


def shown_soon(field, value: str) -> bool:
    for _ in range(30):  # the page shows the pick a moment after the click
        if fold(field.input_value()) == fold(value):
            return True
        field.page.wait_for_timeout(100)
    return False


def put_text(box, value: str, kind: str) -> str:
    field = box.locator("textarea, input:not([type=file]):not([type=checkbox]):not([type=radio])").first
    field.fill(str(value))
    field.blur()
    got = field.input_value()
    same = digits(got) == digits(str(value)) if kind == "phone" else got == str(value)
    return "ok" if same else f"FAIL shows '{got}'"


def put_location(box, value: str) -> str:
    field = box.locator("input[role=combobox], input").first
    field.fill("")
    field.press_sequentially(value, delay=60)
    options = box.page.locator("[role=option]")
    try:
        options.first.wait_for(timeout=8000)
    except Exception:
        return f"ASK no place matched '{value}'"
    texts = options.all_inner_texts()
    wanted = value.split(",")[0].strip().casefold()
    pick = next((i for i, t in enumerate(texts) if t.casefold().startswith(wanted)), None)
    if pick is None:
        field.fill("")
        return f"ASK no place starts with '{value}'; offered: {', '.join(texts[:5])}"
    options.nth(pick).click()
    return "ok"


def put_yes_no(box, value) -> str:
    word = "Yes" if str(value).casefold() in ("yes", "true") else "No"
    button = box.get_by_role("button", name=word, exact=True)
    if button.get_attribute("aria-pressed") != "true":  # never click a chosen one: it might clear it
        button.click()
    for _ in range(30):  # the page marks the choice a moment after the click
        if button.get_attribute("aria-pressed") == "true":
            return "ok"
        box.page.wait_for_timeout(100)
    return f"FAIL {word} not selected"


def checked_soon(radio) -> bool:
    for _ in range(30):  # the page marks the choice a moment after the click
        if radio.is_checked():
            return True
        radio.page.wait_for_timeout(100)
    return False


def put_choice(box, value) -> str:
    for v in value if isinstance(value, list) else [value]:
        exact = re.compile(rf"^\s*{re.escape(str(v))}\s*$")
        label = box.locator("label", has_text=exact)
        if label.count():
            target = box.locator(f'input[id="{label.first.get_attribute("for")}"]')
            if not target.count():
                label.first.click()
                continue
            if not target.first.is_checked():  # never click a chosen one: a second click clears it
                label.first.click()
            if not checked_soon(target.first):
                return f"FAIL '{v}' not selected"
            continue
        # a long list (15 options, tenant D) is one search box whose value is the pick, no radios
        combo = box.locator("input[role=combobox]")
        if not combo.count():
            return f"FAIL no option '{v}'; offered: {', '.join(box.locator('label').all_inner_texts()[1:6])}"
        field = combo.first
        if fold(field.input_value()) == fold(v):  # never pick a chosen one again
            continue
        field.fill(str(v))
        option = box.page.get_by_role("option", name=str(v), exact=True)
        try:  # the list filters a moment after typing
            option.first.wait_for(timeout=8000)
        except Exception:
            field.fill("")
            return f"FAIL no option '{v}'"
        option.first.click()
        if not shown_soon(field, v):
            return f"FAIL '{v}' not selected"
    return "ok"


def add_school(page, entry: int) -> None:
    """School `entry`'s block comes with the page's own "+ Add Education", one block a click (block 0 shows)."""
    more = page.locator("button", has_text=ADD_SCHOOL)
    for _ in range(entry):
        if page.locator(f'label[for="{EDUCATION_PATH}-school"]').count() > entry or not more.count():
            return
        more.first.click()
        page.wait_for_timeout(300)


def put_school(box, value: str) -> str:
    """The school search: picked only when the list offers the school by its exact words - never a near
    name; none offered -> the user picks theirs on the page."""
    field = box.locator("input[role=combobox]").first
    if fold(field.input_value()) == fold(value):  # never pick a chosen one again
        return "ok"
    ask = f"ASK school '{value}' not on the form's list - the user picks theirs on the page"
    field.fill("")
    field.press_sequentially(value, delay=60)
    options = box.page.locator("[role=option]")
    try:  # the list filters a moment after typing
        options.first.wait_for(timeout=LIST_WAIT_MS)
    except Exception:
        field.fill("")
        return ask
    pick = next((i for i, t in enumerate(options.all_inner_texts()) if fold(t) == fold(value)), None)
    if pick is None:
        field.fill("")
        return ask
    options.nth(pick).click()
    return "ok" if shown_soon(field, value) else f"FAIL '{value}' not selected"


def chosen(select) -> str:
    return select.evaluate("s => s.selectedOptions[0] && s.value ? s.selectedOptions[0].text : ''")


def date_select(box, key: str):
    """A date's month (first) or year (second) select."""
    return box.locator("select").nth(0 if key.endswith("_month") else 1)


def put_date_part(select, value: str) -> str:
    labels = [t.strip() for t in select.locator("option").all_inner_texts()]
    label = next((t for t in labels if fold(t) == fold(value)), None)
    if label is None:
        return f"ASK no option '{value}' - the user picks it on the page"
    if fold(chosen(select)) != fold(label):  # never choose a chosen one again
        select.select_option(label=label)
    return "ok" if fold(chosen(select)) == fold(label) else f"FAIL '{value}' not selected"


def put_education(page, q: dict) -> str:
    entry = q.get("entry") or 0
    add_school(page, entry)
    box = school_box(page, q)
    if not box.count():
        return "FAIL question not on page"
    box.scroll_into_view_if_needed()
    key, value = q["key"], str(q["answer"])
    if key == "school":
        return put_school(box, value)
    if key in ("degree", "discipline"):
        return put_text(box, value, "text")
    return put_date_part(date_select(box, key), value)


def upload_error(page, name: str) -> str:
    """The page's own words for a failed upload ("<file> failed to upload"), else ''."""
    try:
        text = page.locator("body").inner_text(timeout=2000)
    except Exception:
        return ""
    return next((t for t in (" ".join(x.split()) for x in text.splitlines()) if name in t and UPLOAD_FAILED.search(t)), "")


def put_file(box, path: str) -> str:
    """A failed upload still shows the file name + "Replace" (3 of 3 employers): the name is no
    verdict. Ok = the name shows and the page says nothing failed for ERROR_WAIT_MS after it."""
    page, name = box.page, Path(path).name
    with contextlib.suppress(Exception):  # a page that keeps polling never goes idle: the read decides
        page.wait_for_load_state("networkidle", timeout=IDLE_WAIT_MS)
    box.locator("input[type=file]").first.set_input_files(path)
    shown = box.get_by_text(name)
    since = None
    deadline = time.monotonic() + SHOWN_WAIT_MS / 1000
    while time.monotonic() < deadline:
        if said := upload_error(page, name):
            return f"FAIL the page says '{said}' - choose the file again on the page, or check the resume box"
        if since is None and shown.count():
            since = time.monotonic()
        if since is not None and time.monotonic() - since >= ERROR_WAIT_MS / 1000:
            return "ok"
        page.wait_for_timeout(250)
    return "ASK upload not confirmed on page - check the resume box"


def holds(page, q: dict) -> bool:
    """The answer still shows, read off the page once the form had time to keep it (form.recheck),
    each kind as ashby.md "Read back" records it shows: a tick by its own checked state, a long list's
    pick + a place by the search box's value, Yes / No by the pressed button. Nothing to read = False."""
    box = box_of(page, q)
    if not box.count():
        return False
    kind, value = q["kind"], q["answer"]
    if q.get("native") == "EducationHistory":
        if q["key"] == "school":
            return fold(box.locator("input[role=combobox]").first.input_value()) == fold(value)
        if q["key"] not in ("degree", "discipline"):
            return fold(chosen(date_select(box, q["key"]))) == fold(value)
    if kind == "yesno":
        button = box.get_by_role("button", name="Yes" if str(value).casefold() in ("yes", "true") else "No", exact=True)
        return bool(button.count()) and button.first.get_attribute("aria-pressed") == "true"
    if kind in ("choice", "multichoice"):
        ticks = dict(box.locator("input[type=radio], input[type=checkbox]").evaluate_all(
            "es => es.map(e => [e.labels && e.labels[0] ? e.labels[0].innerText : '', e.checked])"))
        ticks = {fold(t): on for t, on in ticks.items()}
        if ticks:
            return all(ticks.get(fold(v)) is True for v in wanted(value))
        combo = box.locator("input[role=combobox]")
        return kind == "choice" and bool(combo.count()) and fold(combo.first.input_value()) == fold(value)
    field = box.locator("textarea, input:not([type=file]):not([type=checkbox]):not([type=radio])")
    if not field.count():
        return False
    got = field.first.input_value()
    if kind == "location":  # shows Ashby's own "City, State, Country" for the pick
        town = fold(str(value).split(",")[0])
        return bool(town) and town in fold(got)
    return digits(got) == digits(str(value)) if kind == "phone" else got == str(value)


def fill(page, q: dict, resume_file: str | None) -> str:
    if q.get("native") == "EducationHistory":  # school 2's boxes show once its block is added
        return put_education(page, q)
    box = box_of(page, q)
    if not box.count():
        return "FAIL question not on page"
    box.scroll_into_view_if_needed()
    kind, value = q["kind"], q["answer"]
    if kind == "file":
        # the resume goes in the resume box only; a cover letter box gets the letter made for this job
        if q.get("key") not in ("resume", "cover_letter"):
            return f"ASK not the resume box ({q['title']}) - the user uploads their own file there"
        if q.get("key") == "cover_letter" and not resume_file:
            return "ASK cover letter box - no letter made for this job (letter prepare), or the user uploads their own"
        return put_file(box, resume_file) if value is True and resume_file else "skipped - upload not approved"
    if kind == "location":
        return put_location(box, value)
    if kind == "yesno":
        return put_yes_no(box, value)
    if kind in ("choice", "multichoice"):
        return put_choice(box, value)
    return put_text(box, value, kind)
