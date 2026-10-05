"""Paylocity (recruiting.paylocity.com): questions from the form definition in the apply page itself,
answers typed into its widgets, step by step ("Step 1 of N"), work history added from the resume.

One host for every employer, no account. The apply page carries the whole form as
`window.pageData = {...}` - a plain HTTP read, the same GET as opening the form. Measured facts
and why each rule exists: app/docs/apply/paylocity.md.
"""
import json
import re
from pathlib import Path

import httpx

from apply import dom
from apply.questions import LATER, asks_complete_history, form_roles, key_from_title, question

NAME = "Paylocity"
POSTING_URL = re.compile(r"https?://recruiting\.paylocity\.com/Recruiting/Jobs/(?:Details|Apply)/(\d+)(?=[/?#]|$)", re.I)
HOST = "https://recruiting.paylocity.com"
# freehire `source` whose links land here (test_systems_live.py); link shapes, anonymised
SOURCES = ("paylocity",)
EXAMPLES = ("https://recruiting.paylocity.com/Recruiting/Jobs/Details/1000001?utm_source=acme",
            "https://recruiting.paylocity.com/recruiting/jobs/Apply/1000001?ref=acme")
# questions() is a plain HTTP read, no browser: the live test runs it
QUESTIONS_OVER_HTTP = True
# steps of one page: fill works on the user's own tab, boxes on another step are LATER
PER_PAGE = True
# on every step (labelled boxes sit in .form-group); the first step's name box comes with it
READY = ".form-group"
# a picked file POSTs to Paylocity at once, before Submit (paylocity.md)
FILE_ON_CHOICE = True
PAGE_DATA = re.compile(r"window\.pageData\s*=\s*")
# info field -> (page id, kind, key, widget); widgets: text box, react-widgets dropdown (combo),
# native radios, tag box, file input. Definition `type` is null on every field (7 of 7): the name decides
INFO = {
    "emailAddress": ("info.email", "email", "email", "text"),
    "cellPhone": ("info.cellPhone", "phone", "phone", "text"),
    "homePhone": ("info.phone", "phone", None, "text"),
    "smsOptedIn": ("info.smsOptedIn", "yesno", None, "combo"),
    "appliedBefore": ("info.haveYouAppliedWithUsBefore", "yesno", None, "combo"),
    "workedHereBefore": ("info.haveYouWorkedWithUsBefore", "yesno", None, "combo"),
    "dateAvailable": ("info.dateAvailableToStart", "date", None, "text"),
    "howDidYouHear": ("info.howDidYouHearAboutUs", "choice", None, "radio"),
    "referredBy": ("info.referredBy", "text", None, "text"),
    "linkedInUrl": ("info.linkedIn", "url", "linkedin", "text"),
    "skills": ("info.skills", "text", None, "tags"),
    "uploadCoverLetter": ("btn-coverLetter", "file", "cover_letter", "file"),
}
# the name field is four boxes on the page (2026-10-03, 8 of 8)
NAMES = (("info.firstName", "First Name", "first_name", True), ("info.lastName", "Last Name", "last_name", True),
         ("info.middleName", "Middle Name", "middle_name", False),
         ("info.preferredName", "Preferred Name", "preferred_name", False))
# home address: shown only when `address` is included (2 tenants with city/state but no `address`: no box)
ADDRESS = (("country", "country", "Country", None, "list"), ("address", "address-1", "Address Line 1", "street", "lookup"),
           ("address2", "address-2", "Address Line 2", None, "text"), ("city", "city", "City", "city", "text"),
           ("address", "county", "County", None, "text"), ("state", "us-state", "State", "state", "list"),
           ("postalCode", "zip", "Zip Code", "zip", "text"))
# acknowledgements: the field is a block of lists, each from the page's own option list (same on 8 of 8)
SELF_ID = {"eeoGenderEthnicity": (("Gender", "genderOptions"), ("Race/Ethnicity", "raceOptions")),
           "eeoDisability": (("Disability status", "disabilityOptions"),),
           "ofccp": (("Veteran status", "militaryServiceOptions"),)}
