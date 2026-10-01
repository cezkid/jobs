"""UKG Pro Recruiting (recruiting*.ultipro.com): questions read off the signed-in form, answers typed
into its widgets, work history / education / skills / links added from the resume.

No public form definition: the form shows only after the user signs in (their own account, never
typed by us), so `questions` reads it from Job Finder's Chrome. Measured facts and why each rule
exists: app/docs/apply/ukg.md.
"""
import json
import re
from pathlib import Path

from apply import browser
from apply.questions import question

NAME = "UKG"
POSTING_URL = re.compile(
    r"https?://(recruiting\d*\.ultipro\.com)/([^/?#]+)/JobBoard/([0-9a-f-]{36})/Opportunity(?:Detail|Apply)\?"
    r"(?:[^#]*&)?opportunityId=([0-9a-f-]{36})", re.I)
READY = "[data-automation=first-name-textbox]"
SIGN_IN = "input[type=password]"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
# UKG screening question type -> shared kind; Yes/No choices become yesno below
KIND = {"MultipleChoice": "choice", "Text": "longtext", "Numeric": "number"}
# contact boxes the form shows under the account's name; name + email come from the account itself
FIELDS = {"Country": ("choice", None), "AddressLine1": ("text", "street"), "City": ("text", "city"),
          "State": ("choice", "state"), "PostalCode": ("text", "zip"), "Phone": ("phone", "phone"),
          "ApplicantSource": ("choice", None)}
DECLINE = "I decline to say"
PROFILE = "resume-sections"
DEGREES = {"b": "Bachelor", "a": "Associate", "m": "Master", "d": "Doctor", "p": "Doctor"}

# everything the form asks, read in the page (runs in Chrome)
SNAPSHOT = """() => {
  const vis = e => !!e && e.getBoundingClientRect().width > 0;
  const text = e => (e ? e.innerText || e.textContent || '' : '').replace(/\\s+/g, ' ').trim();
  const labelFor = e => text(document.querySelector(`label[for="${e.id}"]`)) || e.getAttribute('aria-label') || '';
  const req = e => e.required || e.getAttribute('aria-required') === 'true';
  const out = {signin: !!document.querySelector('input[type=password]'), fields: [], questions: [], eeo: []};
  for (const id of %s) {
    const e = document.getElementById(id);
    if (!e) continue;
    out.fields.push({id, label: labelFor(e), required: req(e),
      options: e.tagName === 'SELECT' ? [...e.options].slice(1).map(o => o.text.trim()) : []});
  }
  out.upload = !!document.querySelector('[data-automation=upload-file-input]');
  out.referral = !!document.querySelector('[data-automation=no-employee-referral-radio]');
  out.startDate = !!document.querySelector('[data-automation=available-start-date-datepicker]');
  const q = document.querySelector('[data-automation=application-knockout-question]');
  if (q && window.ko)
    for (const x of ko.toJS(ko.contextFor(q).$parent.opportunity).ApplicationQuestions || [])
      out.questions.push({Id: x.Id, Question: x.Question, ResponseType: x.ResponseType,
        Choices: ((x.ResponseConfiguration || {}).Choices || []).map(c => c.Text)});
  for (const e of document.querySelectorAll('select[data-automation^=country-questions]')) {
    const group = e.closest('.form-group');
    out.eeo.push({id: e.id, label: labelFor(e), required: req(e) && vis(e),
      options: [...e.options].slice(1).map(o => o.text.trim()),
      decline: !!(group && group.querySelector('input[type=checkbox]'))});
  }
  return out;
}""" % json.dumps(list(FIELDS))


def matches(url: str) -> bool:
    return bool(POSTING_URL.match(url.strip()))


def parse_url(url: str) -> tuple[str, str, str, str]:
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not a UKG (recruiting.ultipro.com) posting link: {url}")
    return m.groups()


def application_url(url: str) -> str:
    host, tenant, board, opportunity = parse_url(url)
    return f"https://{host}/{tenant}/JobBoard/{board}/OpportunityApply?opportunityId={opportunity}"


