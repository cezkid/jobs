import json
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

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
        (d / tailor.CHECK_FILE).write_text(f"# {title} - {company}\n\n- Link: {url}\n- Posted on: pasted\n\n"
                                           f"## Ready to send?\n\nYes - all 22 page checks passed.\n", encoding="utf-8")
    return d


def test_state_words_the_user_says():
    assert status.state_key("resume made") == "resume_made"
    assert status.state_key("Heard-back") == "heard_back"
    assert status.state_key("They said no") == "no"
    assert status.state_key("not_sending") == "not_sending"
    assert status.state_key("Closed") == "closed"
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


def test_plain_link_finds_listed_job(conn, tmp_path):
    """Pasted from the employer's page: no utm_source tag, same job."""
    store.upsert(conn, [make_job("a", url="https://boards.greenhouse.io/acme/jobs/a?utm_source=freehire.me")], NOW)
    status.set_state(conn, status.resolve(conn, tmp_path, "a"), "applied", NOW)
    plain = status.resolve(conn, tmp_path, "https://boards.greenhouse.io/acme/jobs/a")
    assert plain["public_slug"] == "a" and status.get(conn, plain["key"])["state"] == "applied"


def test_pasted_posting_by_link_slug_or_folder(conn, tmp_path):
    make_folder(tmp_path, "Globex - Data Analyst", PASTED_URL, "Globex", "Data Analyst", "globex-data-analyst")
    status.sort_folders(conn, tmp_path)  # renamed 'Job N - Globex - Data Analyst', filed under its stage
    [filed] = [f["dir"].name for f in status.folders(tmp_path)]
    for ref in (PASTED_URL, "globex-data-analyst", filed):
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


def test_folder_without_its_job_file_is_never_a_job(conn, tmp_path, monkeypatch):
    # a note or answers file written at a folder's old path, or a half-copied folder: never a
    # numbered job in Waiting on you, never moved
    monkeypatch.setattr(status.cfg, "DATA", tmp_path / ".data")
    stray = tmp_path / "1 To apply" / "Job 4 - Umbrella - Nurse"
    stray.mkdir(parents=True)
    (stray / tailor.CHECK_FILE).write_text("# Nurse - Umbrella\n\n- Link: https://umbrella.com/n\n", encoding="utf-8")
    (stray / "Application answers.md").write_text("answers\n", encoding="utf-8")
    broken = make_folder(tmp_path, "Acme - Engineer", "https://acme.com/j/1", "Acme", "Engineer", "acme-1")
    (broken / tailor.JOB_DATA / "jd.json").write_text("{", encoding="utf-8")  # cut off mid-write
    before = files(tmp_path)
    assert status.backfill(conn, tmp_path) == 0 and status.sort_folders(conn, tmp_path) == ([], [])
    assert files(tmp_path) == before and status.all_statuses(conn) == []


def test_backfill_never_overrides_recorded_status_but_upgrades_saved(conn, tmp_path):
    make_folder(tmp_path, "Globex - Data Analyst", PASTED_URL, "Globex", "Data Analyst", "globex-data-analyst")
    status.set_state(conn, status.resolve(conn, tmp_path, PASTED_URL), "not_sending", NOW)
    status.backfill(conn, tmp_path)
    assert status.get(conn, PASTED_URL)["state"] == "not_sending"

    d = make_folder(tmp_path, "Acme - Engineer", "https://acme.com/j/1", "Acme", "Engineer", "acme-1", made=False)
    status.backfill(conn, tmp_path)
    # a failed check writes its report too: still saved, never "resume made" in Waiting on you
    (d / tailor.CHECK_FILE).write_text("# Engineer - Acme\n\n- Link: https://acme.com/j/1\n\n"
                                       "## Ready to send?\n\nNot yet - 2 to fix first.\n", encoding="utf-8")
    status.backfill(conn, tmp_path)
    assert status.get(conn, "https://acme.com/j/1")["state"] == "saved"
    (d / tailor.CHECK_FILE).write_text("# Engineer - Acme\n\n- Link: https://acme.com/j/1\n\n"
                                       "## Ready to send?\n\nYes - all 22 page checks passed.\n", encoding="utf-8")
    status.backfill(conn, tmp_path)
    assert status.get(conn, "https://acme.com/j/1")["state"] == "resume_made"


