"""Fill a job application on any supported system in the user's own Chrome window - never Submit.

`prepare <job> <link>` (job = its number or slug) picks the system from the link, reads the form's
questions and writes `<job folder>/.data/application.json`: contact boxes answered from the resume,
the US work-permit questions from setup, every other question blank for the AI to fill with the user.
`fill <job>` opens the form in Job Finder's Chrome, types each answer, prints what took, and lets
go - the window stays open for the user to check and click Submit. A system it can't fill whose
questions were read ahead (apply/readahead.py): `prepare` drafts from those, `paste <job>` writes
the answers as a page to paste from.
Systems + how to add one: app/docs/apply/apply-systems.md.
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

import cfg
from apply import answers as saved_answers
from apply import browser, questions, readahead, systems
from resume import render, schema, tailor

# a system the program can't fill: answers drafted from the read-ahead, pasted by the user
PASTE = "paste"
ANSWERS_FILE = "Application answers.md"
# how long a form gets to save typed answers before they are read back
SETTLE_MS = 2500
# what a closed posting says where its form would be
CLOSED = re.compile(r"no longer (?:accepting applications|available|open)|(?:position|job|role) (?:has been|is) "
                    r"(?:filled|closed)|(?:this )?job (?:post(?:ing)? )?(?:is )?closed|isn't accepting applications|"
                    r"not accepting applications|posting (?:has )?expired", re.I)


def job_dir(config: dict, slug: str) -> Path:
    found = tailor.find_job_dir(cfg.resume_path(config, "jobs_dir"), tailor.by_number(config, slug))
    if found is None:
        sys.exit(f"no job folder for {slug}; run tailor first")
    return found


def resume_for(config: dict, folder: Path) -> str | None:
    """The job's tailored PDF where its folder is now - never a path saved earlier: the folder
    moves when its status does (sent, heard back ...). The file is named from the name on the page,
    which can change after tailoring (initials, a name they go by) -> then the one *_Resume.pdf
    there; none or several -> None, fill says why."""
    resume = folder / render.file_name(schema.load(cfg.resume_path(config, "master")))
    if resume.exists():
        return str(resume)
    found = sorted(folder.glob("*_Resume.pdf"))
    return str(found[0]) if len(found) == 1 else None


def system_for(url: str):
    system = systems.for_url(url)
    if system is None:
        other = systems.elsewhere(url)
        sys.exit(other or "this application system is not supported yet - give the user the tailored PDF "
                          "and answers to paste; to add it see app/docs/apply/apply-systems.md")
    return system


def line(a: dict) -> str:
    """One question as prepare prints it; a sensitive one names its kind so the AI asks, never fills -
    or, a work break answered from the user's saved words, shows them those words before Submit."""
    state = "ok" if not questions.blank(a["answer"]) else ("NEEDED" if a["required"] else "optional")
    opts = f" options={a['options']}" if a["options"] else ""
    tag = f" ({a['source'].split(' - ', 1)[1]})" if " - sensitive: " in a["source"] or \
        f" - {questions.SIGN_ON_PAGE}: " in a["source"] else ""
    return f"  [{state}] {a['kind']}: {a['title']}{opts}{tag}"


