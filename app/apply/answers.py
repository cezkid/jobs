"""Saved answers: the user's own answers to application questions, reused on the next form.

Kept in My Settings/Saved answers.yml - visible, private, their words. Only an answer they gave
(source "you said") is kept, only after they said yes to keeping them (settings
`saved_answers: true`). freehire.me's captured forms (647,795, measured 2026-09-09) counted how-did-you-hear 61,762, an
18-or-older gate 30,337, salary 24,762, notice period 7,841 (2026-09) - most questions still
recall nothing (69% of 12,352 labels in a 4,000-form sample), so most are still asked.

Recall, by what's at stake if it's wrong for this job:
- filled + named before Submit: 18 or older, notice period, how you heard, the same question word
  for word;
- offered first, never filled: the pay you expect (shown beside the posting's pay), moving for the
  job, start date, any written answer - each depends on this job;
- never kept or recalled: work permit + sponsorship (setup's answers, the US question asked the same
  way - a saved Yes would travel to another country's form), sensitive kinds, voluntary questions
  about them, where they live, current pay, agreeing / consenting / signing (an "I agree" kept
  would tick the next form's box - the applicant's own act).
"""
import argparse
import re
import sys
import unicodedata
from datetime import date

import yaml

import cfg
import locks
from apply import questions

FILE = cfg.ROOT / "My Settings" / "Saved answers.yml"
HEADER = ("# Your own answers from application forms, reused on the next one - each named to you before\n"
          "# Submit. Tell the chat to forget one; nothing else removes them.\n")
MAX_CHARS = 2000
TOPICS = (
    ("expected pay", r"(?:desired|expected|expectation|expect).{0,30}(?:salary|compensation|pay)|(?:salary|compensation|pay).{0,30}(?:expect|desired|requirement)"),
    ("current pay", r"current (?:salary|compensation|pay)|(?:salary|pay) (?:currently|now)"),
    ("notice period", r"notice period|how much notice"),
    ("start date", r"start date|when can you start|available to start|earliest (?:start|date)"),
    ("moving for the job", r"relocat"),
    ("how you heard", r"how did you (?:hear|find out|learn about)|where did you hear|how you heard"),
    ("18 or older", r"\bat least 18\b|over the age of 18|18 years of age or older|\b18 or older\b"),
)
FILLED = {"notice period", "how you heard", "18 or older"}
NEVER = re.compile(r"authori[sz]|right to work|sponsor|\bvisa\b|citizen|green card|current (?:salary|compensation|pay)")
POLITE = re.compile(r"^(?:please |kindly )?(?:tell us|share|provide|let us know|could you|we'd like to know)\b\W*")


def fold(text: str) -> str:
    plain = unicodedata.normalize("NFKC", text).casefold()
    plain = POLITE.sub("", plain.strip())
    return " ".join(re.findall(r"\w+", plain))


def topic(text: str) -> str | None:
    found = [name for name, pattern in TOPICS if re.search(pattern, text, re.I)]
    return found[0] if len(found) == 1 else None


def key(q: dict) -> str | None:
    """What a saved answer is filed under: its topic, else the question folded; None = never kept."""
    title = q["title"]
    if (q.get("kind") == "file" or q.get("key") or NEVER.search(title.casefold())
            or questions.sensitive(q, {}) or topic(title) == "current pay"
            or questions.signs(title) or questions.never_draft(title) in ("where you live", questions.VOLUNTARY)):
        return None
    if len([n for n, p in TOPICS if re.search(p, title, re.I)]) > 1:
        return None  # two topics in one question: asked, never guessed
    return topic(title) or fold(title) or None


def load() -> list[dict]:
    if not FILE.exists():
        return []
    try:
        return yaml.safe_load(FILE.read_text(encoding="utf-8")) or []
    except yaml.YAMLError:
        raise SystemExit(f"{FILE} can't be read - nothing saved or reused until it's fixed by hand")


def write(saved: list[dict]) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    with locks.held(cfg.DATA / "answers.lock", "another chat is saving answers - try again in a minute"):
        locks.write_atomic(FILE, HEADER + yaml.safe_dump(saved, sort_keys=False, allow_unicode=True, width=10_000))


def keep(asked: list[dict], job: str, company: str, on: str) -> int:
    """Answers the user gave on this form, one per topic or question; the newest wins."""
    saved = load()
    added = 0
    for q in asked:
        k, answer = key(q), q.get("answer")
        if not k or q.get("source") != questions.USER_SAID or questions.blank(answer) or isinstance(answer, bool):
            continue
        text = ", ".join(answer) if isinstance(answer, list) else str(answer).strip()
        if len(text) > MAX_CHARS:
            continue
        saved = [s for s in saved if s["key"] != k]
        saved.append({"key": k, "question": q["title"], "answer": text, "job": job, "company": company, "on": on})
        added += 1
    if added:
        write(saved)
    return added


def recall(saved: list[dict], q: dict) -> tuple[str, dict] | None:
    """("fill" | "offer", saved entry) for a question a saved answer fits."""
    k = key(q)
    hit = next((s for s in reversed(saved) if k and s["key"] == k), None)
    if hit is None:
        return None
    same = fold(hit["question"]) == fold(q["title"])
    fills = (k in FILLED or same) and q["kind"] != "longtext" and (not q["options"] or hit["answer"] in q["options"])
    return ("fill" if fills else "offer"), hit


def named(hit: dict) -> str:
    return f"your answer from {hit['job']}'s form, {hit['on']}"


def main() -> None:
    ap = argparse.ArgumentParser(description="saved answers from application forms: list | forget N")
    ap.add_argument("step", choices=("list", "forget"))
    ap.add_argument("n", nargs="?", type=int, help="forget: the number list shows")
    args = ap.parse_args()
    saved = load()
    if args.step == "list":
        print("\n".join(f"{i}. {s['question']} -> {s['answer']} ({named(s)})" for i, s in enumerate(saved, 1))
              or "no saved answers")
        return
    if not args.n or not 1 <= args.n <= len(saved):
        sys.exit("forget: give the number `answers list` shows")
    gone = saved.pop(args.n - 1)
    write(saved)
    print(f"forgot: {gone['question']}")


if __name__ == "__main__":
    main()