def run(monkeypatch, tmp_path, *argv):
    monkeypatch.setattr(sys, "argv", ["status", *argv])
    status.main()


@pytest.fixture
def cli(monkeypatch, tmp_path):
    config = {"db": str(tmp_path / "jobs.db"), "resume": {"jobs_dir": str(tmp_path / "My Jobs")}}
    monkeypatch.setattr(status.cfg, "load_or_defaults", lambda: config)
    monkeypatch.setattr(status.cfg, "DATA", tmp_path / ".data")
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


def made_on(conn, tmp_path, name, url, at):
    make_folder(tmp_path, name, url, *name.split(" - "), name)
    status.set_state(conn, status.resolve(conn, tmp_path, url), "resume_made", at)


def test_passed_check_records_resume_made_without_moving_a_job_on(conn, tmp_path):
    d = make_folder(tmp_path, "Globex - Data Analyst", PASTED_URL, "Globex", "Data Analyst", "g-da")
    status.record_made(conn, d, NOW)
    assert (status.get(conn, PASTED_URL)["state"], status.get(conn, PASTED_URL)["state_at"]) == ("resume_made", NOW)
    status.set_state(conn, status.resolve(conn, tmp_path, PASTED_URL), "applied", NOW)
    status.record_made(conn, d, LATER)  # tailored again after sending: still applied
    assert status.get(conn, PASTED_URL)["state"] == "applied"
    still_tailoring = make_folder(tmp_path, "Acme - Engineer", "https://acme.com/j/1", "Acme", "Engineer", "a-1", made=False)
    status.record_made(conn, still_tailoring, NOW)
    assert status.get(conn, "https://acme.com/j/1") is None


def test_resume_made_untouched_14_days_drops_out_quietly(conn, tmp_path):
    made_on(conn, tmp_path, "Old - Nurse", "https://old.example/1", "2026-09-10T12:00:00Z")    # 19 days
    made_on(conn, tmp_path, "Edge - Nurse", "https://edge.example/1", "2026-09-15T12:00:01Z")  # just under 14
    made_on(conn, tmp_path, "New - Nurse", "https://new.example/1", "2026-09-28T12:00:00Z")
    assert [r["company"] for r in status.waiting(conn, NOW)] == ["Edge", "New"]
    assert status.get(conn, "https://old.example/1")["state"] == "resume_made"  # kept, not deleted
    assert status.to_ask(conn, NOW)["company"] == "Edge"  # never the dropped one


def test_chat_start_asks_about_the_oldest_job_only_once_in_3_days(conn, tmp_path):
    made_on(conn, tmp_path, "Acme - Analyst", "https://acme.example/1", "2026-09-24T12:00:00Z")
    made_on(conn, tmp_path, "Globex - Analyst", "https://globex.example/1", "2026-09-22T12:00:00Z")
    made_on(conn, tmp_path, "Fresh - Analyst", "https://fresh.example/1", "2026-09-28T12:00:00Z")
    assert status.to_ask(conn, NOW)["company"] == "Globex"
    # second chat same day, or the day after: no question at all - not the next job in line
    assert status.to_ask(conn, NOW) is None
    assert status.to_ask(conn, "2026-10-01T12:00:00Z") is None
    assert status.to_ask(conn, "2026-10-02T12:00:00Z")["company"] == "Globex"  # 'Not yet' 3 days ago
    status.set_state(conn, status.resolve(conn, tmp_path, "https://globex.example/1"), "applied", "2026-10-02T12:00:00Z")
    assert status.to_ask(conn, "2026-10-02T12:00:00Z")["company"] == "Acme"


def test_nothing_to_ask_before_3_days(conn, tmp_path):
    made_on(conn, tmp_path, "Acme - Analyst", "https://acme.example/1", "2026-09-27T12:00:00Z")
    assert status.to_ask(conn, NOW) is None


