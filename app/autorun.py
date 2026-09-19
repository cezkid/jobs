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


def hour_minute(config: dict) -> tuple[int, int]:
    hh, mm = config["schedule"]["local_daily"].split(":")
    return int(hh), int(mm)


def windows_script(uvw: str, root: Path, at: tuple[int, int]) -> str:
    uvw, root = (str(v).replace("'", "''") for v in (uvw, root))
    # pythonw + uvw => no console window flashes at run time
    return f"""$ErrorActionPreference = 'Stop'
$a = New-ScheduledTaskAction -Execute '{uvw}' -Argument 'run --directory "{root}" pythonw app/daily.py' -WorkingDirectory '{root}'
$t = New-ScheduledTaskTrigger -Daily -At '{at[0]:02d}:{at[1]:02d}'
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes {RUN_LIMIT_MIN})
Register-ScheduledTask -TaskName '{TASK_NAME}' -Action $a -Trigger $t -Settings $s -Force | Out-Null
"""


def mac_plist(uv: str, root: Path, at: tuple[int, int]) -> bytes:
    return plistlib.dumps({
        "Label": LAUNCHD_LABEL,
        "ProgramArguments": [uv, "run", "--directory", str(root), "python", "app/daily.py"],
        "WorkingDirectory": str(root),
        # asleep at run time => launchd runs it on wake
        "StartCalendarInterval": {"Hour": at[0], "Minute": at[1]},
        "StandardOutPath": str(cfg.DAILY_LOG),
        "StandardErrorPath": str(cfg.DAILY_LOG),
    })


def powershell(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                          capture_output=True, text=True)


def uv_binary(name: str) -> str:
    path = shutil.which(name) or shutil.which(name, path=str(Path.home() / ".local/bin"))
    if not path:
        sys.exit(f"{name} not found on PATH")
    return path


def turn_on(config: dict) -> None:
    at = hour_minute(config)
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
    print(f"on: checks for jobs daily at {at[0]:02d}:{at[1]:02d}, tells you about new ones")


def turn_off() -> None:
    if sys.platform == "win32":
        powershell(f"Unregister-ScheduledTask -TaskName '{TASK_NAME}' -Confirm:$false")
    elif sys.platform == "darwin":
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(PLIST)], capture_output=True)
        PLIST.unlink(missing_ok=True)
    print("off")


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
