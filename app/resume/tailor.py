import argparse
import functools
import json
import re
import sys
from datetime import date
from pathlib import Path

import httpx
import pymupdf

import cfg
from resume import handoff, jd, lint, measure, render, report, schema, typeface

STRING, NULLABLE, STRINGS, obj, array = handoff.STRING, handoff.NULLABLE, handoff.STRINGS, handoff.obj, handoff.array
# plan #Visual spec: bullets/role 6 max, 1-2 lines. A bullet is judged on its RENDERED width
# (resume/measure.py, real font advances), never on a character count: one glyph runs 3.1x the
# width of another, so counting characters mis-sizes a line by a quarter
MAX_BULLETS_PER_ENTRY = 6
MAX_BULLET_LINES = 2
# one-line bullets among the two-line ones keep lint's uniform-bullet-length CV off the floor
ONE_LINE_SHARE = 5
SKILLS_TITLE = "Skills"
# prose the character guides are read off: a writer thinks in characters, so the prompt has to
# quote some, but how many fit is a property of the font. Wrapping this in the configured font
# is what turns one into the other - no number here survives a font change unmeasured.
GUIDE_PROSE = (
    "Built retrieval-augmented search over support documentation with an evaluation harness "
    "scoring answer grounding, cutting first-tier ticket volume across the support platform "
    "and shipping the change to every customer region in the same quarter without regression"
)

TAILORED_SCHEMA = obj(
    summary=NULLABLE,
    entries=array(obj(id=STRING, title_mirror=NULLABLE, bullets=array(obj(text=STRING, sources=STRINGS)))),
    skills=array(obj(group=STRING, items=STRINGS)),
    inferences=array(obj(claim=STRING, sources=STRINGS)),
    coverage=array(obj(requirement={"type": "integer"}, evidence=STRINGS, note=STRING)),
)


def char_guides(font: str) -> tuple[int, tuple[int, int]]:
    """Characters that land a bullet on the right side of the fill bands, in THIS font.

    Found by wrapping real prose, not assumed: where one line stops fitting, where a second
    first clears the fill floor, and where a third would start. Each edge is pulled one word
    inside the true boundary, because the writer edits in words - a bullet written exactly to
    the boundary crosses it the moment a word changes, and bullet_shape sends it back.

    In Caladea at 11pt that is 91 characters or fewer for one line, 145-194 to fill two; the gap
    between is what makes a stub. Another family moves all three, which is why they are read
    off the font here instead of being written down.
    """
    avail = measure.bullet(font)
    # one average word of this prose, the space before it included: the unit an edit moves by
    slack = measure.width(font, GUIDE_PROSE) / len(GUIDE_PROSE.split())
    sized = {n: (measure.fit(font, GUIDE_PROSE[:n], avail), measure.width(font, GUIDE_PROSE[:n]))
             for n in range(1, len(GUIDE_PROSE) + 1)}
    one = [n for n, ((lines, _), w) in sized.items() if lines == 1 and w <= avail - slack]
    two = [n for n, ((lines, _), _w) in sized.items() if lines == MAX_BULLET_LINES]
    filled = [n for n in two if sized[n][0][1] * avail >= render.MIN_LINE_FILL * avail + slack]
    high = [n for n in two if sized[n][1] <= MAX_BULLET_LINES * avail - slack]
    return max(one), (min(filled), max(high))