WORK, SCHOOL, REFERENCES = "workHistory", "educationHistory", "references"
# present on the page: one JS pass for every question (fill + ids_on_page share it)
PRESENT = """qs => { const vis = e => !!e && !!e.getClientRects().length;
  const clean = s => (s || '').replace(/\\((?:required|optional)\\)/gi, '').replace(/\\s+/g, ' ').trim().toLowerCase();
  const labels = [...document.querySelectorAll('.form-group')].filter(vis)
    .map(g => clean((g.querySelector(':scope > label') || {}).innerText));
  const buttons = [...document.querySelectorAll('button')].filter(vis).map(b => clean(b.innerText));
  const anyVis = sel => [...document.querySelectorAll(sel)].some(vis);
  return qs.filter(q => {
    if (q.native === 'radio') return anyVis(`input[name="${q.id}"]`) || vis((document.querySelector(`input[name="${q.id}"]`) || {}).closest?.('[role=radiogroup]'));
    if (q.native === 'file') return anyVis(`[data-automation-id="${q.id}"]`);
    if (q.native === 'work') return anyVis('[id^="workHistory.companyName."]') || buttons.includes('add work history');
    if (q.native === 'school') return anyVis('[id^="educationHistory.name."]') || buttons.includes('add education');
    if (q.native === 'references') return buttons.some(b => b.includes('reference')) || labels.some(l => l.startsWith('reference'));
    if (q.native === 'label') return labels.includes(clean(q.title));
    return vis(document.getElementById(q.id));
  }).map(q => q.id); }"""


def matches(url: str) -> bool:
    return bool(POSTING_URL.match(url.strip()))


def parse_url(url: str) -> tuple[str]:
    """(job id,): the posting page and the form share it."""
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not a Paylocity (recruiting.paylocity.com) posting link: {url}")
    return m.groups()


def application_url(url: str) -> str:
    return f"{HOST}/Recruiting/Jobs/Apply/{parse_url(url)[0]}"


def page_data(html: str) -> dict | None:
    """The `window.pageData = {...};` inline script, as JSON (80-105 KB, 8 of 8)."""
    m = PAGE_DATA.search(html)
    return json.JSONDecoder().raw_decode(html, m.end())[0] if m else None


def option_texts(data: dict, name: str) -> list[str]:
    return [o["text"] for o in data.get(name) or [] if o.get("text")]


def values(field: dict) -> list[str]:
    """A field's choices: `label` is the text shown; null on the employer's own lists, where `value` is (8 of 8)."""
    return [v.get("label") or v["value"] for v in field.get("values") or []]


def info_questions(data: dict, fields: list[dict]) -> list[dict]:
    out, by_name = [], {f["name"]: f for f in fields}
    for f in fields:
        n, title, required = f["name"], " ".join(f["displayName"].split()), f["isRequired"]
        if n == "name":
            out += [question(id, t, "text", required and must, key=key, native="text", page="info")
                    for id, t, key, must in NAMES]
        elif n == "address":
            out += [question(f"public-site-address-{part}", label, "choice" if widget == "list" else "text",
                             bool(by_name.get(field, {}).get("isRequired")),
                             option_texts(data, "countriesOptions" if part == "country" else "statesOptions")
                             if widget == "list" else (), key, widget, page="info")
                    for field, part, label, key, widget in ADDRESS if field == "address" or field in by_name]
        elif n in ("country", "address2", "city", "state", "postalCode", "uploadAdditionalFiles"):
            continue  # address parts go with `address`; extra files: the user's own (unmeasured box)
        elif n == "desiredSalary":
            # input type 1: pay type list + range boxes; 2: one box (2026-10-03, both seen)
            if data["customJobApplication"].get("desiredSalaryInputType") == 1:
                out += [question("info.desiredSalaryType", f"{title} - hourly or yearly", "choice", required,
                                 option_texts(data, "desiredSalaryTypeOptions"), native="combo", page="info"),
                        question("info.minimumDesiredSalary", f"{title} - from", "number", required, native="text", page="info"),
                        question("info.maximumDesiredSalary", f"{title} - to", "number", False, native="text", page="info")]
            else:
                out.append(question("info.desiredSalaryDescription", title, "text", required, native="text", page="info"))
        elif n in INFO:
            id, kind, key, widget = INFO[n]
            options = values(f) if widget == "radio" else \
                ["Yes", "No"] if kind == "yesno" else []
            if kind == "date":
                title += " (MM/DD/YYYY)"
            out.append(question(id, title, kind, required, options, key or key_from_title(title, kind), widget, page="info"))
        else:  # a field not seen yet: found by its label, typed as text
            out.append(question(f"info.{n}", title, "text", required, native="label", page="info"))
    return out


