"""Fill the gaps: ask the user for the numbers and leadership their bullets leave out.

Resume scorers and career guides alike mark a bullet without a number as weak, and the easy fix
they offer is a template - "for {{count}} screens". A template filled by anyone but the user is
an invented number (docs/resume/bullets.md Tier 1), so this asks instead. `prepare` lists every bullet without a
number, every bullet saying "helped" or "we" (whose part was it?), and a leadership question for each
recent job, as an AI task; the AI asks the user in
chat and writes down only what they said; `finish` checks every number, name and tool in a
reworded line came from the old line or the user's answer - never from a sentence where the
answer denies it, never a stronger ownership verb than either used - then merges it into
My Resume/Resume details.yml with a backup. A skipped question changes nothing. Measured on 5 real
answers (2026-10-01): no negation cue, no upgraded verb - guards against a known failure, not a
measured one; 2 of the 5 were two words, so no minimum answer length.
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

import yaml

import cfg
import locks
from resume import facts, handoff, lint, schema, tidy
from resume.carry import claim_key as carry_key

STRING, NULLABLE, obj, array = handoff.STRING, handoff.NULLABLE, handoff.obj, handoff.array
TASK = cfg.DATA / "gaps-task.md"
ANSWER = cfg.DATA / "gaps.json"
BACKUP_NAME = "Resume details before gaps.yml"
# leadership is asked about for the most recent jobs only: what an employer reads first, and a
# short chat - leadership is read across the page, not demanded of every job
LEADERSHIP_ROLES = 3
PART_ASK = ("This line says \"{word}\". What was your own part - what did you do, and what did the "
            "team do? \"Helped\" stays if that's the truth.")
# a hedge or "we" leaves the reader guessing whose work it was; one question per line, before a number
PART_WORDS = re.compile(rf"{lint.HEDGES.pattern}|\b(?:we|our|ours)\b", re.I)
# "I didn't lead them" holds "lead them": a name or number the answer only denies never goes in
NEGATION = re.compile(r"n't\b|\bnot\b|\bnever\b|\bno longer\b|\bwithout ever\b|\bcannot\b", re.I)
REFUSALS = {"no", "none", "nope", "not really", "n/a", "na", "not sure", "don't know", "dont know", "no idea"}
NUMBER_ASK = ("Can you put a real number on this - how many (people, users, screens, items, "
              "locations), how often, how much faster, cheaper or bigger, or what changed after? "
              "Skip it if you don't know the number for sure.")
LEADERSHIP_ASK = ("At {company} ({title}), did you lead, mentor or train anyone, or start something "
                  "others then used - a process, tool, event or program? Only what really happened, "
                  "and how many people if you know.")
# a student with fewer jobs than that: their clubs and teams are where leadership shows
ACTIVITY_ASK = ("In {name} ({role}), did you lead, organise or train anyone, or start something others "
                "then used - an event, a project, a program? Only what really happened, and how many "
                "people if you know.")
FACT_ASK = ("Something real you said in practice that {at} doesn't show yet - add it, in your own words? "
            "Only what happened, never something you tried out.")
ANSWER_SCHEMA = obj(answers=array(obj(id=STRING, said=NULLABLE, claim=NULLABLE)))
SYSTEM = """You help the candidate add facts only they know. Every line you write comes from their own answer.

Asking
- Ask the user each question in `questions`, in plain words, in this chat - ONE question per ask, never batched (several at once show as tabs and users stall there). Clickable choices where they fit ("I know it" / "Not sure - skip"); the number itself is free text.
- Show the line the question is about. Say why once: numbers and scope are what a reader can picture, and anything on the page gets asked about in interview.
- Never guess, estimate, round or suggest a number. "About 20" is written as the user said it ("about 20", "20+"). Don't know -> skip; skipping costs nothing.

