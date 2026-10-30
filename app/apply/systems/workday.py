"""Workday careers sites (<company>.wd<N>.myworkdayjobs.com/<site>/job/...): the application filled step by
step in Job Finder's own Chrome, the user's tab, never a Submit of ours (Save and Continue only with the
user's continue_on_apply: true, on a step with nothing left for them - form.go_on).

No public form definition: the steps show after Apply, a start choice (Autofill with Resume / Apply
Manually / Use My Last Application) and the user's own sign-in. Each step is read off the page with the
same filler the Claude Chrome extension runs (app/apply/workday.js, every field found by its visible label),
then answered: My Information, Application Questions, Voluntary Disclosures field by field with real mouse
and keys; My Experience (work history, education, skills, profile links) by workday.js's own run(), its
clicks on list options made real here (synthetic ones were ignored on some options, tenant H). The user
clicks Save and Continue on each step, then prepare + fill again - or fill does, on to the next step,
when the user said yes to continue_on_apply. Facts and why each rule exists:
app/docs/apply/workday.md; the extension route stays the fallback (job-apply skill, Steps).
"""
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from apply import browser, dom, profile
from apply.questions import LATER, asks_complete_history, form_roles, key_from_title, question
from resume import schema

NAME = "Workday"
# <company>.wd<N>.myworkdayjobs.com/[<lang>/]<site>/job/[<location>/]<title>_<requisition>[/apply...]; the
# same sites under wd<N>.myworkdaysite.com/[<lang>/]recruiting/<company>/<site>/job/...
POSTING_URL = re.compile(
    r"https?://((?:[\w-]+\.wd\d+\.myworkdayjobs\.com)|(?:wd\d+\.myworkdaysite\.com))"
    r"(/(?:[a-z]{2}-[A-Z]{2}/)?(?:recruiting/[\w-]+/)?[\w-]+)/job/(?:[^/?#]+/)*?([^/?#]+_[\w-]+)(?=[/?#]|$)", re.I)
SOURCES = ("workday",)
EXAMPLES = ("https://acme.wd5.myworkdayjobs.com/en-US/External/job/Remote-USA/Data-Analyst_R-12345",
            "https://acme.wd12.myworkdayjobs.com/Careers/job/California---San-Francisco/Software-Engineer_JR100200/apply/applyManually",
            "https://wd3.myworkdaysite.com/recruiting/acme/External/job/Austin-TX/Analyst_R1000")
PER_PAGE = True
# the resume goes to the employer's Workday site as soon as it is chosen (tenant G: still in the box after
# signing out and in, 2026-10-14) - before Submit
FILE_ON_CHOICE = True
STEP = '[data-automation-id="progressBarActiveStep"]'
APPLY = '[data-automation-id="adventureButton"]'
READY = f"{STEP}, {APPLY}"
# the step's footer button: Continue (autofill step), Save and Continue, Submit on Review (tenant H, 2026-10-22);
# form.go_on presses it only on a Continue label, with continue_on_apply
NEXT = '[data-automation-id="pageFooterNextButton"]'
# the start choices after Apply (tenant G 2026-10-14, tenant H 2026-10-22)
STARTS = ["Autofill with Resume", "Apply Manually", "Use My Last Application"]
START, EXPERIENCE, RESUME, AUTOFILL_RESUME = "workday-start", "workday-experience", "workday-resume", "workday-autofill-resume"
SIGN_IN = re.compile(r"create account|sign in", re.I)
REVIEW = re.compile(r"^review$", re.I)
# label words -> the shared key its answer comes from (My Information, tenant G + H)
KEYS = [(re.compile(r"^address line 1$", re.I), "street"), (re.compile(r"^city$", re.I), "city"),
        (re.compile(r"^state$", re.I), "state"), (re.compile(r"^(postal code|zip)", re.I), "zip"),
        (re.compile(r"^phone number$", re.I), "phone"), (re.compile(r"^email", re.I), "email")]
