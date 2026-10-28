import plistlib
from pathlib import Path

import autorun
import cfg

CONFIG = cfg.load(cfg.PROFILES / "example.yml")


def test_default_time_parses():
    assert autorun.hour_minute(CONFIG) == (8, 0)


def test_checks_every_two_hours_from_morning_until_ten():
    # one check a day showed the morning's jobs all day: 30 new on the user's lists by 21:22 (2026-10-27)
    assert autorun.label(autorun.times(CONFIG)) == "08:00 10:00 12:00 14:00 16:00 18:00 20:00 22:00"
    late = {**CONFIG, "schedule": {**CONFIG["schedule"], "local_daily": "23:30"}}
    assert autorun.times(late) == [(23, 30)]
    once = {**CONFIG, "schedule": {**CONFIG["schedule"], "every_hours": 0}}
    assert autorun.times(once) == [(8, 0)]


def test_windows_script_quotes_apostrophe_path():
    script = autorun.windows_script("C:/u/uvw.exe", Path("C:/Users/O'Brien/jobs"), [(7, 5), (9, 5)])
    assert "O''Brien" in script
    assert "$t = @((New-ScheduledTaskTrigger -Daily -At '07:05'), (New-ScheduledTaskTrigger -Daily -At '09:05'))" in script
    assert "pythonw app/daily.py" in script
    assert "-StartWhenAvailable" in script and "-AllowStartIfOnBatteries" in script


def test_mac_plist_runs_daily_at_time():
    plist = plistlib.loads(autorun.mac_plist("/u/uv", Path("/Users/x/jobs"), [(8, 30), (10, 30)]))
    assert plist["ProgramArguments"][-1] == "app/daily.py"
    assert plist["StartCalendarInterval"] == [{"Hour": 8, "Minute": 30}, {"Hour": 10, "Minute": 30}]
    assert plist["StandardOutPath"] == str(cfg.DAILY_LOG)


def test_powershell_never_opens_a_window_on_windows(monkeypatch):
    # daily run = pythonw => child powershell got its own visible console each run (measured 2026-09-28)
    seen = {}
    monkeypatch.setattr(autorun.sys, "platform", "win32")
    monkeypatch.setattr(autorun.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    monkeypatch.setattr(autorun.subprocess, "run", lambda args, **kw: seen.update(kw))
    autorun.powershell("'x'")
    assert seen["creationflags"] == 0x08000000


def schedule_launch(monkeypatch, stamp: str | None, on: bool) -> list:
    if stamp is not None:
        autorun.STAMP.write_text(stamp + "\n", encoding="utf-8")
    calls = []
    monkeypatch.setattr(autorun.cfg, "load", lambda: CONFIG)
    monkeypatch.setattr(autorun, "is_on", lambda: on)
    monkeypatch.setattr(autorun, "turn_on", lambda config: calls.append("on"))
    autorun.ensure_current()
    return calls


def test_launch_brings_an_old_schedule_up_to_the_settings_times(monkeypatch):
    # installed before the later checks: one 08:00 run a day until a launch re-installs it
    assert schedule_launch(monkeypatch, None, on=True) == ["on"]
    assert schedule_launch(monkeypatch, "08:00", on=True) == ["on"]


def test_launch_leaves_a_current_or_switched_off_schedule_alone(monkeypatch):
    assert schedule_launch(monkeypatch, autorun.label(autorun.times(CONFIG)), on=True) == []
    assert schedule_launch(monkeypatch, "off", on=True) == []
    autorun.STAMP.unlink()
    # never turned on: asked once, remembered as off
    assert schedule_launch(monkeypatch, None, on=False) == []
    assert autorun.STAMP.read_text(encoding="utf-8").strip() == "off"
