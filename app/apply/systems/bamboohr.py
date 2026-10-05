"""BambooHR (<co>.bamboohr.com/careers/<id>): questions from the posting's own form definition, answers typed into its page.

Measured facts and why each rule exists: app/docs/apply/bamboohr.md.
"""
import re
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from apply.questions import key_from_title, question, signs

NAME = "BambooHR"
# freehire adds ?utm_source=freehire.me (10 of 10 newest US links, 2026-10-03)
POSTING_URL = re.compile(r"https?://([\w-]+)\.bamboohr\.com/careers/(\d+)(?=[/?#]|$)", re.I)
SOURCES = ("bamboohr",)
EXAMPLES = ("https://acme.bamboohr.com/careers/101",
            "https://acme.bamboohr.com/careers/101?utm_source=freehire.me")
# GET /careers/<id>/detail = every box the form shows, plain JSON, no key (12 of 12 tenants, 2026-10-03)
QUESTIONS_OVER_HTTP = True
READY = "#firstName"
# a chosen file POSTs to the employer's BambooHR at once, before Submit (bamboohr.md)
FILE_ON_CHOICE = True
# the form opens on the same URL only after this button (4 of 4)
APPLY = "Apply for This Job"
# definition key -> (shared kind, shared key)
SYSTEM = {"firstName": ("text", "first_name"), "lastName": ("text", "last_name"), "email": ("email", "email"),
          "phone": ("phone", "phone"), "streetAddress": ("text", "street"), "city": ("text", "city"),
          "state": ("text", "state"), "zip": ("text", "zip"), "countryId": ("choice", None),
          "resumeFileId": ("file", "resume"), "coverLetterFileId": ("file", "cover_letter"),
          "dateAvailable": ("date", None), "desiredPay": ("text", None), "linkedinUrl": ("url", "linkedin"),
          "websiteUrl": ("url", "website"), "educationLevelId": ("choice", None),
          "educationInstitutionName": ("text", None), "referredBy": ("text", None), "references": ("longtext", None),
          "genderId": ("choice", None), "ethnicityId": ("choice", None), "veteranStatusId": ("choice", None)}
# address boxes + Country carry a `name` of <key>.value; their ids change between loads (1 of 4).
# State + Country are Fabric lists (fab-Select), State by full name ("New York", 4 tries 2026-10-03)
BY_NAME = {"streetAddress", "city", "state", "zip", "countryId"}
# Date Available: no name, a changing id - its label is the only hook; takes mm/dd/yyyy typed (4 tenants)
BY_LABEL = {"dateAvailable"}
# the page shows Veteran Status as 3 radios, not required, whatever the definition lists (4 of 4)
VETERAN = "veteranStatusId"
VETERAN_OPTIONS = ["Decline to Answer", "Not a Veteran", "Veteran"]
# its radios are named by React per page (":r5:") - the only radios not named customQuestionAnswers.*
VETERAN_RADIOS = 'input[type=radio][name^=":"]'
CUSTOM = {"yes_no": "yesno", "short": "text", "long": "longtext", "multi": "choice", "file": "file"}
# file boxes have no name or label: found under their heading, else by place - cover letter, resume,
# then file questions (tenant B)
FILES = ("coverLetterFileId", "resumeFileId")
FILE_PLACE = re.compile(r"bamboohr:file (\d+) of (\d+)$")
OPEN = "Open"


def matches(url: str) -> bool:
    return bool(POSTING_URL.match(url.strip()))


def parse_url(url: str) -> tuple[str, str]:
    """(tenant, posting id)."""
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not a BambooHR posting link: {url}")
    return m.group(1), m.group(2)


def application_url(url: str) -> str:
    co, id = parse_url(url)
    return f"https://{co}.bamboohr.com/careers/{id}"


def on_tab(url: str, tab_url: str) -> bool:
    # posting ids are short numbers: /careers/12 must not match /careers/123
    app, tab = urlsplit(application_url(url)), urlsplit(tab_url)
    return app.hostname == tab.hostname and tab.path.rstrip("/") == app.path


def custom_id(c: dict) -> str:
    """The page's name for an employer question: customQuestionAnswers.<type>_<id> (4 of 4)."""
    return f"customQuestionAnswers.{c['type']}_{c['id']}"


def options_of(f: dict) -> list[str]:
    # system fields carry {id, text}; a `multi` question {id, option} (tenant E)
    return [str(o.get("text") or o.get("option") or "").strip() for o in f.get("options") or []]


def yes_no(options: list[str]) -> bool:
    return sorted(o.casefold() for o in options) == ["no", "yes"]


