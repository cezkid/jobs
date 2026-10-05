"""Greenhouse (job-boards.greenhouse.io, or embedded on an employer's own page as ?gh_jid=): questions from its
public job board, answers typed into its widgets.

Measured facts and why each rule exists: app/docs/apply/greenhouse.md.
"""
import contextlib
import re
import time
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote, urlsplit

import httpx

from apply import dom
from apply.questions import key_from_title, question

NAME = "Greenhouse"
# job-boards / boards, EU host too; the embed link carries the board + job as ?for=...&token=...
POSTING_URL = re.compile(r"https?://(?:job-)?boards(\.eu)?\.greenhouse\.io/(?!embed/)([\w-]+)/jobs/(\d+)", re.I)
EMBED_URL = re.compile(r"https?://(?:job-)?boards(\.eu)?\.greenhouse\.io/embed/job_app\?(?=.*\bfor=([\w-]+))(?=.*\btoken=(\d+))", re.I)
# employer's own careers page w/ the Greenhouse form embedded: job id only, board looked up (board_for)
EMPLOYER_URL = re.compile(r"https?://[^?#]+\?(?:[^#]*&)?gh_jid=(\d+)", re.I)
# Greenhouse sends an embed link w/o the board on to the one naming it - the listing id is all that goes out
LOOKUP = "https://boards.greenhouse.io/embed/job_app?token={}"
# freehire `source` whose links land here (test_systems_live.py); link shapes, anonymised
SOURCES = ("greenhouse",)
EXAMPLES = ("https://job-boards.greenhouse.io/acme/jobs/4001234005",
            "https://boards.greenhouse.io/acme/jobs/4001234005?gh_src=x",
            "https://job-boards.eu.greenhouse.io/acme/jobs/4001234005",
            "https://job-boards.greenhouse.io/embed/job_app?for=acme&token=4001234005")
# questions() is a plain HTTP read, no browser: the live test runs it
QUESTIONS_OVER_HTTP = True
READY = "#first_name"
# a chosen file POSTs to Greenhouse's storage at once, before Submit (3 of 3 employers, 2026-10-05)
FILE_ON_CHOICE = True
IDLE_WAIT_MS, SHOWN_WAIT_MS = 15000, 20000
# the same file chosen again changes nothing on the page; a fill reloads it (plan-29g.25, measured)
NOT_READY = ("FAIL the page wasn't ready for the file (its own 'uploadFile' error; the same file chosen again does "
             "nothing) - fill again (it reloads the page), or reload it and attach the file by hand")
# Greenhouse type -> shared kind; a type missing here is asked as text
KIND = {"input_text": "text", "textarea": "longtext", "input_file": "file",
        "multi_value_single_select": "choice", "multi_value_multi_select": "multichoice"}
SYSTEM_KEY = {"first_name": "first_name", "last_name": "last_name", "email": "email", "phone": "phone",
              "resume": "resume", "cover_letter": "cover_letter"}
SYSTEM_KIND = {"email": "email", "phone": "phone"}
LOCATION = "candidate-location"
# the phone box's own Country list: required on the page, absent from the job board's list
COUNTRY = "country"
# Hispanic/Latino shows on the page beside the government (EEOC) race list, not in the job board's list
HISPANIC = ("hispanic_ethnicity", "Are you Hispanic/Latino?", ["Yes", "No", "Decline To Self Identify"])


def matches(url: str) -> bool:
    url = url.strip()
    return bool(POSTING_URL.match(url) or EMBED_URL.match(url) or EMPLOYER_URL.match(url))


@lru_cache(maxsize=64)
def board_for(job: str) -> tuple[str, str]:
    """(host suffix, board) for a job id seen only on an employer's page: Greenhouse redirects the
    board-less embed link to the one naming it (10 of 10 employer-site links, 2026-10-04)."""
    r = httpx.get(LOOKUP.format(job), timeout=30)
    m = r.is_redirect and EMBED_URL.match(r.headers.get("location", ""))
    if not m:
        raise ValueError("posting not found on Greenhouse - it may have closed")
    return m.group(1) or "", m.group(2)


