import argparse
import re
import shutil
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

import pymupdf
import yaml

import cfg
from resume import handoff, schema

ZERO_WIDTH = re.compile("[\u200b\u200c\u200d\u2060\ufeff]")
LINE_BULLET = re.compile("^[ \t]*[\u25cf\u2022\u25aa\u25e6\u00b7]", re.M)
FOLD = str.maketrans({
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u00a0": " ", "\u202f": " ",
})
WHITESPACE = re.compile(r"\s+")
WORD = re.compile(r"\w+")
# subset font w/o ToUnicode map extracts glyph ids => text mostly non-letters
MIN_ALPHA_RATIO = 0.5
# every source word lands in master; headings excluded
MIN_RECOVERY = 0.98
MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
ENDPOINT = re.compile(r"^(?:(?P<month>[a-z]{3})[a-z]*\.?\s+)?(?P<year>\d{4})$")
RANGE_SEP = re.compile(r"\s*-\s*|\s+to\s+")
PRESENT_WORDS = {"present", "current", "now"}
NON_SLUG = re.compile(r"[^a-z0-9]+")

SYSTEM = """You map resume text extracted from a PDF onto fixed fields. You never write, rephrase, correct or expand.

Rules:
- Every string you emit is copied character-for-character from the source text. Only allowed change: joining a line wrapped across a line break with one space, and dropping bullet glyphs.
- Never add words: no legal suffixes on company names, no https:// on links, no expanded abbreviations, no fixed typos or capitalization.
- `dates` = the exact calendar date range from the source (e.g. "Feb 2023 - Oct 2026", "2019 - 2021"); null when the source gives none. Durations ("6 Summers") stay inside the claim, never in `dates`.
- Two titles under one company = two roles, each with its own dates and bullets.
- `blurb` = company description line (industry, product, website) exactly as written.
- `metrics` = verbatim number phrases inside the claim. `stack` = verbatim technology names inside the claim.
- `ai_work` true only when the claim itself describes AI/LLM work.
- Skills: `group` is your short label; `items` = each pipe- or comma-separated entry copied verbatim.
- Every non-heading source line must land in some field."""

STRING, NULLABLE, STRINGS, obj, array = handoff.STRING, handoff.NULLABLE, handoff.STRINGS, handoff.obj, handoff.array
TASK = cfg.DATA / "resume-task.md"
ANSWER = cfg.DATA / "resume-mapped.json"
FINISH = "uv run app/jobs.py resume-import finish"
BULLET = obj(claim=STRING, metrics=STRINGS, stack=STRINGS, ai_work={"type": "boolean"})
MAPPED_SCHEMA = obj(
    contact=obj(name=STRING, email=STRING, phone=NULLABLE, location=STRING, links=STRINGS),
    summary=NULLABLE,
    roles=array(obj(
        company=STRING, title=STRING, location=NULLABLE, blurb=NULLABLE, dates=STRING, bullets=array(BULLET),
    )),
    projects=array(obj(name=STRING, dates=NULLABLE, bullets=array(BULLET))),
    skills=array(obj(group=STRING, items=STRINGS)),
    education=array(obj(institution=STRING, degree=STRING, field=NULLABLE, details=NULLABLE, end=NULLABLE)),
    certifications=array(obj(name=STRING, issuer=NULLABLE, date=NULLABLE)),
    languages=STRINGS,
)


def extract(pdf: Path) -> str:
    # content-stream order, never pymupdf4llm: its column detection interleaved two-column page 2 (measured 2026-09-16)
    with pymupdf.open(pdf) as doc:
        raw = "\n".join(page.get_text() for page in doc)
    text = LINE_BULLET.sub("", ZERO_WIDTH.sub("", raw))
    visible = [c for c in text if not c.isspace()]
    if not visible:
        raise ValueError(f"{pdf}: no text layer (scanned?)")
    alpha = sum(c.isalpha() for c in visible) / len(visible)
    if alpha < MIN_ALPHA_RATIO:
        raise ValueError(f"{pdf}: {alpha:.0%} letters - fonts lack ToUnicode map, text is glyph ids")
    return text


def normalize(value: str) -> str:
    return WHITESPACE.sub(" ", ZERO_WIDTH.sub("", value).translate(FOLD)).strip().casefold()


