"""Rippling Recruiting (ats.rippling.com): questions from the form definition inside the posting page,
answers put in its React form by each box's own `data-testid` (the definition's ids).

Measured facts and why each rule exists: app/docs/apply/rippling.md.
"""
import json
import re
from datetime import date

import httpx

from apply import dom
from apply.questions import key_from_title, left_on_page, question, signs

NAME = "Rippling"
# employer, posting id; the form is the same link + /apply; freehire's links add ?utm_source=freehire.me
POSTING_URL = re.compile(r"https?://ats\.rippling\.com/([\w-]+)/jobs/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-"
                         r"[0-9a-f]{12})(?:/apply)?/?(?:[?#].*)?$")
SOURCES = ("rippling",)
EXAMPLES = ("https://ats.rippling.com/acme/jobs/0e4c8300-8a74-4858-9a83-3e9566b708fb",
            "https://ats.rippling.com/acme-careers/jobs/0e4c8300-8a74-4858-9a83-3e9566b708fb?utm_source=freehire.me")
# questions() is one plain GET of the posting page, no browser: the live test runs it
QUESTIONS_OVER_HTTP = True
# the resume goes to Rippling's storage as soon as it is chosen, then is read to fill boxes (rippling.md)
FILE_ON_CHOICE = True
# the Location box searches places with each keystroke (rippling.md "Location")
SEARCHED_AS_TYPED = ("location",)
# ...through Google's place suggestions (Maps script loads as the town is typed, try 2026-10-27)
SEARCHED_WITH = "Google"
# first name: on all 24 forms read (rippling.md "Form definition")
READY = '[data-testid="input-first_name"]'
NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)
# Rippling's own boxes, by the definition's oid: (kind, key); the page's box is data-testid=<oid>
BASIC = {"first_name": ("text", "first_name"), "last_name": ("text", "last_name"), "email": ("email", "email"),
         "phone_number": ("phone", "phone"), "current_company": ("text", None),
         # "Location (city only)": the town they live in - home_address city (rippling.md "Location")
         "location": ("location", "city"), "linkedin_link": ("url", "linkedin"), "website_link": ("url", "website"),
         "resume": ("file", "resume"), "cover_letter": ("file", "cover_letter"), "pronouns": ("choice", None)}
# where a basic box's block is when its testid isn't the oid
BOX = {"pronouns": "pronouns_strategy"}
# the pronoun list as the page offers it (3 tenants, 2026-10-27); "Enter my pronouns" opens a box to type in
PRONOUNS = ["She/her/hers", "He/him/his", "They/them/theirs", "She/her/hers, they/them/theirs",
            "He/him/his, they/them/theirs", "Just use my name"]
# employer question types -> shared kind (45 + 24 forms, rippling.md "Question types")
KIND = {"KNOCKOUT": "choice", "SINGLE_SELECT_RADIO": "choice", "SINGLE_SELECT_DROPDOWN": "choice",
        "YES_NO_SCALE_4": "choice", "MULTI_SELECT_CHECKBOX": "multichoice", "SHORT_ANSWER": "text",
        "LONG_ANSWER": "longtext", "DATE": "date"}
# a 4-point scale: the definition gives 1-4, the page names them (rippling.md "Widgets")
SCALE = ["Strong No", "No", "Yes", "Strong Yes"]
# the voluntary EEO block, drawn when the posting turns it on; the same words on every tenant read (3, 2026-10-27)
EEO = {"eeoc.gender": ("Gender", ["Male", "Female", "Non-binary", "Choose not to disclose"]),
       "eeoc.race": ("Please identify your race",
                     ["American Indian or Alaskan Native", "Asian", "Black or African American",
                      "Middle Eastern or North African", "White", "Native Hawaiian or other Pacific Islander",
                      "Two or more races", "Choose not to disclose"]),
       "eeoc.hispanicOrLatino": ("Are you Hispanic/Latino?", ["Yes", "No", "Choose not to disclose"]),
       "eeoc.veteranStatus": ("Veteran Status",
                              ["I am not a protected veteran",
                               "I identify as one or more of the classifications of a protected veteran",
                               "Choose not to disclose"])}
# blocks the page draws that ids_on_page names: basic + EEO testids, an employer question's
# customQuestions.<group>.<key>, the text-message consent (the applicant's own, never filled)
ON_PAGE = re.compile(r"^(?:customQuestions\.\w+\.[0-9a-f-]{36}|eeoc\.\w+|sms_opt_in|"
                     + "|".join(sorted({BOX.get(o, o) for o in BASIC})) + ")$")
