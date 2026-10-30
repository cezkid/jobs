"""Workday through Job Finder's own Chrome (apply/systems/workday.py): links, the step read off the page,
answers typed with real mouse + keys, My Experience by workday.js with its option clicks made real - on
local models of the steps tenant H showed (2026-10-22). EchoJobs + Built In copies resolved to the employer's own
posting (apply/listing_copy.py)."""
import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from apply import browser, listing_copy, profile, systems
from apply.systems import workday

FIXTURES = Path(__file__).parent / "fixtures" / "workday"
HOME = "https://acme.wd5.myworkdayjobs.example/"
POSTING = "https://acme.wd12.myworkdayjobs.com/External/job/California---San-Francisco/Software-Engineer--REMOTE-_JR100200"


# --- links ---

@pytest.mark.parametrize("link", [
    POSTING, POSTING + "?utm_source=freehire.me", POSTING.replace("/External/", "/en-US/External/") + "/apply/autofillWithResume",
    "https://acme.wd1.myworkdayjobs.com/ACMEJOBS/job/Analyst-I_R0120279-1",
    "https://wd3.myworkdaysite.com/recruiting/acme/External/job/Austin-TX/Analyst_R1000"])
def test_workday_links_are_this_system(link):
    assert systems.for_url(link) is workday
    assert workday.matches(workday.application_url(link))


def test_application_url_is_the_posting_page_without_the_apply_tail():
    assert workday.application_url(POSTING + "/apply/applyManually?x=1") == POSTING


def test_the_users_tab_found_through_every_step_by_the_posting_part():
    tab = POSTING.replace("/External/", "/en-US/External/") + "/apply/autofillWithResume"
    assert workday.on_tab(POSTING, tab)
    assert not workday.on_tab(POSTING, tab.replace("_JR100200", "_JR100201"))
    assert not workday.on_tab(POSTING, tab.replace("acme.wd12", "globex.wd12"))


# --- a board's copy (EchoJobs) -> the employer's own posting ---

COPY = ("<h1>Software Engineer III - Search Team (REMOTE)</h1><p>Location: California - San Francisco</p>"
        "<p>The Search team owns ranking, indexing and the query service behind the product, its "
        "latency budget, evaluation sets and release process.</p>")


def search(rows):
    class Reply:
        def json(self):
            return {"data": rows}
    asked = []

    def get(url, params=None, timeout=None):
        asked.append(params)
        return Reply()
    return get, asked


def row(source, title, text, url):
    return {"source": source, "title": title, "description": text, "url": url}


def test_copy_resolves_to_the_employers_own_posting_by_title_and_text():
    body = COPY.split("</h1>", 1)[1]
    get, asked = search([
        row("echojobs", "Software Engineer (Remote)", COPY, "https://echojobs.io/job/acme-x"),
        row("greenhouse", "Software Engineer III - Search Team (REMOTE)", "<p>Another employer, same title.</p>",
            "https://boards.greenhouse.io/globex/jobs/1"),
        row("workday", "Software Engineer III - Search Team (REMOTE)", body, POSTING + "?utm_source=freehire.me")])
    assert listing_copy.apply_link(COPY, "https://api.example", get=get) == POSTING
    assert asked[0]["q"] == '"Software Engineer III - Search Team (REMOTE)"' and asked[0]["q_fields"] == "title"


def test_copy_without_the_same_text_elsewhere_is_not_resolved():
    get, _ = search([row("greenhouse", "Software Engineer III - Search Team (REMOTE)", "<p>Other words.</p>",
                         "https://boards.greenhouse.io/globex/jobs/1")])
    assert listing_copy.apply_link(COPY, "https://api.example", get=get) is None
    assert listing_copy.apply_link("<p>no title heading</p>", "https://api.example", get=get) is None


def test_built_in_copy_resolves_by_its_own_title_and_whole_text():
    body = COPY.split("</h1>", 1)[1]
    get, asked = search([
        row("builtin", "Software Engineer III - Search Team (REMOTE)", body, "https://builtin.com/job/x/1"),
        row("workday", "Software Engineer III - Search Team (REMOTE)", body, POSTING + "?utm_source=freehire.me")])
    assert listing_copy.apply_link(body, "https://api.example", get=get,
                                   title="Software Engineer III -  Search Team (REMOTE)") == POSTING
    assert asked[0]["q"] == '"Software Engineer III - Search Team (REMOTE)"'
    assert "builtin" in listing_copy.TITLED


