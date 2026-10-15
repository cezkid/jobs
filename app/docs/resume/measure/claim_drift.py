#!/usr/bin/env python3
"""Claim drift: what the tailoring AI and the letter AI wrote beyond the facts they cited (plan-d4t.5).

Proposed generated-text gates wait on this count (bullets.md #Considered, not mechanised: measure
before enforcing). Real AI output lives only in the owner's job folders, so this reads them in place:
read-only, no network, no AI call.

  uv run app/docs/resume/measure/claim_drift.py [root] [--show]

root = the folder holding `My Jobs/` (default: this checkout's). Each `My Jobs/<stage>/<job>/.data/`:
  task.md + tailored.json        each bullet vs its sources' facts, the summary vs every fact
  letter-task.md + letter.json   each paragraph vs the facts it cites (their own sentence left out)
The facts are the ones the AI saw: the payload in the task file (handoff.TASK), not today's resume.
A line citing an id that payload lacks (an older resume) is skipped and counted.

Counts only; --show adds each hit with its line - claim text, so it stays on this computer:
  (a) a number every source qualifies ("about 120", "20+") written bare - lint.dropped_qualifier
  (b) a co- word ("co-led") written bare - lint.dropped_qualifier
  (c) a superlative no cited fact uses; "first" / "only" in their own column
  (d) longest run of words copied in order from the posting, per line: 5 / 6 / 7 / 8+
  (e) the posting's most used word: times on the tailored page vs the untailored one
  (f) bracket placeholders ("[Company]", "{metric}", "<team size>") no cited fact holds
  (g) hedge upgrade: a cited fact opens hedged ("Assisted with") and the line opens "Led" / "Built" ...
  (h) reach: "company-wide", "adopted by ..." in no cited fact (bullets + letter paragraphs, not summary)
  (i) vendor credit: a cited fact names a vendor / contractor, the line opens "Built" and names none
  Ship rule for each: FAIL only w/ >= 1 true hit and 0 false on 300+ lines; else report-only.
"""

import argparse
import collections
import json
import re
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(APP))

import yaml  # noqa: E402

import cfg  # noqa: E402
from resume import letter, lint  # noqa: E402

SUPERLATIVE = re.compile(r"(?<![\w-])(largest|biggest|fastest|youngest|first-ever|industry-first|record-breaking)(?![\w-])"
                         r"|(?<![\w#])#1(?!\d)", re.I)
FIRST_ONLY = re.compile(r"(?<![\w-])(first|only)(?![\w-])", re.I)
PLACEHOLDER = re.compile(r"\[[^\]\n]*\]|\{[^}\n]*\}|<[^>\n]*>")
RUNS = (5, 6, 7, 8)  # histogram buckets; the last is 8 or more
TASK_FILE, ANSWER_FILE = "task.md", "tailored.json"
HEDGE = re.compile(r"(assist(ed|ing)?|help(ed|ing)?|support(ed|ing)?|contribut(ed|ing)e?|participat(ed|ing)e?"
                   r"|collaborat(ed|ing)e?|worked on|part of|involved in)(?![\w-])", re.I)
STRONG_LEAD = {"led", "owned", "built", "drove", "directed", "managed", "architected", "spearheaded", "headed",
               "founded", "launched", "created", "designed", "delivered", "established", "ran", "oversaw"}
REACH = re.compile(r"(?<![\w-])((company|organization|organisation|department|enterprise|firm|team|org|business)-wide"
                   r"|(across|throughout) (the )?(entire |whole )?(company|organization|organisation|enterprise|firm|business)"
                   r"|adopted by [\w ]{3,30}|(entire|whole) (company|organization|organisation))(?![\w-])", re.I)
VENDOR = re.compile(r"(?<![\w-])(vendors?|contractors?|outsourced|agency|third-party|consultants?|freelancers?"
                    r"|offshore|subcontract\w*)(?![\w-])", re.I)
PAYLOAD_START = re.compile(r"^(?:\{$|your_words:)", re.M)


def payload(task: Path):
    """The Input section of a task file (handoff.TASK) as data: JSON for tailoring, YAML for a letter."""
    text = task.read_text(encoding="utf-8")
    start, end = text.find("\n## Input\n"), text.rfind("\n## Answer schema\n")
    # the payload's first line, after whatever words on input the template carried that day:
    # tailoring's JSON opens "{", a letter's YAML its first key
    at = PAYLOAD_START.search(text, start, end) if 0 <= start < end else None
    if not at:
        return None
    try:
        if task.name == TASK_FILE:
            return json.loads(text[at.start():end])
        return yaml.safe_load(text[at.start():end])
    except (ValueError, yaml.YAMLError):
        return None


