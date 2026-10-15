"""Offline eval of the tailoring AI: fixed resumes + postings, any AI chat writes the answers,
`tailor check` grades them. Dev tool like demo.py - pytest never collects it (no test_ prefix).

    uv run python app/tests/tailor_eval.py prepare <out_dir>          # one task file per case
    uv run python app/tests/tailor_eval.py check <out_dir> <case>     # the AI runs this, as a user's AI runs tailor check
    uv run python app/tests/tailor_eval.py grade <out_dir>            # case | passed | runs | gates failed | traps

Each case (fixtures/tailor-eval/<case>/): case.yml (which tracked resume details), posting.txt,
extract.json (the posting step's answer, so prepare runs offline), traps.yml (regexes over the
answer's page text - eval only, never a runtime gate), golden.json (an answer that passes).
<out_dir>/<case>/ is a mini Job Finder folder: real job folder, task file, fail count + STOP.
Method + results: app/docs/resume/tailor-evals.md.
"""
import argparse
import contextlib
import json
import re
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cfg  # noqa: E402
from resume import handoff, tailor  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
CASES = Path(__file__).resolve().parent / "fixtures" / "tailor-eval"
RUNS = "eval-runs.json"
SCHEMA_GATE = "answer schema"
COLUMNS = ("case", "passed", "runs", "gates failed", "traps")


def cases() -> list[str]:
    return sorted(p.name for p in CASES.iterdir() if (p / "case.yml").is_file())


def case_spec(case: str) -> dict:
    spec = yaml.safe_load((CASES / case / "case.yml").read_text(encoding="utf-8"))
    return {**spec, "master": REPO / spec["master"]}


def refuse_reason(out_dir: Path) -> str | None:
    """Inside the checkout the mini folders would sit beside real code and could be committed."""
    if out_dir.resolve().is_relative_to(REPO):
        return f"{out_dir} is inside the checkout {REPO} - pick a folder outside it (a temp folder)"
    return None


@contextlib.contextmanager
def rooted(root: Path):
    """Point Job Finder's folders at one case's mini root, as the tests do; put them back after."""
    saved = cfg.ROOT, cfg.DATA
    cfg.ROOT, cfg.DATA = root, root / ".data"
    try:
        yield cfg.defaults()
    finally:
        cfg.ROOT, cfg.DATA = saved


def check_line(out_dir: Path, case: str) -> str:
    return f'uv run python app/tests/tailor_eval.py check "{out_dir.resolve()}" {case}'


def job_dir(root: Path) -> Path | None:
    found = tailor.job_dirs(root / "My Jobs")
    return found[0] if found else None


def answer_path(out_dir: Path, case: str) -> Path | None:
    found = job_dir(out_dir / case)
    return found / tailor.JOB_DATA / "tailored.json" if found else None


def prepare(out_dir: Path, only: list[str] | None = None) -> list[Path]:
    """Fresh mini root per case, tailor prepare on its posting; task's check line points here."""
    if why := refuse_reason(out_dir):
        raise SystemExit(f"tailor_eval: {why}")
    tasks = []
    for case in only or cases():
        spec, src, root = case_spec(case), CASES / case, out_dir / case
        shutil.rmtree(root, ignore_errors=True)
        with rooted(root) as config:
            master = cfg.resume_path(config, "master")
            master.parent.mkdir(parents=True)
            shutil.copyfile(spec["master"], master)
            posting = cfg.DATA / "posting.txt"
            posting.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src / "posting.txt", posting)
            shutil.copyfile(src / "extract.json", tailor.posting_files(posting)[1])
            tailor.prepare(config, None, posting, spec.get("url", ""))
        found = job_dir(root)
        slug = json.loads((found / tailor.JOB_DATA / "jd.json").read_text(encoding="utf-8"))["public_slug"]
        task = found / tailor.JOB_DATA / "task.md"
        text = task.read_text(encoding="utf-8")
        if tailor.check_command(slug) not in text:
            raise SystemExit(f"tailor_eval: {task} has no '{tailor.check_command(slug)}' line to point at the eval")
        task.write_text(text.replace(tailor.check_command(slug), check_line(out_dir, case)), encoding="utf-8")
        tasks.append(task)
        print(f"{case}: task {task}\n  then run: {check_line(out_dir, case)}")
    return tasks


