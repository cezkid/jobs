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


def schedule_launch(monkeypatch, stamp: str | None, owner: Path | None) -> list:
    if stamp is not None:
        autorun.STAMP.write_text(stamp + "\n", encoding="utf-8")
    calls = []
    monkeypatch.setattr(autorun.cfg, "load", lambda: CONFIG)
    monkeypatch.setattr(autorun, "installed_root", lambda: owner)
    monkeypatch.setattr(autorun, "turn_on", lambda config: calls.append("on"))
    autorun.ensure_current()
    return calls


def test_launch_brings_an_old_schedule_up_to_the_settings_times(monkeypatch):
    # installed before the later checks: one 08:00 run a day until a launch re-installs it
    assert schedule_launch(monkeypatch, None, cfg.ROOT) == ["on"]
    assert schedule_launch(monkeypatch, "08:00", cfg.ROOT) == ["on"]


def test_launch_leaves_a_current_or_switched_off_schedule_alone(monkeypatch):
    assert schedule_launch(monkeypatch, autorun.label(autorun.times(CONFIG)), cfg.ROOT) == []
    assert schedule_launch(monkeypatch, "off", cfg.ROOT) == []
    autorun.STAMP.unlink()
    # never turned on: asked once, remembered as off
    assert schedule_launch(monkeypatch, None, None) == []
    assert autorun.STAMP.read_text(encoding="utf-8").strip() == "off"


def make_copy(tmp_path: Path) -> Path:
    other = tmp_path / "other copy"
    (other / "app").mkdir(parents=True)
    (other / "app" / "daily.py").write_text("", encoding="utf-8")
    return other


def test_launch_never_takes_the_schedule_another_copy_runs(monkeypatch, tmp_path):
    # 2026-11-05: a scratch copy's launch (no stamp) re-installed the one schedule on this Mac
    # for itself => two days of checks ran in /tmp, none in the user's folder
    other = make_copy(tmp_path)
    assert schedule_launch(monkeypatch, None, other) == []
    assert not autorun.STAMP.exists()  # asked again next launch: that copy may be gone by then
    assert schedule_launch(monkeypatch, "08:00", other) == []


def test_launch_takes_over_from_a_folder_that_is_gone(monkeypatch, tmp_path):
    # folder moved or deleted: its schedule starts nothing, so this one takes it
    assert schedule_launch(monkeypatch, None, tmp_path / "gone") == ["on"]


def test_installed_root_reads_the_plist(monkeypatch, tmp_path):
    monkeypatch.setattr(autorun.sys, "platform", "darwin")
    assert autorun.installed_root() is None
    other = make_copy(tmp_path)
    autorun.PLIST.write_bytes(autorun.mac_plist("/u/uv", other, [(8, 0)]))
    assert autorun.installed_root() == other
    assert autorun.elsewhere() == other and not autorun.is_on()
    autorun.PLIST.write_bytes(autorun.mac_plist("/u/uv", cfg.ROOT, [(8, 0)]))
    assert autorun.elsewhere() is None and autorun.is_on()