# the resume read fills name, email, phone + Location some seconds after the file is chosen (tenant A's form,
# 2026-10-27): the rest waits for it, so the read never lands over typed answers
PARSE_MS = 12000


def matches(url: str) -> bool:
    return bool(POSTING_URL.match(url.strip()))


def parse_url(url: str) -> tuple[str, str]:
    """(employer, posting id)."""
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not an ats.rippling.com posting link: {url}")
    return m.group(1), m.group(2)


def posting_url(url: str) -> str:
    employer, posting = parse_url(url)
    return f"https://ats.rippling.com/{employer}/jobs/{posting}"


def application_url(url: str) -> str:
    return f"{posting_url(url)}/apply?step=application"


def norm(s) -> str:
    return " ".join(str(s).replace(" ", " ").split())


def from_definition(post: dict) -> list[dict]:
    """The shared questions, in page order: Rippling's own boxes, each employer group's questions, the EEO block.
    An employer question's id is its group + key: one key can sit in two groups (a tenant, 2026-10-27)."""
    form = post.get("activeJobApplication")
    if not form:
        raise ValueError("the posting shows no application form - it may have closed")
    out = []
    for b in form.get("basicQuestions") or []:
        kind, key = BASIC.get(b["oid"], ("text", None))
        out.append(question(b["oid"], norm(b["title"]), kind, bool(b.get("required")),
                            PRONOUNS if b["oid"] == "pronouns" else (), key, f"basic:{b.get('fieldType')}"))
    for group in form.get("additionalQuestions") or []:
        for q in (group.get("form") or {}).get("questions") or []:
            qtype, title = q.get("questionType"), norm(q.get("title") or "")
            kind = KIND.get(qtype, "text")
            options = SCALE if qtype == "YES_NO_SCALE_4" else [norm(c) for c in q.get("strChoices") or []]
            if kind == "choice" and sorted(options) == ["No", "Yes"]:
                kind = "yesno"
            out.append(question(f"customQuestions.{group['id']}.{q['uniqueKey']}", title, kind, bool(q.get("isRequired")),
                                options, key_from_title(title, kind), qtype, max_chars=q.get("maxChars")))
    if post.get("eeocQuestionnaireEnabledForJobPost"):
        for id, (title, options) in EEO.items():
            out.append(question(id, title, "choice", False, options, native="eeoc"))
    return out


def posting_page(url: str):
    """The posting page, plain GET; a gone posting answers 308 to the job list (rippling.md "Closed posting")."""
    r = httpx.get(posting_url(url), timeout=30, follow_redirects=False)
    if r.status_code in (301, 302, 307, 308) and "job_not_found" in (r.headers.get("location") or ""):
        raise ValueError("posting not found on Rippling - it may have closed")
    r.raise_for_status()
    return r


def job_post(html: str) -> dict:
    m = NEXT_DATA.search(html or "")
    if not m:
        raise ValueError("no application form on the posting page - it may have closed")
    post = (((json.loads(m.group(1)).get("props") or {}).get("pageProps") or {}).get("apiData") or {}).get("jobPost")
    if not post:
        raise ValueError("no application form on the posting page - it may have closed")
    return post


def questions(url: str) -> list[dict]:
    return from_definition(job_post(posting_page(url).text))


def closed(url: str) -> str | None:
    """Why the form isn't there (form.closed): None = Rippling still has the posting."""
    try:
        job_post(posting_page(url).text)
    except ValueError as e:
        return str(e)
    except httpx.HTTPError as e:
        return f"can't tell if the posting is open - Rippling didn't answer ({type(e).__name__})"
    return None


def ids_on_page(page) -> list[str]:
    """Question ids the page shows, by its blocks' data-testid (the definition's own ids)."""
    tags = page.evaluate("() => [...document.querySelectorAll('form [data-testid]')].map(e => e.dataset.testid)")
    back = {v: k for k, v in BOX.items()}
    return list(dict.fromkeys(back.get(t, t) for t in tags if ON_PAGE.match(t)))


def box_of(page, q: dict):
    """The question's block: data-testid = its id (try reads how each shows its answer)."""
    return page.locator(f'form [data-testid="{BOX.get(q["id"], q["id"])}"]').first


def wanted(q: dict) -> list[str]:
    value = q["answer"]
    if isinstance(value, list):
        return [norm(v) for v in value]
    return [("Yes" if dom.yes(value) else "No") if q["kind"] == "yesno" else norm(value)]


