"""measure.py raw's pure parts (app/docs/apply/vscode-browser/rawkit.py, plan-k8n.1): the ready test reads every
system's READY as Playwright does (':visible', open shadow roots) on local pages; one EXAMPLES link per system
scrubs to no tenant / host part; raw's tenant lines reach tenants.txt. No live page."""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

import pytest

import cfg
from apply import browser, lab, systems
from apply.systems import icims, oracle, paylocity, smartrecruiters

sys.path.insert(0, str(cfg.APP / "docs" / "apply" / "vscode-browser"))
import rawkit  # noqa: E402

MODULES = [s for s in systems.SYSTEMS if hasattr(s, "EXAMPLES")]
# every system's READY + one box of each kind it must or mustn't count
PAGE = """<!doctype html><body>
<form id="form_submit_new_resume"><input id="first_name"><input type="hidden" name="h"><input id="gone" style="display:none">
<input id="ghost" style="visibility:hidden"><select id="pick"><option>a</option></select><textarea></textarea>
<input name="firstname"><input id="firstName"><div class="form-group"><input></div>
<div data-field-path="x"><input></div><div id="application-form"><input name="name"></div>
<input data-automation="first-name-textbox"></form>
<div id="app"><form><input id="field101"></form></div>
<div id="host"></div><div id="closed"></div>
<script>
const open = document.getElementById('host').attachShadow({mode: 'open'});
open.innerHTML = '<div id="inner"></div>';
open.getElementById('inner').attachShadow({mode: 'open'}).innerHTML = '<input id="first-name-input">';
document.getElementById('closed').attachShadow({mode: 'closed'}).innerHTML = '<input id="sealed">';
</script></body>"""


@pytest.fixture(scope="module")
def page():
    pw = pytest.importorskip("playwright.sync_api")
    try:
        exe = browser.chrome()
    except SystemExit:
        pytest.skip("Chrome not installed")
    with pw.sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe, headless=True)
        pg = b.new_page()
        pg.route("**/*", lambda route: route.abort())  # nothing reaches the network
        pg.set_content(PAGE)
        yield pg
        b.close()


def test_ready_splits_at_top_level_commas_and_lifts_visible():
    assert rawkit.ready_parts(oracle.READY) == [("input:not([type=hidden])", True), ("select", True), ("textarea", True)]
    assert rawkit.ready_parts(icims.READY)[0] == ("iframe[src*='in_iframe=1']", False)
    assert rawkit.ready_parts("a[title='x, y:visible'], b") == [("a[title='x, y:visible']", False), ("b", False)]
    with pytest.raises(ValueError):
        rawkit.ready_parts("div:visible input")


def test_ready_check_counts_as_playwright_does_for_every_system(page):
    """':visible' (Oracle, iCIMS, ADP) no longer throws; SmartRecruiters' box two shadow roots deep is found;
    hidden, display:none and visibility:hidden boxes drop out where ':visible' asks."""
    for system in MODULES:
        got = page.evaluate(rawkit.count_js(system.READY))
        assert got == page.locator(system.READY).count(), system.NAME
        assert got > 0 and page.evaluate(rawkit.ready_js(system.READY)) is True, system.NAME
    assert page.evaluate(rawkit.count_js(smartrecruiters.READY)) == 1
    assert page.evaluate(rawkit.count_js("#first-name-input:visible")) == 1
    assert page.evaluate(rawkit.count_js("#gone:visible, #ghost:visible, #sealed")) == 0
    assert page.evaluate(rawkit.count_js("#gone, #ghost")) == 2
    with pytest.raises(Exception):  # the old test, for the record: it threw on these
        page.evaluate(f"!!document.querySelector({json.dumps(oracle.READY)})")
    assert page.evaluate(f"!!document.querySelector({json.dumps(smartrecruiters.READY)})") is False


def shared(host: str) -> bool:
    return bool(rawkit.SHARED_HOST.fullmatch(host))