def from_snapshot(snap: dict) -> list[dict]:
    out = []
    for f in snap["fields"]:
        kind, key = FIELDS[f["id"]]
        out.append(question(f["id"], f["label"] or f["id"], kind, f["required"], f["options"], key, "field"))
    if snap.get("upload"):
        out.append(question("resume", "Resume", "file", False, key="resume", native="document"))
    if snap.get("referral"):
        out.append(question("employeereferral", "Were you referred by a current employee?", "yesno", True,
                            ["Yes", "No"], native="referral"))
    if snap.get("startDate"):
        out.append(question("start-date", "When can you start? (MM/DD/YYYY)", "date", True, native="start-date"))
    for q in snap["questions"]:
        kind = KIND.get(q["ResponseType"], "text")
        if kind == "choice" and sorted(q["Choices"]) == ["No", "Yes"]:
            kind = "yesno"
        out.append(question(q["Id"], " ".join(q["Question"].split()), kind, True, q["Choices"], native=q["ResponseType"]))
    for e in snap["eeo"]:
        out.append(question(e["id"], e["label"] or e["id"], "choice", e["required"],
                            e["options"] + ([DECLINE] if e["decline"] else []), native="self-id"))
    # work history, education, skills, links: separate boxes the resume fills, each saved to the
    # user's account on the site as it is added - so asked, never assumed
    out.append(question(PROFILE, "Add work history, education, skills and links from the resume "
                        "(UKG saves each to the user's account on the site as it is added)",
                        "yesno", False, ["Yes", "No"], native="profile"))
    return out


def questions(url: str) -> list[dict]:
    with browser.page_at(application_url(url)) as page:
        page.locator(f"{READY}, {SIGN_IN}").first.wait_for(timeout=30000)
        snap = page.evaluate(SNAPSHOT)
    if snap["signin"]:
        raise SystemExit("UKG shows the form only after sign-in: Job Finder's Chrome is open on the sign-in page - "
                         "the user signs in or creates an account there (never typed for them), then run prepare again")
    return from_snapshot(snap)


def ids_on_page(page) -> list[str]:
    return [q["id"] for q in from_snapshot(page.evaluate(SNAPSHOT))]


# --- typing answers ---

def settle(box) -> None:
    """Knockout reads text boxes on change, not input (Links refused 'must not be empty' without it)."""
    box.dispatch_event("change")
    box.blur()


def put_text(box, value) -> str:
    box.fill(str(value))
    settle(box)
    got = box.input_value()
    same = re.sub(r"\D", "", got) == re.sub(r"\D", "", str(value)) if box.get_attribute("type") == "tel" else got == str(value)
    return "ok" if same else f"FAIL shows '{got}'"


def put_select(page, select, value: str) -> str:
    for _ in range(50):  # State reloads its list a moment after Country changes
        if value in select.evaluate("e => [...e.options].map(o => o.text.trim())"):
            select.select_option(label=value)
            got = select.evaluate("e => e.options[e.selectedIndex].text.trim()")
            return "ok" if got == value else f"FAIL shows '{got}'"
        page.wait_for_timeout(200)
    return f"ASK no option '{value}'"


def put_self_id(page, q: dict) -> str:
    select = page.locator(f"#{q['id']}")
    # before the decline box too: Race (list + box) shows only after "Not Hispanic/Latino", and
    # ticking its hidden box waited 30s then failed (2026-09-30)
    if not select.is_visible():
        return "skipped - not shown for the other answers"
    if q["answer"] == DECLINE:
        box = page.locator(f".form-group:has(#{q['id']}) input[type=checkbox]").first
        box.check()
        return "ok" if box.is_checked() else "FAIL decline box not ticked"
    return put_select(page, select, q["answer"])


