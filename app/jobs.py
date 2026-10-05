import errno
import importlib
import json
import os
import subprocess
import sys
import time
import uuid
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit

# VS Code reads PDFs only through a viewer extension (launch.py installs one) => else system app
VIEWER_EXTENSION_SUFFIXES = {".pdf"}
COMMANDS = {
    "find": (None, "check for new jobs, then list ranked matches (rank args pass through)"),
    "poll": ("ingest.freehire", "check for new jobs only"),
    "rank": ("rank", "list ranked matches + why; --limit N, --best (Today order), --suspects, --would-hide PHRASE"),
    "probe": ("ingest.probe", "count jobs a candidate search would match"),
    "check-settings": (None, "validate search settings"),
    "email": ("alert", "email unseen matches; --dry-run prints instead"),
    "daily": ("daily", "poll + notify (or email if set up), as the daily schedule runs it"),
    "autorun": ("autorun", "daily schedule on | off | status"),
    "resume-import": ("resume.import_pdf", "resume PDF -> resume details: prepare | finish"),
    "resume-tidy": ("resume.tidy", "rewrite resume details as plain facts, notes out of sight"),
    "resume-render": ("resume.render", "render untailored resume PDF + checks"),
    "resume-lint": ("resume.lint", "wording + honesty lint on untailored resume"),
    "resume-feedback": ("resume.feedback", "plain-words feedback on the user's resume -> My Resume/Resume feedback.md"),
    "resume-gaps": ("resume.gaps", "ask the user for numbers + leadership their lines leave out: prepare | finish"),
    "resume-fit": ("resume.fit", "does this wording fit a line? candidates, or every bullet"),
    "tailor": ("resume.tailor", "tailored resume for one job: posting | prepare | check"),
    "letter": ("resume.letter", "cover letter for one job, checked like the resume: prepare | check JOB"),
    "today": ("today", "write Today.md: waiting on you, follow up, new since last check, not finished"),
    "status": ("status", "where each job stands: list | show JOB | set JOB STATE (or --company --title) | followed-up JOB | undo JOB --from STATE | sort"),
    "follow-up": ("followup", "draft a follow-up email for one job into its folder - the user sends it: JOB [--name NAME]"),
    "interview": ("interview", "interview practice or debrief for one job: requirements, backing lines, pay: JOB"),
    "apply": ("apply.profile", "application answers -> script the Chrome extension runs on a Workday form"),
    "answers": ("apply.answers", "the user's saved answers from application forms: list | forget N"),
    "apply-form": ("apply.form", "fill a job application in Chrome (not Workday), stops before Submit: prepare | fill; measure | try LINK (developers)"),
    "attribution": ("attribution", "Claude credit on fixes sent upstream: status | off | on | strip FILE | hook"),
    "ai": ("ai", "which AI the user chats with: prints it; ai claude | chatgpt | copilot saves it"),
    "look": ("look", "window look: prints it; look auto | light | dark saves it + switches the open window"),
    "update": ("update", "get latest Job Finder program; never touches My folders"),
    "launch": ("launch", "open VS Code on Today (START HERE before setup), chat in right sidebar (Desktop launcher)"),
    "open": (None, "open file or link for user: VS Code tab (PDF too); link as a tab in the Job Finder window, browser when it's closed; --outside: browser always"),
    "window-setup": (None, "installer step: Job Finder's VS Code profile + its extensions, plain progress lines"),
    "tui": ("tui", "terminal job browser (developers)"),
}


def run_module(module: str, args: list[str]) -> None:
    sys.argv = [module, *args]
    importlib.import_module(module).main()


def opens_as_tab(path: Path) -> bool:
    if path.suffix.lower() not in VIEWER_EXTENSION_SUFFIXES:
        return True
    import launch
    return launch.has_pdf_viewer()


# link => the open window's extension (app/vscode/start.js LINK_DIR): one file per link, renamed in
# under *.json; whoever renames or deletes it first opens it, so never twice. No other local way
# in: code's CLI server is remote-only, the start-page marker is read once, vscode:// is refused
LINK_DIR = Path(".data") / "open-link"
# extension claims in well under this; past it the window isn't Job Finder's (or has no browser)
LINK_WAIT = 2.0
# requests older than this are leftovers (extension.js discards them unseen too: LINK_MAX_AGE_MS)
LINK_MAX_AGE = 10.0
# printed so the AI says where it opened
IN_WINDOW = "opened in the Job Finder window"
IN_BROWSER = "opened in your browser"


