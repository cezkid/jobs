"""Window look: match the computer, light or dark. One word in .data/look, outside the window's
settings file (the launcher rewrites that at every launch). Missing or unknown word = auto.
Saving rewrites the window's settings at once => VS Code switches live, no reload."""
import sys
from pathlib import Path

import cfg

CHOICE_FILE = cfg.DATA / "look"
# word -> plain words (command output, Today's switch says the same)
NAMES = {"auto": "match my computer", "light": "light", "dark": "dark"}
# chat words people use -> word
ALIASES = {"match": "auto", "match my computer": "auto", "computer": "auto", "system": "auto", "light-mode": "light", "dark-mode": "dark"}


def current(path: Path | None = None) -> str:
    try:
        word = (path or CHOICE_FILE).read_text(encoding="utf-8").strip().lower()
    except (OSError, UnicodeDecodeError):
        return "auto"
    return word if word in NAMES else "auto"


def set(word: str, path: Path | None = None) -> str:
    word = ALIASES.get(word.strip().lower(), word.strip().lower())
    if word not in NAMES:
        raise ValueError(f"unknown look {word!r}: pick one of {', '.join(NAMES)}")
    path = path or CHOICE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(word + "\n", encoding="utf-8")
    return word


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(f"Look: {NAMES[current()]}.")
        return
    try:
        word = set(args[0])
    except ValueError as e:
        sys.exit(str(e))
    import launch
    launch.write_workspace(launch.chosen_ai())
    print(f"Look: {NAMES[word]}. Switched.")


if __name__ == "__main__":
    main()
