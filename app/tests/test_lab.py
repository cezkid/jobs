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
    assert lab.tenants("https://jobs.dayforcehcm.com/en-US/acmetest/candidateportal/jobs/1/apply", [],
                       {"controls": []}) == ["acmetest"]


def test_tenants_smartrecruiters_oneclick_link_and_generic_names():
    uuid = "0a1b2c3d-4e5f-6789-abcd-ef0123456789"
    url = f"https://jobs.smartrecruiters.com/oneclick-ui/company/AcmeTest/publication/{uuid}"
    got = lab.tenants(url, ["SmartRecruiters", "Acme Test Co"], {"controls": []})
    assert got == ["Acme Test Co", "AcmeTest", uuid]
    assert lab.tenants("https://jobs.smartrecruiters.com/AcmeTest/1234-analyst", [], {"controls": []}) == ["AcmeTest"]
    # ADP: every employer shares host + path, the employer is only the cid (2026-10-03)
    assert lab.tenants("https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=x", [], {"controls": []}) == []
    # Oracle: the path's first part is Oracle's own app on every employer (2026-10-03); the pod names the employer
    assert lab.tenants("https://acme.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX/job/1", [], {"controls": []}) == ["acme"]
    # iCIMS: a "Login" title + a "Next" submit input are page chrome - they'd hit every "next" in the code
    snap = {"controls": [{"control": "input", "type": "submit", "value": "Next"}]}
    assert lab.tenants("https://careers-acme.icims.com/jobs/1/x/login", ["Login", "Loading..."], snap) == ["careers-acme"]


def test_measure_never_uses_the_application_window():
    src = (Path(lab.__file__)).read_text()
    assert "apply-browser" not in src.replace("never `.data/apply-browser`", "")
    assert "browser.PROFILE" not in src and "page_at" not in src and "open_tab" not in src


def test_tenants_leave_out_platform_site_name():
    assert lab.tenants("https://acmetest.bamboohr.com/careers/1", ["BambooHR", "Acme Test Co"], {"controls": []}) \
        == ["Acme Test Co", "acmetest"]


# the one named exception (owner OK 2026-10-05): Ashby's question read passes, nothing else does
ASHBY = "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobPosting"
READ_VARS = {"organizationHostedJobsPageName": "acme", "jobPostingId": "00000000-0000-0000-0000-000000000000"}


def ashby_body(query="query ApiJobPosting($a: String!) { jobPosting { title } }", op="ApiJobPosting", variables=None, **extra):
    import json
    return json.dumps({"operationName": op, "query": query, "variables": READ_VARS if variables is None else variables} | extra)


@pytest.mark.parametrize("url", [ASHBY, "https://jobs.ashbyhq.com/acme/non-user-graphql?op=ApiJobPosting",
                                 "https://jobs.ashbyhq.com/api/non-user-graphql"])
def test_named_read_passes(url):
    assert lab.named_read("POST", url, ashby_body()) == "ApiJobPosting"
    frag = "query ApiJobPosting { jobPosting { ...F } } fragment F on JobPosting { title }"
    assert lab.named_read("POST", url, ashby_body(frag)) == "ApiJobPosting"


