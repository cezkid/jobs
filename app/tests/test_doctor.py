import json
from datetime import datetime, timedelta, timezone

import doctor
import jobs

NOW = datetime(2026, 10, 15, 8, 0, 0)


def env(tmp_path, **over):
    base = dict(
        data=tmp_path, now=lambda: NOW, autorun_on=lambda: True, scheduled_program=lambda: None,
        window_behind=lambda: False, ai_extension=lambda name: True, settings_path=lambda: tmp_path / "s.yml",
        resume_path=tmp_path / "r.yml", fonts_installed=lambda: ["Caladea"], email_env=tmp_path / "email.env")
    base.update(over)
    return doctor.Env(**base)


def log(tmp_path, *lines):
    (tmp_path / "daily.log").write_text("\n".join(lines) + "\n", encoding="utf-8")


def snapshot(path):
    return sorted((p.name, p.read_bytes()) for p in path.iterdir())


def test_doctor_registered():
    assert "doctor" in jobs.COMMANDS


def test_doctor_morning_check_ok_and_off(tmp_path):
    log(tmp_path, f"ok {(NOW - timedelta(hours=5)).isoformat()} 10 jobs")
    assert doctor.morning_check(env(tmp_path)).ok
    assert doctor.morning_check(env(tmp_path, autorun_on=lambda: False)).ok


