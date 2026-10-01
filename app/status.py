import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import cfg
import locks
import store
from resume import tailor

# state -> what the user reads. Order = the path a job usually takes
STATES = {
    "saved": "Saved",
    "resume_made": "Resume made",
    "applied": "Applied",
    "heard_back": "Heard back",
    "interview": "Interview",
    "no": "They said no",
    "offer": "Offer",
    "not_sending": "Not sending",
    "closed": "Closed",
}
LINK_LINE = "- Link: "
# resume made this many days ago -> asked "did you send it?" at chat start; untouched this long
# -> drops out of Waiting on you
ASK_AFTER_DAYS, QUIET_AFTER_DAYS = 3, 14
# still being worked on => worth asking "is it still open?"; no / offer / not sending / closed are done
IN_PROGRESS = ("saved", "resume_made", "applied", "heard_back", "interview")
# status -> its job folder's place under My Jobs. Same pipeline job-search trackers use (to apply,
# applied, interviewing, closed) - convention, not a measured rule. Numbered => every file list
# (VS Code, Finder, Explorer, a browser's upload box) shows the stages in this order
STAGES = {
    "saved": "1 To send", "resume_made": "1 To send",
    "applied": "2 Sent",
    "heard_back": "3 Heard back", "interview": "3 Heard back", "offer": "3 Heard back",
    "no": "4 Closed", "not_sending": "4 Closed", "closed": "4 Closed",
}


def state_key(word: str) -> str:
    """'resume made', 'Heard-back', 'not_sending' -> key; the AI passes the user's own words."""
    key = "_".join(word.casefold().replace("-", " ").replace("_", " ").split())
    by_label = {"_".join(label.casefold().split()): k for k, label in STATES.items()}
    if key in STATES:
        return key
    if key in by_label:
        return by_label[key]
    raise ValueError(f"{word}: not a status; use one of {', '.join(STATES)}")


def outside_key(company: str, title: str) -> str:
    return "outside:" + " ".join(company.casefold().split()) + "|" + " ".join(title.casefold().split())


def job_key(url: str | None, company: str, title: str) -> str:
    return url.strip() if url and url.strip() else outside_key(company, title)


def _same(a: str | None, b: str | None) -> bool:
    return " ".join((a or "").casefold().split()) == " ".join((b or "").casefold().split())


def folder_link(job_dir: Path) -> str | None:
    check = job_dir / tailor.CHECK_FILE
    if not check.exists():
        return None
    for line in check.read_text(encoding="utf-8").splitlines():
        if line.startswith(LINK_LINE):
            return line[len(LINK_LINE):].strip() or None
    return None


def folder(job_dir: Path) -> dict | None:
    """One job folder, read only: its job file names the job, Check before sending.md the link.
    No readable job file => not a job folder (a stray note, a half-copied folder): never
    counted, numbered or moved."""
    jd = tailor.read_jd(job_dir)
    if jd is None:
        return None
    check, saved = job_dir / tailor.CHECK_FILE, job_dir / tailor.JOB_DATA / "jd.json"
    try:
        made = check.exists()
        at = datetime.fromtimestamp((check if made else saved).stat().st_mtime, timezone.utc).strftime(store.ISO)
        link = folder_link(job_dir)
    except OSError:  # moved or deleted while being read
        return None
    return {
        "dir": job_dir, "url": link or jd.get("url") or None,
        "company": jd.get("company") or "", "title": jd.get("title") or "", "public_slug": jd.get("public_slug"),
        "state": "resume_made" if made else "saved", "at": at,
    }


def folders(jobs_dir: Path) -> list[dict]:
    return [f for d in tailor.job_dirs(jobs_dir) if (f := folder(d))]


def folder_key(f: dict) -> str:
    return job_key(f["url"], f["company"], f["title"])


def _log(conn, key: str, state: str, at: str) -> None:
    conn.execute("INSERT INTO application_log VALUES (?, ?, ?)", (key, state, at))