def test_ask_command_prints_one_question_or_nothing(cli, tmp_path, capsys):
    cli("ask")
    assert capsys.readouterr().out == "nothing to ask\n"
    cli("set", "resume made", "--company", "Initech", "--title", "Analyst", "--on", "2026-09-01")
    capsys.readouterr()
    cli("ask")
    assert capsys.readouterr().out == "nothing to ask\n"  # 14+ days old: dropped quietly
    five_days_ago = (date.today() - timedelta(days=5)).isoformat()
    cli("set", "resume made", "--company", "Umbrella", "--title", "Nurse", "--on", five_days_ago)
    capsys.readouterr()
    cli("ask")
    out = capsys.readouterr().out.splitlines()
    assert "Umbrella - Nurse" in out[0] and "did you send it?" in out[1] and len(out) == 2
    cli("ask")
    assert capsys.readouterr().out == "nothing to ask\n"


def test_still_open_says_open_may_be_closed_or_cant_tell_with_why(conn, tmp_path):
    store.upsert(conn, [make_job("live"), make_job("gone"), make_job("old")], "2026-09-10T12:00:00Z")
    store.upsert(conn, [make_job("live")], NOW)
    store.upsert(conn, [make_job("gone")], "2026-09-27T12:00:00Z")
    conn.execute("UPDATE jobs SET closed_at = ? WHERE public_slug = 'gone'", (NOW,))
    make_folder(tmp_path, "Globex - Data Analyst", PASTED_URL, "Globex", "Data Analyst", "g-da")
    for ref in ("live", "gone", "old", PASTED_URL):
        status.set_state(conn, status.resolve(conn, tmp_path, ref), "resume_made", NOW)
    status.set_state(conn, status.resolve(conn, tmp_path, company="Initech", title="Analyst"), "applied", NOW)
    said = {(r["public_slug"] or r["key"]): status.still_open(conn, r, 14, NOW) for r in status.in_progress(conn)}
    assert said == {
        "live": ("open", "on your job list, seen 2026-09-29"),
        "gone": ("may be closed", "gone from your job search since 2026-09-29"),
        "old": ("may be closed", "not seen in 19 days"),
        "g-da": ("can't tell", "never on your job list (pasted or found elsewhere) - check the link"),
        "outside:initech|analyst": ("can't tell", "never on your job list (pasted or found elsewhere) - check the link"),
    }


def test_morning_check_stopped_is_cant_tell_not_closed(conn, tmp_path):
    store.upsert(conn, [make_job("a")], "2026-09-10T12:00:00Z")
    status.set_state(conn, status.resolve(conn, tmp_path, "a"), "applied", NOW)
    assert status.still_open(conn, status.in_progress(conn)[0], 14, NOW) == \
        ("can't tell", "no job check in 19 days - check the link")


def test_finished_jobs_are_not_in_progress(conn, tmp_path):
    for company, state in (("A", "no"), ("B", "offer"), ("C", "not_sending"), ("D", "interview")):
        status.set_state(conn, status.resolve(conn, tmp_path, company=company, title="Nurse"), state, NOW)
    assert [r["company"] for r in status.in_progress(conn)] == ["D"]


def test_open_command_never_asks_about_a_pasted_posting(cli, tmp_path, capsys, monkeypatch):
    """A pasted posting's slug is made up locally - the job search can't know it."""
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: pytest.fail("no network call"))
    monkeypatch.setattr(status.httpx.Client, "get", lambda *a, **k: pytest.fail("no network call"))
    cli("open")
    assert capsys.readouterr().out == "no jobs in progress\n"
    make_folder(tmp_path / "My Jobs", "Globex - Data Analyst", PASTED_URL, "Globex", "Data Analyst", "g-da")
    cli("open")
    out = capsys.readouterr().out.splitlines()
    assert "Globex - Data Analyst" in out[0] and out[1].strip().startswith("can't tell - never on your job list")