def test_doctor_last_ok_from_store_with_z(tmp_path):
    import store
    conn = store.connect(tmp_path / "jobs.db")
    cols = [r[1] for r in conn.execute("PRAGMA table_info(jobs)") if r[3] and r[4] is None]
    stamp = (NOW - timedelta(hours=5)).astimezone().astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(f"INSERT INTO jobs ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                 [stamp if c.endswith("fetched_at") else "x" for c in cols])
    conn.commit()
    conn.close()
    r = doctor.morning_check(env(tmp_path))
    assert r.ok and "Worked on" in r.say
    old = doctor.morning_check(env(tmp_path, now=lambda: NOW + timedelta(days=9)))
    assert not old.ok and "hasn't run since" in old.say


def test_doctor_morning_check_stale_names_failure(tmp_path):
    log(tmp_path, f"ok {(NOW - timedelta(days=4)).isoformat()} 10 jobs", "failed 2026-10-14T07:00:00 timed out")
    r = doctor.morning_check(env(tmp_path))
    assert not r.ok and "hasn't run since" in r.say and "timed out" not in r.say and r.fix
    assert "Wednesday 14 October" in r.say and "timed out" in r.detail


def test_doctor_plain_words_old_failure_not_named(tmp_path):
    log(tmp_path, "failed 2026-10-01T07:00:00 boom", f"ok {(NOW - timedelta(days=4)).isoformat()} 10 jobs")
    r = doctor.morning_check(env(tmp_path))
    assert not r.ok and "failed" not in r.say and r.detail == ""


def test_doctor_plain_words_load_error(tmp_path):
    bad = tmp_path / "bad.yml"
    bad.write_text("passes: [not, a, pass]\n")
    r = doctor.search_settings(env(tmp_path, settings_path=lambda: bad))
    assert not r.ok and "pass" not in r.say and r.detail


def test_doctor_font_chosen_must_be_installed(tmp_path):
    assert doctor.fonts(env(tmp_path, chosen_font=lambda: "Caladea")).ok
    r = doctor.fonts(env(tmp_path, fonts_installed=lambda: ["Other"], chosen_font=lambda: "Caladea"))
    assert not r.ok and "Caladea" in r.say


def test_doctor_font_chosen_default_from_defaults():
    assert doctor.chosen_font_name()


def test_doctor_schedule_windows_reads_program(tmp_path):
    from types import SimpleNamespace as NS
    here = tmp_path / "uvw.exe"
    here.write_text("x")
    asked = []

    def run(script):
        asked.append(script)
        return NS(returncode=0, stdout=f'{here}\n')
    program = doctor.windows_program(run)
    assert program == str(here) and "Get-ScheduledTask" in asked[0] and "Register" not in asked[0]
    assert doctor.schedule_program(env(tmp_path, scheduled_program=lambda: program)).ok
    gone = doctor.windows_program(lambda s: NS(returncode=0, stdout=str(tmp_path / "gone.exe")))
    assert not doctor.schedule_program(env(tmp_path, scheduled_program=lambda: gone)).ok
    assert doctor.windows_program(lambda s: NS(returncode=1, stdout="")) is None


def test_doctor_schedule_program(tmp_path):
    assert doctor.schedule_program(env(tmp_path)).ok
    here = tmp_path / "uv"
    here.write_text("x")
    assert doctor.schedule_program(env(tmp_path, scheduled_program=lambda: str(here))).ok
    assert not doctor.schedule_program(env(tmp_path, scheduled_program=lambda: str(tmp_path / "gone"))).ok


def test_doctor_window_extension(tmp_path):
    assert doctor.window_extension(env(tmp_path)).ok
    assert not doctor.window_extension(env(tmp_path, window_behind=lambda: True)).ok


def test_doctor_chosen_ai(tmp_path):
    assert not doctor.chosen_ai(env(tmp_path)).ok
    (tmp_path / "ai").write_text("claude\n")
    assert doctor.chosen_ai(env(tmp_path)).ok
    assert not doctor.chosen_ai(env(tmp_path, ai_extension=lambda n: False)).ok


def test_doctor_settings_and_resume(tmp_path):
    for check, key in ((doctor.search_settings, "settings_path"), (doctor.resume_details, "resume_path")):
        assert not check(env(tmp_path)).ok  # missing
    bad = tmp_path / "bad.yml"
    bad.write_text("passes: [not, a, pass]\n")
    r = doctor.search_settings(env(tmp_path, settings_path=lambda: bad))
    assert not r.ok and "can't be read" in r.say
    assert not doctor.resume_details(env(tmp_path, resume_path=bad)).ok


def test_doctor_settings_ok(tmp_path):
    good = tmp_path / "good.yml"
    good.write_text("passes:\n  - tier: remote\n    label: Remote\n    params:\n      work_mode: [remote]\n")
    assert doctor.search_settings(env(tmp_path, settings_path=lambda: good)).ok


def test_doctor_fonts(tmp_path):
    assert doctor.fonts(env(tmp_path)).ok
    assert not doctor.fonts(env(tmp_path, fonts_installed=lambda: [])).ok


def test_doctor_email_never_shows_password(tmp_path):
    assert doctor.email(env(tmp_path)).ok  # off
    (tmp_path / "email.env").write_text("SMTP_USER=a@b.c\n")
    r = doctor.email(env(tmp_path))
    assert not r.ok and "app password" in r.say
    (tmp_path / "email.env").write_text("SMTP_USER=a@b.c\nSMTP_PASSWORD=hunter2\n")
    r = doctor.email(env(tmp_path))
    assert r.ok and "hunter2" not in json.dumps(r.__dict__)


def test_doctor_run_writes_nothing_and_survives_a_crashing_check(tmp_path):
    before = snapshot(tmp_path)
    results = doctor.run(env(tmp_path, window_behind=lambda: 1 / 0))
    assert len(results) == len(doctor.CHECKS)
    assert not next(r for r in results if r.name == "window_extension").ok
    assert snapshot(tmp_path) == before


def test_doctor_json(tmp_path, monkeypatch, capsys):
    fake = env(tmp_path)
    monkeypatch.setattr(doctor, "Env", lambda: fake)
    monkeypatch.setattr("sys.argv", ["doctor", "--json"])
    doctor.main()
    data = json.loads(capsys.readouterr().out)
    assert {"name", "ok", "say", "fix"} <= data[0].keys()


def test_doctor_updates_held_back(tmp_path):
    assert doctor.updates(env(tmp_path)).ok
    (tmp_path / "update-skipped").write_text("app/today.js\n", encoding="utf-8")
    r = doctor.updates(env(tmp_path))
    assert not r.ok and r.detail == "app/today.js" and "app/" not in r.say
