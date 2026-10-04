"""Today page: what the user comes back to. Waiting on you, follow up, new since the last check,
not finished - each item ends w/ the exact words to say in the chat.

Private (their jobs, their progress) => gitignored like My Jobs/. Lists, never tables: the
editor sits beside the chat, narrow. No counts of what the user has not done - progress only.
"""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote

from dotenv import dotenv_values

import autorun
import cfg
import locks
import rank
import status
import store
from text import inert_md

PAGE = cfg.ROOT / "Today.md"
# same page as data for the window's dashboard (app/vscode/today.js); beside the page's own .data/
DASHBOARD = Path(".data") / "today.json"
DASHBOARD_VERSION = 1
# words to say, shared w/ the dashboard buttons: a word changed here changes there
SAY_FILE = cfg.APP / "vscode" / "say.json"
TEMPLATES = {t["id"]: t["words"] for t in json.loads(SAY_FILE.read_text(encoding="utf-8"))["templates"]}
WAITING_MAX, FOLLOW_UP_MAX, NEW_MAX = 5, 5, 10
# jobs per line in the chat brief: a few hundred tokens at most, the page holds the rest
BRIEF_MAX = 3
# where it stands -> how the follow-up item opens; the days come from settings `follow_up`
# (app/docs/apply/follow-up.md: convention + thin measurements, said so on the page)
STAGE_WORDS = {"applied": "Applied", "heard_back": "Heard back", "interview": "Interview"}
FOLLOW_UP_NOTE = ("No reply for a while. A short note asking where things stand is common practice - about 3 weeks"
                  " after applying, about 2 weeks once you've talked with them - if you have someone to write to."
                  " Many employers never write back.")
# applied or further along: counted as progress on the page
SENT = ("applied", "heard_back", "interview", "no", "offer")
# START HERE is first-run steps only; everything else it said lives in these (launch.py)
GUIDES = (
    ("What you can ask", "Guides/What%20you%20can%20ask.md"),
    ("Who sees what", "Guides/Who%20sees%20what.md"),
    ("What makes a good resume", "Guides/What%20makes%20a%20good%20resume.md"),
    ("Keep your chats out of AI training", "Guides/Keep%20your%20chats%20out%20of%20AI%20training.md"),
)


def words(template: str, n: int | None = None) -> str:
    """Words to say from say.json; job number filled in."""
    return TEMPLATES[template].replace("{n}", str(n))


# "What you can say": example number 12, each one a say.json template
SAY = (
    (words("find"),),
    (words("resume", 12),),
    (words("sent", 12), words("heard_back", 12)),
    (words("still_open", 12),),
    (words("search"),),
)


def chip(words: str) -> str:
    """Words to say as a code span: pages.css draws them as bold quoted words (never yellow: yellow
    means a button), the words stay on the page for other AIs + the chat brief."""
    return f"`{words}`"


def say(words: str, *more: str, tail: str = "") -> str:
    """Say: `apply to job 12` - or `I sent job 12` if you already did."""
    alts = f" - or {', '.join(map(chip, more))}" if more else ""
    return f"Say: {chip(words)}{alts}{tail}"


def posting(url: str | None) -> str:
    """Link text, never a bare 100-char URL. URL copied as is (AGENTS.md: a rebuilt one 404s);
    angle brackets keep a ')' in it from ending the link."""
    if not url:
        return ""
    return f"[Open the posting](<{url.replace('<', '%3C').replace('>', '%3E')}>)"


def resume_pdf(job_dir: Path | None) -> Path | None:
    """Tailored resume in the job folder (`First_Last_Resume.pdf`); not made yet => None."""
    if job_dir is None:
        return None
    return next(iter(sorted(job_dir.glob("*Resume.pdf"))), None)


def rel(path: Path | None, root: Path) -> str | None:
    """Path relative to the page's folder, `/` between parts; outside it => None."""
    if path is None:
        return None
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return None


def resume_link(rel_pdf: str | None) -> str:
    """Opens the PDF as a tab in the preview (measured: file link -> vscode.open; a folder link only
    reveals it in the file list). Relative to the page, spaces %20 - preview reads no raw spaces."""
    return f"[Open its resume]({quote(rel_pdf)})" if rel_pdf else ""


