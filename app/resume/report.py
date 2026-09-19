from resume import lint

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


def report_md(job: dict, tailored: dict, result: dict, rows: list[dict], gaps: list[dict]) -> str:
    enrichment, reality = job.get("enrichment") or {}, job.get("reality") or {}
    facts = [
        ("url", job["url"]), ("source", job.get("source")), ("seniority", enrichment.get("seniority")),
        ("salary", salary_label(job)),
        ("reality", ", ".join(f"{k} {reality[k]}" for k in ("class", "age_days", "repost_count") if reality.get(k) is not None)),
        ("pdf", result["pdf"].name),
    ]
    out = [f"# {job['title']} - {job['company']}", ""]
    out += [f"- {k}: {v}" for k, v in facts if v]

    status = "FAIL" if result["failed"] else "pass"
    out += ["", f"## Checks: {status}", ""]
    out += [f"- {'pass' if ok else 'FAIL'} {name}: {detail}" for name, ok, detail in result["gates"]]
    out += [f"- FAIL selection: {v}" for v in result["selection"]]

    texts = bullet_texts(tailored)
    ordered = sorted(rows, key=lambda r: (PRIORITY_ORDER.index(r["priority"]), r["status"] != "gap", r["index"]))
    met = sum(r["status"] == "met" for r in rows)
    out += ["", f"## Coverage: {met}/{len(rows)} met", "", "| # | priority | status | requirement | evidence |", "| --- | --- | --- | --- | --- |"]
    for r in ordered:
        evidence = "; ".join(f"`{s}` {' / '.join(texts.get(s, []))}" for s in r["evidence"]) or r["note"]
        out.append(f"| {r['index']} | {r['priority']} | {r['status']} | {cell(r['text'])} | {cell(evidence)} |")

    gap_rows = [r for r in ordered if r["status"] == "gap"]
    if gap_rows:
        out += ["", "## Gaps", ""]
        out += [f"- {r['priority']}: {r['text']} - {r['note']}" for r in gap_rows]
    if gaps:
        out += ["", "## Employment gaps over 6 months", ""]
        out += [f"- {g['after']} -> {g['before']}: {g['months']} months" for g in gaps]

    findings = result["findings"]
    if findings:
        out += ["", "## Lint", ""]
        out += [f"- {f.severity} {f.rule} at {f.where}: {f.detail}" for f in findings]
    return "\n".join(out) + "\n"


def diff_md(master: dict, tailored: dict, model: dict) -> str:
    restated = bullet_texts(tailored)
    chosen = {t["id"]: t for t in tailored["entries"]}
    headings = {e["id"]: e["heading"] for s in model["sections"] for e in s.get("entries", [])}
    out = ["# Diff vs master", ""]

    if tailored["inferences"]:
        out += ["## Inferences - verify each before sending", ""]
        claims = {b["id"]: b["claim"] for e in [*master["roles"], *master.get("projects", [])] for b in e["bullets"]}
        for inference in tailored["inferences"]:
            out.append(f"- {inference['claim']}")
            out += [f"  - from `{s}`: {claims.get(s, '(unknown id)')}" for s in inference["sources"]]
        out.append("")

    out += ["## Summary", "", f"- master: {master.get('summary') or '(none)'}", f"- tailored: {model['summary'] or '(omitted)'}", ""]

    for entry in [*master["roles"], *master.get("projects", [])]:
        name = entry.get("title", entry.get("name"))
        heading = f"## {name}" + (f" | {entry['company']}" if entry.get("company") else "")
        t = chosen.get(entry["id"])
        if t is None:
            out += [heading, "", "- omitted", ""]
            continue
        out += [heading, ""]
        if t["title_mirror"]:
            out.append(f"- title: {headings[entry['id']]}")
        for n, bullet in enumerate(t["bullets"], 1):
            sources = [b for b in entry["bullets"] if b["id"] in bullet["sources"]]
            if len(sources) == 1 and sources[0]["claim"] == bullet["text"]:
                out.append(f"- {n}. kept `{sources[0]['id']}`: {bullet['text']}")
                continue
            out.append(f"- {n}. rewritten: {bullet['text']}")
            out += [f"  - was `{b['id']}`: {b['claim']}" for b in sources]
        dropped = [b for b in entry["bullets"] if b["id"] not in restated]
        out += [f"- dropped `{b['id']}`: {b['claim']}" for b in dropped]
        out.append("")

    master_items = {lint.norm(i) for g in master.get("skills", []) for i in g["items"]}
    shown = [i for g in tailored["skills"] for i in g["items"]]
    out += ["## Skills", ""]
    out += [f"- {g['group']}: {', '.join(g['items'])}" for g in tailored["skills"] if g["items"]]
    added = [i for i in shown if lint.norm(i) not in master_items]
    dropped = sorted({i for g in master.get("skills", []) for i in g["items"]} - set(shown))
    if added:
        out.append(f"- not in master: {', '.join(added)}")
    if dropped:
        out.append(f"- dropped: {', '.join(dropped)}")
    return "\n".join(out) + "\n"
