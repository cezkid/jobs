"""Trial: fill a Greenhouse, Ashby or Lever form in a tab of the Job Finder window (apply/window.py, `apply-form fill
--in-window`), off by default. The Page/Locator adapter runs in real headless Chrome over raw CDP - the
same protocol the window's debugger proxy speaks - on local Greenhouse- and Ashby-like pages + Lever's saved
form; Ashby's and Lever's fillers run through Playwright too, same read-back asked of both. The window's side (open the holding
page, attach, detach) is a fake extension answering as extension.js does."""
import contextlib
import json
import os
import re
import subprocess
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from conftest import REAL_HOME

import cfg
import launch
from apply import browser, dom, form, questions, window
from apply.cdp import CDP
from apply.systems import ashby, greenhouse, jazzhr, lever, workable

FORM = Path(__file__).parent / "fixtures" / "dom" / "greenhouse-form.html"
ASHBY_FORM = FORM.with_name("ashby-form.html")
ASHBY_PATH = "/acme/45bdb7e5-14a8-494f-8fcb-30e42f0be67a/application"
ASHBY_EDUCATION_PATH = "/acme/45bdb7e5-14a8-494f-8fcb-30e42f0be67a/education"
LEVER_FORM = FORM.parent.parent / "lever" / "tenant-a.html"
LEVER_PATH = "/acme/1b2c3d4e-5f60-4718-9a0b-1c2d3e4f5a6b/apply"
# what Lever's own scripts do that its saved form lacks: the place search offers towns 300 ms after
# typing stops (a pick = the town in the box + Lever's own record; typing again drops the record), a
# chosen resume shows its verdict 500 ms later; the verdicts + search notes hidden until then
LEVER_BEHAVES = """<style>.resume-upload-failure, .resume-upload-working, .resume-upload-success, .resume-upload-oversize,
  .dropdown-no-results, .dropdown-loading-results {display: none}</style>
<script>
const box = document.getElementById("location-input"), pick = document.getElementById("selected-location"),
  results = document.querySelector(".dropdown-results"), file = document.getElementById("resume-upload-input");
const PLACES = ["Austin, Texas, United States", "Austin, Minnesota, United States", "Boston, Massachusetts, United States"];
let typing;
box.addEventListener("input", () => {
  pick.value = ""; results.replaceChildren(); clearTimeout(typing);
  typing = setTimeout(() => { const t = box.value.trim().toLowerCase();
    for (const p of PLACES.filter((p) => t && p.toLowerCase().startsWith(t))) {
      const d = document.createElement("div"); d.textContent = p; results.append(d); } }, 300); });
results.addEventListener("click", (ev) => { const d = ev.target.closest(".dropdown-results > div");
  if (d) { box.value = d.textContent; pick.value = JSON.stringify({name: d.textContent}); results.replaceChildren(); } });
file.addEventListener("change", () => setTimeout(() => {
  document.querySelector(".visible-resume-upload .filename").textContent = file.files[0] ? file.files[0].name : "";
  document.querySelector(".resume-upload-success").style.display = "inline"; }, 500));
</script>"""
JAZZHR_FORM = FORM.parent.parent / "jazzhr" / "tenant-b.html"
JAZZHR_PATH = "/apply/AbCdE00001/Test-Role"
# what JazzHR's own page does that its saved form lacks: class none hides, "Attach resume" swaps the
# paste / attach choice for the file box (its href="#" link)
JAZZHR_BEHAVES = """<style>.none {display: none}</style>
<script>
document.getElementById("resumator-choose-upload").addEventListener("click", (e) => { e.preventDefault();
  document.getElementById("resumator-resume-options").classList.add("none");
  document.getElementById("resumator-resume-upload-wrapper").classList.remove("none"); });
</script>"""
WORKABLE_FORM = FORM.with_name("workable-form.html")
WORKABLE_PATH = "/acme/j/1A2B3C4D5E/apply/"
# what the live page has that the hand-built form lacks: Workable's cookie dialog over the whole form on load
# (data-ui=cookie-consent, role=dialog, aria-modal, grey overlay - 2 tenants, plan-k8n.7); its buttons do
# nothing here (the filler never clicks them)
WORKABLE_BEHAVES = """<div data-ui="cookie-consent" role="dialog" aria-modal="true"
  style="position: fixed; inset: 0; z-index: 10; background: rgba(0, 0, 0, .4)">
  <div style="position: absolute; left: 0; right: 0; bottom: 0; background: #fff; padding: 12px">
    This website uses cookies to enhance your experience.
    <button type="button">Accept all</button><button type="button">Decline all</button>
    <button type="button">Cookies settings</button></div></div>"""
BAMBOOHR_FORM = FORM.with_name("bamboohr-form.html")
BAMBOOHR_PATH = "/careers/101"
# a same-site frame, another site's frame (the same server by its other name), open + closed shadow roots
FRAMES_PATH = "/dom/frames-shadow.html"
HOLDING = re.compile(r"^http://127\.0\.0\.1:\d{1,5}/jf-[0-9a-f]{32}$")


@pytest.fixture(scope="module")
def tab(tmp_path_factory):
    """One headless Chrome tab -> its CDP address, as the window's debugger proxy hands one over."""
    try:
        exe = browser.chrome()
    except SystemExit:
        pytest.skip("Chrome not installed")
    profile = tmp_path_factory.mktemp("chrome")
    # started before conftest's per-test guard: under the made-up home Chrome's first page load hangs
    proc = subprocess.Popen([exe, "--headless=new", "--remote-debugging-port=0", f"--user-data-dir={profile}",
                             "--no-first-run", "--no-default-browser-check", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            env={**os.environ, "HOME": REAL_HOME or os.environ["HOME"]})
    try:
        port_file, deadline = profile / "DevToolsActivePort", time.monotonic() + 30
        while not (port_file.exists() and len(port_file.read_text().splitlines()) >= 2):
            if time.monotonic() > deadline:
                pytest.skip("Chrome didn't start")
            time.sleep(0.1)
        port = int(port_file.read_text().splitlines()[0])
        targets = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=10).read())
        page = next(t for t in targets if t["type"] == "page")
        yield {"host": "127.0.0.1", "port": port, "path": urlsplit(page["webSocketDebuggerUrl"]).path}
    finally:
        proc.terminate()
        proc.wait(10)


# the form's own request that readies its file box: answered after this many seconds (Greenhouse asks
# its storage form once the page has loaded, plan-29g.25)
PRESIGNED = {"after": 1.5}


@pytest.fixture(scope="module")
def site():
    """The form on this computer -> its link."""
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/uncacheable_attributes/presigned_fields?"):
                time.sleep(PRESIGNED["after"])
                body, kind = b'{"resume": {}}', "application/json"
            else:
                page = {"/acme/jobs/1": FORM, ASHBY_PATH: ASHBY_FORM,
                        ASHBY_EDUCATION_PATH: FORM.with_name("ashby-education.html"), BAMBOOHR_PATH: BAMBOOHR_FORM,
                        FRAMES_PATH: FORM.with_name("frames-shadow.html"),
                        FRAMES_PATH.replace("shadow", "inner"): FORM.with_name("frames-inner.html")}.get(self.path)
                body, kind = (page.read_bytes() if page else None), "text/html; charset=utf-8"
                if self.path == JAZZHR_PATH:
                    body = ("<!doctype html><html><head><meta charset=utf-8><title>Test Role - Acme</title></head><body>"
                            f"{JAZZHR_FORM.read_text()}{JAZZHR_BEHAVES}</body></html>").encode()
                if self.path == WORKABLE_PATH:
                    body = WORKABLE_FORM.read_text().replace("</body>", f"{WORKABLE_BEHAVES}</body>").encode()
                if self.path == LEVER_PATH:
                    body = ("<!doctype html><html><head><meta charset=utf-8><title>Apply - Acme</title></head><body>"
                            f"{LEVER_FORM.read_text()}{LEVER_BEHAVES}</body></html>").encode()
            with contextlib.suppress(OSError):  # the tab moved on while it waited
                self.send_response(200 if body else 404)
                self.send_header("Content-Type", kind)
                self.end_headers()
                self.wfile.write(body or b"")

        def do_POST(self):
            # Workable's storage + BambooHR's upload stand-ins: a chosen resume goes here at once
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            body = {"/workable-upload.json": b'{"url": "/stored/resume"}',
                    "/bamboohr-upload.json": BAMBOOHR_FORM.with_name("bamboohr-upload.json").read_bytes()}.get(self.path)
            self.send_response(200 if body else 404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body or b"")

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/acme/jobs/1"
    server.shutdown()
    server.server_close()


def asked(id, title, kind, answer, key=None, options=(), native=None):
    return questions.question(id, title, kind, True, options, key, native) | {"answer": answer}


ANSWERS = [asked("first_name", "First Name", "text", "Ada", key="first_name"),
           asked("email", "Email", "email", "ada@example.com", key="email"),
           asked("question_5", "Country of residence", "choice", "Canada", options=["Canada", "Cameroon"]),
           # the page empties it once, 800 ms after the pick: read back, filled again, it holds
           asked("question_6", "Sponsorship", "yesno", "No", options=["Yes", "No"]),
           # the page empties every pick: never an ok the page doesn't show (plan-29g.20)
           asked("question_7", "How did you hear about this job?", "choice", "Referral", options=["Career Fair", "Referral"]),
           asked("question_100[]", "Employment Preference", "multichoice", ["Part Time", "Contract"]),
           asked("resume", "Resume/CV", "file", True, key="resume")]