def from_definition(data: dict) -> list[dict]:
    """The form's questions off its definition. Page = the section a box is in (steps per section unmeasured)."""
    form = data["customJobApplication"]
    out = [question("btn-resume", "Resume", "file", bool(data.get("requireResume")), key="resume", native="file",
                    page="info")]
    for s in sorted(form["sections"], key=lambda s: s["displayOrder"]):
        if not s["isIncluded"]:
            continue
        fields = sorted((f for f in s["fields"] if f["isIncluded"]), key=lambda f: f["displayOrder"])
        name = s["name"]
        if name == "info":
            out += info_questions(data, fields)
        elif name == WORK:
            out.append(question(WORK, "Add work history from the resume (company, title, dates, what you did)",
                                "yesno", bool(s["isOneRequired"]), ["Yes", "No"], native="work", page=name))
        elif name == SCHOOL:
            out.append(question(SCHOOL, "Add education from the resume (school, area of study)",
                                "yesno", bool(s["isOneRequired"]), ["Yes", "No"], native="school", page=name))
        elif name == REFERENCES:
            n = form.get("referencesRequiredCount") or 0
            out.append(question(REFERENCES, f"References{f' ({n} needed)' if n else ''}: name and phone of people "
                                "who know your work", "longtext", bool(form.get("referencesRequired")),
                                native="references", page=name))
        else:
            for f in fields:
                if f["name"] in SELF_ID:
                    out += [question(f"{name}.{f['name']}.{i}", t, "choice", f["isRequired"], option_texts(data, opts),
                                     native="label", page=name) for i, (t, opts) in enumerate(SELF_ID[f["name"]])]
                elif f["name"] != "dni":  # "dni": the heading over the identity questions
                    shown = values(f)
                    kind = "choice" if shown else "yesno" if f["displayName"].rstrip().endswith("?") or \
                        f["name"] == "acknowledgement" else "text"
                    out.append(question(f"{name}.{f['name']}", " ".join(f["displayName"].split()), kind, f["isRequired"],
                                        shown or (["Yes", "No"] if kind == "yesno" else []), native="label", page=name))
    # the employer's own questions; `isCorrect` / `isAutoReject` in the same data never read:
    # the answer is the applicant's truth, not the reply the employer grades
    for q in sorted((data.get("screener") or {}).get("questions") or [], key=lambda q: q.get("order", 0)):
        options = [a["title"] for a in q.get("answers") or []]
        if q["questionType"] == "multi":
            kind = "multichoice" if q.get("allowsMultipleResponses") else \
                "yesno" if sorted(options) == ["No", "Yes"] else "choice"
        else:
            kind = "longtext" if str(q.get("isParagraph")).casefold() == "true" else "text"
        title = " ".join(q["title"].split())
        out.append(question(f"screener.{q.get('order', len(out))}", title, kind, bool(q.get("isRequired")), options,
                            key_from_title(title, kind), "label", page="screener"))
    return out


def questions(url: str) -> list[dict]:
    r = httpx.get(application_url(url), timeout=30)
    # a missing or closed job: 302 to /Recruiting/Jobs/JobNotFound (2026-10-03)
    if r.status_code in (301, 302, 404) or "JobNotFound" in r.headers.get("location", ""):
        raise ValueError("posting not found - it may have closed")
    r.raise_for_status()
    data = page_data(r.text)
    if data is None:
        raise ValueError("no form on the apply page - the posting may have closed")
    return from_definition(data)


