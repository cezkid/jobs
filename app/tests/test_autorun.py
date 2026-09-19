import plistlib
from pathlib import Path

import autorun
import cfg

CONFIG = cfg.load(cfg.PROFILES / "example.yml")


def test_default_time_parses():
    assert autorun.hour_minute(CONFIG) == (8, 0)


def test_windows_script_quotes_apostrophe_path():
    script = autorun.windows_script("C:/u/uvw.exe", Path("C:/Users/O'Brien/jobs"), (7, 5))
    assert "O''Brien" in script
    assert "-At '07:05'" in script
    assert "pythonw app/daily.py" in script
    assert "-StartWhenAvailable" in script and "-AllowStartIfOnBatteries" in script


def test_mac_plist_runs_daily_at_time():
    plist = plistlib.loads(autorun.mac_plist("/u/uv", Path("/Users/x/jobs"), (8, 30)))
    assert plist["ProgramArguments"][-1] == "app/daily.py"
    assert plist["StartCalendarInterval"] == {"Hour": 8, "Minute": 30}
    assert plist["StandardOutPath"] == str(cfg.DAILY_LOG)
