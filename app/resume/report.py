from datetime import date

import rank
from resume import lint, schema

PRIORITY_ORDER = ("required", "preferred")


def cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def bullet_texts(tailored: dict) -> dict[str, list[str]]:
    """master bullet id -> tailored bullet texts restating it."""
    out: dict[str, list[str]] = {}
    for entry in tailored["entries"]:
        for bullet in entry["bullets"]:
            for source in bullet["sources"]:
                out.setdefault(source, []).append(bullet["text"])
    return out


def salary_label(job: dict) -> str | None:
    enrichment = job.get("enrichment") or {}
    salary = "-".join(str(enrichment[k]) for k in ("salary_min", "salary_max") if enrichment.get(k))
    return f"{salary} {enrichment.get('salary_currency') or ''}".strip() if salary else None


def posting_md(job: dict) -> str:
    out = [f"# {job['title']}", "", f"**{job['company']}**", ""]
    out += [f"- {k}: {v}" for k, v in (("Link", job["url"]), ("Pay", salary_label(job))) if v]
    out += ["", "## What they ask for", ""]
    out += [f"- ({r['priority']}) {r['text']}" for r in job["requirements"]]
    out += ["", "## Full posting", "", job["text"]]
    return "\n".join(out) + "\n"


# gate -> plain sentence for the user. The gate's own name stays only as a trailing parenthetical
GATE_WHY = {
    "round-trip": "Job-site software can read every word back in order",
    "single-column": "Text reads top to bottom in one column",
    "ligatures": "No joined letters that software misreads",
    "contact-in-body": "Your contact details are readable text, not hidden in a header",
    "entry-lines": "Each job and school has its own name line with details under it, so application forms can fill their fields",
    "no-abbreviated-title": "Job titles are spelled out (Senior, not Sr.)",
    "no-prose-block": "No paragraph too long for a quick read",
    "size": "The file is small enough to upload anywhere",
    "fonts": "Fonts are built into the file",
    "typeface": "Every letter prints in your resume's typeface",
    "no-images": "No pictures that software cannot read",
    "tagged": "The file is tagged for screen readers",
    "no-table": "No tables that software reads out of order",
    "metadata-wiped": "The file carries no hidden details about how it was made",
    "no-header-footer": "Nothing sits in the page header or footer, where software skips it",
    "split-words": "Every word reads back whole - no letters spaced so far apart that software splits them",
    "text-color": "All text is black, which resume scanners check for",
    "heading-gap": "The same space sits under every section heading",
    "headline": "Your headline fits on one row",
    "contact-line": "Your contact line fits on one row",
    "pages": "One page, or two with the second mostly full",
    "line-fill": "No line ends with a few words alone on a row",
    "budget": "Enough words to fill the page, not so many it overflows",
}


def gate_line(name: str, ok: bool, detail: str) -> str:
    key = name.removesuffix(" (info)")
    said = GATE_WHY.get(key, key)
    if not ok:
        return f"- {said} - not yet: {detail} ({key})"
    return f"- {said}" + (f" - {detail}" if name.endswith("(info)") else "") + f" ({key})"


# marker status.py reads: an older report's "Yes - all ..." line still counts
READY = "## Ready to send?\n\nYes"


def ready(check_text: str) -> bool:
    """Check before sending.md says every check passed - a failed check writes the file too."""
    return READY in check_text


def posting_history(job: dict) -> str:
    """The job search's history numbers in words. Reposted = earlier copies that closed
    (rank.reposts); copies open at once are one role in several places, not a relisting."""
    reality = job.get("reality") or {}
    copies = reality.get("mass_posting_count") or 1
    return ", ".join(part for part in (
        reality.get("class") and f"listing type {reality['class']}",
        reality.get("age_days") is not None and f"days old {reality['age_days']}",
        reality.get("repost_count") is not None and f"times reposted {rank.reposts(job)}",
        copies > 1 and f"copies open at once {copies}",
    ) if part)


