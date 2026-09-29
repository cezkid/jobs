"""Today page: what the user comes back to. Waiting on you, follow up, new since the last check,
not finished - each item ends w/ the exact words to say in the chat.

Private (their jobs, their progress) => gitignored like My Jobs/. Lists, never tables: the
editor sits beside the chat, narrow. No counts of what the user has not done - progress only.
"""
import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import dotenv_values

import autorun
import cfg
import locks
import rank
import status
import store

PAGE = cfg.ROOT / "Today.md"
WAITING_MAX, FOLLOW_UP_MAX, NEW_MAX = 5, 5, 10
# jobs per line in the chat brief: a few hundred tokens at most, the page holds the rest
BRIEF_MAX = 3
# applied this long ago, no reply => worth a check-in if they have a contact there. Convention
# (recruiter advice: 1-3 weeks), not a measured rule - the page says so
FOLLOW_UP_DAYS = 21
# posting this much older than its day on the user's list => its own age shown too (a repost or
# long-open job reaching the list now); closer than that the two read the same
POSTING_AGE_GAP = 7
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


def say(words: str) -> str:
    return f'Say: "{words}"'


def name(row: dict) -> str:
    return ", ".join(x for x in (row.get("title"), row.get("company")) if x)


def days_ago(since: str, now: str) -> str:
    days = int(status._days(since, now))
    return "today" if days < 1 else "1 day ago" if days == 1 else f"{days} days ago"


def item(row: dict, *details: str) -> list[str]:
    return [f"- **Job {row['num']}** - {name(row)}", *(f"  - {d}" for d in details if d)]


def progress(conn) -> str:
    marks = ",".join("?" * len(SENT))
    counts = dict(conn.execute(f"SELECT state, COUNT(*) FROM applications WHERE state IN ({marks}) GROUP BY state", SENT).fetchall())
    parts = [f"{sum(counts.values())} sent"] if counts else []
    parts += [f"{n} {w}" for n, w in ((counts.get("interview", 0), "interview"), (counts.get("offer", 0), "offer")) if n]
    return f"So far: {', '.join(parts)}." if parts else ""


def waiting(conn, now: str) -> list[str]:
    rows = status.waiting(conn, now)
    if not rows:
        return []
    out = ["## Waiting on you", ""]
    for r in status.numbered(conn, rows[:WAITING_MAX]):
        out += item(r, f"Resume made {days_ago(r['state_at'], now)}", r["url"],
                    say(f"apply to job {r['num']}") + f' - or "I sent job {r["num"]}" if you already did')
    if len(rows) > WAITING_MAX:
        out.append(f"- More in the chat. {say('what is waiting on me')}")
    return out + [""]


def follow_up_rows(conn, now: str) -> list[dict]:
    return [r for r in status.in_progress(conn)
            if r["state"] == "applied" and status._days(r["state_at"], now) >= FOLLOW_UP_DAYS]


def follow_up(conn, now: str) -> list[str]:
    rows = follow_up_rows(conn, now)
    if not rows:
        return []
    out = ["## Follow up", "",
           f"No reply {FOLLOW_UP_DAYS}+ days after applying. A short check-in is common if you have a contact"
           " there - that's convention, not a rule. Many employers never write back.", ""]
    for r in status.numbered(conn, rows[:FOLLOW_UP_MAX]):
        out += item(r, f"Applied {days_ago(r['state_at'], now)}, no reply yet", r["url"],
                    say(f"I heard back from job {r['num']}") + f' - or "mark job {r["num"]} as no"')
    if len(rows) > FOLLOW_UP_MAX:
        out.append(f"- More in the chat. {say('what should I follow up on')}")
    return out + [""]


def new_jobs(conn, config: dict, now: datetime) -> list[dict]:
    """Found in the last check, or not yet announced: the same jobs the email / pop-up named,
    ranked the same way, so "Job 12" here = Job 12 there. Stale rows (likely filled) and jobs
    the user already acts on are left out."""
    last_check = conn.execute("SELECT MAX(fetched_at) FROM jobs").fetchone()[0]
    if last_check is None:
        return []
    announced = {r[0] for r in conn.execute("SELECT public_slug FROM seen WHERE alerted_at >= ?", (last_check,))}
    acting = {v for r in conn.execute("SELECT public_slug, url FROM applications") for v in r if v}
    out = []
    for j in rank.rank(store.all_jobs(conn), config, now):
        slugs = {j["public_slug"], *j["duplicates"]}
        if j["stale"] or (j["seen"] and not slugs & announced) or (slugs | {j["url"]}) & acting:
            continue
        out.append(j)
    return out


def added(job: dict, now: datetime) -> str:
    """Age that agrees w/ "new": when the job reached their list (first fetch), not freehire's
    first sighting - that alone read "new" next to "first seen 66d ago" (real install)."""
    now_iso = now.astimezone(timezone.utc).strftime(store.ISO)
    listed = int(status._days(job["first_fetched_at"], now_iso))
    out = f"added to your list {days_ago(job['first_fetched_at'], now_iso)}"
    posting = rank.age(job, now)
    if posting is not None and posting - listed >= POSTING_AGE_GAP:
        out += f" · posting first seen {posting} days ago"
    return out


def new_section(conn, config: dict, now: datetime) -> list[str]:
    rows = new_jobs(conn, config, now)
    if not rows:
        return []
    out = ["## New since last check", ""]
    for j in store.numbered(conn, rows[:NEW_MAX]):
        out += item(j, rank.reasons(j, config, now, added(j, now)), j["url"], say(f"resume for job {j['num']}"))
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


def build(conn, config: dict, jobs_dir: Path, now: datetime, todo: list[str]) -> str:
    """now = local time the page is for (shown in its heading); every section hides when empty."""
    now_iso = now.astimezone(timezone.utc).strftime(store.ISO)
    status.backfill(conn, jobs_dir)
    out = ["# Today", "", f"{now:%A, %B} {now.day}."]
    if line := progress(conn):
        out[-1] += f" {line}"
    out.append("")
    body = waiting(conn, now_iso) + follow_up(conn, now_iso) + new_section(conn, config, now)
    if todo:
        body += ["## Not finished", "", *(f"- {t}" for t in todo), ""]
    out += body or [f"Nothing new since the last check. {say('find new jobs')}", ""]
    out += ["## What you can say", "", *(f'- "{s}"' for s in SAY), "",
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
    if rows := follow_up_rows(conn, now_iso)[:BRIEF_MAX]:
        out.append(f"- Follow up (applied {FOLLOW_UP_DAYS}+ days, no reply): {jobs(status.numbered(conn, rows), 'applied')}")
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
