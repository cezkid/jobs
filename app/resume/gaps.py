"""Fill the gaps: ask the user for the numbers and leadership their bullets leave out.

VMock (2026-09-24) scored six bullets weak for carrying no number and offered templates to fill
them - "for {{count}} screens". A template filled by anyone but the user is an invented
number (docs/bullets.md Tier 1), so this asks instead. `prepare` lists every bullet without a
number, and a leadership question for each recent job, as an AI task; the AI asks the user in
chat and writes down only what they said; `finish` checks every number, name and tool in a
reworded line came from the old line or the user's answer, then merges it into
My Resume/Resume details.yml with a backup. A skipped question changes nothing.
"""
import argparse
import shutil
import sys
from pathlib import Path

import yaml

import cfg
from resume import facts, handoff, lint, schema, tidy

STRING, NULLABLE, obj, array = handoff.STRING, handoff.NULLABLE, handoff.obj, handoff.array
TASK = cfg.DATA / "gaps-task.md"
ANSWER = cfg.DATA / "gaps.json"
BACKUP_NAME = "Resume details before gaps.yml"
# leadership is asked about for the most recent jobs only: what an employer reads first, and a
# short chat - VMock counted leadership across the page, not per job
LEADERSHIP_ROLES = 3
NUMBER_ASK = ("Can you put a real number on this - how many (people, users, screens, items, "
              "locations), how often, how much faster, cheaper or bigger, or what changed after? "
              "Skip it if you don't know the number for sure.")
LEADERSHIP_ASK = ("At {company} ({title}), did you lead, mentor or train anyone, or start something "
                  "others then used - a process, tool, event or program? Only what really happened, "
                  "and how many people if you know.")
ANSWER_SCHEMA = obj(answers=array(obj(id=STRING, said=NULLABLE, claim=NULLABLE)))
SYSTEM = """You help the candidate add facts only they know. Every line you write comes from their own answer.

Asking
- Ask the user each question in `questions`, in plain words, in this chat. Batch up to 4 per round with clickable choices where they fit ("I know the number" / "Not sure - skip"); the number itself is free text.
- Show the line the question is about. Say why once: numbers and scope are what a reader can picture, and anything on the page gets asked about in interview.
- Never guess, estimate, round or suggest a number. "About 20" is written as the user said it ("about 20", "20+"). Don't know -> skip; skipping costs nothing.

Answer
- One entry per question: `id` as given; `said` = the user's answer in their own words, null if skipped.
- `claim`: null when skipped or when the answer adds nothing. For `number`: the line rewritten to carry what they said, keeping the rest of their wording. For `leadership`: one new line in their words, opening with what they did ("Mentored 3 junior engineers on ...").
- Every number, name and tool in `claim` must appear in the original line or in `said` - the check fails anything else.
- One sentence, US spelling, no em dash. Aim for one full line or two (`uv run app/jobs.py resume-fit "<line>"` tells you which)."""


def questions(master: dict) -> list[dict]:
    """Bullets without a digit, then leadership for the recent jobs - each with where it lives."""
    out = []
    for section in ("roles", "projects"):
        for i, entry in enumerate(master.get(section) or []):
            for j, bullet in enumerate(entry["bullets"]):
                if not lint.NUMBER.search(bullet["claim"]):
                    out.append({"id": f"q{len(out) + 1}", "kind": "number", "section": section, "entry": i,
                                "bullet": j, "line": bullet["claim"], "ask": NUMBER_ASK,
                                "job": entry.get("title", entry.get("name")), "at": entry.get("company")})
    for i, role in enumerate(master["roles"][:LEADERSHIP_ROLES]):
        out.append({"id": f"q{len(out) + 1}", "kind": "leadership", "section": "roles", "entry": i, "bullet": None,
                    "line": None, "ask": LEADERSHIP_ASK.format(company=role["company"], title=role["title"]),
                    "job": role["title"], "at": role["company"],
                    "already": [b["claim"] for b in role["bullets"]]})
    return out


def prepare(path: Path) -> list[dict]:
    asked = questions(schema.load(path))
    payload = yaml.safe_dump({"questions": asked}, sort_keys=False, allow_unicode=True, width=10_000)
    (cfg.DATA / "gaps-questions.yml").write_text(payload, encoding="utf-8")
    handoff.write_task(TASK, ANSWER, SYSTEM, ANSWER_SCHEMA, payload, "uv run app/jobs.py resume-gaps finish")
    numbers = sum(q["kind"] == "number" for q in asked)
    print(f"{numbers} line(s) without a number, {len(asked) - numbers} leadership question(s)")
    return asked


def invented(claim: str, sources: list[str]) -> list[str]:
    """Numbers, names and tools in `claim` found in none of `sources`."""
    known = {lint.entity_key(t) for t in lint.TOKEN.findall(" ".join(s for s in sources if s))}
    return sorted({e for e in lint.entities(claim) if lint.entity_key(e) not in known})


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
        entry = master[q["section"]][q["entry"]]
        header = [entry.get(k) for k in ("company", "title", "name", "location", "blurb")]
        if extra := invented(a["claim"], [q["line"], a["said"], *header]):
            out.append(f"{a['id']}: {extra} in neither the old line nor the user's answer: {a['claim']!r}")
        if lint.EM_DASH in a["claim"] or "\n" in a["claim"]:
            out.append(f"{a['id']}: one plain line, no em dash: {a['claim']!r}")
        if q["kind"] == "number" and master[q["section"]][q["entry"]]["bullets"][q["bullet"]]["claim"] != q["line"]:
            out.append(f"{a['id']}: that line changed since the questions were written - run prepare again")
    return out


def merge(path: Path, asked: list[dict], answers: list[dict], notes: Path | None = None) -> tuple[int, int, Path]:
    """Write answered lines into the user's file; skipped ones untouched. (changed, added, backup)."""
    master = schema.load(path, notes)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    by_id = {q["id"]: q for q in asked}
    changed = added = 0
    # appends go last so a reworded line's position is never shifted by a new one above it
    for a in sorted((a for a in answers if a["claim"]), key=lambda a: by_id[a["id"]]["kind"] == "leadership"):
        q = by_id[a["id"]]
        entry, internal = raw[q["section"]][q["entry"]], master[q["section"]][q["entry"]]
        if q["kind"] == "number":
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
    path.write_text(tidy.dump(raw), encoding="utf-8")
    try:
        schema.load(path, notes)
    except ValueError:
        shutil.copyfile(backup, path)
        raise
    facts.write(master, notes)
    return changed, added, backup


def finish(path: Path) -> int:
    asked = yaml.safe_load((cfg.DATA / "gaps-questions.yml").read_text(encoding="utf-8"))["questions"]
    answers = handoff.read_answer(ANSWER, ANSWER_SCHEMA)["answers"]
    if found := problems(asked, answers, schema.load(path)):
        print("\n".join(f"  FAIL  {p}" for p in found))
        print("fix gaps.json, rerun finish")
        return 1
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
    args = ap.parse_args()
    path = args.master or cfg.resume_path(cfg.load(), "master")
    if not path.exists():
        sys.exit(f"{path} missing - import the resume PDF first")
    if args.step == "prepare":
        prepare(path)
    else:
        sys.exit(finish(path))


if __name__ == "__main__":
    main()
