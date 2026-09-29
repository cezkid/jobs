import json
import sys

import pytest

import status
import store
from conftest import make_job
from resume import tailor

NOW = "2026-09-29T12:00:00Z"
LATER = "2026-09-30T09:00:00Z"
PASTED_URL = "https://jobs.lever.co/globex/123"


def make_folder(jobs_dir, name, url, company, title, slug, made=True):
    d = jobs_dir / name
    (d / tailor.JOB_DATA).mkdir(parents=True)
    (d / tailor.JOB_DATA / "jd.json").write_text(json.dumps(
        {"public_slug": slug, "company": company, "title": title, "url": url}), encoding="utf-8")
    if made:
        (d / tailor.CHECK_FILE).write_text(f"# {title} - {company}\n\n- Link: {url}\n- Posted on: pasted\n",
                                           encoding="utf-8")
    return d


def test_state_words_the_user_says():
    assert status.state_key("resume made") == "resume_made"
    assert status.state_key("Heard-back") == "heard_back"
    assert status.state_key("They said no") == "no"
    assert status.state_key("not_sending") == "not_sending"
    with pytest.raises(ValueError):
        status.state_key("ghosted")


def test_listed_job_by_slug_and_link(conn, tmp_path):
    store.upsert(conn, [make_job("a")], NOW)
    job = status.resolve(conn, tmp_path, "a")
    assert job["key"] == "https://boards.greenhouse.io/acme/jobs/a"
    status.set_state(conn, job, "applied", NOW)
    by_link = status.resolve(conn, tmp_path, "https://boards.greenhouse.io/acme/jobs/a")
    assert status.get(conn, by_link["key"])["state"] == "applied"
    assert status.get(conn, by_link["key"])["public_slug"] == "a"


def test_pasted_posting_by_link_slug_or_folder(conn, tmp_path):
    make_folder(tmp_path, "Globex - Data Analyst", PASTED_URL, "Globex", "Data Analyst", "globex-data-analyst")
    for ref in (PASTED_URL, "globex-data-analyst", "Globex - Data Analyst"):
        job = status.resolve(conn, tmp_path, ref)
        assert (job["key"], job["company"], job["title"]) == (PASTED_URL, "Globex", "Data Analyst")
    status.set_state(conn, status.resolve(conn, tmp_path, PASTED_URL), "interview", NOW)
    job = status.resolve(conn, tmp_path, company="globex", title="data  analyst")
    assert status.get(conn, job["key"])["state"] == "interview"


def test_outside_job_by_company_and_title(conn, tmp_path):
    job = status.resolve(conn, tmp_path, company="Initech", title="Analyst")
    assert job["key"] == "outside:initech|analyst" and job["url"] is None
    status.set_state(conn, job, "applied", "2026-09-20T12:00:00Z")
    again = status.resolve(conn, tmp_path, company="INITECH", title="analyst")
    status.set_state(conn, again, "heard_back", NOW)
    rows = status.all_statuses(conn)
    assert [(r["company"], r["state"]) for r in rows] == [("Initech", "heard_back")]
    log = conn.execute("SELECT state FROM application_log WHERE key = ? ORDER BY at", (job["key"],)).fetchall()
    assert [r["state"] for r in log] == ["applied", "heard_back"]


def test_outside_job_with_link_needs_company_and_title(conn, tmp_path):
    with pytest.raises(status.NotFound):
        status.resolve(conn, tmp_path, "https://careers.initech.com/9")
    job = status.resolve(conn, tmp_path, company="Initech", title="Analyst", url="https://careers.initech.com/9")
    status.set_state(conn, job, "applied", NOW)
    assert status.resolve(conn, tmp_path, "https://careers.initech.com/9")["title"] == "Analyst"


def test_job_number_names_the_same_job_as_on_the_list(conn, tmp_path):
    store.upsert(conn, [make_job("a")], NOW)
    make_folder(tmp_path, "Globex - Data Analyst", PASTED_URL, "Globex", "Data Analyst", "g-da")
    listed, pasted = store.number(conn, "a"), store.number(conn, "g-da")
    assert status.resolve(conn, tmp_path, f"job {listed}")["key"] == status.resolve(conn, tmp_path, "a")["key"]
    assert status.resolve(conn, tmp_path, f"#{pasted}")["key"] == PASTED_URL
    with pytest.raises(status.NotFound, match="job 99"):
        status.resolve(conn, tmp_path, "99")