def prepare(slug: str, url: str) -> None:
    config = cfg.load()
    master = schema.load(cfg.resume_path(config, "master"))
    folder = job_dir(config, slug)
    system = systems.for_url(url)
    form = None if system else readahead.load(folder / tailor.JOB_DATA)
    if system is None and not (form and form.get("found")):
        system_for(url)  # says why: filled another way, or not supported
    out = folder / tailor.JOB_DATA / questions.FILE
    old = questions.load(out)
    name, app_url = (system.NAME, system.application_url(url)) if system else (PASTE, url)
    asked = system.questions(url) if system else readahead.as_questions(form)
    same_form = old and old.get("url") == app_url
    keeping = config.get("saved_answers")
    answers = questions.draft(asked, master["contact"], old["questions"] if same_form else None, config,
                              master.get("career_break"), saved_answers.load() if keeping else [])
    questions.save(out, {"system": name, "url": app_url, "questions": answers})
    where = f"{name} form" if system else f"{(form.get('provider') or 'this').title()} form, read ahead (no options captured)"
    print(f"{where} -> {out}: {len(answers)} questions, {len(questions.missing(answers))} required still blank")
    for a in answers:
        print(line(a))
    selfid = config.get("self_identification") or {}
    if questions.asks_voluntary(answers) and selfid and selfid.get("fill_on_forms") is None:
        print("ask once: fill the user's saved voluntary answers (gender, race, veteran) on forms, named before "
              "Submit? Yes -> self_identification.fill_on_forms: true in search settings, then prepare again; "
              "No -> false (asked on each form as now)")
    if keeping is None:
        print("ask once: keep the user's own answers for the next form (named before Submit, on this computer)? "
              "Yes -> saved_answers: true in search settings, No -> false")
    print("Write answers into the file (file kind: answer = true only after the user said yes to uploading; a "
          f"question marked '{questions.YOURS}' or 'sensitive': the user's own answer, its source set to "
          f"'{questions.USER_SAID}'; one marked '{questions.SIGN_ON_PAGE}': left blank, the user ticks or signs it "
          "there), then: uv run app/jobs.py apply-form {'fill' if system else 'paste'} {slug}")


def paste(slug: str) -> None:
    """A system the program can't fill: the answers as a page the user pastes from, in order."""
    config = cfg.load()
    folder = job_dir(config, slug)
    data = questions.load(folder / tailor.JOB_DATA / questions.FILE)
    if data is None:
        sys.exit(f"no answers yet; run: uv run app/jobs.py apply-form prepare {slug} <link>")
    refuse(data["questions"])
    out = ["# Application answers", "",
           "Paste each into the form, in this order. Options weren't read ahead - for a choice, pick the one "
           "that means your answer (the page may word it longer, e.g. \"No, I do not require sponsorship...\").",
           "Check every answer on the page before you click Submit.", ""]
    resume = resume_for(config, folder)
    upload = f"(upload {Path(resume).name} from this job's folder)" if resume else "(upload your resume PDF here)"
    for a in data["questions"]:
        answer = a.get("answer")
        shown = upload if a["kind"] == "file" and answer is True else (
            "(yours to answer on the page)" if questions.blank(answer) else ", ".join(answer) if isinstance(answer, list) else str(answer))
        out += [f"**{a['title']}**{' (required)' if a['required'] else ''}", "", shown, ""]
    path = folder / ANSWERS_FILE
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"written: {path}")
    remember(config, folder, data)


def refuse(qs: list[dict]) -> None:
    """Answers nothing may type: the AI's on the user's own questions, any on agreeing or signing."""
    if bad := questions.on_page(qs):
        sys.exit("the user ticks or signs these on the page themselves - clear the answer: "
                 + "; ".join(a["title"] for a in bad))
    if bad := questions.unvouched(qs):
        sys.exit("only the user answers these - ask them, set source 'you said': " + "; ".join(a["title"] for a in bad))


def page_text(page) -> str:
    try:
        return page.locator("body").inner_text(timeout=10000)
    except Exception:  # unreadable page: the form wait below says what's wrong
        return ""