def present(page, qs: list[dict]) -> set[str]:
    return set(page.evaluate(PRESENT, [{k: q.get(k) for k in ("id", "native", "title")} for q in qs]))


def ids_on_page(page) -> list[str]:
    data = page.evaluate("() => window.pageData || null")
    if not data:
        return []
    qs = from_definition(data)
    shown = present(page, qs)
    return [q["id"] for q in qs if q["id"] in shown]


# --- typing answers ---

def by_id(page, id: str):
    return page.locator(f'[id="{id}"]').first  # ids hold dots: never #info.email


def norm(s: str) -> str:
    return " ".join((s or "").split())


def open_list(box, options) -> bool:
    """Click; a layer over the box can take the click (30 s timeout on 2 boxes of one tenant,
    2026-10-03): then the click goes to the box itself."""
    for opener in (lambda: box.click(timeout=3000), lambda: box.evaluate("e => e.click()")):
        try:
            opener()
            options.first.wait_for(timeout=3000)
            return True
        except Exception:
            continue
    return False


def put_combo(page, box, value) -> str:
    """react-widgets dropdown (div role=combobox): open, click the option that is the answer, read
    the box back. The list is `aria-owns` = `<id>__listbox` (2026-10-03, 11 per page on tenant H)."""
    want = "Yes" if value is True else "No" if value is False else str(value).strip()
    if norm(box.inner_text()).casefold() == want.casefold():
        return "ok"
    owns = box.get_attribute("aria-owns")
    options = page.locator(f'[id="{owns}"] [role=option]' if owns else "[role=listbox] [role=option]")
    if not open_list(box, options):
        box.press("Escape")
        return f"ASK the list didn't open - pick '{want}' by hand"
    texts = [norm(t) for t in options.all_inner_texts()]
    hit = next((i for i, t in enumerate(texts) if t.casefold() == want.casefold()), None)
    if hit is None:
        box.press("Escape")
        return f"ASK no option '{want}'; offered: {', '.join(t for t in texts if t)[:200]}"
    options.nth(hit).click()
    page.wait_for_timeout(200)
    got = norm(box.inner_text())
    return "ok" if got.casefold() == want.casefold() else f"FAIL shows '{got}'"


def put_radio(page, name: str, value) -> str:
    """Native radios in a role=radiogroup, named by the text beside each (no [role=radio])."""
    radios = page.locator(f'input[type=radio][name="{name}"]')
    names = radios.evaluate_all("rs => rs.map(r => ((r.closest('label') || r.parentElement).innerText || r.value)"
                                ".replace(/\\s+/g, ' ').trim())")
    want = str(value).strip()
    if want not in names:
        return f"ASK no option '{want}'; offered: {', '.join(names)[:200]}"
    radio = radios.nth(names.index(want))
    radio.evaluate("e => e.click()")
    return "ok" if radio.is_checked() else f"FAIL {want} not selected"


def shown_in(box) -> str:
    """Text of the box's .form-group: a list's chosen value shows over the input, not in it
    ("CountryUnited States" read with value '', 2026-10-03)."""
    return norm(box.locator("xpath=ancestor::div[contains(@class,'form-group')][1]").inner_text())


def put_list(page, box, value) -> str:
    """Country / State: a text box that opens a list as you type. A "Select a state" layer sits over
    the box and takes the click (click timed out 30 s, 2026-10-03): focused, never clicked."""
    want = str(value).strip()
    if box.input_value().casefold() == want.casefold():
        return "ok"
    box.focus()
    box.fill("")
    box.press_sequentially(want, delay=30)
    page.wait_for_timeout(500)
    options = page.locator("[role=option]:visible, [role=listbox] li:visible")
    texts = [norm(t) for t in options.all_inner_texts()]
    hit = next((i for i, t in enumerate(texts) if t.casefold() == want.casefold()), None)
    if hit is not None:
        options.nth(hit).click()
    else:
        box.press("Enter")
    page.wait_for_timeout(200)
    got = box.input_value()
    if got.casefold() == want.casefold() or want.casefold() in shown_in(box).casefold():
        return "ok"
    return f"ASK shows '{got}' - pick '{want}' from the list by hand"


