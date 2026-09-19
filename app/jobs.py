import importlib
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

# VS Code ships no PDF viewer => system app
SYSTEM_VIEWER_SUFFIXES = {".pdf"}
COMMANDS = {
    "find": (None, "check for new jobs, then list ranked matches (rank args pass through)"),
    "poll": ("ingest.freehire", "check for new jobs only"),
    "rank": ("rank", "list ranked matches; --limit N, --suspects"),
    "probe": ("ingest.probe", "count jobs a candidate search would match"),
    "check-settings": (None, "validate search settings"),
    "email": ("alert", "email unseen matches; --dry-run prints instead"),
    "daily": ("daily", "poll + notify (or email if set up), as the daily schedule runs it"),
    "autorun": ("autorun", "daily schedule on | off | status"),
    "resume-import": ("resume.import_pdf", "resume PDF -> resume details: prepare | finish"),
    "resume-render": ("resume.render", "render untailored resume PDF + checks"),
    "resume-lint": ("resume.lint", "wording + honesty lint on untailored resume"),
    "tailor": ("resume.tailor", "tailored resume for one job: posting | prepare | check"),
    "update": ("update", "get latest Job Finder program; never touches My folders"),
    "launch": ("launch", "open VS Code on START HERE, Claude tab pre-filled (Desktop launcher)"),
    "open": (None, "open file or link for user: VS Code tab, PDF in system viewer, link in browser"),
    "tui": ("tui", "terminal job browser (developers)"),
}


def run_module(module: str, args: list[str]) -> None:
    sys.argv = [module, *args]
    importlib.import_module(module).main()


def open_for_user(target: str) -> None:
    path = Path(target)
    code = shutil.which("code")
    if path.exists() and code and path.suffix.lower() not in SYSTEM_VIEWER_SUFFIXES:
        subprocess.run([code, "-r", str(path.resolve())], check=False)
    else:
        webbrowser.open(path.resolve().as_uri() if path.exists() else target)


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
        import cfg
        cfg.load()
        print(f"ok: {cfg.config_path()}")
    elif name == "open":
        open_for_user(" ".join(args))
    else:
        run_module(COMMANDS[name][0], args)


if __name__ == "__main__":
    main()