def test_in_window_page_fills_greenhouse_in_a_tab_over_cdp(tab, site, tmp_path, monkeypatch):
    # what form.fill does on the page, through the adapter: every box Greenhouse's filler types into
    monkeypatch.setattr(form, "SETTLE_MS", 1500)  # past the page's 800 ms drop, quicker than live
    resume = tmp_path / "Ada_Lovelace_Resume.pdf"
    resume.write_bytes(b"%PDF-1.4\n%%EOF\n")
    cdp = CDP(**tab)
    try:
        cdp.send("Debugger.enable")  # attached as js-debug is: a `debugger;` line would pause the page
        page = window.Page(cdp)
        page.goto(site)
        assert page.url == site and form.closed(page) is None
        page.locator(greenhouse.READY).first.wait_for(timeout=5000)
        report, extra = form.fill_page(page, greenhouse, ANSWERS, str(resume), None)
        got = dict(report)
        # a slow run sees it empty at the pick's own read-back ("not selected"), else at recheck: FAIL either way
        assert got.pop("question_7").startswith("FAIL ")
        assert got == {q["id"]: "ok" for q in ANSWERS if q["id"] != "question_7"} and extra == []
        # read back off the page itself, not the filler's word: the old name replaced, not added to
        assert page.run("document.getElementById('first_name').value") == "Ada"
        assert page.run("document.getElementById('email').value") == "ada@example.com"
        shown = "id => document.getElementById(id).closest('.select__control').querySelector('.select__single-value')?.innerText"
        assert [page.run(f"({shown})('question_{n}')") for n in (5, 6, 7)] == ["Canada", "No", None]
        assert page.run("[...document.querySelectorAll('[name=\"question_100[]\"]')].map(b => b.checked)") == [False, True, True]
        assert page.run("document.getElementById('resume').files[0].name") == resume.name
    finally:
        cdp.close()


@pytest.fixture(scope="module")
def playwright_chrome():
    """Playwright's own headless Chrome: the Chrome path the window's adapter must match."""
    pw = pytest.importorskip("playwright.sync_api")
    try:
        exe = browser.chrome()
    except SystemExit:
        pytest.skip("Chrome not installed")
    with pw.sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe, headless=True)
        yield b
        b.close()


@contextlib.contextmanager
def both(tab, playwright_chrome, url):
    """The same page twice -> {"playwright": page, "window": window.Page}, each loaded."""
    context = playwright_chrome.new_context()
    cdp = CDP(**tab)
    try:
        pw = context.new_page()
        pw.goto(url)
        cdp.send("Debugger.enable")  # attached as js-debug is
        page = window.Page(cdp)
        page.goto(url)
        yield {"playwright": pw, "window": page}
    finally:
        cdp.close()
        context.close()


def ashby_url(site):
    return site.replace("/acme/jobs/1", ASHBY_PATH)


ASHBY_ANSWERS = [asked("_systemfield_name", "Name", "text", "Ada Lovelace", key="name"),
                 asked("_systemfield_email", "Email", "email", "ada@example.com", key="email"),
                 asked("q_phone", "Phone", "phone", "555-0100"),
                 asked("q_why", "Why Acme?", "longtext", "Their own words."),
                 # pressed 200 ms after the click; a second click clears
                 asked("q_sponsor", "Will you require sponsorship?", "yesno", "No", options=["Yes", "No"]),
                 # ticked 200 ms after the label's click; a second click clears
                 asked("q_years", "Years of experience", "choice", "8+", options=["0-2", "3-5", "8+"]),
                 asked("q_stack", "Which do you use?", "multichoice", ["Python", "SQL"]),
                 asked("q_country", "Country", "choice", "United States"),
                 # the page empties every pick 800 ms later: never an ok the page doesn't show
                 asked("q_region", "Region", "choice", "West"),
                 asked("q_city", "Location", "location", "Austin, Texas"),
                 asked("_systemfield_resume", "Resume", "file", True, key="resume")]
# each box's value or tick, pressed buttons, the file name shown - read off the page, never the filler's word
ASHBY_SHOWN = ("es => es.map(e => e.matches('input[type=radio], input[type=checkbox]') ? e.checked"
               " : e.matches('button') ? e.getAttribute('aria-pressed') : e.matches('input[type=file]') ? e.files.length"
               " : 'value' in e ? e.value : e.innerText)")


def test_in_window_fills_ashby_as_playwright_does(tab, site, playwright_chrome, tmp_path, monkeypatch):
    # ashby.fill + holds + form.fill_page through each: same report, same page after, and a second
    # fill changes nothing (a chosen Yes / No or radio clicked again would clear)
    monkeypatch.setattr(form, "SETTLE_MS", 1200)  # past the page's 800 ms drop
    monkeypatch.setattr(ashby, "ERROR_WAIT_MS", 500)
    resume = tmp_path / "Ada_Lovelace_Resume.pdf"
    resume.write_bytes(b"%PDF-1.4\n%%EOF\n")
    reports, pages = {}, {}
    with both(tab, playwright_chrome, ashby_url(site)) as tabs:
        for name, page in tabs.items():
            page.locator(ashby.READY).first.wait_for(timeout=5000)
            assert form.closed(page, ashby) is None
            report, extra = form.fill_page(page, ashby, ASHBY_ANSWERS, str(resume), None)
            reports[name] = dict(report)
            assert extra == []
            page.wait_for_timeout(300)
            once = page.eval_on_selector_all("form input, form textarea, form button, form .name", ASHBY_SHOWN)
            assert [ashby.fill(page, q, None) for q in ASHBY_ANSWERS if q["kind"] != "file" and q["id"] != "q_region"] == ["ok"] * 9
            page.wait_for_timeout(300)
            assert page.eval_on_selector_all("form input, form textarea, form button, form .name", ASHBY_SHOWN) == once
            pages[name] = once
            assert [q["id"] for q in ASHBY_ANSWERS if q["kind"] != "file" and not ashby.holds(page, q)] == ["q_region"]
    assert reports["window"] == reports["playwright"]
    assert reports["window"] == {q["id"]: "ok" for q in ASHBY_ANSWERS} | {"q_region": "FAIL answer dropped after filling - fill it by hand"}
    assert pages["window"] == pages["playwright"]
    assert pages["window"] == ["Ada Lovelace", "ada@example.com", "555-0100", "Their own words.", "false", "true",
                               False, False, True, True, True, False, "United States", "", "Austin, TX, United States",
                               f"{resume.name} Replace", 1]


def test_in_window_fills_ashby_education_as_playwright_does(tab, site, playwright_chrome, monkeypatch):
    # two schools' blocks (same ids in each, school 2 through "+ Add Education"): same report + page through each
    monkeypatch.setattr(form, "SETTLE_MS", 300)
    job = {"applicationForm": {"sections": [{"fieldEntries": [{"isRequired": True, "field": {
        "path": ashby.EDUCATION_PATH, "title": "Education History", "type": "EducationHistory", "schoolName": "required",
        "degree": "optional", "major": "optional", "startDate": "optional", "endDate": "optional"}}]}]}}
    schools = [{"institution": "New York University", "degree": "BS", "field": "Economics", "end": "2020-05"},
               {"institution": "Massachusetts Institute of Technology", "degree": "MS", "field": "Computer Science",
                "end": "2022-06"}]
    drafted = questions.draft(ashby.from_form(job, 2), {}, schools=schools)
    reports, pages = {}, {}
    with both(tab, playwright_chrome, site.replace("/acme/jobs/1", ASHBY_EDUCATION_PATH)) as tabs:
        for name, page in tabs.items():
            page.locator(ashby.READY).first.wait_for(timeout=5000)
            report, extra = form.fill_page(page, ashby, drafted, None, None)
            reports[name] = dict(report)
            assert extra == ["_systemfield_name"]
            pages[name] = page.eval_on_selector_all(
                "form input, form select", "es => es.map(e => e.tagName === 'SELECT' ? (e.value ? e.selectedOptions[0].text"
                " : '') : e.type === 'checkbox' ? e.checked : e.value)")
    assert reports["window"] == reports["playwright"] == {q["id"]: "ok" for q in drafted}
    assert pages["window"] == pages["playwright"] == [
        "", "New York University", "Bachelor of Science", "Economics", "", "", "May", "2020", False,
        "Massachusetts Institute of Technology", "Master of Science", "Computer Science", "", "", "June", "2022", False]


def lever_url(site):
    return site.replace("/acme/jobs/1", LEVER_PATH)


# tenant A's own questions, each kind answered once: radios, a dropdown, ticks, text, a place, the resume;
# the rest left blank (skipped, as an unanswered one is)
LEVER_GIVEN = {"resume": True, "name": "Ada Lovelace", "email": "ada@example.com", "phone": "555-0100",
               "location": "Austin, Texas", "urls[LinkedIn]": "https://www.linkedin.com/in/ada",
               "Are you authorized to work in the United States?": "Yes",
               "Will you require sponsorship for employment now or": "No",
               "If yes, what type of sponsorship?": "None needed.",
               "Acme provides technology": "Other", "How did you hear about us?": "LinkedIn Post",
               "Please state your full legal name:": "Ada King Lovelace",
               "Are you local to or willing to relocate?": "Yes",
               "What office(s) would you be willing to relocate to": ["Boston, MA", "International"],
               "eeo[gender]": "Decline to self-identify", "eeo[race]": "Asian (Not Hispanic or Latino)",
               "eeo[disability]": "I do not want to answer", "eeo[disabilitySignature]": "Ada Lovelace"}