@functools.cache
def system(font: str) -> str:
    one_line_chars, two_line_chars = char_guides(font)
    return f"""You tailor one candidate's resume to one job posting. Input JSON: `master` (candidate facts, stable ids), `job` (posting + indexed requirements), `budget`. You emit selection + rewrite JSON; code lays out the page and checks every rule below.

Entries
- `entries` lists every master role id, plus any project ids worth page space. Never drop a role: dates must stay contiguous. Oldest roles may carry zero bullets.
- Each bullet's `sources` = ids of master bullets from the SAME entry that it restates. Never move a claim into another role or project. Order bullets by relevance to this job.
- Bullets per entry: 3-5 for recent roles ({MAX_BULLETS_PER_ENTRY} max), 2-3 for older, 0 for the oldest.
- Every bullet either fits ONE line or FILLS two. Land between and it wraps to a stub carrying a few words, wasting a whole row. The check measures rendered width in the real font, so character counts are a guide only: about {one_line_chars} characters or fewer fits one line, {two_line_chars[0]}-{two_line_chars[1]} fills two. Write to the nearer edge, never into the gap.
- Mix the two: at least one bullet in {ONE_LINE_SHARE} fits a single line, so the page never reads templated.
- Skills groups follow the same rule on their rendered "Label: items" line - trim items to one line, or add until a second line is {render.MIN_LINE_FILL:.0%} full.
- `title_mirror`: null, or part of the posting's title copied exactly, on a role whose work genuinely matches it. Rendered as "Master Title (mirror)". Never abbreviate.

Wording
- Start from the candidate's own claim text. Keep their words where they already fit; change only what this job makes relevant: what leads, emphasis, the posting's term for the same thing.
- Every bullet names a product, stack item, number or proper noun.
- Numbers only as written in master claims or metrics. Never invent or round one.
- AI/LLM wording only inside entries whose `ai_era` is true (absent = false).
- Where the posting names a technology differently from master, spell both forms once, full name then short form: "Electronic Health Record (EHR)", and list the new form in `inferences`.
- Plain text: no markdown, no em dashes, no non-breaking or zero-width spaces.
- Never use: {", ".join((*lint.STYLE_WORD_LIST, *lint.HEDGE_LIST, *lint.RESUME_VERB_LIST))}.
- No "not only X but also Y", no filler lists of three, no two consecutive bullets opening with the same word.

Summary
- `summary`: at most {render.MAX_BLOCK_WORDS} words, fragments over sentences, leads with the candidate's real current title and this job's core stack; null to omit. It sits in a narrower column than the bullets, so the same rule applies: one line, or two with the second well filled.

Skills
- `skills`: master skill groups reordered and filtered for this job, most relevant first. Items copied from master; a group label may be renamed.

Honesty
- Implied-but-unwritten claims are allowed only when master bullets support them. Each one gets an `inferences` entry: `claim` = the exact added wording, `sources` = supporting master bullet ids. Any company, tool, number or credential absent from master must appear in an inference.
- Never change employer, title, dates, degrees or certifications.

Coverage
- `coverage`: exactly one entry per job requirement index. `evidence` = ids of master bullets you placed on the page whose page text alone proves it; empty = gap. `note` = short phrase: how it is proven, or what is missing.

Budget
- Page word count must land inside one of budget.page_words windows (measured from this candidate's page density: a page either fits on one page or fills most of a second). Fixed parts (contact, headings, dates, education) take budget.fixed_words, so summary + bullets + skills must land inside the matching budget.generated_words window."""


def entries_by_id(master: dict) -> dict:
    return {e["id"]: e for e in [*master["roles"], *master.get("projects", [])]}


def page_model(master: dict, tailored: dict) -> dict:
    """Master page model w/ tailored summary, entry selection, bullets, skills; everything else verbatim."""
    base = render.page_model(master)
    chosen = {t["id"]: t for t in tailored["entries"]}
    sections = []
    for section in base["sections"]:
        if "entries" in section:
            entries = [
                {**e, "heading": mirrored(e["heading"], chosen[e["id"]]["title_mirror"]),
                 "bullets": [b["text"] for b in chosen[e["id"]]["bullets"]]}
                for e in section["entries"] if e["id"] in chosen
            ]
            if entries:
                sections.append({**section, "entries": entries})
        elif section["title"] == SKILLS_TITLE:
            lines = [{"label": g["group"], "text": ", ".join(g["items"])} for g in tailored["skills"] if g["items"]]
            if lines:
                sections.append({**section, "lines": lines})
        else:
            sections.append(section)
    return {**base, "summary": tailored["summary"] or None, "sections": sections}


def mirrored(title: str, mirror: str | None) -> str:
    return f"{title} ({mirror})" if mirror else title


def skeleton(master: dict) -> dict:
    return {"summary": None, "entries": [{"id": r["id"], "title_mirror": None, "bullets": []} for r in master["roles"]],
            "skills": []}


def page_words(model: dict) -> int:
    return sum(len(render.tokens(s)) for s in render.page_strings(model))


