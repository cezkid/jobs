import argparse
import copy
import json
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
import locks
from resume import carry, facts, handoff, schema, tidy, word

ZERO_WIDTH = re.compile("[\u200b\u200c\u200d\u2060\ufeff]")
# Word exports its 2nd-level bullet as a plain "o" (Courier New) and Symbol/Wingdings bullets as
# private-use U+F0A7 / U+F0B7; left in, each bullet line gains a stray "o" word recovery counts missing
LINE_BULLET = re.compile("^[ \t]*(?:[\u25cf\u2022\u25aa\u25e6\u00b7\uf0a7\uf0b7]|o(?=[ \t]|$))", re.M)
FOLD = str.maketrans({
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u00a0": " ", "\u202f": " ",
    # Word's non-breaking hyphen (phones, date ranges), hyphen, minus sign; soft hyphen shows only at a line end
    "\u2010": "-", "\u2011": "-", "\u2212": "-", "\u00ad": "",
    # typeset ligatures (LaTeX, design apps): "After E\ufb00ects" matches no "After Effects" ask and
    # fails the page's ligature gate; one character each, so the AI's copy can't spell them out
    "\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl", "\ufb05": "st", "\ufb06": "st",
})
# PDF text w/ ligatures spelled out (pymupdf keeps them by default)
PDF_TEXT = pymupdf.TEXTFLAGS_TEXT & ~pymupdf.TEXT_PRESERVE_LIGATURES
WHITESPACE = re.compile(r"\s+")
# a reel's password ("password: cutfast24", "pw = reel24"): never a fact, never printed (SYSTEM)
PASSWORD = re.compile(r"(\b(?:password|passcode|pass|pwd|pw)\s*[:=]\s*)[^\s,;|)]+", re.I)
PASSWORD_NOTE = ("  <- a link password, kept off the page on purpose: a resume is copied into every system it's "
                 "uploaded to. They type it in the application's own box; an unlisted link needs none")
# "Reel <link: vimeo.com/name>": the word(s) back to the last separator, then the mark
LABELLED = re.compile(r"([^|\t\n,;]*?)\s*<link: (\S+?)>")
WORD = re.compile(r"\w+")
# subset font w/o ToUnicode map extracts glyph ids => text mostly non-letters
MIN_ALPHA_RATIO = 0.5
# every source word lands in master; headings excluded
MIN_RECOVERY = 0.98
MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
ENDPOINT = re.compile(r"^(?:(?P<month>[a-z]{3})[a-z]*\.?\s+)?(?P<year>\d{4})$")
# Word resumes write "10/24" or "03/2019"; slash is no range separator, so a part stays whole
NUMERIC_ENDPOINT = re.compile(r"^(?P<month>\d{1,2})/(?P<year>\d{2}|\d{4})$")
RANGE_SEP = re.compile(r"\s*-\s*|\s+to\s+")
# "2021-03 - 2023-05": a date's own hyphen is no range separator, so ISO months are split first
ISO_MONTH = re.compile(r"^(?P<year>\d{4})-(?P<month>\d{2})$")
ISO_RANGE = re.compile(r"^(\d{4}-\d{2})\s*(?:-|to)\s*(\d{4}-\d{2}|\D.*)$")
# "date" = what "... to date" leaves once " to " splits the range
PRESENT_WORDS = {"present", "current", "now", "ongoing", "today", "till date", "date"}
NON_SLUG = re.compile(r"[^a-z0-9]+")
# a section heading carries no fact, so it is the one line recovery may skip. Named, never guessed
# from capitals: "ACTIVE TS/SCI CLEARANCE" or "BLS/ACLS CERTIFIED" is all caps and a real credential
HEADING = re.compile(
    r"^(?:(?:professional|work|relevant|technical|core|key|additional|other|selected|career|volunteer)\s+)?"
    r"(?:experience|work history|employment(?: history)?|history|education(?: and (?:training|professional development))?|"
    r"training|professional development|"
    r"skills(?: and abilities)?|competencies|summary|profile|objective|about(?: me)?|"
    r"certifications?(?: and licen[cs]es?)?|licen[cs]es?(?: and certifications?)?|credentials|projects|languages|"
    r"volunteer(?:ing)?|work|awards(?: and honors)?|honors(?: and awards)?|achievements|accomplishments|"
    r"publications|interests|activities|affiliations|memberships|references|qualifications|highlights|expertise|"
    # a student's page: Relevant Coursework, Leadership & Activities, Campus Involvement, Academic Projects
    r"coursework|courses|leadership(?: experience| and activities| and involvement)?|activities and leadership|"
    r"extracurricular(?: activities)?|campus involvement|involvement|research(?: experience)?|academic projects|"
    r"projects and activities)"
    r"\s*:?$", re.I)