def facts(master: dict) -> dict[str, list[str]]:
    """Bullet id -> its fact's words: the claim + any older metrics list."""
    return {b["id"]: [b.get("claim") or "", *(b.get("metrics") or [])]
            for e in [*master.get("roles", []), *master.get("projects", [])] for b in e.get("bullets", [])}


def posting_text(job: dict) -> str:
    return " ".join([job.get("title") or "", job.get("description") or "",
                     *(r.get("text") or "" for r in job.get("requirements", []))])


def words(text: str) -> list[str]:
    return [t.casefold() for t in lint.TOKEN.findall(text)]


def longest_run(text: str, posting: list[str], at: dict[str, list[int]]) -> int:
    """Most words in a row `text` shares, in order, with the posting."""
    tokens, best = words(text), 0
    for i, token in enumerate(tokens):
        for p in at.get(token, ()):
            k = 1
            while i + k < len(tokens) and p + k < len(posting) and tokens[i + k] == posting[p + k]:
                k += 1
            best = max(best, k)
    return best


def top_term(posting: str) -> str | None:
    counts = collections.Counter(w for w in words(posting)
                                 if len(w) > 2 and not w[0].isdigit() and w not in letter.STOPWORDS)
    return counts.most_common(1)[0][0] if counts else None


def times(term: str, texts: list[str]) -> int:
    return sum(words(t).count(term) for t in texts)


class Tally:
    def __init__(self, show: bool):
        self.show = show
        self.n = collections.Counter()
        self.runs = collections.Counter()
        self.terms = collections.Counter()
        self.lines: list[str] = []

    def hit(self, key: str, where: str, text: str, detail: str) -> None:
        self.n[key] += 1
        if self.show:
            self.lines.append(f"  ({key[0]}) {where}: {detail} - {text!r}")

    def line(self, where: str, text: str, sources: list[str], posting: list[str], at: dict,
             per_source: bool = True) -> None:
        """One generated line vs the facts it rests on."""
        self.n["lines"] += 1
        said = " | ".join(sources)
        for found in lint.dropped_qualifier(text, sources):
            self.hit("a qualifier" if not lint.CO_WORD.match(found) else "b co", where, text, f"sources say {found!r}")
        for pattern, key in ((SUPERLATIVE, "c superlative"), (FIRST_ONLY, "c first/only")):
            for word in sorted({m.group().casefold() for m in pattern.finditer(text)}):
                if not re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", said, re.I):
                    self.hit(key, where, text, f"{word!r} in no cited fact")
        run = longest_run(text, posting, at)
        if run >= RUNS[0]:
            self.runs[min(run, RUNS[-1])] += 1
            if self.show:
                self.lines.append(f"  (d) {where}: {run} words in a row from the posting - {text!r}")
        for m in PLACEHOLDER.finditer(text):
            if m.group() not in said:
                self.hit("f placeholder", where, text, f"{m.group()!r}")
        if per_source:
            self.sourced(where, text, said)

    def sourced(self, where: str, text: str, said: str) -> None:
        """Kinds g-i: one line against its own cited sources (never the whole resume)."""
        lead = (re.match(r"\W*([A-Za-z-]+)", text) or [None, ""])[1].casefold()
        if HEDGE.match(said.lstrip()) is not None or any(HEDGE.match(s.strip()) for s in said.split(" | ")):
            if lead in STRONG_LEAD and not re.search(rf"(?<![\w-]){re.escape(lead)}", said, re.I):
                self.hit("g hedge upgrade", where, text, f"sources hedge, line opens {lead!r}")
        for m in REACH.finditer(text):
            if not re.search(re.escape(m.group()), said, re.I):
                self.hit("h reach", where, text, f"{m.group().casefold()!r} in no cited fact")
        if VENDOR.search(said) and lead in STRONG_LEAD and not VENDOR.search(text):
            self.hit("i vendor credit", where, text, "sources name a vendor, line does not")


