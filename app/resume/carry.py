"""Re-import a resume without losing what the user added since the last one.

Resume details are the user's file: after the first import they reword lines, answer the
fill-the-gaps questions, add a break, hide a year, set a language level, give a legal name. A new
PDF knows none of that. Importing it used to overwrite the file whole, with no backup. Now
`left_behind` lists what the new read lacks, in three groups the user picks from once, and
`carry` puts back only the groups they keep. Nothing is deleted from the new read; a backup of
the old file is written first.

Matching (case, spaces and punctuation never make two lines differ; numbers always do - "20s to
1s" is not "30s to 1s"): jobs by employer (legal suffix aside) + title, else employer + start
date (a title corrected by hand); projects, certifications, sections by name; schools by name.
A kept line that shares half its words w/ a line the PDF has is the user's rewording of it and
replaces it; below that it is a line of their own and is added. Measured on one user's 10 kept
versions (2026-10-01): unrelated lines in the same job topped out at 0.38 overlap, rewordings at
0.6 or more.
"""
import re
import shutil
from datetime import datetime
from pathlib import Path

import cfg
from resume import schema

GROUPS = {
    "lines": "your wording, or lines + skills added since the last import",
    "entries": "jobs, projects, schools, certifications, breaks or sections the new resume file lacks",
    "details": "details the PDF can't carry: legal name, hidden years, language levels, notes on a job",
}
REWORDED = 0.5
DATE_WORDS = {"jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec", "pre", "cur", "now"}
SECTIONS = ("roles", "projects", "education", "certifications", "other")
LEGAL = re.compile(r"[,.]?\s+(inc|llc|ltd|corp|corporation|co|company|plc|lp|llp)\.?$", re.I)


def claim_key(text: str) -> str:
    return re.sub(r"[\W_]+", "", (text or "").casefold())


def words(text: str) -> set[str]:
    return set(re.findall(r"\w+", (text or "").casefold()))


def overlap(a: str, b: str) -> float:
    wa, wb = words(a), words(b)
    return len(wa & wb) / max(len(wa | wb), 1)


def company(name) -> str:
    return claim_key(LEGAL.sub("", (name or "").strip()))


def name_of(section: str, entry: dict) -> str:
    keys = {"roles": "title", "projects": "name", "education": "institution", "certifications": "name", "other": "heading"}
    return claim_key(entry.get(keys[section]))


def text_of(bullet) -> str:
    return bullet.get("claim", "") if isinstance(bullet, dict) else str(bullet)


def match(section: str, old: dict, new: list[dict]) -> int | None:
    for i, entry in enumerate(new):
        if name_of(section, entry) == name_of(section, old) and (
                section != "roles" or company(entry.get("company")) == company(old.get("company"))):
            return i
    if section == "roles":
        return next((i for i, e in enumerate(new) if company(e.get("company")) == company(old.get("company"))
                     and e.get("start") and e.get("start") == old.get("start")), None)
    return None


def label(section: str, entry: dict) -> str:
    if section == "roles":
        return f"{entry.get('title')} at {entry.get('company')} ({entry.get('start', '?')})"
    if section == "career_break":
        return f"break {entry.get('start')} - {entry.get('end')}"
    return str(entry.get({"projects": "name", "education": "institution", "certifications": "name",
                          "other": "heading"}[section]))


def moved_to_projects(section: dict, new: dict) -> bool:
    """An older import kept a student's Activities as plain lines; this one reads each club as a
    project with its role. Every old line found there = the same facts, not a section lost."""
    found = " ".join(claim_key(" ".join([p.get("name") or "", p.get("role") or "", *map(text_of, p.get("bullets") or [])]))
                     for p in new.get("projects") or [])
    lines = section.get("lines") or []
    # dates are the project's start and end now: their words ("Sep", "2024", "Present") aren't looked for
    words = [claim_key(w) for line in lines for w in re.findall(r"\w+", line)
             if not (w.isdigit() or w.casefold()[:3] in DATE_WORDS)]
    return bool(lines) and all(w in found for w in words if w)


def in_school_fields(details: str, school: dict) -> bool:
    """Old details ("GPA: 3.8; Relevant coursework: ...") now read into the school's own fields."""
    return bool(school.get("gpa") or school.get("coursework")) and bool(re.search(r"gpa|coursework|courses", str(details), re.I))