def parse_url(url: str) -> tuple[str, str, str]:
    """(host suffix "" or ".eu", board, job id)."""
    url = url.strip()
    if m := POSTING_URL.match(url) or EMBED_URL.match(url):
        return m.group(1) or "", m.group(2), m.group(3)
    if m := EMPLOYER_URL.match(url):
        return *board_for(m.group(1)), m.group(1)
    raise ValueError(f"not a Greenhouse posting link: {url}")


def application_url(url: str) -> str:
    eu, board, job = parse_url(url)
    return f"https://job-boards{eu}.greenhouse.io/{board}/jobs/{job}"


def embed_url(url: str, site: str) -> str:
    """The bare form for a board that sends its job page on to the employer's own site (2026-10): `b=` names that site, so Greenhouse serves the form instead of redirecting."""
    eu, board, job = parse_url(url)
    return f"https://job-boards{eu}.greenhouse.io/embed/job_app?for={board}&token={job}&b={quote(site, safe='')}"


def recover(page, url: str) -> None:
    """Landed off Greenhouse (the board redirects to the employer's careers page, no form there)
    -> open the embedded form for the same job on this tab."""
    here = urlsplit(page.url)
    if here.hostname and not here.hostname.endswith("greenhouse.io"):
        page.goto(embed_url(url, f"{here.scheme}://{here.hostname}"))


def from_board(job: dict) -> list[dict]:
    out = []
    for q in job.get("questions") or []:
        # Resume/CV + Cover Letter come as an upload and a paste-in box: the upload is the question
        f = next((f for f in q["fields"] if f["type"] != "input_hidden"), None)
        if f is None:
            continue
        kind = SYSTEM_KIND.get(f["name"]) or KIND.get(f["type"], "text")
        options = [v["label"] for v in f.get("values") or []]
        if kind == "choice" and sorted(options) == ["No", "Yes"]:
            kind = "yesno"
        out.append(question(f["name"], q["label"], kind, bool(q.get("required")), options,
                            SYSTEM_KEY.get(f["name"]) or key_from_title(q["label"], kind), f["type"]))
        if f["name"] == "phone":
            out.append(question(COUNTRY, "Country (of your phone number)", "choice", True, native="country"))
    if any(f["name"] == "location" for q in job.get("location_questions") or [] for f in q["fields"]):
        out.append(question(LOCATION, "Location (City)", "location", True, key="location", native="location"))
    for q in (job.get("demographic_questions") or {}).get("questions") or []:
        kind = "multichoice" if q["type"] == "multi_value_multi_select" else "choice"
        out.append(question(str(q["id"]), q["label"], kind, bool(q.get("required")),
                            [o["label"] for o in q["answer_options"] if not o.get("free_form")], native="demographic"))
    eeoc = [(f["name"], q["label"], [v["label"] for v in f["values"]], bool(q.get("required")))
            for c in job.get("compliance") or [] for q in c["questions"] for f in q["fields"]]
    if any(name == "race" for name, *_ in eeoc):
        eeoc.insert(next(i for i, e in enumerate(eeoc) if e[0] == "race"), (*HISPANIC, False))
    for name, label, options, required in eeoc:
        # the job board names them "VeteranStatus", "Race": spaced as the page shows them
        out.append(question(name, re.sub(r"(?<=[a-z])(?=[A-Z])", " ", label), "choice", required, options, native="self-id"))
    return out


def questions(url: str) -> list[dict]:
    eu, board, job = parse_url(url)
    r = httpx.get(f"https://boards-api{eu}.greenhouse.io/v1/boards/{board}/jobs/{job}", params={"questions": "true"},
                  timeout=30)
    if r.status_code == 404:
        raise ValueError("posting not found - it may have closed")
    r.raise_for_status()
    return from_board(r.json())


