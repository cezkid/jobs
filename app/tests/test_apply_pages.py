"""Forms spread over pages (start box, then the form; "Step 1 of 5"): fill works on the user's own
tab, fills what this page shows, LATER for the rest; prepare reads page by page and merges."""
import contextlib
import importlib
import inspect
import pkgutil

import pytest

from apply import browser, form, questions, systems
from apply.systems import ashby, ukg
from resume import tailor

CONTACT = {"name": "Test Applicant", "email": "test@example.com", "phone": "555-0100"}
URL = "https://jobs.example/acme/apply/1"


def q(id, page, answer=None, required=True):
    return {**questions.question(id, f"Question {id}", "text", required, page=page), "answer": answer,
            "source": "you said" if answer else questions.ASK}


class Page:
    """The tab: which step of the form it shows."""
    first = property(lambda self: self)

    def __init__(self, step):
        self.step = step

    def locator(self, selector):
        return self

    def wait_for(self, timeout):
        pass

    def inner_text(self, timeout):
        return ""

    def wait_for_timeout(self, ms):
        pass


class TwoPages:
    """A multi-page system: a box shows only on its own step."""
    NAME, READY, PER_PAGE = "Fake", "form", True

    def __init__(self, qs):
        self.page_of = {x["id"]: x["page"] for x in qs}
        self.filled = []

    def fill(self, page, q, resume_file):
        if self.page_of[q["id"]] != page.step:
            return f"{questions.LATER} on {self.page_of[q['id']]}"
        self.filled.append(q["id"])
        return "ok"

    def ids_on_page(self, page):
        return [id for id, step in self.page_of.items() if step == page.step]

    def on_tab(self, url, tab_url):
        return tab_url == url


@pytest.fixture
def job(tmp_path, monkeypatch):
    folder = tmp_path / "7 - Acme - Analyst"
    monkeypatch.setattr(form.cfg, "load", lambda: {"resume": {"master": "Resume details.yml"}})
    monkeypatch.setattr(form.schema, "load", lambda path: {"contact": CONTACT})
    monkeypatch.setattr(form, "job_dir", lambda config, slug: folder)
    monkeypatch.setattr(form, "resume_for", lambda config, folder: None)
    tabs = []

    def run(system, qs, step):
        questions.save(folder / tailor.JOB_DATA / questions.FILE, {"system": "Fake", "url": URL, "questions": qs})
        monkeypatch.setattr(form, "system_for", lambda url: system)

        def page_at(url, match=None):
            tabs.append(match)
            return contextlib.nullcontext(Page(step))
        monkeypatch.setattr(form.browser, "page_at", page_at)
        form.fill("7")
    run.tabs = tabs
    return run


def test_two_page_form_fills_this_page_and_leaves_the_rest_for_later(job, capsys):
    qs = [q("a", "Step 1", "x"), q("b", "Step 2", "y")]
    system = TwoPages(qs)
    job(system, qs, "Step 1")
    out = capsys.readouterr().out
    assert "  [ok] Question a\n" in out and "Question b" not in out.split("this page:")[0]
    assert "this page: 1 of 1 required answered\n" in out
    assert "1 question(s) on other pages - the user checks this page and clicks Next / Continue themselves (never us)" in out
    assert "FAIL" not in out
    job(system, qs, "Step 2")  # the user clicked Next themselves
    out = capsys.readouterr().out
    assert "  [ok] Question b\n" in out and "  [" not in out.replace("  [ok] Question b", "")
    assert "this page: 1 of 1 required answered" in out
    assert system.filled == ["a", "b"]


def test_fill_attaches_to_the_users_tab_on_a_multi_page_form(job):
    qs = [q("a", "Step 1", "x")]
    job(TwoPages(qs), qs, "Step 1")
    match = job.tabs[-1]
    assert match(URL) and not match("https://jobs.example/other/apply/2")


def test_tab_closed_new_tab_is_page_one_and_its_boxes_are_filled_again(job, capsys):
    qs = [q("a", "Step 1", "x"), q("b", "Step 2", "y")]
    system = TwoPages(qs)
    job(system, qs, "Step 1")
    job(system, qs, "Step 1")  # the user closed the tab: page_at opened a fresh one on step 1
    assert system.filled == ["a", "a"]
    assert capsys.readouterr().out.count("  [ok] Question a") == 2


