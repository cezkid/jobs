"""Resume parser test: one made-up resume in 7 layouts, read by open-source PDF readers, scored.

The study behind /research/resume-parser-test/ (method, written before the run:
app/web/research/resume-parser-test-2026-10/METHOD.md).

  uv run app/web/parser_test.py build            # facts.yml -> pdf/<layout>.pdf + truth.json
  uv run app/web/parser_test.py build --check    # exit 1 when a built file is stale (rerun = byte-identical)
  uv run app/web/parser_read.py > readings.json  # the readers (own pinned deps, not the project's)
  uv run app/web/parser_test.py score readings.json > results.csv

Truth comes from facts.yml, never from reading a PDF. Scoring (METHOD.md "Measures"): text is compared
as words (casefolded, split on anything not a letter or digit); blocks are found in the reader's word
stream by their opening words; job headers on one output line; name on the first line; email + phone
exact.
"""

import argparse
import collections
import csv
import io
import json
import re
import sys
from pathlib import Path

import pymupdf
import typst
import yaml

APP = Path(__file__).resolve().parent.parent
STUDY = APP / "web" / "research" / "resume-parser-test-2026-10"
FONTS = APP / "resume" / "fonts" / "Caladea"
LAYOUTS = ["one-column", "sidebar", "table", "header-footer", "icons", "text-boxes", "spaced-headings"]
HEADINGS = {"summary": "Summary", "experience": "Experience", "education": "Education", "skills": "Skills"}
KEY_WORDS = 5  # a block is found by its first words, up to this many
WORD = re.compile(r"[^\W_]+")
COLUMNS = ["layout", "reader", "broke", "broke_because", "lost_words", "extra_words", "split_words",
           "merged_words", "name_first_line", "name_found", "email", "phone", "job_headers_together",
           "blocks_not_found", "sections_mixed", "within_section_order", "page_order"]


def words(text: str) -> list[str]:
    return WORD.findall(text.casefold())


def squash(text: str) -> str:
    return " ".join(text.split())


# --- build ---

def load_facts(study: Path = STUDY) -> dict:
    return yaml.safe_load((study / "facts.yml").read_text(encoding="utf-8"))


def truth(facts: dict) -> dict:
    """Expected blocks in reading order (each tagged with its section) + the fields, from the facts alone.
    Text here = what every layout prints; separators (|) are not words, so they never matter."""
    blocks = [("name", facts["name"])]
    blocks += [("contact", facts[k]) for k in ("email", "phone", "location")]
    blocks += [("summary", HEADINGS["summary"]), ("summary", squash(facts["summary"]))]
    blocks.append(("experience", HEADINGS["experience"]))
    for j in facts["jobs"]:
        blocks.append(("experience", f"{j['title']} | {j['employer']} | {j['dates']}"))
        blocks += [("experience", b) for b in j["bullets"]]
    blocks.append(("education", HEADINGS["education"]))
    blocks += [("education", f"{e['degree']} | {e['school']} | {e['dates']}") for e in facts["education"]]
    blocks.append(("skills", HEADINGS["skills"]))
    blocks += [("skills", s) for s in facts["skills"]]
    return {
        "blocks": [{"section": s, "text": t} for s, t in blocks],
        "name": facts["name"], "email": facts["email"], "phone": facts["phone"],
        "jobs": [{k: j[k] for k in ("title", "employer", "dates")} for j in facts["jobs"]],
    }


def render(layout: str, facts: dict, study: Path = STUDY) -> bytes:
    pdf = typst.compile(str(study / "layouts" / f"{layout}.typ"), font_paths=[str(FONTS)], ignore_system_fonts=True,
                        sys_inputs={"data": json.dumps(facts, ensure_ascii=False)})
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        if doc.page_count != 1:
            raise SystemExit(f"{layout}: {doc.page_count} pages - every layout must fit one page")
    return pdf