def test_echojobs_links_known():
    assert listing_copy.matches("https://echojobs.io/job/acme-software-engineer-x1y2z?utm_source=freehire.me")
    assert listing_copy.matches("https://builtin.com/job/software-engineer/11934125?utm_source=freehire.me")
    assert not listing_copy.matches(POSTING)


# --- the page ---

@pytest.fixture(scope="module")
def chrome():
    pw = pytest.importorskip("playwright.sync_api")
    try:
        exe = browser.chrome()
    except SystemExit:
        pytest.skip("Chrome not installed")
    with pw.sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe, headless=True)
        yield b
        b.close()


# My Information as tenant H showed it: a two-level How Did You Hear list that draws only what is in view and
# ignores typing, a radio pair, Country already chosen, Legal Name boxes the autofill filled, address, State +
# Phone Device Type menus, phone. Menus open a shared listbox like tenant G's.
MY_INFORMATION = """<div data-automation-id="progressBarActiveStep">current step 2 of 6 My Information</div>
<div data-automation-id="formField-source"><label for="source--source">How Did You Hear About Us?*</label>
  <span>0 items selected</span><div id="pills"></div><input id="source--source"></div>
<div data-automation-id="formField-candidateIsPreviousWorker"><label>Have you previously worked for Acme?*</label>
  <input type="radio" name="w" id="w1"><label for="w1">Yes</label><input type="radio" name="w" id="w2"><label for="w2">No</label></div>
<div data-automation-id="formField-country"><label for="country--country">Country*</label><button id="country--country" class="menu" data-list="countries">United States of America</button></div>
<h3>Legal Name</h3>
<div data-automation-id="formField-legalName--firstName"><label for="name--legalName--firstName">First Name*</label><input id="name--legalName--firstName" value="Ana"></div>
<div data-automation-id="formField-legalName--lastName"><label for="name--legalName--lastName">Last Name*</label><input id="name--legalName--lastName" value="Lima"></div>
<h3>Address</h3>
<div data-automation-id="formField-addressLine1"><label for="address--addressLine1">Address Line 1*</label><input id="address--addressLine1"></div>
<div data-automation-id="formField-city"><label for="address--city">City*</label><input id="address--city"></div>
<div data-automation-id="formField-countryRegion"><label for="address--countryRegion">State*</label><button id="address--countryRegion" class="menu" data-list="states">Select One</button></div>
<div data-automation-id="formField-postalCode"><label for="address--postalCode">Postal Code*</label><input id="address--postalCode"></div>
<div data-automation-id="formField-phoneType"><label for="phoneNumber--phoneType">Phone Device Type*</label><button id="phoneNumber--phoneType" class="menu" data-list="phones">Select One</button></div>
<div data-automation-id="formField-phoneNumber"><label for="phoneNumber--phoneNumber">Phone Number*</label><input id="phoneNumber--phoneNumber"></div>
<div id="menu" role="listbox" hidden></div>
<div id="prompt" hidden style="height:120px;overflow:auto"><div id="rows"></div></div>
<script>
  const lists = { countries: ['United States of America', 'Canada'], states: ['New Jersey', 'New York'], phones: ['Landline', 'Mobile'] };
  const tree = { 'Current or Former Employee': ['I am a Returning Employee'], 'Referral': ['Employee Referral'],
    'External Career Site Sources': ['Alumni Network', 'Facebook', 'Glassdoor', 'Handshake', 'Indeed', 'Instagram',
      'Job Board', 'LinkedIn Connection Post', 'Reddit Ads', 'Search Engine (Google, Bing etc.)', 'Twitter'] };
  let open = null, level = null;
  const prompt = document.getElementById('prompt'), rowsEl = document.getElementById('rows');
  const ROW = 24;
  const draw = () => {  // only the rows in view exist, like the live list
    const items = level ? tree[level] : Object.keys(tree);
    rowsEl.style.height = `${items.length * ROW}px`; rowsEl.style.position = 'relative';
    const first = Math.floor(prompt.scrollTop / ROW), last = first + Math.ceil(120 / ROW) + 1;
    rowsEl.innerHTML = items.slice(first, last).map((t, i) => `<div data-automation-id="promptOption" style="position:absolute;top:${(first + i) * ROW}px;height:${ROW}px" data-t="${t}">${level ? '<input type="radio">' : ''}${t}</div>`).join('');
  };
  prompt.addEventListener('scroll', draw);
  document.addEventListener('click', (e) => {
    const el = e.target, menu = document.getElementById('menu');
    if (el.matches('button.menu')) { open = el; menu.innerHTML = lists[el.dataset.list].map((o) => `<div role="option">${o}</div>`).join(''); menu.hidden = false; return; }
    if (el.matches('#menu [role=option]')) { open.textContent = el.textContent; menu.hidden = true; return; }
    if (el.id === 'source--source') { level = null; prompt.scrollTop = 0; prompt.hidden = false; draw(); return; }
    const opt = el.closest('#prompt [data-automation-id=promptOption]');
    if (opt && !level) { level = opt.dataset.t; prompt.scrollTop = 0; draw(); return; }
    if (opt) { document.getElementById('pills').innerHTML = `<div data-automation-id="selectedItem">${opt.dataset.t}</div>`; prompt.hidden = true; }
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { prompt.hidden = true; document.getElementById('menu').hidden = true; level = null; } });
</script>"""

