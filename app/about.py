"""What Job Finder knows about the user, in one place, and their notes beyond the resume.

`My Settings/About me.yml` - notes in the user's own words, each saved only after they said yes to
saving it (`app/docs/about-me.md`). Kinds below say what each is used for; the AI reads one kind at
a time (`about read KIND`), only for what that kind is used for - never the whole file into chat.
`values` + `personal` are sensitive: read only when the user asks whether a job or company fits.

`about show` writes `.data/What Job Finder knows about you.md` - every store in plain words (search,
pay, work permit, address, saved answers, resume, notes), each w/ what it's used for, who sees it
and how to change it - and prints its path only: the page is for the user's eyes, its contents
never pass through the chat. Rebuilt on each `about` command, so it never shows a forgotten note.
"""
import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

import cfg
import locks
import rank

FILE = cfg.ROOT / "My Settings" / "About me.yml"
HEADER = ("# Notes about you beyond your resume - your own words, each saved after you said yes.\n"
          "# Private: only this computer. Tell the chat to change or forget one.\n")
# kind -> (plain name, what it's used for). Order = order on the page.
KINDS = {
    "goals": ("What you want next",
              "choosing which of your true lines lead a tailored resume; interview practice. Never written into a letter"),
    "workplace": ("Workplaces you like or avoid",
                  "when you ask whether a job fits; companies you name can be hidden from your list (counted first)"),
    "voice": ("How you like to sound",
              "wording of a cover letter or follow-up email you ask for - never a reason or a fact"),
    "never_mention": ("Never mention",
                      "checked before any resume, cover letter, form answer or email is made"),
    "values": ("Values and beliefs you want weighed",
               "only when you ask whether a job or company fits. Never on a resume, a form or a letter; "
               "never sent to the job search"),
    "personal": ("Personal circumstances you want weighed",
                 "only when you ask whether a job fits. Never on a resume, a form or a letter; never sent to the job search"),
}
SENSITIVE = {"values", "personal"}
VIEW = cfg.DATA / "What Job Finder knows about you.md"