def ids_on_page(page) -> list[str]:
    # education rows (school--0 ...) are optional extras; iti-* is the phone box's own country search;
    # a mark-all-that-apply list drawn as checkboxes is one question, named by the boxes' shared name
    return page.eval_on_selector_all(
        "form input[id], form textarea[id]",
        "es => [...new Set(es.filter(e => e.type !== 'hidden' && !e.id.includes('--') && !e.id.startsWith('iti-'))"
        ".map(e => e.id === 'cover_letter_text' || e.id === 'resume_text' ? null"
        " : e.type === 'checkbox' && e.name.endsWith('[]') ? e.name : e.id).filter(Boolean))]")


def by_id(page, id: str):
    return page.locator(f'[id="{id}"]').first


def digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def put_text(field, value: str, kind: str) -> str:
    # first focus on a name box: the page (signed in to MyGreenhouse) puts the saved name in it a
    # moment later - typed at once, the two ran together ("JaneAda", 2026-10-02). Wait, then type
    got = ""
    for _ in range(2):
        field.focus()
        field.page.wait_for_timeout(400)
        field.fill(str(value))
        field.blur()
        got = field.input_value()
        if (digits(got) == digits(str(value))) if kind == "phone" else got == str(value):
            return "ok"
    return f"FAIL shows '{got}'"


def picked(field) -> list[str]:
    """What a dropdown shows chosen: one value, or one tag per choice on a mark-all-that-apply list."""
    return field.evaluate("""e => { const c = e.closest('.select__control') || e.closest('.select');
      return c ? [...c.querySelectorAll('[class*=single-value], [class*=multi-value__label]')].map(v => v.innerText.trim()) : []; }""")


def put_select(page, field, value, starts: bool = False) -> str:
    """Type to filter, then click the option whose text is the answer - never the first one offered.
    `starts`: the option only has to start with the answer (Location: "Springfield, Illinois, United States")."""
    for v in value if isinstance(value, list) else [value]:
        v = str(v).strip()
        if v in picked(field):
            continue
        field.click()
        field.fill("")
        field.press_sequentially(v.split(",")[0] if starts else v[:40], delay=50)
        options = page.locator(".select__menu [role=option]")
        try:
            options.first.wait_for(timeout=8000)
        except Exception:
            field.press("Escape")
            return f"ASK nothing on the list matches '{v}'"
        # Country options carry the dialing code ("United States +1"); once chosen it shows the code only
        raw = [t.strip() for t in options.all_inner_texts()]
        texts = [re.sub(r"\s\+\d+$", "", t) for t in raw]
        want = v.casefold()
        hit = next((i for i, t in enumerate(texts) if t.casefold() == want), None)
        if hit is None and starts:
            hit = next((i for i, t in enumerate(texts) if t.casefold().startswith(want)), None)
        if hit is None:
            field.fill("")
            field.press("Escape")
            return f"ASK no option '{v}'; offered: {', '.join(texts[:5])}"
        options.nth(hit).click()
        page.wait_for_timeout(300)
        code = re.search(r"\+\d+$", raw[hit])
        if not any(p.casefold().startswith(want) or (code and p == code.group()) for p in picked(field)):
            return f"FAIL '{v}' not selected"
    return "ok"


def box_names(boxes) -> list[str]:
    return boxes.evaluate_all("bs => bs.map(b => [...b.labels].map(l => l.innerText).join(' ').replace(/\\s+/g, ' ').trim())")


def wanted(value) -> list[str]:
    return [dom.norm(str(v)) for v in (value if isinstance(value, list) else [value])]


def put_boxes(boxes, value) -> str:
    """A mark-all-that-apply list drawn as checkboxes (`fieldset` of `input[name="question_<n>[]"]`, each
    named by its own label): tick each answer by its label, untick the rest, read every box back."""
    names = box_names(boxes)
    return dom.put_ticks([boxes.nth(i) for i in range(len(names))], names, wanted(value), role=False, single=False)