def job_folders(jobs_dir: Path) -> dict[str, Path]:
    """Job key -> its folder, read once per page."""
    return {status.folder_key(f): f["dir"] for f in status.folders(jobs_dir)}


def name(row: dict) -> str:
    return ", ".join(x for x in (row.get("title"), row.get("company")) if x)


def days_ago(since: str, now: str) -> str:
    days = int(status._days(since, now))
    return "today" if days < 1 else "1 day ago" if days == 1 else f"{days} days ago"


def item(row: dict, *details: str) -> list[str]:
    return [f"- **Job {row['num']}** - {inert_md(name(row))}", *(f"  - {d}" for d in details if d)]


def card(row: dict, detail: str, says: list[str], dirs: dict[str, Path] | None = None, root: Path = cfg.ROOT,
         tail: str = "") -> dict:
    """One job, as both the page and the dashboard show it: says[0] = the main thing to do."""
    job_dir = (dirs or {}).get(row.get("key"))
    return {"num": row["num"], "title": row.get("title") or "", "company": row.get("company") or "",
            "detail": detail, "url": row.get("url") or None, "resume": rel(resume_pdf(job_dir), root),
            "folder": rel(job_dir, root), "say": says, "tail": tail}


def card_md(c: dict) -> list[str]:
    """Posting + its resume on one line: both open from the page, no URL to read."""
    links = " · ".join(filter(None, (posting(c["url"]), resume_link(c["resume"]))))
    return item(c, c["detail"], links, say(*c["say"], tail=c["tail"]))


def section_md(sec: dict | None) -> list[str]:
    if not sec:
        return []
    out = [f"## {sec['title']}", ""] + ([sec["note"], ""] if sec.get("note") else [])
    for c in sec["cards"]:
        out += card_md(c)
    if more := sec.get("more"):
        out.append(f"- {more['text']} {say(more['say'])}")
    return out + [""]


def progress_counts(conn) -> dict[str, int]:
    """Sent so far, counting a job closed after it was sent: closing it never un-sends it."""
    marks = ",".join("?" * len(SENT))
    counts = dict(conn.execute(
        f"SELECT state, COUNT(*) FROM applications a WHERE state IN ({marks}) OR (state = 'closed' AND EXISTS"
        f" (SELECT 1 FROM application_log l WHERE l.key = a.key AND l.state IN ({marks}))) GROUP BY state",
        SENT + SENT).fetchall())
    return {"sent": sum(counts.values()), "interview": counts.get("interview", 0), "offer": counts.get("offer", 0)}


def progress(conn) -> str:
    counts = progress_counts(conn)
    parts = [f"{counts['sent']} sent"] if counts["sent"] else []
    parts += [f"{counts[w]} {w}" for w in ("interview", "offer") if counts[w]]
    return f"So far: {', '.join(parts)}." if parts else ""


def tiles(counts: dict[str, int], new: int) -> list[dict]:
    """Dashboard's top row: progress + what's new only, never a count of what's left to do.
    section = the section it tells about (dashboard orders tiles like its sections)."""
    shown = (("New since last check", new, "new"), ("Sent so far", counts["sent"], None),
             ("Interviews", counts["interview"], "interviews"), ("Offers", counts["offer"], None))
    return [{"label": label, "value": n, "section": sec} for label, n, sec in shown if n]


def waiting_section(conn, now: str, dirs: dict[str, Path] | None = None, root: Path = cfg.ROOT) -> dict | None:
    rows = status.waiting(conn, now)
    if not rows:
        return None
    # no age: "made 8 days ago" reads as overdue (critique 2026-10-04); Follow up keeps its days
    cards = [card(r, "Ready to send", [words("apply", r["num"]), words("sent", r["num"])],
                  dirs, root, tail=" if you already did")
             for r in status.numbered(conn, rows[:WAITING_MAX])]
    more = {"text": "More in the chat.", "say": words("more_waiting")} if len(rows) > WAITING_MAX else None
    return {"id": "waiting", "title": "Waiting on you", "note": None, "cards": cards, "more": more}


def waiting(conn, now: str, dirs: dict[str, Path] | None = None, root: Path = cfg.ROOT) -> list[str]:
    return section_md(waiting_section(conn, now, dirs, root))


