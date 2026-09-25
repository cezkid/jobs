"""Resume facts -> the answers an application form asks for, as one script the Chrome extension runs.

`apply <slug>` uses that job's tailored bullets and skills when `tailor` made them, else the user's
own facts. Output: `<job folder>/.data/apply.js` = `workday.js` + `window.__jf.run(DATA)`.
Workday rules and why: app/docs/apply/workday.md.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import cfg
from resume import render, schema, tailor

FILLER = Path(__file__).with_name("workday.js")
# spelled-out degree -> the generic entry forms list when the exact one is missing
# (tenant A lists "A. - Associate's degree", no "Associate of Arts")
DEGREE_FAMILY = {"Associate": ["Associate's degree"], "Bachelor": ["Bachelor's degree"],
                 "Master": ["Master's degree", "Masters degree"], "Doctor": ["Doctorate", "Professional Doctorate"],
                 "Juris": ["Doctor of Jurisprudence"]}
# level words forms offer, each tier = interchangeable wordings. A missing level falls back only
# inside its own tier: never lower (tenant A offers only Conversational or Fluent; Native -> Fluent)
LEVEL_TIERS = [["Native", "Fluent"], ["Professional", "Advanced"], ["Conversational", "Intermediate"],
               ["Basic", "Beginner", "Elementary"]]
LANGUAGE = re.compile(r"^(.+?)\s*\((.+)\)$")
BULLET = "• "
# a shortened field name never ends on one: "Music Performance in" is no search term
JOINERS = {"in", "and", "of", "the", "for", "&", "with", "to"}


def degree(written: str) -> list[str]:
    full = render.degree_name(written)
    return list(dict.fromkeys([full, written, *DEGREE_FAMILY.get(full.split()[0], [])]))


def field_of_study(field: str | None) -> list[str]:
    """Whole name first, then shorter from the end: "Music Performance in Jazz and Studio" -> "Music Performance"."""
    words = (field or "").split()
    return [" ".join(words[:n]) for n in range(len(words), 1, -1)
            if words[n - 1].casefold() not in JOINERS] or words


def language(line: str) -> dict:
    m = LANGUAGE.match(line.strip())
    if not m:
        return {"name": line.strip(), "levels": []}
    name, said = m.groups()
    for tier in LEVEL_TIERS:
        for i, word in enumerate(tier):
            if word.casefold() in said.casefold():
                return {"name": name, "levels": tier[i:]}
    return {"name": name, "levels": [said]}


def month(value: str) -> str:
    return "" if value == schema.PRESENT else value


def answers(master: dict, tailored: dict | None = None) -> dict:
    chosen = {e["id"]: [b["text"] for b in e["bullets"]] for e in (tailored or {}).get("entries", [])}
    work = [{
        "title": r["title"], "company": r["company"], "location": r.get("location", ""),
        "current": r["end"] == schema.PRESENT, "start": r["start"], "end": month(r["end"]),
        "description": "\n".join(BULLET + b for b in chosen.get(r["id"]) or [b["claim"] for b in r["bullets"]]),
    } for r in master["roles"]]
    education = [{
        "school": s["institution"], "degree": degree(s["degree"]), "field": field_of_study(s.get("field")),
        "end": "" if s.get("hide_year") else s.get("end", ""),
    } for s in master.get("education") or []]
    groups = tailored["skills"] if tailored else master.get("skills") or []
    skills = list(dict.fromkeys(item for g in groups for item in g["items"]))
    return {"work": work, "education": education, "skills": skills,
            "languages": [language(line) for line in master.get("languages") or []]}


def work_authorization(config: dict) -> str:
    """The two work-permit answers from setup; unset = ask the user on the form, never guess."""
    wa = config.get("work_authorization") or {}
    said = lambda v: "not set - ask them" if v is None else "yes" if v else "no"
    return (f"authorized to work in the US: {said(wa.get('authorized_us'))}; "
            f"needs visa sponsorship: {said(wa.get('needs_sponsorship'))}")


def script(data: dict) -> str:
    return FILLER.read_text(encoding="utf-8") + f"\nwindow.__jf.run({json.dumps(data, ensure_ascii=False)});\n'started'\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="application answers -> script for the Chrome extension to run")
    ap.add_argument("slug", nargs="?", help="job with a tailored resume; omit = your own resume facts")
    args = ap.parse_args()
    config = cfg.load()
    master = schema.load(cfg.resume_path(config, "master"))
    tailored, out = None, cfg.DATA / "apply.js"
    if args.slug:
        job_dir = tailor.find_job_dir(cfg.resume_path(config, "jobs_dir"), args.slug)
        if job_dir is None:
            sys.exit(f"no job folder for {args.slug}; run tailor first")
        saved = job_dir / tailor.JOB_DATA / "tailored.json"
        tailored = json.loads(saved.read_text(encoding="utf-8")) if saved.exists() else None
        out = job_dir / tailor.JOB_DATA / "apply.js"
    out.parent.mkdir(parents=True, exist_ok=True)
    data = answers(master, tailored)
    out.write_text(script(data), encoding="utf-8")
    print(f"wrote {out} ({len(data['work'])} jobs, {len(data['education'])} schools, {len(data['skills'])} skills, "
          f"{'tailored' if tailored else 'own resume'} bullets)")
    print(work_authorization(config))


if __name__ == "__main__":
    main()
