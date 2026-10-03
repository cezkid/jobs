import sys
from pathlib import Path

import cfg
import launch

# one word, written by the installer (or `ai NAME`); private, under .data => kept by updates
CHOICE_FILE = cfg.DATA / "ai"
NAMES = {"claude": "Claude", "chatgpt": "ChatGPT", "copilot": "GitHub Copilot"}
# Copilot never inferred: its chat is built into VS Code (1.140+) for everyone => says nothing
EXTENSIONS = {"claude": launch.CLAUDE_EXTENSION, "chatgpt": "openai.chatgpt"}


def current(path: Path | None = None, extensions: Path | None = None) -> str | None:
    path = path or CHOICE_FILE
    if path.is_file():
        word = path.read_text(encoding="utf-8").strip().lower()
        if word in NAMES:
            return word
    for name, extension in EXTENSIONS.items():
        if launch.has_extension(extension, extensions):
            return name
    return None


def set(name: str, path: Path | None = None) -> str:
    path = path or CHOICE_FILE
    word = name.strip().lower()
    if word not in NAMES:
        raise ValueError(f"unknown AI {name!r}: pick one of {', '.join(NAMES)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(word + "\n", encoding="utf-8")
    return word


def main() -> None:
    args = sys.argv[1:]
    if not args:
        name = current()
        print(f"AI: {NAMES[name]} ({name})" if name else "AI: not chosen yet - run: uv run app/jobs.py ai claude | chatgpt | copilot")
        return
    try:
        name = set(args[0])
    except ValueError as e:
        sys.exit(str(e))
    print(f"AI set to {NAMES[name]}. Close and reopen CEZ Job Finder to use it.")


if __name__ == "__main__":
    main()