# Application Questions: menus with no formField hook, found by their label (tenant H's questionnaire), and
# the terms box at the end of Voluntary Disclosures
QUESTIONS = """<div data-automation-id="progressBarActiveStep">current step 4 of 6 Application Questions</div>
<div><label for="primaryQuestionnaire--a1">Will you now or in the future require sponsorship?*</label>
  <button id="primaryQuestionnaire--a1" class="menu" data-list="yn">Select One</button></div>
<div><label for="primaryQuestionnaire--a2">Regarding future positions, please select one of the following options*</label>
  <button id="primaryQuestionnaire--a2" class="menu" data-list="future">Select One</button></div>
<div><label for="primaryQuestionnaire--a3">What is your preferred geographic location?</label><textarea id="primaryQuestionnaire--a3"></textarea></div>
<div data-automation-id="formField-termsAndConditions"><input type="checkbox" id="termsAndConditions--acceptTermsAndAgreements">
  <label for="termsAndConditions--acceptTermsAndAgreements">Yes, I have read and consent to the terms and conditions*</label></div>
<div id="menu" role="listbox" hidden></div>
<script>
  const lists = { yn: ['Select One', 'Yes', 'No'], future: ['Select One', 'Yes, I would like to receive communications', 'No, please do not contact me'] };
  let open = null;
  document.addEventListener('click', (e) => {
    const el = e.target, menu = document.getElementById('menu');
    if (el.matches('button.menu')) { open = el; menu.innerHTML = lists[el.dataset.list].map((o) => `<div role="option">${o}</div>`).join(''); menu.hidden = false; }
    else if (el.matches('#menu [role=option]')) { open.textContent = el.textContent; menu.hidden = true; }
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') document.getElementById('menu').hidden = true; });
</script>"""


@pytest.fixture()
def page(chrome):
    context = chrome.new_context()
    context.route("**/*", lambda route: route.abort())
    pg = context.new_page()
    yield pg
    context.close()


def test_my_information_read_off_the_step(page):
    page.set_content(MY_INFORMATION)
    qs = {q["id"]: q for q in workday.read(page)}
    assert "country--country" not in qs  # chosen already, nothing of the user's answers it
    heard = qs["source--source"]
    assert heard["kind"] == "choice" and heard["page"] == "My Information"
    assert "External Career Site Sources > Job Board" in heard["options"]
    assert "External Career Site Sources > Twitter" in heard["options"]  # past the rows in view
    assert "Referral > Employee Referral" in heard["options"]
    worked = next(q for q in qs.values() if q["title"].startswith("Have you previously worked"))
    assert worked["kind"] == "yesno" and worked["options"] == ["Yes", "No"]
    assert qs["name--legalName--firstName"]["key"] == "legal_first"  # the autofill's guess replaced
    assert qs["name--legalName--lastName"]["key"] == "legal_last"
    assert [qs[i]["key"] for i in ("address--addressLine1", "address--city", "address--countryRegion",
                                   "address--postalCode", "phoneNumber--phoneNumber")] == ["street", "city", "state", "zip", "phone"]
    assert qs["address--countryRegion"]["options"] == ["New Jersey", "New York"]
    assert qs["phoneNumber--phoneType"]["options"] == ["Landline", "Mobile"]
    assert set(workday.ids_on_page(page)) == set(qs)