def follow_up_rows(conn, now: str, days: dict[str, int]) -> list[dict]:
    """In progress + quiet past their stage's days. A logged follow-up starts one more stretch;
    past that too, `chased` is set and the page suggests closing - one nudge per silence."""
    out = []
    for r in status.in_progress(conn):
        if not (wait := days.get(r["state"])):
            continue
        chased = status.last_event(conn, r["key"], "followed_up", r["state_at"])
        if status._days(chased or r["state_at"], now) >= wait:
            out.append(dict(r, chased=chased))
    return out


def follow_up_section(conn, now: str, days: dict[str, int], dirs: dict[str, Path] | None = None,
                      root: Path = cfg.ROOT) -> dict | None:
    rows = follow_up_rows(conn, now, days)
    if not rows:
        return None
    cards = []
    for r in status.numbered(conn, rows[:FOLLOW_UP_MAX]):
        n = r["num"]
        if r["chased"]:
            cards.append(card(r, f"You followed up {days_ago(r['chased'], now)}, still no reply",
                              [words("closed", n), words("heard_back", n)], dirs, root))
        else:
            cards.append(card(r, f"{STAGE_WORDS[r['state']]} {days_ago(r['state_at'], now)}, no reply yet",
                              [words("follow_up", n), words("heard_back", n), words("closed", n)], dirs, root))
    more = {"text": "More in the chat.", "say": words("more_follow_up")} if len(rows) > FOLLOW_UP_MAX else None
    return {"id": "follow_up", "title": "Follow up", "note": FOLLOW_UP_NOTE, "cards": cards, "more": more}


def follow_up(conn, now: str, days: dict[str, int], dirs: dict[str, Path] | None = None, root: Path = cfg.ROOT) -> list[str]:
    return section_md(follow_up_section(conn, now, days, dirs, root))


def interviews_section(conn, now: str, days: dict[str, int], dirs: dict[str, Path] | None = None,
                       root: Path = cfg.ROOT) -> dict | None:
    """Jobs at the interview stage, until a follow-up is due (they move to Follow up then)."""
    due = {r["key"] for r in follow_up_rows(conn, now, days)}
    rows = [r for r in status.in_progress(conn) if r["state"] == "interview" and r["key"] not in due]
    if not rows:
        return None
    cards = [card(r, f"Interview stage since {days_ago(r['state_at'], now)}",
                  [words("practise", r["num"]), words("had_interview", r["num"])], dirs, root)
             for r in status.numbered(conn, rows[:FOLLOW_UP_MAX])]
    return {"id": "interviews", "title": "Interviews", "note": None, "cards": cards, "more": None}


def new_jobs(conn, config: dict, now: datetime) -> list[dict]:
    """Found in the last check, or not yet announced: the same jobs the email / pop-up named,
    ranked the same way, so "Job 12" here = Job 12 there. Stale rows (likely filled) and jobs
    the user already acts on are left out."""
    last_check = conn.execute("SELECT MAX(fetched_at) FROM jobs").fetchone()[0]
    if last_check is None:
        return []
    announced = {r[0] for r in conn.execute("SELECT public_slug FROM seen WHERE alerted_at >= ?", (last_check,))}
    acting = {v for r in conn.execute("SELECT public_slug, link_key(url) FROM applications") for v in r if v}
    out = []
    for j in rank.rank(store.all_jobs(conn), config, now):
        slugs = {j["public_slug"], *j["duplicates"]}
        if j["stale"] or (j["seen"] and not slugs & announced) or (slugs | {store.link_key(j["url"])}) & acting:
            continue
        out.append(j)
    return out


def new_section(conn, config: dict, now: datetime, rows: list[dict] | None = None) -> dict | None:
    rows = new_jobs(conn, config, now) if rows is None else rows
    if not rows:
        return None
    cards = [card(j, rank.reasons(j, config, now, rank.added(j, now)), [words("resume", j["num"])])
             for j in store.numbered(conn, rows[:NEW_MAX])]
    more = ({"text": f"{len(rows) - NEW_MAX} more - ask the chat.", "say": words("more_new")}
            if len(rows) > NEW_MAX else None)
    return {"id": "new", "title": "New since last check", "note": None, "cards": cards, "more": more}


