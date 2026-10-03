"""apply/lab.py (apply-form measure) offline: canary + block in real headless Chrome against a local
listener, service-worker refusal, refused clicks, tenants.txt, and a whole measure run on a local
page - never reading the user's settings."""
from pathlib import Path

import pytest

from apply import browser, lab

SW_PAGE = """<!doctype html><script>
navigator.serviceWorker.register('/sw.js').then(() => navigator.serviceWorker.ready)
  .then(() => { if (navigator.serviceWorker.controller) window.done = true;
    else navigator.serviceWorker.oncontrollerchange = () => window.done = true; });
</script>"""
SW = "self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));"


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


@pytest.fixture
def page(chrome):
    context = chrome.new_context()
    yield context.new_page()
    context.close()


def test_canary_detects_every_leak_without_block(page):
    # block off -> each kind reaches the listener: the canary can see a leak of every kind
    assert set(lab.canary(page, None)["received"]) == lab.KINDS


def test_canary_block_lets_nothing_through(page):
    block = lab.Block()
    block.install(page)
    got = lab.canary(page, block)
    assert got["received"] == []
    assert set(got["blocked"]) == lab.KINDS
    assert all(b["after"] == "canary" for b in block.log)


def test_service_worker_page_refused(page):
    listener = lab.Listener({"/sw.html": ("text/html", SW_PAGE), "/sw.js": ("text/javascript", SW)})
    try:
        page.goto(listener.home + "/sw.html")
        page.wait_for_function("window.done", timeout=10000)
        with pytest.raises(lab.Refused, match="service worker"):
            lab.check_page(page)
    finally:
        listener.close()


def test_page_without_service_worker_passes(page):
    page.set_content("<p>plain</p>")
    lab.check_page(page)


@pytest.mark.parametrize("text", ["Submit application", "Send", "Save & Continue", "Finish", "Complete profile",
                                  "Sign in", "Signature", "submit"])
def test_refused_clicks(text):
    assert lab.refused([text]) == [text]


@pytest.mark.parametrize("text", ["Apply", "Apply without an Account", "Apply for this job", "I'm interested"])
def test_allowed_clicks(text):
    assert lab.refused([text]) == []


def test_refused_click_stops_before_chrome(monkeypatch):
    monkeypatch.setattr(lab, "throwaway", lambda *a: pytest.fail("Chrome started for a refused click"))
    with pytest.raises(SystemExit, match="refused"):
        lab.measure("https://acme.example/jobs/1", ["Apply", "Submit"])


def test_tenants_append_once(tmp_path):
    path = tmp_path / "measure" / "tenants.txt"
    assert lab.record_tenants(path, ["Acme Test Co", "acme-test", "Acme Test Co"]) == 2
    assert lab.record_tenants(path, ["acme-test", "Prefilled Acme"]) == 1
    assert path.read_text().splitlines() == ["Acme Test Co", "acme-test", "Prefilled Acme"]


def test_tenants_keep_tenant_part_of_link_only():
    snap = {"controls": [{"control": "input", "value": "Acme Recruiter"}, {"control": "input", "value": "No"},
                         {"control": "select", "value": "United States"}]}
    got = lab.tenants("https://job-boards.greenhouse.io/acmetest/jobs/123", ["Acme Test Co"], snap)
    assert got == ["Acme Test Co", "acmetest", "Acme Recruiter"]
    assert lab.tenants("https://acmetest.wd5.myworkdayjobs.com/en-US/Careers/job/1", [], {"controls": []}) == ["acmetest"]


def test_measure_never_uses_the_application_window():
    src = (Path(lab.__file__)).read_text()
    assert "apply-browser" not in src.replace("never `.data/apply-browser`", "")
    assert "browser.PROFILE" not in src and "page_at" not in src and "open_tab" not in src