def fill(slug: str) -> None:
    config = cfg.load()
    folder = job_dir(config, slug)
    saved = folder / tailor.JOB_DATA / questions.FILE
    data = questions.load(saved)
    if data is None:
        sys.exit(f"no answers yet; run: uv run app/jobs.py apply-form prepare {slug} <link>")
    if data.get("system") == PASTE:
        sys.exit(f"this form can't be filled here - write the answers to paste: uv run app/jobs.py apply-form paste {slug}")
    refuse(data["questions"])
    if gaps := questions.missing(data["questions"]):
        sys.exit("required questions still blank: " + "; ".join(a["title"] for a in gaps))
    system = system_for(data["url"])
    resume = resume_for(config, folder)
    letter = next((str(p) for p in folder.glob("*_Cover_Letter.pdf")), None)
    if resume is None and any(q["kind"] == "file" and q.get("answer") is True for q in data["questions"]):
        pdfs = [p.name for p in folder.glob("*_Resume.pdf")]
        print(f"no resume uploaded: {'several resume PDFs in ' + folder.name + ' - ' + ', '.join(pdfs) if pdfs else 'no tailored resume PDF in ' + folder.name} "
              "- the user uploads one by hand, or make the resume again")
    report = []
    with browser.page_at(data["url"]) as page:
        # a closed posting never shows its form: say so instead of timing out on it
        if said := CLOSED.search(page_text(page)):
            sys.exit(f"the posting says it's closed (\"{said.group()}\") - nothing filled; ask the user, "
                     "then status set <job> closed")
        if hasattr(system, "recover"):  # optional: the link landed somewhere without the form
            system.recover(page, data["url"])
        page.locator(system.READY).first.wait_for(timeout=30000)
        # resume first: an upload must never re-trigger anything over typed answers
        for q in sorted(data["questions"], key=lambda q: q["kind"] != "file"):
            if questions.blank(q.get("answer")):
                continue
            try:
                result = system.fill(page, q, letter if q.get("key") == "cover_letter" else resume)
            except Exception as e:  # one stuck box never stops the rest
                result = f"FAIL {type(e).__name__}: {str(e).splitlines()[0][:120]}"
            report.append((q["id"], result))
        report = recheck(page, system, data["questions"], report, resume)
        known = {q["id"] for q in data["questions"]}
        extra = [i for i in system.ids_on_page(page) if i not in known]
    # by id: one title can name two questions ("Phone" on two pages)
    title = {q["id"]: q["title"] for q in data["questions"]}
    for id, result in report:
        print(f"  [{result}] {title[id]}")
    required = [q for q in data["questions"] if q["required"]]
    done = {id for id, result in report if result == "ok"}
    left = [q["title"] for q in required if q["id"] not in done]
    if required:
        print(f"required answered {len(required) - len(left)} of {len(required)}"
              + (f" - still to do on the page: {'; '.join(left)}" if left else ""))
    if extra:
        print(f"  {len(extra)} question(s) on the page not in the answers file - user answers them on screen")
    remember(config, folder, data)
    print("Chrome is open on the filled form. Nothing is sent until the user clicks Submit.")


def recheck(page, system, qs: list[dict], report: list[tuple], resume: str | None) -> list[tuple]:
    """Answers that showed then dropped before Submit (a user saw two flagged empty on Ashby,
    2026-10): once the form has had time to save, read each back; one gone is filled again once,
    still gone -> FAIL so the user fills it by hand. Systems without `holds` are left as filled."""
    if not hasattr(system, "holds"):
        return report
    page.wait_for_timeout(SETTLE_MS)
    by_id = {q["id"]: q for q in qs}
    out = []
    for id, result in report:
        q = by_id[id]
        if result == "ok" and q["kind"] != "file" and not system.holds(page, q):
            result = system.fill(page, q, resume)
            page.wait_for_timeout(SETTLE_MS)
            if result == "ok" and not system.holds(page, q):
                result = "FAIL answer dropped after filling - fill it by hand"
        out.append((id, result))
    return out


def remember(config: dict, folder: Path, data: dict) -> None:
    """The user's own answers on this form, kept for the next one - only after they said yes."""
    if config.get("saved_answers"):
        n = saved_answers.keep(data["questions"], "Job " + folder.name.split(" - ")[0], "", date.today().isoformat())
        if n:
            print(f"kept {n} of the user's answers for next time (My Settings/Saved answers.yml)")


def main() -> None:
    ap = argparse.ArgumentParser(description="fill a job application in Chrome, stopping before Submit")
    sub = ap.add_subparsers(dest="step", required=True)
    p = sub.add_parser("prepare", help="read the form's questions, answer what the resume states")
    p.add_argument("slug")
    p.add_argument("url")
    f = sub.add_parser("fill", help="open Chrome and fill the form from the answers file")
    f.add_argument("slug")
    t = sub.add_parser("paste", help="a form that can't be filled here: answers to paste -> Application answers.md")
    t.add_argument("slug")
    args = ap.parse_args()
    {"prepare": lambda: prepare(args.slug, args.url), "fill": lambda: fill(args.slug),
     "paste": lambda: paste(args.slug)}[args.step]()


if __name__ == "__main__":
    main()