def ticks(box) -> tuple[list, list[str]]:
    """A radio or tick set: Rippling draws each as a role=radio / role=checkbox block holding its words."""
    members = box.locator("[role=radio], [role=checkbox]").all()
    return members, [norm(m.inner_text()) or norm(m.get_attribute("aria-label") or "") for m in members]


def is_on(el) -> bool:
    return el.get_attribute("aria-checked") == "true"


def put_ticks(members, names: list[str], want: list[str], single: bool) -> str:
    """Clicked like a person on the visible block - a click on the hidden input does nothing (2026-10-27)."""
    if missing := [v for v in want if v not in names]:
        return f"ASK no option '{missing[0]}'; offered: {', '.join(names)[:200]}"
    for el, name in zip(members, names):
        if (name in want) != is_on(el) and not (single and name not in want):
            el.scroll_into_view_if_needed()
            el.click()
    wrong = [n for el, n in zip(members, names) if (n in want) != is_on(el)]
    return "ok" if not wrong else f"FAIL '{wrong[0]}' shows the wrong tick"


def shown(combo) -> str:
    """What a dropdown shows: its search box's value, or the words in the box."""
    return norm(combo.input_value() if combo.evaluate("e => e.tagName") == "INPUT" else combo.inner_text())


def put_menu(page, box, want: str) -> str:
    """A dropdown opens a list under the box; the option that is the answer is clicked - never the first offered."""
    combo = box.locator("[role=combobox]").first
    combo.scroll_into_view_if_needed()
    combo.click()
    options = page.locator("[role=option]")
    try:
        options.first.wait_for(timeout=5000)
    except Exception:
        return "FAIL the list didn't open - pick it on the page"
    texts = [norm(t) for t in options.all_inner_texts()]
    if want not in texts:
        page.keyboard.press("Escape")
        return f"ASK no option '{want}'; offered: {', '.join(texts)[:200]}"
    options.nth(texts.index(want)).click()
    page.wait_for_timeout(200)
    got = shown(combo)
    return "ok" if got == want else f"FAIL shows '{got}'"


def town_pick(texts: list[str], value: str) -> str | None:
    """The place to click: the option written as the answer, else the one US town of that name
    ("<town>" -> "<town>, <ST>, USA", never a UK town of that name or a "<town> Township" in another state)."""
    if value in texts:
        return value
    town = value.split(",")[0].strip().casefold()
    hits = [t for t in texts if t.split(",")[0].strip().casefold() == town and t.endswith(", USA")]
    return hits[0] if len(hits) == 1 else None


def put_location(page, box, value: str) -> str:
    """A place search: the town typed key by key (the search runs on keys), the matching place clicked.
    It replaces what the resume read put there ("NYC" from a resume, 2026-10-27)."""
    field = box.locator("input").first
    field.scroll_into_view_if_needed()
    field.click()
    field.fill("")
    field.press_sequentially(norm(value).split(",")[0], delay=40)
    options = page.locator("[role=option]")
    try:
        options.first.wait_for(timeout=8000)
    except Exception:
        return "ASK no places offered - pick the town on the page"
    texts = [norm(t) for t in options.all_inner_texts()]
    pick = town_pick(texts, norm(value))
    if pick is None:
        page.keyboard.press("Escape")
        return f"ASK which place is '{value}'? offered: {', '.join(texts)[:200]} - answer with one as written"
    options.nth(texts.index(pick)).click()
    page.wait_for_timeout(300)
    got = norm(field.input_value())
    return "ok" if got == pick else f"FAIL shows '{got}'"


def day(value) -> date | None:
    s = str(value).strip()
    for pattern in (r"(\d{4})-(\d{1,2})-(\d{1,2})", r"(\d{1,2})/(\d{1,2})/(\d{4})"):
        if m := re.fullmatch(pattern, s):
            y, mo, d = (m.group(1), m.group(2), m.group(3)) if "-" in s else (m.group(3), m.group(1), m.group(2))
            try:
                return date(int(y), int(mo), int(d))
            except ValueError:
                return None
    return None


def put_date(box, value) -> str:
    """Three boxes, MM / DD / YYYY (rippling.md "Widgets")."""
    when = day(value)
    if when is None:
        return f"ASK '{value}' is not a date - write it as YYYY-MM-DD"
    for part, text in (("month", f"{when.month:02d}"), ("day", f"{when.day:02d}"), ("year", str(when.year))):
        dom.put_text(box.locator(f'[data-testid="input-{part}"]').first, text, "text", editable=False)
    return "ok" if date_held(box, when) else "FAIL the date didn't take - type it on the page"


