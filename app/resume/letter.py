"""Cover letter for one job, checked like the resume: the AI drafts, code checks, the user confirms.

Basis graded in app/docs/resume/cover-letter.md. What code holds a draft to:
- the user's own sentence on why this job, verbatim, exactly once - their motive is never written
  for them (an AI's enthusiasm is the generic text readers spot);
- every number, tool and name in what they've done comes from the facts that paragraph cites;
- 3-4 paragraphs, at most 5 facts, 250-400 words - over fails, under is fine and said, never padded;
- none of the filler career guides warn against; the resume's own wording rules on the AI's words;
- date, greeting, contact block and sign-off by code, never the AI.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import pymupdf
import typst
import yaml

import cfg
from resume import gaps, handoff, lint, render, report, schema, tailor, typeface

WHY_FILE, TASK_FILE, ANSWER_FILE = "letter-why.txt", "letter-task.md", "letter.json"
MD_FILE = "Cover letter.md"
TEMPLATE = render.HERE / "templates" / "letter.typ"
PARAGRAPHS, MAX_WORDS, SHORT_WORDS, MAX_FACTS = (3, 4), 400, 250, 5
GREETING, CLOSING = "Dear Hiring Team,", "Sincerely,"
FAIL, WARN, INFO = "FAIL", "WARN", "info"
FILLER = re.compile(r"\bi am writing to\b|to whom it may concern|\bpassionate\b|excited to apply|\bdream job\b|"
                    r"perfect fit|hit the ground running|team player|results[- ]driven|\bsynerg", re.I)
# a letter's voice: capitalised, never a name the facts must hold
FIRST_PERSON = {"I", "I'm", "I've", "I'd", "I'll"}
# the resume's wording rules that hold in a letter too (first person is a letter's voice: not these)
PROSE_RULES = ("style-word", "resume-verb", "unmeasurable-grade", "em-dash", "markdown", "invisible-unicode",
               "round-metric", "spelling", "font-coverage")
# words a requirement uses that say nothing about having done it: never listed as "never shows"
STOPWORDS = set("""a an and are as at be been both but by can could do does etc for from has have how in into is it
its least may more most must of on one or our over plus should such than that the their them they this three to two
under up us use using via was we well were what when where which while who will with within without would you your
able ability abilities across also any based being best between building can collaborate demonstrated deep degree
desire environment equivalent etc excellent experience experienced familiarity field good great hands help high
including knowledge level make minimum new other part passion preferred proven related required requirement role
skills skill solid strong team teams understanding work working world years year""".split())
WHY = {
    "letter-shape": "A letter reads as 3 or 4 short paragraphs, each telling something the resume backs.",
    "your-words": "Why you want this job goes in exactly as you said it - never written for you.",
    "unresolved-entity": "A number, tool or name appears that the facts this paragraph cites never mention.",
    "too-many-facts": "A letter that cites more than 5 things reads as the resume again.",
    "letter-filler": "Phrases like 'passionate' or 'excited to apply' are what readers skim past.",
    "gap-claim": "This word is in the posting but nowhere in your resume - a gap, not a claim.",
    "restates-resume": "This sentence repeats a resume line; the letter should add, not repeat.",
    "letter-length": "Career guides put a letter at 250-400 words, under one page.",
}
ANSWER_SCHEMA = handoff.obj(paragraphs=handoff.array(handoff.obj(text=handoff.STRING, sources=handoff.STRINGS)))
SYSTEM = f"""You draft one cover letter for one job from the candidate's own facts. Code adds the date, greeting, contact details and sign-off - write only the paragraphs.