def test_status_set_moves_that_jobs_folder_only(cli, tmp_path, capsys):
    jobs = tmp_path / "My Jobs"
    globex = make_folder(jobs, "Globex - Data Analyst", PASTED_URL, "Globex", "Data Analyst", "g-da")
    acme = make_folder(jobs, "Acme - Engineer", "https://acme.com/j/1", "Acme", "Engineer", "acme-1")
    for reading in (("open",), (), ("show", PASTED_URL), ("ask",)):
        cli(*reading)
    assert globex.is_dir() and acme.is_dir()  # reading never moves a folder
    before = files(globex)
    capsys.readouterr()
    cli("set", PASTED_URL, "applied")
    [sent] = (jobs / "2 Applied").iterdir()
    assert sent.name.endswith(" - Globex - Data Analyst") and files(sent) == before
    assert f"folder: {sent}\n" in capsys.readouterr().out  # the path the chat uses from now on
    assert acme.is_dir()  # the other job stays where it is until launch or sort
    cli("set", PASTED_URL, "closed")
    assert [d.name for d in (jobs / "4 Closed").iterdir()] == [sent.name]
    assert (jobs / "2 Applied").is_dir()  # emptied stage kept: nothing deleted, ever
    capsys.readouterr()
    cli("show", PASTED_URL)
    assert "Closed" in capsys.readouterr().out


def files(root: Path) -> dict:
    """Every file under root by its place inside it => same bytes after a move."""
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.fixture
def jobs(tmp_path, monkeypatch):
    monkeypatch.setattr(status.cfg, "DATA", tmp_path / ".data")
    return tmp_path / "My Jobs"


def test_every_status_has_a_stage_in_pipeline_order():
    assert status.STAGES.keys() == status.STATES.keys()
    stages = list(dict.fromkeys(status.STAGES[s] for s in status.STATES))
    assert stages == ["1 To apply", "2 Applied", "3 Heard back", "4 Closed"] == sorted(stages)


def test_sort_files_every_folder_by_status_and_number(conn, jobs):
    globex = make_folder(jobs, "Globex - Data Analyst", PASTED_URL, "Globex", "Data Analyst", "g-da")
    acme = make_folder(jobs, "Acme - Engineer", "https://acme.com/j/1", "Acme", "Engineer", "acme-1", made=False)
    initech = make_folder(jobs, "Initech - Analyst", "https://initech.com/2", "Initech", "Analyst", "i-2")
    with conn:
        a, g, i = (store.number(conn, slug) for slug in ("acme-1", "g-da", "i-2"))
    status.set_state(conn, status.resolve(conn, jobs, PASTED_URL), "applied", NOW)
    status.set_state(conn, status.resolve(conn, jobs, "https://initech.com/2"), "interview", NOW)
    before = {d.name: files(d) for d in (globex, acme, initech)}
    moved, stuck = status.sort_folders(conn, jobs)
    assert len(moved) == 3 and stuck == []
    want = {"Globex - Data Analyst": jobs / "2 Applied" / f"Job {g} - Globex - Data Analyst",
            "Acme - Engineer": jobs / "1 To apply" / f"Job {a} - Acme - Engineer",
            "Initech - Analyst": jobs / "3 Heard back" / f"Job {i} - Initech - Analyst"}
    for old, new in want.items():
        assert files(new) == before[old] and not (jobs / old).exists()
    assert status.sort_folders(conn, jobs) == ([], [])  # already in place: nothing to do


def test_sort_renames_only_never_copies_or_deletes(conn, jobs, monkeypatch):
    # copy-then-delete (shutil.move's fallback when a rename fails) can leave a job in two places
    for name in ("move", "copytree", "rmtree"):
        monkeypatch.setattr(shutil, name, lambda *a, **k: pytest.fail("rename only"))
    make_folder(jobs, "Globex - Data Analyst", PASTED_URL, "Globex", "Data Analyst", "g-da")
    status.sort_folders(conn, jobs)
    status.set_state(conn, status.resolve(conn, jobs, PASTED_URL), "applied", NOW)
    status.sort_folders(conn, jobs)
    assert list((jobs / "1 To apply").iterdir()) == [] and len(list((jobs / "2 Applied").iterdir())) == 1