def left_behind(old: dict, new: dict) -> dict[str, list[dict]]:
    """What the old file says that the new read lacks, by group. Each item knows where it goes."""
    out: dict[str, list[dict]] = {g: [] for g in GROUPS}
    if not isinstance(old, dict):
        return out
    for key, value in (old.get("contact") or {}).items():
        if value not in (None, "", []) and key not in (new.get("contact") or {}):
            out["details"].append({"kind": "contact", "key": key, "value": value, "say": f"contact {key}"})
    for key in ("headline", "summary"):
        if old.get(key) and claim_key(old[key]) != claim_key(new.get(key)):
            out["lines"].append({"kind": "top", "key": key, "value": old[key], "say": f"your {key}"})
    for section in SECTIONS:
        new_entries = new.get(section) or []
        for entry in old.get(section) or []:
            if not isinstance(entry, dict):
                continue
            at = match(section, entry, new_entries)
            if at is None:
                if not (section == "other" and moved_to_projects(entry, new)):
                    out["entries"].append({"kind": "entry", "section": section, "value": entry, "say": label(section, entry)})
                continue
            there = new_entries[at]
            for key, value in entry.items():
                if section == "education" and key == "details" and in_school_fields(value, there):
                    continue
                if key not in ("bullets", "lines", "id") and key not in there and value not in (None, ""):
                    out["details"].append({"kind": "field", "section": section, "at": at, "key": key, "value": value,
                                           "say": f"{key} on {label(section, there)}"})
            have = {claim_key(text_of(b)) for b in there.get("bullets") or there.get("lines") or []}
            for line in entry.get("bullets") or entry.get("lines") or []:
                if claim_key(text_of(line)) not in have:
                    out["lines"].append({"kind": "line", "section": section, "at": at, "value": text_of(line),
                                         "say": text_of(line)})
    known_breaks = {(b.get("start"), b.get("end")) for b in new.get("career_break") or []}
    for gap in old.get("career_break") or []:
        if isinstance(gap, dict) and (gap.get("start"), gap.get("end")) not in known_breaks:
            out["entries"].append({"kind": "entry", "section": "career_break", "value": gap, "say": label("career_break", gap)})
    new_groups = {claim_key(g.get("group")): g for g in new.get("skills") or []}
    for group in old.get("skills") or []:
        have = new_groups.get(claim_key(group.get("group")))
        known = {claim_key(i) for i in (have or {}).get("items") or []}
        for item in group.get("items") or []:
            if claim_key(item) not in known:
                out["lines"].append({"kind": "skill", "group": group.get("group"), "value": item, "say": f"skill {item}"})
    new_languages = {language_name(x): x for x in new.get("languages") or []}
    for line in old.get("languages") or []:
        if new_languages.get(language_name(line)) != line:
            out["details"].append({"kind": "language", "value": line, "say": f"language {line}"})
    return out


def language_name(line: str) -> str:
    return claim_key(str(line).split("(")[0])


def carry(new: dict, left: dict[str, list[dict]], keep: set[str]) -> dict:
    """`new` + the kept groups. Reworded lines replace the PDF's version; kept entries go in
    newest-first like any other."""
    out = {k: (list(v) if isinstance(v, list) else dict(v) if isinstance(v, dict) else v) for k, v in new.items()}
    for section in (*SECTIONS, "career_break"):
        if section in out:
            out[section] = [dict(e) if isinstance(e, dict) else e for e in out[section]]
    for group in keep:
        for item in left.get(group) or []:
            put(out, item)
    for section in ("roles", "projects"):
        if all(isinstance(e, dict) and e.get("start") for e in out.get(section) or []) and out.get(section):
            out[section] = schema.newest_first(out[section])
    return out


def put(out: dict, item: dict) -> None:
    kind = item["kind"]
    if kind == "contact":
        out.setdefault("contact", {})[item["key"]] = item["value"]
    elif kind == "top":
        out[item["key"]] = item["value"]
    elif kind == "entry":
        out.setdefault(item["section"], []).append(item["value"])
    elif kind == "field":
        out[item["section"]][item["at"]][item["key"]] = item["value"]
    elif kind == "line":
        entry = out[item["section"]][item["at"]]
        field = "bullets" if "bullets" in entry or item["section"] in ("roles", "projects") else "lines"
        lines = list(entry.get(field) or [])
        best = max(range(len(lines)), key=lambda i: overlap(text_of(lines[i]), item["value"]), default=None)
        if best is not None and overlap(text_of(lines[best]), item["value"]) >= REWORDED:
            lines[best] = item["value"]
        else:
            lines.append(item["value"])
        entry[field] = lines
    elif kind == "skill":
        groups = out.setdefault("skills", [])
        group = next((g for g in groups if claim_key(g.get("group")) == claim_key(item["group"])), None)
        if group is None:
            groups.append({"group": item["group"], "items": [item["value"]]})
        else:
            group["items"] = [*group.get("items", []), item["value"]]
    elif kind == "language":
        languages = list(out.get("languages") or [])
        at = next((i for i, x in enumerate(languages) if language_name(x) == language_name(item["value"])), None)
        if at is None:
            languages.append(item["value"])
        else:
            languages[at] = item["value"]
        out["languages"] = languages


def kept(keep: str | None, left: dict[str, list[dict]]) -> set[str]:
    """--keep words -> groups. all / none / a comma list of group names."""
    if keep is None:
        return set()
    words_given = {w.strip() for w in keep.split(",") if w.strip()}
    if "all" in words_given:
        return set(GROUPS)
    unknown = words_given - set(GROUPS) - {"none"}
    if unknown:
        raise SystemExit(f"--keep: no group {sorted(unknown)}; use {', '.join(GROUPS)}, all or none")
    return words_given & set(GROUPS)


def describe(left: dict[str, list[dict]]) -> list[str]:
    out = []
    for group, items in left.items():
        if items:
            shown = "; ".join(i["say"] for i in items[:3]) + (f"; +{len(items) - 3} more" if len(items) > 3 else "")
            out.append(f"  {group} ({len(items)}) - {GROUPS[group]}: {shown}")
    return out


def backup(path: Path) -> Path:
    """Timestamped, so a second import never overwrites the copy a first one kept."""
    target = cfg.DATA / f"Resume details before import {datetime.now():%Y-%m-%d %H%M}.yml"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, target)
    return target