def test_my_information_answers_typed_and_picked(page):
    page.set_content(MY_INFORMATION)
    qs = {q["id"]: q for q in workday.read(page)}
    worked = next(i for i, q in qs.items() if q["title"].startswith("Have you previously worked"))
    answers = {"source--source": "External Career Site Sources > Job Board", worked: "No",
               "name--legalName--firstName": "Jane", "address--addressLine1": "1 Main St",
               "address--countryRegion": "New Jersey", "phoneNumber--phoneType": "Mobile",
               "phoneNumber--phoneNumber": "(555) 010-0100"}
    for id, value in answers.items():
        assert workday.fill(page, {**qs[id], "answer": value}, None) == "ok", id
    assert page.text_content("#pills") == "Job Board"
    assert page.is_checked("#w2") and not page.is_checked("#w1")
    assert page.input_value("#name--legalName--firstName") == "Jane"
    assert page.text_content("#address--countryRegion") == "New Jersey"
    assert page.text_content("#phoneNumber--phoneType") == "Mobile"


def test_a_list_answer_not_there_is_asked_never_near(page):
    page.set_content(MY_INFORMATION)
    q = next(q for q in workday.read(page) if q["id"] == "source--source")
    assert workday.fill(page, {**q, "answer": "External Career Site Sources > Other Job Board"}, None).startswith("ASK")
    assert page.text_content("#pills") == ""


def test_questions_without_a_hook_found_by_label_terms_left_for_the_user(page):
    page.set_content(QUESTIONS)
    qs = {q["title"]: q for q in workday.read(page)}
    sponsor = qs["Will you now or in the future require sponsorship?"]
    assert sponsor["id"] == "primaryQuestionnaire--a1" and sponsor["kind"] == "yesno" and sponsor["required"]
    assert qs["What is your preferred geographic location?"]["kind"] == "longtext"
    future = qs["Regarding future positions, please select one of the following options"]
    assert workday.fill(page, {**future, "answer": "No, please do not contact me"}, None) == "ok"
    assert page.text_content("#primaryQuestionnaire--a2") == "No, please do not contact me"
    terms = qs["Yes, I have read and consent to the terms and conditions"]
    from apply import questions
    drafted = questions.draft([terms], {"name": "Jane Doe"})[0]
    assert drafted["answer"] is None and questions.SIGN_ON_PAGE in drafted["source"]


def test_posting_page_asks_how_to_start_and_another_step_is_later(page, monkeypatch):
    monkeypatch.setattr(workday, "START_WAIT_MS", 500)
    page.set_content('<h2>Analyst</h2><a data-automation-id="adventureButton" href="#">Apply</a>')
    qs = workday.read(page)
    assert [q["id"] for q in qs] == [workday.START] and qs[0]["options"] == workday.STARTS
    assert workday.fill(page, {**qs[0], "answer": "Apply Manually"}, None).startswith("ASK")  # no start menu here
    page.set_content(QUESTIONS)
    assert workday.fill(page, {"id": "address--city", "kind": "text", "native": "text", "answer": "Springfield"},
                        None).startswith("LATER")


def test_sign_in_step_stops_prepare(page):
    page.set_content('<div data-automation-id="progressBarActiveStep">current step 1 of 7 Create Account/Sign In</div>'
                     '<input type="password">')
    with pytest.raises(SystemExit, match="sign in"):
        workday.read(page)


# --- My Experience: workday.js's run(), its option clicks made real (tenant H) ---

SKILLS = ["MCP", "React.js", "CSS3", "TypeScript", "JavaScript", "Node.js", "PostgreSQL", "AWS", "Jest", "Docker",
          "GitLab", "Figma"]
DATA = {"work": [], "education": [], "skills": SKILLS, "languages": [],
        "links": ["https://linkedin.com/in/someone", "https://example.com"]}