def put_file(page, q: dict, path: str) -> str:
    # the page readies its upload with a request of its own once loaded: a file chosen before that
    # gets "Cannot read properties of undefined (reading 'uploadFile')" (owner's run, plan-29g.25)
    with contextlib.suppress(Exception):  # a page that keeps polling never goes idle: the read-back decides
        page.wait_for_load_state("networkidle", timeout=IDLE_WAIT_MS)
    page.locator(f'input[type=file][id="{q["id"]}"]').set_input_files(path)
    # the name shows only once the file reached Greenhouse's storage
    shown = page.locator(f'[aria-labelledby="upload-label-{q["id"]}"] .file-upload__filename').get_by_text(Path(path).name)
    said = page.locator(f'[id="{q["id"]}-error"]')
    deadline = time.monotonic() + SHOWN_WAIT_MS / 1000
    while time.monotonic() < deadline:
        if "uploadfile" in " ".join(said.all_inner_texts()).casefold():
            return NOT_READY
        if shown.count():
            return "ok"
        page.wait_for_timeout(250)
    return "ASK upload not confirmed on page - check the box"


def holds(page, q: dict) -> bool:
    """The answer still shows, read off the page once the form had time to keep it (form.recheck): a
    dropdown by the choice it shows (single value / tags), never the filler's word - a live form showed
    every dropdown empty that fill had reported ok (plan-29g.20)."""
    kind, value = q["kind"], q["answer"]
    boxes = page.locator(f'input[type=checkbox][name="{q["id"]}"]')
    if boxes.count():
        want = wanted(value)
        return all((n in want) == t for n, t in zip(box_names(boxes), boxes.evaluate_all("bs => bs.map(b => b.checked)")))
    field = by_id(page, q["id"])
    if not field.count():
        return False
    if field.get_attribute("role") == "combobox":
        shown = [p.casefold() for p in picked(field)]
        if q["id"] == COUNTRY:  # shows the dialing code only ("+1")
            return bool(shown)
        if kind == "yesno":
            value = "Yes" if str(value).casefold() in ("yes", "true") else "No"
        return all(any(p.startswith(str(v).strip().casefold()) for p in shown)
                   for v in (value if isinstance(value, list) else [value]))
    got = field.input_value()
    return digits(got) == digits(str(value)) if kind == "phone" else got == str(value)


def fill(page, q: dict, resume_file: str | None) -> str:
    kind, value = q["kind"], q["answer"]
    if kind == "file":
        # the resume goes in the resume box only; a cover letter box gets the letter made for this job
        if q.get("key") not in ("resume", "cover_letter"):
            return f"ASK not the resume box ({q['title']}) - the user uploads their own file there"
        if q.get("key") == "cover_letter" and not resume_file:
            return "ASK cover letter box - no letter made for this job (letter prepare), or the user uploads their own"
        if not page.locator(f'input[type=file][id="{q["id"]}"]').count():
            return "FAIL question not on page"
        return put_file(page, q, resume_file) if value is True and resume_file else "skipped - upload not approved"
    field = by_id(page, q["id"])
    if not field.count():
        # Race shows only after Hispanic/Latino = No; others only for some answers
        return "skipped - not shown for the other answers" if q.get("native") == "self-id" else "FAIL question not on page"
    # the same kind of question is a dropdown on one form, checkboxes on another (both on one form, 2026-10-05)
    boxes = page.locator(f'input[type=checkbox][name="{q["id"]}"]')
    if boxes.count():
        return put_boxes(boxes, value)
    field.scroll_into_view_if_needed()
    if field.get_attribute("role") == "combobox":
        if kind == "yesno":
            value = "Yes" if str(value).casefold() in ("yes", "true") else "No"
        return put_select(page, field, value, starts=kind == "location")
    return put_text(field, value, kind)