- {PARAGRAPHS[0]}-{PARAGRAPHS[1]} short paragraphs, {SHORT_WORDS}-{MAX_WORDS} words in all. First: the role, and the candidate's own sentence (`your_words`) verbatim, exactly once - never add reasons of your own. Middle: what they have done that this job asks for. Last: one line offering to talk.
- What the candidate has DONE comes only from facts you cite in each paragraph's `sources` (master bullet ids, `certifications[i]`, `education[i]`) - at most {MAX_FACTS} facts in all. Every number, tool and name in a paragraph must be in the facts it cites (code checks).
- Prefer requirements the resume does not show (`on_resume: false`): the letter adds, it never repeats a resume line.
- Never use a word from `words_resume_never_shows`: those are what the candidate has not shown - a gap, never a claim.
- No filler: "I am writing to", "To Whom It May Concern", passionate, excited to apply, dream job, perfect fit, hit the ground running, team player, results-driven.
- Plain US English, first person fine, no em dash, no markdown."""


def facts_of(master: dict) -> dict[str, str]:
    """Citable id -> the fact's own words: bullets, certifications[i], education[i]."""
    out = {b["id"]: b["claim"] for e in [*master["roles"], *master.get("projects", [])] for b in e["bullets"]}
    out |= {f"certifications[{i}]": render.joined(c["name"], c.get("issuer")) for i, c in enumerate(master.get("certifications") or [])}
    out |= {f"education[{i}]": schema.degree_words(s, date.today()) for i, s in enumerate(master.get("education") or [])}
    return out


def headers_of(master: dict, ids: list[str]) -> list[str]:
    """The job or project a cited bullet sits under: its employer, title, place are the fact's too."""
    entries = [e for e in [*master["roles"], *master.get("projects", [])] if {b["id"] for b in e["bullets"]} & set(ids)]
    return [str(e.get(k)) for e in entries for k in ("company", "title", "name", "role", "location") if e.get(k)]


def never_shows(job: dict, master: dict) -> list[str]:
    """Requirement words absent from every fact - what the resume has not shown."""
    corpus = set(re.findall(r"[a-z0-9+#]+", " ".join(lint.master_strings({k: v for k, v in master.items() if k != "contact"})).casefold()))
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#]{2,}", " ".join(r["text"] for r in job["requirements"]))
    return sorted({w.casefold() for w in words} - corpus - STOPWORDS)


def payload(master: dict, job: dict, tailored: dict, why: str) -> str:
    rows = tailor.coverage_rows(job, tailored, master)
    data = {
        "your_words": why,
        "job": {"title": job["title"], "company": job["company"], "requirements": [
            {"index": r["index"], "priority": r["priority"], "text": r["text"], "on_resume": r["status"] == "met",
             "resume_lines": r["shown"][:2]} for r in rows]},
        "words_resume_never_shows": never_shows(job, master),
        "resume_page": [b["text"] for t in tailored["entries"] for b in t["bullets"]],
        "master": {k: v for k, v in master.items() if k != "contact"},
        "limits": {"paragraphs": list(PARAGRAPHS), "words": [SHORT_WORDS, MAX_WORDS], "max_facts": MAX_FACTS},
    }
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=10_000)


def content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.casefold()) if w not in STOPWORDS and len(w) > 2}