Answer
- One entry per question: `id` as given; `said` = the user's answer in their own words, null if skipped.
- `claim`: null when skipped, when the answer says no, or when it adds nothing. For `number`: the line rewritten to carry what they said, keeping the rest of their wording. For `part`: the line rewritten to say what they themselves did, in their words - "helped" stays when that is the truth; never a stronger verb (led, managed, owned) than they used. For `leadership`: one new line in their words, opening with what they did ("Mentored 3 junior engineers on ...").
- Never write what the answer denies: "I didn't lead the 4 new hires" puts neither "led" nor "4" in a line.
- For `fact` (interview practice): only a fact the user said happened AND agreed to add - never something they improvised, hedged or tried out ("I could say ..."). `claim` = one new line in their words; null for every job they added nothing to.
- Every number, name and tool in `claim` must appear in the original line or in `said` - the check fails anything else.
- Confidential work (compliance, AML, fraud, audit, investigations, legal, health records): never a customer's, client's or investigated person's name, a case detail, a non-public exam finding, or anything that could point to one Suspicious Activity Report (31 U.S.C. 5318(g)(2)) - volume and outcome only ("Cleared 60+ alerts a day"). An answer carrying one -> ask them for the same fact without it; never write it.
- One sentence, US spelling, no em dash. Aim for one full line or two (`uv run app/jobs.py resume-fit "<line>"` tells you which)."""


def questions(master: dict) -> list[dict]:
    """Bullets without a digit, then leadership for the recent jobs - each with where it lives."""
    out = []
    for section in ("roles", "projects"):
        for i, entry in enumerate(master.get(section) or []):
            for j, bullet in enumerate(entry["bullets"]):
                word = PART_WORDS.search(bullet["claim"])
                if word or not lint.NUMBER.search(bullet["claim"]):
                    out.append({"id": f"q{len(out) + 1}", "kind": "part" if word else "number", "section": section,
                                "entry": i, "bullet": j, "line": bullet["claim"],
                                "ask": PART_ASK.format(word=word[0]) if word else NUMBER_ASK,
                                "job": entry.get("title", entry.get("name")), "at": entry.get("company")})
    for i, role in enumerate(master["roles"][:LEADERSHIP_ROLES]):
        out.append({"id": f"q{len(out) + 1}", "kind": "leadership", "section": "roles", "entry": i, "bullet": None,
                    "line": None, "ask": LEADERSHIP_ASK.format(company=role["company"], title=role["title"]),
                    "job": role["title"], "at": role["company"],
                    "already": [b["claim"] for b in role["bullets"]]})
    room = LEADERSHIP_ROLES - len(master["roles"][:LEADERSHIP_ROLES])
    groups = [(i, p) for i, p in enumerate(master.get("projects") or []) if p.get("role")][:max(room, 0)]
    for i, group in groups:
        out.append({"id": f"q{len(out) + 1}", "kind": "leadership", "section": "projects", "entry": i, "bullet": None,
                    "line": None, "ask": ACTIVITY_ASK.format(name=group["name"], role=group["role"]),
                    "job": group["role"], "at": group["name"], "already": [b["claim"] for b in group["bullets"]]})
    return out


def fact_questions(master: dict) -> list[dict]:
    """One per job + project: where a fact the user stated in interview practice goes."""
    out = []
    for section in ("roles", "projects"):
        for i, entry in enumerate(master.get(section) or []):
            at = " at ".join(x for x in (entry.get("title") or entry.get("name"), entry.get("company")) if x)
            out.append({"id": f"q{len(out) + 1}", "kind": "fact", "section": section, "entry": i, "bullet": None,
                        "line": None, "ask": FACT_ASK.format(at=at), "job": entry.get("title", entry.get("name")),
                        "at": entry.get("company"), "already": [b["claim"] for b in entry["bullets"]]})
    return out


def files(job_dir: Path | None) -> tuple[Path, Path, Path]:
    """(task, answer, questions): a job's interview facts sit in its own folder, so two chats never
    cross-wire; the resume-wide numbers + leadership round keeps .data/."""
    if job_dir is None:
        return TASK, ANSWER, cfg.DATA / "gaps-questions.yml"
    data = job_dir / tailor_data()
    return data / "facts-task.md", data / "facts.json", data / "facts-questions.yml"


def tailor_data() -> str:
    from resume import tailor  # tailor imports this module's neighbours; resolved at call time
    return tailor.JOB_DATA


def prepare(path: Path, job_dir: Path | None = None) -> list[dict]:
    task, answer, saved = files(job_dir)
    master = schema.load(path)
    asked = fact_questions(master) if job_dir else questions(master)
    payload = yaml.safe_dump({"questions": asked}, sort_keys=False, allow_unicode=True, width=10_000)
    saved.parent.mkdir(parents=True, exist_ok=True)
    saved.write_text(payload, encoding="utf-8")
    then = "uv run app/jobs.py resume-gaps finish" + (f' --job "{job_dir.name}"' if job_dir else "")
    handoff.write_task(task, answer, SYSTEM, ANSWER_SCHEMA, payload, then,
                       "Your resume details stay as they were - nothing changed.", "the rules for your answers")
    if job_dir:
        print(f"{len(asked)} job(s) a stated fact could go under")
        return asked
    kinds = {k: sum(q["kind"] == k for q in asked) for k in ("number", "part", "leadership")}
    print(f"{kinds['number']} line(s) without a number, {kinds['part']} saying 'helped' or 'we', "
          f"{kinds['leadership']} leadership question(s)")
    return asked


def invented(claim: str, sources: list[str]) -> list[str]:
    """Numbers, names and tools in `claim` found in none of `sources`."""
    known = {lint.entity_key(t) for t in lint.TOKEN.findall(" ".join(s for s in sources if s))}
    return sorted({e for e in lint.entities(claim) if lint.entity_key(e) not in known})


def negated(said: str, term: str) -> str | None:
    """The sentence of `said` naming `term` after a negation cue. A "but" opens a new clause:
    "I didn't lead it, but I trained 2 new hires" gives the 2."""
    for sentence in re.split(r"[.;!?]", said):
        at = sentence.casefold().find(term.casefold())
        if at >= 0 and NEGATION.search(re.split(r"\bbut\b", sentence[:at], flags=re.I)[-1]):
            return sentence.strip()
    return None


def problems(asked: list[dict], answers: list[dict], master: dict) -> list[str]:
    by_id = {q["id"]: q for q in asked}
    out = [f"{a['id']}: not one of the questions" for a in answers if a["id"] not in by_id]
    for a in answers:
        q = by_id.get(a["id"])
        if q is None or not a["claim"]:
            continue
        if not (a["said"] or "").strip():
            out.append(f"{a['id']}: claim written but `said` is empty - only the user's answer goes in")
            continue
        if a["said"].strip().casefold().rstrip(".!") in REFUSALS:
            out.append(f"{a['id']}: the answer says no ({a['said']!r}) - claim must be null")
            continue
        line_keys = {lint.entity_key(t) for t in lint.TOKEN.findall(q["line"] or "")}
        for term in sorted({e for e in lint.entities(a["claim"]) if lint.entity_key(e) not in line_keys}):
            if sentence := negated(a["said"], term):
                out.append(f"{a['id']}: the answer denies {term!r} ({sentence!r}) - write only what they did")
        if verb := lint.upgraded_verb(a["claim"], [q["line"], a["said"]]):
            out.append(f"{a['id']}: {verb!r} claims more than the line or the answer says - use their own verb")
        entry = master[q["section"]][q["entry"]]
        header = [entry.get(k) for k in ("company", "title", "name", "location", "blurb")]
        if extra := invented(a["claim"], [q["line"], a["said"], *header]):
            out.append(f"{a['id']}: {extra} in neither the old line nor the user's answer: {a['claim']!r}")
        if lint.EM_DASH in a["claim"] or "\n" in a["claim"]:
            out.append(f"{a['id']}: one plain line, no em dash: {a['claim']!r}")
        if q["kind"] == "fact" and carry_key(a["claim"]) in {carry_key(c) for c in q["already"]}:
            out.append(f"{a['id']}: already a line under that job: {a['claim']!r}")
        if q["kind"] not in ("leadership", "fact") and master[q["section"]][q["entry"]]["bullets"][q["bullet"]]["claim"] != q["line"]:
            out.append(f"{a['id']}: that line changed since the questions were written - run prepare again")
    return out


def merge(path: Path, asked: list[dict], answers: list[dict], notes: Path | None = None) -> tuple[int, int, Path]:
    """Write answered lines into the user's file; skipped ones untouched. (changed, added, backup)."""
    with facts.resume_lock(notes):
        return _merge(path, asked, answers, notes)