def lever_answers() -> list[dict]:
    out = []
    for q in lever.from_page(LEVER_FORM.read_text()):
        given = [v for k, v in LEVER_GIVEN.items() if k == q["id"] or q["title"].startswith(k)]
        out.append(q | {"answer": given[0] if given else ""})
    assert sum(1 for q in out if q["answer"] != "") == len(LEVER_GIVEN)
    return out


# each box's value or tick, each list's picked texts, Lever's own place record + the resume verdict shown -
# read off the page, never the filler's word
LEVER_SHOWN = ("es => es.map(e => e.matches('input[type=radio], input[type=checkbox]') ? e.checked"
               " : e.matches('select') ? [...e.selectedOptions].map(o => o.text.trim()).join('|')"
               " : e.matches('input[type=file]') ? e.files.length : e.value)"
               ".concat([document.getElementById('selected-location').value,"
               " document.querySelector('.visible-resume-upload .filename').textContent])")
LEVER_BOXES = "#application-form input:not([type=hidden]), #application-form select, #application-form textarea"


def test_in_window_fills_lever_as_playwright_does(tab, site, playwright_chrome, tmp_path, monkeypatch):
    # lever.fill + holds + form.fill_page through each on tenant A's saved form: same report, same page
    # after, every answer read back, a second fill changes nothing (a tick clicked again would clear)
    monkeypatch.setattr(form, "SETTLE_MS", 1000)
    resume = tmp_path / "Ada_Lovelace_Resume.pdf"
    resume.write_bytes(b"%PDF-1.4\n%%EOF\n")
    qs = lever_answers()
    answered = [q for q in qs if q["answer"] != ""]
    again = [q for q in answered if q["kind"] != "file" and q.get("native") != "eeo:signature"]
    reports, pages = {}, {}
    with both(tab, playwright_chrome, lever_url(site)) as tabs:
        for name, page in tabs.items():
            assert form.closed(page, lever) is None
            report, extra = form.fill_page(page, lever, qs, str(resume), None)
            reports[name] = dict(report)
            assert extra == []
            page.wait_for_timeout(300)
            once = page.eval_on_selector_all(LEVER_BOXES, LEVER_SHOWN)
            assert [lever.fill(page, q, None) for q in again] == ["ok"] * len(again)
            page.wait_for_timeout(500)  # past the place search's own wait
            assert page.eval_on_selector_all(LEVER_BOXES, LEVER_SHOWN) == once
            pages[name] = once
            assert [q["id"] for q in again if not lever.holds(page, q)] == []
    assert reports["window"] == reports["playwright"]
    assert reports["window"] == {q["id"]: "ok" for q in answered} | {"eeo[disabilitySignature]": questions.left_on_page(
        next(q for q in qs if q["id"] == "eeo[disabilitySignature]"))}
    assert pages["window"] == pages["playwright"]
    # what shows, empty boxes + clear ticks left out: the file, text boxes, ticks (Yes, No, Other, LinkedIn Post,
    # Boston, International, Asian), lists (veteran left at its own "Select ..."), Lever's place record, its verdict
    assert [v for v in pages["window"] if v not in ("", False, 0)] == [
        1, "Ada Lovelace", "ada@example.com", "555-0100", "Austin, Texas, United States", "https://www.linkedin.com/in/ada",
        True, True, "None needed.", True, True, "Ada King Lovelace", "Yes", True, True, "Decline to self-identify", True,
        "Select ...", "I do not want to answer", '{"name":"Austin, Texas, United States"}', resume.name]


def jazzhr_url(site):
    return site.replace("/acme/jobs/1", JAZZHR_PATH)


# tenant B's own questions, each kind answered once: contact + address boxes, upper-case YES / NO lists,
# Yes / No as two ticks, the attestation tick (left to the applicant), a voluntary list, the resume
JAZZHR_GIVEN = {"resume": True, "first_name": "Ada", "last_name": "Lovelace", "email": "ada@example.com",
                "phone": "555-0100", "street": "1 Main St", "city": "Austin", "state": "TX", "zip": "78701",
                "I understand": "Yes", "Desired/expected": "90000", "Are you currently, or have you ever": "No",
                "Do you currently have a non-compete": "Yes", "Do you need, or will you need": "No",
                "Do you live in the geographical": "Yes", "Race/Ethnicity": "Asian, not Hispanic or Latino"}


def jazzhr_answers() -> list[dict]:
    out = []
    for q in jazzhr.from_html(JAZZHR_FORM.read_text()):
        given = [v for k, v in JAZZHR_GIVEN.items() if k == q.get("key") or q["title"].startswith(k)]
        out.append(q | {"answer": given[0] if given else ""})
    assert sum(1 for q in out if q["answer"] != "") == len(JAZZHR_GIVEN)
    return out


# each box's value or tick, each list's shown text, the file's name, whether the file box shows - read off
# the page, never the filler's word
JAZZHR_SHOWN = ("es => es.map(e => e.type === 'checkbox' ? e.checked : e.matches('select') ? e.selectedOptions[0].text"
                " : e.type === 'file' ? (e.files[0] || {}).name || '' : e.value)"
                ".concat([!document.getElementById('resumator-resume-upload-wrapper').classList.contains('none')])")
JAZZHR_BOXES = "#form_submit_new_resume input:not([type=hidden]), #form_submit_new_resume select, #form_submit_new_resume textarea"


def test_in_window_fills_jazzhr_as_playwright_does(tab, site, playwright_chrome, tmp_path, monkeypatch):
    # jazzhr.fill + holds + form.fill_page through each on tenant B's saved form: same report, same page
    # after, every answer read back, a second fill changes nothing (a tick clicked again would clear)
    monkeypatch.setattr(form, "SETTLE_MS", 300)
    resume = tmp_path / "Ada_Lovelace_Resume.pdf"
    resume.write_bytes(b"%PDF-1.4\n%%EOF\n")
    qs = jazzhr_answers()
    answered = [q for q in qs if q["answer"] != ""]
    attest = next(q for q in qs if q["title"].startswith("I understand"))
    again = [q for q in answered if q["kind"] != "file" and q is not attest]
    reports, pages = {}, {}
    with both(tab, playwright_chrome, jazzhr_url(site)) as tabs:
        for name, page in tabs.items():
            assert form.closed(page, jazzhr) is None
            report, extra = form.fill_page(page, jazzhr, qs, str(resume), None)
            reports[name] = dict(report)
            assert extra == []
            once = page.eval_on_selector_all(JAZZHR_BOXES, JAZZHR_SHOWN)
            assert [jazzhr.fill(page, q, None) for q in again] == ["ok"] * len(again)
            assert page.eval_on_selector_all(JAZZHR_BOXES, JAZZHR_SHOWN) == once
            pages[name] = once
            assert [q["id"] for q in again if not jazzhr.holds(page, q)] == []
    assert reports["window"] == reports["playwright"]
    assert reports["window"] == {q["id"]: "ok" for q in answered} | {attest["id"]: questions.left_on_page(attest)}
    assert pages["window"] == pages["playwright"]
    # what shows, empty boxes + clear ticks left out: contact + address, the file, the referral box left
    # empty, salary, NO / YES as the page writes them, ticks (NO, YES), gender left at its own "Decline",
    # race, the file box shown by "Attach resume"
    assert [v for v in pages["window"] if v not in ("", False)] == [
        "Ada", "Lovelace", "ada@example.com", "555-0100", "1 Main St", "Austin", "TX", "78701", resume.name,
        "90000", "NO", "YES", True, True, "Decline to answer", "Asian, not Hispanic or Latino", True]


def workable_url(site):
    return site.replace("/acme/jobs/1", WORKABLE_PATH)


# the hand-built form's questions, each kind answered once: text boxes, YES / NO + single-choice radios, ticks,
# both dropdowns, the resume
WORKABLE_ANSWERS = [
    asked("firstname", "First name", "text", "Ada", key="first_name", native="firstname"),
    asked("lastname", "Last name", "text", "Lovelace", key="last_name", native="lastname"),
    asked("email", "Email", "email", "ada@example.com", key="email", native="email"),
    asked("phone", "Phone", "phone", "555-0100", key="phone", native="phone"),
    # prefilled by the page, never the user's answer: left as it shows
    asked("address", workable.PREFILLED, "location", "", key="location", native="address"),
    asked("summary", "Summary", "longtext", "Built the monthly reports.", native="summary"),
    asked("QA_1", "Why Acme?", "longtext", "Their own words.", native="QA:paragraph"),
    asked("QA_2", "Expected salary", "number", "90000", native="QA:number"),
    asked("QA_3", "Are you authorized to work in the US?", "yesno", "Yes", options=["Yes", "No"], native="QA:boolean"),
    asked("QA_4", "Do you need adjustments?", "choice", "No", options=["Yes - please add details below", "No"],
          native="QA:multiple"),
    asked("CA_9", "Which shifts can you work?", "multichoice", ["Weekends", "Holiday"],
          options=["Weekends", "Evenings", "Holiday"], native="CA:multiple:152176,152177,152178"),
    asked("CA_1", "Highest degree", "choice", "Associate", options=["High School/GED", "Associate", "Bachelor's"],
          native="CA:dropdown"),
    asked("CA_2", "Are you 18 or older?", "yesno", "No", options=["Yes", "No"], native="CA:dropdown"),
    asked("resume", "Resume", "file", True, key="resume", native="resume")]