def tenant_h(chrome, real: bool):
    context = chrome.new_context()
    context.route("**/*", lambda route: route.fulfill(path=str(FIXTURES / "tenant-h.html"))
                  if urlsplit(route.request.url).path == "/tenant-h.html" else route.abort())
    pg = context.new_page()
    pg.goto(HOME + "tenant-h.html")
    pg.evaluate(profile.FILLER.read_text(encoding="utf-8") + "\n0")
    pg.evaluate("(args) => { window.__jf.R.on = args.real; window.__jf.run(args.data); }", {"real": real, "data": DATA})
    if real:
        status = workday.drive(pg, limit_s=120)
    else:
        pg.wait_for_function("window.__jf.S.done", timeout=120000)
        status = json.loads(pg.evaluate("window.__jf.status()"))
    pills = pg.evaluate("[...document.querySelectorAll('#skillPills [data-automation-id=selectedItem] [data-automation-id=promptOption]')].map(p => p.textContent.trim())")
    return context, pg, status, pills


@pytest.fixture(scope="module")
def real_clicks(chrome):
    context, pg, status, pills = tenant_h(chrome, real=True)
    yield pg, status, pills
    context.close()


@pytest.fixture(scope="module")
def synthetic_clicks(chrome):
    context, pg, status, pills = tenant_h(chrome, real=False)
    yield pg, status, pills
    context.close()


def test_skills_capped_at_what_the_form_takes_closest_first(real_clicks):
    _, status, pills = real_clicks
    assert len(pills) == 10
    assert pills[:2] == ["Model Context Protocol", "React.js"]
    assert any(p.startswith("NOTE Skills > limit") and "left out GitLab, Figma" in p for p in status["problems"])
    assert any("took off 1 the page had added" in p for p in status["problems"])


def test_acronym_takes_its_spelled_out_name_never_another_skills_bracket(real_clicks):
    _, _, pills = real_clicks
    assert "Mortgage Cadence Platform (MCP)" not in pills and "Model Context Protocol" in pills


def test_option_that_ignores_synthetic_clicks_picked_by_a_real_one(real_clicks, synthetic_clicks):
    pg, _, pills = real_clicks
    assert "React.js" in pills and pg.evaluate("window.trusted") >= 10
    _, status, pills = synthetic_clicks
    assert "React.js" not in pills  # the extension's route: said, for a real click by hand
    assert any(p.startswith('ASK Skills > React.js: "React.js" click did not register - pick it by hand') for p in status["problems"])


def test_linkedin_box_gets_the_www_link_its_check_takes(real_clicks):
    pg, _, _ = real_clicks
    assert pg.input_value("#li") == "https://www.linkedin.com/in/someone"
    assert pg.is_hidden("#liError")


def test_optional_section_headings_still_found(chrome):
    context = chrome.new_context()
    pg = context.new_page()
    pg.set_content("""<div data-automation-id="progressBarActiveStep">My Experience</div>
<section><h3>Work History (Optional)</h3><div id="entries"></div><button id="add">Add</button></section>
<script>document.getElementById('add').addEventListener('click', (e) => {
  document.getElementById('entries').insertAdjacentHTML('beforeend', '<div data-automation-id="formField-jobTitle"><label for="t">Job Title*</label><input id="t"></div>');
  e.target.textContent = 'Add Another'; });</script>""")
    pg.evaluate(profile.FILLER.read_text(encoding="utf-8") + "\n0")
    pg.evaluate("window.__jf.run({work: [{title: 'Analyst', company: '', location: '', current: false, start: '', end: '', "
                "description: ''}], education: [], skills: [], languages: []}, ['work'])")
    pg.wait_for_function("window.__jf.S.done", timeout=30000)
    assert pg.input_value("#t") == "Analyst"
    context.close()


@pytest.mark.parametrize("name, closed", [("posting-closed-b.html", True), ("posting-open-d.html", False)])
def test_closed_posting_page_told_apart_before_any_step(chrome, name, closed):
    context = chrome.new_context()
    context.route("**/*", lambda route: route.fulfill(path=str(FIXTURES / name))
                  if urlsplit(route.request.url).path == f"/{name}" else route.abort())
    pg = context.new_page()
    pg.goto(HOME + name)
    said = workday.gone(pg, POSTING)
    assert (said is not None and "closed" in said) if closed else said is None
    context.close()


# --- a Workday tenant (2026-10-23): typed-only dates, School a search list, footer over the skills results ---

