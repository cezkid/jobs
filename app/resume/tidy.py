"""Rewrite My Resume/Resume details.yml as plain facts the user can edit.

The imported shape carried four fields of program bookkeeping around every single bullet -
217 of 380 lines in the first real file, with the 32 lines of actual career buried inside them.
Those fields are all derivable or recoverable (resume/schema.py #expand, resume/facts.py), so
they move out and what is left is the user's own words, one sentence per line, under headings
written in plain English. Reads back identical: the rewrite is refused unless it does.
"""
import argparse
import copy
import re
import shutil
import sys
from pathlib import Path

import yaml

import cfg
from resume import facts, schema

HEADER = [
    "# Your resume facts, the only place CEZ Job Finder reads them from. Your wording always wins.",
    "# Employer, job title and dates: change them only to fix a mistake - employers check them.",
    "# Keep the spacing as it is. Dates are year-month, like 2023-02, or a year alone, like 2023.",
]
NOTES = {
    "contact": ["# Your name and how an employer reaches you."],
    "headline": ["# One line above the summary: your real title and main skills. Optional."],
    "summary": ["# The short pitch at the top of the page - up to four lines."],
    "roles": [
        "# Your jobs, newest first. Under each one, every line is one thing you did there.",
        "# 2023-02 means February 2023. The job you are in now ends with the word: present",
    ],
    "career_break": ["# Time away from work, said plainly: reason, then start and end. Shown with your jobs."],
    "projects": ["# Worth showing but not a job: side projects, teaching. Dates may be left out."],
    "skills": ["# The skills block. 'group' is the heading, 'items' are the words under it."],
    "education": ["# Schools, newest first. hide_year: true leaves the year off the page."],
    "certifications": ["# Licences and certifications. Leave it as [] if you have none."],
    "languages": ["# Languages you speak, one per line, level in brackets: Spanish (Fluent).",
                  "# Levels: Native, Fluent, Professional, Conversational, Basic."],
    "other": ["# Anything else worth a heading: volunteer work, awards, clearances. Printed as written."],
}
ORDER = ["contact", "headline", "summary", "roles", "career_break", "projects", "skills", "education", "certifications",
         "other", "languages"]
ENTRY_ORDER = ["company", "name", "title", "heading", "reason", "location", "blurb", "start", "end", "ai_era",
               "bullets", "lines"]
ORDERS = {"contact": ["name", "email", "phone", "location", "links"]}
# plain scalar would read back as something else: leading indicator, a key, a comment, a number
SPECIAL = re.compile(r"""^[\s#&*!|>%@`,\[\]{}?:'"-]|:\s|\s#|:$|\s$""")
RESERVED = re.compile(r"^(true|false|null|yes|no|on|off|~|-?\d[\d,]*(\.\d+)?)$", re.I)


