"""Resume feedback: how the user's own resume reads, in plain words, with what to do next.

Everything here is measured by code that already exists - lint.py's wording rules, the file
checks, the gap finder - plus a count of the lines showing leadership, initiative and teamwork.
It judges content only. Page layout is not scored: render.py's gates hold every PDF to it
before the user ever sees one (docs/resume/page-format.md).

Writes My Resume/Resume feedback.md and keeps the last result in .data/, so each run can say
what moved since the one before. Statuses are guidance, never a pass mark: a thin area is
something to ask the user about (`resume-gaps`), never words to add (docs/resume/bullets.md Tier 1).
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import cfg
from resume import lint, render, schema

REPORT_NAME = "Resume feedback.md"
STATE = cfg.DATA / "resume-feedback.json"
GUIDE = "../Guides/What makes a good resume.md"
STRONG, GOOD, LOOK = "Strong", "Good", "Worth a look"
# share of lines carrying a number or scope. Career guidance asks for evidence on most lines,
# not all (docs/resume/bullets.md: "every bullet needs a metric" did not survive) - convention, not measured
NUMBER_STRONG, NUMBER_GOOD = 0.80, 0.60
# lines showing a quality across the page: two or more reads as a pattern, one as a mention
SHOWN_STRONG = 2
# words that show the quality when a line uses them for the candidate's own act. Counted, never
# required: a quality the user's work did not involve is not a gap to fill with a verb.
# "paired" stays out of Teamwork: it pairs code as often as people ("paired screens with APIs")
QUALITIES = {
    "Leadership": r"\b(led|lead|leading|mentor\w*|coach\w*|train(ed|ing)?|onboard\w*|manag(ed|ing)|"
                  r"supervis\w*|direct(ed|ing)|head(ed|ing)|hired|delegat\w*)\b",
    "Initiative": r"\b(launch\w*|start(ed|ing)|found(ed|ing)|introduc\w*|propos\w*|initiat\w*|"
                  r"establish\w*|pioneer\w*|set up|creat(ed|ing))\b",
    "Teamwork": r"\b(collaborat\w*|partner\w*|align\w*|coordinat\w*|cross-functional|"
                r"teams?|stakeholders?|with (the )?(designers?|engineers?|product))\b",
}
# lint rules grouped the way a reader meets them; anything not listed is not a content question
WORDING = ("spelling", "compound-modifier", "overused-opening", "same-verb-opening", "filler-word",
           "style-word", "unmeasurable-grade", "hedge", "resume-verb", "empty-clause", "em-dash",
           "markdown", "invisible-unicode", "canonical-casing", "uniform-bullet-length")
EVIDENCE = ("lead-bullet-weak",)
PERSONAL = ("street-address", "personal-details", "old-graduation-year", "abbreviated-school", "language-level")
DATES = ("role-dates-overlap", "bullet-taper")


def bullets(master: dict) -> list[tuple[str, str]]:
    """(where, claim) for every line under a job or project."""
    return [(f"{e.get('title', e.get('name'))}" + (f" at {e['company']}" if e.get("company") else ""), b["claim"])
            for e in [*master["roles"], *master.get("projects", [])] for b in e["bullets"]]


def status(share: float, strong: float, good: float) -> str:
    return STRONG if share >= strong else GOOD if share >= good else LOOK


def assess(master: dict, today: date) -> dict:
    lines = bullets(master)
    findings = lint.lint(render.page_model(master), master) + lint.master_findings(master, today)
    counted = [f for f in findings if f.rule in (*WORDING, *EVIDENCE, *PERSONAL, *DATES)]
    numbered = [(w, c) for w, c in lines if lint.NUMBER.search(c)]
    bare = [(w, c) for w, c in lines if not lint.NUMBER.search(c)]
    share = len(numbered) / len(lines) if lines else 0.0
    shown = {q: [(w, c) for w, c in lines if re.search(p, c, re.I)] for q, p in QUALITIES.items()}
    gaps = schema.employment_gaps(master, today)
    areas = {
        "Numbers and scope": (status(share, NUMBER_STRONG, NUMBER_GOOD),
                              f"{len(numbered)} of {len(lines)} lines say how many, how much or what changed"),
        "Wording": (STRONG if not [f for f in counted if f.rule in WORDING] else LOOK,
                    f"{sum(f.rule in WORDING for f in counted)} note(s): spelling, repetition, filler"),
        **{q: (STRONG if len(s) >= SHOWN_STRONG else GOOD if s else LOOK, f"{len(s)} line(s) show it")
           for q, s in shown.items()},
        "Personal details and dates": (STRONG if not [f for f in counted if f.rule in (*PERSONAL, *DATES)] and not gaps
                                       else LOOK,
                                       f"{sum(f.rule in (*PERSONAL, *DATES) for f in counted) + len(gaps)} note(s)"),
    }
    return {"date": today.isoformat(), "areas": areas, "bare": bare, "shown": shown, "gaps": gaps,
            "notes": [(f.rule, f.where, f.detail) for f in counted]}


def changes(now: dict, before: dict | None) -> list[str]:
    if not before:
        return []
    out = []
    for area, (state, detail) in now["areas"].items():
        was = before.get("areas", {}).get(area)
        if was and (was[0], was[1]) != (state, detail):
            out.append(f"{area}: {was[0]} -> {state} ({detail})" if was[0] != state else f"{area}: {detail} (was: {was[1]})")
    return out


def plain(rule: str, where: str, detail: str) -> str:
    """One note as the user reads it: why it matters, then the text it is about."""
    return f"- {lint.WHY.get(rule, rule)} {detail} ({where})"


def report_md(result: dict, moved: list[str]) -> str:
    out = ["# Resume feedback", "",
           f"Checked {result['date']}. How your resume reads to an employer, and what would make it stronger.",
           f"Why each point matters: [What makes a good resume]({GUIDE.replace(' ', '%20')}).", "",
           "Page layout is not in here: every resume CEZ Job Finder makes is checked for it automatically.", ""]
    if moved:
        out += ["## Since last time", "", *(f"- {m}" for m in moved), ""]
    out += ["## At a glance", "", "| Area | How it reads | |", "| --- | --- | --- |"]
    out += [f"| {area} | {state} | {detail} |" for area, (state, detail) in result["areas"].items()]
    look = [area for area, (state, _) in result["areas"].items() if state == LOOK]

    if result["bare"]:
        out += ["", "## Lines without a number", "",
                "A number lets a reader picture the size of the work - how many, how often, what changed. "
                "Only add one you know; say \"help me add numbers to my resume\" and the chat asks you line by line.", ""]
        out += [f"- {claim} ({where})" for where, claim in result["bare"]]
    notes = result["notes"]
    wording = [n for n in notes if n[0] in WORDING]
    if wording:
        out += ["", "## Wording notes", "", "None of these stop a resume going out; each is worth a look.", ""]
        out += [plain(*n) for n in wording]
    personal = [n for n in notes if n[0] in (*PERSONAL, *DATES, *EVIDENCE)]
    if personal or result["gaps"]:
        out += ["", "## Details and dates", ""]
        out += [plain(*n) for n in personal]
        out += [f"- A break of {g['months']} months between jobs ({g['after']} to {g['before']}). "
                "A one-line reason answers the question it raises." for g in result["gaps"]]
    out += ["", "## What your lines show", ""]
    for quality, found in result["shown"].items():
        out.append(f"**{quality}** - {len(found)} line(s)" + (":" if found else
                   ". If you led, started or worked with others on something, say so in the chat - only what really happened."))
        out += [f"- {claim} ({where})" for where, claim in found]
        out.append("")
    steps = []
    if result["bare"]:
        steps.append("\"Help me add numbers to my resume\" - the chat asks about each line above; skip any you don't know.")
    if wording:
        steps.append("\"Go through the wording notes\" - you decide on each one; nothing changes without your yes.")
    if any(q in look for q in QUALITIES):
        steps.append("\"Help me show leadership\" - the chat asks what you led, started or taught.")
    if steps:
        out += ["## Next steps", "", *(f"{n}. {s}" for n, s in enumerate(steps, 1))]
    else:
        out += ["## Next steps", "", "Nothing stands out. Pick a job and ask for a resume made for it."]
    return "\n".join(out).rstrip() + "\n"


def run(path: Path, today: date | None = None, state: Path = STATE) -> tuple[Path, dict, list[str]]:
    result = assess(schema.load(path), today or date.today())
    before = json.loads(state.read_text(encoding="utf-8")) if state.exists() else None
    moved = changes(result, before)
    report = path.parent / REPORT_NAME
    report.write_text(report_md(result, moved), encoding="utf-8")
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({"date": result["date"], "areas": result["areas"]}, indent=1), encoding="utf-8")
    return report, result, moved


def main() -> None:
    ap = argparse.ArgumentParser(description="plain-words feedback on the user's own resume: evidence, wording, what it shows")
    ap.add_argument("--master", type=Path, help="resume details file (default: the one in settings)")
    args = ap.parse_args()
    path = args.master or cfg.resume_path(cfg.load(), "master")
    if not path.exists():
        sys.exit(f"{path} missing - import the resume PDF first")
    report, result, moved = run(path)
    for area, (state, detail) in result["areas"].items():
        print(f"  {state:13} {area:28} {detail}")
    for m in moved:
        print(f"  moved         {m}")
    print(f"report: {report}")


if __name__ == "__main__":
    main()