def test_folder_that_cannot_move_now_stays_whole_and_moves_next_time(conn, jobs, monkeypatch):
    acme = make_folder(jobs, "Acme - Engineer", "https://acme.com/j/1", "Acme", "Engineer", "acme-1")
    make_folder(jobs, "Globex - Data Analyst", PASTED_URL, "Globex", "Data Analyst", "g-da")
    before, rename = files(acme), Path.rename

    def busy(self, to):  # Windows: a PDF open in another program pins its folder
        if self.name == "Acme - Engineer":
            raise PermissionError(13, "file in use")
        return rename(self, to)
    monkeypatch.setattr(Path, "rename", busy)
    moved, stuck = status.sort_folders(conn, jobs)
    assert [d.name for d, _ in moved] == ["Globex - Data Analyst"]
    assert stuck == [(acme, "could not move now - file in use")] and files(acme) == before
    monkeypatch.setattr(Path, "rename", rename)
    assert [d.name for d, _ in status.sort_folders(conn, jobs)[0]] == ["Acme - Engineer"]


def test_taken_name_leaves_both_and_says_so(conn, jobs):
    acme = make_folder(jobs, "Acme - Engineer", "https://acme.com/j/1", "Acme", "Engineer", "acme-1")
    with conn:
        n = store.number(conn, "acme-1")
    mine = jobs / "1 To apply" / f"Job {n} - Acme - Engineer"
    mine.mkdir(parents=True)
    (mine / "notes.txt").write_text("my own notes", encoding="utf-8")
    moved, stuck = status.sort_folders(conn, jobs)
    assert moved == [] and stuck == [(acme, f"1 To apply/Job {n} - Acme - Engineer already there - left both")]
    assert acme.is_dir() and (mine / "notes.txt").read_text(encoding="utf-8") == "my own notes"


def test_name_differing_only_in_letter_case_is_renamed_not_a_clash(conn, jobs):
    with conn:
        n = store.number(conn, "acme-1")
    make_folder(jobs / "1 To apply", f"Job {n} - acme - Engineer", "https://acme.com/j/1", "Acme", "Engineer", "acme-1")
    moved, stuck = status.sort_folders(conn, jobs)
    assert stuck == [] and [p.name for p in (jobs / "1 To apply").iterdir()] == [f"Job {n} - Acme - Engineer"]


def test_job_folder_dragged_inside_another_is_filed_first(conn, jobs):
    acme = make_folder(jobs, "Acme - Engineer", "https://acme.com/j/1", "Acme", "Engineer", "acme-1")
    make_folder(acme, "Globex - Data Analyst", PASTED_URL, "Globex", "Data Analyst", "g-da")
    make_folder(jobs / "2025" / "old", "Initech - Analyst", "https://initech.com/2", "Initech", "Analyst", "i-2")
    moved, stuck = status.sort_folders(conn, jobs)
    assert len(moved) == 3 and stuck == []
    assert sorted(p.name.split(" - ", 1)[1] for p in (jobs / "1 To apply").iterdir()) == [
        "Acme - Engineer", "Globex - Data Analyst", "Initech - Analyst"]


def test_closed_is_done_never_asked_or_followed_up(conn, tmp_path):
    made_on(conn, tmp_path, "Acme - Analyst", "https://acme.example/1", "2026-09-20T12:00:00Z")
    status.set_state(conn, status.resolve(conn, tmp_path, "https://acme.example/1"), "closed", NOW)
    assert status.in_progress(conn) == [] and status.waiting(conn, NOW) == [] and status.to_ask(conn, NOW) is None


def test_sort_command_says_what_moved_and_what_stayed(cli, tmp_path, capsys):
    cli("sort")
    assert capsys.readouterr().out == "every job folder is where its status says\n"
    make_folder(tmp_path / "My Jobs", "Acme - Engineer", "https://acme.com/j/1", "Acme", "Engineer", "acme-1")
    cli("sort")
    assert capsys.readouterr().out == f"moved: Acme - Engineer -> {Path('1 To apply', 'Job 1 - Acme - Engineer')}\n"
    cli("sort")
    assert capsys.readouterr().out == "every job folder is where its status says\n"


def test_two_chats_filing_at_once_take_turns(conn, jobs):
    make_folder(jobs, "Acme - Engineer", "https://acme.com/j/1", "Acme", "Engineer", "acme-1")
    with status.lock():
        with pytest.raises(SystemExit, match="another chat is moving job folders"):
            status.sort_folders(conn, jobs, wait_s=0)
    assert len(status.sort_folders(conn, jobs)[0]) == 1