def from_detail(data: dict) -> list[dict]:
    result = data.get("result") or {}
    if (result.get("jobOpening") or {}).get("jobOpeningStatus", OPEN) != OPEN:
        raise ValueError("the posting is no longer open - it may have closed")
    out = []
    for name, f in (result.get("formFields") or {}).items():
        if name == "customQuestions":
            for c in f or []:
                title = " ".join(str(c.get("question") or "").split())
                kind = CUSTOM.get(c.get("type"), "text")
                options = options_of(c)
                if kind == "choice" and yes_no(options):
                    kind = "yesno"
                if kind == "yesno":  # two radios Yes / No, no options in the definition (42 of 42)
                    options = options or ["Yes", "No"]
                out.append(question(custom_id(c), title, kind, bool(c.get("isRequired")), options,
                                    None if kind == "file" else key_from_title(title, kind), f"bamboohr:{c.get('type')}"))
            continue
        if not isinstance(f, dict):  # turned off by the employer: [] (genderId 7 of 12, disabilityId 12 of 12)
            continue
        title, options = f.get("label") or name, options_of(f)
        kind, key = SYSTEM.get(name, ("choice" if options else "text", None))
        required = bool(f.get("isRequired"))
        if name == "state":
            options = []  # a text box on the page (4 of 4); the definition's 60 codes are not offered there
        if name == VETERAN:
            options, required = VETERAN_OPTIONS, False
        out.append(question(name, title, kind, required, options, key or key_from_title(title, kind), f"bamboohr:{name}"))
    # file boxes have no hook but their place: cover letter, resume, then file questions (tenant B)
    files = [q for id in FILES for q in out if q["id"] == id] + [q for q in out if q["kind"] == "file" and q["id"] not in FILES]
    for n, q in enumerate(files, 1):
        q["native"] = f"bamboohr:file {n} of {len(files)}"
    return out


def questions(url: str) -> list[dict]:
    r = httpx.get(application_url(url) + "/detail", timeout=30, follow_redirects=True)
    # unknown posting id: 404 {"type": "not_found"} (2026-10-03)
    if r.status_code == 404:
        raise ValueError("posting not found - it may have closed")
    r.raise_for_status()
    return from_detail(r.json())


def ids_on_page(page) -> list[str]:
    """Named boxes as question ids: system ones by id or <key>.value, employer ones by name. Files,
    Date Available + Veteran Status have no stable hook; the honeypot + MUI's autosize copy are no questions."""
    return page.eval_on_selector_all(
        "form input, form select, form textarea",
        """es => [...new Set(es.map(e => e.name && e.name.startsWith('customQuestionAnswers.') ? e.name
              : e.name && e.name.endsWith('.value') ? e.name.slice(0, -6)
              : e.id && !e.id.startsWith('Fabric') && !e.id.startsWith('fab-') && e.id !== 'nickname_hpcsaf'
                && e.type !== 'radio' && e.type !== 'file' ? e.id : null).filter(Boolean))]""")


def recover(page, url: str) -> None:
    """The posting page shows no form until "Apply for This Job" is clicked."""
    if page.locator(READY).count():
        return
    button = page.get_by_role("button", name=APPLY)
    if not button.count():
        button = page.get_by_text(APPLY, exact=True)
    button.first.click()


def locate(page, q: dict):
    id = q["id"]
    if id.startswith("customQuestionAnswers."):
        return page.locator(f'[name="{id}"]').first
    if id in BY_NAME:
        return page.locator(f'[name="{id}.value"]').first
    if id in BY_LABEL:
        return page.get_by_label(q["title"]).first
    return page.locator(f'[id="{id}"]').first


def digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def put_text(field, value, kind: str) -> str:
    v = str(value)
    field.fill(v)
    if kind == "date":  # a picker may open on focus: Escape shuts it, the typed date stays
        field.press("Escape")
    field.blur()
    got = field.input_value()
    return "ok" if (digits(got) == digits(v) if kind == "phone" else got == v) else f"FAIL shows '{got}'"


def norm(s: str) -> str:
    return " ".join(str(s).split()).casefold()


def radio_labels(page, selector: str) -> list[str]:
    return page.eval_on_selector_all(selector, """es => es.map(e => ((e.labels && e.labels[0]) || e.closest('label') || {}).innerText
                                                     || e.getAttribute('aria-label') || e.value || '')""")