def unfinished(config: dict, data: Path = cfg.DATA, morning_check_on: bool | None = None) -> list[str]:
    """Setup steps still open, only the ones that are. Email is optional: listed only when
    started and left half done, never as a nudge to add it."""
    out = []
    if not cfg.resume_path(config, "master").exists():
        out.append(f"Your resume isn't in yet. {say(words('import'))}")
    elif not (data / "gaps.json").exists():
        out.append(f"Your resume lines could carry more of your own numbers. {say(words('gaps'))}")
    if not (autorun.is_on() if morning_check_on is None else morning_check_on):
        out.append(f"The morning job check is off. {say(words('morning'))}")
    email = data / "email.env"
    if email.exists() and not all(dotenv_values(email).get(k) for k in ("SMTP_USER", "SMTP_PASSWORD")):
        out.append(f"Email alerts are half set up. {say(words('email'))}")
    return out


def todo_item(line: str) -> dict:
    """`text Say: `words`` => its two parts (dashboard: text + a button)."""
    text, _, rest = line.partition(" Say: ")
    return {"text": text, "say": rest.strip("`") if rest else None}


def model(conn, config: dict, jobs_dir: Path, now: datetime, todo: list[str], root: Path = cfg.ROOT) -> dict:
    """What the page shows, as data: the Markdown page + the window's dashboard both drawn from it.
    Paths relative to root (the page's folder), `/` between parts."""
    now_iso = now.astimezone(timezone.utc).strftime(store.ISO)
    status.backfill(conn, jobs_dir)
    dirs = job_folders(jobs_dir)
    days = config["follow_up"]
    new = new_jobs(conn, config, now)
    sections = [waiting_section(conn, now_iso, dirs, root), interviews_section(conn, now_iso, days, dirs, root),
                follow_up_section(conn, now_iso, days, dirs, root), new_section(conn, config, now, new)]
    sections = [s for s in sections if s]
    return {
        "version": DASHBOARD_VERSION,
        "date": f"{now:%A, %B} {now.day}",
        "progress": progress(conn),
        "tiles": tiles(progress_counts(conn), len(new)),
        "sections": sections,
        "todo": [todo_item(t) for t in todo],
        "empty": None if sections or todo else {"text": "Nothing new since the last check.", "say": words("find")},
        "examples": [list(s) for s in SAY],
        "guides": [{"title": title, "path": unquote(link)} for title, link in GUIDES],
    }


def render(m: dict) -> str:
    """Markdown page from the model: other AIs, the chat brief's twin, and the fallback when the
    window's own extension is missing."""
    out = ["# Today", "", f"{m['date']}." + (f" {m['progress']}" if m["progress"] else ""), ""]
    for sec in m["sections"]:
        out += section_md(sec)
    if m["todo"]:
        out += ["## Not finished", "", *(f"- {t['text']}" + (f" {say(t['say'])}" if t["say"] else "") for t in m["todo"]), ""]
    if m["empty"]:
        out += [f"{m['empty']['text']} {say(m['empty']['say'])}", ""]
    out += ["## What you can say", "", *("- " + " / ".join(map(chip, s)) for s in m["examples"]), "",
            "Guides:", "", *(f"- [{title}]({link})" for title, link in GUIDES), ""]
    return "\n".join(out)


def build(conn, config: dict, jobs_dir: Path, now: datetime, todo: list[str], root: Path = cfg.ROOT) -> str:
    """now = local time the page is for (shown in its heading); every section hides when empty.
    root = folder the page sits in: its resume links are relative to it."""
    return render(model(conn, config, jobs_dir, now, todo, root))