def _merge(path: Path, asked: list[dict], answers: list[dict], notes: Path | None) -> tuple[int, int, Path]:
    master = schema.load(path, notes)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    by_id = {q["id"]: q for q in asked}
    changed = added = 0
    # appends go last so a reworded line's position is never shifted by a new one above it
    appended = ("leadership", "fact")
    for a in sorted((a for a in answers if a["claim"]), key=lambda a: by_id[a["id"]]["kind"] in appended):
        q = by_id[a["id"]]
        entry, internal = raw[q["section"]][q["entry"]], master[q["section"]][q["entry"]]
        if q["kind"] not in appended:  # number, part: the line rewritten in place
            bullet = entry["bullets"][q["bullet"]]
            if isinstance(bullet, dict):
                bullet["claim"] = a["claim"]
            else:
                entry["bullets"][q["bullet"]] = a["claim"]
            # its notes (stack, metrics) follow the reworded claim instead of dropping off
            internal["bullets"][q["bullet"]]["claim"] = a["claim"]
            changed += 1
        else:
            entry["bullets"].append(a["claim"])
            added += 1
    backup = (notes or facts.PATH).parent / BACKUP_NAME
    if not changed + added:
        return 0, 0, backup
    shutil.copyfile(path, backup)
    locks.write_atomic(path, tidy.dump(raw))
    try:
        schema.load(path, notes)
    except ValueError:
        shutil.copyfile(backup, path)
        raise
    facts.write(master, notes)
    return changed, added, backup