def date_held(box, when: date) -> bool:
    got = [box.locator(f'[data-testid="input-{p}"]').first.input_value() for p in ("month", "day", "year")]
    return [int(g) if g.isdigit() else None for g in got] == [when.month, when.day, when.year]


def phone(value) -> str:
    """Digits only; a US number's leading 1 dropped - the country box already says +1 US (rippling.md)."""
    digits = dom.digits(str(value))
    return digits[1:] if len(digits) == 11 and digits.startswith("1") else digits


def put_file(page, box, path: str, resume: bool) -> str:
    """Chosen = sent to Rippling's storage at once. The resume is then read and fills name, email, phone and
    Location: waited for (up to PARSE_MS), so typed answers come after it - never under it."""
    box.locator("input[type=file]").first.set_input_files(path)
    name = path.rsplit("/", 1)[-1]
    try:  # the box shows "Preview file : <name, cut short>" once it holds the file
        box.locator("button[aria-label^='Preview file'], button:has-text('Preview file')").or_(
            box.get_by_text(name[:12])).first.wait_for(timeout=10000)
    except Exception:
        return "ASK upload not confirmed on page - check the resume box"
    if resume:
        first = page.locator('[data-testid="input-first_name"]').first
        waited = 0
        while waited < PARSE_MS and not first.input_value():
            page.wait_for_timeout(500)
            waited += 500
    page.wait_for_timeout(1500)
    # its own words when the file didn't reach its storage (every try, upload blocked: 2026-10-27)
    if "upload failed" in box.inner_text().casefold():
        return "FAIL Rippling says the upload failed - choose the file again on the page"
    return "ok"


def text_field(box):
    return box.locator("textarea, input:not([type=file]):not([type=hidden]):not([role=combobox])").first


def holds(page, q: dict) -> bool:
    """The answer still shows, read off the page as a person sees it (form.recheck)."""
    box = box_of(page, q)
    if not box.count():
        return False
    kind, value = q["kind"], q["answer"]
    if kind == "file":
        return value is not True or "Preview file" in (box.inner_html() or "")
    if kind in ("choice", "multichoice", "yesno"):
        members, names = ticks(box)
        if members:
            want = wanted(q)
            return all((n in want) == is_on(m) for m, n in zip(members, names))
        combo = box.locator("[role=combobox]")
        return bool(combo.count()) and shown(combo.first) == wanted(q)[0]
    if kind == "date":
        return (when := day(value)) is not None and date_held(box, when)
    field = text_field(box)
    if not field.count():
        return False
    got = norm(field.input_value())
    if kind == "location":
        return bool(got) and got.split(",")[0].casefold() == norm(value).split(",")[0].casefold()
    if kind == "phone":
        return dom.digits(got) == phone(value)
    return got == str(value) if kind != "longtext" else got == norm(value)


def fill(page, q: dict, resume_file: str | None) -> str:
    kind, value = q["kind"], q["answer"]
    if signs(q["title"]):
        return left_on_page(q)
    box = box_of(page, q)
    if not box.count():
        return "FAIL question not on page"
    if kind == "file":
        if q.get("key") not in ("resume", "cover_letter"):
            return f"ASK not the resume box ({q['title']}) - the user uploads their own file there"
        if q.get("key") == "cover_letter" and not resume_file:
            return "ASK cover letter box - no letter made for this job (letter prepare), or the user uploads their own"
        return put_file(page, box, resume_file, q.get("key") == "resume") if value is True and resume_file else \
            "skipped - upload not approved"
    if kind in ("choice", "multichoice", "yesno"):
        members, names = ticks(box)
        if members:
            return put_ticks(members, names, wanted(q), single=kind != "multichoice")
        return put_menu(page, box, wanted(q)[0])
    if kind == "location":
        return put_location(page, box, value)
    if kind == "date":
        return put_date(box, value)
    field = text_field(box)
    if not field.count():
        return "FAIL no box to type in"
    field.scroll_into_view_if_needed()
    if kind == "phone":
        return dom.put_text(field, phone(value), "phone", editable=False)
    # one fill, never key by key: 689 characters typed per key stalled the page (2026-10-27)
    return dom.put_text(field, value, kind, editable=False)
