"""Zoho Recruit (<tenant>.zohorecruit.com/jobs/Careers/<id>): questions from the posting's public form
definition (plain HTTP), answers typed into its Lyte widgets once the posting's own apply button shows the
form on the same page.

Measured facts and why each rule exists: app/docs/apply/zoho.md.
"""
import json
import re
from pathlib import Path

import httpx

from apply import dom
from apply.questions import (MONTHS, asks_complete_history, form_roles, key_from_title, left_on_page, question,
                             signs)

NAME = "Zoho Recruit"
# /jobs/<portal page>/<18-digit job id>, a slug after it on the page's own links (og:url ...?source=CareerSite)
POSTING_URL = re.compile(r"https?://([\w-]+)\.zohorecruit\.com/jobs/([\w-]+)/(\d{12,20})(?:/[^?#]*)?(?:[?#].*)?$", re.I)
SOURCES = ("zohorecruit",)
EXAMPLES = ("https://acme.zohorecruit.com/jobs/Careers/600000000000123456",
            "https://acme.zohorecruit.com/jobs/Careers/600000000000123456?utm_source=freehire.me",
            "https://acme.zohorecruit.com/jobs/Careers/600000000000123456/Software-Engineer?source=CareerSite")
# questions() = two plain GETs (the posting page, its form definition), no browser: the live test runs it
QUESTIONS_OVER_HTTP = True
# one set of Educational Details boxes per school on the resume (a row each, the section's own Add button)
EDUCATION_ENTRIES = True
# zip / city / state boxes search the tenant's own place list with each key typed (Locations/search); the
# Skill Set box its skills list (competency_skills) - GETs to the employer's Zoho Recruit, before Submit
SEARCHED_AS_TYPED = ("zip", "city", "state", "skills")
DEFINITION = "https://{tenant}.zohorecruit.com/recruit/v2/public/Job_Openings/{job}/apply/{webform}"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/141.0.0.0 Safari/537.36"}
# the posting's apply button (its words are the tenant's own: "I'm interested", "Apply now") or the form
# itself: either says the posting is open (form.closed); recover() opens the form from the button
APPLY = "lyte-button#detail-page-applybtn"
FORM_BOX = '[name^="rec-form_"]'
READY = f"{APPLY}, {FORM_BOX}"
# Zoho data type -> shared kind (13 forms, 2026-10-21); a type missing here is asked as text, never filled
KIND = {"text": "text", "email": "email", "phone": "phone", "website": "url", "textarea": "longtext",
        "picklist": "choice", "multipicklist": "multichoice", "boolean": "yesno", "currency": "number",
        "integer": "number", "bigint": "number", "double": "number", "decimal": "number"}
# Zoho's own fields, by api name
KEY = {"First_Name": "first_name", "Middle_Name": "middle_name", "Last_Name": "last_name",
       "Preferred_Name": "preferred_name", "Email": "email", "Mobile": "phone", "Phone": "phone",
       "Street": "street", "City": "city", "State": "state", "Zip_Code": "zip", "LinkedIn__s": "linkedin"}
SKILLS_UI = 600  # Skill_Set: a search box that adds a chip per skill
# screening question ("Assessments") type -> (kind, native); 2 a text area, 3 Yes / No radios, 4 radios,
# 5 ticks, 6 a list (19 questions, 2 forms, 2026-10-21)
ASSESSMENT = {2: ("longtext", "zoho:textarea"), 3: ("choice", "zoho:radio"), 4: ("choice", "zoho:radio"),
              5: ("multichoice", "zoho:checks"), 6: ("choice", "zoho:picklist")}
NONE = "-None-"
# a tick whose words the shared signing check misses ("Applicant Certification and Accuracy of Information",
# a required tick on 1 of 13 forms): agreeing to it is the applicant's own act
VOUCHING = re.compile(r"\bcertif|\baccura|\bterms\b|\bagree|\bpolic(?:y|ies)\b|\backnowledg|\bauthori[sz]", re.I)
PHOTO = re.compile(r"photo", re.I)
LIST_WAIT_MS, OPEN_TRIES = 250, 8


def matches(url: str) -> bool:
    return bool(POSTING_URL.match(url.strip()))


def link_parts(url: str) -> tuple[str, str, str]:
    """(tenant, portal page, job id)."""
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not a Zoho Recruit posting link: {url}")
    return m.group(1).lower(), m.group(2), m.group(3)


def parse_url(url: str) -> tuple[str, str]:
    """(tenant, job id) - the parts naming the employer + posting; the portal page ("Careers") is every
    tenant's word, never a name (link_parts has it)."""
    tenant, _, job = link_parts(url)
    return tenant, job


def application_url(url: str) -> str:
    # the form opens on the posting page itself (no address of its own)
    tenant, portal, job = link_parts(url)
    return f"https://{tenant}.zohorecruit.com/jobs/{portal}/{job}"


# --- the posting page + its form definition, read without a browser ---