def put_date(box, value) -> str:
    """Date box with a typing mask (MM/DD/YYYY + calendar button): a whole-value fill and slashes
    typed key by key both read back empty (2026-10-03), so digits only, the mask adds the slashes."""
    want = str(value).strip()
    box.focus()
    box.fill("")
    box.press_sequentially(dom.digits(want), delay=40)
    typed = box.input_value()
    box.press("Escape")  # the calendar it opens would sit over the boxes below
    box.press("Tab")
    got = box.input_value()
    if dom.digits(got) == dom.digits(want):
        return "ok"
    return f"ASK shows '{got}' (while typing '{typed}') - type {want} or pick it in the calendar"


def put_lookup(box, value) -> str:
    """Address Line 1 looks the address up as you type: typed, the suggestions shut, never one picked
    (a picked one would replace what the user gave)."""
    box.fill(str(value))
    box.press("Escape")
    got = box.input_value()
    return "ok" if got == str(value) else f"FAIL shows '{got}'"


def put_tags(page, box, value) -> str:
    """Skills: one tag per item, each typed then Enter (react-tagsinput, 'Type a skill and press enter')."""
    items = [i.strip() for i in (value if isinstance(value, list) else re.split(r"[,\n]", str(value))) if i.strip()]
    tags = page.locator(".react-tagsinput-tag")
    for item in items:
        if item.casefold() in (norm(t).casefold() for t in tags.all_inner_texts()):
            continue
        box.fill(item)
        box.press("Enter")
    have = [norm(t).casefold() for t in tags.all_inner_texts()]
    missing = [i for i in items if i.casefold() not in have]
    return "ok" if not missing else f"FAIL not added: {', '.join(missing)[:120]}"


def put_file(page, id: str, path: str) -> str:
    page.locator(f'input[type=file][id="{id}"]').set_input_files(path)
    try:
        page.get_by_text(Path(path).name).first.wait_for(timeout=15000)
    except Exception:
        return "ASK upload not confirmed on page - check the box"
    return "ok"


def group(page, title: str):
    """The .form-group whose own label is the question (labels sit beside the box, no `for`)."""
    said = re.compile(rf"^\s*{re.escape(title)}\s*(?:\((?:required|optional)\))?\s*$", re.I)
    return page.locator(".form-group:visible").filter(has=page.locator(":scope > label").filter(has_text=said)).first


def put_labelled(page, q: dict) -> str:
    g = group(page, q["title"])
    value = q["answer"]
    if g.locator("[role=combobox]").count():
        return put_combo(page, g.locator("[role=combobox]").first, value)
    if g.locator("input[type=radio]").count():
        name = g.locator("input[type=radio]").first.get_attribute("name")
        return put_radio(page, name, value) if name else "ASK radios without a name - pick by hand"
    box = g.locator("textarea, input[type=text], input:not([type])").first
    if not box.count():
        return "ASK box not recognised - answer it on the page"
    return dom.put_text(box, value, q["kind"], editable=False)


# --- work history + education from the resume ---

def month_year(value) -> str | None:
    """'2023-02' -> '02/2023' (the box takes MM/YYYY); a year alone has no month to give -> None."""
    m = re.fullmatch(r"(\d{4})-(\d{2})(?:-\d{2})?", str(value or "").strip())
    return f"{m[2]}/{m[1]}" if m else None


def entry(page, kind: str, field: str, i: int, button: str):
    """Box `field` of entry i, adding an entry with the page's own button when it isn't there yet."""
    box = by_id(page, f"{kind}.{field}.{i}")
    if not box.count():
        page.get_by_role("button", name=button, exact=True).first.click()
        box.wait_for(timeout=10000)
    return box