# words a student's education lines carry around the facts copied out of them ("GPA: 3.62/4.00",
# "Relevant Coursework: ...", "Expected May 2027"): counted as kept when the school holds that fact
EDUCATION_LABELS = {"gpa", "cumulative", "overall", "relevant", "selected", "coursework", "courses", "expected",
                    "anticipated", "graduation", "class", "of"}
# qualifiers around a graduation date: "Expected May 2027", "May 2027 (expected)", "Class of 2027"
EXPECTED_WORDS = re.compile(r"^(?:expected|anticipated|projected|estimated|est\.?|exp\.?|graduating|graduation|"
                            r"class of)\s*:?\s*|\s*\((?:expected|anticipated)\)$|\s+(?:expected|anticipated)$", re.I)
# the source itself says the degree isn't done yet ("Class of 2025" alone says nothing either way)
SAYS_EXPECTED = re.compile(r"\b(?:expected|anticipated|projected|estimated|est|exp)\b", re.I)

SYSTEM = """You map resume text extracted from the user's resume file (PDF or Word) onto fixed fields. You never write, rephrase, correct or expand.

Rules:
- Every string you emit is copied character-for-character from the source text. Only allowed change: joining a line wrapped across a line break with one space, and dropping bullet glyphs.
- Never add words: no legal suffixes on company names, no https:// on links, no expanded abbreviations, no fixed typos or capitalization.
- `<link: ADDRESS>` after a word = a web address the file hid behind that word ("Reel <link: vimeo.com/name>"): ADDRESS goes in `contact.links`, copied as written; the word itself only where it belongs anyway (a name stays the name; "Reel", "Portfolio", "LinkedIn" go nowhere). Never copy the mark into another field.
- A password for a link ("password: ...", "pw: ...") is no link and no fact: leave it out. It is never printed; the user types it into an application's own box.
- `dates` = the exact calendar date range from the source (e.g. "Feb 2023 - Oct 2026", "2019 - 2021"); null when the source gives none. Durations ("6 Summers") stay inside the claim, never in `dates`.
- Two titles under one company = two roles, each with its own dates and bullets.
- `blurb` = company description line (industry, product, website) exactly as written.
- `metrics` = verbatim number phrases inside the claim. `stack` = verbatim technology names inside the claim.
- `ai_work` true only when the claim itself describes AI/LLM work.
- Skills: `group` is your short label; `items` = each pipe- or comma-separated entry copied verbatim. A comma inside brackets splits nothing: "Adobe Creative Cloud (Premiere Pro, After Effects)" is one item.
- `dates` on a project may be null when the source gives none.
- Education: `start` / `end` = the source's own date words ("Aug 2023", "Expected May 2027", "Class of 2027"); a range splits into start and end. `gpa` = the GPA figure exactly as written ("3.62/4.00", "9.2/10"), never rounded or converted. `coursework` = each course listed under that school, copied verbatim. Honors and minors stay in `details`.
- Clubs, student organisations, teams, sororities and fraternities, student government, volunteering with a role: one `projects` entry each - `name` = the group exactly as written, `role` = the position held ("Treasurer"), `section` = the heading it sits under, as written ("Leadership & Activities"). Class or academic projects: `projects` with `section` only if the source gives them their own heading. Never leave out, shorten, generalise or reword a group because of what kind of group it is (cultural, religious, identity, political): copy every one.
- `other` = every section fitting none of the fields above (volunteer work, awards, clearances, publications, licences outside a certifications list, film or TV credits, guild or union memberships): `heading` as written, `lines` each source line copied verbatim, dates left inside the line.
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
    projects=array(obj(name=STRING, role=NULLABLE, section=NULLABLE, dates=NULLABLE, bullets=array(BULLET))),
    skills=array(obj(group=STRING, items=STRINGS)),
    education=array(obj(institution=STRING, degree=STRING, field=NULLABLE, details=NULLABLE, start=NULLABLE, end=NULLABLE,
                        gpa=NULLABLE, coursework=STRINGS)),
    certifications=array(obj(name=STRING, issuer=NULLABLE, date=NULLABLE)),
    languages=STRINGS,
    other=array(obj(heading=STRING, lines=STRINGS)),
)
# a student's fields came later: an answer written before them (or one leaving them out) still checks
for _entry, _keys in ((MAPPED_SCHEMA["properties"]["projects"]["items"], ("role", "section")),
                      (MAPPED_SCHEMA["properties"]["education"]["items"], ("start", "gpa", "coursework"))):
    _entry["required"] = [k for k in _entry["required"] if k not in _keys]


def extract(path: Path) -> str:
    """Resume file -> text the AI maps and the gates check: PDF or Word, told by its first bytes."""
    if word.kind(path) != "pdf":
        text = LINE_BULLET.sub("", ZERO_WIDTH.sub("", word.read(path)))
        if not WORD.search(text):
            raise ValueError(f"{path.name}: no text in it")
        return text
    # content-stream order, never pymupdf4llm: its column detection interleaved two-column page 2 (measured 2026-09-16)
    with pymupdf.open(path) as doc:
        raw = "\n".join(marked_links(page) for page in doc)
    text = LINE_BULLET.sub("", ZERO_WIDTH.sub("", raw)).translate(FOLD)
    visible = [c for c in text if not c.isspace()]
    if not visible:
        raise ValueError(f"{path}: no text layer (scanned?)")
    alpha = sum(c.isalpha() for c in visible) / len(visible)
    if alpha < MIN_ALPHA_RATIO:
        raise ValueError(f"{path}: {alpha:.0%} letters - fonts lack ToUnicode map, text is glyph ids")
    return text


def marked_links(page: pymupdf.Page) -> str:
    """Page text, each web address hidden behind words marked after them (word.LINK_MARK)."""
    text = page.get_text(flags=PDF_TEXT)
    words = page.get_text("words", flags=PDF_TEXT)
    links = [(pymupdf.Rect(link["from"]), link["uri"]) for link in page.get_links() if link.get("uri")]
    cursor = 0
    for rect, url in sorted(links, key=lambda pair: (pair[0].y0, pair[0].x0)):
        label = [w[4] for w in words if rect.contains(pymupdf.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2))]
        if not (mark := word.link_mark(" ".join(label), url)):
            continue
        # first showing of those words after the last mark: text runs in the order links are read
        found = re.compile(r"\s+".join(re.escape(w) for w in label)).search(text, cursor)
        if found:
            text = text[:found.end()] + mark + text[found.end():]
            cursor = found.end() + len(mark)
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
    for kind, named in (("roles", ("company", "title", "location", "blurb", "dates")),
                        ("projects", ("name", "role", "section", "dates"))):
        for i, entry in enumerate(mapped[kind]):
            for key in named:
                add(f"{kind}[{i}].{key}", entry.get(key))
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
        for key in ("institution", "degree", "field", "details", "start", "end", "gpa"):
            add(f"education[{i}].{key}", school.get(key))
        for k, course in enumerate(school.get("coursework") or []):
            add(f"education[{i}].coursework[{k}]", course)
    for i, cert in enumerate(mapped["certifications"]):
        for key in ("name", "issuer", "date"):
            add(f"certifications[{i}].{key}", cert[key])
    for i, v in enumerate(mapped["languages"]):
        add(f"languages[{i}]", v)
    for i, section in enumerate(mapped["other"]):
        add(f"other[{i}].heading", section["heading"])
        for k, v in enumerate(section["lines"]):
            add(f"other[{i}].lines[{k}]", v)
    return out


def untraced(mapped: dict, source: str) -> list[str]:
    haystack = normalize(source)
    return [f"{path}: {value!r}" for path, value in traced_strings(mapped) if normalize(value) not in haystack]


def heading(text: str) -> bool:
    return bool(HEADING.match(normalize(text).replace("&", "and")))


def content_lines(source: str) -> list[str]:
    # a layout table puts a heading cell and its first entry on one tab-joined line: the heading
    # part is skipped there too, or its words count against recovery
    out = []
    for line in source.splitlines():
        parts = [part.strip() for part in line.split("\t") if WORD.search(part) and not heading(part)]
        if parts:
            out.append("\t".join(parts))
    return out


def recovery(mapped: dict, source: str) -> tuple[float, list[str]]:
    got = Counter(w for _, v in traced_strings(mapped) for w in WORD.findall(normalize(v)))
    # a skill group label stays untraced (AI may coin its own), but one copied from the source
    # ("Agile Practice - Scrum, Kanban") holds that line's words; counted here or the line reads left out
    got.update(w for group in mapped["skills"] for w in WORD.findall(normalize(group["group"])))
    if any(s.get("gpa") or s.get("coursework") or s.get("end") or s.get("start") for s in mapped["education"]):
        got.update(EDUCATION_LABELS)
    # the word a link hid behind ("Reel <link: vimeo.com/name>") is the address's label, kept once it is
    links = {normalize(link) for link in mapped["contact"].get("links") or []}
    lines = [LABELLED.sub(lambda m: "" if normalize(m[2]) in links else f"{m[1]} {m[2]}", line)
             for line in content_lines(source)]
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


def endpoint(value: str, today: date) -> str | None:
    if match := ISO_MONTH.match(value):
        return value if 1 <= int(match["month"]) <= 12 else None
    if match := NUMERIC_ENDPOINT.match(value):
        if not 1 <= int(match["month"]) <= 12:
            return None
        year = int(match["year"])
        if len(match["year"]) == 2:
            # "98" is 1998, not 2098: a 20YY past next year can't be a real date on a resume
            year += 2000 if 2000 + year <= today.year + 1 else 1900
        return f"{year}-{int(match['month']):02d}"
    match = ENDPOINT.match(value)
    if not match or (match["month"] and match["month"] not in MONTHS):
        return None
    # year-only source stays a year: a month the resume never gave is one a checker may not find
    return f"{match['year']}-{MONTHS.index(match['month']) + 1:02d}" if match["month"] else match["year"]


def parse_endpoint(text: str, where: str, today: date, assumptions: list[str], school: bool = False) -> str | None:
    value = normalize(text)
    if value in PRESENT_WORDS:
        return schema.PRESENT
    if school:
        value = EXPECTED_WORDS.sub("", value).strip()
    result = endpoint(value, today)
    if result is None:
        # left unset => schema flags field missing; hand edit settles it
        assumptions.append(f"{where}: unparseable date {text!r}, set by hand")
        return None
    # a school's end ahead of today is a degree still being earned, not a slip
    if not school and schema.month_index(result, today) > schema.month_index(schema.PRESENT, today):
        assumptions.append(f"{where}: {result} after today")
    return result


def parse_range(text: str | None, where: str, today: date, assumptions: list[str]) -> dict:
    if not text:
        return {}
    value = normalize(text)
    iso = ISO_RANGE.match(value)
    parts = [iso[1], iso[2]] if iso else RANGE_SEP.split(value)
    if len(parts) != 2:
        assumptions.append(f"{where}: dates {text!r} not start - end, set by hand")
        return {}
    return {
        "start": parse_endpoint(parts[0], f"{where}.start", today, assumptions),
        "end": parse_endpoint(parts[1], f"{where}.end", today, assumptions),
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
            "id": project_id, "name": p["name"], "role": p.get("role"), "section": p.get("section"),
            **parse_range(p["dates"], f"projects[{i}]", today, assumptions),
            "ai_era": any(b.get("ai_work") for b in bullets),
            "bullets": bullets,
        }))
    education = []
    for i, s in enumerate(mapped["education"]):
        where = f"education[{i}]"
        dates = {"start": s.get("start"), "end": s["end"]}
        # "Aug 2023 - Expected May 2027" mapped whole into end: a range is a start and an end
        if s["end"] and not s.get("start") and len(RANGE_SEP.split(normalize(s["end"]))) == 2:
            dates["start"], dates["end"] = RANGE_SEP.split(normalize(s["end"]))
        start = dates["start"] and parse_endpoint(dates["start"], f"{where}.start", today, assumptions, school=True)
        end = dates["end"] and parse_endpoint(dates["end"], f"{where}.end", today, assumptions, school=True)
        studying = bool(end) and (bool(SAYS_EXPECTED.search(normalize(dates["end"]))) or
                                  schema.in_progress({"end": end}, today))
        education.append(drop_empty({**{k: v for k, v in s.items() if k not in ("start", "end")}, "start": start,
                                     "end": end, "expected": True if studying else None,
                                     "coursework": s.get("coursework") or None}))
    certifications = []
    for i, c in enumerate(mapped["certifications"]):
        when = c["date"] and parse_endpoint(c["date"], f"certifications[{i}].date", today, assumptions)
        certifications.append(drop_empty({**c, "date": when}))
    if schema.out_of_order(roles):
        roles = schema.newest_first(roles)
        assumptions.append("the resume file listed jobs out of date order - they are now newest first")
    master = drop_empty({
        "contact": drop_empty(mapped["contact"]),
        "summary": mapped["summary"],
        "roles": roles,
        "projects": projects,
        "skills": mapped["skills"],
        "education": education,
        "certifications": certifications,
        "languages": mapped["languages"],
        "other": [drop_empty(o) for o in mapped["other"] if o["lines"]],
    })
    return master, assumptions


# what prepare handed the AI: finish checks the answer against exactly this text (never a re-read -
# a PDF and a Word copy can both sit in My Resume), and the next --force reads that same file
def source_record() -> Path:
    return cfg.DATA / "resume-source.json"


def original(config: dict, suffix: str) -> Path:
    """My Resume/Original resume.pdf, or .docx for a Word resume - the other one is never touched."""
    return cfg.resume_path(config, "input_pdf").with_suffix(suffix)


def recorded(config: dict) -> tuple[Path, str | None]:
    """(file the last prepare read, its text) - (input_pdf, None) when nothing is recorded."""
    try:
        record = json.loads(source_record().read_text(encoding="utf-8"))
        return Path(record["file"]), record["text"]
    except (OSError, ValueError, KeyError, TypeError):
        return cfg.resume_path(config, "input_pdf"), None


def source_file(config: dict) -> Path:
    return recorded(config)[0]


def prepare(config: dict, file_from: Path | None, force: bool) -> None:
    master_path = cfg.resume_path(config, "master")
    if master_path.exists() and not force:
        sys.exit(f"{master_path} exists - hand edits live there; --force to read a new resume file "
                 "(finish then lists what the new file lacks, and keeps what the user picks)")
    if file_from and (refused := word.refusal(file_from)):
        sys.exit(refused)
    source = original(config, file_from.suffix.lower()) if file_from else source_file(config)
    if file_from:
        source.parent.mkdir(parents=True, exist_ok=True)
        if file_from.resolve() != source.resolve():
            shutil.copyfile(file_from, source)
    try:
        text = extract(source)
    except ValueError as e:
        sys.exit(str(e))
    source_record().parent.mkdir(parents=True, exist_ok=True)
    locks.write_atomic(source_record(), json.dumps({"file": str(source), "text": text}))
    handoff.write_task(TASK, ANSWER, SYSTEM, MAPPED_SCHEMA, text, FINISH,
                       f"Your resume file is unchanged: {source}", "the rules for reading your resume")


def finish(config: dict, keep: str | None = None) -> None:
    started = time.perf_counter()
    (pdf, source), master_path = recorded(config), cfg.resume_path(config, "master")
    source = source if source is not None else extract(pdf)
    mapped = handoff.read_answer(ANSWER, MAPPED_SCHEMA)

    failures = untraced(mapped, source)
    ratio, dropped = recovery(mapped, source)
    print(f"recovery {ratio:.1%} (floor {MIN_RECOVERY:.0%}), untraced {len(failures)}")
    for line in failures:
        print(f"  untraced {line}")
    left_out(dropped)
    if failures or ratio < MIN_RECOVERY:
        sys.exit(f"gate failed, nothing written; fix {ANSWER} to copy source text exactly, then rerun"
                 + handoff.stop_text(handoff.failed(ANSWER, quiet=True)))
    handoff.passed(ANSWER)

    today = date.today()
    master, assumptions = build(mapped, today)
    plain, kept_copy = tidy.strip(master), None
    if master_path.exists():
        # the user's own additions since the last import: listed, kept only when they say so
        try:
            old = yaml.safe_load(master_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            old = {}
        left = carry.left_behind(old, plain)
        if any(left.values()) and keep is None:
            print("The new resume file lacks things in the resume details - nothing written yet:")
            print("\n".join(carry.describe(left)))
            print("Ask the user ONE multiSelect question (these groups, w/ what each holds; tick all that fit, "
                  "then Submit), then:\n  uv run app/jobs.py resume-import finish --keep <groups comma-separated | all | none>")
            sys.exit(2)
        kept_copy = carry.backup(master_path)
        plain = carry.carry(plain, left, carry.kept(keep, left))
    extra = [f"# Read out of {pdf.name} on {today.isoformat()}; importing again needs --force."]
    extra += [f"# assumed {a}" for a in assumptions]
    master_path.parent.mkdir(parents=True, exist_ok=True)
    with facts.resume_lock():
        facts.write(master)
        locks.write_atomic(master_path, tidy.dump(plain, extra))

    errors = schema.validate(schema.expand(copy.deepcopy(plain)))
    print(f"wrote {master_path} in {time.perf_counter() - started:.1f}s")
    if kept_copy:
        print(f"old file kept at {kept_copy}")
    for a in assumptions:
        print(f"  assumed  {a}")
    dated = all("start" in r and "end" in r for r in master["roles"])
    for gap in schema.employment_gaps(master, today) if dated else []:
        print(f"  gap      {gap['after']} -> {gap['before']} ({gap['months']} months)")
    for e in errors:
        print(f"  schema   {e}")
    if errors:
        sys.exit(f"schema errors above need hand edits in {master_path.name}")


def left_out(dropped: list[str]) -> None:
    """Every resume-file line not fully in the details file, pass or fail: the user decides, not the floor.
    A link's password is masked and named as kept off on purpose - never read back into the chat."""
    if not dropped:
        print("left out: nothing - every line of the resume file is in the resume details")
        return
    print(f"left out: {len(dropped)} line(s) of the resume file are not fully in the resume details. "
          "Read each one to the user; any that is a real fact goes back in:")
    for line in dropped:
        masked = PASSWORD.sub(lambda m: f"{m[1]}{'*' * 4}", line)
        print(f"  - {masked}" + (PASSWORD_NOTE if masked != line else ""))


def main() -> None:
    ap = argparse.ArgumentParser(description="Resume file (PDF or Word .docx) -> structured resume details: prepare AI task, then finish")
    ap.add_argument("step", choices=["prepare", "finish"])
    ap.add_argument("--file", "--pdf", dest="file", type=Path,
                    help="prepare: resume PDF or Word (.docx) anywhere on disk; copied into My Resume first")
    ap.add_argument("--force", action="store_true", help="prepare: read a new resume file over existing resume details")
    ap.add_argument("--keep", help="finish, re-import: groups of the old file to keep - "
                                   f"{', '.join(carry.GROUPS)}, all or none (finish lists them first)")
    args = ap.parse_args()
    # resume paths only: runs before search settings exist (the welcome page reads a picked resume at
    # once; setup may import it first) - shipped defaults then, the same paths
    config = cfg.load_or_defaults()
    if args.step == "prepare":
        prepare(config, args.file, args.force)
    else:
        finish(config, args.keep)


if __name__ == "__main__":
    main()