LEGAL = {"first name": "legal_first", "middle name": "legal_middle", "last name": "legal_last"}
# widget (workday.js kind) -> shared kind
KIND = {"text": "text", "textarea": "longtext", "menu": "choice", "select": "choice", "search-pick": "choice",
        "radio": "choice", "checkboxes": "multichoice", "checkbox": "yesno", "date": "date", "tel": "phone",
        "email": "email", "url": "url", "number": "number"}
PLACEHOLDER = re.compile(r"^select one$", re.I)
# a two-level search list's answer: "<category> > <option>"
LEVEL = " > "
OPTION = '[data-automation-id="promptOption"]'
# the start choices show a moment after Apply (a pop-up over the posting)
START_WAIT_MS = 10000
# the whole My Experience run: about 4 s a skill when the window is in front (tenant H, 45 skills ~3 min)
RUN_LIMIT_S = 600

# read every option of an open search list: it draws only what is in view (tenant H, How Did You Hear).
# A leaf carries a tick box: inside the option on tenant H; on its promptLeafNode beside the option on
# another tenant, where categories have none (tenant P's How Did You Hear, 2026-10-30: read as all
# categories, so no option at all and another employer's saved pick filled)
LIST_ALL = """() => new Promise(async (done) => {
  const shown = () => [...document.querySelectorAll('[data-automation-id="promptOption"]')]
    .filter((o) => o.getClientRects().length && !o.closest('[data-automation-id="selectedItem"]'));
  let pane = shown()[0];
  while (pane && pane.scrollHeight <= pane.clientHeight + 2) pane = pane.parentElement;
  const seen = new Map();
  if (pane) pane.scrollTop = 0;
  for (let i = 0; i < 60; i++) {
    for (const o of shown()) seen.set(o.textContent.trim(), !!(o.closest('[data-automation-id="promptLeafNode"]') || o).querySelector('input'));
    if (!pane || pane.scrollTop + pane.clientHeight >= pane.scrollHeight - 2) break;
    pane.scrollTop += pane.clientHeight * 0.8;
    await new Promise((r) => setTimeout(r, 250));
  }
  done([...seen].map(([text, leaf]) => ({ text, leaf })));
})"""
# a search list drawn open: an option outside the picked pills - a pill's own option shows on the step all
# along (tenant P's Phone Country Code, 2026-10-30: waiting on any shown option read the list before it drew)
LIST_OPEN = """() => [...document.querySelectorAll('[data-automation-id="promptOption"]')]
  .some((o) => o.getClientRects().length && !o.closest('[data-automation-id="selectedItem"]'))"""
# scroll an open search list until the option with these words shows -> true when it does
SCROLL_TO = """(want) => new Promise(async (done) => {
  const shown = () => [...document.querySelectorAll('[data-automation-id="promptOption"]')]
    .filter((o) => o.getClientRects().length && !o.closest('[data-automation-id="selectedItem"]'));
  let pane = shown()[0];
  while (pane && pane.scrollHeight <= pane.clientHeight + 2) pane = pane.parentElement;
  if (pane) pane.scrollTop = 0;
  for (let i = 0; i < 60; i++) {
    const hit = shown().find((o) => o.textContent.trim() === want);
    if (hit) { hit.scrollIntoView({ block: 'center' }); return done(true); }
    if (!pane || pane.scrollTop + pane.clientHeight >= pane.scrollHeight - 2) break;
    pane.scrollTop += pane.clientHeight * 0.8;
    await new Promise((r) => setTimeout(r, 250));
  }
  done(false);
})"""


def parse_url(url: str) -> tuple[str, str, str]:
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not a Workday (myworkdayjobs.com) posting link: {url}")
    return m.groups()


def matches(url: str) -> bool:
    return bool(POSTING_URL.match(url.strip()))


def application_url(url: str) -> str:
    """The posting page: its Apply starts the application (the start choice, then the user's sign-in)."""
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not a Workday (myworkdayjobs.com) posting link: {url}")
    return url.strip()[:m.end()]


# --- the page ---

def inject(page) -> None:
    """workday.js on the page once (kept across steps: Workday changes steps without a new page)."""
    if not page.evaluate("() => !!(window.__jf && window.__jf.fields)"):
        page.evaluate(profile.FILLER.read_text(encoding="utf-8") + "\n0")