def js_string(s: str) -> str:
    """A single-quoted JS string literal's body as the text it stands for (\\x22, \\u2013, \\/, \\-)."""
    simple = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}

    def one(m):
        e = m.group(1)
        if e[0] in "xu":
            return chr(int(e[1:], 16))
        return simple.get(e, e)
    return re.sub(r"\\(x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|.)", one, s, flags=re.S)


def page_facts(page: str) -> tuple[list[dict], str | None, str | None]:
    """(the page's job records, the apply form's id, the portal page's name) off the posting page."""
    m = re.search(r"var jobs = JSON\.parse\('(.*?)'\);", page, re.S)
    try:
        jobs = json.loads(js_string(m.group(1))) if m else []
    except ValueError:
        jobs = []
    form = re.search(r'"webform_id"\s*:\s*"(\d+)"', page)
    portal = re.search(r'"page_name"\s*:\s*"([^"]+)"', page)
    return jobs, form and form.group(1), portal and portal.group(1)


def why_closed(record: dict | None) -> str | None:
    """The posting page's own reasons (its detail template, 2026-10-21): no record of the job, a job taken
    off ("Position filled"), or one kept but read-only ("No longer accepting applications"); else None."""
    if record is None:
        return "the posting is not on the employer's Zoho Recruit careers page - it may have closed"
    if record.get("$read_only_job"):
        return "posting closed on Zoho Recruit - it says 'No longer accepting applications'"
    if record.get("Publish") is False:
        return "posting closed on Zoho Recruit - it says 'Position filled'"
    return None


def posting(url: str) -> tuple[dict, str, str]:
    """(the job's record, form id, portal page) - ValueError when the posting is gone or has no form."""
    _, portal, job = link_parts(url)
    r = httpx.get(application_url(url), headers=UA, timeout=60, follow_redirects=True)
    if r.status_code in (404, 410):
        raise ValueError("posting not found on Zoho Recruit - it may have closed")
    r.raise_for_status()
    jobs, form, page_name = page_facts(r.text)
    record = next((j for j in jobs if str(j.get("id")) == job), None)
    if why := why_closed(record):
        raise ValueError(why)
    if not form:
        raise ValueError("no application form on the Zoho Recruit posting page - the employer takes applications elsewhere")
    return record, form, page_name or portal


def definition(url: str) -> dict:
    tenant, job = parse_url(url)
    _, form, page_name = posting(url)
    r = httpx.get(DEFINITION.format(tenant=tenant, job=job, webform=form),
                  params={"pagename": page_name, "source": "CareerSite"}, headers=UA, timeout=30)
    r.raise_for_status()
    return r.json()


def norm(s) -> str:
    return " ".join(str(s or "").split())


def title_of(f: dict) -> str:
    """The box's label, and its hint where it has one (an SMS consent's words sit in the hint, 2026-10-21)."""
    label = norm(f.get("field_label"))
    hint = norm((f.get("tooltip") or {}).get("value")) if isinstance(f.get("tooltip"), dict) else ""
    return f"{label} - {hint}" if hint and hint.casefold() != label.casefold() else label


def field(f: dict) -> dict:
    """One of the form's own boxes (Basic Info, Address, the employer's sections)."""
    id, api, type = str(f["id"]), f.get("api_name") or "", f.get("data_type") or ""
    title, required = title_of(f), bool(f.get("required"))
    if f.get("ui_type") == SKILLS_UI:
        return question(id, f"{title} (skills, separated by commas)", "text", required, (), "skills", "zoho:skills")
    kind = KIND.get(type, "text")
    options = [norm(p["display_value"]) for p in f.get("pick_list_values") or [] if p.get("display_value") != NONE]
    if kind == "choice" and sorted(options) == ["No", "Yes"]:
        kind = "yesno"
    if type == "boolean":
        options = ["Yes", "No"]
        # a tick carrying terms to agree to (`termsandconditions`: 3 required on 1 of 13 forms) or vouching
        # words: agreeing is the applicant's own act - said so in the title, so it is never drafted
        if f.get("termsandconditions") and not signs(title):
            title += " - terms and conditions: ticking it agrees to them"
        elif VOUCHING.search(title) and not signs(title):
            title += " - ticking it: I certify / I agree"
    key = KEY.get(api) or key_from_title(title, kind)
    room = f.get("length") if kind in ("text", "longtext", "email", "url") and f.get("length") else None
    native = f"zoho:{type}" if type in KIND else f"zoho:other:{type}"
    return question(id, title, kind, required, options, key, native, max_chars=room)


