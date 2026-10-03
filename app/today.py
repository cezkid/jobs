"""Today page: what the user comes back to. Waiting on you, follow up, new since the last check,
not finished - each item ends w/ the exact words to say in the chat.

Private (their jobs, their progress) => gitignored like My Jobs/. Lists, never tables: the
editor sits beside the chat, narrow. No counts of what the user has not done - progress only.
"""
import argparse
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from dotenv import dotenv_values

import autorun
import cfg
import locks
import rank
import status
import store
from text import inert_md

PAGE = cfg.ROOT / "Today.md"
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
SAY = (
    "find new jobs",
    "resume for job 12",
    "I sent job 12 / I heard back from job 12",
    "is job 12 still open?",
    "change what I'm looking for",
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


def resume_link(job_dir: Path | None, root: Path) -> str:
    """Opens the PDF as a tab in the preview (measured: file link -> vscode.open; a folder link only
    reveals it in the file list). Relative to the page, spaces %20 - preview reads no raw spaces."""
    if not (pdf := resume_pdf(job_dir)):
        return ""
    try:
        rel = pdf.relative_to(root).as_posix()
    except ValueError:
        return ""
    return f"[Open its resume]({quote(rel)})"


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


def links(row: dict, dirs: dict[str, Path] | None, root: Path) -> str:
    """Posting + its resume on one line: both open from the page, no URL to read."""
    return " · ".join(filter(None, (posting(row.get("url")), resume_link((dirs or {}).get(row.get("key")), root))))


def progress(conn) -> str:
    """Sent so far, counting a job closed after it was sent: closing it never un-sends it."""
    marks = ",".join("?" * len(SENT))
    counts = dict(conn.execute(
        f"SELECT state, COUNT(*) FROM applications a WHERE state IN ({marks}) OR (state = 'closed' AND EXISTS"
        f" (SELECT 1 FROM application_log l WHERE l.key = a.key AND l.state IN ({marks}))) GROUP BY state",
        SENT + SENT).fetchall())
    parts = [f"{sum(counts.values())} sent"] if counts else []
    parts += [f"{n} {w}" for n, w in ((counts.get("interview", 0), "interview"), (counts.get("offer", 0), "offer")) if n]
    return f"So far: {', '.join(parts)}." if parts else ""


def waiting(conn, now: str, dirs: dict[str, Path] | None = None, root: Path = cfg.ROOT) -> list[str]:
    rows = status.waiting(conn, now)
    if not rows:
        return []
    out = ["## Waiting on you", ""]
    for r in status.numbered(conn, rows[:WAITING_MAX]):
        out += item(r, f"Resume made {days_ago(r['state_at'], now)}", links(r, dirs, root),
                    say(f"apply to job {r['num']}", f"I sent job {r['num']}", tail=" if you already did"))
    if len(rows) > WAITING_MAX:
        out.append(f"- More in the chat. {say('what is waiting on me')}")
    return out + [""]


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


def follow_up(conn, now: str, days: dict[str, int], dirs: dict[str, Path] | None = None, root: Path = cfg.ROOT) -> list[str]:
    rows = follow_up_rows(conn, now, days)
    if not rows:
        return []
    out = ["## Follow up", "", FOLLOW_UP_NOTE, ""]
    for r in status.numbered(conn, rows[:FOLLOW_UP_MAX]):
        n = r["num"]
        if r["chased"]:
            out += item(r, f"You followed up {days_ago(r['chased'], now)}, still no reply", links(r, dirs, root),
                        say(f"job {n} is closed", f"I heard back from job {n}"))
        else:
            out += item(r, f"{STAGE_WORDS[r['state']]} {days_ago(r['state_at'], now)}, no reply yet", links(r, dirs, root),
                        say(f"write a follow-up for job {n}", f"I heard back from job {n}", f"job {n} is closed"))
    if len(rows) > FOLLOW_UP_MAX:
        out.append(f"- More in the chat. {say('what should I follow up on')}")
    return out + [""]


def interviews(conn, now: str, days: dict[str, int], dirs: dict[str, Path] | None = None, root: Path = cfg.ROOT) -> list[str]:
    """Jobs at the interview stage, until a follow-up is due (they move to Follow up then)."""
    due = {r["key"] for r in follow_up_rows(conn, now, days)}
    rows = [r for r in status.in_progress(conn) if r["state"] == "interview" and r["key"] not in due]
    if not rows:
        return []
    out = ["## Interviews", ""]
    for r in status.numbered(conn, rows[:FOLLOW_UP_MAX]):
        out += item(r, f"Interview stage since {days_ago(r['state_at'], now)}", links(r, dirs, root),
                    say(f"practise my interview for job {r['num']}", f"I had the interview for job {r['num']}"))
    return out + [""]


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


def new_section(conn, config: dict, now: datetime) -> list[str]:
    rows = new_jobs(conn, config, now)
    if not rows:
        return []
    out = ["## New since last check", ""]
    for j in store.numbered(conn, rows[:NEW_MAX]):
        out += item(j, rank.reasons(j, config, now, rank.added(j, now)), posting(j["url"]), say(f"resume for job {j['num']}"))
    if len(rows) > NEW_MAX:
        out.append(f"- {len(rows) - NEW_MAX} more - ask the chat. {say('show me more new jobs')}")
    return out + [""]


def unfinished(config: dict, data: Path = cfg.DATA, morning_check_on: bool | None = None) -> list[str]:
    """Setup steps still open, only the ones that are. Email is optional: listed only when
    started and left half done, never as a nudge to add it."""
    out = []
    if not cfg.resume_path(config, "master").exists():
        out.append(f"Your resume isn't in yet. {say('import my resume')}")
    elif not (data / "gaps.json").exists():
        out.append(f"Your resume lines could carry more of your own numbers. {say('ask me about my resume numbers')}")
    if not (autorun.is_on() if morning_check_on is None else morning_check_on):
        out.append(f"The morning job check is off. {say('turn on the morning job check')}")
    email = data / "email.env"
    if email.exists() and not all(dotenv_values(email).get(k) for k in ("SMTP_USER", "SMTP_PASSWORD")):
        out.append(f"Email alerts are half set up. {say('finish setting up email')}")
    return out


def build(conn, config: dict, jobs_dir: Path, now: datetime, todo: list[str], root: Path = cfg.ROOT) -> str:
    """now = local time the page is for (shown in its heading); every section hides when empty.
    root = folder the page sits in: its resume links are relative to it."""
    now_iso = now.astimezone(timezone.utc).strftime(store.ISO)
    status.backfill(conn, jobs_dir)
    dirs = job_folders(jobs_dir)
    out = ["# Today", "", f"{now:%A, %B} {now.day}."]
    if line := progress(conn):
        out[-1] += f" {line}"
    out.append("")
    days = config["follow_up"]
    body = (waiting(conn, now_iso, dirs, root) + interviews(conn, now_iso, days, dirs, root)
            + follow_up(conn, now_iso, days, dirs, root) + new_section(conn, config, now))
    if todo:
        body += ["## Not finished", "", *(f"- {t}" for t in todo), ""]
    out += body or [f"Nothing new since the last check. {say('find new jobs')}", ""]
    out += ["## What you can say", "", *("- " + " / ".join(map(chip, s.split(" / "))) for s in SAY), "",
            "Guides:", "", *(f"- [{title}]({link})" for title, link in GUIDES), ""]
    return "\n".join(out)


def brief(conn, config: dict, jobs_dir: Path, now: datetime, todo: list[str]) -> str:
    """The page in a few lines for a new Claude chat (session-start hook, .claude/settings.json)
    => a plain "hi" gets what's next w/o a command. Job numbers, titles, companies only - the
    postings they work on reach the chat anyway; never resume text, name, contact or settings.
    Other AIs have no such hook: they keep the page."""
    now_iso = now.astimezone(timezone.utc).strftime(store.ISO)
    status.backfill(conn, jobs_dir)

    def jobs(rows: list[dict], when: str = "") -> str:
        return "; ".join(f"Job {r['num']} - {name(r)}" + (f", {when} {days_ago(r['state_at'], now_iso)}" if when else "")
                         for r in rows)

    out = ["Job Finder today (same as their Today page). If the user only greets you or asks what's next,"
           " answer with this in plain words, each job written"
           " \"**Job 12** - title, company\", never a 1. 2. 3. list; otherwise use it only when it helps."
           " Never say how many resumes are unsent."]
    if rows := status.waiting(conn, now_iso)[:BRIEF_MAX]:
        out.append(f"- Waiting on you (resume made, not sent): {jobs(status.numbered(conn, rows), 'resume made')}")
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
            text = build(conn, config, cfg.resume_path(config, "jobs_dir"), now or datetime.now().astimezone(),
                         unfinished(config))
            locks.write_atomic(page, text)
    finally:
        conn.close()
    return page


def main() -> None:
    ap = argparse.ArgumentParser(description="Write Today.md: waiting on you, follow up, new jobs, not finished")
    ap.add_argument("--print", action="store_true", help="print the page instead of writing it")
    ap.add_argument("--brief", action="store_true", help="print a few lines for a new chat (Claude session-start hook)")
    args = ap.parse_args()
    if args.brief:
        print_brief()
        return
    config = cfg.load()
    if args.print:
        conn = store.connect(cfg.db_path(config))
        print(build(conn, config, cfg.resume_path(config, "jobs_dir"), datetime.now().astimezone(), unfinished(config)))
        return
    print(f"written: {os.path.relpath(write(config), cfg.ROOT)}")


if __name__ == "__main__":
    main()
