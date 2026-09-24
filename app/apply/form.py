"""Fill a job application on any supported system in the user's own Chrome window - never Submit.

`prepare <slug> <link>` picks the system from the link, reads the form's questions and writes
`<job folder>/.data/application.json`: contact boxes answered from the resume, the US work-permit
questions from setup, every other question blank for the AI to fill with the user.
`fill <slug>` opens the form in Job Finder's Chrome, types each answer, prints what took, and lets
go - the window stays open for the user to check and click Submit.
Systems + how to add one: app/docs/apply-systems.md.
"""
import argparse
import sys
from pathlib import Path

import cfg
from apply import browser, questions, systems
from resume import render, schema, tailor


def job_dir(config: dict, slug: str) -> Path:
    found = tailor.find_job_dir(cfg.resume_path(config, "jobs_dir"), slug)
    if found is None:
        sys.exit(f"no job folder for {slug}; run tailor first")
    return found


def system_for(url: str):
    system = systems.for_url(url)
    if system is None:
        other = systems.elsewhere(url)
        sys.exit(other or "this application system is not supported yet - give the user the tailored PDF "
                          "and answers to paste; to add it see app/docs/apply-systems.md")
    return system


def prepare(slug: str, url: str) -> None:
    config = cfg.load()
    master = schema.load(cfg.resume_path(config, "master"))
    system = system_for(url)
    folder = job_dir(config, slug)
    out = folder / tailor.JOB_DATA / questions.FILE
    old = questions.load(out)
    same_form = old and old.get("url") == system.application_url(url)
    answers = questions.draft(system.questions(url), master["contact"], old["questions"] if same_form else None, config)
    resume = folder / render.file_name(master)
    questions.save(out, {"system": system.NAME, "url": system.application_url(url),
                         "resume_file": str(resume) if resume.exists() else None, "questions": answers})
    print(f"{system.NAME} form -> {out}: {len(answers)} questions, {len(questions.missing(answers))} required still blank")
    for a in answers:
        state = "ok" if not questions.blank(a["answer"]) else ("NEEDED" if a["required"] else "optional")
        opts = f" options={a['options']}" if a["options"] else ""
        print(f"  [{state}] {a['kind']}: {a['title']}{opts}")
    print("Write answers into the file (file kind: answer = true only after the user said yes to uploading), "
          f"then: uv run app/jobs.py apply-form fill {slug}")


def fill(slug: str) -> None:
    config = cfg.load()
    saved = job_dir(config, slug) / tailor.JOB_DATA / questions.FILE
    data = questions.load(saved)
    if data is None:
        sys.exit(f"no answers yet; run: uv run app/jobs.py apply-form prepare {slug} <link>")
    if gaps := questions.missing(data["questions"]):
        sys.exit("required questions still blank: " + "; ".join(a["title"] for a in gaps))
    system = system_for(data["url"])
    report = []
    with browser.page_at(data["url"]) as page:
        page.locator(system.READY).first.wait_for(timeout=30000)
        # resume first: an upload must never re-trigger anything over typed answers
        for q in sorted(data["questions"], key=lambda q: q["kind"] != "file"):
            if questions.blank(q.get("answer")):
                continue
            try:
                result = system.fill(page, q, data.get("resume_file"))
            except Exception as e:  # one stuck box never stops the rest
                result = f"FAIL {type(e).__name__}: {str(e).splitlines()[0][:120]}"
            report.append((q["title"], result))
        known = {q["id"] for q in data["questions"]}
        extra = [i for i in system.ids_on_page(page) if i not in known]
    for title, result in report:
        print(f"  [{result}] {title}")
    if extra:
        print(f"  {len(extra)} question(s) on the page not in the answers file - user answers them on screen")
    print("Chrome is open on the filled form. Nothing is sent until the user clicks Submit.")


def main() -> None:
    ap = argparse.ArgumentParser(description="fill a job application in Chrome, stopping before Submit")
    sub = ap.add_subparsers(dest="step", required=True)
    p = sub.add_parser("prepare", help="read the form's questions, answer what the resume states")
    p.add_argument("slug")
    p.add_argument("url")
    f = sub.add_parser("fill", help="open Chrome and fill the form from the answers file")
    f.add_argument("slug")
    args = ap.parse_args()
    prepare(args.slug, args.url) if args.step == "prepare" else fill(args.slug)


if __name__ == "__main__":
    main()
