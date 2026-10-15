"""Self-check: what is broken, in plain words, and what the AI does about it.

Read-only + offline: reads files and local program state, writes nothing, opens no connection
(email: only whether the settings are filled in - never signs in, never prints the password).
Each check returns a Result; the AI runs `jobs.py doctor` first when anything seems wrong."""
import argparse
import json
import plistlib
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import cfg

STALE_AFTER = timedelta(hours=48)


@dataclass
class Result:
    name: str
    ok: bool
    say: str
    fix: str = ""


@dataclass
class Env:
    """Everything a check reads, so tests can swap each piece for a fake."""
    data: Path = field(default_factory=lambda: cfg.DATA)
    now: Callable[[], datetime] = datetime.now
    autorun_on: Callable[[], bool] = lambda: __import__("autorun").is_on()
    scheduled_program: Callable[[], str | None] = lambda: scheduled_program()
    window_behind: Callable[[], bool] = lambda: __import__("launch").window_behind()
    ai_extension: Callable[[str], bool] = lambda name: ai_extension_installed(name)
    settings_path: Callable[[], Path] = cfg.config_path
    resume_path: Path = field(default_factory=lambda: cfg.ROOT / "My Resume" / "Resume details.yml")
    fonts_installed: Callable[[], list[str]] = lambda: __import__("resume.typeface", fromlist=["x"]).installed()
    email_env: Path = field(default_factory=lambda: cfg.EMAIL_ENV)


def scheduled_program() -> str | None:
    """Program the macOS daily schedule starts; None = not readable here (other systems)."""
    import autorun
    if sys.platform != "darwin" or not autorun.PLIST.exists():
        return None
    try:
        return plistlib.loads(autorun.PLIST.read_bytes())["ProgramArguments"][0]
    except (OSError, ValueError, KeyError, IndexError):
        return ""


def ai_extension_installed(name: str) -> bool:
    import ai
    import launch
    extension = ai.EXTENSIONS.get(name)
    return extension is None or launch.has_extension(extension)


def last_failed(data: Path) -> str | None:
    try:
        lines = (data / "daily.log").read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        if line.startswith("failed "):
            return line[len("failed "):].strip()
    return None


def day_word(when: datetime) -> str:
    return f"{when:%A} {when.day} {when:%B}"


def morning_check(env: Env) -> Result:
    name = "Morning check"
    if not env.autorun_on():
        return Result(name, True, "Switched off - you asked for no daily check, or it was never set up.")
    import daily
    ran = daily.last_ok(env.data)  # timezone-aware UTC
    now = env.now().astimezone()  # naive = local time
    if ran:
        ran = ran.astimezone()
    if ran and now - ran <= STALE_AFTER:
        return Result(name, True, f"Worked on {day_word(ran)}.")
    since = f"hasn't run since {day_word(ran)}" if ran else "hasn't run yet"
    say = f"The morning check {since} - your computer may have been off, or the check is failing."
    if failed := last_failed(env.data):
        say += f" Last failure: {failed}"
    return Result(name, False, say, "Run the job check now; if it fails, fix the cause, then switch the daily check off and on again.")


def schedule_program(env: Env) -> Result:
    name = "Daily schedule"
    program = env.scheduled_program()
    if program is None:
        return Result(name, True, "Nothing to check here.")
    if program and Path(program).exists():
        return Result(name, True, "The program the schedule starts is there.")
    return Result(name, False, "The daily schedule points at a program that is gone, so the morning check can't start.",
                  "Switch the daily check off and on again to point it at the program now installed.")


def window_extension(env: Env) -> Result:
    name = "Job Finder window"
    if env.window_behind():
        return Result(name, False, "The open window still runs the version from before the update.",
                      "Tell the user to close the Job Finder window and open it again from the Desktop icon.")
    return Result(name, True, "The window is up to date.")


def chosen_ai(env: Env) -> Result:
    import ai
    name = "Your AI"
    word = ai.current(env.data / "ai") if (env.data / "ai").is_file() else None
    if word is None:
        return Result(name, False, "No AI is recorded for this program.",
                      "Ask the user which AI they chat with (Claude, ChatGPT or GitHub Copilot) and save it with the ai command.")
    if not env.ai_extension(word):
        return Result(name, False, f"{ai.NAMES[word]} is chosen but its chat add-on is not installed in the window.",
                      "Run the window setup step to add it, then tell the user to reopen the window.")
    return Result(name, True, f"{ai.NAMES[word]}.")


def loads(name: str, path: Path, missing: str, load: Callable[[Path], object]) -> Result:
    if not path.exists():
        return Result(name, False, missing, "Start setup (job-setup skill).")
    try:
        load(path)
    except (Exception, SystemExit) as exc:
        reason = " ".join(str(exc).split())[:300] or type(exc).__name__
        return Result(name, False, f"It can't be read: {reason}", "Show the user what is wrong in plain words and fix it with their OK.")
    return Result(name, True, "Reads fine.")


def search_settings(env: Env) -> Result:
    return loads("Search settings", env.settings_path(), "No search settings yet.", cfg.load)


def resume_details(env: Env) -> Result:
    def load(path: Path) -> object:
        from resume import schema
        return schema.load(path)
    return loads("Resume details", env.resume_path, "No resume details yet.", load)


def fonts(env: Env) -> Result:
    name = "Resume fonts"
    have = env.fonts_installed()
    if not have:
        return Result(name, False, "No resume font files are installed.", "Run an update to restore the program's fonts.")
    return Result(name, True, f"Installed: {', '.join(have)}.")


def email(env: Env) -> Result:
    name = "Email"
    values = {}
    try:
        lines = env.email_env.read_text(encoding="utf-8").splitlines()
    except OSError:
        return Result(name, True, "Not turned on.")
    for line in lines:
        key, sep, value = line.partition("=")
        if sep and not key.strip().startswith("#"):
            values[key.strip()] = value.strip().strip("\"'")
    missing = [k for k in ("SMTP_USER", "SMTP_PASSWORD") if not values.get(k)]
    if missing:
        what = " and ".join("the email address" if k == "SMTP_USER" else "the app password" for k in missing)
        return Result(name, False, f"Email is turned on but {what} is missing.", "Ask the user for it and save it; never repeat the password back.")
    return Result(name, True, "Email settings are filled in (not signed in - this check stays offline).")


CHECKS = (morning_check, schedule_program, window_extension, chosen_ai, search_settings, resume_details, fonts, email)


def run(env: Env | None = None) -> list[Result]:
    env = env or Env()
    out = []
    for check in CHECKS:
        try:
            out.append(check(env))
        except (Exception, SystemExit) as exc:
            out.append(Result(check.__name__, False, f"This check could not run: {type(exc).__name__}.", "Look into it before anything else."))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(prog="doctor", description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable results")
    args = parser.parse_args()
    results = run()
    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
        return
    for r in results:
        print(f"{'ok     ' if r.ok else 'PROBLEM'} {r.name}: {r.say}")
        if not r.ok and r.fix:
            print(f"        AI does: {r.fix}")
    bad = sum(not r.ok for r in results)
    print("Everything checks out." if not bad else f"{bad} thing{'s' if bad > 1 else ''} to fix.")


if __name__ == "__main__":
    main()
