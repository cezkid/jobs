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
# no VS Code viewer at all: a tab would show "binary file" => always the computer's own app (Word, Pages)
SYSTEM_APP_SUFFIXES = {".docx", ".docm", ".doc", ".rtf", ".odt", ".pages"}
COMMANDS = {
    "find": (None, "check for new jobs, then list ranked matches (rank args pass through)"),
    "poll": ("ingest.freehire", "check for new jobs only"),
    "rank": ("rank", "list ranked matches + why; --limit N, --best (Today order), --suspects, --would-hide PHRASE"),
    "probe": ("ingest.probe", "count jobs a candidate search would match"),
    "check-settings": (None, "validate search settings"),
    "email": ("alert", "email unseen matches; --dry-run prints instead"),
    "daily": ("daily", "poll + notify (or email if set up), as the daily schedule runs it"),
    "autorun": ("autorun", "daily schedule on | off | status"),
    "resume-import": ("resume.import_pdf", "resume PDF or Word file -> resume details: prepare [--file F] | finish"),
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
    "about": ("about", "what Job Finder knows about the user + their notes beyond the resume: show | list | read KIND | add KIND WORDS | forget KIND N"),
    "answers": ("apply.answers", "the user's saved answers from application forms: list | forget N"),
    "apply-form": ("apply.form", "fill a job application in Chrome (not Workday), stops before Submit: prepare | fill (--in-window: trial, Greenhouse, Ashby, Lever, JazzHR, Workable, BambooHR; a multi-page form: one helper keeps its tab, let-go ends it); measure | try LINK, workday-fixture FILE (developers)"),
    "attribution": ("attribution", "Claude credit on fixes sent upstream: status | off | on | strip FILE | hook"),
    "ai": ("ai", "which AI the user chats with: prints it; ai claude | chatgpt | copilot saves it"),
    "look": ("look", "window look: prints it; look auto | light | dark saves it + switches the open window"),
    "update": ("update", "get latest Job Finder program; never touches My folders"),
    "launch": ("launch", "open VS Code on Today (START HERE before setup), chat in right sidebar (Desktop launcher)"),
    "open": (None, "open file or link for user: VS Code tab (PDF too); link as a tab in the Job Finder window, browser when it's closed; --outside: browser always"),
    "clear-signins": (None, "empty sign-ins + site data of pages opened in the Job Finder window (VS Code keeps them outside this folder) - before removing the app"),
    "window-setup": (None, "installer step: Job Finder's VS Code profile + its extensions, plain progress lines"),
    "window-update": (None, "after update: the new window extension into Job Finder's profile now; says when the open window must restart"),
    "tui": ("tui", "terminal job browser (developers)"),
}


def run_module(module: str, args: list[str]) -> None:
    sys.argv = [module, *args]
    importlib.import_module(module).main()


def opens_as_tab(path: Path) -> bool:
    if path.suffix.lower() in SYSTEM_APP_SUFFIXES:
        return False
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
    return send_request({"url": url}, root, wait) is not None


def send_request(request: dict, root: Path, wait: float = LINK_WAIT) -> str | None:
    """Hand a request to Job Finder's window; its name once the extension took it, else None."""
    folder = root / LINK_DIR
    name = uuid.uuid4().hex
    temp, request_file = folder / f"{name}.tmp", folder / f"{name}.json"
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
        temp.write_text(json.dumps({**request, "t": int(time.time() * 1000)}), encoding="utf-8")
        retry_busy(lambda: os.replace(temp, request_file))
    except OSError:
        temp.unlink(missing_ok=True)
        return None
    deadline = time.monotonic() + wait
    while request_file.exists():
        if time.monotonic() >= deadline:
            try:
                retry_busy(request_file.unlink)  # taken back: the extension's rename now finds nothing
            except FileNotFoundError:
                return name  # it took it in the same moment
            except OSError:
                pass  # still held after the retries: browser anyway - a missed link is worse than two
            return None
        time.sleep(0.05)
    return name


def window_answer(name: str, root: Path, wait: float):
    """What the window answered request `name` in <name>.done (None: unreadable); TimeoutError when
    it took the request but said nothing in time."""
    done = root / LINK_DIR / f"{name}.done"
    deadline = time.monotonic() + wait
    while not done.exists():
        if time.monotonic() >= deadline:
            raise TimeoutError(name)
        time.sleep(0.05)
    try:
        answer = json.loads(done.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        answer = None
    done.unlink(missing_ok=True)
    return answer


# the window's sign-ins live in VS Code's storage for this folder, outside it (app/docs/app-window.md
# #s, #t): deleting the folder leaves them, and only the open window can empty them => asked through
# the link folder; extension.js answers in <name>.done once VS Code's own clear has run
CLEAR_REQUEST = "clear-signins"
# VS Code's clear took 186 ms (#s); past this the window took it but never said
CLEAR_WAIT = 10.0
CLEARED = "cleared: sign-ins + site data of pages opened in the Job Finder window"


def clear_signins(wait: float = LINK_WAIT, answer_wait: float = CLEAR_WAIT) -> None:
    import cfg
    import launch
    name = launch.vscode_running() and send_request({"do": CLEAR_REQUEST}, cfg.ROOT, wait)
    if not name:
        # also a VS Code w/o its browser (before 1.109): nothing kept there
        sys.exit("not cleared: the Job Finder window isn't open - open CEZ Job Finder, then run this again")
    try:
        answer = window_answer(name, cfg.ROOT, answer_wait)
    except TimeoutError:
        sys.exit("not sure it cleared: the window took the request but never answered - run this again")
    if not isinstance(answer, dict) or answer.get("ok") is not True:
        error = answer.get("error") if isinstance(answer, dict) else None
        sys.exit(f"not cleared: VS Code's clear failed ({error or 'no reason given'})")
    print(CLEARED)


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
            if path.suffix.lower() in SYSTEM_APP_SUFFIXES:
                print("opened in the computer's own app for this file (Word, Pages ...)")
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
    # window open but on the extension from before an update => no link folder watcher; say why
    if not outside and launch.window_behind():
        print(f"{launch.BEHIND}. {launch.RESTART_LINE}")


def check_settings() -> None:
    import cfg
    import launch
    config = cfg.load()
    wa = config.get("work_authorization") or {}
    if wa.get("authorized_us") and wa.get("needs_sponsorship"):
        # setup's old "allowed now, will need sponsorship later" option saved this pair; a CPT/OPT or
        # H-1B permit has limits, so "without restriction" forms now ask each time
        print("ask once: work permit says 'allowed without restriction' and 'needs sponsorship later' - "
              "CPT, OPT and H-1B work has limits. Ask the work-permit question again (job-setup)")
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
    elif name == "clear-signins":
        clear_signins()
    elif name == "window-setup":
        import launch
        launch.window_setup()
    elif name == "window-update":
        import launch
        launch.window_update()
    else:
        run_module(COMMANDS[name][0], args)


if __name__ == "__main__":
    main()