def tenant_w(chrome):
    context = chrome.new_context(viewport={"width": 1000, "height": 700})
    context.route("**/*", lambda route: route.fulfill(path=str(FIXTURES / "tenant-w.html"))
                  if urlsplit(route.request.url).path == "/tenant-w.html" else route.abort())
    pg = context.new_page()
    pg.goto(HOME + "tenant-w.html")
    pg.evaluate(profile.FILLER.read_text(encoding="utf-8") + "\n0")
    data = {"work": [{"title": "Analyst", "company": "Acme", "location": "", "current": False, "start": "2021-11",
                      "end": "2022-11", "description": ""}],
            "education": [{"school": "Springfield State University", "degree": [], "field": [], "end": ""}],
            "skills": ["React.js", "Jest", "Docker"], "languages": [], "links": []}
    pg.evaluate("(data) => { window.__jf.R.on = true; window.__jf.run(data); }", data)
    status = workday.drive(pg, limit_s=120)
    return context, pg, status, workday.type_dates(pg)


@pytest.fixture(scope="module")
def tenant_w_run(chrome):
    context, pg, status, dates = tenant_w(chrome)
    yield pg, status, dates
    context.close()


def test_dates_kept_only_when_typed_get_real_keys(tenant_w_run):
    pg, _, dates = tenant_w_run
    assert dates == []
    shown = pg.evaluate("[...document.querySelectorAll('.date')].map(d => [...d.querySelectorAll('input')].map(i => i.value).join('/'))")
    assert shown == ["11/2021", "11/2022"]


def test_school_search_list_picked_never_typed(tenant_w_run):
    pg, status, _ = tenant_w_run
    assert pg.evaluate("document.querySelector('#schoolPills [data-automation-id=promptOption]').textContent.trim()") == "Springfield State University"
    assert not any("School" in p for p in status["problems"]), status["problems"]


def test_skills_at_the_page_end_picked_clear_of_the_footer(tenant_w_run):
    pg, status, _ = tenant_w_run
    pills = pg.evaluate("[...document.querySelectorAll('#skillPills [data-automation-id=promptOption]')].map(p => p.textContent.trim())")
    assert pills == ["React.js", "Jest (JavaScript Testing Framework)", "Docker (Software)"]
    assert pg.evaluate("window.footerClicks") == 0
    assert not any("did not register" in p for p in status["problems"]), status["problems"]


START_PAGE = ('<h2>Start Your Application</h2><a href="#" role="button">Apply Manually</a>'
              '<a href="#" role="button">Use My Last Application</a>')


def test_start_page_without_autofill_read_and_started_manually(page, monkeypatch, capsys):
    """The tab already on the start choices (.../apply), Autofill with Resume not offered: Apply Manually,
    named to the user - never a 30 s wait for a step or an Apply that isn't there."""
    monkeypatch.setattr(workday, "START_WAIT_MS", 500)
    page.set_content(START_PAGE)
    qs = workday.read(page)
    assert [q["id"] for q in qs] == [workday.START] and qs[0]["options"] == ["Apply Manually", "Use My Last Application"]
    page.evaluate("document.querySelectorAll('a').forEach(a => a.addEventListener('click', () => window.started = a.textContent))")
    assert workday.fill(page, {**qs[0], "answer": "Autofill with Resume"}, None) == "ok"
    assert page.evaluate("window.started") == "Apply Manually"
    assert "started with 'Apply Manually' - name it to the user" in capsys.readouterr().out


def test_apply_link_that_ignores_the_click_opened(chrome, monkeypatch):
    """A tenant's Apply did nothing when clicked (2026-10-23): its link is opened instead."""
    monkeypatch.setattr(workday, "START_WAIT_MS", 1000)
    context = chrome.new_context()
    posting = '<h2>Analyst</h2><a data-automation-id="adventureButton" href="/job/apply" onclick="return false">Apply</a>'
    context.route("**/*", lambda route: route.fulfill(content_type="text/html",
                                                      body=START_PAGE if route.request.url.endswith("/apply") else posting))
    pg = context.new_page()
    pg.goto(HOME + "job")
    assert workday.fill(pg, {"id": workday.START, "native": "start", "kind": "choice", "answer": "Apply Manually"}, None) == "ok"
    assert "/job/apply" in pg.url
    context.close()


# --- a Workday tenant, 2026-10-26: sign-in email, a pay number box, a passed step's box, the date boxes ---