def education(section: dict, sub: list[dict], schools: int) -> list[dict]:
    """Educational Details: one row of boxes per school on the resume; id <box>--<row>, native
    zoho:edu:<section>:<box>:<part> (the row's boxes are named <box>_<n>, its dates are four lists)."""
    out, sid = [], str(section["id"])
    by_api = {s.get("api_name"): s for s in sub}
    boxes = (("Institute_School", "School", "school", "text", "text"),
             ("Degree", "Degree", "degree", "text", "text"),
             ("Major_Department", "Major / Department", "discipline", "text", "text"))
    dates = (("from_month", "Start month", "school_start_month"), ("from_year", "Start year", "school_start_year"),
             ("to_month", "End month", "school_end_month"), ("to_year", "End year", "school_end_year"))
    for i in range(max(1, schools)):
        for api, title, key, kind, part in boxes:
            if s := by_api.get(api):
                out.append(question(f"{s['id']}--{i}", f"Education {i + 1}: {title}", kind, bool(s.get("required")),
                                    (), key, f"zoho:edu:{sid}:{s['id']}:{part}", entry=i, max_chars=s.get("length")))
        if s := by_api.get("Duration"):
            for part, title, key in dates:
                out.append(question(f"{s['id']}-{part}--{i}", f"Education {i + 1}: {title}",
                                    "choice" if part.endswith("month") else "number", False,
                                    MONTHS if part.endswith("month") else (), key, f"zoho:edu:{sid}:{s['id']}:{part}",
                                    entry=i))
        if s := by_api.get("Currently_pursuing"):
            # never "currently pursuing" in the title: the shared student answer would tick every school
            out.append(question(f"{s['id']}--{i}", f"Education {i + 1}: still in progress (tick)", "yesno", False,
                                ["Yes", "No"], None, f"zoho:edu:{sid}:{s['id']}:tick", entry=i))
    return out


def experience(section: dict, sub: list[dict]) -> dict:
    """Experience Details: one yes / no - the jobs from the resume added a row each (questions.form_roles);
    the row's boxes by api name in native (zoho:work:<section>:<api>=<box>,...)."""
    boxes = ",".join(f"{s['api_name']}={s['id']}" for s in sub)
    return question(f"work:{section['id']}", f"{norm(section.get('display_label')) or 'Experience Details'}: add "
                    "the jobs from the resume, a row each (title, company, dates, the tailored page's lines as "
                    "Summary; Reason for Leaving stays yours on the page)", "yesno", False, ["Yes", "No"], None,
                    f"zoho:work:{section['id']}:{boxes}")


def screening(q: dict) -> dict:
    kind, native = ASSESSMENT.get(q.get("type"), ("text", f"zoho:assessment:{q.get('type')}"))
    options = [norm(o["value"]) for o in q.get("options") or []]
    if kind == "choice" and sorted(options) == ["No", "Yes"]:
        kind = "yesno"
    return question(str(q["id"]), norm(q.get("question")), kind, bool(q.get("ismandatory")), options, None, native)


def from_definition(d: dict, schools: int = 1) -> list[dict]:
    """The form's questions in page order: its sections, then the screening questions under them."""
    out = []
    form = (d.get("webforms") or [{}])[0]
    for section in form.get("sections") or []:
        if section.get("isattachment"):
            for a in section.get("attachmenttypes") or []:
                title = norm(a.get("field_label"))
                if a.get("api_name") == "$photo_id" or PHOTO.search(title):
                    continue  # never a photo (AGENTS.md "Photo: can't"), never required (6 of 6)
                key = {"RESUME": "resume", "COVERLETTER": "cover_letter"}.get(a.get("api_name")) or key_from_title(title, "file")
                out.append(question(str(a["id"]), title, "file", bool(a.get("required")), (), key,
                                    f"zoho:file:{a.get('$limit') or ''}"))
            continue
        fields = section.get("fields") or []
        if section.get("istabular"):
            table = next((f for f in fields if f.get("data_type") == "tabular"), None)
            sub = (table or {}).get("fields") or []
            if section.get("api_name") == "Educational_Details":
                out += education(section, sub, schools)
            elif section.get("api_name") == "Experience_Details":
                out.append(experience(section, sub))
            continue  # another table of the employer's own: the user adds its rows on the page
        for f in fields:
            if f.get("data_type") == "captcha" or f.get("visible") is False:
                continue  # the CAPTCHA is the applicant's own step (ids_on_page counts it for them)
            out.append(field(f))
    for q in (d.get("Assessments") or {}).get("questions") or []:
        out.append(screening(q))
    return out


def questions(url: str, schools: int = 1) -> list[dict]:
    return from_definition(definition(url), schools)


def closed(url: str) -> str | None:
    """Why the form isn't there (form.closed, when the page shows no apply button): None = still open."""
    try:
        posting(url)
    except httpx.HTTPStatusError as e:
        return f"can't tell if the posting is open - Zoho Recruit answered {e.response.status_code}"
    except httpx.HTTPError as e:
        return f"can't tell if the posting is open - Zoho Recruit didn't answer ({type(e).__name__})"
    except ValueError as e:
        return str(e)
    return None


# --- the page in the browser ---

def recover(page, url: str) -> None:
    """The form shows on the posting page once its apply button is pressed (no new address). The cookie
    notice lays a layer over the page until the user chooses (theirs, never clicked): the button's own click
    runs under it."""
    if page.locator(f"{FORM_BOX}:visible").count():
        return
    button = page.locator(f"{APPLY}:visible").first
    if button.count():
        button.evaluate("b => b.click()")
    page.locator(f"{FORM_BOX}:visible").first.wait_for(timeout=30000)


def comp(id: str) -> str:
    """A box's own component (the page keeps a <template> copy under the same id)."""
    return f'[id="rec-form_{id}"]:not(template)'


