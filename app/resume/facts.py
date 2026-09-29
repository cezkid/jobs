"""Per-bullet bookkeeping kept out of the user's sight.

`metrics` (the number phrases inside a claim) and `stack` (the technology names inside it) are
the tailorer's and lint's working notes, not facts the user recognizes as theirs: they doubled
the length of My Resume/Resume details.yml and buried the 32 lines that are actually their
career. They live here instead, hidden in `.data/`, keyed by the claim itself - so reordering or
rewriting bullets can never hand one bullet's numbers to another one's text, and a claim the
user reworded simply loses its notes until the next import writes them again.
"""
from pathlib import Path

import yaml

import cfg
import locks

PATH = cfg.DATA / "resume-index.yml"
KEYS = ("metrics", "stack")
FLAGS = ("ai_work",)
BUSY = "another chat is saving your resume right now - try again in a minute"


def key(claim: str) -> str:
    return " ".join(claim.split()).casefold()


def read(path: Path | None = None) -> dict:
    path = path or PATH
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def collect(master: dict) -> dict:
    """Internal-shape master -> {claim: {metrics, stack}}, skipping bullets with neither."""
    out = {}
    for entry in [*(master.get("roles") or []), *(master.get("projects") or [])]:
        for bullet in entry.get("bullets") or []:
            noted = {k: list(bullet[k]) for k in KEYS if bullet.get(k)}
            noted |= {k: True for k in FLAGS if bullet.get(k)}
            if noted and isinstance(bullet.get("claim"), str):
                out[key(bullet["claim"])] = noted
    return out


def write(master: dict, path: Path | None = None) -> Path:
    path = path or PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump(collect(master), sort_keys=True, allow_unicode=True, width=10_000)
    locks.write_atomic(path, "# Working notes for app/resume - written by the program, never by hand.\n" + body)
    return path


def resume_lock(notes: Path | None = None):
    """Held while a command rewrites Resume details.yml + these notes as one step."""
    return locks.held((notes or PATH).parent / "resume.lock", BUSY)


def attach(claim: str, index: dict) -> dict:
    """Notes for one claim. Reword the claim and its notes drop off rather than follow it."""
    noted = index.get(key(claim)) or {}
    attached = {k: [v for v in noted.get(k) or [] if isinstance(v, str)] for k in KEYS}
    return attached | {k: True for k in FLAGS if noted.get(k)}
