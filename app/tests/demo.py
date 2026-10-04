"""Demo folder for live looks at the app window: fills THIS checkout's private folders w/ placeholder
jobs so `jobs.py today` + the window show every section. Never real data, never the owner's install.

    uv run python app/tests/demo.py

Writes My Settings/Search settings.yml (example search), My Jobs/1 To apply + 2 Applied (3 job
folders), .data/jobs.db (8 listed jobs, sample required asks), My Resume/Resume details.yml
("Your Name", finance) => Best to apply next shows its match; no numbers yet => Not finished shows too. Each
file it writes is listed in .data/demo-files.txt; a file there it did not write => refuses, so a
real user's folder is never overwritten. Rerun = same demo, fresh dates.
"""
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cfg  # noqa: E402
import status  # noqa: E402
import store  # noqa: E402
from resume import report, tailor  # noqa: E402

MANIFEST = Path(".data") / "demo-files.txt"
# owner's live install: never filled, whatever else holds
LIVE_INSTALL = Path.home() / "jobs"
CHECKED = ("My Resume", "My Settings", "My Jobs")
DB = Path(".data") / "jobs.db"

LISTED = [
    # slug, title, company, tier, city, pay min/max, days since posted
    ("demo-1", "Financial Analyst", "Example Co", "remote", None, 70000, 90000, 1),
    ("demo-2", "Senior Accountant", "Sample Corp", "remote", None, 80000, 100000, 2),
    ("demo-3", "Accounts Payable Specialist", "Placeholder Inc", "local", "Springfield", 50000, 60000, 1),
    ("demo-4", "FP&A Manager", "Example Co", "remote", None, None, None, 3),
    ("demo-5", "Staff Accountant", "Demo Partners", "local", "Springfield", 60000, 72000, 2),
    ("demo-6", "Payroll Specialist", "Sample Corp", "remote", None, 55000, 65000, 4),
    ("demo-7", "Budget Analyst", "Placeholder Inc", "remote", None, None, None, 5),
    ("demo-8", "Tax Associate", "Demo Partners", "local", "Springfield", 58000, 70000, 2),
]
# slug, stage, status set here (None = from the folder: resume made / saved), days since
# required asks per listed job: strong + weak matches, a light + a heavy list (Best to apply next)
ASKS = {
    "demo-2": ["Bachelor's degree in Accounting or Finance", "3+ years of accounting experience",
               "Month-end close and account reconciliations", "Advanced Excel", "Experience with NetSuite"],
    "demo-3": ["1+ years of accounts payable experience", "Invoice processing and vendor payments", "Excel"],
    "demo-5": ["Bachelor's degree in Accounting", "2+ years of experience in general ledger accounting",
               "Journal entries and account reconciliations", "Month-end close", "Excel"],
    "demo-6": ["3+ years of payroll processing experience", "Experience with ADP Workforce Now",
               "Multi-state payroll tax filings", "Garnishments and benefits deductions", "CPP certification"],
    "demo-8": ["CPA or CPA eligible", "2+ years of public accounting experience", "Individual and partnership tax returns",
               "Experience with CCH Axcess", "Lead client engagements end to end", "Manage seasonal staff",
               "Own the review of workpapers", "Research complex tax issues", "Excel", "Bachelor's degree in Accounting",
               "Supervise junior associates", "Manage multiple client deadlines", "Tax provision experience",
               "State and local tax filings"],
}
RESUME = """contact:
  name: Your Name
  email: your.name@example.com
  location: Springfield, IL
summary: Accountant with six years of month-end close, reconciliations and financial reporting.
roles:
  - company: Example Co
    title: Senior Accountant
    start: "2022-03"
    end: present
    bullets:
      - Ran the month-end close for three entities in NetSuite, closing in five days instead of eight.
      - Built account reconciliations and journal entries for the general ledger in Excel.
  - company: Sample Corp
    title: Staff Accountant
    start: "2019-06"
    end: "2022-02"
    bullets:
      - Processed invoices and vendor payments for accounts payable, about 400 a month.
      - Prepared budget variance reports for the finance team each quarter.
skills:
  - group: Tools
    items: [Excel, NetSuite, QuickBooks]
education:
  - institution: State University
    degree: Bachelor of Science
    field: Accounting
    end: "2019-05"
"""
FOLDERS = [
    ("demo-1", "1 To apply", None, 2),
    ("demo-4", "1 To apply", None, 1),
    ("demo-7", "2 Applied", "applied", 25),
]