def test_job_search_says_closed_gone_or_seen_for_listed_jobs(conn, tmp_path, monkeypatch, capsys):
    """Its listing id only, never the employer's page; unreachable -> the list's own answer."""
    import httpx
    answers = {
        "/v1/jobs/closed": httpx.Response(200, json={"data": {"closed_at": "2026-09-21T11:33:35Z"}}),
        "/v1/jobs/gone": httpx.Response(404, json={"error": "not found"}),
        "/v1/jobs/seen": httpx.Response(200, json={"data": {"closed_at": None, "last_seen_at": "2026-09-29T02:00:00Z"}}),
        "/v1/jobs/quiet": httpx.Response(200, json={"data": {"closed_at": None, "last_seen_at": "2026-09-01T02:00:00Z"}}),
    }
    asked = []

    def handler(request):
        asked.append(request.url.path)
        if request.url.path == "/v1/jobs/down":
            raise httpx.ConnectError("offline")
        return answers[request.url.path]

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        said = {slug: status.ask_job_search(client, "https://api.test/v1", slug, 14, NOW)
                for slug in ("closed", "gone", "seen", "quiet", "down")}
    assert said == {
        "closed": ("may be closed", "the job search marked it closed on 2026-09-21"),
        "gone": ("may be closed", "the job search no longer lists it"),
        "seen": ("open", "the job search saw it 2026-09-29"),
        "quiet": ("may be closed", "the job search last saw it on 2026-09-01"),
        "down": None,
    }
    assert all("acme" not in path for path in asked)


def test_closed_posting_not_waiting_asked_once_as_closed(conn, tmp_path):
    store.upsert(conn, [make_job("gone")], "2026-09-20T12:00:00Z")
    status.set_state(conn, status.resolve(conn, tmp_path, "gone"), "resume_made", "2026-09-24T12:00:00Z")
    conn.execute("UPDATE jobs SET closed_at = '2026-09-26T08:00:00Z' WHERE public_slug = 'gone'")
    assert status.waiting(conn, NOW) == []
    asked = status.to_ask(conn, NOW)
    assert asked["public_slug"] == "gone" and asked["closed_since"] == "2026-09-26"
    assert status.to_ask(conn, NOW) is None


def test_followed_up_is_logged_never_a_status_and_shows_in_history(cli, tmp_path, capsys):
    cli("set", "resume made", "--company", "Initech", "--title", "Analyst", "--on", "2026-09-01")
    with pytest.raises(SystemExit, match="sent and waiting"):
        cli("followed-up", "--company", "Initech", "--title", "Analyst")
    cli("set", "applied", "--company", "Initech", "--title", "Analyst", "--on", "2026-09-02")
    cli("followed-up", "--company", "Initech", "--title", "Analyst", "--on", "2026-09-25")
    capsys.readouterr()
    cli("show", "--company", "Initech", "--title", "Analyst")
    out = capsys.readouterr().out.splitlines()
    assert "Applied" in out[0]
    assert [line.split(None, 1)[1] for line in out[1:4]] == ["Followed up", "Applied", "Resume made"]
    assert out[1].strip().startswith("2026-09-25")


def test_old_stage_folders_go_once_empty_never_with_a_job_inside(conn, jobs):
    """Renamed stages (To send -> To apply, Sent -> Applied) left empty duplicates behind."""
    (jobs / "1 To send").mkdir(parents=True)
    (jobs / "1 To send" / ".DS_Store").write_bytes(b"")
    (jobs / "2 Sent").mkdir()
    make_folder(jobs / "2 Sent", "Job 9 - Acme - Engineer", "https://acme.com/j/9", "Acme", "Engineer", "acme-9")
    status.backfill(conn, jobs)
    status.sort_folders(conn, jobs)
    assert not (jobs / "1 To send").exists() and not (jobs / "2 Sent").exists()
    assert [p.parent.name for p in jobs.glob("*/Job * - Acme - Engineer")] == ["1 To apply"]
    (jobs / "2 Sent").mkdir()
    (jobs / "2 Sent" / "notes.txt").write_text("mine")
    status.sort_folders(conn, jobs)
    assert (jobs / "2 Sent" / "notes.txt").exists()  # the user's own file: folder kept