def traced_strings(mapped: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []

    def add(path: str, value) -> None:
        if isinstance(value, str) and value.strip():
            out.append((path, value))

    for key, value in mapped["contact"].items():
        for i, v in enumerate(value) if isinstance(value, list) else [(None, value)]:
            add(f"contact.{key}" + ("" if i is None else f"[{i}]"), v)
    add("summary", mapped["summary"])
    for kind, named in (("roles", ("company", "title", "location", "blurb", "dates")), ("projects", ("name", "dates"))):
        for i, entry in enumerate(mapped[kind]):
            for key in named:
                add(f"{kind}[{i}].{key}", entry[key])
            for j, bullet in enumerate(entry["bullets"]):
                where = f"{kind}[{i}].bullets[{j}]"
                add(f"{where}.claim", bullet["claim"])
                for key in ("metrics", "stack"):
                    for k, v in enumerate(bullet[key]):
                        add(f"{where}.{key}[{k}]", v)
    for i, group in enumerate(mapped["skills"]):
        for k, v in enumerate(group["items"]):
            add(f"skills[{i}].items[{k}]", v)
    for i, school in enumerate(mapped["education"]):
        for key in ("institution", "degree", "field", "details", "end"):
            add(f"education[{i}].{key}", school[key])
    for i, cert in enumerate(mapped["certifications"]):
        for key in ("name", "issuer", "date"):
            add(f"certifications[{i}].{key}", cert[key])
    for i, v in enumerate(mapped["languages"]):
        add(f"languages[{i}]", v)
    return out


def untraced(mapped: dict, source: str) -> list[str]:
    haystack = normalize(source)
    return [f"{path}: {value!r}" for path, value in traced_strings(mapped) if normalize(value) not in haystack]


def content_lines(source: str) -> list[str]:
    # all-caps line = section heading => carries no fact
    return [line.strip() for line in source.splitlines() if WORD.search(line) and not line.isupper()]


def recovery(mapped: dict, source: str) -> tuple[float, list[str]]:
    got = Counter(w for _, v in traced_strings(mapped) for w in WORD.findall(normalize(v)))
    lines = content_lines(source)
    want = Counter(w for line in lines for w in WORD.findall(normalize(line)))
    ratio = sum((want & got).values()) / max(sum(want.values()), 1)
    dropped = [line for line in lines if any(w not in got for w in WORD.findall(normalize(line)))]
    return ratio, dropped


def slug(value: str) -> str:
    return NON_SLUG.sub("-", value.casefold()).strip("-")


def unique(base: str, taken: set[str]) -> str:
    candidate, n = base, 2
    while candidate in taken:
        candidate, n = f"{base}-{n}", n + 1
    taken.add(candidate)
    return candidate


def parse_endpoint(text: str, is_end: bool, where: str, today: date, assumptions: list[str]) -> str | None:
    value = normalize(text)
    if value in PRESENT_WORDS:
        return schema.PRESENT
    match = ENDPOINT.match(value)
    if not match or (match["month"] and match["month"] not in MONTHS):
        # left unset => schema flags field missing; hand edit settles it
        assumptions.append(f"{where}: unparseable date {text!r}, set by hand")
        return None
    if match["month"]:
        month = MONTHS.index(match["month"]) + 1
    else:
        # year-only source => widest honest span, flagged for hand edit
        month = 12 if is_end else 1
        assumptions.append(f"{where}: {text!r} year only -> month {month:02d}")
    result = f"{match['year']}-{month:02d}"
    if schema.month_index(result, today) > schema.month_index(schema.PRESENT, today):
        assumptions.append(f"{where}: {result} after today")
    return result


def parse_range(text: str | None, where: str, today: date, assumptions: list[str]) -> dict:
    if not text:
        return {}
    parts = RANGE_SEP.split(normalize(text))
    if len(parts) != 2:
        assumptions.append(f"{where}: dates {text!r} not start - end, set by hand")
        return {}
    return {
        "start": parse_endpoint(parts[0], False, f"{where}.start", today, assumptions),
        "end": parse_endpoint(parts[1], True, f"{where}.end", today, assumptions),
    }


def build_bullets(bullets: list[dict], entry_id: str) -> list[dict]:
    out = []
    for n, b in enumerate(bullets, 1):
        bullet = {"id": f"{entry_id}-{n}", "claim": b["claim"], "metrics": b["metrics"], "stack": b["stack"]}
        if b["ai_work"]:
            bullet["ai_work"] = True
        out.append(bullet)
    return out


def drop_empty(entry: dict) -> dict:
    return {k: v for k, v in entry.items() if v is not None and v != ""}


def collapse(value):
    # LLM keeps source line breaks inside wrapped strings; master holds one line per fact
    if isinstance(value, str):
        return WHITESPACE.sub(" ", value).strip()
    if isinstance(value, list):
        return [collapse(v) for v in value]
    if isinstance(value, dict):
        return {k: collapse(v) for k, v in value.items()}
    return value


def build(mapped: dict, today: date) -> tuple[dict, list[str]]:
    mapped = collapse(mapped)
    assumptions: list[str] = []
    taken: set[str] = set()
    roles = []
    for i, r in enumerate(mapped["roles"]):
        company_slug = slug(schema.LEGAL_IDENTIFIER.sub("", r["company"].strip()))
        base = company_slug if company_slug not in taken else f"{company_slug}-{slug(r['title'])}"
        role_id = unique(base, taken)
        bullets = build_bullets(r["bullets"], role_id)
        roles.append(drop_empty({
            "id": role_id, "company": r["company"], "title": r["title"], "location": r["location"], "blurb": r["blurb"],
            **parse_range(r["dates"], f"roles[{i}]", today, assumptions),
            # AI claims only where source already holds AI work => no backdated AI bullet
            "ai_era": any(b.get("ai_work") for b in bullets),
            "bullets": bullets,
        }))
    projects = []
    for i, p in enumerate(mapped["projects"]):
        project_id = unique(slug(p["name"]), taken)
        bullets = build_bullets(p["bullets"], project_id)
        projects.append(drop_empty({
            "id": project_id, "name": p["name"], **parse_range(p["dates"], f"projects[{i}]", today, assumptions),
            "ai_era": any(b.get("ai_work") for b in bullets),
            "bullets": bullets,
        }))
    education = []
    for i, s in enumerate(mapped["education"]):
        end = s["end"] and parse_endpoint(s["end"], True, f"education[{i}].end", today, assumptions)
        education.append(drop_empty({**s, "end": end}))
    certifications = []
    for i, c in enumerate(mapped["certifications"]):
        when = c["date"] and parse_endpoint(c["date"], False, f"certifications[{i}].date", today, assumptions)
        certifications.append(drop_empty({**c, "date": when}))
    master = drop_empty({
        "contact": drop_empty(mapped["contact"]),
        "summary": mapped["summary"],
        "roles": roles,
        "projects": projects,
        "skills": mapped["skills"],
        "education": education,
        "certifications": certifications,
        "languages": mapped["languages"],
    })
    return master, assumptions


def prepare(config: dict, pdf_from: Path | None, force: bool) -> None:
    pdf, master_path = cfg.resume_path(config, "input_pdf"), cfg.resume_path(config, "master")
    if master_path.exists() and not force:
        sys.exit(f"{master_path} exists - hand edits live there; --force to overwrite")
    if pdf_from:
        pdf.parent.mkdir(parents=True, exist_ok=True)
        if pdf_from.resolve() != pdf.resolve():
            shutil.copyfile(pdf_from, pdf)
    handoff.write_task(TASK, ANSWER, SYSTEM, MAPPED_SCHEMA, extract(pdf), FINISH)


def finish(config: dict) -> None:
    started = time.perf_counter()
    pdf, master_path = cfg.resume_path(config, "input_pdf"), cfg.resume_path(config, "master")
    source = extract(pdf)
    mapped = handoff.read_answer(ANSWER, MAPPED_SCHEMA)

    failures = untraced(mapped, source)
    ratio, dropped = recovery(mapped, source)
    print(f"recovery {ratio:.1%} (floor {MIN_RECOVERY:.0%}), untraced {len(failures)}")
    for line in failures:
        print(f"  untraced {line}")
    for line in dropped:
        print(f"  dropped  {line}")
    if failures or ratio < MIN_RECOVERY:
        sys.exit(f"gate failed, nothing written; fix {ANSWER} to copy source text exactly, then rerun")

    today = date.today()
    master, assumptions = build(mapped, today)
    header = [f"# Imported from {pdf.name} {today.isoformat()}; hand edits win, re-import needs --force"]
    header += [f"# assumed {a}" for a in assumptions]
    body = yaml.safe_dump(master, sort_keys=False, allow_unicode=True, width=10_000)
    master_path.parent.mkdir(parents=True, exist_ok=True)
    master_path.write_text("\n".join(header) + "\n" + body, encoding="utf-8")

    errors = schema.validate(master)
    print(f"wrote {master_path} in {time.perf_counter() - started:.1f}s")
    for a in assumptions:
        print(f"  assumed  {a}")
    dated = all("start" in r and "end" in r for r in master["roles"])
    for gap in schema.employment_gaps(master, today) if dated else []:
        print(f"  gap      {gap['after']} -> {gap['before']} ({gap['months']} months)")
    for e in errors:
        print(f"  schema   {e}")
    if errors:
        sys.exit(f"schema errors above need hand edits in {master_path.name}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Resume PDF -> structured resume details: prepare AI task, then finish")
    ap.add_argument("step", choices=["prepare", "finish"])
    ap.add_argument("--pdf", type=Path, help="prepare: resume anywhere on disk; copied into My Resume first")
    ap.add_argument("--force", action="store_true", help="prepare: overwrite existing resume details")
    args = ap.parse_args()
    config = cfg.load()
    if args.step == "prepare":
        prepare(config, args.pdf, args.force)
    else:
        finish(config)


if __name__ == "__main__":
    main()