# each box's value or tick, each radio's aria-checked, each list's shown pick, the resume box's words - read off
# the page, never the filler's word
WORKABLE_SHOWN = ("es => es.map(e => ['checkbox', 'radio'].includes(e.type) ? e.checked : e.type === 'file' ? e.files.length : e.value)"
                  ".concat([...document.querySelectorAll('[role=radio]')].map(r => r.getAttribute('aria-checked')),"
                  " [document.querySelector('[data-ui=\"resume\"] .file').textContent])")
WORKABLE_BOXES = "#application input:not([type=hidden]), #application textarea"


def test_in_window_fills_workable_as_playwright_does(tab, site, playwright_chrome, tmp_path, monkeypatch):
    # workable.fill + holds + form.fill_page through each, under the cookie dialog as measured: same report,
    # same page after, every answer read back, a second fill changes nothing
    monkeypatch.setattr(form, "SETTLE_MS", 300)
    monkeypatch.setattr(workable, "ERROR_WAIT_MS", 500)
    resume = tmp_path / "Ada_Lovelace_Resume.pdf"
    resume.write_bytes(b"%PDF-1.4\n%%EOF\n")
    answered = [q for q in WORKABLE_ANSWERS if q["answer"] != ""]
    again = [q for q in answered if q["kind"] != "file"]
    reports, pages = {}, {}
    with both(tab, playwright_chrome, workable_url(site)) as tabs:
        for name, page in tabs.items():
            assert form.closed(page, workable) is None
            # the dialog is what a click at a list's middle meets, as on the live page
            assert page.evaluate("""() => { const b = document.querySelector('[data-ui=CA_1] [role=combobox]');
              b.scrollIntoView({block: 'center'}); const r = b.getBoundingClientRect();
              return document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2).closest('[role=dialog]') !== null; }""")
            report, extra = form.fill_page(page, workable, WORKABLE_ANSWERS, str(resume), None)
            reports[name] = dict(report)
            assert extra == []
            once = page.eval_on_selector_all(WORKABLE_BOXES, WORKABLE_SHOWN)
            assert [workable.fill(page, q, None) for q in again] == ["ok"] * len(again)
            page.wait_for_timeout(300)
            assert page.eval_on_selector_all(WORKABLE_BOXES, WORKABLE_SHOWN) == once
            pages[name] = once
            assert [q["id"] for q in answered if not workable.holds(page, q)] == []
    assert reports["window"] == reports["playwright"]
    assert reports["window"] == {q["id"]: "ok" for q in answered}
    assert pages["window"] == pages["playwright"]
    # what shows, empty boxes + clear ticks left out: contact, the page's own address, the resume chosen,
    # summary, both answers, the inputs under YES + No, ticks (Weekends, Holiday), both picks, YES + No as
    # Workable marks them, the stored file's name
    assert [v for v in pages["window"] if v not in ("", False, 0, "false")] == [
        "Ada", "Lovelace", "ada@example.com", "555-0100", "Example City", 1, "Built the monthly reports.",
        "Their own words.", "90000", True, True, True, True, "Associate", "No", "true", "true", resume.name]


def test_in_window_workable_click_force_dispatch_keys_and_evaluate_as_playwright_does(tab, site, playwright_chrome):
    # the calls workable.py makes that the adapter lacked (plan-k8n.7), each on the same page: a covered click
    # times out, forced it lands on what is on top, a dispatched click reaches the element itself, Down + Space
    # by name, Escape wherever focus is, page.evaluate calls a function and evaluates the rest, ':visible'
    got = {}
    with both(tab, playwright_chrome, workable_url(site)) as tabs:
        for name, page in tabs.items():
            page.evaluate("""() => { window.told = []; document.addEventListener('click', (e) => told.push(
              (e.target.closest('[data-ui]') || e.target).getAttribute('data-ui') || e.target.tagName), true); }""")
            box, radio = page.locator("[data-ui=CA_1] [role=combobox]"), page.locator("fieldset [role=radio]").first
            row = []
            with pytest.raises(Exception, match="(?i)timeout|sits over"):
                box.click(timeout=500)
            box.click(force=True)
            row.append([page.locator("[role=option]:visible").count(), page.evaluate("told.slice()")])
            box.focus()
            box.press("ArrowDown")
            row.append(page.locator("[role=option]:visible, [data-ui=CA_2] [role=option]:visible").all_inner_texts())
            page.keyboard.press("Escape")
            row.append(page.locator("[role=option]:visible").count())
            radio.focus()
            radio.press("Space")
            row.append(radio.get_attribute("aria-checked"))
            box.press("ArrowDown")
            page.locator("[role=option]:visible").nth(1).dispatch_event("click")
            row.append([box.input_value(), page.evaluate("told.slice()")])
            row.append([page.evaluate("document.title"), page.evaluate("(n) => n + 1", 41),
                        page.evaluate("([a, b]) => a + b", ["x", "y"]), page.evaluate("function () { return 7; }")])
            got[name] = row
        with pytest.raises(ValueError):
            tabs["window"].locator("div:not(:visible)")
    assert got["window"] == got["playwright"]
    assert got["window"][0][0] == 0 and got["window"][1] == ["High School/GED", "Associate", "Bachelor's"]
    assert got["window"][3] == "true" and got["window"][4][0] == "Associate" and got["window"][5][1:] == [42, "xy", 7]


def test_in_window_is_visible_and_select_by_value_as_playwright_does(tab, site, playwright_chrome):
    # the two calls jazzhr.py makes that the adapter lacked (plan-k8n.4), each read on the same page
    shown = ["#resumator-choose-upload", "#resumator-resume-value", "#resumator-resume-upload-wrapper",
             "#form_submit_new_resume select", ".g-recaptcha", "#nobody"]
    got = {}
    with both(tab, playwright_chrome, jazzhr_url(site)) as tabs:
        for name, page in tabs.items():
            run = page.run if name == "window" else page.evaluate
            run("window.told = []; document.addEventListener('change', (e) => told.push(e.target.id))")
            before = [page.locator(s).first.is_visible() for s in shown]
            page.locator("#resumator-choose-upload").click()
            box = page.locator('[id="resumator-questionnaire-q1474074"]')
            no = box.evaluate("e => [...e.options].find(o => o.text === 'NO').value")
            got[name] = [before, [page.locator(s).first.is_visible() for s in shown], box.select_option(value=no),
                         box.select_option(value=[no]), box.evaluate("e => e.selectedOptions[0].text"), run("told")]
        with pytest.raises(TimeoutError):
            tabs["window"].locator('[id="resumator-questionnaire-q1474074"]').select_option(value="nobody", timeout=300)
        with pytest.raises(ValueError):
            tabs["window"].locator('[id="resumator-questionnaire-q1474074"]').select_option()
    assert got["window"] == got["playwright"]
    assert got["window"][0][:3] == [True, False, False] and got["window"][1][:3] == [False, True, True]


@pytest.mark.parametrize("selector", ["#application-form .resume-upload-success, #application-form .resume-upload-failure",
                                      "#application-form .application-label", "#application-form input",
                                      "#application-form .dropdown-results > div", "#application-form .filename"])
def test_in_window_visible_filter_and_all_find_what_playwright_finds(tab, site, playwright_chrome, tmp_path, selector):
    resume = tmp_path / "Ada_Lovelace_Resume.pdf"
    resume.write_bytes(b"%PDF-1.4\n%%EOF\n")
    got = {}
    with both(tab, playwright_chrome, lever_url(site)) as tabs:
        for name, page in tabs.items():
            before = [page.locator(selector).filter(visible=True).count(), len(page.locator(selector).all())]
            page.locator("#resume-upload-input").set_input_files(str(resume))
            page.locator("#location-input").press_sequentially("Aus")
            page.wait_for_timeout(800)
            shown = page.locator(selector).filter(visible=True)
            got[name] = before + [shown.count(), [m.inner_text() for m in shown.all()]]
    assert got["window"] == got["playwright"]


def test_in_window_select_option_picks_by_label_as_playwright_does(tab, site, playwright_chrome):
    got = {}
    with both(tab, playwright_chrome, lever_url(site)) as tabs:
        for name, page in tabs.items():
            run = page.run if name == "window" else page.evaluate
            run("window.told = []; document.addEventListener('change', (e) => told.push(e.target.name))")
            box = page.locator('[name="eeo[gender]"]')
            got[name] = [box.select_option(label="Female"), box.select_option(label=["Male"]),
                         box.evaluate("e => e.selectedOptions[0].text"), run("told")]
        with pytest.raises(Exception, match="Non-multiple select element"):
            tabs["window"].locator('[name="eeo[gender]"]').select_option(label=["Male", "Female"])
        with pytest.raises(TimeoutError):
            tabs["window"].locator('[name="eeo[gender]"]').select_option(label="Nobody", timeout=300)
    assert got["window"] == got["playwright"]