def measure_job(data: Path, tally: Tally) -> None:
    name = data.parent.name
    request = payload(data / TASK_FILE) if (data / TASK_FILE).exists() else None
    if not isinstance(request, dict) or not (data / ANSWER_FILE).exists():
        return
    try:
        tailored = json.loads((data / ANSWER_FILE).read_text(encoding="utf-8"))
    except ValueError:
        return
    if not isinstance(tailored, dict):
        return
    tally.n["tailored"] += 1
    master, job = request.get("master") or {}, request.get("job") or {}
    posting = words(posting_text(job))
    at = collections.defaultdict(list)
    for p, token in enumerate(posting):
        at[token].append(p)
    by_id = facts(master)
    page = []
    if summary := tailored.get("summary"):
        page.append(summary)
        tally.line(f"{name} summary", summary, lint.master_strings(master), posting, at, per_source=False)
    for entry in tailored.get("entries", []):
        for i, bullet in enumerate(entry.get("bullets", []), 1):
            page.append(bullet["text"])
            if not bullet.get("sources") or any(s not in by_id for s in bullet["sources"]):
                tally.n["skipped"] += 1
                continue
            sources = [s for b in bullet["sources"] for s in by_id[b]]
            tally.line(f"{name} {entry.get('id')} bullet {i}", bullet["text"], sources, posting, at)
    page += [tailored.get("headline_title") or ""] + [i for g in tailored.get("skills", []) for i in g.get("items", [])]
    if term := top_term(posting_text(job)):
        untailored = [master.get("summary") or "", *(s for f in by_id.values() for s in f),
                      *(i for g in master.get("skills", []) for i in g.get("items", []))]
        now, before = times(term, page), times(term, untailored)
        tally.terms["more" if now > before else "same" if now == before else "fewer"] += 1
        tally.terms["tailored"] += now
        tally.terms["untailored"] += before
        if tally.show:
            tally.lines.append(f"  (e) {name}: {term!r} {now} on the tailored page, {before} untailored")
    measure_letter(data, name, posting, at, tally)


def measure_letter(data: Path, name: str, posting: list[str], at: dict, tally: Tally) -> None:
    task, answer = data / letter.TASK_FILE, data / letter.ANSWER_FILE
    if not task.exists() or not answer.exists():
        return
    request = payload(task)
    try:
        drafted = json.loads(answer.read_text(encoding="utf-8"))
    except ValueError:
        return
    if not isinstance(request, dict) or not isinstance(drafted, dict):
        return
    tally.n["letters"] += 1
    master, why = request.get("master") or {}, str(request.get("your_words") or "").strip()
    known = facts(master)
    known |= {f"certifications[{i}]": [" ".join(str(v) for v in c.values())] for i, c in enumerate(master.get("certifications") or [])}
    known |= {f"education[{i}]": [" ".join(str(v) for v in s.values())] for i, s in enumerate(master.get("education") or [])}
    for i, p in enumerate(drafted.get("paragraphs", []), 1):
        if any(s not in known for s in p.get("sources", [])):
            tally.n["skipped"] += 1
            continue
        text = p["text"].replace(why, " ") if why else p["text"]
        sources = [s for c in p.get("sources", []) for s in known[c]] + letter.headers_of(master, p.get("sources", []))
        tally.line(f"{name} letter paragraph {i}", text, sources, posting, at)


def job_data(root: Path) -> list[Path]:
    jobs = root / "My Jobs"
    return sorted({p.parent for name in (TASK_FILE, letter.TASK_FILE) for p in jobs.glob(f"**/.data/{name}")})


def measure(root: Path, show: bool = False) -> Tally:
    tally = Tally(show)
    for data in job_data(root):
        measure_job(data, tally)
    return tally


def report(tally: Tally) -> str:
    n, runs, terms = tally.n, tally.runs, tally.terms
    out = [
        f"claim drift: {n['tailored']} tailored resumes, {n['letters']} letters, {n['lines']} lines read, "
        f"{n['skipped']} skipped (cite a fact the task file lacks)",
        f"(a) number qualifier dropped: {n['a qualifier']}",
        f"(b) co- dropped: {n['b co']}",
        f"(c) superlative in no cited fact: {n['c superlative']}   first/only: {n['c first/only']}",
        "(d) longest run from the posting: " + "  ".join(
            f"{r}{'+' if r == RUNS[-1] else ''}: {runs[r]}" for r in RUNS),
        f"(e) posting's top word: more on the tailored page {terms['more']}, same {terms['same']}, "
        f"fewer {terms['fewer']} (total {terms['tailored']} tailored vs {terms['untailored']} untailored)",
        f"(f) bracket placeholder: {n['f placeholder']}",
        f"(g) hedged source, stronger verb: {n['g hedge upgrade']} of {n['lines']} lines",
        f"(h) reach no cited fact makes: {n['h reach']} of {n['lines']} lines",
        f"(i) vendor's work credited: {n['i vendor credit']} of {n['lines']} lines",
    ]
    return "\n".join(out + tally.lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="count claim drift in tailored resumes + letters (read-only)")
    ap.add_argument("root", nargs="?", type=Path, default=cfg.ROOT, help="folder holding My Jobs/")
    ap.add_argument("--show", action="store_true", help="also print each hit with its line (claim text)")
    args = ap.parse_args()
    print(report(measure(args.root, args.show)))


if __name__ == "__main__":
    main()
