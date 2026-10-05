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
from apply import browser, form, questions, window
from apply.cdp import CDP
from apply.systems import ashby, greenhouse, lever

FORM = Path(__file__).parent / "fixtures" / "dom" / "greenhouse-form.html"
ASHBY_FORM = FORM.with_name("ashby-form.html")
ASHBY_PATH = "/acme/45bdb7e5-14a8-494f-8fcb-30e42f0be67a/application"
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
                page = {"/acme/jobs/1": FORM, ASHBY_PATH: ASHBY_FORM}.get(self.path)
                body, kind = (page.read_bytes() if page else None), "text/html; charset=utf-8"
                if self.path == LEVER_PATH:
                    body = ("<!doctype html><html><head><meta charset=utf-8><title>Apply - Acme</title></head><body>"
                            f"{LEVER_FORM.read_text()}{LEVER_BEHAVES}</body></html>").encode()
            with contextlib.suppress(OSError):  # the tab moved on while it waited
                self.send_response(200 if body else 404)
                self.send_header("Content-Type", kind)
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


@pytest.mark.parametrize("name", ["Greenhouse", "Ashby", "Lever"])
def test_in_window_fills_its_systems_in_the_window_tab(tmp_path, monkeypatch, capsys, name):
    opened = fill_setup(tmp_path, monkeypatch, name)
    monkeypatch.setattr(form.sys, "argv", ["form.py", "fill", "7", "--in-window"])
    form.main()
    out = capsys.readouterr().out
    assert opened == ["window"] and "  [ok] First Name\n" in out
    said = "The Job Finder window shows the filled form. Nothing is sent until the user clicks Submit.\n"
    assert out.endswith(said + (f"note: {window.AT_SUBMIT[name]}\n" if name == "Lever" else ""))


def test_in_window_refuses_every_other_system(tmp_path, monkeypatch):
    assert window.SYSTEMS == ("Greenhouse", "Ashby", "Lever")
    opened = fill_setup(tmp_path, monkeypatch, "Workable")
    with pytest.raises(SystemExit) as stop:
        form.fill("7", in_window=True)
    assert str(stop.value) == "in the window: Greenhouse, Ashby, Lever only for now - run fill without --in-window"
    assert opened == []
