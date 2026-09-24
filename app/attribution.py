"""Claude credit on fixes sent upstream: follow the user's own Claude Code setting.

Claude Code adds "Co-Authored-By: Claude" to commits and "Generated with Claude Code" to PR text
unless `attribution` (or the older `includeCoAuthoredBy`) in its settings turns that off. An
assistant can still type the lines by hand, so when the setting is off `strip` removes them and
`hook` installs a commit-msg hook that runs `strip` on every commit.
Standard library only: the hook runs this file directly, without the program's packages.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KINDS = ("commit", "pr")
CREDIT = re.compile(
    r"^\s*(co-authored-by:\s*claude\b.*|.*generated with \[?claude code\]?.*|.*noreply@anthropic\.com.*"
    r"|claude-session:.*|.*claude\.ai/code/session.*)\s*$", re.I)
OFF = {"commit": "", "pr": "", "sessionUrl": False}
HOOK_MARK = "# Job Finder: strip Claude credit when the user's setting is off"


def user_settings() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "settings.json"


def settings_files(root: Path = ROOT) -> list[Path]:
    """Claude Code's order, later wins: user, project, project-local."""
    return [user_settings(), root / ".claude" / "settings.json", root / ".claude" / "settings.local.json"]


def merged(root: Path = ROOT) -> dict:
    out = {}
    for path in settings_files(root):
        if path.exists():
            out.update(json.loads(path.read_text(encoding="utf-8") or "{}"))
    return out


def state(kind: str, settings: dict) -> str | None:
    """'off' / 'on' for commit or pr credit; None = never chosen, so Claude Code credits by default."""
    attr = settings.get("attribution")
    if attr is False:
        return "off"
    if isinstance(attr, dict) and kind in attr:
        return "off" if attr[kind] == "" else "on"
    legacy = settings.get("includeCoAuthoredBy")
    return None if legacy is None else "on" if legacy else "off"


def strip(text: str) -> str:
    kept = [line for line in text.splitlines() if not CREDIT.match(line)]
    return "\n".join(kept).rstrip() + "\n"


def choose(on: bool, path: Path | None = None) -> None:
    """Write the user's answer into their own Claude Code settings, keeping every other key."""
    path = path or user_settings()
    data = json.loads(path.read_text(encoding="utf-8") or "{}") if path.exists() else {}
    data.pop("includeCoAuthoredBy", None)
    if on:
        data.pop("attribution", None)
    else:
        data["attribution"] = {**(data.get("attribution") or {}), **OFF}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def install_hook(repo: Path) -> str:
    common = subprocess.run(["git", "-C", str(repo), "rev-parse", "--git-common-dir"],
                            capture_output=True, text=True, check=True).stdout.strip()
    hook = (repo / common if not Path(common).is_absolute() else Path(common)) / "hooks" / "commit-msg"
    if hook.exists() and HOOK_MARK not in hook.read_text(encoding="utf-8"):
        return f"kept: {hook} is someone else's hook; add `{Path(__file__)} strip \"$1\"` to it by hand"
    hook.parent.mkdir(parents=True, exist_ok=True)
    # program moved or an old branch checked out -> let the commit through untouched, never block it
    hook.write_text(f'#!/bin/sh\n{HOOK_MARK}\npy="{sys.executable}"; f="{Path(__file__).resolve()}"\n'
                    '[ -x "$py" ] && [ -f "$f" ] || exit 0\nexec "$py" "$f" strip "$1"\n', encoding="utf-8")
    hook.chmod(0o755)
    return f"installed: {hook}"


def describe(settings: dict) -> str:
    said = {k: state(k, settings) for k in KINDS}
    if all(v is None for v in said.values()):
        return "Claude credit: not set - ask the user (Claude Code adds it by default)"
    return "Claude credit: " + ", ".join(f"{k} {v or 'on (default)'}" for k, v in said.items())


def main() -> None:
    ap = argparse.ArgumentParser(description="Claude credit on commits + PR text, per the user's Claude Code setting")
    sub = ap.add_subparsers(dest="action")
    sub.add_parser("status", help="print the setting (default)")
    sub.add_parser("off", help="leave Claude's name off: writes the user's Claude Code settings")
    sub.add_parser("on", help="let Claude Code credit Claude again")
    s = sub.add_parser("strip", help="remove credit lines from a commit message or PR body file when the setting is off")
    s.add_argument("file")
    s.add_argument("--pr", action="store_true", help="file is PR text, not a commit message")
    h = sub.add_parser("hook", help="install the commit-msg hook in a git checkout")
    h.add_argument("repo", nargs="?", default=str(ROOT / ".data" / "upstream"))
    args = ap.parse_args()
    if args.action in ("off", "on"):
        choose(args.action == "on")
        print(f"saved in {user_settings()}")
    elif args.action == "strip":
        if state("pr" if args.pr else "commit", merged()) == "off":
            path = Path(args.file)
            path.write_text(strip(path.read_text(encoding="utf-8")), encoding="utf-8")
    elif args.action == "hook":
        print(install_hook(Path(args.repo)))
    else:
        print(describe(merged()))


if __name__ == "__main__":
    main()