VALUE = """([id, arg]) => { const e = document.querySelector(`[id="rec-form_${id}"]:not(template)`);
  if (!e || !e.component) return null; const v = arg ? e.component.getValue(arg) : e.component.getValue();
  return v === undefined ? null : v; }"""


def value(page, id: str, arg: str | None = None):
    """What the form itself holds for the box - what Submit sends (getFormDataAndCheckValidation reads it)."""
    return page.evaluate(VALUE, [id, arg])


def ids_on_page(page) -> list[str]:
    """Every box the form shows, by its field id (the CAPTCHA too - the user's to type); never the photo,
    the mobile box's inner parts (rec-form_<id>_input...) or a table (rec-form_<layout>_<section>: its rows
    come from the resume)."""
    return page.evaluate("""() => [...document.querySelectorAll('[id^="rec-form_"]:not(template)')]
        .filter(e => /^rec-form_\\d+$/.test(e.id) && e.getClientRects().length && e.tagName !== 'REC-TABULAR-COMPONENT'
                && !/photo/i.test(e.getAttribute('cx-prop-label') || ''))
        .map(e => e.id.slice('rec-form_'.length))""")


def shown(page, id: str) -> bool:
    box = page.locator(comp(id))
    return bool(box.count()) and box.first.is_visible()


def fold(s) -> str:
    return norm(s).casefold()


def open_list(page, dropdown) -> bool:
    """A Lyte list opened like a person would: a click on its button; a layer over the page (the cookie
    notice) takes that click -> the button's own click event. The list sometimes draws a moment late after
    a row was added (hand-measured 2026-10-21): tried again, LIST_WAIT_MS apart."""
    button = dropdown.locator("lyte-drop-button").first
    items = page.locator("lyte-drop-item:visible")
    for i in range(OPEN_TRIES):
        if items.count():
            return True
        try:
            button.click(timeout=1500) if i == 0 else button.dispatch_event("click")
        except Exception:
            button.dispatch_event("click")
        page.wait_for_timeout(LIST_WAIT_MS)
    return bool(items.count())


def pick_item(page, item) -> None:
    try:
        item.click(timeout=3000)
    except Exception:
        item.dispatch_event("click")
    page.wait_for_timeout(200)


def put_pick(page, q: dict, want: str) -> str:
    """A list (picklist, a screening list): opened, the option whose words are the answer clicked - never
    the first offered. The form keeps its value (getValue)."""
    dd = page.locator(f'{comp(q["id"])} lyte-dropdown, lyte-dropdown[id="{q["id"]}"]').first
    if not dd.count():
        return "FAIL question not on page"
    if not open_list(page, dd):
        return "FAIL list didn't open"
    items = page.locator("lyte-drop-item:visible")
    texts = [norm(t) for t in items.all_inner_texts()]
    hit = next((i for i, t in enumerate(texts) if t.casefold() == fold(want)), None)
    if hit is None:
        page.keyboard.press("Escape")
        return f"ASK no option '{want}'; offered: {', '.join(t for t in texts if t != NONE)[:200]}"
    pick_item(page, items.nth(hit))
    return "ok" if holds(page, q) else f"FAIL '{texts[hit]}' not kept"


def put_multi(page, q: dict, want: list[str]) -> str:
    """A multi-pick list: each answer's option clicked (the list stays open between picks)."""
    dd = page.locator(f'{comp(q["id"])} lyte-dropdown').first
    if not dd.count():
        return "FAIL question not on page"
    have = {fold(v) for v in value(page, q["id"]) or []}
    for w in want:
        if fold(w) in have:
            continue
        if not open_list(page, dd):
            return "FAIL list didn't open"
        items = page.locator("lyte-drop-item:visible")
        texts = [norm(t) for t in items.all_inner_texts()]
        hit = next((i for i, t in enumerate(texts) if t.casefold() == fold(w)), None)
        if hit is None:
            page.keyboard.press("Escape")
            return f"ASK no option '{w}'; offered: {', '.join(texts)[:200]}"
        pick_item(page, items.nth(hit))
    page.keyboard.press("Escape")
    return "ok" if holds(page, q) else "FAIL the list shows other options"


OPTIONS = """(c) => [...c.querySelectorAll('lyte-radiobutton, lyte-checkbox')].map(o => {
  const i = o.querySelector('input'); return [o.getAttribute('lt-prop-label') || '', o.getAttribute('lt-prop-value') || '', !!(i && i.checked)]; })"""


def options_of(page, id: str) -> list[list]:
    box = page.locator(comp(id))
    return box.first.evaluate(OPTIONS) if box.count() else []


