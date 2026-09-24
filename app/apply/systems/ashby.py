"""Ashby (jobs.ashbyhq.com): questions from its public job board, answers typed into its widgets.

Measured facts and why each rule exists: app/docs/apply/ashby.md.
"""
import re
from pathlib import Path

import httpx

from apply.questions import key_from_title, question

NAME = "Ashby"
GRAPHQL = "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobPosting"
QUERY = """query ApiJobPosting($organizationHostedJobsPageName: String!, $jobPostingId: String!) {
  jobPosting(organizationHostedJobsPageName: $organizationHostedJobsPageName, jobPostingId: $jobPostingId) {
    title applicationForm { sections { fieldEntries { ... on FormFieldEntry { isRequired field } } } } } }"""
POSTING_URL = re.compile(r"https?://jobs\.ashbyhq\.com/([^/?#]+)/([0-9a-f-]{36})", re.I)
READY = "[data-field-path]"
# Ashby type -> shared kind; a type missing here is asked as text and flagged by the contract test
KIND = {"String": "text", "LongText": "longtext", "Email": "email", "Phone": "phone", "Number": "number",
        "Date": "date", "Location": "location", "Boolean": "yesno", "ValueSelect": "choice",
        "MultiValueSelect": "multichoice", "File": "file"}
SYSTEM_KEY = {"_systemfield_name": "name", "_systemfield_email": "email",
              "_systemfield_location": "location", "_systemfield_resume": "resume"}


def matches(url: str) -> bool:
    return bool(POSTING_URL.match(url.strip()))


def parse_url(url: str) -> tuple[str, str]:
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not a jobs.ashbyhq.com posting link: {url}")
    return m.group(1), m.group(2)


def application_url(url: str) -> str:
    org, posting = parse_url(url)
    return f"https://jobs.ashbyhq.com/{org}/{posting}/application"


def from_form(job: dict) -> list[dict]:
    out = []
    for section in job["applicationForm"]["sections"]:
        for entry in section["fieldEntries"]:
            f = entry.get("field")
            if not f or f.get("isDeactivated"):
                continue
            kind = KIND.get(f["type"], "text")
            out.append(question(
                f["path"], f["title"], kind, bool(entry.get("isRequired")),
                [v["label"] for v in f.get("selectableValues") or [] if not v.get("isArchived")],
                SYSTEM_KEY.get(f["path"]) or key_from_title(f["title"], kind), f["type"]))
    return out


def questions(url: str) -> list[dict]:
    org, posting = parse_url(url)
    r = httpx.post(GRAPHQL, timeout=30, json={
        "operationName": "ApiJobPosting", "query": QUERY,
        "variables": {"organizationHostedJobsPageName": org, "jobPostingId": posting}})
    r.raise_for_status()
    job = (r.json().get("data") or {}).get("jobPosting")
    if not job:
        raise ValueError("posting not found - it may have closed")
    return from_form(job)


def ids_on_page(page) -> list[str]:
    return page.eval_on_selector_all(READY, "es => es.map(e => e.dataset.fieldPath)")


def digits(s: str) -> str:
    return re.sub(r"\D", "", s)


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


def put_choice(box, value) -> str:
    for v in value if isinstance(value, list) else [value]:
        exact = re.compile(rf"^\s*{re.escape(str(v))}\s*$")
        label = box.locator("label", has_text=exact)
        if label.count():
            label.first.click()
            target = box.locator(f'input[id="{label.first.get_attribute("for")}"]')
            if target.count() and not target.first.is_checked():
                return f"FAIL '{v}' not selected"
            continue
        combo = box.locator("input[role=combobox]")  # long lists show as a search box
        if not combo.count():
            return f"FAIL no option '{v}'; offered: {', '.join(box.locator('label').all_inner_texts()[1:6])}"
        combo.first.fill(str(v))
        option = box.page.get_by_role("option", name=str(v), exact=True)
        if not option.count():
            return f"FAIL no option '{v}'"
        option.first.click()
    return "ok"


def put_file(box, path: str) -> str:
    box.locator("input[type=file]").first.set_input_files(path)
    try:
        box.get_by_text(Path(path).name).first.wait_for(timeout=20000)
    except Exception:
        return "ASK upload not confirmed on page - check the resume box"
    return "ok"


def fill(page, q: dict, resume_file: str | None) -> str:
    box = page.locator(f'[data-field-path="{q["id"]}"]').first
    if not box.count():
        return "FAIL question not on page"
    box.scroll_into_view_if_needed()
    kind, value = q["kind"], q["answer"]
    if kind == "file":
        return put_file(box, resume_file) if value is True and resume_file else "skipped - upload not approved"
    if kind == "location":
        return put_location(box, value)
    if kind == "yesno":
        return put_yes_no(box, value)
    if kind in ("choice", "multichoice"):
        return put_choice(box, value)
    return put_text(box, value, kind)