def test_outside_job_gets_a_number_too(conn, tmp_path):
    job = status.resolve(conn, tmp_path, company="Initech", title="Analyst")
    status.set_state(conn, job, "applied", NOW)
    [row] = status.numbered(conn, status.all_statuses(conn))
    assert status.line(row).startswith(f"#{row['num']} ")
    assert status.resolve(conn, tmp_path, str(row["num"]))["key"] == job["key"]


def test_unknown_job_name_is_not_found(conn, tmp_path):
    with pytest.raises(status.NotFound):
        status.resolve(conn, tmp_path, "no-such-slug")
    with pytest.raises(status.NotFound):
        status.resolve(conn, tmp_path)


def test_backfill_existing_folders_read_only(conn, tmp_path):
    made = make_folder(tmp_path, "Globex - Data Analyst", PASTED_URL, "Globex", "Data Analyst", "globex-data-analyst")
    make_folder(tmp_path, "Acme - Engineer", "https://acme.com/j/1", "Acme", "Engineer", "acme-1", made=False)
    before = {p: p.read_bytes() for p in made.rglob("*") if p.is_file()}
    assert status.backfill(conn, tmp_path) == 2
    assert status.backfill(conn, tmp_path) == 0
    states = {r["key"]: r["state"] for r in status.all_statuses(conn)}
    assert states == {PASTED_URL: "resume_made", "https://acme.com/j/1": "saved"}
    assert {p: p.read_bytes() for p in made.rglob("*") if p.is_file()} == before


def test_backfill_link_from_check_file_without_jd(conn, tmp_path):
    d = tmp_path / "Umbrella - Nurse"
    d.mkdir()
    (d / tailor.CHECK_FILE).write_text("# Nurse - Umbrella\n\n- Link: https://umbrella.com/n\n", encoding="utf-8")
    status.backfill(conn, tmp_path)
    assert status.get(conn, "https://umbrella.com/n") | {"state_at": None, "added_at": None} == {
        "key": "https://umbrella.com/n", "url": "https://umbrella.com/n", "company": "Umbrella", "title": "Nurse",
        "public_slug": None, "state": "resume_made", "state_at": None, "added_at": None}


def test_backfill_never_overrides_recorded_status_but_upgrades_saved(conn, tmp_path):
    make_folder(tmp_path, "Globex - Data Analyst", PASTED_URL, "Globex", "Data Analyst", "globex-data-analyst")
    status.set_state(conn, status.resolve(conn, tmp_path, PASTED_URL), "not_sending", NOW)
    status.backfill(conn, tmp_path)
    assert status.get(conn, PASTED_URL)["state"] == "not_sending"

    d = make_folder(tmp_path, "Acme - Engineer", "https://acme.com/j/1", "Acme", "Engineer", "acme-1", made=False)
    status.backfill(conn, tmp_path)
    (d / tailor.CHECK_FILE).write_text("# Engineer - Acme\n\n- Link: https://acme.com/j/1\n", encoding="utf-8")
    status.backfill(conn, tmp_path)
    assert status.get(conn, "https://acme.com/j/1")["state"] == "resume_made"


def run(monkeypatch, tmp_path, *argv):
    monkeypatch.setattr(sys, "argv", ["status", *argv])
    status.main()


@pytest.fixture
def cli(monkeypatch, tmp_path):
    config = {"db": str(tmp_path / "jobs.db"), "resume": {"jobs_dir": str(tmp_path / "My Jobs")}}
    monkeypatch.setattr(status.cfg, "load_or_defaults", lambda: config)
    return lambda *argv: run(monkeypatch, tmp_path, *argv)


def test_one_command_sets_and_reads_each_source(cli, tmp_path, capsys):
    conn = store.connect(tmp_path / "jobs.db")
    store.upsert(conn, [make_job("a", company="Acme", title="Engineer")], NOW)
    conn.commit()
    conn.close()
    make_folder(tmp_path / "My Jobs", "Globex - Data Analyst", PASTED_URL, "Globex", "Data Analyst", "g-da")

    cli("set", "a", "applied")
    cli("set", PASTED_URL, "heard back")
    cli("set", "applied", "--company", "Initech", "--title", "Analyst", "--on", "2026-09-20")
    capsys.readouterr()
    cli("show", "--company", "initech", "--title", "analyst")
    assert capsys.readouterr().out.startswith("#3    Applied       2026-09-20  Initech - Analyst  (no link)")
    cli()
    out = capsys.readouterr().out
    assert "Applied" in out and "Acme - Engineer" in out
    assert f"Heard back    " in out and PASTED_URL in out
    with pytest.raises(SystemExit, match="not a status"):
        cli("set", "a", "ghosted")
