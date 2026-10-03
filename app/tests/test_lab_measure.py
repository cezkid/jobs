"""apply-form measure end to end, offline: throwaway Chrome (headless), canary, block, two loads
of a local page, record written, profile deleted - never reading the user's settings. Own file:
test_lab's headless Chrome holds Playwright's loop for its whole module."""
import json

import pytest

import cfg
from apply import browser, lab

FORM = """<!doctype html><title>Job Application for Tester at Acme Test Co</title>
<meta property="og:site_name" content="Acme Test Co">
<button onclick="document.getElementById('form').hidden = false">Apply</button>
<form id=form hidden>
  <label for=first>First Name *</label><input id=first required>
  <label>Referred by <input name=ref value="Prefilled Acme Recruiter"></label>
  <label>Notes <input id=box-0 name=notes></label>
</form>
<script>
document.querySelector('[name=notes]').id = 'box-' + Math.random().toString(36).slice(2);
fetch('/api/form.json').then(r => r.json());
fetch('/w/track', {method: 'POST', body: 'load'}).catch(() => {});
</script>"""

def test_measure_end_to_end_offline(tmp_path, monkeypatch):
    pytest.importorskip("playwright.sync_api")
    try:
        browser.chrome()
    except SystemExit:
        pytest.skip("Chrome not installed")

    def no_settings(*a, **k):
        raise AssertionError("measure read the user's settings")

    monkeypatch.setattr(cfg, "load", no_settings)
    monkeypatch.setattr(lab, "RUNS", tmp_path / "measure-browser")
    monkeypatch.setattr(lab, "OUT", tmp_path / "measure")
    listener = lab.Listener({"/job.html": ("text/html", FORM), "/api/form.json": ("application/json", '{"fields": ["first"]}')})
    try:
        out = lab.measure(listener.home + "/job.html", ["Apply"], headless=True)
    finally:
        listener.close()
    assert listener.writes == []
    data = json.loads(out.read_text())
    assert data["canary"]["received"] == [] and set(data["canary"]["blocked"]) == lab.KINDS
    assert {c["label"] for c in data["snapshot"]["controls"]} >= {"First Name *", "Notes"}
    assert [c["label"] for c in data["changed_ids"]] == ["Notes"]
    assert [b["method"] for b in data["blocked"]] == ["POST", "POST"]  # /w/track, once per load
    assert any(r["url"].endswith("/api/form.json") and '"fields"' in r["first"] for r in data["json"])
    lines = (tmp_path / "measure" / "tenants.txt").read_text().splitlines()
    assert {"Acme Test Co", "Prefilled Acme Recruiter"} <= set(lines)
    assert not (tmp_path / "measure-browser").exists() or not any((tmp_path / "measure-browser").iterdir())