@pytest.mark.parametrize("ask", [
    lambda p: p.get_by_role("button", name="Yes", exact=True),  # the one hidden from a screen reader left out
    lambda p: p.get_by_role("button", name="yes"),
    lambda p: p.get_by_role("button", name="No", exact=True),
    lambda p: p.get_by_role("button", name="no"),  # aria-label "No thanks" too, never its text "Close"
    lambda p: p.get_by_role("button", name="Close"),
    lambda p: p.get_by_role("button"),
    lambda p: p.locator('[data-field-path="q_years"]').get_by_role("button", name="No", exact=True),
    lambda p: p.locator("label", has_text=re.compile(r"^\s*8\+\s*$")),
    lambda p: p.locator("label", has_text=re.compile(r"^\s*8\+\s*$", re.IGNORECASE)),
    lambda p: p.locator("label", has_text=re.compile("^python$")),
    lambda p: p.locator("label", has_text="  PYTHON "),
    lambda p: p.locator("label", has_text="sponsor"),
    lambda p: p.locator("div", has_text=re.compile("Which do you use")),
])
def test_in_window_role_and_text_lookups_find_what_playwright_finds(tab, site, playwright_chrome, ask):
    with both(tab, playwright_chrome, ashby_url(site)) as tabs:
        counts = {name: ask(page).count() for name, page in tabs.items()}
        texts = {name: ask(page).all_inner_texts() for name, page in tabs.items()}
    assert counts["window"] == counts["playwright"] and texts["window"] == texts["playwright"]


def test_in_window_is_checked_reads_the_tick_as_playwright_does(tab, site, playwright_chrome):
    with both(tab, playwright_chrome, ashby_url(site)) as tabs:
        for page in tabs.values():
            page.locator("#stack-1").click()
        assert {n: [p.locator(f"#stack-{i}").is_checked() for i in range(3)] for n, p in tabs.items()} == \
            {"playwright": [False, True, False], "window": [False, True, False]}
        with pytest.raises(Exception, match="Not a checkbox or radio button"):
            tabs["window"].locator("#name").is_checked()


def test_in_window_upload_waits_for_the_page_to_ready_its_file_box(tab, site, tmp_path):
    # owner's run: a file chosen as the form showed got the page's own error, the name never came
    resume = tmp_path / "Ada_Lovelace_Resume.pdf"
    resume.write_bytes(b"%PDF-1.4\n%%EOF\n")
    q = asked("resume", "Resume/CV", "file", True, key="resume")
    error, name = "document.getElementById('resume-error').innerText", "document.querySelector('.file-upload__filename').innerText"
    cdp = CDP(**tab)
    try:
        page = window.Page(cdp)
        page.goto(site)
        page.locator("#resume").set_input_files(str(resume))  # as the fill did: no wait
        page.until(f"{error}.includes('uploadFile')", 3000, "the page's own error")
        assert "Cannot read properties of undefined (reading 'uploadFile')" in page.run(error) and page.run(name) == ""
        page.goto(site)
        start = time.monotonic()
        assert greenhouse.put_file(page, q, str(resume)) == "ok"
        assert time.monotonic() - start >= PRESIGNED["after"] - 0.2  # waited for the page's own request
        assert page.run(name) == resume.name and page.run(error) == ""
    finally:
        cdp.close()


def test_in_window_upload_the_page_never_readies_is_a_fail_to_do_by_hand(tab, site, tmp_path, monkeypatch):
    # its request still out when the wait gives up: chosen anyway, the page's error read back -> never ok
    monkeypatch.setitem(PRESIGNED, "after", 10)
    monkeypatch.setattr(greenhouse, "IDLE_WAIT_MS", 1000)
    resume = tmp_path / "Ada_Lovelace_Resume.pdf"
    resume.write_bytes(b"%PDF-1.4\n%%EOF\n")
    cdp = CDP(**tab)
    try:
        page = window.Page(cdp)
        page.goto(site)
        with pytest.raises(TimeoutError):
            page.wait_for_load_state("networkidle", timeout=1000)
        assert greenhouse.put_file(page, asked("resume", "Resume/CV", "file", True, key="resume"), str(resume)) == greenhouse.NOT_READY
        assert page.run("document.querySelector('.file-upload__filename').innerText") == ""
    finally:
        cdp.close()


def test_in_window_locator_waits_then_says_what_never_came(tab, site):
    cdp = CDP(**tab)
    try:
        page = window.Page(cdp)
        page.goto(site)
        assert page.locator("form input[type=checkbox]").count() == 3
        assert page.locator("label").get_by_text("  part   TIME ").count() == 1
        assert page.locator("form").locator("label").nth(1).inner_text() == "Email"
        with pytest.raises(TimeoutError):
            page.locator("#nowhere").first.wait_for(timeout=300)
        page.run("document.getElementById('email').style.display = 'none'")
        with pytest.raises(TimeoutError):  # in the page but not shown: never clicked blind
            page.locator("#email").click(timeout=300)
        assert page.locator("#email").input_value() == ""  # read without waiting to be shown
    finally:
        cdp.close()


def frames_url(site):
    return site.replace("/acme/jobs/1", FRAMES_PATH)


def loaded(page):
    """Both frames in: the same-site one with its boxes, the other site's listed."""
    deadline = time.monotonic() + 10
    while len(page.frames) < 3 and time.monotonic() < deadline:
        time.sleep(0.1)
    page.frames[1].locator("#city").wait_for(timeout=10000)
    return page


def test_in_window_parity_snapshot(tab, site, playwright_chrome):
    # dom.snapshot through each on the frame + shadow page: same controls, frames, captcha, closed root
    with both(tab, playwright_chrome, frames_url(site)) as tabs:
        snaps = {name: dom.snapshot(loaded(page)) for name, page in tabs.items()}
    assert snaps["window"] == snaps["playwright"]
    snap, inner = snaps["window"], frames_url(site).replace("shadow", "inner")
    assert [c["hook"] for c in snap["controls"] if c["frame"] == inner] == [
        '[id="years"]', '[id="degree"]', '[name="relocate"]', '[id="weekends"]', '[id="city"]']
    assert [c["hook"] for c in snap["controls"] if c["in_shadow"]] == ['[id="nick"]', '[id="cv"]']
    assert snap["captcha"] == [{"url": frames_url(site), "marker": "g-recaptcha"}]
    assert [f["url"] for f in snap["other_frames"]] == [inner.replace("127.0.0.1", "localhost")]
    assert [(n["host"], n["why"]) for n in snap["not_readable"]] == [("closed-box", "closed shadow root - not readable")]


FRAMES_ANSWERS = [("full_name", "Ada Lovelace"), ("country", "Mexico"), ("years", "8"), ("degree", "Bachelor's"),
                  ("relocate", "No"), ("weekends", "Yes"), ("city", "Austin, Texas"), ("nick", "Ada"), ("cv", True)]
# each box as the page shows it, in its own frame + shadow root - never the filler's word
FRAMES_SHOWN = """() => { const deep = (d) => d.querySelector('shadow-box') ? d.querySelector('shadow-box').shadowRoot : d;
  const inner = document.getElementById('same').contentDocument, s = deep(document);
  return [document.getElementById('full_name').value, document.getElementById('country').value,
    inner.getElementById('years').value, inner.getElementById('degree').value,
    [...inner.querySelectorAll('[name=relocate]')].map(r => r.checked), inner.getElementById('weekends').checked,
    inner.getElementById('city').value, s.getElementById('nick').value,
    s.getElementById('cv').files[0] ? s.getElementById('cv').files[0].name : '']; }"""


def test_in_window_parity_dom_fill(tab, site, playwright_chrome, tmp_path):
    # dom.fill through each: boxes in the main page, the same-site frame (a list clicked inside it) and an open
    # shadow root (the resume chosen there) - same reports, same page after
    resume = tmp_path / "Ada_Lovelace_Resume.pdf"
    resume.write_bytes(b"%PDF-1.4\n%%EOF\n")
    reports, shown = {}, {}
    with both(tab, playwright_chrome, frames_url(site)) as tabs:
        for name, page in tabs.items():
            qs = {q["id"]: q for q in dom.questions(dom.snapshot(loaded(page)))}
            todo = [qs[f'[id="{i}"]'] if f'[id="{i}"]' in qs else qs[f'[name="{i}"]'] for i, _ in FRAMES_ANSWERS]
            reports[name] = [dom.fill(page, q | {"answer": a} | ({"key": "resume"} if a is True else {}), str(resume))
                             for q, (_, a) in zip(todo, FRAMES_ANSWERS)]
            shown[name] = page.evaluate(FRAMES_SHOWN)
    assert reports["window"] == reports["playwright"] == ["ok"] * len(FRAMES_ANSWERS)
    assert shown["window"] == shown["playwright"] == [
        "Ada Lovelace", "Mexico", "8", "Bachelor's", [False, True], True, "Austin, Texas, United States", "Ada", resume.name]