def iso(at: datetime) -> str:
    return at.astimezone(timezone.utc).strftime(store.ISO)


def refuse_reason(root: Path) -> str | None:
    if root.resolve() == LIVE_INSTALL.resolve():
        return f"{root} is the live install - demo data goes only in a developer checkout"
    try:
        ours = set((root / MANIFEST).read_text(encoding="utf-8").splitlines())
    except OSError:
        ours = set()
    theirs = [p for name in CHECKED for p in (root / name).rglob("*")
              if p.is_file() and p.name != ".DS_Store" and p.relative_to(root).as_posix() not in ours]
    if (root / DB).exists() and DB.as_posix() not in ours:
        theirs.append(root / DB)
    if theirs:
        return f"{theirs[0]} was not written by the demo - this folder holds real data, nothing changed"
    return None


def job(slug, title, company, tier, city, low, high, days, now) -> dict:
    return {**{c: None for c in store.COLS},
            "public_slug": slug, "tier": tier, "title": title, "company": company,
            "company_slug": company.lower().replace(" ", "-"), "url": f"https://example.com/jobs/{slug}",
            "source": "greenhouse", "location": city or "Remote, US", "cities": [city] if city else [],
            "countries": ["us"], "regions": [], "work_mode": "onsite" if city else "remote",
            "skills": [], "collections": [], "employment_type": "full_time", "seniority": None,
            "category": "finance", "salary_min": low, "salary_max": high,
            "salary_currency": "USD" if low else None, "salary_period": "year" if low else None,
            "posted_at": iso(now - timedelta(days=days)), "created_at": iso(now - timedelta(days=days)),
            "description": f"Placeholder posting for {title} at {company}.", "reality": {},
            "enrichment": {"requirements": [{"text": t, "priority": "required"} for t in ASKS.get(slug, [])]}}


def job_folder(root: Path, conn, row: dict, stage: str, made: bool, at: datetime) -> Path:
    d = root / "My Jobs" / stage / tailor.folder_name(row, store.number(conn, row["public_slug"]))
    (d / tailor.JOB_DATA).mkdir(parents=True, exist_ok=True)
    tailor.write_json(d / tailor.JOB_DATA / "jd.json", {k: row[k] for k in ("public_slug", "title", "company", "url")})
    (d / tailor.POSTING_FILE).write_text(
        f"# {row['title']} - {row['company']}\n\n{row['description']}\n\n- Pay: placeholder\n- Where: {row['location']}\n",
        encoding="utf-8")
    if made:
        check = d / tailor.CHECK_FILE
        check.write_text(f"# Check before sending\n\n{status.LINK_LINE}{row['url']}\n\n{report.READY}\n", encoding="utf-8")
        stamp = at.timestamp()
        os.utime(check, (stamp, stamp))
    return d


def fill(root: Path | None = None, now: datetime | None = None) -> list[Path]:
    root, now = root or cfg.ROOT, now or datetime.now(timezone.utc)
    if why := refuse_reason(root):
        raise SystemExit(f"demo: {why}")
    for name in CHECKED:
        shutil.rmtree(root / name, ignore_errors=True)
    (root / DB).unlink(missing_ok=True)
    cfg.ensure_private_dirs(root)
    (root / ".data").mkdir(exist_ok=True)
    settings = root / "My Settings" / "Search settings.yml"
    shutil.copyfile(cfg.PROFILES / "example.yml", settings)
    (root / "My Resume" / "Resume details.yml").write_text(RESUME, encoding="utf-8")

    conn = store.connect(root / DB)
    rows = {r[0]: job(*r, now) for r in LISTED}
    store.upsert(conn, list(rows.values()), iso(now))
    for slug, stage, state, days in FOLDERS:
        at = now - timedelta(days=days)
        d = job_folder(root, conn, rows[slug], stage, made=True, at=at)
        if state:
            f = status.folder(d)
            status.set_state(conn, {**f, "key": status.folder_key(f)}, state, iso(at))
    status.backfill(conn, root / "My Jobs")
    conn.commit()
    conn.close()

    written = sorted(p for name in CHECKED for p in (root / name).rglob("*") if p.is_file()) + [root / DB]
    (root / MANIFEST).write_text("".join(p.relative_to(root).as_posix() + "\n" for p in written), encoding="utf-8")
    return written


def main() -> None:
    written = fill()
    print(f"demo: {len(written)} files written under {cfg.ROOT} - next: uv run app/jobs.py today")


if __name__ == "__main__":
    main()