def report_md(job: dict, tailored: dict, result: dict, rows: list[dict], gaps: list[dict],
              today: date | None = None) -> str:
    enrichment = job.get("enrichment") or {}
    facts = [
        ("Link", job["url"]), ("Posted on", job.get("source")), ("Level", enrichment.get("seniority")),
        ("Pay", salary_label(job)), ("Posting history", posting_history(job)), ("Your resume file", result["pdf"].name),
    ]
    out = [f"# {job['title']} - {job['company']}", ""]
    out += [f"- {k}: {v}" for k, v in facts if v]

    problems = len(result["failed"])
    # wording the resume never says in so many words: still the user's to confirm, so "Yes" names it
    confirm = len(tailored.get("inferences") or []) + sum(1 for e in tailored.get("entries") or [] if e.get("title_mirror"))
    out += ["", *READY.split("\n")[:2],
            f"Not yet - {problems} to fix first." if problems
            else f'Yes, once you confirm the {confirm} line(s) under "To confirm" further down - all '
                 f"{len(result['gates'])} page checks passed." if confirm
            else f"Yes - all {len(result['gates'])} page checks passed."]
    if problems:
        out += ["", "### Still to fix", ""]
        out += [gate_line(name, ok, detail) for name, ok, detail in result["gates"] if not ok]
        out += [f"- A tailoring rule was broken: {v}" for v in result["selection"]]
        out += [f"- {lint.WHY.get(f.rule, f.rule)} {f.detail} ({f.rule})" for f in result["findings"] if f.severity == lint.FAIL]
    # passed checks = one count, not a 22-line list; only the ones carrying a note are spelled out
    info = [gate_line(name, ok, detail) for name, ok, detail in result["gates"] if ok and name.endswith("(info)")]
    if info:
        out += ["", "### Notes", "", *info]

    ordered = sorted(rows, key=lambda r: (PRIORITY_ORDER.index(r["priority"]), r["status"] != "gap", r["index"]))
    # traits are shown in interview, never a line to add: apart, and out of the count
    asked = [r for r in ordered if not r.get("trait")]
    met = sum(r["status"] == "met" for r in asked)
    out += ["", "## What they ask vs your resume", "",
            f"Shown: {met} of {len(asked)}.", "",
            "| Need | Shown? | They ask | Your line |", "| --- | --- | --- | --- |"]
    for r in asked:
        must = "Must have" if r["priority"] == "required" else "Nice to have"
        shown = (r.get("shown") or [r["note"]])[0]  # one line proves it; the rest repeat the page
        said = f"Yes - {r['strength']}" if r["status"] == "met" and r.get("strength") else (
            "Yes" if r["status"] == "met" else "Not shown")
        out.append(f"| {must} | {said} | {cell(r['text'])} | {cell(shown)} |")

    gap_rows = [r for r in asked if r["status"] == "gap"]
    if gap_rows:
        out += ["", "## Asked for, not shown", "", "Have one? Say so - added only if true.", ""]
        out += [f"- {'Must have' if r['priority'] == 'required' else 'Nice to have'}: {r['text']} - {r['note']}"
                for r in gap_rows]
    skills_only = [r for r in asked if r["priority"] == "required" and r.get("strength") == "Skills list only"]
    if skills_only:
        out += ["", "## In your Skills list only", "",
                "A must-have no line shows you doing. Used it at a job? Say where - your own sentence goes in.", ""]
        out += [f"- {r['text']}" for r in skills_only]
    traits = [r for r in ordered if r.get("trait")]
    if traits:
        out += ["", "## Soft skills they ask for", "",
                "Shown in interview and in how your lines read - not a line to add.", ""]
        out += [f"- {r['text']}" for r in traits]
    if gaps:
        today = today or date.today()
        out += ["", f"## Breaks over {schema.MAX_GAP_MONTHS} months", ""]
        out += [f"- {g['after']} to {g['before']}: {g['months']} months. "
                + schema.gap_note(g["months"], schema.gap_is_current(g, today)) for g in gaps]

    notes = [f for f in result["findings"] if f.severity != lint.FAIL]
    if notes:
        out += ["", "## Wording notes", "", "Worth a look; none block sending.", ""]
        out += [f"- {lint.WHY.get(f.rule, f.rule)} {f.detail} ({f.rule}, {f.where})" for f in notes]
    return "\n".join(out) + "\n"


def reasons_by_id(tailored: dict) -> dict[str, str]:
    return {lint.norm(r["id"]): r["reason"] for r in tailored.get("reasons") or []}


def because(reasons: dict[str, str], key: str) -> str:
    reason = reasons.get(lint.norm(key))
    return f" - why: {reason}" if reason else ""


def diff_md(master: dict, tailored: dict, model: dict) -> str:
    restated = bullet_texts(tailored)
    reasons = reasons_by_id(tailored)
    chosen = {t["id"]: t for t in tailored["entries"]}
    headings = {e["id"]: e["heading"] for s in model["sections"] for e in s.get("entries", []) if e.get("id")}
    out = ["# What changed from your resume", ""]

    mirrors = [t for t in tailored["entries"] if t["title_mirror"]]
    if tailored["inferences"] or mirrors:
        out += ["## To confirm - is each of these true?", "",
                "Each one is wording your resume does not say in so many words.", ""]
        for t in mirrors:
            out.append(f"- Job title shown as \"{headings[t['id']]}\". The part in brackets is the posting's "
                       f"title - is it a fair name for the work you did there?")
        claims = {b["id"]: b["claim"] for e in [*master["roles"], *master.get("projects", [])] for b in e["bullets"]}
        for inference in tailored["inferences"]:
            out.append(f"- {inference['claim']}")
            out += [f"  - based on: {claims.get(s, '(not found in your resume)')} ({s})" for s in inference["sources"]]
        out.append("")

    out += ["## Summary", "", f"- Your resume: {master.get('summary') or '(none)'}",
            f"- This version: {model['summary'] or '(left out)'}", ""]

    for entry in [*master["roles"], *master.get("projects", [])]:
        name = entry.get("title", entry.get("name"))
        heading = f"## {name}" + (f" | {entry['company']}" if entry.get("company") else "")
        t = chosen.get(entry["id"])
        if t is None:
            out += [heading, "", f"- Left off this version{because(reasons, entry['id'])}", ""]
            continue
        out += [heading, ""]
        for bullet in t["bullets"]:
            sources = [b for b in entry["bullets"] if b["id"] in bullet["sources"]]
            if len(sources) == 1 and sources[0]["claim"] == bullet["text"]:
                out.append(f"- Kept as written: {bullet['text']}")
                continue
            out.append(f"- Reworded: {bullet['text']}")
            out += [f"  - was: {b['claim']}" for b in sources]
        dropped = [b for b in entry["bullets"] if b["id"] not in restated]
        out += [f"- Left out: {b['claim']}{because(reasons, b['id'])}" for b in dropped]
        out.append("")

    shown = {lint.norm(i) for g in tailored["skills"] for i in g["items"]}
    out += ["## Skills", ""]
    out += [f"- {g['group']}: {', '.join(g['items'])}" for g in tailored["skills"] if g["items"]]
    dropped = sorted({i for g in master.get("skills", []) for i in g["items"] if lint.norm(i) not in shown})
    out += [f"- Left out: {i}{because(reasons, i)}" for i in dropped]
    return "\n".join(out) + "\n"