@pytest.mark.parametrize("method, url, body", [
    # a mutation carrying the read's name, or hiding beside it in the same text
    ("POST", ASHBY, ashby_body("mutation ApiJobPosting { submit(x: 1) { ok } }")),
    ("POST", ASHBY, ashby_body("query ApiJobPosting { a } mutation ApiJobPosting2 { submit { ok } }")),
    ("POST", ASHBY, ashby_body("subscription ApiJobPosting { a }")),
    ("POST", ASHBY, ashby_body(" { a }")),
    # another operation, or the name in the link not the body's
    ("POST", "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiApplicationFormSubmit",
     ashby_body("query ApiApplicationFormSubmit { a }", op="ApiApplicationFormSubmit")),
    ("POST", "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiOrganizationFromHostedJobsPageName", ashby_body()),
    # typed text riding along: an extra variable, a non-string one, an extra top-level key
    ("POST", ASHBY, ashby_body(variables=READ_VARS | {"email": "test@example.com"})),
    ("POST", ASHBY, ashby_body(variables={**READ_VARS, "jobPostingId": {"x": 1}})),
    ("POST", ASHBY, ashby_body(extensions={"x": 1})),
    # batched, not JSON, no body
    ("POST", ASHBY, "[" + ashby_body() + "]"),
    ("POST", ASHBY, "operationName=ApiJobPosting"),
    ("POST", ASHBY, None),
    # another host, path, scheme or method
    ("POST", "https://jobs.lever.co/api/non-user-graphql?op=ApiJobPosting", ashby_body()),
    ("POST", "https://evil.example/api/non-user-graphql?op=ApiJobPosting", ashby_body()),
    ("POST", "https://jobs.ashbyhq.com/api/graphql?op=ApiJobPosting", ashby_body()),
    ("POST", "http://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobPosting", ashby_body()),
    ("PUT", ASHBY, ashby_body()),
])
def test_named_read_refuses(method, url, body):
    assert lab.named_read(method, url, body) is None


class FakeRoute:
    def __init__(self, method, url, body):
        self.request = type("R", (), {"method": method, "url": url, "post_data": body, "resource_type": "fetch"})()
        self.done = None

    def continue_(self):
        self.done = "continued"

    def abort(self):
        self.done = "aborted"


def test_block_passes_named_read_and_aborts_its_mutation():
    block = lab.Block()
    read, write = FakeRoute("POST", ASHBY, ashby_body()), \
        FakeRoute("POST", ASHBY, ashby_body("mutation ApiJobPosting { submit { ok } }"))
    block.request(read)
    block.request(write)
    assert (read.done, write.done) == ("continued", "aborted")
    assert [p["op"] for p in block.passed] == ["ApiJobPosting"]
    assert [b["url"] for b in block.log] == [ASHBY]


def test_block_aborts_binary_body():
    # Ashby's closed page, 2026-10-05: a gzipped beacon - post_data raised inside the route handler
    class Binary(FakeRoute):
        def __init__(self):
            super().__init__("POST", ASHBY, None)
            type(self.request).post_data = property(lambda r: b"\x9c".decode())
    block, route = lab.Block(), Binary()
    block.request(route)
    assert route.done == "aborted" and [b["url"] for b in block.log] == [ASHBY] and block.passed == []


def test_canary_still_blocks_every_kind_with_named_reads(page):
    # the exception never widens the block for anything the canary sends
    block = lab.Block()
    block.install(page)
    got = lab.canary(page, block)
    assert got["received"] == [] and set(got["blocked"]) == lab.KINDS and block.passed == []
    # Manatal + Rippling: one host for every employer, site name = the platform's (2026-10-06)
    assert lab.tenants("https://www.careers-page.com/acmetest/job/AB12CD/apply", ["Manatal", "Acme Test Co"],
                       {"controls": []}) == ["Acme Test Co", "acmetest"]
    assert lab.tenants("https://ats.rippling.com/acmetest/jobs/1", ["Rippling Recruiting"], {"controls": []}) == ["acmetest"]
    # Breezy + Teamtailor: employer = host label; platform names + a "people." careers host are not names (2026-10-07)
    assert lab.tenants("https://acmetest.breezy.hr/p/ab12-dev/apply", ["Breezy HR"], {"controls": []}) == ["acmetest"]
    assert lab.tenants("https://acmetest.na.teamtailor.com/jobs/1-dev/applications/new", ["Teamtailor"],
                       {"controls": []}) == ["acmetest"]
    assert lab.tenants("https://people.acmetest.com/jobs/1-dev/applications/new", [], {"controls": []}) == ["acmetest"]
