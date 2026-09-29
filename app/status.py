import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import cfg
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
}
LINK_LINE = "- Link: "


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


def folders(jobs_dir: Path) -> list[dict]:
    """Every job folder, read only: link from Check before sending.md (jd.json as fallback),
    company + title from jd.json, else from the 'Company - Title' folder name."""
    out = []
    if not jobs_dir.is_dir():
        return out
    for job_dir in sorted(p for p in jobs_dir.iterdir() if p.is_dir()):
        check, saved = job_dir / tailor.CHECK_FILE, job_dir / tailor.JOB_DATA / "jd.json"
        if not check.exists() and not saved.exists():
            continue
        jd = json.loads(saved.read_text(encoding="utf-8")) if saved.exists() else {}
        company, _, title = job_dir.name.partition(" - ")
        company, title = (jd.get("company") or company), (jd.get("title") or title or company)
        made = check.exists()
        out.append({
            "dir": job_dir, "url": folder_link(job_dir) or jd.get("url") or None,
            "company": company, "title": title, "public_slug": jd.get("public_slug"),
            "state": "resume_made" if made else "saved",
            "at": datetime.fromtimestamp((check if made else saved).stat().st_mtime, timezone.utc).strftime(store.ISO),
        })
    return out


def _log(conn, key: str, state: str, at: str) -> None:
    conn.execute("INSERT INTO application_log VALUES (?, ?, ?)", (key, state, at))


def backfill(conn, jobs_dir: Path) -> int:
    """Job folder w/ a resume = resume made; folder still being tailored = saved. Never
    overrides a status already recorded, except saved -> resume made once the resume exists."""
    added = 0
    for f in folders(jobs_dir):
        key = job_key(f["url"], f["company"], f["title"])
        row = conn.execute("SELECT state FROM applications WHERE key = ?", (key,)).fetchone()
        if row is None:
            conn.execute("INSERT INTO applications VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (key, f["url"], f["company"], f["title"], f["public_slug"], f["state"], f["at"], f["at"]))
            _log(conn, key, f["state"], f["at"])
            added += 1
        elif row["state"] == "saved" and f["state"] == "resume_made":
            conn.execute("UPDATE applications SET state = ?, state_at = ? WHERE key = ?", (f["state"], f["at"], key))
            _log(conn, key, f["state"], f["at"])
    conn.commit()
    return added


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


def when(day: str | None, now: str) -> str:
    return date.fromisoformat(day).strftime("%Y-%m-%dT12:00:00Z") if day else now


def main() -> None:
    ap = argparse.ArgumentParser(description="Where each job stands: saved, resume made, applied, heard back ...")
    steps = ap.add_subparsers(dest="step")
    steps.add_parser("list", help="every job w/ a status, newest first (default)")
    for name, helptext in (("show", "one job's status"), ("set", "record a job's status")):
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
        try:
            job = resolve(conn, jobs_dir, args.job, args.company, args.title, args.url)
            if args.step == "set":
                set_state(conn, job, state_key(args.state), when(args.on, store.utc_now()))
        except (NotFound, ValueError) as e:
            sys.exit(str(e))
        row = get(conn, job["key"])
        print(line(numbered(conn, [row])[0]) if row else f"no status yet: {job['company']} - {job['title']}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