def put_options(page, q: dict, want: list[str]) -> str:
    """Radios (one) or ticks (several) by their words; each changed by its own input's click - the page's
    handlers run and the form keeps the pick (measured: a click on the input, 2026-10-21)."""
    got = options_of(page, q["id"])
    if not got:
        return "FAIL question not on page"
    names = [norm(n) for n, _, _ in got]
    if missing := [w for w in want if fold(w) not in {n.casefold() for n in names}]:
        return f"ASK no option '{missing[0]}'; offered: {', '.join(names)[:200]}"
    single = q["native"] == "zoho:radio"
    wanted = {fold(w) for w in want}
    inputs = page.locator(f"{comp(q['id'])} lyte-radiobutton input, {comp(q['id'])} lyte-checkbox input")
    for i, (name, _, on) in enumerate(got):
        if (fold(name) in wanted) != on and not (single and fold(name) not in wanted):
            inputs.nth(i).evaluate("e => e.click()")
            page.wait_for_timeout(100)
    return "ok" if holds(page, q) else "FAIL the form shows another choice"


def put_tick(page, q: dict, yes: bool) -> str:
    box = page.locator(f"{comp(q['id'])} input[type=checkbox]").first
    if not box.count():
        return "FAIL question not on page"
    if box.is_checked() != yes:
        box.evaluate("e => e.click()")
    return "ok" if box.is_checked() == yes else "FAIL the tick didn't change"


def phone_typed(answer) -> str | None:
    """The number as typed into the box (its own list says +1 first): a US / Canada number without its +1;
    another country's -> None (its code is picked on the page)."""
    v, d = str(answer).strip(), dom.digits(str(answer))
    if v.startswith("+"):
        return re.sub(r"^\+\s*1[\s.-]*", "", v) if d.startswith("1") and len(d) == 11 else None
    if len(d) == 11 and d.startswith("1"):
        return re.sub(r"^1[\s.-]*", "", v)
    return v if len(d) >= 7 else None


def put_text(page, q: dict, v: str) -> str:
    box = page.locator(f'[name="rec-form_{q["id"]}"]').first
    if not box.count():
        return "FAIL question not on page"
    box.scroll_into_view_if_needed()
    box.fill(v)
    box.blur()
    page.wait_for_timeout(150)
    return "ok" if holds(page, q) else f"FAIL shows '{value(page, q['id'])}'"


def put_phone(page, q: dict) -> str:
    v = phone_typed(q["answer"])
    if v is None:
        return f"ASK '{q['answer']}' isn't a US / Canada number - the user picks its country code beside the box"
    got = put_text(page, q, v)
    held = str(value(page, q["id"]) or "")
    if got == "ok" and not held.startswith("+1"):
        return f"ASK the box holds '{held}' - another country code in front: the user picks United States (+1) beside it"
    return got


def put_place(page, q: dict, v: str) -> str:
    """Zip / city / state: a search box on most tenants (lyte-autocomplete, its own place list), a plain
    box on some. Typed and left as typed - the form keeps the words (getValue); a suggestion is never
    picked: it would put its own city / state / country in the other boxes."""
    search = page.locator(f'lyte-autocomplete[id="{q["id"]}"] input').first
    if not search.count():
        return put_text(page, q, v)
    search.scroll_into_view_if_needed()
    search.fill("")
    search.press_sequentially(v, delay=50)
    page.wait_for_timeout(800)
    search.press("Tab")
    page.keyboard.press("Escape")
    return "ok" if holds(page, q) else f"FAIL shows '{value(page, q['id'])}'"


def skill_names(page, id: str) -> list[str]:
    return [norm(s.get("name")) for s in value(page, id) or [] if isinstance(s, dict)]


def type_skill(page, box, skill: str) -> None:
    """The skill's words in the search box, its search set off. Typed key by key, the box lost letters
    while its search came back ("proj" + "t management", 2026-10-21): the whole words set at once, then
    the key-up its search listens for (hand-measured: that searches, 9 of 9 skills)."""
    box.fill("")
    box.fill(skill)
    box.dispatch_event("keyup")
    page.wait_for_timeout(LIST_WAIT_MS)
    if box.input_value() != skill:
        box.fill("")
        box.press_sequentially(skill, delay=90)


def put_skills(page, q: dict) -> str:
    """Each skill typed in the search box, the suggestion with its exact words clicked (the list offers the
    typed words themselves when Zoho has no such skill); never a near one."""
    raw = q["answer"]
    want = [norm(s) for s in (raw if isinstance(raw, list) else re.split(r"[,;\n]", str(raw))) if norm(s)]
    box = page.locator(f"{comp(q['id'])} input#addSkills, {comp(q['id'])} input[name='-add-skills']").first
    if not box.count():
        return "FAIL question not on page"
    left = []
    for skill in want:
        if fold(skill) in {fold(s) for s in skill_names(page, q["id"])}:
            continue
        type_skill(page, box, skill)
        offered = page.locator(".skl-suggested-skill li:visible")
        hit = None
        for _ in range(16):
            page.wait_for_timeout(LIST_WAIT_MS)
            texts = [norm(t) for t in offered.all_inner_texts()]
            hit = next((i for i, t in enumerate(texts) if t.casefold() == fold(skill)
                        or t.endswith("...") and fold(skill).startswith(t[:-3].casefold())), None)
            if hit is not None:
                break
        if hit is None:
            left.append(skill)
            box.fill("")
            continue
        pick_item(page, offered.nth(hit))
    box.fill("")
    page.keyboard.press("Escape")
    missing = [s for s in want if fold(s) not in {fold(x) for x in skill_names(page, q["id"])}]
    if missing:
        return f"ASK not added: {', '.join(missing)[:200]} - the user adds them on the page"
    return "ok"