def check(master: dict, job: dict, tailored: dict, why: str, answer: dict) -> list[tuple[str, str, str]]:
    paragraphs = [p["text"].strip() for p in answer["paragraphs"]]
    text = "\n\n".join(paragraphs)
    found: list[tuple[str, str, str]] = []
    if not PARAGRAPHS[0] <= len(paragraphs) <= PARAGRAPHS[1]:
        found.append((FAIL, "letter-shape", f"{len(paragraphs)} paragraphs - write {PARAGRAPHS[0]} or {PARAGRAPHS[1]}"))
    if text.count(why.strip()) != 1:
        found.append((FAIL, "your-words", f"their sentence must appear exactly once, word for word: {why.strip()!r}"))
    facts = facts_of(master)
    cited = [s for p in answer["paragraphs"] for s in p["sources"]]
    if unknown := sorted(set(cited) - facts.keys()):
        found.append((FAIL, "letter-shape", f"sources not in the resume details: {unknown}"))
    for i, p in enumerate(answer["paragraphs"][1:-1], 2):
        if not p["sources"]:
            found.append((FAIL, "letter-shape", f"paragraph {i} cites no fact"))
    if len(set(cited)) > MAX_FACTS:
        found.append((FAIL, "too-many-facts", f"{len(set(cited))} facts cited (at most {MAX_FACTS})"))
    gap_words = set(never_shows(job, master))
    page_lines = [b["text"] for t in tailored["entries"] for b in t["bullets"]]
    for i, p in enumerate(answer["paragraphs"], 1):
        own = p["text"].replace(why.strip(), " ")
        sources = [facts.get(s, "") for s in p["sources"]] + headers_of(master, p["sources"])
        if extra := [e for e in gaps.invented(own, [*sources, job["title"], job["company"]]) if e not in FIRST_PERSON]:
            found.append((FAIL, "unresolved-entity", f"paragraph {i}: {extra} in no fact it cites"))
        if m := FILLER.search(own):
            found.append((FAIL, "letter-filler", f"paragraph {i}: {m.group()!r}"))
        if used := sorted(content_words(own) & gap_words):
            found.append((WARN, "gap-claim", f"paragraph {i}: {used}"))
        for sentence in re.split(r"(?<=[.!?])\s+", own):
            words = content_words(sentence)
            if words and any(len(words & content_words(line)) / len(words) >= 0.8 for line in page_lines):
                found.append((WARN, "restates-resume", f"paragraph {i}: {sentence.strip()!r}"))
    if m := FILLER.search(why):
        found.append((WARN, "letter-filler", f"your sentence: {m.group()!r} - your words, your call"))
    count = len(re.findall(r"\w+", text))
    if count > MAX_WORDS:
        found.append((FAIL, "letter-length", f"{count} words (at most {MAX_WORDS}) - cut, never pad"))
    elif count < SHORT_WORDS:
        found.append((INFO, "letter-length", f"{count} words - short, fine if that's all that's true"))
    found += prose(master, job, [p.replace(why.strip(), " ") for p in paragraphs])
    return found


def prose(master: dict, job: dict, paragraphs: list[str]) -> list[tuple[str, str, str]]:
    """The resume's wording rules on the AI's words: each paragraph read as a summary line."""
    out = []
    for i, text in enumerate(paragraphs, 1):
        model = {"contact": {"name": master["contact"]["name"], "parts": []}, "summary": text, "sections": []}
        for f in lint.lint(model, master, posting=tailor.posting_text(job)):
            if f.rule in PROSE_RULES and f.where == "summary":
                out.append((f.severity, f.rule, f"paragraph {i}: {f.detail}"))
    return out


def page(master: dict, paragraphs: list[str], today: date) -> dict:
    contact, parts = master["contact"], render.contact_parts(master["contact"])
    return {"title": f"{contact['name']} Cover Letter", "date": f"{today:%B} {today.day}, {today.year}",
            "contact": {"name": contact["name"], "parts": [t for t, _ in parts], "part_urls": [u for _, u in parts]},
            "greeting": GREETING, "paragraphs": paragraphs, "closing": CLOSING}


def file_name(master: dict) -> str:
    return render.file_name({"contact": master["contact"]}).replace("_Resume.pdf", "_Cover_Letter.pdf")


def compile_letter(model: dict, font: str) -> bytes:
    pdf = typst.compile(str(TEMPLATE), font_paths=[str(typeface.folder(typeface.use(font)))], ignore_system_fonts=True,
                        sys_inputs={"data": json.dumps(render.with_page(model, font), ensure_ascii=False)}, pdf_standards="ua-1")
    return render.scrub(pdf, model["title"])


def gates(path: Path, font: str) -> list[tuple[str, bool, str]]:
    """The resume's page checks that a letter shares: one page, fonts built in, black, whole words."""
    with pymupdf.open(path) as doc:
        fonts = {f[0]: f for p in range(doc.page_count) for f in doc.get_page_fonts(p)}
        bare = [f[3] for x, f in fonts.items() if f[1] == "n/a" or doc.xref_get_key(x, "ToUnicode")[0] == "null"]
        colored, wide = render.colored_text(doc), render.spaced_letters(doc)
        foreign = render.foreign_glyphs(doc, font)
        return [("pages", doc.page_count == 1, f"{doc.page_count} page(s)"),
                ("fonts", bool(fonts) and not bare, f"missing embed/ToUnicode: {bare}" if bare else "built in"),
                ("text-color", not colored, f"not black: {colored}" if colored else "every word black"),
                ("split-words", not wide, f"letters spaced apart in {wide}" if wide else "whole words"),
                ("typeface", not foreign, f"drawn in another typeface: {foreign}" if foreign else f"every letter in {font}")]