def test_in_window_parity_frames(tab, site, playwright_chrome):
    # page.frames / main_frame / frame.url / frame.evaluate: same list in the same order, each frame its own page
    got = {}
    with both(tab, playwright_chrome, frames_url(site)) as tabs:
        for name, page in tabs.items():
            fs = loaded(page).frames
            got[name] = [[f.url for f in fs], fs[0] is page.main_frame, page.frames[1] is fs[1],
                         [f.evaluate("document.title") for f in fs[:2]], fs[1].evaluate("(n) => n * 2", 21),
                         fs[1].locator("label").all_inner_texts()]
    assert got["window"] == got["playwright"]
    assert got["window"][1:4] == [True, True, ["Apply - Acme", "Inner form"]]


def test_in_window_parity_evaluate_handle(tab, site, playwright_chrome):
    # evaluate_handle + JSHandle get_property / json_value / get_properties / as_element, as dom.find and
    # smartrecruiters.py use them
    got = {}
    with both(tab, playwright_chrome, frames_url(site)) as tabs:
        for name, page in tabs.items():
            h = page.evaluate_handle("(id) => ({n: 3, s: 'x', none: null, list: [document.body, document.getElementById(id)]})",
                                     "full_name")
            members = h.get_property("list").get_properties()
            row = [h.get_property("n").json_value(), h.get_property("s").json_value(), h.get_property("none").json_value(),
                   h.get_property("none").as_element(), h.get_property("n").as_element(), sorted(members),
                   [m.as_element().evaluate("e => e.tagName") for m in members.values()], h.evaluate("x => x.n + 1"),
                   h.evaluate("x => x === null")]
            el = page.evaluate_handle("() => document.querySelector('shadow-box').shadowRoot.getElementById('nick')").as_element()
            el.fill("Ada")
            row += [el.input_value(), el.get_attribute("name"), page.evaluate_handle("() => null").as_element(),
                    page.evaluate_handle("() => 5").json_value()]
            h.dispose()
            got[name] = row
    assert got["window"] == got["playwright"]
    assert got["window"][:4] == [3, "x", None, None] and got["window"][5:7] == [["0", "1"], ["BODY", "INPUT"]]


def test_in_window_parity_closed_shadow(tab, site, playwright_chrome):
    with both(tab, playwright_chrome, frames_url(site)) as tabs:
        got = {name: dom.closed_shadow(loaded(page)) for name, page in tabs.items()}
    assert got["window"] == got["playwright"] == [
        {"url": frames_url(site), "host": "closed-box", "why": "closed shadow root - not readable"}]


@pytest.mark.parametrize("selector", [
    "#nick", "input", "section.part > input", "label + input", "h3 ~ section", "shadow-box section", "shadow-box label",
    "button, #full_name, [role=option]", ".part-note i", "section:visible > span", "#closed-box input", "[id=hidden-away]",
    "div.form-group:visible > label", "body > *:visible",
])
def test_in_window_parity_css_pierces_shadow(tab, site, playwright_chrome, selector):
    # CSS looks inside open shadow roots as Playwright's does: combinators, comma lists in page order, :visible
    with both(tab, playwright_chrome, frames_url(site)) as tabs:
        got = {name: [page.locator(selector).count(), page.locator(selector).evaluate_all("es => es.map(e => e.id || e.tagName)")]
               for name, page in tabs.items()}
    assert got["window"] == got["playwright"]


def test_in_window_parity_scope_and_chained_steps(tab, site, playwright_chrome):
    got = {}
    with both(tab, playwright_chrome, frames_url(site)) as tabs:
        for name, page in tabs.items():
            got[name] = [page.locator("section").locator(":scope > label").all_inner_texts(),
                         page.locator("shadow-box").locator("input").count(),
                         page.locator("div").locator(":scope > input").evaluate_all("es => es.map(e => e.id)"),
                         page.locator(".fab-Select").locator(":scope button").count()]
    assert got["window"] == got["playwright"]
    assert got["window"][0] == ["Preferred name"]


@pytest.mark.parametrize("text, exact", [("Attach", True), ("attach", False), ("attach", True), ("required", False),
                                         ("Inside the shadow", True), ("inside", False), ("Phone", True),
                                         ("Phone (optional)", True), (re.compile(r"^Cover"), False)])
def test_in_window_parity_get_by_text_exact(tab, site, playwright_chrome, text, exact):
    with both(tab, playwright_chrome, frames_url(site)) as tabs:
        got = {name: [page.get_by_text(text, exact=exact).count(), page.get_by_text(text, exact=exact).all_inner_texts()]
               for name, page in tabs.items()}
    assert got["window"] == got["playwright"]


@pytest.mark.parametrize("text, exact", [("Full name", True), ("full", False), ("Preferred name", True),
                                         ("Resume file", True), ("name", False), ("Country", True), ("country", True),
                                         (re.compile("^Pref"), False)])
def test_in_window_parity_get_by_label(tab, site, playwright_chrome, text, exact):
    with both(tab, playwright_chrome, frames_url(site)) as tabs:
        got = {name: page.get_by_label(text, exact=exact).evaluate_all("es => es.map(e => e.id)") for name, page in tabs.items()}
    assert got["window"] == got["playwright"]


def test_in_window_parity_last(tab, site, playwright_chrome):
    with both(tab, playwright_chrome, frames_url(site)) as tabs:
        got = {name: [page.locator("input").last.get_attribute("id"), page.locator("label").nth(-1).inner_text(),
                      page.locator("label").last.inner_text(), page.locator("#nowhere").last.count()]
               for name, page in tabs.items()}
    assert got["window"] == got["playwright"]
    assert got["window"][:2] == ["cv", "Preferred name"]


@pytest.mark.parametrize("ask", [
    # bamboohr.py's shapes
    lambda p: p.locator("#pick-in").locator("xpath=ancestor::div[contains(@class,'fab-Select')][1]//button[@aria-haspopup]").first,
    lambda p: p.locator("""xpath=//p[normalize-space(translate(., '*', ''))="Cover letter"]/following-sibling::*//input[@type='file']"""),
    lambda p: p.locator("#letter").locator("xpath=ancestor::*[contains(@class,'nowhere')][1]"),
    lambda p: p.locator("//label"),
    lambda p: p.locator("xpath=..").first,
])
def test_in_window_parity_xpath(tab, site, playwright_chrome, ask):
    with both(tab, playwright_chrome, frames_url(site)) as tabs:
        got = {name: ask(page).evaluate_all("es => es.map(e => e.id || e.tagName)") for name, page in tabs.items()}
    assert got["window"] == got["playwright"]


def test_in_window_parity_filter_has(tab, site, playwright_chrome):
    # paylocity.py's group(): the shown .form-group whose own label is the question
    said = re.compile(r"^\s*Phone\s*(?:\((?:required|optional)\))?\s*$", re.I)
    got = {}
    with both(tab, playwright_chrome, frames_url(site)) as tabs:
        for name, page in tabs.items():
            g = page.locator(".form-group:visible").filter(has=page.locator(":scope > label").filter(has_text=said)).first
            got[name] = [g.locator("input").get_attribute("id"), page.locator(".form-group").filter(has=page.locator("label")).count(),
                         page.locator("div").filter(has=page.locator("button"), has_text="Choose").count(),
                         page.locator(".form-group").filter(has=page.locator("#nowhere")).count()]
    assert got["window"] == got["playwright"]
    assert got["window"][:2] == ["phone", 2]


@pytest.mark.parametrize("wait_until", ["commit", "domcontentloaded", "load", "networkidle"])
def test_in_window_parity_goto_wait_until(tab, site, playwright_chrome, wait_until):
    # oracle.py + icims.py: goto(wait_until=); the page there to read once it says so
    url = frames_url(site)
    got = {}
    with both(tab, playwright_chrome, site) as tabs:
        for name, page in tabs.items():
            page.goto(url, wait_until=wait_until)
            page.locator("#full_name").wait_for(timeout=5000)
            got[name] = [page.url, page.locator("#full_name").count()]
        with pytest.raises(ValueError):
            tabs["window"].goto(url, wait_until="soon")
    assert got["window"] == got["playwright"] == [url, 1]


def test_in_window_parity_press_modifier(tab, site, playwright_chrome):
    # ukg.py: ControlOrMeta+a then typing replaces what the box held; held Control types nothing
    got = {}
    with both(tab, playwright_chrome, frames_url(site)) as tabs:
        for name, page in tabs.items():
            box = page.locator("#full_name")
            box.fill("old words")
            box.press("ControlOrMeta+a")
            box.press_sequentially("new")
            row = [box.input_value()]
            box.press("Control+j")  # no macOS editing command: types nothing
            box.press("Shift+A")
            row.append(box.input_value())
            got[name] = row
        with pytest.raises(ValueError):
            tabs["window"].locator("#full_name").press("Hyper+a")
    assert got["window"] == got["playwright"]
    assert got["window"][0] == "new"


def test_in_window_parity_check_force(tab, site, playwright_chrome):
    # check / uncheck (force too) inside the same-site frame: a click only where the tick differs
    got = {}
    with both(tab, playwright_chrome, frames_url(site)) as tabs:
        for name, page in tabs.items():
            frame = loaded(page).frames[1]
            frame.evaluate("() => { window.clicks = 0; document.getElementById('weekends').addEventListener('click', () => clicks++); }")
            box, no = frame.locator("#weekends"), frame.locator("[name=relocate]").last
            box.check(force=True)
            box.check(force=True)
            row = [box.is_checked(), frame.evaluate("clicks")]
            box.uncheck(force=True)
            no.check()
            row += [box.is_checked(), frame.evaluate("clicks"), no.is_checked()]
            got[name] = row
    assert got["window"] == got["playwright"] == [True, 1, False, 2, True]