def put_radio(radios, value: str) -> str:
    for i in range(radios.count()):
        r = radios.nth(i)
        if r.is_visible() and r.evaluate("e => (e.closest('label') || e.parentElement).innerText.trim()") == value:
            r.check()
            return "ok" if r.is_checked() else f"FAIL {value} not selected"
    return f"ASK no option '{value}'"


def put_date(page, value: str) -> str:
    """Start date = three boxes (Month, Day, Year) in UKG's own date picker."""
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", value.strip()) or re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", value.strip())
    if not m:
        return f"FAIL date '{value}' not MM/DD/YYYY"
    month, day, year = m.groups() if "/" in value else (m.group(2), m.group(3), m.group(1))
    parts = page.locator("[data-automation=available-start-date-datepicker] input")
    for i, part in enumerate((month.zfill(2), day.zfill(2), year)):
        box = parts.nth(i)
        box.click()
        box.press("ControlOrMeta+a")
        box.press_sequentially(part, delay=60)
    parts.nth(2).press("Tab")
    got = [parts.nth(i).input_value() for i in range(3)]
    return "ok" if got == [month.zfill(2), day.zfill(2), year] else f"FAIL shows {'/'.join(got)}"


def put_question(page, q: dict) -> str:
    index = page.evaluate("""id => [...document.querySelectorAll('[data-automation=application-knockout-question]')]
        .findIndex(e => ko.dataFor(e).Id === id)""", q["id"])
    if index < 0:
        return "FAIL question not on page"
    box = page.locator("[data-automation=application-knockout-question]").nth(index)
    box.scroll_into_view_if_needed()
    if q["native"] == "MultipleChoice":
        return put_radio(box.locator("[data-automation=multiple-choice-response]"), q["answer"])
    field = box.locator("[data-automation=text-response]:visible, [data-automation=numeric-response]:visible").first
    return put_text(field, q["answer"])


def put_file(page, path: str) -> str:
    page.locator("[data-automation=upload-file-input]").first.set_input_files(path)
    docs = page.locator("[data-automation=application-documents]")
    try:
        docs.get_by_text(Path(path).name).first.wait_for(timeout=20000)
    except Exception:
        return "ASK upload not confirmed on page - check the Documents box"
    return "ok"


# --- work history, education, skills, links from the resume ---

def resume_facts(resume_file: str | None) -> tuple[dict, dict]:
    """Master resume + this job's tailored lines (tailored copy's bullets go on the site, same as the PDF)."""
    import cfg
    from resume import schema, tailor
    master = schema.load(cfg.resume_path(cfg.load(), "master"))
    tailored = {}
    if resume_file:
        saved = Path(resume_file).parent / tailor.JOB_DATA / "tailored.json"
        if saved.exists():
            tailored = json.loads(saved.read_text(encoding="utf-8"))
    return master, tailored


def month_year(value: str | None) -> tuple[str, str] | None:
    """'2023-02' -> ('Feb', '2023'); '2016' -> ('', '2016'); present/blank -> None (UKG shows 'Current')."""
    if not value or str(value).casefold() == "present":
        return None
    year, _, month = str(value).partition("-")
    return (MONTHS[int(month) - 1] if month else "", year)


def description(role: dict, tailored: dict) -> str:
    lines = next((e["bullets"] for e in tailored.get("entries", []) if e["id"] == role.get("id")), None)
    texts = [b["text"] for b in lines] if lines is not None else [b["claim"] for b in role.get("bullets", [])]
    return "\n".join("- " + t for t in texts)[:2000]  # UKG box: 2000 characters


def degree_word(degree: str) -> str | None:
    """Resume 'BA' / 'B.S.' / 'Bachelor of Arts' -> the word UKG's degree list is searched by."""
    d = degree.strip().casefold()
    if d.startswith("ph"):
        return "Doctor"
    return DEGREES.get(d[:1])


def major_option(field: str, options: list[str]) -> str | None:
    """Exact major, or the longest option the field starts with ('Art Education in School and
    Community' -> 'Art Education'); none -> left blank, the field goes in the description."""
    f = field.casefold().strip()
    fits = [o for o in options if f == o.casefold() or f.startswith(o.casefold() + " ")]
    return max(fits, key=len) if fits else None