def put_radio(page, selector: str, value) -> str:
    """Tick the radio whose label is the answer; read the tick back."""
    labels = [" ".join(t.split()) for t in radio_labels(page, selector)]
    hit = next((i for i, t in enumerate(labels) if norm(t) == norm(value)), None)
    if hit is None:
        return f"ASK no option '{value}'; offered: {', '.join(labels)}"
    radio = page.locator(selector).nth(hit)
    radio.check(force=True)  # MUI hides the native radio under its own circle
    return "ok" if radio.is_checked() else f"FAIL '{value}' not ticked"


def toggle_of(field):
    """A select is a hidden native one (no options, 4 of 4) under Fabric's own button + menu."""
    return field.locator("xpath=ancestor::div[contains(@class,'fab-Select')][1]//button[@aria-haspopup]").first


def shows(toggle) -> str:
    # the button shows the choice ("United States"), or a placeholder "-Select-" when none
    return " ".join(toggle.locator(".fab-SelectToggle__content").all_inner_texts()).strip()


def put_select(page, field, value) -> str:
    """Open the menu, click the item whose text is the answer, read the button back."""
    toggle = toggle_of(field)
    if not toggle.count():
        return "FAIL no menu button by this list"
    if norm(shows(toggle)) == norm(value):
        return "ok"
    toggle.click()
    items = page.locator(f'[id="{toggle.get_attribute("data-menu-id")}"] [role=menuitem]')
    try:
        items.first.wait_for(timeout=5000)
    except Exception:
        return "FAIL the list didn't open"
    texts = [" ".join(t.split()) for t in items.all_inner_texts()]
    hit = next((i for i, t in enumerate(texts) if norm(t) == norm(value)), None)
    if hit is None:
        toggle.press("Escape")
        return f"ASK no option '{value}'; offered: {', '.join(texts[:8])}"
    items.nth(hit).scroll_into_view_if_needed()
    items.nth(hit).click()
    got = shows(toggle)
    return "ok" if norm(got) == norm(value) else f"FAIL shows '{got}'"


def file_box(page, q: dict):
    """The upload box under the question's own heading ("Resume*" over the Choose File button, 2
    tenants); else its place among the page's upload boxes (they carry no name or label)."""
    title = q["title"].replace('"', "")
    under = page.locator(f"""xpath=//p[normalize-space(translate(., '*', ''))="{title}"]/following-sibling::*//input[@type='file']""")
    if under.count() == 1:
        return under.first, None
    boxes = page.locator("form input[type=file]")
    n, of = (int(x) for x in FILE_PLACE.match(q["native"]).groups())
    if boxes.count() != of:
        return None, f"ASK {boxes.count()} upload boxes on the page, {of} expected - check which is the resume"
    return boxes.nth(n - 1), None


def put_file(page, q: dict, path: str) -> str:
    box, why = file_box(page, q)
    if box is None:
        return why
    # choosing the file sends it at once (POST /ajax/files/attachTemporary.php, 2 tenants); the
    # box then lists the file by name - read that back, not the input (React empties it)
    box.set_input_files(path)
    upload = box.locator("xpath=ancestor::*[@data-fabric-component='FileUpload'][1]")
    try:
        upload.get_by_text(Path(path).name).first.wait_for(timeout=20000)
    except Exception:
        return "ASK upload not confirmed on page - check the box"
    return "ok"


def fill(page, q: dict, resume_file: str | None) -> str:
    if signs(q["title"]):
        return "ASK yours to do on the page - agreeing, consenting or signing"
    kind, value = q["kind"], q["answer"]
    if kind == "file":
        if q.get("key") not in ("resume", "cover_letter"):
            return f"ASK not the resume box ({q['title']}) - the user uploads their own file there"
        if q.get("key") == "cover_letter" and not resume_file:
            return "ASK cover letter box - no letter made for this job (letter prepare), or the user uploads their own"
        return put_file(page, q, resume_file) if value is True and resume_file else "skipped - upload not approved"
    if q["id"] == VETERAN:
        return put_radio(page, VETERAN_RADIOS, value)
    if kind == "yesno":
        value = "Yes" if str(value).casefold() in ("yes", "true") else "No"
    if q.get("native") in ("bamboohr:yes_no", "bamboohr:multi") and page.locator(f'input[type=radio][name="{q["id"]}"]').count():
        return put_radio(page, f'input[type=radio][name="{q["id"]}"]', value)
    field = locate(page, q)
    if not field.count():
        return "FAIL question not on page"
    field.scroll_into_view_if_needed()
    if field.evaluate("e => e.tagName") == "SELECT":
        return put_select(page, field, value)
    return put_text(field, value, kind)