def step(page) -> str:
    """The step the tab shows ("My Information"), '' on the posting page."""
    raw = page.evaluate(f"() => document.querySelector('{STEP}')?.textContent || ''")
    return re.sub(r"^\s*(current )?step \d+ of \d+\s*", "", " ".join(raw.split()), flags=re.I)


def page_errors(page) -> list[str]:
    """What the step says is wrong after Save and Continue ("The field Field of Study is required and must have
    a value.", tenant H 2026-10-22) - workday.js errors()."""
    inject(page)
    return page.evaluate("() => window.__jf.errors()") or []


def signing_in(page) -> bool:
    return bool(SIGN_IN.search(step(page))) or page.locator("input[type=password]:visible").count() > 0


def gone(page, url: str) -> str | None:
    """Workday's own closed posting page ("The page you are looking for doesn't exist.", no Apply - workday.md
    #Closed posting), told apart on the posting page only: a step of the application is never closed."""
    try:
        page.locator(READY + ', [data-automation-id="errorContainer"]').first.wait_for(timeout=10000)
    except Exception:
        pass
    if step(page):
        return None
    inject(page)
    if page.evaluate("() => window.__jf.closed(5000)"):
        return "the posting says it's closed (\"The page you are looking for doesn't exist.\")"
    return None


def key_for(f: dict) -> str | None:
    label = f["label"].strip()
    if re.search(r"legal name", f.get("section") or "", re.I) and label.casefold() in LEGAL:
        return LEGAL[label.casefold()]
    for pattern, key in KEYS:
        if pattern.search(label):
            return key
    return key_from_title(label, "text") if f["kind"] == "text" else None


def wanted(f: dict) -> bool:
    """A field the user answers here: shown, not filled by the page already unless the resume or search
    settings answer it (names, address, phone - autofill's guess replaced), never a preferred-name tick
    (job-apply #Names: only when the resume name is one they chose) or a file box (its own question)."""
    if f["kind"] in ("file", "other", "button", "submit") or not f["label"]:
        return False
    if f["kind"] == "checkbox" and re.search(r"preferred name", f["label"], re.I):
        return False
    return not f["filled"] or key_for(f) is not None


def shown_fields(page) -> list[dict]:
    inject(page)
    return [f for f in json.loads(page.evaluate("() => window.__jf.fields()")) if wanted(f)]


def has_resume_box(page) -> bool:
    inject(page)
    return page.evaluate("() => window.__jf.resumeInput()") == "tagged"


def box(page, id: str):
    return page.locator(f'[data-jf-id="{id}"]').first


def menu_options(page, f: dict) -> list[str]:
    """A menu's options exist only while it is open: opened (a real click), read, closed with Escape."""
    btn = box(page, f["id"]).locator("button").first
    try:
        btn.click()
        opts = page.locator('[role="listbox"] [role="option"]:visible')
        opts.first.wait_for(timeout=4000)
        return [t.strip() for t in opts.all_inner_texts() if t.strip() and not PLACEHOLDER.match(t.strip())]
    except Exception:
        return []
    finally:
        page.keyboard.press("Escape")


def list_options(page, f: dict) -> list[str]:
    """A search list's options, a category's ones as "<category> > <option>" (tenant H's How Did You Hear:
    Current or Former Employee / External Career Site Sources / Referral, each a list of its own; typing did
    not filter it, 2026-10-22). Back to the top: Escape, then open again (unmeasured: the list's own back arrow)."""
    field = box(page, f["id"]).locator("input").first
    out = []
    try:
        field.click()
        page.wait_for_function(LIST_OPEN, timeout=4000)
        top = page.evaluate(LIST_ALL)
        for o in top:
            if o["leaf"]:
                out.append(o["text"])
                continue
            page.locator(f"{OPTION}:visible", has_text=o["text"]).first.click()
            page.wait_for_timeout(600)
            out += [f"{o['text']}{LEVEL}{x['text']}" for x in page.evaluate(LIST_ALL) if x["leaf"] and x["text"] != o["text"]]
            page.keyboard.press("Escape")
            field.click()
            page.wait_for_timeout(400)
    except Exception:
        pass
    finally:
        page.keyboard.press("Escape")
    return out


