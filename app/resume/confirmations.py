"""How often a job's To-confirm list re-asks what an earlier job already asked - a count, not a feature.

Every tailored job lists its `inferences` under "To confirm" in `Check before sending.md`
(report.diff_md), and nothing records an answer. Reusing a confirmed answer on later jobs is an
open proposal (plan-40m.11) resting on the guess that the same inference comes back job after
job. bullets.md: measure before mechanising - so this walks the user's job folders and counts.

Two keys per inference, compared against every earlier job (job-number order):
- (a) wording: the claim lowercased, whitespace collapsed. Catches the AI reusing a sentence.
- (b) substance: sorted source ids + their master claim texts + the terms the claim names that
  none of those sources carries (`lint.entities`, compared as `lint.entity_key`). Catches the
  same stretch from the same facts worded differently - what a saved answer would cover.
  Master claim texts are part of the key: a fact reworded since makes its old answers stale.

Threshold, decided before the numbers came in: build reuse only if key (b) repeats in >= 20% of
inferences from job 2 on, across >= 8 tailored jobs. Short of either, close plan-40m.11 with a
bullets.md "Considered, not mechanised" row carrying the measured numbers.

The headline title stays asked on every job by decision (page-format.md), so only inferences count.
Prints counts only; claim text and terms are the user's resume and show only with --show.

    uv run python app/resume/confirmations.py measure "<My Jobs dir>" --master "<Resume details.yml>"
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

if __name__ == "__main__":  # run as a script: app/ on the path, not app/resume/ (its names would shadow)
    sys.path[0] = str(Path(__file__).resolve().parents[1])

from resume import lint, schema  # noqa: E402

JOB_DATA = ".data"
MIN_JOBS = 8
MIN_SHARE = 0.20
TOP_TERMS = 10
LEADING_NUMBER = re.compile(r"\s*(\d+)\b")


def job_number(folder: Path) -> int | None:
    m = LEADING_NUMBER.match(folder.name)
    return int(m.group(1)) if m else None


def job_folders(jobs_dir: Path) -> list[Path]:
    """`<stage>/<N - Company - Title>` folders holding a tailored answer, in job-number order."""
    found = [p.parent.parent for p in Path(jobs_dir).glob(f"*/*/{JOB_DATA}/tailored.json")]
    return sorted(found, key=lambda f: (job_number(f) is None, job_number(f) or 0, f.name))


def master_bullets(master: dict) -> dict[str, dict]:
    return {b["id"]: b for e in [*(master.get("roles") or []), *(master.get("projects") or [])]
            for b in e.get("bullets") or [] if isinstance(b, dict)}


def wording_key(claim: str) -> str:
    return " ".join(claim.lower().split())


def new_terms(claim: str, sources: list[dict]) -> dict[str, str]:
    """entity_key -> first spelling, for each term of the claim no source fact carries."""
    facts = lint.master_strings([{k: v for k, v in b.items() if k != "id"} for b in sources])
    known = {lint.entity_key(t) for t in lint.TOKEN.findall(" ".join(facts))}
    out: dict[str, str] = {}
    for term in lint.entities(claim):
        if (key := lint.entity_key(term)) not in known:
            out.setdefault(key, term)
    return out


def substance_key(inference: dict, bullets: dict[str, dict]) -> tuple:
    ids = sorted(set(inference.get("sources") or []))
    sources = [bullets[i] for i in ids if i in bullets]
    texts = tuple(bullets[i]["claim"] if i in bullets else "" for i in ids)
    return tuple(ids), texts, frozenset(new_terms(inference["claim"], sources))


def read_job(folder: Path) -> tuple[dict, dict]:
    data = folder / JOB_DATA
    tailored = json.loads((data / "tailored.json").read_text(encoding="utf-8"))
    jd_path = data / "jd.json"
    job = json.loads(jd_path.read_text(encoding="utf-8")) if jd_path.exists() else {}
    return tailored, job if isinstance(job, dict) else {}


def measure(jobs_dir: Path, master: dict) -> dict:
    bullets = master_bullets(master)
    seen_a: dict[str, int | str] = {}
    seen_b: dict[tuple, int | str] = {}
    per_job, repeats, terms, spelling = [], [], Counter(), {}
    total = later = 0
    for k, folder in enumerate(job_folders(jobs_dir), 1):
        tailored, job = read_job(folder)
        label = job_number(folder) or folder.name
        row = {"job": label, "inferences": 0, "repeat_a": 0, "repeat_b": 0}
        keys = []
        for inference in tailored.get("inferences") or []:
            if not isinstance(inference, dict) or not inference.get("claim"):
                continue
            a, b = wording_key(inference["claim"]), substance_key(inference, bullets)
            row["inferences"] += 1
            if a in seen_a:
                row["repeat_a"] += 1
            if b in seen_b:
                row["repeat_b"] += 1
                found = new_terms(inference["claim"], [bullets[i] for i in b[0] if i in bullets])
                terms.update(found.keys())
                for key, term in found.items():
                    spelling.setdefault(key, term)
            if a in seen_a or b in seen_b:
                repeats.append({"job": label, "claim": inference["claim"], "title": job.get("title"),
                                "same_wording_as": seen_a.get(a), "same_substance_as": seen_b.get(b)})
            keys.append((a, b))
        for a, b in keys:  # an earlier job only: a repeat inside one job is not a re-ask
            seen_a.setdefault(a, label)
            seen_b.setdefault(b, label)
        total += row["inferences"]
        later += row["inferences"] if k > 1 else 0
        per_job.append(row)

    repeat_b = sum(r["repeat_b"] for r in per_job)
    share = repeat_b / later if later else 0.0
    return {
        "jobs": len(per_job), "inferences": total, "later_inferences": later,
        "repeat_a": sum(r["repeat_a"] for r in per_job), "repeat_b": repeat_b, "share_b": share,
        "build_reuse": len(per_job) >= MIN_JOBS and share >= MIN_SHARE,
        "per_job": per_job, "repeats": repeats,
        "top_terms": [(spelling[key], n) for key, n in terms.most_common(TOP_TERMS)],
    }


def report(result: dict, show: bool = False) -> str:
    out = [f"{result['jobs']} tailored jobs, {result['inferences']} inferences "
           f"({result['later_inferences']} from job 2 on)"]
    out += [f"  job {r['job']}: {r['inferences']} inferences, {r['repeat_a']} same wording, "
            f"{r['repeat_b']} same sources + new terms" for r in result["per_job"]]
    out.append(f"repeats of an earlier job: {result['repeat_a']} by wording (a), "
               f"{result['repeat_b']} by sources + terms (b) = {result['share_b']:.0%} of inferences from job 2 on")
    if show:
        out.append("top repeated (b) terms: " + (", ".join(f"{t} x{n}" for t, n in result["top_terms"]) or "none"))
        for r in result["repeats"]:
            first = r["same_substance_as"] if r["same_substance_as"] is not None else r["same_wording_as"]
            title = f" ({r['title']})" if r["title"] else ""
            out.append(f"  job {r['job']}{title} repeats job {first}: {r['claim']}")
    else:
        out.append(f"top repeated (b) terms: {len(result['top_terms'])} distinct, counts "
                   f"{[n for _, n in result['top_terms']]} (--show names them)")
    verdict = "build reuse (plan-40m.11)" if result["build_reuse"] else \
        "close plan-40m.11 with a bullets.md 'Considered, not mechanised' row"
    out.append(f"threshold: (b) >= {MIN_SHARE:.0%} across >= {MIN_JOBS} jobs -> {verdict}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Count To-confirm items repeated across tailored job folders")
    steps = ap.add_subparsers(dest="step", required=True)
    p = steps.add_parser("measure", help="count repeats; prints numbers only unless --show")
    p.add_argument("jobs_dir", type=Path, help="the My Jobs folder")
    p.add_argument("--master", type=Path, required=True, help="Resume details.yml")
    p.add_argument("--show", action="store_true", help="also print the repeated claims and terms (the user's resume text)")
    args = ap.parse_args(argv)
    print(report(measure(args.jobs_dir, schema.load(args.master)), show=args.show))


if __name__ == "__main__":
    main()