def _record(conn, f: dict, at: str) -> bool:
    """New job -> its folder's state; saved -> resume made. A status already recorded (applied,
    not sending ...) is never overridden."""
    key = job_key(f["url"], f["company"], f["title"])
    row = conn.execute("SELECT state FROM applications WHERE key = ?", (key,)).fetchone()
    if row is None:
        conn.execute("INSERT INTO applications VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (key, f["url"], f["company"], f["title"], f["public_slug"], f["state"], at, at))
        _log(conn, key, f["state"], at)
        return True
    if row["state"] == "saved" and f["state"] == "resume_made":
        conn.execute("UPDATE applications SET state = ?, state_at = ? WHERE key = ?", (f["state"], at, key))
        _log(conn, key, f["state"], at)
    return False


def backfill(conn, jobs_dir: Path) -> int:
    """Job folder w/ a resume = resume made; folder still being tailored = saved."""
    added = sum(_record(conn, f, f["at"]) for f in folders(jobs_dir))
    conn.commit()
    return added


def record_made(conn, job_dir: Path, at: str) -> None:
    """`tailor check` passed => resume made, w/o the user saying so."""
    f = folder(job_dir)
    if f and f["state"] == "resume_made":
        _record(conn, f, at)
        conn.commit()


class NotFound(LookupError):
    pass


def _from_jobs_row(row) -> dict:
    return {"url": row["url"], "company": row["company"] or "", "title": row["title"], "public_slug": row["public_slug"]}


def _from_folder(f: dict) -> dict:
    return {k: f[k] for k in ("url", "company", "title", "public_slug")}


def resolve(conn, jobs_dir: Path, job: str | None = None, company: str | None = None,
            title: str | None = None, url: str | None = None) -> dict:
    """Job number, listed job (slug or link), pasted posting (its link, slug or job folder name),
    or a job applied outside Job Finder (company + title, link optional) -> key, url, company, title."""
    found = None
    try:
        job = job and store.key_for(conn, job)
    except LookupError as e:
        raise NotFound(str(e)) from None
    if job and job.startswith(("http://", "https://")):
        url = job
    elif job:
        row = conn.execute("SELECT * FROM jobs WHERE public_slug = ?", (job,)).fetchone()
        found = _from_jobs_row(row) if row else next(
            (_from_folder(f) for f in folders(jobs_dir) if job in (f["public_slug"], f["dir"].name)), None)
        if found is None:
            found = next((dict(r) for r in conn.execute("SELECT * FROM applications") if _same(r["key"], job)), None)
        if found is None:
            raise NotFound(f"{job}: no such job on your list or in your job folders")
    if found is None and url:
        url = url.strip()
        row = conn.execute("SELECT * FROM applications WHERE key = ? OR url = ?", (url, url)).fetchone()
        jobs_row = conn.execute("SELECT * FROM jobs WHERE url = ?", (url,)).fetchone()
        folder = next((f for f in folders(jobs_dir) if f["url"] == url), None)
        found = (dict(row) if row else _from_jobs_row(jobs_row) if jobs_row
                 else _from_folder(folder) if folder else None)
    if found is None and company and title:
        row = next((r for r in conn.execute("SELECT * FROM applications")
                    if _same(r["company"], company) and _same(r["title"], title)), None)
        listed = [r for r in conn.execute("SELECT * FROM jobs WHERE closed_at IS NULL")
                  if _same(r["company"], company) and _same(r["title"], title)]
        folder = next((f for f in folders(jobs_dir) if _same(f["company"], company) and _same(f["title"], title)), None)
        found = (dict(row) if row else _from_jobs_row(listed[0]) if len(listed) == 1
                 else _from_folder(folder) if folder
                 else {"url": url or None, "company": company.strip(), "title": title.strip(), "public_slug": None})
    if found is None:
        raise NotFound("name the job: its link, or company + title" if not url
                       else f"{url}: not a job on your list or in your job folders - add company + title")
    found = {k: found.get(k) for k in ("url", "company", "title", "public_slug")}
    found["key"] = job_key(found["url"], found["company"] or "", found["title"] or "")
    return found


def set_state(conn, job: dict, state: str, at: str) -> None:
    conn.execute(
        "INSERT INTO applications VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (key) DO UPDATE SET"
        " state = excluded.state, state_at = excluded.state_at,"
        " url = COALESCE(applications.url, excluded.url),"
        " public_slug = COALESCE(applications.public_slug, excluded.public_slug)",
        (job["key"], job["url"], job["company"], job["title"], job["public_slug"], state, at, at))
    _log(conn, job["key"], state, at)
    conn.commit()


def get(conn, key: str) -> dict | None:
    row = conn.execute("SELECT * FROM applications WHERE key = ?", (key,)).fetchone()
    return dict(row) if row else None


def all_statuses(conn) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM applications ORDER BY state_at DESC")]


def numbered(conn, rows: list[dict]) -> list[dict]:
    """Same number the job had on the list; a job w/o a slug (applied outside) gets its own."""
    with conn:
        for r in rows:
            r["num"] = store.number(conn, r["public_slug"] or r["key"])
    return rows


def line(row: dict) -> str:
    name = " - ".join(x for x in (row["company"], row["title"]) if x)
    return f"#{row['num']:<4} {STATES[row['state']]:13} {row['state_at'][:10]}  {name}  {row['url'] or '(no link)'}"


def _days(since: str, now: str) -> float:
    return (datetime.strptime(now, store.ISO) - datetime.strptime(since, store.ISO)).total_seconds() / 86400


def waiting(conn, now: str) -> list[dict]:
    """Resume made, not sent yet, oldest first. Untouched 14+ days -> drops out quietly: kept,
    never deleted, never asked about again."""
    rows = conn.execute("SELECT * FROM applications WHERE state = 'resume_made' ORDER BY state_at")
    return [dict(r) for r in rows if _days(r["state_at"], now) < QUIET_AFTER_DAYS]


def to_ask(conn, now: str) -> dict | None:
    """The one job to ask 'did you send it?' about at chat start: oldest resume made 3+ days
    ago, unless it was asked in the last 3 days. One job, never a stack; the ask is recorded
    here, so a second chat opened the same day asks nothing."""
    with conn:
        due = [r for r in waiting(conn, now) if _days(r["state_at"], now) >= ASK_AFTER_DAYS]
        if not due:
            return None
        oldest = due[0]
        asked = conn.execute("SELECT at FROM asked WHERE key = ?", (oldest["key"],)).fetchone()
        if asked and _days(asked["at"], now) < ASK_AFTER_DAYS:
            return None
        conn.execute("INSERT INTO asked VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET at = excluded.at",
                     (oldest["key"], now))
    return oldest


def _day(at: str) -> str:
    return at[:10]


def still_open(conn, row: dict, stale_days: int, now: str) -> tuple[str, str]:
    """Open / may be closed / can't tell, w/ why - read off the job list only, never the
    employer's page (that would send something new off the computer). A pasted posting or a job
    applied outside was never on the list, so nothing can say it closed."""
    job = (row["public_slug"] and conn.execute("SELECT * FROM jobs WHERE public_slug = ?", (row["public_slug"],)).fetchone()) \
        or (row["url"] and conn.execute("SELECT * FROM jobs WHERE url = ?", (row["url"],)).fetchone())
    if not job:
        return "can't tell", "never on your job list (pasted or found elsewhere) - check the link"
    if job["closed_at"]:
        return "may be closed", f"gone from your job search since {_day(job['closed_at'])}"
    # measured from the last check, not today: a morning check that stopped running must not
    # turn every job "closed"
    last = conn.execute("SELECT MAX(fetched_at) FROM jobs").fetchone()[0]
    unseen = int(_days(job["fetched_at"], last))
    if unseen > stale_days:
        return "may be closed", f"not seen in {unseen} days"
    if (idle := int(_days(last, now))) > stale_days:
        return "can't tell", f"no job check in {idle} days - check the link"
    return "open", f"on your job list, seen {_day(job['fetched_at'])}"


def in_progress(conn) -> list[dict]:
    marks = ",".join("?" * len(IN_PROGRESS))
    return [dict(r) for r in conn.execute(
        f"SELECT * FROM applications WHERE state IN ({marks}) ORDER BY state_at", IN_PROGRESS)]


def lock(wait_s: float = 60):
    """Two chats (or a chat + the launcher) filing folders at once => one moves, the other waits."""
    return locks.held(cfg.DATA / "job-folders.lock", "another chat is moving job folders - try again in a minute",
                      wait_s)


def placed(conn, f: dict, jobs_dir: Path) -> Path | None:
    """Where a job folder belongs: under the stage its status names, as 'Job N - Company - Title'.
    No status yet => where a new one starts (saved / resume made)."""
    row = get(conn, folder_key(f))
    stage = STAGES.get(row["state"] if row else f["state"])
    if stage is None:
        return None
    with conn:  # committed => the number in the name is the one every chat reads
        num = store.number(conn, f["public_slug"] or folder_key(f))
    return jobs_dir / stage / tailor.folder_name(f, num)


def sort_folders(conn, jobs_dir: Path, key: str | None = None,
                 wait_s: float = 60) -> tuple[list[tuple[Path, Path]], list[tuple[Path, str]]]:
    """Every job folder (key => that job's only) -> where `placed` says. Renamed, never copied,
    merged, overwritten or deleted. Can't move now (a file open on Windows, name taken) => stays
    whole where it is, said why, tried again next time. Deepest first => a job folder dragged
    inside another is filed before the outer one moves. Emptied stage folders stay."""
    todo = [(f["dir"], to) for f in sorted(folders(jobs_dir), key=lambda f: -len(f["dir"].parts))
            if key in (None, folder_key(f)) and (to := placed(conn, f, jobs_dir)) and to != f["dir"]]
    moved, stuck = [], []
    if not todo:
        return moved, stuck
    with lock(wait_s):
        for d, to in todo:
            if not d.is_dir():  # another chat filed it first
                continue
            try:
                # same folder under other letter case (macOS, Windows) => a rename, not a clash
                if to.exists() and not to.samefile(d):
                    stuck.append((d, f"{to.parent.name}/{to.name} already there - left both"))
                    continue
                to.parent.mkdir(parents=True, exist_ok=True)
                d.rename(to)
                moved.append((d, to))
            except OSError as e:
                stuck.append((d, f"could not move now - {e.strerror or type(e).__name__}"))
    return moved, stuck


def folder_of(jobs_dir: Path, key: str) -> Path | None:
    return next((f["dir"] for f in folders(jobs_dir) if folder_key(f) == key), None)


def file_job(conn, jobs_dir: Path, job_dir: Path) -> tuple[Path, str | None]:
    """A job tailored (again) => its folder filed now, before any path is handed out. Tailoring a
    closed one again reopens it (saved => To send). -> folder, status it left when reopened."""
    f = folder(job_dir)
    if f is None:
        return job_dir, None
    key, reopened = folder_key(f), None
    row = get(conn, key)
    if row and STAGES.get(row["state"]) == STAGES["closed"]:
        reopened = STATES[row["state"]]
        set_state(conn, row, "saved", store.utc_now())
    sort_folders(conn, jobs_dir, key)
    return folder_of(jobs_dir, key) or job_dir, reopened


def sort_jobs(config: dict, wait_s: float = 5) -> tuple[list, list]:
    """Launch: every misplaced job folder filed before the Today page is built."""
    conn = store.connect(cfg.db_path(config))
    try:
        return sort_folders(conn, cfg.resume_path(config, "jobs_dir"), wait_s=wait_s)
    finally:
        conn.close()


def when(day: str | None, now: str) -> str:
    return date.fromisoformat(day).strftime("%Y-%m-%dT12:00:00Z") if day else now


def main() -> None:
    ap = argparse.ArgumentParser(description="Where each job stands: saved, resume made, applied, heard back ...")
    steps = ap.add_subparsers(dest="step")
    steps.add_parser("list", help="every job w/ a status, newest first (default)")
    steps.add_parser("ask", help="chat start: the one job to ask 'did you send it?' about, if any")
    steps.add_parser("open", help="each job in progress: open, may be closed, or can't tell - and why")
    steps.add_parser("sent", help="each job not marked sent: sent page in this computer's browser history? sent,"
                     " likely not sent, can't tell - and why")
    steps.add_parser("sort", help="file every job folder under the stage its status names (launch does it too)")
    for name, helptext in (("show", "one job's status + its folder"),
                           ("set", "record a job's status; its folder moves to that stage")):
        p = steps.add_parser(name, help=helptext)
        p.add_argument("job", nargs="?", help="job number, slug, the job's https link, or its job folder name")
        p.add_argument("--company")
        p.add_argument("--title")
        p.add_argument("--url", help="link for a job applied outside Job Finder")
        if name == "set":
            p.add_argument("state", help=" | ".join(STATES))
            p.add_argument("--on", help="YYYY-MM-DD it happened, when not today")
    # `set <job> <state>` or `set <state> --company C --title T`: argparse fills state first
    args = ap.parse_args()
    config = cfg.load_or_defaults()
    jobs_dir = cfg.resume_path(config, "jobs_dir")
    conn = store.connect(cfg.db_path(config))
    try:
        backfill(conn, jobs_dir)
        if args.step in (None, "list"):
            rows = numbered(conn, all_statuses(conn))
            print("\n".join(map(line, rows)) if rows else "no jobs w/ a status yet")
            return
        if args.step == "ask":
            now = store.utc_now()
            row = to_ask(conn, now)
            if row is None:
                print("nothing to ask")
                return
            print(line(numbered(conn, [row])[0]))
            print(f"resume made {int(_days(row['state_at'], now))} days ago - ask once: did you send it?"
                  f" (Sent -> applied, Not yet -> nothing, Not sending -> not_sending)")
            return
        if args.step == "open":
            now, stale_days = store.utc_now(), config.get("rank", cfg.defaults()["rank"])["stale_days"]
            rows = numbered(conn, in_progress(conn))
            for row in rows:
                print(line(row) + "\n      " + " - ".join(still_open(conn, row, stale_days, now)))
            if not rows:
                print("no jobs in progress")
            return
        if args.step == "sent":
            import sent
            visits, unread = sent.all_visits()
            rows = numbered(conn, [r for r in in_progress(conn) if r["state"] in ("saved", "resume_made")])
            for row in rows:
                print(line(row) + "\n      " + " - ".join(sent.verdict(row, visits)))
            if not rows:
                print("no jobs waiting to be sent")
            if unread:
                print("could not read: " + ", ".join(unread) + " (macOS: Safari needs Full Disk Access)"
                      * ("Safari" in unread))
            return
        if args.step == "sort":
            moved, stuck = sort_folders(conn, jobs_dir)
            for old, new in moved:
                print(f"moved: {old.relative_to(jobs_dir)} -> {new.relative_to(jobs_dir)}")
            for d, why in stuck:
                print(f"left: {d.relative_to(jobs_dir)} - {why}")
            if not moved and not stuck:
                print("every job folder is where its status says")
            return
        stuck = []
        try:
            job = resolve(conn, jobs_dir, args.job, args.company, args.title, args.url)
            if args.step == "set":
                set_state(conn, job, state_key(args.state), when(args.on, store.utc_now()))
                stuck = sort_folders(conn, jobs_dir, job["key"])[1]
        except (NotFound, ValueError) as e:
            sys.exit(str(e))
        row = get(conn, job["key"])
        print(line(numbered(conn, [row])[0]) if row else f"no status yet: {job['company']} - {job['title']}")
        # moved folder => old paths in the chat are stale; this line is the one to use
        if d := folder_of(jobs_dir, job["key"]):
            print(f"folder: {d}" + "".join(f" - not moved now ({why}); moves at next launch or status sort"
                                           for _, why in stuck))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