def as_question(page, f: dict, on: str, options: bool) -> dict:
    kind, key = KIND.get(f["kind"], "text"), key_for(f)
    opts = f["options"]
    if options and f["kind"] == "menu":
        opts = menu_options(page, f)
    elif options and f["kind"] == "search-pick":
        opts = list_options(page, f)
    if kind == "choice" and sorted(o.casefold() for o in opts) == ["no", "yes"]:
        kind = "yesno"
    if key == "phone":
        kind = "phone"
    elif key == "email":
        kind = "email"
    title = f["label"] if not key or not key.startswith("legal_") else f"Legal name - {f['label']}"
    return question(f["id"], title, kind, f["required"], opts, key, native=f["kind"], page=on)


def read(page) -> list[dict]:
    """The step the user's tab is on. Before the steps (posting page: the start choice; the sign-in) and
    the Review step, nothing else is the program's to fill."""
    ready(page).wait_for(timeout=30000)
    inject(page)
    on = step(page)
    if not on:
        if page.locator(f"{APPLY}:visible").count() or (shown := start_options(page)):
            return [question(START, "How to start the application (Workday's own choice after Apply; the sign-in "
                             "comes next and is the user's)", "choice", True, STARTS if page.locator(f"{APPLY}:visible").count()
                             else shown, native="start", page="Start")]
        raise SystemExit("Workday shows neither the posting's Apply nor an application step - open the posting in "
                         "Job Finder's Chrome, then run prepare again")
    if signing_in(page):
        raise SystemExit("Workday asks the user to sign in or create an account: Job Finder's Chrome is open on it - "
                         f"{dom.sign_in_email(page)}the user types the password and signs in or creates the account "
                         "there (a password is never typed for them), then run prepare again")
    if REVIEW.match(on):
        print("  the applicant's own step: check every step on this page, then click Submit yourself")
        return []
    resume = has_resume_box(page)
    if re.search(r"autofill", on, re.I):
        return [question(AUTOFILL_RESUME, "Resume for Workday's Autofill with Resume (it reads the file to fill the "
                         "next steps)", "file", True, key="resume", native="file", page=on)] if resume else []
    if re.search(r"my experience", on, re.I):
        return [question(EXPERIENCE, "Work history, education, skills and profile links from the tailored resume "
                         "(Workday keeps them once the user clicks Save and Continue)", "yesno", False, ["Yes", "No"],
                         native="experience", page=on)] + \
               ([question(RESUME, "Resume/CV", "file", True, key="resume", native="file", page=on)] if resume else [])
    return [as_question(page, f, on, options=True) for f in shown_fields(page)]


def questions(url: str) -> list[dict]:
    with browser.page_at(application_url(url), match=lambda tab: on_tab(url, tab)) as page:
        return read(page)


def on_tab(url: str, tab_url: str) -> bool:
    """This application's tab: same site, the posting's own <title>_<requisition> part in its address (kept
    through every step, tenant H: .../<title>_<req>/apply/autofillWithResume)."""
    try:
        host, _, slug = parse_url(url)
    except ValueError:
        return False
    return urlsplit(tab_url).hostname == host.casefold() and slug in tab_url


def ids_on_page(page) -> list[str]:
    inject(page)
    on = step(page)
    if not on:
        return [START] if page.locator(f"{APPLY}:visible").count() or start_options(page) else []
    if signing_in(page) or REVIEW.match(on):
        return []
    resume = has_resume_box(page)
    if re.search(r"autofill", on, re.I):
        return [AUTOFILL_RESUME] if resume else []
    if re.search(r"my experience", on, re.I):
        return [EXPERIENCE] + ([RESUME] if resume else [])
    return [f["id"] for f in shown_fields(page)]


# --- typing answers ---

def start_options(page) -> list[str]:
    """The start choices shown (the page after Apply, .../apply): a tenant offers only some - a Workday
    tenant (2026-10-23) had Apply Manually + Use My Last Application, no Autofill with Resume."""
    return [c for c in STARTS if page.get_by_text(c, exact=True).locator("visible=true").count()]