def file_limit(q: dict) -> int | None:
    tail = str(q.get("native") or "").rsplit(":", 1)[-1]
    return int(tail) if tail.isdigit() else None


def queued(page, id: str) -> list[str]:
    return page.locator(f"rec-file-upload-component{comp(id)}").first.evaluate(
        "e => (e.component.getValue('queueList') || []).map(q => q.name || (q.file && q.file.name) || '')") \
        if page.locator(f"rec-file-upload-component{comp(id)}").count() else []


def put_file(page, q: dict, path: str) -> str:
    """The file goes into the box's own queue - kept in the page until Submit sends it with the form
    (measured: no request on choosing, 2026-10-21)."""
    if (limit := file_limit(q)) and Path(path).stat().st_size > limit:
        return f"ASK the file is over the box's {limit // 1048576} MB - the user chooses a smaller one"
    chooser = page.locator(f'input[type=file][name="rec-form_{q["id"]}_file"]').first
    if not chooser.count():
        return "FAIL question not on page"
    chooser.set_input_files(path)
    for _ in range(20):
        if Path(path).name in queued(page, q["id"]):
            return "ok"
        page.wait_for_timeout(LIST_WAIT_MS)
    return "ASK upload not confirmed on page - check the resume box"


# --- the tables: Educational Details, Experience Details ---

def table(page, section: str):
    return page.locator(f'rec-tabular-component[id$="_{section}"]').first


def rows(page, section: str) -> list[str]:
    """The table's row numbers in page order, off its boxes' names (<box>_<n>)."""
    t = table(page, section)
    if not t.count():
        return []
    return t.evaluate("""t => [...new Set([...t.querySelectorAll('[name]')].map(e => (e.getAttribute('name').match(/_(\\d+)$/) || [])[1])
        .filter(Boolean))]""")


def add_rows(page, section: str, n: int) -> list[str] | None:
    """Rows up to n, a click of the section's Add / Add More each (one button; its label counts the rows);
    None when the table won't take more."""
    add = page.locator(f'button[id^="crc-tabular-add-btn-"][id$="_{section}"]').first
    have = rows(page, section)
    while len(have) < n:
        if not add.count() or not add.is_enabled():
            return None
        add.dispatch_event("click")
        for _ in range(12):
            page.wait_for_timeout(LIST_WAIT_MS)
            if len(rows(page, section)) > len(have):
                break
        else:
            return None
        have = rows(page, section)
    return have


def put_date_list(page, box: str, row: str, part: str, v: str) -> str:
    """A month / year list of a row: the item whose value is the month's number (1-12) or the year."""
    dd = page.locator(f'lyte-dropdown[id="cxd-{box}_{row}_{part}"]').first
    if not dd.count():
        return f"FAIL no {part.replace('_', ' ')} list on the row"
    if str(dd.evaluate("d => d.ltProp('selected')")) == v:
        return "ok"
    for _ in range(OPEN_TRIES):
        open_list(page, dd)
        item = page.locator(f'lyte-drop-item:visible[data-value="{v}"]')
        if item.count():
            pick_item(page, item.first)
            break
        page.keyboard.press("Escape")
        page.wait_for_timeout(LIST_WAIT_MS)
    else:
        return f"ASK no '{v}' in the {part.replace('_', ' ')} list - the user picks it on the page"
    return "ok" if str(dd.evaluate("d => d.ltProp('selected')")) == v else f"FAIL {part.replace('_', ' ')} not kept"


def month_number(v) -> str | None:
    s = norm(v).casefold()
    if s.isdigit() and 1 <= int(s) <= 12:
        return str(int(s))
    return next((str(i + 1) for i, m in enumerate(MONTHS) if m.casefold().startswith(s[:3]) and len(s) >= 3), None)


def row_box(page, box: str, row: str):
    return page.locator(f'[name="{box}_{row}"]').first


def edu_parts(q: dict) -> tuple[str, str, str]:
    _, _, section, box, part = q["native"].split(":")
    return section, box, part


def put_edu(page, q: dict) -> str:
    section, box, part = edu_parts(q)
    have = add_rows(page, section, (q.get("entry") or 0) + 1)
    if have is None:
        return "ASK the table won't take another row - the user adds this school on the page"
    row, v = have[q.get("entry") or 0], q["answer"]
    if part == "tick":
        tick = row_box(page, box, row)
        if tick.is_checked() != dom.yes(v):
            tick.evaluate("e => e.click()")
        return "ok" if tick.is_checked() == dom.yes(v) else "FAIL the tick didn't change"
    if part == "text":
        field = row_box(page, box, row)
        field.fill(str(v))
        field.blur()
        return "ok" if field.input_value() == str(v) else f"FAIL shows '{field.input_value()}'"
    want = month_number(v) if part.endswith("month") else dom.digits(str(v))
    if not want:
        return f"ASK '{v}' is not a {part.split('_')[1]} - the user picks it on the page"
    return put_date_list(page, box, row, part, want)


