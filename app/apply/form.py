"""Fill a job application on any supported system in the user's own Chrome window - never Submit.

`prepare <job> <link>` (job = its number or slug) picks the system from the link, reads the form's
questions and writes `<job folder>/.data/application.json`: contact boxes answered from the resume,
the US work-permit questions from setup, every other question blank for the AI to fill with the user.
`fill <job>` opens the form in Job Finder's Chrome, types each answer, prints what took, and lets
go - the window stays open for the user to check and click Submit. A system it can't fill whose
questions were read ahead (apply/readahead.py): `prepare` drafts from those, `paste <job>` writes
the answers as a page to paste from.
A form spread over pages: `fill` works on the user's own tab, fills what this page shows (the rest
reported LATER), the user clicks Next / Continue, then `prepare` again (systems that read the page)
and `fill` again.
`measure <link>` (developers): a safe look at a live form - apply/lab.py; `try <link> [--next] [--no-upload]`: a
system's filler on it with synthetic answers - apply/trial.py.
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
from text import inert_md

# a system the program can't fill: answers drafted from the read-ahead, pasted by the user
PASTE = "paste"
ANSWERS_FILE = "Application answers.md"
# how long a form gets to save typed answers before they are read back
SETTLE_MS = 2500
# what a closed posting says where its form would be
CLOSED = re.compile(r"no longer (?:accepting applications|available|open)|(?:position|job|role) (?:has been|is) "
                    r"(?:filled|closed)|(?:this )?job (?:post(?:ing)? )?(?:is )?closed|isn't accepting applications|"
                    r"not accepting applications|posting (?:has )?expired|"
                    # Lever, 404 at the form link (2026-10-03)
                    r"posting you['’]re looking for might have closed|"
                    # Paylocity (2026-10-03)
                    r"does not exist or is not currently active", re.I)


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


def upload_note(system, answers: list[dict]) -> str:
    """A system that sends a file the moment it is chosen: the yes for the named file says so."""
    if getattr(system, "FILE_ON_CHOICE", False) and any(a["kind"] == "file" for a in answers):
        return (f"{system.NAME}: a file goes to the employer's site as soon as it is chosen, before Submit - "
                "say so in the question asking the user's yes to the named file")
    return ""


def ai_note(answers: list[dict]) -> str:
    """A form asking the applicant to say whether AI helped: the AI names it and how the resume was made."""
    if any(questions.never_draft(a["title"]) == questions.AI_USE for a in answers):
        return (f"name it to the user: the form asks them to say whether AI helped ({questions.AI_USE}) - their "
                "resume was tailored with AI help in this chat; only they answer it, on the page, never drafted or ticked")
    return ""


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
    same_form = old and old.get("url") == app_url
    before = old["questions"] if same_form else []
    reads = hasattr(system, "read")
    if reads:  # a form read page by page, off the tab the user is on
        with browser.page_at(app_url, match=systems.tab_match(system, url)) as page:
            asked = system.read(page)
    else:
        asked = system.questions(url) if system else readahead.as_questions(form)
    keeping = config.get("saved_answers")
    answers = questions.draft(asked, master["contact"], before, config,
                              master.get("career_break"), saved_answers.load() if keeping else [])
    if reads:
        answers = questions.merge(before, answers)
    questions.save(out, {"system": name, "url": app_url, "questions": answers})
    where = f"{name} form" if system else f"{(form.get('provider') or 'this').title()} form, read ahead (no options captured)"
    print(f"{where} -> {out}: {len(answers)} questions, {len(questions.missing(answers))} required still blank")
    for a in answers:
        print(line(a))
    if note := upload_note(system, answers):
        print(note)
    if note := ai_note(answers):
        print(note)
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
          f"there), then: uv run app/jobs.py apply-form {'fill' if system else 'paste'} {slug}")


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
        # question = the employer's words, inert; answer = the user's, pasted as is
        out += [f"**{inert_md(a['title'])}**{' (required)' if a['required'] else ''}", "", shown, ""]
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
    system = system_for(data["url"])
    per_page = getattr(system, "PER_PAGE", False)
    if not per_page and (gaps := questions.missing(data["questions"])):
        sys.exit("required questions still blank: " + "; ".join(a["title"] for a in gaps))
    resume = resume_for(config, folder)
    letter = next((str(p) for p in folder.glob("*_Cover_Letter.pdf")), None)
    if resume is None and any(q["kind"] == "file" and q.get("answer") is True for q in data["questions"]):
        pdfs = [p.name for p in folder.glob("*_Resume.pdf")]
        print(f"no resume uploaded: {'several resume PDFs in ' + folder.name + ' - ' + ', '.join(pdfs) if pdfs else 'no tailored resume PDF in ' + folder.name} "
              "- the user uploads one by hand, or make the resume again")
    # a multi-page form: the user's own tab, where they are - a fresh tab is page 1 again
    match = systems.tab_match(system, data["url"]) if per_page else None
    with browser.page_at(data["url"], match=match) as page:
        # a closed posting never shows its form: say so instead of timing out on it
        if said := closed(page):
            sys.exit(f"the posting says it's closed (\"{said}\") - nothing filled; ask the user, "
                     "then status set <job> closed")
        open_form(page, system, data["url"])
        shown = set(system.ids_on_page(page)) if per_page else set()
        if per_page:  # blank on this page blocks it; blank on another page waits for that page
            gaps = [a for a in questions.missing(data["questions"]) if a["id"] in shown]
            if gaps:
                sys.exit("required questions on this page still blank: " + "; ".join(a["title"] for a in gaps))
        report, extra = fill_page(page, system, data["questions"], resume, letter)
    lines, other = page_report(data["questions"], report, shown, per_page)
    print("\n".join(lines))
    if other:
        blank = [q["title"] for q in questions.missing(other)]
        print(f"{len(other)} question(s) on other pages - the user checks this page and clicks Next / Continue "
              "themselves (never us), then: " + (f"uv run app/jobs.py apply-form prepare {slug} \"{data['url']}\", then " if hasattr(system, "read") else "")
              + f"uv run app/jobs.py apply-form fill {slug}"
              + (f"; still blank there: {'; '.join(blank)}" if blank else ""))
    if extra:
        print(f"  {len(extra)} question(s) on the page not in the answers file - user answers them on screen")
    remember(config, folder, data)
    print("Chrome is open on the filled form. Nothing is sent until the user clicks Submit.")


def closed(page) -> str | None:
    """What a closed posting says where its form would be, else None."""
    said = CLOSED.search(page_text(page))
    return said.group() if said else None


def open_form(page, system, url: str) -> None:
    if hasattr(system, "recover"):  # optional: the link landed somewhere without the form
        system.recover(page, url)
    page.locator(system.READY).first.wait_for(timeout=30000)


def fill_page(page, system, qs: list[dict], resume: str | None, letter: str | None, before=None) -> tuple[list, list]:
    """Every answered question typed into the page as it stands -> (report [(id, result)], ids on
    the page the file lacks). One path for fill and try (lab): what try proves is what fill does.
    `before(q)`: called as each box is filled (try names the box a blocked request came from)."""
    report = []
    # resume first: an upload must never re-trigger anything over typed answers
    for q in sorted(qs, key=lambda q: q["kind"] != "file"):
        if questions.blank(q.get("answer")):
            continue
        if before:
            before(q)
        try:
            result = system.fill(page, q, letter if q.get("key") == "cover_letter" else resume)
        except Exception as e:  # one stuck box never stops the rest
            result = f"FAIL {type(e).__name__}: {str(e).splitlines()[0][:120]}"
        report.append((q["id"], result))
    if before:
        before(None)
    report = recheck(page, system, qs, report, resume)
    known = {q["id"] for q in qs}
    return report, [i for i in system.ids_on_page(page) if i not in known]


def page_report(qs: list[dict], report: list[tuple], shown: set, per_page: bool) -> tuple[list[str], list[dict]]:
    """Lines fill prints for the page: one per box filled (LATER ones left out), required count ->
    (lines, questions on other pages - per-page systems only)."""
    later = {id for id, result in report if result.startswith(questions.LATER)}
    # by id: one title can name two questions ("Phone" on two pages)
    title = {q["id"]: q["title"] for q in qs}
    lines = [f"  [{result}] {title[id]}" for id, result in report if id not in later]
    done = {id for id, result in report if result == "ok"}
    here = ({id for id, _ in report if id not in later} | shown) if per_page else {q["id"] for q in qs}
    required = [q for q in qs if q["required"] and q["id"] in here]
    left = [q["title"] for q in required if q["id"] not in done]
    count, todo = f"{len(required) - len(left)} of {len(required)}", f" - still to do on the page: {'; '.join(left)}" if left else ""
    if per_page:
        lines.append(f"this page: {count} required answered{todo}")
    elif required:
        lines.append(f"required answered {count}{todo}")
    return lines, [q for q in qs if q["id"] not in here] if per_page else []


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
    m = sub.add_parser("measure", help="(developers) safe look at a live form: throwaway Chrome, every write "
                       "blocked, canary first -> .data/measure/")
    m.add_argument("url")
    m.add_argument("--click", action="append", default=[], help="exact visible text to click first (Apply ...)")
    tr = sub.add_parser("try", help="(developers) a system's filler on a live form: synthetic answers, same block + "
                       "canary as measure, never Submit")
    tr.add_argument("url")
    tr.add_argument("--next", action="store_true", help="then press the one Next / Continue button (block on)")
    tr.add_argument("--no-upload", action="store_true", help="leave file boxes: a page whose upload is blocked "
                    "can break the rest of the form (Workable)")
    args = ap.parse_args()
    if args.step == "measure":
        from apply import lab
        return lab.measure(args.url, args.click)
    if args.step == "try":
        from apply import trial
        return trial.trial(args.url, args.next, upload=not args.no_upload)
    {"prepare": lambda: prepare(args.slug, args.url), "fill": lambda: fill(args.slug),
     "paste": lambda: paste(args.slug)}[args.step]()


if __name__ == "__main__":
    main()