def ready(page):
    """A step, the posting's Apply, or the start choices: whichever shows first."""
    return page.locator(READY).or_(page.get_by_text(re.compile(rf"^({'|'.join(STARTS)})$"))).first


def start(page, choice: str) -> str:
    """Apply, then the start choice. Apply clicked but nothing came (a Workday tenant, 2026-10-23: its Apply
    link didn't answer the click) -> its link opened. The choice not offered -> Apply Manually, else
    Autofill with Resume: the steps after it are filled the same either way, named to the user."""
    shown = start_options(page)
    if not shown:
        apply = page.locator(f"{APPLY}:visible").first
        link = apply.get_attribute("href") or ""
        apply.click()
        shown = wait_start(page, START_WAIT_MS // 2)
        if not shown and link and not link.startswith("#"):
            page.goto(urljoin(page.url, link))
            shown = wait_start(page, START_WAIT_MS // 2)
    if not shown:
        page.keyboard.press("Escape")
        return f"ASK no '{choice}' after Apply - the user picks how to start on the page"
    pick = choice if choice in shown else next((c for c in ("Apply Manually", "Autofill with Resume") if c in shown), None)
    if pick is None:
        return f"ASK no '{choice}' after Apply (only {', '.join(shown)}) - the user picks how to start on the page"
    if pick != choice:
        print(f"  NOTE this site has no '{choice}': started with '{pick}' - name it to the user")
    page.get_by_text(pick, exact=True).locator("visible=true").first.click()
    return "ok"


def wait_start(page, ms: int) -> list[str]:
    for _ in range(max(1, ms // 250)):
        if shown := start_options(page):
            return shown
        page.wait_for_timeout(250)
    return []


def upload(page, path: str) -> str:
    """The file chosen in the step's Resume/CV box; ok once its name shows there (workday.js uploaded())."""
    name = Path(path).name
    if not has_resume_box(page):
        return "ASK no Resume/CV box on this step - upload it by hand"
    shown = page.evaluate("(name) => { const i = document.querySelector('[data-jf-file=resume]');"
                          " let b = i; for (let n = 0; b && n < 6; n++) b = b.parentElement;"
                          " return !!b && b.textContent.includes(name); }", name)
    if shown:
        return "ok"  # the autofill step's file, kept in My Experience's box (tenant G)
    page.set_input_files("[data-jf-file=resume]", path)
    said = page.evaluate("(name) => window.__jf.uploaded(name)", name)
    if said == "ok":
        return "ok"
    if said == "not confirmed":
        return "ASK upload not confirmed on page - check the Resume/CV box"
    return f"FAIL the page says '{said}' - choose the file again on the page"


def resume_facts(resume_file: str | None) -> tuple[dict, dict | None]:
    import cfg
    from resume import tailor
    master = schema.load(cfg.resume_path(cfg.load(), "master"))
    tailored = None
    if resume_file and (saved := Path(resume_file).parent / tailor.JOB_DATA / "tailored.json").exists():
        tailored = json.loads(saved.read_text(encoding="utf-8"))
    return master, tailored


def drive(page, limit_s: float = RUN_LIMIT_S) -> dict:
    """workday.js's run() under way on the page: each click it asks for made with the real mouse, until done."""
    deadline = time.monotonic() + limit_s
    while time.monotonic() < deadline:
        if want := page.evaluate("() => window.__jf.takeClick()"):
            w = json.loads(want)
            page.mouse.click(w["x"], w["y"])
            page.evaluate("(n) => window.__jf.clicked(n)", w["n"])
            continue
        status = json.loads(page.evaluate("() => window.__jf.status()"))
        if status["done"]:
            return status
        page.wait_for_timeout(100)
    return {"done": False, "problems": [f"FAIL still filling after {int(limit_s)} s - check the page"], "ok": 0}


def experience(page, resume_file: str | None) -> str:
    master, tailored = resume_facts(resume_file)
    roles, note = form_roles(master, tailored, asks_complete_history(page.locator("body").inner_text()))
    if note and note.startswith("ASK"):
        return note
    data = profile.answers(master, tailored, roles)
    page.evaluate("(data) => { window.__jf.data = data; window.__jf.R.on = true; window.__jf.run(data); }", data)
    try:
        status = drive(page)
        dates = type_dates(page)
    finally:
        page.evaluate("() => { window.__jf.R.on = false; }")
    problems = status["problems"] + dates + ([note] if note else [])
    done = f"{status['ok']} filled, {len(data['work'])} jobs, {len(data['education'])} schools"
    return f"ASK {done}; " + "; ".join(problems) if problems else f"ok - {done}"


def type_dates(page) -> list[str]:
    """Every From / To the run set, typed again with real keys (MMYYYY into the month box; the year box takes
    the rest): tenant G kept only typed dates, a Workday tenant (2026-10-23) showed none of the set ones
    and Save said "Invalid Date: /2021". A date that still doesn't show -> FAIL, filled by hand."""
    out = []
    for t in json.loads(page.evaluate("() => window.__jf.dateTargets()")):
        if t.get("missing"):
            continue
        spot = json.loads(page.evaluate("(i) => window.__jf.spot(i)", t["i"]) or "null")
        if not spot:
            continue
        page.mouse.click(spot["x"], spot["y"])
        page.keyboard.type(t["keys"], delay=40)
        page.wait_for_timeout(150)
    page.keyboard.press("Tab")
    for t in json.loads(page.evaluate("() => window.__jf.dateTargets()")):
        shown = page.evaluate("(i) => window.__jf.dateShown(i)", t["i"])
        if not t.get("missing") and shown != t["keys"]:
            out.append(f"FAIL {t['area']} > {t['name']}: shows '{shown}' - type it by hand")
    return out


def put_text(page, b, value: str) -> str:
    field = b.locator("input:not([type=hidden]), textarea").first
    if field.get_attribute("type") == "number":  # takes digits only: "$95,000" typed as 95000
        value = re.sub(r"[^\d.]", "", str(value))
    field.fill(str(value))
    field.blur()  # Workday keeps a typed value only once focus leaves the box (workday.md #Widgets)
    got = field.input_value()
    # a phone, or pay typed as "$95,000" into a number box that keeps 95000 (a Workday tenant, 2026-10-26)
    same = re.sub(r"\D", "", got) == re.sub(r"\D", "", str(value)) if got and re.fullmatch(r"[\d\s()+.,$-]+", str(value)) else got == str(value)
    return "ok" if same else f"FAIL shows '{got[:40]}'"


def put_menu(page, b, value: str) -> str:
    btn = b.locator("button").first
    btn.click()
    option = page.locator('[role="listbox"] [role="option"]:visible').filter(
        has_text=re.compile(rf"^\s*{re.escape(value)}\s*$"))
    try:
        option.first.wait_for(timeout=4000)
    except Exception:
        page.keyboard.press("Escape")
        return f"ASK no option '{value}'"
    option.first.click()
    page.wait_for_timeout(300)
    got = " ".join(btn.inner_text().split())
    return "ok" if got == value else f"FAIL shows '{got}'"


def put_list(page, b, value: str) -> str:
    """A search list, two levels when the answer names a category (list_options)."""
    field = b.locator("input").first
    *category, leaf = value.split(LEVEL, 1)
    picked = lambda: any(p.strip() == leaf for p in b.locator('[data-automation-id="selectedItem"]').all_inner_texts())
    # already picked: opening the list again showed the picked leaf over its category and the category
    # click timed out under it (a Workday tenant's How Did You Hear, 2026-10-23)
    if picked():
        return "ok"
    field.click()
    try:
        page.wait_for_function(LIST_OPEN, timeout=4000)
        if category:
            page.locator(f"{OPTION}:visible", has_text=category[0]).first.click()
            page.wait_for_timeout(600)
        if not page.evaluate(SCROLL_TO, leaf):
            close_list(page)
            return f"ASK no option '{value}'"
        page.locator(f"{OPTION}:visible").filter(has_text=re.compile(rf"^\s*{re.escape(leaf)}\s*$")).first.click()
    except Exception as e:
        close_list(page)
        return f"FAIL {type(e).__name__}"
    page.wait_for_timeout(400)
    return "ok" if picked() else f"FAIL '{leaf}' not picked"


def close_list(page) -> None:
    """Shut an open search list. Inside a category Escape left it open over the boxes below (tenant H's
    How Did You Hear, 2026-10-22: every later click on the step timed out under it); a click on the step's
    heading shut it."""
    page.keyboard.press("Escape")
    if page.locator(f"{OPTION}:visible").count():
        page.locator("h2:visible").first.click()


def put_choice(b, value: str) -> str:
    target = b.get_by_label(value, exact=True).first
    target.check()
    return "ok" if target.is_checked() else f"FAIL {value} not selected"


def put_date(page, b, value: str) -> str:
    """Typed with real keys into the first date box: tenant G kept only typed dates (workday.md #Widgets).
    Unmeasured through this route."""
    v = value.strip()
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", v) or re.fullmatch(r"(\d{4})-(\d{2})(?:-(\d{2}))?", v)
    if not m:
        return f"FAIL date '{value}' not MM/DD/YYYY"
    parts = [m[1].zfill(2), m[2].zfill(2), m[3]] if "/" in v else [m[2], *([m[3]] if m[3] else []), m[1]]
    # the date's boxes are spin buttons drawn outside the viewport, under the shown digits: a click on the
    # box timed out (a Workday tenant's Self Identify date, 2026-10-26) - focused, then a real click on
    # the digits shown over it took the typed keys
    field = b.locator("input").first
    field.evaluate("e => { e.scrollIntoView({block: 'center'}); e.focus(); }")
    r = field.evaluate("e => { const r = e.parentElement.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }")
    page.mouse.click(*r)
    page.keyboard.type("".join(parts), delay=60)
    page.keyboard.press("Tab")
    got = b.locator("input").evaluate_all("es => es.map(e => e.getAttribute('aria-valuetext') || e.value || '')")
    shown = [int(g) for g in got if g.isdigit()]
    return "ok" if shown == [int(x) for x in parts] else f"FAIL date shows '{'/'.join(got)}' - type it by hand"


def fill(page, q: dict, resume_file: str | None) -> str:
    inject(page)
    value, native = q["answer"], q["native"]
    if native in ("start", "experience") and q["id"] not in ids_on_page(page):
        # an earlier step's: the start choice re-clicked Apply on every later step (a 30 s FAIL, tenant H
        # 2026-10-22), My Experience's run would type the work history again over another step
        return f"{LATER} on another step"
    if native == "start":
        return start(page, str(value))
    if native == "experience":
        return experience(page, resume_file) if str(value).casefold() in ("yes", "true") else "skipped - user said no"
    if q["kind"] == "file":
        if q["id"] not in ids_on_page(page):
            return f"{LATER} on another step"
        return upload(page, resume_file) if value is True and resume_file else "skipped - upload not approved"
    if q.get("page") and q["page"] != step(page):
        # a box of the step just passed: after Save and Continue its tagged box lingered while Workday
        # drew the next step, and the fill failed on it, detached (a Workday tenant, 2026-10-26)
        return f"{LATER} on another step"
    page.evaluate("() => window.__jf.fields()")  # tags the step's boxes again (a re-render drops them)
    b = box(page, q["id"])
    if not b.count():
        return f"{LATER} on another step"
    b.scroll_into_view_if_needed()
    if native in ("text", "textarea", "tel", "email", "url", "number"):
        return put_text(page, b, value)
    if native == "menu":
        return put_menu(page, b, str(value))
    if native == "search-pick":
        return put_list(page, b, str(value))
    if native == "select":
        b.locator("select").first.select_option(label=str(value))
        return "ok"
    if native == "radio":
        return put_choice(b, str(value))
    if native == "checkboxes":
        results = [put_choice(b, v) for v in (value if isinstance(value, list) else [value])]
        return next((r for r in results if r != "ok"), "ok")
    if native == "checkbox":
        tick = b.locator("input[type=checkbox]").first
        tick.set_checked(str(value).casefold() in ("yes", "true"))
        return "ok"
    if native == "date":
        return put_date(page, b, str(value))
    return f"ASK unknown box '{native}' - fill it by hand"