def test_blank_required_question_on_another_page_does_not_block_this_page(job, capsys):
    qs = [q("a", "Step 1", "x"), q("b", "Step 2")]
    system = TwoPages(qs)
    job(system, qs, "Step 1")
    out = capsys.readouterr().out
    assert system.filled == ["a"]
    assert "still blank there: Question b" in out
    with pytest.raises(SystemExit, match="required questions on this page still blank: Question b"):
        job(system, qs, "Step 2")


def test_single_page_system_keeps_a_fresh_tab_and_blocks_on_any_blank_before_opening(job):
    class OnePage:
        NAME, READY = "Fake", "form"
        fill = staticmethod(lambda page, q, resume_file: "ok")
        ids_on_page = staticmethod(lambda page: ["a"])
    job(OnePage, [q("a", None, "x")], None)
    assert job.tabs == [None]
    with pytest.raises(SystemExit, match="required questions still blank: Question b"):
        job(OnePage, [q("a", None, "x"), q("b", None)], None)
    assert job.tabs == [None]  # never opened


def test_recheck_skips_answers_left_for_later():
    read = []

    class System:
        def holds(self, page, q):
            read.append(q["id"])
            return True
    qs = [q("a", "Step 1", "x"), q("b", "Step 2", "y")]
    report = [("a", "ok"), ("b", f"{questions.LATER} on Step 2")]
    assert form.recheck(Page("Step 1"), System(), qs, report, None) == report
    assert read == ["a"]


def test_merge_keeps_other_pages_replaces_this_page_appends_a_new_one():
    old = [q("a", "Step 1", "kept"), q("b", "Step 2", "old"), q("c", "Step 2"), q("d", "Step 3", "kept")]
    step2 = [q("b", "Step 2", "new"), q("e", "Step 2")]
    assert [(x["id"], x["answer"]) for x in questions.merge(old, step2)] == \
        [("a", "kept"), ("b", "new"), ("e", None), ("d", "kept")]
    step4 = [q("f", "Step 4")]
    assert [x["id"] for x in questions.merge(old, step4)] == ["a", "b", "c", "d", "f"]
    # read all at once (no page): the whole list replaced
    assert [x["id"] for x in questions.merge(old, [q("z", None)])] == ["z"]


def test_prepare_reads_the_page_the_user_is_on_and_merges_it(tmp_path, monkeypatch, job):
    folder = tmp_path / "7 - Acme - Analyst"
    saved = folder / tailor.JOB_DATA / questions.FILE
    questions.save(saved, {"system": "Fake", "url": URL, "questions": [q("a", "Step 1", "my words")]})
    tabs = []

    class Reads:
        NAME = "Fake"
        application_url = staticmethod(lambda url: URL)
        on_tab = staticmethod(lambda url, tab_url: tab_url == URL)

        def read(page):
            return [questions.question("b", "Question b", "text", True, page=page.step)]
    monkeypatch.setattr(form.systems, "for_url", lambda url: Reads)

    def page_at(url, match=None):
        tabs.append(match)
        return contextlib.nullcontext(Page("Step 2"))
    monkeypatch.setattr(form.browser, "page_at", page_at)
    form.prepare("7", URL)
    got = questions.load(saved)["questions"]
    assert [(x["id"], x["page"], x["answer"]) for x in got] == [("a", "Step 1", "my words"), ("b", "Step 2", None)]
    assert tabs[0](URL)


def test_ukg_reads_the_form_off_the_open_tab_or_stops_at_sign_in():
    class Signed(Page):
        def __init__(self, signin):
            self.signin = signin

        def evaluate(self, js):
            return {"signin": self.signin, "fields": [], "questions": [], "eeo": [], "upload": True}
    assert [x["id"] for x in ukg.read(Signed(False))] == ["resume", ukg.PROFILE]
    assert all("page" not in x for x in ukg.read(Signed(False)))  # one page: replaces the whole list
    with pytest.raises(SystemExit, match="only after sign-in"):
        ukg.read(Signed(True))


