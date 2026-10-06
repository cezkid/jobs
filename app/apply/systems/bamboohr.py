"""BambooHR (<co>.bamboohr.com/careers/<id>): questions from the posting's own form definition, answers typed into its page.

Measured facts and why each rule exists: app/docs/apply/bamboohr.md.
"""
import contextlib
import re
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from apply.questions import key_from_title, left_on_page, question, signs

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
# a file name as the block lists it
FILE_SHOWN = re.compile(r"\S\.(pdf|docx?|odt|rtf|txt)\b", re.I)
OPEN = "Open"
# the employer's own list of open postings, plain JSON `{result: [{id, ...}]}` (4 of 4 tenants, 2026-10-06)
BOARD = "https://{co}.bamboohr.com/careers/list"
# an upload box's own block: it lists each file by name, a progress bar while it goes (Fabric's FileUpload,
# BambooHR's page script 2026-10-06)
UPLOAD_BLOCK = "xpath=ancestor::*[@data-fabric-component='FileUpload'][1]"
PROGRESS = "[role=progressbar]"
# a failed upload: the file leaves the block and a banner slides down at the top of the page with
# BambooHR's own words (page script, 2026-10-06; a live failure unmeasured - try blocks the upload)
BANNER = "[data-fabric-component=Slidedown]:not([aria-hidden=true])"
UPLOAD_ERRORS = re.compile(r"Upload failed|One or more files failed to upload|Whoops, something on our side prevented[^.]*\."
                           r"|Something on our side prevented[^.]*\.|For some reason we are having trouble uploading files[^.]*\."
                           r"|Whoa, this is a big file[^.]*\.[^.]*\d+ MB\.|Unable to upload an empty file\."
                           r"|Sorry, we can.t accept the [^ ]+ (?:file )?format\.|Make sure you.re only trying to upload the file types specified\."
                           r"|Encrypted PDFs are not allowed\.|You can't upload files on a backup\."
                           r"|Uploading the file .* would cause you to exceed your plan's storage limit\."
                           r"|Request failed with status code \d+|Network Error", re.I)
IDLE_WAIT_MS, SHOWN_WAIT_MS, ERROR_WAIT_MS = 15000, 20000, 2000


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


def board_says(url: str) -> str:
    """The definition gives 404 for a taken-down posting and an unknown id alike (bamboohr.md "Closed
    posting"): the employer's own job list, read once, tells which - never a guess."""
    co, id = parse_url(url)
    r = httpx.get(BOARD.format(co=co), timeout=30, follow_redirects=True)
    if r.status_code != 200:
        return f"can't tell if the posting is open - the employer's BambooHR job list answered {r.status_code}"
    if any(str(j.get("id")) == id for j in r.json().get("result") or []):
        return "can't tell if the posting is open - it is on the employer's BambooHR job list, but its form didn't load"
    return "the posting is no longer on the employer's BambooHR job list - it may have closed"


def questions(url: str) -> list[dict]:
    r = httpx.get(application_url(url) + "/detail", timeout=30, follow_redirects=True)
    # unknown or taken down: 404 {"type": "not_found"} either way (4 links, 2026-10-06): the job list says which
    if r.status_code == 404:
        raise ValueError(board_says(url))
    r.raise_for_status()
    return from_detail(r.json())


def closed(url: str) -> str | None:
    """Why the form isn't there (form.closed, when the page shows no form): None = BambooHR still has it open."""
    try:
        r = httpx.get(application_url(url) + "/detail", timeout=30, follow_redirects=True)
        if r.status_code == 404:
            return board_says(url)
        if r.status_code != 200:
            return f"can't tell if the posting is open - BambooHR answered {r.status_code}"
        status = ((r.json().get("result") or {}).get("jobOpening") or {}).get("jobOpeningStatus", OPEN)
        return None if status == OPEN else f"BambooHR lists the posting as '{status}' - it may have closed"
    except (httpx.HTTPError, ValueError) as e:
        return f"can't tell if the posting is open - BambooHR didn't answer ({type(e).__name__})"


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