SIGN_IN = ('<div data-automation-id="progressBarActiveStep">current step 1 of 7 Create Account/Sign In</div>'
           '<input data-automation-id="email" type="text" aria-label="Email Address">'
           '<input data-automation-id="password" type="password" aria-label="Password">')


def test_sign_in_step_gets_their_email_never_the_password(page, monkeypatch):
    from apply import dom
    monkeypatch.setattr(dom, "account_email", lambda: "jane@example.com")
    page.set_content(SIGN_IN)
    with pytest.raises(SystemExit, match=r"their email \(jane@example.com\) typed in, the password box left for them"):
        workday.read(page)
    assert page.input_value('[data-automation-id="email"]') == "jane@example.com"
    assert page.input_value('[data-automation-id="password"]') == ""
    monkeypatch.setattr(dom, "account_email", lambda: None)  # before setup: nothing typed, the user types it
    page.set_content(SIGN_IN)
    with pytest.raises(SystemExit) as stop:
        workday.read(page)
    assert "typed in" not in str(stop.value) and page.input_value('[data-automation-id="email"]') == ""


PAY_AND_DATE = """<div data-automation-id="progressBarActiveStep">current step 3 of 6 Application Questions</div>
<div data-automation-id="formField-pay"><label for="q--pay">Desired Annual Pay:*</label><input id="q--pay" type="number"></div>
<div data-automation-id="formField-payText"><label for="q--payText">Desired Pay (text)*</label>
  <input id="q--payText" onblur="this.value = this.value.replace(/\\D/g, '')"></div>
<div data-automation-id="formField-dateSignedOn"><label for="d--month">Date*</label>
  <div style="display:flex">%s</div></div>
<script>
  // spin buttons drawn off screen under the digits shown (the live page's Self Identify date): a click on the
  // shown digits focuses the box, typed digits fill it and move on, as Workday does
  const boxes = [...document.querySelectorAll('input[role=spinbutton]')];
  document.querySelectorAll('.seg').forEach((s, i) => s.addEventListener('click', () => boxes[i].focus()));
  boxes.forEach((b, i) => b.addEventListener('keydown', (e) => {
    if (!/^\\d$/.test(e.key)) return;
    e.preventDefault();
    const v = (b.getAttribute('aria-valuetext') || '').replace(/\\D/g, '') + e.key;
    b.setAttribute('aria-valuetext', v);
    if (v.length >= b.maxLength && boxes[i + 1]) boxes[i + 1].focus();
  }));
</script>""" % "".join(
    f'<div class="seg" style="width:24px;height:28px"><input role="spinbutton" maxlength="{n}" id="d--{part}" '
    f'data-automation-id="dateSection{part.title()}-input" aria-label="{part}" '
    f'style="position:fixed;left:-500px;top:-500px"></div>' for part, n in (("month", 2), ("day", 2), ("year", 4)))


def test_pay_typed_with_a_dollar_sign_kept_as_the_number_box_shows_it(page):
    page.set_content(PAY_AND_DATE)
    qs = {q["title"]: q for q in workday.read(page)}
    assert qs["Date"]["kind"] == "date"
    pay, text = qs["Desired Annual Pay:"], qs["Desired Pay (text)"]
    assert workday.fill(page, {**pay, "answer": "$95,000"}, None) == "ok"
    assert page.input_value("#q--pay") == "95000"
    assert workday.fill(page, {**text, "answer": "$95,000"}, None) == "ok"  # the box keeps 95000 once left
    assert page.input_value("#q--payText") == "95000"


def test_date_typed_into_spin_boxes_drawn_off_screen(page):
    page.set_content(PAY_AND_DATE)
    date = next(q for q in workday.read(page) if q["kind"] == "date")
    assert workday.fill(page, {**date, "answer": "10/26/2026"}, None) == "ok"
    assert [page.get_attribute(f"#d--{p}", "aria-valuetext") for p in ("month", "day", "year")] == ["10", "26", "2026"]


def test_a_passed_steps_box_is_later_never_filled_on_the_next_step(page):
    page.set_content(PAY_AND_DATE)
    passed = {"id": "formField-pay", "kind": "text", "native": "text", "answer": "He/Him", "page": "Voluntary Disclosures"}
    workday.inject(page)
    assert workday.fill(page, passed, None).startswith("LATER")
    assert page.input_value("#q--pay") == ""