def work_boxes(q: dict) -> tuple[str, dict]:
    _, _, section, boxes = q["native"].split(":", 3)
    return section, dict(b.split("=", 1) for b in boxes.split(",") if "=" in b)


def resume_facts(resume_file: str | None) -> tuple[dict, dict]:
    """Master resume + this job's tailored lines (the tailored page's bullets go on the form, as on the PDF)."""
    import cfg
    from resume import schema, tailor
    master = schema.load(cfg.resume_path(cfg.load(), "master"))
    tailored = {}
    if resume_file:
        saved = Path(resume_file).parent / tailor.JOB_DATA / "tailored.json"
        if saved.exists():
            tailored = json.loads(saved.read_text(encoding="utf-8"))
    return master, tailored


def summary(role: dict, tailored: dict, room: int = 6000) -> str:
    lines = next((e["bullets"] for e in tailored.get("entries", []) if e["id"] == role.get("id")), None)
    texts = [b["text"] for b in lines] if lines is not None else [b["claim"] for b in role.get("bullets", [])]
    return "\n".join("- " + t for t in texts)[:room]


def when(v) -> tuple[str | None, str | None]:
    """'2023-02' -> ('2', '2023'); '2016' -> (None, '2016'); present / blank -> (None, None)."""
    if not v or str(v).casefold() == "present":
        return None, None
    year, _, month = str(v).partition("-")
    return (str(int(month)) if month.isdigit() else None), (year if year.isdigit() else None)


def row_values(page, boxes: dict, row: str) -> tuple[str, str]:
    get = lambda api: row_box(page, boxes[api], row).input_value() if api in boxes and row_box(page, boxes[api], row).count() else ""
    return get("Occupation_Title"), get("Company")


def add_role(page, section: str, boxes: dict, row: str, role: dict, tailored: dict) -> list[str]:
    """One job into one row -> what didn't take."""
    bad = []
    for api, v in (("Occupation_Title", role.get("title")), ("Company", role.get("company")),
                   ("Summary", summary(role, tailored))):
        if api in boxes and v:
            box = row_box(page, boxes[api], row)
            box.fill(v)
            box.blur()
            if box.input_value() != v:
                bad.append(f"{api.replace('_', ' ')} shows '{box.input_value()[:40]}'")
    if "Work_Duration" in boxes:
        for side, v in (("from", role.get("start")), ("to", role.get("end"))):
            month, year = when(v)
            for part, x in ((f"{side}_month", month), (f"{side}_year", year)):
                if x and (r := put_date_list(page, boxes["Work_Duration"], row, part, x)) != "ok":
                    bad.append(r)
    now = str(role.get("end") or "").casefold() == "present"
    if now and "I_currently_work_here" in boxes:
        tick = row_box(page, boxes["I_currently_work_here"], row)
        if not tick.is_checked():
            tick.evaluate("e => e.click()")
        if not tick.is_checked():
            bad.append("'I currently work here' not ticked")
    return bad


def put_work(page, q: dict, resume_file: str | None) -> str:
    """The jobs the form gets (questions.form_roles: same as the tailored page unless the user chose all or
    the form asks for complete history), a row each; a row already holding a job's title + company is left."""
    section, boxes = work_boxes(q)
    master, tailored = resume_facts(resume_file)
    roles, note = form_roles(master, tailored, asks_complete_history(page.locator("body").inner_text()))
    if not roles:
        return note or "ok - no jobs on the resume"
    report = []
    for role in roles:
        name = f"{role.get('title')}, {role.get('company')}"
        have = rows(page, section)
        filled = {r: row_values(page, boxes, r) for r in have}
        if any((fold(t), fold(c)) == (fold(role.get("title")), fold(role.get("company"))) for t, c in filled.values()):
            report.append(f"{name}: already there")
            continue
        row = next((r for r, (t, c) in filled.items() if not t and not c), None)
        if row is None:
            more = add_rows(page, section, len(have) + 1)
            if more is None:
                report.append(f"{name}: ASK the table won't take another row - the user adds it on the page")
                continue
            row = more[-1]
        bad = add_role(page, section, boxes, row, role, tailored)
        report.append(f"{name}: " + (f"FAIL {'; '.join(bad)}" if bad else "ok"))
    if note:
        report.append(note)
    worse = [r for r in report if " FAIL" in f" {r}" or " ASK" in f" {r}"]
    return ("ASK " if worse else "ok - ") + "; ".join(worse or report)


# --- reading back ---