def build_request(master: dict, job: dict, font: str = typeface.DEFAULT) -> dict:
    """Everything AI tailors from; pure function of master + JD + font => byte-identical per slug."""
    fixed = page_words(page_model(master, skeleton(master)))
    untailored = render.page_model(master)
    with pymupdf.open(stream=render.compile_pdf(untailored, font), filetype="pdf") as doc:
        windows = render.word_windows(page_words(untailored), render.pages_used(doc))
    payload = {
        "job": {
            "title": job["title"], "company": job["company"], "description": job["text"],
            "requirements": [{"index": i, **r} for i, r in enumerate(job["requirements"])],
        },
        "budget": {"page_words": windows, "fixed_words": fixed,
                   "generated_words": [[low - fixed, high - fixed] for low, high in windows]},
        "master": master,
    }
    return {"system": system(font), "schema": TAILORED_SCHEMA, "prompt": json.dumps(payload, indent=1, ensure_ascii=False)}


def bullet_shape(text: str, where: str, font: str = typeface.DEFAULT) -> list[str]:
    """Bullet must fit one line or fill two - measured in points off the font, not in characters.

    The gap between those two is what leaves a stub line carrying a few words and wasting a whole
    row. render.py's line-fill gate re-checks this on the rendered PDF and has the last word.
    """
    avail = measure.bullet(font)
    lines, fill = measure.fit(font, text, avail)
    if lines > MAX_BULLET_LINES:
        over = measure.width(font, text) - avail * MAX_BULLET_LINES
        return [f"{where}: renders {lines} lines (max {MAX_BULLET_LINES}) - cut "
                f"{measure.chars_for(font, text, over)} chars: {text!r}"]
    if lines > 1 and fill < render.MIN_LINE_FILL:
        tail = measure.wrap(font, text, avail)[-1]
        cut = measure.chars_for(font, text, measure.width(font, text) - avail)
        add = measure.chars_for(font, text, render.MIN_LINE_FILL * avail - measure.width(font, tail))
        grow = f", or add ~{add} to fill two" if add > 0 else ""
        return [f"{where}: wraps to a line only {fill:.0%} full - cut {cut} chars to fit one line"
                f"{grow}: {text!r}"]
    return []


def check_selection(master: dict, job: dict, tailored: dict, font: str = typeface.DEFAULT) -> list[str]:
    """Rules lint cannot see: entry ids, claim ownership, mirror source, coverage shape."""
    violations: list[str] = []
    entries = entries_by_id(master)
    owner = {b["id"]: e["id"] for e in entries.values() for b in e["bullets"]}
    ids = [t["id"] for t in tailored["entries"]]
    violations += [f"entries: {i!r} listed twice" for i in sorted({i for i in ids if ids.count(i) > 1})]
    violations += [f"entries: {i!r} not a master role or project id" for i in ids if i not in entries]
    violations += [f"entries: role {r['id']!r} dropped - every role stays" for r in master["roles"] if r["id"] not in ids]
    roles = {r["id"]: r for r in master["roles"]}
    job_title = lint.norm(job["title"])
    for t in tailored["entries"]:
        where = f"entries[{t['id']}]"
        if len(t["bullets"]) > MAX_BULLETS_PER_ENTRY:
            violations.append(f"{where}: {len(t['bullets'])} bullets (max {MAX_BULLETS_PER_ENTRY})")
        for n, bullet in enumerate(t["bullets"], 1):
            if not bullet["sources"]:
                violations.append(f"{where} bullet {n}: sources empty")
            for source in bullet["sources"]:
                if owner.get(source) != t["id"]:
                    violations.append(f"{where} bullet {n}: source {source!r} belongs to {owner.get(source)!r}, not this entry")
            if t["id"] in entries and (unsourced := unsourced_entities(entries[t["id"]], bullet, tailored["inferences"])):
                violations.append(f"{where} bullet {n}: {unsourced} in none of its sources' facts or inferences: {bullet['text']!r}")
            violations += bullet_shape(bullet["text"], f"{where} bullet {n}", font)
        mirror = t["title_mirror"]
        if mirror:
            if t["id"] not in roles:
                violations.append(f"{where}: title_mirror on non-role")
            elif lint.norm(mirror) not in job_title:
                violations.append(f"{where}: title_mirror {mirror!r} not part of job title {job['title']!r}")
            elif lint.norm(mirror) == lint.norm(roles[t["id"]]["title"]):
                violations.append(f"{where}: title_mirror repeats master title")
            if schema.ABBREVIATED_TITLE.search(mirror):
                violations.append(f"{where}: title_mirror {mirror!r} abbreviated")

    on_page = on_page_sources(tailored)
    indexes = [c["requirement"] for c in tailored["coverage"]]
    count = len(job["requirements"])
    violations += [f"coverage: requirement {i} listed twice" for i in sorted({i for i in indexes if indexes.count(i) > 1})]
    violations += [f"coverage: requirement {i} out of range 0-{count - 1}" for i in indexes if not 0 <= i < count]
    violations += [f"coverage: requirement {i} missing" for i in range(count) if i not in indexes]
    for c in tailored["coverage"]:
        for source in c["evidence"]:
            if source not in on_page:
                violations.append(f"coverage: requirement {c['requirement']} evidence {source!r} not a source of any on-page bullet")
    return violations