def panel(page, name: str):
    return page.locator(f"[data-automation={name}]").first


def open_entry(p, probe: str) -> None:
    if not p.locator(f"[data-automation={probe}]:visible").count():
        p.locator("[data-automation=primary-action-button]:visible").first.click()
        p.locator(f"[data-automation={probe}]:visible").first.wait_for(timeout=10000)


def save_entry(page, p) -> str:
    """Saved = the editor closes. A refused entry keeps it open with the reason under the box (hint
    lines like 'Leave this blank if you currently work here' share the same class, so never read alone)."""
    p.locator("[data-automation=save-button]:visible").first.click()
    for _ in range(40):
        page.wait_for_timeout(250)
        if not p.locator("[data-automation=save-button]:visible").count():
            return "ok"
    errors = p.evaluate("""p => [...p.querySelectorAll('.has-error .help-block')]
        .filter(e => e.getBoundingClientRect().width > 0 && e.innerText.trim()).map(e => e.innerText.trim())""")
    p.locator("[data-automation=cancel-button]:visible").first.click()
    return "FAIL " + ("; ".join(errors)[:160] or "entry not saved")


def pick_typeahead(page, box, typed: str, starts: str) -> str | None:
    """Pick the site's own suggestion starting with `starts`. The first search after an entry opens
    comes back empty while the list loads (measured: degree 'Bachelor' -> nothing, same again -> 'Bachelors')."""
    options = page.locator(".tt-suggestion:visible, [role=option]:visible")
    for _ in range(2):
        box.fill("")
        box.press_sequentially(typed, delay=40)
        for _ in range(12):
            page.wait_for_timeout(250)
            texts = [t.strip() for t in options.all_inner_texts()]
            if texts:
                break
        for i, t in enumerate(texts):
            if t.casefold().startswith(starts.casefold()):
                options.nth(i).click()
                page.wait_for_timeout(300)
                return box.input_value()
    return None


def add_work(page, roles: list[dict], tailored: dict) -> list[str]:
    p, report = panel(page, "work-experience-panel"), []
    for role in roles:
        name = f"{role['title']}, {role['company']}"
        if name in p.inner_text():
            report.append(f"{name}: already there")
            continue
        open_entry(p, "job-title-textbox")
        box = lambda a: p.locator(f"[data-automation={a}]:visible").first
        for a, v in (("job-title-textbox", role["title"]), ("company-textbox", role["company"]),
                     ("location-textbox", role.get("location") or "")):
            put_text(box(a), v)
        for side, value in (("from", role.get("start")), ("to", role.get("end"))):
            if when := month_year(value):
                if when[0]:
                    box(f"{side}-month-dropdown").select_option(label=when[0])
                put_text(box(f"{side}-year-textbox"), when[1])
        put_text(box("description-textarea"), description(role, tailored))
        report.append(f"{name}: {save_entry(page, p)}")
    return report


def add_education(page, schools: list[dict]) -> list[str]:
    p, report = panel(page, "education-panel"), []
    for school in schools:
        name = school["institution"]
        if name.casefold() in p.inner_text().casefold():
            report.append(f"{name}: already there")
            continue
        open_entry(p, "school-textbox")
        box = lambda a: p.locator(f"[data-automation={a}]:visible").first
        # school: the site's own spelling when it lists the school ("<school> (NJ)"), else as typed
        if not pick_typeahead(page, box("school-textbox"), name, name):
            put_text(box("school-textbox"), name)
        word = degree_word(school.get("degree") or "")
        if not word or not pick_typeahead(page, box("degree-textbox"), word, word):
            p.locator("[data-automation=cancel-button]:visible").first.click()
            report.append(f"{name}: ASK degree '{school.get('degree')}' not in the site's list - pick it by hand")
            continue
        field = school.get("field") or ""
        major = major_option(field, box("major-dropdown").evaluate("e => [...e.options].slice(1).map(o => o.text.trim())"))
        if major:
            box("major-dropdown").select_option(label=major)
        if when := month_year(school.get("end")):
            if when[0]:
                box("to-month-dropdown").select_option(label=when[0])
            put_text(box("to-year-textbox"), when[1])
        if field:
            put_text(box("description-textarea"), field)
        report.append(f"{name}: {save_entry(page, p)}" + (f" (major: {major})" if major and major != field else ""))
    return report