def gate_name(line: str) -> str:
    """Rule a failed line names: "gate pages: ..." -> pages, "lint X at ..." -> lint X, "entries[acme] ..." -> entries."""
    if m := re.match(r"(gate|lint) ([\w-]+)", line):
        return m[2] if m[1] == "gate" else f"lint {m[2]}"
    m = re.match(r"\w+", line)
    return m[0] if m else line


def runs(root: Path) -> list[dict]:
    try:
        return json.loads((root / RUNS).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def check(out_dir: Path, case: str) -> int:
    """tailor check under the case's mini root - its own fail count + STOP - and log the run."""
    root = out_dir / case
    if job_dir(root) is None:
        raise SystemExit(f"tailor_eval: no task for {case} under {out_dir} - run prepare first")
    seen: list[dict] = []
    real = tailor.evaluate

    def recorded(*args, **kw):
        result = real(*args, **kw)
        seen.append(result)
        return result

    tailor.evaluate = recorded
    try:
        with rooted(root) as config:
            code = tailor.check(config, tailor.read_jd(job_dir(root))["public_slug"])
        failed = [gate_name(line) for line in seen[-1]["failed"]] if seen else []
        looks = sorted({kind for kind, _ in seen[-1]["second_looks"]}) if seen else []
    except SystemExit as e:  # answer missing, not JSON, or off the schema: a failed run all the same
        print(e)
        code, failed, looks = 1, [SCHEMA_GATE], []
    finally:
        tailor.evaluate = real
    log = runs(root) + [{"passed": code == 0, "failed": sorted(set(failed)), "second looks": looks}]
    (root / RUNS).write_text(json.dumps(log, indent=1), encoding="utf-8")
    return code


def page_text(answer: dict) -> str:
    """Words of the answer that reach the page - coverage notes + inferences never print."""
    parts = [answer.get("summary"), answer.get("headline_title")]
    for entry in answer.get("entries") or []:
        parts += [entry.get("title_mirror"), *(b.get("text") for b in entry.get("bullets") or [])]
    parts += [i for g in answer.get("skills") or [] for i in [g.get("group"), *g.get("items", [])]]
    return "\n".join(p for p in parts if isinstance(p, str))


def trap_hits(case: str, answer: dict) -> list[str]:
    traps = yaml.safe_load((CASES / case / "traps.yml").read_text(encoding="utf-8")) or []
    text = page_text(answer)
    return [t["id"] for t in traps if re.search(t["pattern"], text)]


def grade_case(out_dir: Path, case: str) -> dict:
    root = out_dir / case
    log = runs(root)
    answer = answer_path(out_dir, case)
    try:
        hits = trap_hits(case, json.loads(answer.read_text(encoding="utf-8"))) if answer else []
    except (OSError, ValueError):
        hits = []
    last = log[-1] if log else {"passed": False, "failed": []}
    return {"case": case, "passed": last["passed"], "runs": len(log), "gates failed": last["failed"], "traps": hits,
            "second looks": last.get("second looks", []),
            "stopped": handoff.read_fails(answer)["fails"] >= handoff.STOP_AFTER if answer else False}


def grade(out_dir: Path) -> list[dict]:
    rows = [grade_case(out_dir, c) for c in cases() if (out_dir / c).is_dir()]
    print(" | ".join(COLUMNS))
    print(" | ".join("---" for _ in COLUMNS))
    for r in rows:
        print(" | ".join([r["case"], ("yes" if r["passed"] else "no") + (" (STOP)" if r["stopped"] else ""),
                          str(r["runs"]), ", ".join(r["gates failed"]) or "-", ", ".join(r["traps"]) or "-"]))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="Offline eval of the tailoring AI (app/docs/resume/tailor-evals.md)")
    steps = ap.add_subparsers(dest="step", required=True)
    p = steps.add_parser("prepare", help="mini folder + tailoring task per case")
    p.add_argument("out_dir", type=Path)
    p.add_argument("cases", nargs="*", help=f"default: all ({', '.join(cases())})")
    p = steps.add_parser("check", help="check one case's answer; the AI runs this")
    p.add_argument("out_dir", type=Path)
    p.add_argument("case", choices=cases())
    p = steps.add_parser("grade", help="results table")
    p.add_argument("out_dir", type=Path)
    args = ap.parse_args()
    if args.step == "prepare":
        prepare(args.out_dir, args.cases or None)
    elif args.step == "check":
        sys.exit(check(args.out_dir, args.case))
    else:
        grade(args.out_dir)


if __name__ == "__main__":
    main()