def built(study: Path = STUDY) -> dict[str, bytes]:
    """Every file `build` writes, relative to the study folder -> its bytes."""
    facts = load_facts(study)
    out = {f"pdf/{name}.pdf": render(name, facts, study) for name in LAYOUTS}
    out["truth.json"] = (json.dumps(truth(facts), ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    return out


def build(study: Path = STUDY, check: bool = False) -> list[str]:
    """Write (or with check, list) the files that differ from a fresh build."""
    stale = []
    for rel, data in built(study).items():
        path = study / rel
        if path.is_file() and path.read_bytes() == data:
            continue
        stale.append(rel)
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    return stale


# --- score ---

def find_run(stream: list[str], key: list[str], taken: list[bool]) -> int:
    """First index where key sits as a run in stream on words no other block has claimed, else -1."""
    n = len(key)
    for i in range(len(stream) - n + 1):
        if stream[i:i + n] == key and not any(taken[i:i + n]):
            return i
    return -1


def locate(blocks: list[dict], stream: list[str]) -> list[int]:
    """Position of each block's opening words in the stream (-1 = not found). Longer keys claim first, so
    "Your Name" can't take the start of the email (your.name@...) when the name itself is missing."""
    keys = [words(b["text"])[:KEY_WORDS] for b in blocks]
    taken, pos = [False] * len(stream), [-1] * len(blocks)
    for i in sorted(range(len(blocks)), key=lambda i: (-len(keys[i]), i)):
        at = find_run(stream, keys[i], taken)
        if at >= 0:
            pos[i] = at
            taken[at:at + len(keys[i])] = [True] * len(keys[i])
    return pos


def in_order(seq: list[int]) -> int:
    """Length of the longest increasing run (not necessarily adjacent) - blocks that kept their order."""
    tails: list[int] = []
    for x in seq:
        lo, hi = 0, len(tails)
        while lo < hi:
            mid = (lo + hi) // 2
            if tails[mid] < x:
                lo = mid + 1
            else:
                hi = mid
        tails[lo:lo + 1] = [x]
    return len(tails)


def word_damage(want: list[str], got: list[str]) -> dict[str, int]:
    """Lost, extra, split and merged words (METHOD.md measures 1-3)."""
    missing = collections.Counter(want) - collections.Counter(got)
    extra = collections.Counter(got) - collections.Counter(want)
    split = merged = 0
    for w in sorted(missing):  # sorted: same counts every run
        for _ in range(missing[w]):
            for i in range(len(got)):
                piece, j = got[i], i
                while len(piece) < len(w) and j + 1 < len(got) and w.startswith(piece):
                    j += 1
                    piece += got[j]
                if j > i and piece == w and all(extra[got[k]] > 0 for k in range(i, j + 1)):
                    split += 1
                    missing[w] -= 1
                    for k in range(i, j + 1):
                        extra[got[k]] -= 1
                    break
    for o in sorted(extra):
        for _ in range(extra[o]):
            for i in range(len(want)):
                piece, j = want[i], i
                while len(piece) < len(o) and j + 1 < len(want) and o.startswith(piece):
                    j += 1
                    piece += want[j]
                if j > i and piece == o:
                    merged += 1
                    extra[o] -= 1
                    for k in range(i, j + 1):
                        if missing[want[k]] > 0:
                            missing[want[k]] -= 1
                    break
    return {"lost_words": sum(v for v in missing.values() if v > 0), "extra_words": sum(v for v in extra.values() if v > 0),
            "split_words": split, "merged_words": merged}


def score(t: dict, text: str) -> dict:
    """One reader's text of one layout against the truth -> the METHOD.md measures + broke / why."""
    blocks, stream = t["blocks"], words(text)
    want = [w for b in blocks for w in words(b["text"])]
    row = word_damage(want, stream)
    lines = [squash(line) for line in text.splitlines() if line.strip()]
    flat = squash(text)
    row["name_first_line"] = bool(lines) and lines[0] == t["name"]
    row["name_found"] = t["name"] in flat
    row["email"] = t["email"] in flat
    row["phone"] = t["phone"] in flat

    def has_run(line_words: list[str], part: str) -> bool:
        k = words(part)
        return any(line_words[i:i + len(k)] == k for i in range(len(line_words) - len(k) + 1))
    line_words = [words(line) for line in lines]
    row["job_headers_together"] = sum(any(all(has_run(lw, j[f]) for f in ("title", "employer", "dates")) for lw in line_words)
                                      for j in t["jobs"])

    pos = locate(blocks, stream)
    row["blocks_not_found"] = pos.count(-1)
    sections = list(dict.fromkeys(b["section"] for b in blocks))
    found = {s: [p for b, p in zip(blocks, pos) if b["section"] == s and p >= 0] for s in sections}
    kept = sum(in_order(found[s]) for s in sections)
    total = sum(len(found[s]) for s in sections)
    row["within_section_order"] = round(kept / total, 2) if total else 0.0
    row["sections_mixed"] = sum(any(min(found[s]) < p < max(found[s]) for o in sections if o != s for p in found[o])
                                for s in sections if found[s])
    row["page_order"] = round(in_order([p for p in pos if p >= 0]) / len(blocks), 2)

    why = []
    for k in ("lost_words", "split_words", "merged_words"):
        if row[k]:
            why.append(f"{k.replace('_', ' ')} {row[k]}")
    why += [f"{k.replace('_', ' ')} wrong" for k in ("name_first_line", "email", "phone") if not row[k]]
    if row["job_headers_together"] < len(t["jobs"]):
        why.append(f"job headers together {row['job_headers_together']}/{len(t['jobs'])}")
    if row["within_section_order"] < 1:
        why.append(f"within-section order {row['within_section_order']:.2f}")
    if row["sections_mixed"]:
        why.append(f"sections mixed {row['sections_mixed']}")
    if row["blocks_not_found"]:
        why.append(f"blocks not found {row['blocks_not_found']}")
    row["broke"] = bool(why)
    row["broke_because"] = "; ".join(why)
    return row


def results(t: dict, readings: dict, out) -> None:
    """readings = {"readers": {reader: {layout: text}}} (parser_read.py) -> one CSV row per layout x reader."""
    w = csv.DictWriter(out, COLUMNS, lineterminator="\n")
    w.writeheader()
    readers = sorted(readings["readers"])
    for layout in LAYOUTS:
        for reader in readers:
            row = score(t, readings["readers"][reader][layout])
            w.writerow({"layout": layout, "reader": reader, **{k: (str(v).lower() if isinstance(v, bool) else v)
                                                               for k, v in row.items()}})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--check", action="store_true")
    s = sub.add_parser("score")
    s.add_argument("readings")
    args = ap.parse_args(argv)
    if args.cmd == "build":
        stale = build(check=args.check)
        for rel in stale:
            print(f"{'stale' if args.check else 'wrote'}: {rel}")
        return 1 if args.check and stale else 0
    t = json.loads((STUDY / "truth.json").read_text(encoding="utf-8"))
    buf = io.StringIO()
    results(t, json.loads(Path(args.readings).read_text(encoding="utf-8")), buf)
    sys.stdout.write(buf.getvalue())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