def add_skills(page, items: list[str]) -> list[str]:
    p = panel(page, "skills-panel")
    have = {t.strip().casefold() for t in p.inner_text().splitlines()}
    todo = [i for i in items if i.casefold() not in have]
    if not todo:
        return ["skills: already there"]
    open_entry(p, "item-typeahead")
    box = p.locator("[data-automation=item-typeahead]:visible").first
    for item in todo:
        # never Escape here: it closes the whole Skills editor (measured)
        box.fill("")
        box.press_sequentially(item, delay=20)
        p.locator("[data-automation=item-add-button]:visible").first.click()
        page.wait_for_timeout(300)
    return [f"skills ({len(todo)} added, level left 'Not Specified'): {save_entry(page, p)}"]


def link_title(url: str) -> str:
    host = url.casefold()
    return "LinkedIn" if "linkedin." in host else "GitHub" if "github." in host else "Website"


def add_links(page, links: list[str]) -> list[str]:
    p = panel(page, "links-panel")
    urls = [u if u.startswith("http") else "https://" + u for u in links]
    bare = lambda u: u.split("://", 1)[-1].removeprefix("www.").rstrip("/").casefold()
    have = {bare(h) for h in p.evaluate("p => [...p.querySelectorAll('a[href]')].map(a => a.href)")}
    todo = [u for u in urls if bare(u) not in have]
    if not todo:
        return ["links: already there"]
    open_entry(p, "url-textbox")
    for u in todo:
        rows = p.locator("[data-automation=url-textbox]:visible")
        if rows.nth(rows.count() - 1).input_value():
            p.locator("[data-automation=primary-action-button]:visible").first.click()
            page.wait_for_timeout(500)
        put_text(p.locator("[data-automation=title-textbox]:visible").last, link_title(u))
        put_text(p.locator("[data-automation=url-textbox]:visible").last, u)
    return [f"links ({len(todo)}): {save_entry(page, p)}"]


def put_profile(page, resume_file: str | None) -> str:
    master, tailored = resume_facts(resume_file)
    skills = tailored.get("skills") or master.get("skills") or []
    report = (add_work(page, master.get("roles", []), tailored) + add_education(page, master.get("education", []))
              + add_skills(page, [i for g in skills for i in g["items"]])
              + add_links(page, (master.get("contact") or {}).get("links") or []))
    bad = [r for r in report if " FAIL" in r or " ASK" in r]
    return ("ASK " if bad else "ok - ") + "; ".join(bad or report)


def fill(page, q: dict, resume_file: str | None) -> str:
    kind, value, native = q["kind"], q["answer"], q["native"]
    if native == "profile":
        return put_profile(page, resume_file) if str(value).casefold() in ("yes", "true") else "skipped - user said no"
    if kind == "file":
        return put_file(page, resume_file) if value is True and resume_file else "skipped - upload not approved"
    if native == "referral":
        word = "yes" if str(value).casefold() in ("yes", "true") else "no"
        radio = page.locator(f"[data-automation={word}-employee-referral-radio]")
        radio.check()
        return "ok" if radio.is_checked() else "FAIL not selected"
    if native == "start-date":
        return put_date(page, str(value))
    if native == "self-id":
        return put_self_id(page, q)
    if native == "field":
        box = page.locator(f"#{q['id']}")
        box.scroll_into_view_if_needed()
        return put_select(page, box, value) if kind == "choice" else put_text(box, value)
    return put_question(page, q)