def load() -> dict:
    if not FILE.exists():
        return {}
    try:
        notes = yaml.safe_load(FILE.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        raise SystemExit(f"{FILE} can't be read - fix it by hand or ask the chat to") from None
    return {k: v for k, v in notes.items() if k in KINDS and isinstance(v, list)}


def write(notes: dict) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    kept = {k: notes[k] for k in KINDS if notes.get(k)}
    body = yaml.safe_dump(kept, sort_keys=False, allow_unicode=True, width=10_000) if kept else ""
    locks.write_atomic(FILE, HEADER + body)


def held():
    return locks.held(cfg.DATA / "about.lock", "another chat is saving your notes - try again in a minute")


def add(kind: str, words: str, on: date) -> int:
    words = " ".join(words.split())
    if not words:
        sys.exit("nothing to save: give the user's own words")
    with held():
        notes = load()
        notes.setdefault(kind, []).append({"said": words, "on": on.isoformat()})
        write(notes)
        return len(notes[kind])


def forget(kind: str, n: int) -> str:
    with held():
        notes = load()
        items = notes.get(kind) or []
        if not 1 <= n <= len(items):
            sys.exit(f"no note {n} under {kind} - `about read {kind}` lists them")
        gone = items.pop(n - 1)
        write(notes)
        return gone["said"]


def read(kind: str) -> list[str]:
    return [f"{i}. {item['said']}" for i, item in enumerate(load().get(kind) or [], 1)]


# --- the page --------------------------------------------------------------------------------

def yes_no(value) -> str:
    return {True: "yes", False: "no"}.get(value, "not asked yet - each application asks")


def section(title: str, lines: list[str], used: str, who: str, change: str) -> list[str]:
    out = [f"## {title}", ""]
    out += [f"- {line}" for line in lines] or ["- Nothing saved."]
    out += ["", f"**Used for:** {used}  ", f"**Who sees it:** {who}  ", f"**To change it:** {change}", ""]
    return out


def resume_lines(config: dict) -> list[str]:
    lines = []
    master = cfg.resume_path(config, "master")
    if master.exists():
        try:
            facts = yaml.safe_load(master.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            facts = {}
        lines.append(f"Resume details: {len(facts.get('roles') or [])} jobs, "
                     f"{len(facts.get('education') or [])} schools, {len(facts.get('certifications') or [])} "
                     f"certifications - in My Resume/{master.name}")
    original = cfg.resume_path(config, "input_pdf")
    lines += [f"Resume file you gave: My Resume/{p.name}" for p in sorted(original.parent.glob(f"{original.stem}.*"))]
    return lines


def search_lines(config: dict) -> list[str]:
    rc, block = config.get("rank") or {}, config.get("blocklist") or {}
    floor = rc.get("salary_floor_usd") or 0
    pay_line = (f"Lowest hourly pay: {rank.floor_words(rc)}" if floor and rank.hourly_floor(rc)
                else f"Lowest yearly pay: {f'${floor:,}' if floor else 'any'}")
    lines = [f"Looking for: {(config.get('profile') or {}).get('name') or 'not set'}",
             pay_line,
             f"Career level: {rc.get('career_level') or 'any'}",
             f"Hours: {', '.join(rc.get('employment_types') or []) or 'any'}"]
    if companies := block.get("companies"):
        lines.append(f"Companies hidden from your list: {', '.join(companies)}")
    return lines


def permit_lines(config: dict) -> list[str]:
    wa = config.get("work_authorization") or {}
    return [f"Allowed to work in the US without restriction: {yes_no(wa.get('authorized_us'))}",
            f"Need visa sponsorship, now or later: {yes_no(wa.get('needs_sponsorship'))}",
            f"US citizen or green card holder: {yes_no(wa.get('citizen_or_permanent_resident'))}",
            f"Can hold a US security clearance: {yes_no(wa.get('can_hold_clearance'))}",
            f"International student (F-1), working through CPT or OPT: {yes_no(wa.get('student_visa'))}"]


def address_lines(config: dict) -> list[str]:
    home = config.get("home_address") or {}
    parts = [home.get(k) for k in ("street", "city", "state", "zip") if home.get(k)]
    return [", ".join(str(p) for p in parts)] if parts else []


def saved_answer_lines(config: dict) -> list[str]:
    from apply import answers
    selfid = {k: v for k, v in (config.get("self_identification") or {}).items() if k != "fill_on_forms"}
    lines = [f"Voluntary answer - {k.replace('_', ' ')}: {yes_no(v) if isinstance(v, bool) else v}"
             for k, v in selfid.items() if v is not None]
    try:
        saved = answers.load()
    except SystemExit:
        saved = []
    lines += [f"\"{s['question']}\" -> {s['answer']}" for s in saved]
    return lines


def note_lines(notes: dict, kind: str) -> list[str]:
    return [f"{i}. {item['said']} ({item.get('on', '')})" for i, item in enumerate(notes.get(kind) or [], 1)]


def page(config: dict, notes: dict, today: date) -> str:
    out = ["# What Job Finder knows about you", "",
           f"Made {today.isoformat()}. Everything here sits on this computer. Your AI reads a part when it's",
           "used - that part then reaches your AI account, like anything you type in the chat. Nothing here",
           "goes to the job search except your search filters.", ""]
    out += section("Your resume", resume_lines(config),
                   "every resume and cover letter made for you", "this computer; your AI while it works on them",
                   "tell the chat - \"change my phone number\"")
    out += section("What you're searching for", search_lines(config),
                   "finding and ranking jobs", "your search filters go to freehire.me at each check - never your "
                   "resume or work permit answers", "tell the chat - \"change my search\"")
    out += section("Work permit answers", permit_lines(config),
                   "application forms ask these; each form shows the answer before you send it",
                   "this computer; an employer when you send its form", "tell the chat")
    out += section("Home address", address_lines(config),
                   "forms that require it - never on your resume", "an employer when you send its form",
                   "tell the chat - \"forget my address\"")
    out += section("Saved answers from application forms", saved_answer_lines(config),
                   "filled into the next form, each named to you before you send it",
                   "an employer when you send its form", "tell the chat - \"forget my saved answer about ...\"")
    notes_note = "this computer; your AI only when it's used, as said under each"
    for kind, (title, used) in KINDS.items():
        out += section(f"Notes: {title}", note_lines(notes, kind), used, notes_note,
                       f"tell the chat - \"forget my note about ...\" ({'sensitive - ' if kind in SENSITIVE else ''}"
                       "saved only after you said yes)")
    out += ["## Kept outside this folder", "",
            "- Your chats live in your AI account (Claude, ChatGPT or GitHub Copilot) - delete them there.",
            "- Claude also keeps a copy of each chat on this computer for its chat history, 30 days by default.",
            "- Sign-ins to sites opened in the Job Finder window stay in the window's own storage.", ""]
    return "\n".join(out)


def show(today: date) -> Path:
    config = cfg.load_or_defaults()
    VIEW.parent.mkdir(parents=True, exist_ok=True)
    locks.write_atomic(VIEW, page(config, load(), today))
    return VIEW


def refresh(today: date) -> None:
    # the page never outlives a change: a forgotten note leaves it at once
    if VIEW.exists():
        show(today)


def main() -> None:
    ap = argparse.ArgumentParser(description="what Job Finder knows about the user + their notes beyond the resume")
    sub = ap.add_subparsers(dest="step", required=True)
    sub.add_parser("show", help="write the page of everything known; prints its path only - open it for the user")
    sub.add_parser("list", help="kinds of notes + how many each, no contents")
    r = sub.add_parser("read", help="one kind's notes, numbered - read only the kind the task uses")
    r.add_argument("kind", choices=list(KINDS))
    a = sub.add_parser("add", help="save one note in the user's own words, after they said yes")
    a.add_argument("kind", choices=list(KINDS))
    a.add_argument("words")
    f = sub.add_parser("forget", help="remove one note by its number (about read KIND)")
    f.add_argument("kind", choices=list(KINDS))
    f.add_argument("n", type=int)
    args = ap.parse_args()
    today = date.today()
    if args.step == "show":
        print(f"written: {show(today)} - open it for the user; never read it into the chat")
    elif args.step == "list":
        notes = load()
        for kind, (title, used) in KINDS.items():
            tag = " (sensitive)" if kind in SENSITIVE else ""
            print(f"{kind}{tag}: {len(notes.get(kind) or [])} - {title}; used: {used}")
    elif args.step == "read":
        print("\n".join(read(args.kind)) or f"no notes under {args.kind}")
    elif args.step == "add":
        n = add(args.kind, args.words, today)
        refresh(today)
        print(f"saved as {args.kind} note {n} in My Settings/About me.yml")
    else:
        gone = forget(args.kind, args.n)
        refresh(today)
        print(f"forgot: {gone!r}. The chat where it was said still holds it in the AI account - delete that chat there.")


if __name__ == "__main__":
    main()