def holds(page, q: dict) -> bool:
    """The answer the form itself holds (each box's component getValue - what Submit sends), read once the
    form had time to keep it (form.recheck): text by its words (phone by digits), a list by the option it
    keeps, radios + ticks by the picked options' ids, skills by their chips, a table row by its boxes, the
    resume by its name in the box's queue. Nothing to read = False."""
    native, kind, v = q.get("native") or "", q["kind"], q["answer"]
    if kind == "file":
        return Path(str(v)).name in queued(page, q["id"]) if isinstance(v, str) else bool(queued(page, q["id"]))
    if native.startswith("zoho:work:"):
        section, boxes = work_boxes(q)
        return not dom.yes(v) or any(t for t, _ in (row_values(page, boxes, r) for r in rows(page, section)))
    if native.startswith("zoho:edu:"):
        section, box, part = edu_parts(q)
        have = rows(page, section)
        entry = q.get("entry") or 0
        if entry >= len(have):
            return False
        row = have[entry]
        if part == "tick":
            return row_box(page, box, row).is_checked() == dom.yes(v)
        if part == "text":
            return row_box(page, box, row).input_value() == str(v)
        dd = page.locator(f'lyte-dropdown[id="cxd-{box}_{row}_{part}"]').first
        want = month_number(v) if part.endswith("month") else dom.digits(str(v))
        return bool(dd.count()) and str(dd.evaluate("d => d.ltProp('selected')")) == want
    if native == "zoho:skills":
        raw = v if isinstance(v, list) else re.split(r"[,;\n]", str(v))
        have = {fold(s) for s in skill_names(page, q["id"])}
        return all(fold(s) in have for s in raw if norm(s))
    if native in ("zoho:radio", "zoho:checks"):
        want = {fold(x) for x in (v if isinstance(v, list) else [v])}
        got = options_of(page, q["id"])
        ids = {i for n, i, _ in got if fold(n) in want}
        if native == "zoho:radio":
            return bool(ids) and value(page, q["id"], "actual_value") in ids
        held = value(page, q["id"])
        held = json.loads(held) if isinstance(held, str) and held.startswith("[") else held or []
        return set(held) == ids
    if native == "zoho:boolean":
        box = page.locator(f"{comp(q['id'])} input[type=checkbox]").first
        return bool(box.count()) and box.is_checked() == dom.yes(v)
    held = value(page, q["id"])
    if native == "zoho:multipicklist":
        return {fold(x) for x in held or []} == {fold(x) for x in (v if isinstance(v, list) else [v])}
    if native == "zoho:picklist" or kind in ("choice", "yesno"):
        want = ("Yes" if dom.yes(v) else "No") if kind == "yesno" else v
        shown_words = page.locator(f'{comp(q["id"])} lyte-drop-button, lyte-dropdown[id="{q["id"]}"] lyte-drop-button')
        words = norm(shown_words.first.inner_text()) if shown_words.count() else ""
        return held not in (None, "", NONE) and fold(words) == fold(want)
    if kind == "phone":
        typed = phone_typed(v)
        return bool(typed) and dom.digits(str(held or "")).endswith(dom.digits(typed))
    if kind == "number":
        return dom.digits(str(held or "")) == dom.digits(str(v)) and bool(dom.digits(str(v)))
    return held == str(v)


def fill(page, q: dict, resume_file: str | None) -> str:
    native, kind, v = q.get("native") or "", q["kind"], q["answer"]
    if signs(q["title"]) or (native == "zoho:boolean" and VOUCHING.search(q["title"])):  # agreeing: theirs
        return left_on_page(q)
    if kind == "file":
        if q.get("key") not in ("resume", "cover_letter"):
            return f"ASK not the resume box ({q['title']}) - the user uploads their own file there"
        return put_file(page, q, resume_file) if v is True and resume_file else "skipped - upload not approved"
    if native.startswith("zoho:work:"):
        return put_work(page, q, resume_file) if dom.yes(v) else "skipped - user said no"
    if native.startswith("zoho:edu:"):
        return put_edu(page, q)
    if native.startswith(("zoho:other:", "zoho:assessment:")):
        return f"ASK a box Job Finder doesn't fill ({q['title'] or 'no words'}) - the user answers it on the page"
    if not page.locator(comp(q["id"])).count():
        return "FAIL question not on page"
    if not shown(page, q["id"]):
        return "skipped - hidden by the form's own rule for the other answers"
    if native == "zoho:skills":
        return put_skills(page, q)
    if native in ("zoho:radio", "zoho:checks"):
        want = v if isinstance(v, list) else [("Yes" if dom.yes(v) else "No") if kind == "yesno" else v]
        return put_options(page, q, [norm(x) for x in want])
    if native == "zoho:boolean":
        return put_tick(page, q, dom.yes(v))
    if native == "zoho:multipicklist":
        return put_multi(page, q, [norm(x) for x in (v if isinstance(v, list) else [v])])
    if native == "zoho:picklist" or kind in ("choice", "yesno"):
        return put_pick(page, q, ("Yes" if dom.yes(v) else "No") if kind == "yesno" else norm(v))
    if kind == "phone":
        return put_phone(page, q)
    if q.get("key") in ("zip", "city", "state"):
        return put_place(page, q, str(v))
    if kind == "number":
        n = re.sub(r"[^\d.]", "", str(v))
        return put_text(page, q | {"answer": n}, n) if n else f"ASK '{v}' is not a number - the box takes digits only"
    return put_text(page, q, str(v))