def banner_says(page) -> str:
    """BambooHR's own words on a failed upload, from the newest banner at the top of the page, or ""."""
    said = [m.group() for t in page.locator(BANNER).all_inner_texts() for m in UPLOAD_ERRORS.finditer(" ".join(t.split()))]
    return said[-1] if said else ""


def block_says(upload) -> tuple[str, bool]:
    """(the upload block's words, still sending = a progress bar in it)."""
    if not upload.count():
        return "", False
    return " ".join(" ".join(t.split()) for t in upload.all_inner_texts()), bool(upload.locator(PROGRESS).count())


def put_file(page, q: dict, path: str) -> str:
    """Page idle first (as Greenhouse, Ashby), then the file chosen - it goes to the employer's BambooHR at
    once (bamboohr.md). Ok = its name shows in the box's block, sent (no progress bar), for ERROR_WAIT_MS
    with no new error banner; BambooHR's own error words, or the file taken back off the block -> FAIL;
    nothing either way -> ASK. A banner already up before the choice is an earlier upload's, not this one's."""
    with contextlib.suppress(Exception):  # a page that keeps polling never goes idle: the read decides
        page.wait_for_load_state("networkidle", timeout=IDLE_WAIT_MS)
    box, why = file_box(page, q)
    if box is None:
        return why
    upload, before = box.locator(UPLOAD_BLOCK), banner_says(page)
    box.set_input_files(path)
    name, seen, since = Path(path).name, False, None
    deadline = time.monotonic() + SHOWN_WAIT_MS / 1000
    while time.monotonic() < deadline:
        said = banner_says(page)
        if said and said != before:
            return f"FAIL the page says '{said}' - choose the file again on the page, or check the {q['title']} box"
        words, sending = block_says(upload)
        if name in words:
            seen = True
        elif seen:  # a failed upload leaves the block (Fabric's FileUpload)
            why = f"the page says '{said}'" if said else "the page took the file back off the box"
            return f"FAIL {why} - choose the file again on the page, or check the {q['title']} box"
        if name not in words or sending:
            since = None
        elif since is None:
            since = time.monotonic()
        elif time.monotonic() - since >= ERROR_WAIT_MS / 1000:
            return "ok"
        page.wait_for_timeout(250)
    return f"ASK upload not confirmed on page - check the {q['title']} box"


def holds(page, q: dict) -> bool:
    """The answer still shows, read off the page once the form had time to keep it (form.recheck), each
    kind as bamboohr.md "Read back (2026-10)" records it: a box by its value (phone by digits), radios by
    the one ticked and its label, a Fabric list by what its button shows, a file by a name in its block,
    sent (a failed upload leaves the block). Nothing to read = False."""
    kind, value, id = q["kind"], q["answer"], q["id"]
    if kind == "file":
        box, _ = file_box(page, q)
        if box is None:
            return False
        words, sending = block_says(box.locator(UPLOAD_BLOCK))
        return bool(FILE_SHOWN.search(words)) and not sending
    pick = ("Yes" if str(value).casefold() in ("yes", "true") else "No") if kind == "yesno" else str(value).strip()
    radios = VETERAN_RADIOS if id == VETERAN else f'input[type=radio][name="{id}"]'
    if id == VETERAN or page.locator(radios).count():
        ticked = [norm(t) for t, on in zip(radio_labels(page, radios), page.locator(radios).evaluate_all("es => es.map(e => e.checked)")) if on]
        return ticked == [norm(pick)]
    field = locate(page, q)
    if not field.count():
        return False
    if field.evaluate("e => e.tagName") == "SELECT":
        toggle = toggle_of(field)
        return bool(toggle.count()) and norm(shows(toggle)) == norm(pick)
    got = field.input_value()
    if kind == "phone":  # a dialling code the box adds in front is the page's, not a changed answer
        return bool(digits(pick)) and digits(got).endswith(digits(pick))
    return got == pick


def fill(page, q: dict, resume_file: str | None) -> str:
    if signs(q["title"]):
        return left_on_page(q)
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