@pytest.mark.parametrize("system", MODULES, ids=lambda s: s.NAME)
def test_one_example_per_system_scrubs_to_no_tenant_or_host_part(system):
    """Every EXAMPLES link names tenant acme somewhere (host, path, query, key); after the scrub no acme,
    no tenant host and no parse_url part is left - in the shapes raw saves (url, at, short, nested)."""
    url = system.EXAMPLES[-1]
    app = system.application_url(url)
    pairs = rawkit.scrub_pairs(system, url, app)
    parts = [str(p) for p in system.parse_url(url)] + [str(p) for p in system.parse_url(app)]
    hosts = {urlsplit(u).hostname for u in (url, app)}
    saved = {"url": app, "posting": url, "at": urlsplit(app).hostname + urlsplit(app).path,
             "block": {"failed": [{"url": f"https://{urlsplit(app).hostname}{urlsplit(app).path}", "after": "load"}]},
             "readyMs": 1012345, "level": 3, "system": system.NAME}
    out = json.dumps(rawkit.scrub_values(saved, pairs))
    assert "acme" not in out.casefold(), (system.NAME, out)
    for h in hosts:
        assert shared(h) == (h in out), (system.NAME, h)
    for p in parts:
        if p not in ("", "eu.", ".eu") and not shared(p):  # Greenhouse + Lever's EU host suffix: no tenant
            assert not re.search(rf"(?<!\d){re.escape(p)}(?!\d)", out, re.I), (system.NAME, p)
    back = json.loads(out)
    assert set(back) == set(saved) and back["readyMs"] == 1012345 and back["system"] == system.NAME


def test_paylocity_one_part_and_a_tenant_in_the_query():
    url = paylocity.EXAMPLES[0]
    assert len(paylocity.parse_url(url)) == 1
    out = rawkit.scrub(f"{url} {paylocity.application_url(url)}", rawkit.scrub_pairs(paylocity, url, paylocity.application_url(url)))
    assert "acme" not in out and "1000001" not in out and "recruiting.paylocity.com" in out


def test_scrub_keeps_keys_numbers_and_placeholders():
    pairs = rawkit.scrub_pairs(icims, "https://careers-acme.icims.com/jobs/101/test-job/job")
    out = rawkit.scrub_values({"acme": "careers-acme.icims.com ACME 101 1012 <org>"}, pairs)
    assert out == {"acme": "<host> <org> <id> 1012 <org>"}


def test_raw_appends_tenant_lines_once(tmp_path):
    """raw's lines: org, tenant host + labels, Oracle's site, the employer's names; never an id, a slug, a
    platform's own name or page chrome. Appended as lab.py's measure appends, no line twice."""
    url = oracle.EXAMPLES[2]
    lines = rawkit.tenant_lines(oracle, [url, oracle.application_url(url)], ["Acme Corp", "BambooHR", "Login"])
    assert {"Acme Corp", "acme", "acme.fa.ocs.oraclecloud.com", "AcmeCareers"} <= set(lines)
    assert not {"678", "BambooHR", "Login", "oraclecloud", "hcmUI"} & set(lines)
    slugged = rawkit.tenant_lines(icims, [icims.EXAMPLES[0]])
    assert "careers-acme" in slugged and "careers-acme.icims.com" in slugged and "test-job" not in slugged
    tenants = tmp_path / ".data" / "measure" / "tenants.txt"
    tenants.parent.mkdir(parents=True)
    tenants.write_text("acme\n")
    assert lab.record_tenants(tenants, lines) == len(lines) - 1
    assert lab.record_tenants(tenants, lines) == 0
    assert tenants.read_text().splitlines().count("acme") == 1
    for system in MODULES:  # every system yields a line to grep for
        url = system.EXAMPLES[0]
        assert any("acme" in s.casefold() for s in rawkit.tenant_lines(system, [url, system.application_url(url)])) \
            or system is paylocity, system.NAME


def test_measure_raw_uses_rawkit():
    """measure.py raw reads READY, scrubs and records tenants only through rawkit (it can't be imported: argv)."""
    src = (cfg.APP / "docs" / "apply" / "vscode-browser" / "measure.py").read_text()
    raw = src[src.index("def raw(result):"):src.index("def restricted(result):")]
    assert "rawkit.ready_js(system.READY)" in raw and "rawkit.count_js(system.READY)" in raw
    assert "rawkit.scrub_pairs(system, GH_URL, app_url)" in raw and raw.count("lab.record_tenants(TENANTS") == 3
    # where the page landed (a short link moves to the employer's own path) scrubbed + recorded the same way
    assert "rawkit.scrub_pairs(system, landed)" in raw and "rawkit.tenant_lines(system, [landed])" in raw
    assert "document.querySelector({json.dumps(system.READY)" not in src and "parse_url(GH_URL)[-2:]" not in src