def paste_text(master: dict, paragraphs: list[str]) -> str:
    """For a text box: no contact block (the form has its own fields), no date."""
    return "\n\n".join([GREETING, *paragraphs, f"{CLOSING}\n{master['contact']['name']}"]) + "\n"


def job_folder(config: dict, job: str) -> Path:
    folder = tailor.find_job_dir(cfg.resume_path(config, "jobs_dir"), tailor.by_number(config, job))
    if folder is None:
        sys.exit(f"no job folder for {job} - make its resume first")
    return folder


def prepare(config: dict, job: str) -> None:
    folder = job_folder(config, job)
    data = folder / tailor.JOB_DATA
    if not report.ready((folder / tailor.CHECK_FILE).read_text(encoding="utf-8") if (folder / tailor.CHECK_FILE).exists() else ""):
        sys.exit("the resume for this job isn't made yet (its check hasn't passed) - the letter rests on it")
    if not (data / WHY_FILE).exists() or not (data / WHY_FILE).read_text(encoding="utf-8").strip():
        sys.exit(f"ask them first, then save their answer word for word to {data / WHY_FILE}: "
                 "\"In one sentence, in your own words: why this job or this company?\"")
    master = schema.load(cfg.resume_path(config, "master"))
    payload_text = payload(master, json.loads((data / "jd.json").read_text(encoding="utf-8")),
                           json.loads((data / "tailored.json").read_text(encoding="utf-8")),
                           (data / WHY_FILE).read_text(encoding="utf-8").strip())
    handoff.write_task(data / TASK_FILE, data / ANSWER_FILE, SYSTEM, ANSWER_SCHEMA, payload_text,
                       f'uv run app/jobs.py letter check {job}',
                       f"Your resume for this job is ready to send without a letter: {folder / render.file_name(master)}",
                       "the rules for the cover letter")


def run_check(config: dict, job: str) -> int:
    folder = job_folder(config, job)
    data = folder / tailor.JOB_DATA
    master = schema.load(cfg.resume_path(config, "master"))
    answer = handoff.read_answer(data / ANSWER_FILE, ANSWER_SCHEMA)
    why = (data / WHY_FILE).read_text(encoding="utf-8").strip()
    found = check(master, json.loads((data / "jd.json").read_text(encoding="utf-8")),
                  json.loads((data / "tailored.json").read_text(encoding="utf-8")), why, answer)
    for severity, rule, detail in found:
        print(f"  {severity:4}  {rule:18} {WHY.get(rule) or lint.WHY.get(rule, '')} {detail}")
    if any(s == FAIL for s, _, _ in found):
        print(f"fix {data / ANSWER_FILE}, rerun: uv run app/jobs.py letter check {job}")
        handoff.failed(data / ANSWER_FILE)
        return 1
    paragraphs = [p["text"].strip() for p in answer["paragraphs"]]
    (folder / MD_FILE).write_text(paste_text(master, paragraphs), encoding="utf-8")
    font = cfg.resume_font(config)
    pdf = folder / file_name(master)
    pdf.write_bytes(compile_letter(page(master, paragraphs, date.today()), font))
    failed = [(n, d) for n, ok, d in gates(pdf, font) if not ok]
    for name, detail in failed:
        print(f"  FAIL  gate {name}: {detail}")
    facts = facts_of(master)
    for i, p in enumerate(answer["paragraphs"], 1):
        for s in p["sources"]:
            print(f"  paragraph {i} rests on: {facts.get(s, s)}")
    print(f"written: {folder / MD_FILE} (paste) + {pdf} (upload) - confirm each paragraph w/ the user")
    if failed:
        handoff.failed(data / ANSWER_FILE)
        return 1
    handoff.passed(data / ANSWER_FILE)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="cover letter for one job: prepare the AI task, then check the draft")
    ap.add_argument("step", choices=("prepare", "check"))
    ap.add_argument("job", help="job number, slug or job folder name")
    args = ap.parse_args()
    config = cfg.load()
    if args.step == "prepare":
        prepare(config, args.job)
    else:
        sys.exit(run_check(config, args.job))


if __name__ == "__main__":
    main()
