"""Follow-up email: a short note asking where an application stands, drafted from what the
program holds - no AI writing step, nothing sent for the user (they send it from their own email).

Shape (app/docs/apply/follow-up.md): name the role and when, ask one direct question, at most one
line on what they bring - their own words, verbatim from the resume sent - thanks, their name. No
apology, no "just checking in", no urgency they didn't state. Under 120 words.
"""
import argparse
import json
import sys

import cfg
import status
import store
from resume import schema, tailor

FILE = "Follow-up email.md"
SENT_STATES = ("applied", "heard_back", "interview")
COUNT = "zero one two three four five six seven eight nine".split()
ASK_APPLIED = "Is the role still open, and what is the timeline for the next step?"
ASK_LATER = "Where does my application stand, and what are the next steps?"


def count_word(n: int) -> str:
    return COUNT[n] if n < len(COUNT) else "several"


def elapsed(days: int) -> str:
    """Weeks up to 45 days, then months: "three weeks", "two months"."""
    if days < 45:
        weeks = max(1, (days + 3) // 7)
        return "a week" if weeks == 1 else f"{count_word(weeks)} weeks"
    months = (days + 15) // 30
    return "a month" if months == 1 else f"{count_word(months)} months"


def draft(role: str, company: str, days: int, state: str, strength: str | None, name: str) -> tuple[str, str]:
    subject = f"Following up: {role} application"
    if state == "applied":
        opening = f"I applied for the {role} role at {company} {elapsed(days)} ago and have not had a reply yet."
        ask = ASK_APPLIED
    else:
        opening = f"We last spoke about the {role} role at {company} {elapsed(days)} ago, and I have not heard since."
        ask = ASK_LATER
    lines = ["Hello,", opening, *([f"For context: {strength}"] if strength else []), ask, "Thanks for your time.", name]
    return subject, "\n\n".join(lines)


def strength(master: dict, job_dir) -> str | None:
    """One line the sent resume shows for a must-have, word for word the user's own - else none."""
    data = job_dir / tailor.JOB_DATA
    if not (data / "tailored.json").exists() or not (data / "jd.json").exists():
        return None
    tailored = json.loads((data / "tailored.json").read_text(encoding="utf-8"))
    job = json.loads((data / "jd.json").read_text(encoding="utf-8"))
    own = {b["id"]: b["claim"] for e in [*master["roles"], *master.get("projects", [])] for b in e["bullets"]}
    on_page = {b["text"] for t in tailored["entries"] for b in t["bullets"]}
    for row in tailor.coverage_rows(job, tailored, master):
        if row["priority"] != "required" or row["status"] != "met":
            continue
        for ref in row["evidence"]:
            if own.get(ref) in on_page:
                return own[ref]
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description="draft a follow-up email for one job into its folder - the user sends it")
    ap.add_argument("job", nargs="?", help="job number, slug, link or job folder name")
    ap.add_argument("--company")
    ap.add_argument("--title")
    ap.add_argument("--name", help="name to sign with (default: the name on their resume)")
    args = ap.parse_args()
    config = cfg.load()
    jobs_dir = cfg.resume_path(config, "jobs_dir")
    conn = store.connect(cfg.db_path(config))
    try:
        try:
            job = status.resolve(conn, jobs_dir, args.job, args.company, args.title)
        except status.NotFound as e:
            sys.exit(str(e))
        row = status.get(conn, job["key"])
        if not row or row["state"] not in SENT_STATES:
            sys.exit("a follow-up is for a job sent and waiting on a reply - record that it was sent first")
        days = int(status._days(row["state_at"], store.utc_now()))
        folder = status.folder_of(jobs_dir, job["key"])
    finally:
        conn.close()
    master = schema.load(cfg.resume_path(config, "master"))
    subject, body = draft(job["title"], job["company"] or "your company", days, row["state"],
                          strength(master, folder) if folder else None, args.name or master["contact"]["name"])
    text = f"Subject: {subject}\n\n{body}\n"
    if folder:
        (folder / FILE).write_text(text, encoding="utf-8")
        print(f"written: {folder / FILE}")
    else:
        print(text)
    print("the user sends it from their own email; nothing is sent for them. Sent -> status followed-up")


if __name__ == "__main__":
    main()