def brief(conn, config: dict, jobs_dir: Path, now: datetime, todo: list[str]) -> str:
    """The page in a few lines for a new Claude chat (session-start hook, .claude/settings.json)
    => a plain "hi" gets what's next w/o a command. Job numbers, titles, companies only - the
    postings they work on reach the chat anyway; never resume text, name, contact or settings.
    Other AIs have no such hook: they keep the page."""
    now_iso = now.astimezone(timezone.utc).strftime(store.ISO)
    status.backfill(conn, jobs_dir)

    def jobs(rows: list[dict]) -> str:
        return "; ".join(f"Job {r['num']} - {name(r)}" for r in rows)

    out = ["Job Finder today (same as their Today page). If the user only greets you or asks what's next,"
           " answer with this in plain words, each job written"
           " \"**Job 12** - title, company\", never a 1. 2. 3. list; otherwise use it only when it helps."
           " Never say how many resumes are unsent."]
    if rows := status.waiting(conn, now_iso)[:BRIEF_MAX]:
        out.append(f"- Waiting on you (resume made, not sent): {jobs(status.numbered(conn, rows))}")
    if rows := follow_up_rows(conn, now_iso, config["follow_up"])[:BRIEF_MAX]:
        quiet = "; ".join(f"Job {r['num']} - {name(r)}, " + (f"followed up {days_ago(r['chased'], now_iso)}" if r["chased"]
                          else f"{STAGE_WORDS[r['state']].lower()} {days_ago(r['state_at'], now_iso)}")
                          for r in status.numbered(conn, rows))
        out.append(f"- Follow up (no reply for a while): {quiet}")
    if rows := new_jobs(conn, config, now):
        out.append(f"- New since last check: {len(rows)}. Top: {jobs(store.numbered(conn, rows[:BRIEF_MAX]))}")
    out += [f"- Not finished: {t.split(' Say: ')[0]}" for t in todo]
    if len(out) == 1:
        out.append("- Nothing new since the last check.")
    return "\n".join(out)


def print_brief() -> None:
    """Hook entry: prints nothing before setup (START HERE covers it) or on any failure - a new
    chat must never open on an error."""
    try:
        if not cfg.config_path().exists():
            return
        config = cfg.load()
        conn = store.connect(cfg.db_path(config))
        try:
            print(brief(conn, config, cfg.resume_path(config, "jobs_dir"), datetime.now().astimezone(),
                        unfinished(config)))
        finally:
            conn.close()
    except Exception:
        return


def lock():
    """Two chats (or a chat + the launcher) rebuilding at once => one writes, the other waits."""
    return locks.held(cfg.DATA / "today.lock", "another chat is updating the Today page - try again in a minute")


def write(config: dict, page: Path = PAGE, now: datetime | None = None) -> Path:
    conn = store.connect(cfg.db_path(config))
    try:
        with lock():
            m = model(conn, config, cfg.resume_path(config, "jobs_dir"), now or datetime.now().astimezone(),
                      unfinished(config), page.parent)
            # data first: the dashboard redraws on the page's change and finds today's data there
            dashboard = page.parent / DASHBOARD
            dashboard.parent.mkdir(parents=True, exist_ok=True)
            locks.write_atomic(dashboard, json.dumps(m, indent=1, ensure_ascii=False) + "\n")
            locks.write_atomic(page, render(m))
    finally:
        conn.close()
    return page


def refresh(config: dict, page: Path = PAGE) -> Path:
    """The one rebuild the launcher + the window extension both call: job folders filed under their
    stage (one moved by hand, one a file kept from moving last time), then the page. Filing never
    stops the page: what can't move now waits for the next one."""
    try:
        status.sort_jobs(config)
    except (Exception, SystemExit):
        pass
    return write(config, page)


def main() -> None:
    ap = argparse.ArgumentParser(description="Write Today.md: waiting on you, follow up, new jobs, not finished")
    ap.add_argument("--print", action="store_true", help="print the page instead of writing it")
    ap.add_argument("--brief", action="store_true", help="print a few lines for a new chat (Claude session-start hook)")
    ap.add_argument("--refresh", action="store_true", help="file job folders under their stage, then write the page"
                    " (launcher + window do this at start)")
    args = ap.parse_args()
    if args.brief:
        print_brief()
        return
    config = cfg.load()
    if args.print:
        conn = store.connect(cfg.db_path(config))
        print(build(conn, config, cfg.resume_path(config, "jobs_dir"), datetime.now().astimezone(), unfinished(config)))
        return
    page = refresh(config) if args.refresh else write(config)
    print(f"written: {os.path.relpath(page, cfg.ROOT)}")


if __name__ == "__main__":
    main()