def test_in_window_parity_type_delay(tab, site, playwright_chrome):
    # dom.put_combo's type(delay=): each letter its own key, the list answering as it goes
    got = {}
    with both(tab, playwright_chrome, frames_url(site)) as tabs:
        for name, page in tabs.items():
            frame = loaded(page).frames[1]
            frame.evaluate("() => { window.keys = []; document.getElementById('city').addEventListener('keydown', (e) => keys.push(e.key)); }")
            box = frame.locator("#city")
            box.click()
            start = time.monotonic()
            box.type("Aus", delay=100)
            took = time.monotonic() - start
            got[name] = [box.input_value(), frame.evaluate("keys"), frame.locator("[role=option]").all_inner_texts(), took >= 0.2]
    assert got["window"] == got["playwright"]
    assert got["window"][2] == ["Austin, Texas, United States", "Austin, Minnesota, United States"]


class FakeExtension:
    """Job Finder's window as window.py sees it: opens the holding page (a GET, as its tab would),
    answers attach-form / detach-form in <name>.done, as extension.js does."""

    def __init__(self, root, proxy, attach=None):
        import jobs
        self.dir, self.proxy, self.attach = root / jobs.LINK_DIR, proxy, attach
        self.opened, self.attached, self.detached = [], [], []

    def answer(self, request, answer):
        temp = request.with_suffix(".done.tmp")
        temp.write_text(json.dumps(answer), encoding="utf-8")
        temp.rename(request.with_suffix(".done"))

    def watch(self):
        while not self.done.is_set():
            for request in sorted(self.dir.glob("*.json")) if self.dir.exists() else []:
                taken = request.with_name(request.name + ".taken")
                try:
                    request.rename(taken)
                except OSError:
                    continue
                req = json.loads(taken.read_text(encoding="utf-8"))
                taken.unlink()
                if req.get("do") == window.ATTACH:
                    self.attached.append(req["url"])
                    self.answer(request, self.attach or {"ok": True, "session": "s-1", "proxy": self.proxy})
                elif req.get("do") == window.DETACH:
                    self.detached.append(req["session"])
                    self.answer(request, {"ok": True, "left": 0})
                else:
                    self.opened.append(req["url"])
                    urllib.request.urlopen(req["url"], timeout=5).read()
            self.done.wait(0.01)

    def __enter__(self):
        self.done = threading.Event()
        self.thread = threading.Thread(target=self.watch, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.done.set()
        self.thread.join(5)


def window_setup(tmp_path, monkeypatch, running=True):
    # temp folder: a request in the dev checkout's .data would reach the developer's own window
    monkeypatch.setattr(cfg, "ROOT", tmp_path)
    monkeypatch.setattr(launch, "vscode_running", lambda paths=None: running)


def test_in_window_page_at_attaches_to_its_own_holding_page_and_lets_go(tab, site, tmp_path, monkeypatch):
    window_setup(tmp_path, monkeypatch)
    hooked = []
    with FakeExtension(tmp_path, tab) as ext:
        with window.page_at(site, before_load=hooked.append) as page:
            assert page.url == site
        # the tab picked by a page only this run knows - never the posting's link (may be open twice)
        assert len(ext.opened) == 1 and HOLDING.match(ext.opened[0]) and ext.attached == ext.opened
        assert ext.detached == ["s-1"] and len(hooked) == 1 and isinstance(hooked[0], CDP)
    assert list((tmp_path / ".data" / "open-link").iterdir()) == []


@pytest.mark.parametrize("running, attach, said", [
    (False, None, "not filled: the Job Finder window isn't open"),
    (True, {"error": "untrusted"}, "not filled: the Job Finder window is in Restricted Mode"),
    (True, {"error": "picker"}, "not filled: the window couldn't tell which tab to use"),
    (True, ["ok"], "not filled: the window could not reach the tab"),
])
def test_in_window_page_at_stops_plainly_and_names_the_chrome_way(tmp_path, monkeypatch, running, attach, said):
    window_setup(tmp_path, monkeypatch, running)
    with FakeExtension(tmp_path, {}, attach) as ext, pytest.raises(SystemExit) as stop:
        with window.page_at("https://job-boards.greenhouse.io/acme/jobs/1"):
            pytest.fail("no page without the window's tab")
    assert str(stop.value).startswith(said) and str(stop.value).endswith(window.FALLBACK)
    assert ext.detached == [] and len(ext.attached) == int(running)


def test_in_window_page_at_says_restart_when_the_window_runs_the_old_extension(tmp_path, monkeypatch):
    # old extension = no attach request answered: a plain line + the Chrome way, not a 15 s timeout
    window_setup(tmp_path, monkeypatch)
    monkeypatch.setattr(launch, "window_behind", lambda: True)
    with FakeExtension(tmp_path, {}) as ext, pytest.raises(SystemExit) as stop:
        with window.page_at("https://job-boards.greenhouse.io/acme/jobs/1"):
            pytest.fail("no page from a window on the old extension")
    assert str(stop.value) == f"not filled: {launch.BEHIND} - {window.FALLBACK}. {launch.RESTART_LINE}"
    assert ext.opened == [] and ext.attached == []


def test_in_window_multipage_page_at_in_the_holder_keeps_the_users_tab(tab, site, tmp_path, monkeypatch):
    # a fresh tab is page 1 again: inside the holder the user's own tab comes back - one attach, no let go
    window_setup(tmp_path, monkeypatch)
    monkeypatch.setattr(window.inside, "on", True, raising=False)
    match = lambda url: url.startswith(site)
    with FakeExtension(tmp_path, tab) as ext:
        try:
            with window.page_at(site, match=match) as first:
                first.evaluate("window.mark = 'kept'")
            with window.page_at(site + "?again", match=match) as again:
                assert again is first and again.evaluate("window.mark") == "kept"
            assert len(ext.attached) == 1 and ext.detached == []
            with window.page_at(site, match=lambda url: False) as other:  # another form: a tab of its own
                assert other is not first
            assert len(ext.attached) == 2 and len(window.held) == 2
        finally:
            for held in list(window.held):
                window.drop(held)
        assert sorted(ext.detached) == ["s-1", "s-1"]


def fill_setup(tmp_path, monkeypatch, name):
    from resume import tailor
    folder = tmp_path / "7 - Acme - Analyst"
    questions.save(folder / tailor.JOB_DATA / questions.FILE, {"system": name, "url": "https://jobs.example/1",
                                                               "questions": [ANSWERS[0]]})
    monkeypatch.setattr(form.cfg, "load", lambda: {})
    monkeypatch.setattr(form, "job_dir", lambda config, slug: folder)
    monkeypatch.setattr(form, "resume_for", lambda config, folder: None)

    class System:
        NAME, READY = name, "form"

        def fill(page, q, resume_file):
            return "ok"

        def ids_on_page(page):
            return ["first_name"]

    class Page:
        first = property(lambda self: self)
        locator = lambda self, selector: self
        wait_for = lambda self, timeout: None
        inner_text = lambda self, timeout: ""

    opened = []
    monkeypatch.setattr(form, "system_for", lambda url: System)
    monkeypatch.setattr(form.browser, "page_at", lambda url, match=None: opened.append("chrome") or contextlib.nullcontext(Page()))
    monkeypatch.setattr(window, "page_at", lambda url, match=None: opened.append("window") or contextlib.nullcontext(Page()))
    return opened


def test_in_window_off_by_default_fill_stays_in_chrome(tmp_path, monkeypatch, capsys):
    opened = fill_setup(tmp_path, monkeypatch, "Greenhouse")
    monkeypatch.setattr(form.sys, "argv", ["form.py", "fill", "7"])
    form.main()
    assert opened == ["chrome"]
    assert capsys.readouterr().out.endswith("Chrome is open on the filled form. Nothing is sent until the user clicks Submit.\n")


@pytest.mark.parametrize("name", ["Greenhouse", "Ashby", "Lever", "JazzHR", "Workable", "BambooHR"])
def test_in_window_fills_its_systems_in_the_window_tab(tmp_path, monkeypatch, capsys, name):
    opened = fill_setup(tmp_path, monkeypatch, name)
    monkeypatch.setattr(form.sys, "argv", ["form.py", "fill", "7", "--in-window"])
    form.main()
    out = capsys.readouterr().out
    assert opened == ["window"] and "  [ok] First Name\n" in out
    said = "The Job Finder window shows the filled form. Nothing is sent until the user clicks Submit.\n"
    assert out.endswith(said + (f"note: {window.AT_SUBMIT[name]}\n" if name in ("Lever", "JazzHR", "Workable", "BambooHR") else ""))


def test_in_window_refuses_every_other_system(tmp_path, monkeypatch):
    assert window.SYSTEMS == ("Greenhouse", "Ashby", "Lever", "JazzHR", "Workable", "BambooHR")
    opened = fill_setup(tmp_path, monkeypatch, "SmartRecruiters")
    with pytest.raises(SystemExit) as stop:
        form.fill("7", in_window=True)
    assert str(stop.value) == "in the window: Greenhouse, Ashby, Lever, JazzHR, Workable, BambooHR only for now - run fill without --in-window"
    assert opened == []


# a form over two pages, each its own document on the same site: Next is a plain link the user
# clicks; a `debugger;` line as each page loads + every 100 ms (a held tab must never freeze on it)
MP_PAGE = """<!doctype html><meta charset=utf-8><title>Step {n}</title>
<form><label for="{id}">Question {id}</label><input id="{id}" name="{id}" required>{next}</form>
<script>window.ticks = 0; debugger; setInterval(() => {{ debugger; window.ticks++; }}, 100);</script>"""


@pytest.fixture(scope="module")
def pages_site():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            n = urlsplit(self.path).path.rsplit("/", 1)[-1]
            body = MP_PAGE.format(n=n, id="ab"[int(n) - 1], next='<a id="next" href="/mp/2">Next</a>' if n == "1" else "")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode())

        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