@pytest.mark.parametrize("module", [m.name for m in pkgutil.iter_modules(systems.__path__)])
def test_optional_page_members_keep_their_shape(module):
    system = importlib.import_module(f"apply.systems.{module}")
    for name, want in {"read": 1, "on_tab": 2}.items():
        if hasattr(system, name):
            assert len(inspect.signature(getattr(system, name)).parameters) == want, name


# --- the tab: the user's own, or a new one picked by its target id ---

class Tab:
    def __init__(self, url, shown=False, target=""):
        self.url, self.shown, self.target = url, shown, target
        self.fronted = False

    def evaluate(self, js):
        return "visible" if self.shown else "hidden"

    def wait_for_load_state(self):
        pass

    def bring_to_front(self):
        self.fronted = True


POSTING = "https://jobs.ashbyhq.com/acme/45bdb7e5-14a8-494f-8fcb-30e42f0be67a"


def test_default_tab_match_needs_same_host_and_posting():
    match = systems.tab_match(ashby, POSTING)
    assert match(POSTING + "/application?step=2")
    assert not match("https://jobs.ashbyhq.com/acme/11111111-2222-3333-4444-555555555555/application")
    assert not match("https://evil.example/?u=" + POSTING)


def test_pick_prefers_the_visible_matching_tab_never_another_host():
    match = systems.tab_match(ashby, POSTING)
    front, back = Tab(POSTING + "/application", shown=True), Tab(POSTING + "/application")
    other = Tab("https://jobs.example/" + POSTING.rsplit("/", 1)[1], shown=True)
    assert browser.pick([front, back, other], match) is front
    assert browser.pick([back, other], match) is back
    assert browser.pick([other], match) is None


def fake_playwright(monkeypatch, tabs):
    import playwright.sync_api

    class Chromium:
        def connect_over_cdp(self, endpoint):
            return type("B", (), {"contexts": [type("C", (), {"pages": tabs})()]})()

    @contextlib.contextmanager
    def sync_playwright():
        yield type("P", (), {"chromium": Chromium()})()
    monkeypatch.setattr(playwright.sync_api, "sync_playwright", sync_playwright)
    monkeypatch.setattr(browser, "target_id", lambda page: page.target)
    monkeypatch.setattr(browser, "live_port", lambda: 9222)


def test_page_at_reuses_the_users_tab_without_opening_one(monkeypatch):
    mine = Tab(POSTING + "/application", shown=True)
    fake_playwright(monkeypatch, [mine, Tab("https://jobs.example/x", shown=True)])
    monkeypatch.setattr(browser, "open_tab", lambda url: pytest.fail("opened a new tab"))
    with browser.page_at(POSTING, match=systems.tab_match(ashby, POSTING)) as page:
        assert page is mine and mine.fronted


def test_new_tab_is_the_one_chrome_opened_by_target_id_not_the_newest(monkeypatch):
    ours = Tab("https://jobs.example/redirected", target="T2")
    newest = Tab("https://jobs.example/another-employer", target="T3")  # opened since, e.g. by a redirect
    fake_playwright(monkeypatch, [Tab("about:blank", target="T1"), ours, newest])
    monkeypatch.setattr(browser, "open_tab", lambda url: (9222, "T2"))
    with browser.page_at(POSTING, match=systems.tab_match(ashby, POSTING)) as page:
        assert page is ours
    with browser.page_at(POSTING) as page:  # single-page systems: always a new tab
        assert page is ours


def test_just_started_chrome_takes_its_only_tab_else_opens_its_own(monkeypatch):
    listed = []
    monkeypatch.setattr(browser.httpx, "get", lambda url, timeout: type("R", (), {"json": lambda self: listed})())
    monkeypatch.setattr(browser, "new_tab", lambda port, url: "NEW")
    listed[:] = [{"id": "A", "type": "page"}, {"id": "W", "type": "service_worker"}]
    assert browser.first_tab(9222, POSTING) == "A"
    listed[:] = [{"id": "A", "type": "page"}, {"id": "B", "type": "page"}]  # restored tabs beside it
    assert browser.first_tab(9222, POSTING) == "NEW"