def scalar(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if not isinstance(value, str):
        return str(value)
    if not value or SPECIAL.search(value) or RESERVED.match(value):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def keys_in_order(mapping: dict, order: list[str]) -> list[str]:
    return [k for k in order if k in mapping] + [k for k in mapping if k not in order]


def emit(key: str, value, indent: int, order: list[str] | None = None) -> list[str]:
    pad, order = " " * indent, ORDERS.get(key) or order or ENTRY_ORDER
    if isinstance(value, dict):
        if not value:
            return [f"{pad}{key}: {{}}"]
        return [f"{pad}{key}:", *(l for k in keys_in_order(value, order) for l in emit(k, value[k], indent + 2, order))]
    if isinstance(value, list):
        if not value:
            return [f"{pad}{key}: []"]
        # list items sit at their key's own indent, the shape yaml.safe_dump writes
        return [f"{pad}{key}:", *(l for item in value for l in item_lines(item, indent, order))]
    return [f"{pad}{key}: {scalar(value)}"]


def item_lines(item, indent: int, order: list[str] | None = None) -> list[str]:
    pad = " " * indent
    if isinstance(item, dict):
        body = [l for k in keys_in_order(item, order or ENTRY_ORDER) for l in emit(k, item[k], indent + 2, order)]
        body[0] = f"{pad}- " + body[0][indent + 2:]
        return body
    return [f"{pad}- {scalar(item)}"]


def dump(master: dict, extra: list[str] | None = None) -> str:
    lines = [*HEADER, *(extra or [])]
    for key in keys_in_order(master, ORDER):
        lines += ["", *NOTES.get(key, [])]
        lines += emit(key, master[key], 0) if isinstance(master[key], (dict, list)) else [f"{key}: {scalar(master[key])}"]
    text = "\n".join(lines) + "\n"
    if yaml.safe_load(text) != master:
        raise ValueError("rewritten resume file would not read back the same - left untouched")
    return text


def strip(master: dict) -> dict:
    """Internal shape -> the user's shape: ids, notes and derivable flags out.

    An id the file does not say is worked out again at load (resume/schema.py #expand), so almost
    every one of them can go. A hand-written id that would not come back the same - older files
    named bullets after their subject - is written out instead of quietly renumbering work the
    user has already tailored against.
    """
    out = dict(master)
    for key in ("roles", "projects"):
        if isinstance(out.get(key), list):
            out[key] = [strip_entry(e) for e in out[key]]
    for _ in range(2):
        if not keep_ids(out, schema.expand(copy.deepcopy(out)), master):
            break
    return out


def keep_ids(out: dict, rebuilt: dict, master: dict) -> bool:
    """Write back any id the rewritten file would not hand out again. True when one was."""
    kept = False
    for key in ("roles", "projects"):
        for entry, loaded, source in zip(out.get(key) or [], rebuilt.get(key) or [], master.get(key) or []):
            if source.get("id") and loaded.get("id") != source["id"]:
                entry["id"], kept = source["id"], True
            for i, (bullet, was) in enumerate(zip(loaded.get("bullets") or [], source.get("bullets") or [])):
                if isinstance(was, dict) and was.get("id") and bullet.get("id") != was["id"]:
                    entry["bullets"][i], kept = {"id": was["id"], "claim": was["claim"]}, True
    return kept


def strip_entry(entry: dict) -> dict:
    out = {k: v for k, v in entry.items() if k != "id"}
    # dates already say it; only a disagreement is worth a line of its own
    if out.get("ai_era", False) == schema.in_ai_era(entry):
        out.pop("ai_era", None)
    out["bullets"] = [b["claim"] if isinstance(b, dict) and isinstance(b.get("claim"), str) else b
                      for b in entry.get("bullets") or []]
    return out


def tidy(path: Path, notes: Path | None = None) -> tuple[Path, Path, int, int]:
    before = len(path.read_text(encoding="utf-8").splitlines())
    master = schema.load(path, notes)
    facts.write(master, notes)
    text = dump(strip(master))
    backup = (notes or facts.PATH).parent / f"{path.stem} before tidy.yml"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, backup)
    path.write_text(text, encoding="utf-8")
    if schema.load(path, notes) != master:
        shutil.copyfile(backup, path)
        raise ValueError("rewritten resume file did not hold the same facts - put the old one back")
    return path, backup, before, len(text.splitlines())


def main() -> None:
    ap = argparse.ArgumentParser(description="rewrite resume details as plain facts; program notes move out of sight")
    ap.add_argument("--master", type=Path, help="resume details file (default: the one in settings)")
    args = ap.parse_args()
    path = args.master or cfg.resume_path(cfg.load(), "master")
    if not path.exists():
        sys.exit(f"{path} missing - import the resume PDF first")
    try:
        path, backup, before, after = tidy(path)
    except ValueError as e:
        sys.exit(str(e))
    print(f"{path}: {before} lines -> {after}; notes in {facts.PATH}, old file kept at {backup}")


if __name__ == "__main__":
    main()