def finish(path: Path, job_dir: Path | None = None) -> int:
    _, answer, saved = files(job_dir)
    asked = yaml.safe_load(saved.read_text(encoding="utf-8"))["questions"]
    answers = handoff.read_answer(answer, ANSWER_SCHEMA)["answers"]
    if found := problems(asked, answers, schema.load(path)):
        print("\n".join(f"  FAIL  {p}" for p in found))
        print("fix gaps.json, rerun finish")
        handoff.failed(answer)
        return 1
    handoff.passed(answer)
    changed, added, backup = merge(path, asked, answers)
    skipped = len(asked) - changed - added
    print(f"{changed} line(s) now carry your number, {added} new line(s) added, {skipped} left as they were")
    if changed + added:
        print(f"old file kept at {backup}")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="ask the user for the numbers and leadership their bullets leave out")
    ap.add_argument("step", choices=("prepare", "finish"))
    ap.add_argument("--master", type=Path, help="resume details file (default: the one in settings)")
    ap.add_argument("--job", help="interview practice: facts the user stated for this job, kept in its folder")
    args = ap.parse_args()
    config = cfg.load()
    path = args.master or cfg.resume_path(config, "master")
    if not path.exists():
        sys.exit(f"{path} missing - import the resume PDF first")
    job_dir = None
    if args.job:
        from resume import tailor
        job_dir = tailor.find_job_dir(cfg.resume_path(config, "jobs_dir"), tailor.by_number(config, args.job)) \
            or next((d for d in cfg.resume_path(config, "jobs_dir").glob(f"*/{args.job}") if d.is_dir()), None)
        if job_dir is None:
            sys.exit(f"no job folder for {args.job}")
    if args.step == "prepare":
        prepare(path, job_dir)
    else:
        sys.exit(finish(path, job_dir))


if __name__ == "__main__":
    main()