def unsourced_entities(entry: dict, bullet: dict, inferences: list[dict]) -> list[str]:
    """Entity resolving only elsewhere in master = claim moved between entries."""
    facts = [b for b in entry["bullets"] if b["id"] in bullet["sources"]]
    header = {k: entry.get(k) for k in ("company", "title", "name", "blurb", "location")}
    corpus = lint.master_strings([facts, header])
    corpus += [i["claim"] for i in inferences if set(i["sources"]) & set(bullet["sources"])]
    known = {t.casefold() for t in lint.TOKEN.findall(" ".join(corpus))}
    return sorted({e for e in lint.entities(bullet["text"]) if e.casefold() not in known})


def on_page_sources(tailored: dict) -> set[str]:
    return {s for t in tailored["entries"] for b in t["bullets"] for s in b["sources"]}


def coverage_rows(job: dict, tailored: dict) -> list[dict]:
    by_index = {c["requirement"]: c for c in tailored["coverage"]}
    on_page = on_page_sources(tailored)
    rows = []
    for i, requirement in enumerate(job["requirements"]):
        claimed = by_index.get(i, {"evidence": [], "note": "not addressed"})
        evidence = [s for s in claimed["evidence"] if s in on_page]
        rows.append({**requirement, "index": i, "evidence": evidence, "note": claimed["note"],
                     "status": "met" if evidence else "gap"})
    return rows


def lint_inferences(tailored: dict) -> list[dict]:
    return [{"claim": i["claim"], "from": i["sources"]} for i in tailored["inferences"]]


def evaluate(master: dict, job: dict, tailored: dict, out_dir: Path, font: str = typeface.DEFAULT) -> dict:
    model = page_model(master, tailored)
    pdf, gates = render.render(model, out_dir, budget=True, font=font)
    findings = lint.lint(model, master, lint_inferences(tailored))
    selection = check_selection(master, job, tailored, font)
    failed = [
        *selection,
        *(f"lint {f.rule} at {f.where}: {f.detail}" for f in findings if f.severity == lint.FAIL),
        *(f"gate {name}: {detail}" for name, ok, detail in gates if not ok),
    ]
    return {"model": model, "pdf": pdf, "gates": gates, "findings": findings, "selection": selection, "failed": failed}


JOB_DATA = ".data"
ILLEGAL_IN_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# Windows path limit leaves room for My Jobs/<name>/.data/<file> under deep home dirs
MAX_FOLDER_CHARS = 80
POSTING_TASK = cfg.DATA / "posting-task.md"
POSTING_ANSWER = cfg.DATA / "posting.json"
CHECK_FILE = "Check before sending.md"
POSTING_FILE = "Job posting.md"


def folder_name(job: dict) -> str:
    name = f"{job['company']} - {job['title']}" if job["company"] else job["title"]
    name = " ".join(ILLEGAL_IN_NAME.sub(" ", name).split())
    if len(name) > MAX_FOLDER_CHARS:
        name = name[:MAX_FOLDER_CHARS + 1].rsplit(" ", 1)[0]
    return name.rstrip(" .,-&") or job["public_slug"]


def find_job_dir(root: Path, slug: str) -> Path | None:
    for saved in root.glob(f"*/{JOB_DATA}/jd.json"):
        if json.loads(saved.read_text(encoding="utf-8"))["public_slug"] == slug:
            return saved.parent.parent
    return None


def job_dir_for(root: Path, job: dict) -> Path:
    """Same job => same folder; other job w/ same company + title => ' (2)' suffix."""
    found = find_job_dir(root, job["public_slug"])
    if found:
        return found
    base = folder_name(job)
    candidate, n = root / base, 2
    while candidate.exists():
        candidate, n = root / f"{base} ({n})", n + 1
    return candidate


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def check_command(slug: str) -> str:
    return f'uv run app/jobs.py tailor check "{slug}"'