class MultiPage:
    """A multi-page system on pages_site: reads + fills the page the tab shows."""
    NAME, READY, PER_PAGE = "MultiPage", "form", True

    def __init__(self, base):
        self.base = base

    def application_url(self, url):
        return url

    def on_tab(self, url, tab_url):
        return tab_url.startswith(self.base + "/mp/")

    def read(self, page):
        return [questions.question(id, f"Question {id}", "text", True, page=page.evaluate("document.title"))
                for id in self.ids_on_page(page)]

    def ids_on_page(self, page):
        return page.eval_on_selector_all("form input", "els => els.map(e => e.id)")

    def fill(self, page, q, resume_file):
        box = page.locator(f"#{q['id']}")
        if not box.count():
            return f"{questions.LATER} on {q['page']}"
        box.fill(q["answer"])
        return "ok"

    def holds(self, page, q):
        return page.locator(f"#{q['id']}").input_value() == q["answer"]


class JsDebugCDP(CDP):
    """js-debug's proxy: its own session has the debugger on - a `debugger;` line pauses the page unless skipped."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.send("Debugger.enable")


def multipage_run(tmp_path, monkeypatch, capsys, system, name, in_window, user_next):
    """prepare, the user's answers, fill, the user's Next, prepare, answers, fill -> (printed per step, answers file per prepare)."""
    folder = tmp_path / name / "7 - Acme - Analyst"
    saved = folder / ".data" / questions.FILE
    monkeypatch.setattr(form, "job_dir", lambda config, slug: folder)
    outs, files = [], []

    def answer():
        data = questions.load(saved)
        for a in data["questions"]:
            if questions.blank(a.get("answer")):
                a.update(answer="Test Applicant", source=questions.USER_SAID)
        questions.save(saved, data)
    for step in (1, 2):
        form.prepare("7", f"{system.base}/mp/1", in_window=in_window)
        files.append(questions.load(saved))
        answer()
        form.fill("7", in_window=in_window)
        outs.append(capsys.readouterr().out)
        if step == 1:
            user_next()
    return outs, files


def test_in_window_multipage_fills_both_pages_on_one_held_tab_as_playwright_does(tab, playwright_chrome, pages_site, tmp_path,
                                                                                monkeypatch, capsys):
    system = MultiPage(pages_site)
    window_setup(tmp_path, monkeypatch)
    monkeypatch.setattr(form.cfg, "load", lambda: {"resume": {"master": "Resume details.yml"}})
    monkeypatch.setattr(form.schema, "load", lambda path: {"contact": {"name": "Test Applicant", "email": "test@example.com"}})
    monkeypatch.setattr(form, "resume_for", lambda config, folder: None)
    monkeypatch.setattr(form.systems, "for_url", lambda url: system)
    monkeypatch.setattr(form, "system_for", lambda url: system)
    monkeypatch.setattr(form, "SETTLE_MS", 50)
    monkeypatch.setattr(window, "SYSTEMS", window.SYSTEMS + (system.NAME,))
    monkeypatch.setattr(window, "CDP", JsDebugCDP)

    # Chrome: Playwright's tab, the user's own between runs (browser.page_at's match)
    context = playwright_chrome.new_context()
    pw = context.new_page()

    @contextlib.contextmanager
    def chrome_tab(url, match=None):
        if not (match and match(pw.url)):
            pw.goto(url)
        yield pw
    monkeypatch.setattr(form.browser, "page_at", chrome_tab)

    def pw_next():
        pw.click("#next")
        pw.wait_for_url("**/mp/2")
    try:
        chrome = multipage_run(tmp_path, monkeypatch, capsys, system, "chrome", False, pw_next)
        assert pw.input_value("#b") == "Test Applicant"
    finally:
        context.close()

    # the window: one holder attached throughout; the user's Next through a CDP of their own (no debugger)
    state = tmp_path / ".data" / window.HOLD_STATE
    ctl = CDP(**tab)

    def page2():
        try:
            return ctl.evaluate("location.pathname + ' ' + document.readyState", 3) == "/mp/2 complete"
        except (RuntimeError, TimeoutError):
            return False

    def user_next():
        assert ctl.evaluate("document.getElementById('a').value") == "Test Applicant"
        ctl.evaluate("document.getElementById('next').click()")
        deadline = time.monotonic() + 15
        while not page2():
            assert time.monotonic() < deadline, "page 2 never loaded"
            time.sleep(0.1)
    with FakeExtension(tmp_path, tab) as ext:
        holder = threading.Thread(target=window.hold, daemon=True)
        holder.start()
        try:
            deadline = time.monotonic() + 10
            while not state.exists():
                assert time.monotonic() < deadline, "the holder never started"
                time.sleep(0.05)
            inside = multipage_run(tmp_path, monkeypatch, capsys, system, "window", True, user_next)
            assert ctl.evaluate("document.getElementById('b').value") == "Test Applicant"
            # not frozen on page 2's `debugger;` lines: its ticks go on
            ticks = ctl.evaluate("ticks", 5)
            time.sleep(0.5)
            assert ctl.evaluate("ticks", 5) > ticks
            assert len(ext.opened) == 1 and ext.attached == ext.opened and ext.detached == []
        finally:
            window.let_go_all()
            holder.join(10)
            ctl.close()
        assert not holder.is_alive() and not state.exists() and ext.detached == ["s-1"]
    assert "let go of 1 tab(s)" in capsys.readouterr().out

    # same answers files, same reports - the window's lines carry --in-window
    def plain(out):
        return (out.replace(" --in-window", "").replace("The Job Finder window shows", "Chrome is open on")
                .replace(f"{tmp_path}/window/", f"{tmp_path}/chrome/"))
    assert [plain(o) for o in inside[0]] == chrome[0]
    assert inside[1] == chrome[1]
    assert [(q["id"], q["page"]) for q in inside[1][1]["questions"]] == [("a", "Step 1"), ("b", "Step 2")]
    assert "  [ok] Question a\n" in inside[0][0] and "  [ok] Question b\n" in inside[0][1]
    assert "apply-form fill 7 --in-window\n" in inside[0][0]


def test_in_window_multipage_next_steps_keep_in_window(tmp_path, monkeypatch, capsys):
    # the user's Next, then prepare + fill again: still in the window, never Chrome by default
    opened = fill_setup(tmp_path, monkeypatch, "MultiPage")
    system = form.system_for("")
    system.PER_PAGE, system.read = True, lambda page: []
    system.fill = lambda page, q, file: f"{questions.LATER} on Step 2" if q["id"] == "later" else "ok"
    data = questions.load(form.job_dir({}, "7") / ".data" / questions.FILE)
    data["questions"].append({**ANSWERS[0], "id": "later", "title": "Later", "page": "Step 2"})
    questions.save(form.job_dir({}, "7") / ".data" / questions.FILE, data)
    monkeypatch.setattr(form.systems, "tab_match", lambda system, url: lambda tab_url: True)
    monkeypatch.setattr(window, "SYSTEMS", window.SYSTEMS + ("MultiPage",))
    monkeypatch.setattr(window.inside, "on", True, raising=False)
    form.fill("7", in_window=True)
    out = capsys.readouterr().out
    assert opened == ["window"]
    assert ('then: uv run app/jobs.py apply-form prepare 7 "https://jobs.example/1" --in-window, then '
            "uv run app/jobs.py apply-form fill 7 --in-window") in out


@pytest.mark.parametrize("step", ["fill", "prepare"])
def test_in_window_multipage_ukg_refused_plainly(tmp_path, monkeypatch, step):
    # UKG's sign-in lives in Job Finder's Chrome: a window tab would land signed out
    opened = fill_setup(tmp_path, monkeypatch, "UKG")
    monkeypatch.setattr(form.systems, "for_url", lambda url: form.system_for(url))
    monkeypatch.setattr(form.schema, "load", lambda path: {"contact": {}})
    monkeypatch.setattr(form.cfg, "resume_path", lambda config, which: tmp_path / "r.yml")
    with pytest.raises(SystemExit) as stop:
        form.fill("7", in_window=True) if step == "fill" else form.prepare("7", "https://jobs.example/1", in_window=True)
    assert str(stop.value) == f"not in the window: UKG - {window.REFUSED['UKG']}; run {step} without --in-window"
    assert opened == []