def web_link(target: str) -> bool:
    parts = urlsplit(target)
    return parts.scheme in ("http", "https") and bool(parts.netloc)


def retry_busy(step, tries: int = 20, pause: float = 0.05):
    # Windows: a file another process has open (the extension, a virus scan) refuses a rename or
    # delete for a moment => brief retry; a missing file is an answer, raised at once
    for left in range(tries - 1, -1, -1):
        try:
            return step()
        except FileNotFoundError:
            raise
        except OSError as e:
            if left == 0 or not (isinstance(e, PermissionError) or e.errno == errno.EBUSY):
                raise
            time.sleep(pause)


def send_to_window(url: str, root: Path, wait: float = LINK_WAIT) -> bool:
    """Hand the link to Job Finder's window; True once its extension took it."""
    folder = root / LINK_DIR
    name = uuid.uuid4().hex
    temp, request = folder / f"{name}.tmp", folder / f"{name}.json"
    try:
        folder.mkdir(parents=True, exist_ok=True)
        stale = time.time() - LINK_MAX_AGE
        for old in folder.iterdir():
            try:
                if old.stat().st_mtime < stale:
                    old.unlink()
            except OSError:
                pass
        # whole file in place before the watcher sees the name
        temp.write_text(json.dumps({"url": url, "t": int(time.time() * 1000)}), encoding="utf-8")
        retry_busy(lambda: os.replace(temp, request))
    except OSError:
        temp.unlink(missing_ok=True)
        return False
    deadline = time.monotonic() + wait
    while request.exists():
        if time.monotonic() >= deadline:
            try:
                retry_busy(request.unlink)  # taken back: the extension's rename now finds nothing
            except FileNotFoundError:
                return True  # it took it in the same moment
            except OSError:
                pass  # still held after the retries: browser anyway - a missed link is worse than two
            return False
        time.sleep(0.05)
    return True


def open_for_user(target: str, outside: bool = False, wait: float = LINK_WAIT) -> None:
    import cfg
    import launch
    path = Path(target)
    if path.exists():
        # folder too, as launch.py does => lands in Job Finder's window, never the last-used one
        # (-r alone put it in whichever VS Code window was active)
        command = launch.code_command(["--disable-workspace-trust", str(cfg.ROOT), str(path.resolve())])
        if command and opens_as_tab(path):
            subprocess.run(command, check=False)
        else:
            webbrowser.open(path.resolve().as_uri())
        return
    # only a file here or a web page: a link to another program (vscode://, a script) from a
    # posting's text never runs
    if not web_link(target):
        sys.exit(f"not opened: {target!r} is not a file here or a web link (https://...)")
    # outside: a site that fails inside the window (Google sign-in)
    if not outside and launch.vscode_running() and send_to_window(target, cfg.ROOT, wait):
        print(IN_WINDOW)
        return
    webbrowser.open(target)
    print(IN_BROWSER)


def check_settings() -> None:
    import cfg
    import launch
    cfg.load()
    # setup runs this right after saving search settings => START HERE ("type set me up") leaves
    # the open window's file list now, not at next launch; no-op when nothing changed
    launch.write_workspace(launch.chosen_ai())
    print(f"ok: {cfg.config_path()}")


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        width = max(map(len, COMMANDS))
        sys.exit("usage: uv run app/jobs.py <command> [args]\n\n" + "\n".join(
            f"  {name:{width}}  {desc}" for name, (_, desc) in COMMANDS.items()))
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    name, args = sys.argv[1], sys.argv[2:]
    if name == "find":
        run_module("ingest.freehire", [])
        run_module("rank", args)
    elif name == "check-settings":
        check_settings()
    elif name == "open":
        open_for_user(" ".join(a for a in args if a != "--outside"), outside="--outside" in args)
    elif name == "window-setup":
        import launch
        launch.window_setup()
    else:
        run_module(COMMANDS[name][0], args)


if __name__ == "__main__":
    main()