def add_work(page, roles: list[dict], tailored: dict) -> list[str]:
    from apply.systems import ukg  # same tailored-lines rule as UKG's description box
    report = []
    for i, role in enumerate(roles):
        name, left = f"{role['title']}, {role['company']}", []
        dom.put_text(entry(page, WORK, "companyName", i, "Add Work History"), role["company"], "text", False)
        dom.put_text(by_id(page, f"{WORK}.position.{i}"), role["title"], "text", False)
        dom.put_text(by_id(page, f"{WORK}.responsibilities.{i}"), ukg.description(role, tailored), "longtext", False)
        for side, value in (("start", role.get("start")), ("end", role.get("end"))):
            if str(value or "").casefold() in ("", "present"):
                continue
            if when := month_year(value):
                dom.put_text(by_id(page, f"txt-{WORK}-{side}Date-{i}"), when, "text", False)
            else:
                left.append(f"{side} month (the resume gives the year only)")
        if str(role.get("end") or "present").casefold() == "present":
            tick = by_id(page, f"{WORK}.currentlyWorkingHere.{i}")
            if tick.count() and not tick.is_checked():
                tick.evaluate("e => e.click()")
        # reason for leaving, supervisor, employer phone + address: the user's own, never from the resume
        report.append(f"{name}: ok" + (f" - left: {'; '.join(left)}" if left else ""))
    return report


def add_schools(page, schools: list[dict]) -> list[str]:
    report = []
    for i, school in enumerate(schools):
        dom.put_text(entry(page, SCHOOL, "name", i, "Add Education"), school["institution"], "text", False)
        if school.get("field"):
            dom.put_text(by_id(page, f"{SCHOOL}.areaOfStudy.{i}"), school["field"], "text", False)
        # school type, graduated, degree, graduation date: asked on the page (a date there is sensitive)
        report.append(f"{school['institution']}: ok")
    return report


def put_history(page, q: dict, resume_file: str | None) -> str:
    from apply.systems import ukg
    master, tailored = ukg.resume_facts(resume_file)
    if q["native"] == "school":
        report = add_schools(page, master.get("education") or [])
    else:
        roles, note = form_roles(master, tailored, asks_complete_history(page.locator("body").inner_text()))
        if note and note.startswith("ASK"):
            return note
        report = add_work(page, roles, tailored) + ([note] if note else [])
    return "ok - " + "; ".join(report or ["nothing on the resume to add"]) + \
        " (the rest of each entry is the user's on the page)"


def fill(page, q: dict, resume_file: str | None) -> str:
    kind, value, native = q["kind"], q["answer"], q["native"]
    if kind == "file" and q.get("key") not in ("resume", "cover_letter"):
        return f"ASK not the resume box ({q['title']}) - the user uploads their own file there"
    if native == "references":
        return "ASK other people's details - the user adds each reference on the page"
    if q["id"] not in present(page, [q]):
        return f"{LATER} on another step of the form"
    if native in ("work", "school"):
        return put_history(page, q, resume_file) if dom.yes(value) else "skipped - user said no"
    if kind == "file":
        if q.get("key") == "cover_letter" and not resume_file:
            return "ASK cover letter box - no letter made for this job (letter prepare), or the user uploads their own"
        return put_file(page, q["id"], resume_file) if value is True and resume_file else "skipped - upload not approved"
    if native == "label":
        return put_labelled(page, q)
    if native == "radio":
        return put_radio(page, q["id"], value)
    box = by_id(page, q["id"])
    box.scroll_into_view_if_needed()
    if native == "combo":
        return put_combo(page, box, "Yes" if kind == "yesno" and dom.yes(value) else "No" if kind == "yesno" else value)
    if native == "list":
        return put_list(page, box, value)
    if native == "lookup":
        return put_lookup(box, value)
    if native == "tags":
        return put_tags(page, box, value)
    if kind == "date":
        return put_date(box, value)
    return dom.put_text(box, value, kind, editable=False)
