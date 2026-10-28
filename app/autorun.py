import argparse
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

import cfg

TASK_NAME = "Job Finder daily"
LAUNCHD_LABEL = "me.jobs.daily"
PLIST = Path.home() / "Library/LaunchAgents" / f"{LAUNCHD_LABEL}.plist"
RUN_LIMIT_MIN = 5
LOG_TAIL_LINES = 12
# times the installed schedule runs at ("08:00 10:00 ..."), or "off": a launch finding it differs
# from the settings' times re-installs it (ensure_current) => installs from before the day checks
# get them without a word from the user
STAMP = cfg.DATA / "schedule"


def hour_minute(config: dict) -> tuple[int, int]:
    hh, mm = config["schedule"]["local_daily"].split(":")
    return int(hh), int(mm)


def times(config: dict) -> list[tuple[int, int]]:
    """Morning check, then one every `every_hours` until `last_check`. One a day showed this
    morning's jobs all day: 65 new rows reached the job search between a 09:51 check and 21:22, 30
    of them on the user's lists (2026-10-27). Only the day's first check tells them (daily.py)."""
    first, sched = hour_minute(config), config["schedule"]
    every = int(sched.get("every_hours") or 0)
    hh, mm = (sched.get("last_check") or "22:00").split(":")
    last = int(hh) * 60 + int(mm)
    start = first[0] * 60 + first[1]
    steps = range(start, max(last, start) + 1, every * 60) if every > 0 else [start]
    return [divmod(m, 60) for m in steps]


def label(at: list[tuple[int, int]]) -> str:
    return " ".join(f"{h:02d}:{m:02d}" for h, m in at)


def windows_script(uvw: str, root: Path, at: list[tuple[int, int]]) -> str:
    uvw, root = (str(v).replace("'", "''") for v in (uvw, root))
    triggers = ", ".join(f"(New-ScheduledTaskTrigger -Daily -At '{h:02d}:{m:02d}')" for h, m in at)
    # pythonw + uvw => no console window flashes at run time
    return f"""$ErrorActionPreference = 'Stop'
$a = New-ScheduledTaskAction -Execute '{uvw}' -Argument 'run --directory "{root}" pythonw app/daily.py' -WorkingDirectory '{root}'
$t = @({triggers})
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes {RUN_LIMIT_MIN})
Register-ScheduledTask -TaskName '{TASK_NAME}' -Action $a -Trigger $t -Settings $s -Force | Out-Null
"""


def mac_plist(uv: str, root: Path, at: list[tuple[int, int]]) -> bytes:
    return plistlib.dumps({
        "Label": LAUNCHD_LABEL,
        "ProgramArguments": [uv, "run", "--directory", str(root), "python", "app/daily.py"],
        "WorkingDirectory": str(root),
        # asleep at run time => launchd runs it on wake
        "StartCalendarInterval": [{"Hour": h, "Minute": m} for h, m in at],
        "StandardOutPath": str(cfg.DAILY_LOG),
        "StandardErrorPath": str(cfg.DAILY_LOG),
    })


def powershell(script: str) -> subprocess.CompletedProcess:
    # daily run = pythonw, no console => powershell opens its own window each run unless told not to
    hidden = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                          capture_output=True, text=True, creationflags=hidden)


def uv_binary(name: str) -> str:
    path = shutil.which(name) or shutil.which(name, path=str(Path.home() / ".local/bin"))
    if not path:
        sys.exit(f"{name} not found on PATH")
    return path


def turn_on(config: dict) -> None:
    at = times(config)
    if sys.platform == "win32":
        result = powershell(windows_script(uv_binary("uvw"), cfg.ROOT, at))
        if result.returncode:
            sys.exit(result.stderr)
    elif sys.platform == "darwin":
        PLIST.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(PLIST)], capture_output=True)
        PLIST.write_bytes(mac_plist(uv_binary("uv"), cfg.ROOT, at))
        subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(PLIST)], check=True)
    else:
        sys.exit("daily run supports Windows + macOS; Linux -> app/deploy/render_units.py")
    write_stamp(label(at))
    later = f", again at {label(at[1:])}" if at[1:] else ""
    print(f"on: checks for jobs daily at {label(at[:1])}{later}; tells you about new ones once a day")


def turn_off() -> None:
    if sys.platform == "win32":
        powershell(f"Unregister-ScheduledTask -TaskName '{TASK_NAME}' -Confirm:$false")
    elif sys.platform == "darwin":
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(PLIST)], capture_output=True)
        PLIST.unlink(missing_ok=True)
    write_stamp("off")
    print("off")


def write_stamp(text: str) -> None:
    try:
        STAMP.parent.mkdir(exist_ok=True)
        STAMP.write_text(text + "\n", encoding="utf-8")
    except OSError:
        pass


def ensure_current() -> None:
    """At launch: the schedule on this computer runs at the settings' times. Off stays off; no
    stamp = installed before it existed => asked once (Windows: one hidden powershell)."""
    try:
        was = STAMP.read_text(encoding="utf-8").strip()
    except OSError:
        was = None
    if was == "off":
        return
    config = cfg.load()
    if was == label(times(config)):
        return
    if was is None and not is_on():
        write_stamp("off")
        return
    turn_on(config)


def is_on() -> bool:
    if sys.platform == "win32":
        return powershell(f"Get-ScheduledTask -TaskName '{TASK_NAME}' -ErrorAction Stop").returncode == 0
    return PLIST.exists()


def status() -> None:
    if sys.platform == "win32":
        result = powershell(f"Get-ScheduledTask -TaskName '{TASK_NAME}' | Get-ScheduledTaskInfo | "
                            "Format-List LastRunTime,LastTaskResult,NextRunTime")
        print(result.stdout.strip() or "off")
    elif sys.platform == "darwin":
        print("on" if PLIST.exists() else "off")
    if cfg.DAILY_LOG.exists():
        print("\n".join(cfg.DAILY_LOG.read_text(encoding="utf-8").splitlines()[-LOG_TAIL_LINES:]))


def main() -> None:
    ap = argparse.ArgumentParser(description="Daily job check + notification on this computer (Windows / macOS)")
    ap.add_argument("action", choices=["on", "off", "status"])
    args = ap.parse_args()
    if args.action == "on":
        turn_on(cfg.load())
    elif args.action == "off":
        turn_off()
    else:
        status()


if __name__ == "__main__":
    main()