def posting(text_file: Path, url: str) -> None:
    then = f'uv run app/jobs.py tailor prepare --posting "{text_file}"' + (f' --url "{url}"' if url else "")
    handoff.write_task(POSTING_TASK, POSTING_ANSWER, jd.EXTRACT_SYSTEM, jd.EXTRACT_SCHEMA,
                       text_file.read_text(encoding="utf-8").strip(), then)


def prepare(config: dict, slug: str | None, posting_file: Path | None, url: str) -> None:
    master = schema.load(cfg.resume_path(config, "master"))
    if posting_file:
        got = handoff.read_answer(POSTING_ANSWER, jd.EXTRACT_SCHEMA)
        job = jd.from_text(posting_file.read_text(encoding="utf-8"), url, got)
    else:
        with httpx.Client(timeout=config["api"]["timeout_s"]) as client:
            job = jd.fetch(client, config["api"]["base"], slug)
    job_dir = job_dir_for(cfg.resume_path(config, "jobs_dir"), job)
    data = job_dir / JOB_DATA
    data.mkdir(parents=True, exist_ok=True)
    write_json(data / "jd.json", job)
    (job_dir / POSTING_FILE).write_text(report.posting_md(job), encoding="utf-8")
    request = build_request(master, job, cfg.resume_font(config))
    handoff.write_task(data / "task.md", data / "tailored.json", request["system"], request["schema"],
                       request["prompt"], check_command(job["public_slug"]))
    print(f"job folder: {job_dir}")


def check(config: dict, slug: str) -> int:
    master = schema.load(cfg.resume_path(config, "master"))
    job_dir = find_job_dir(cfg.resume_path(config, "jobs_dir"), slug)
    if job_dir is None:
        sys.exit(f"no job folder for {slug}; run tailor prepare first")
    data = job_dir / JOB_DATA
    job = json.loads((data / "jd.json").read_text(encoding="utf-8"))
    tailored = handoff.read_answer(data / "tailored.json", TAILORED_SCHEMA)
    result = evaluate(master, job, tailored, job_dir, cfg.resume_font(config))
    rows = coverage_rows(job, tailored)
    gaps = schema.employment_gaps(master, date.today())
    (job_dir / CHECK_FILE).write_text(
        report.report_md(job, tailored, result, rows, gaps) + "\n" + report.diff_md(master, tailored, result["model"]),
        encoding="utf-8")

    for name, ok, detail in result["gates"]:
        print(f"  {'pass' if ok else 'FAIL'}  {name:22} {detail}")
    for line in result["failed"]:
        print(f"  FAIL  {line}")
    met = sum(r["status"] == "met" for r in rows)
    required_gaps = [r for r in rows if r["status"] == "gap" and r["priority"] == "required"]
    print(f"coverage {met}/{len(rows)} met, {len(required_gaps)} required gap(s)")
    print(f"{'FAILED - fix tailored.json, rerun check' if result['failed'] else 'passed'}: {job_dir}")
    return 1 if result["failed"] else 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Tailor resume to one job: AI writes content, this prepares + checks it")
    steps = ap.add_subparsers(dest="step", required=True)
    p = steps.add_parser("posting", help="pasted posting text -> AI task extracting title, company, requirements")
    p.add_argument("text_file", type=Path)
    p.add_argument("--url", default="")
    p = steps.add_parser("prepare", help="job folder + AI tailoring task")
    p.add_argument("slug", nargs="?", help="jobs.public_slug; omit with --posting")
    p.add_argument("--posting", type=Path, help="pasted posting text file, after posting step")
    p.add_argument("--url", default="", help="posting URL, with --posting")
    p = steps.add_parser("check", help="check AI's tailored.json: PDF, gates, Check before sending.md")
    p.add_argument("slug")
    args = ap.parse_args()
    if args.step == "posting":
        posting(args.text_file, args.url)
        return
    config = cfg.load()
    if args.step == "prepare":
        if bool(args.slug) == bool(args.posting):
            ap.error("prepare takes either slug or --posting")
        prepare(config, args.slug, args.posting, args.url)
    else:
        sys.exit(check(config, args.slug))


if __name__ == "__main__":
    main()
