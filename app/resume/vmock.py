"""Read a VMock resume score back - and upload a resume to be scored - in Job Finder's own Chrome.

VMock (app/docs/vmock.md) scores a resume on the sign-in the user's school or career service
gives them, so there is no key to call it with: the user signs in once in Job Finder's Chrome
and this reads the pages they would read. Read only: it opens tabs and module links, and never
clicks Auto-fix, Save, Load Suggestions, Add to Dictionary or Delete. `upload` is the one step
that spends something - one of the user's licensed uploads - so it runs only with --yes, which
the assistant passes after the user said yes in chat.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import cfg
from apply import browser

BASE = "https://www.vmock.com"
DASHBOARD = f"{BASE}/dashboard/resume"
RESUME_ID = re.compile(r"/resume/(\d+)/")
OUT = cfg.DATA / "vmock"
REPORT_NAME = "Vmock feedback.md"
STATUSES = ("Good Job!", "On Track!", "Needs Work!")
MODULE_SCORE = re.compile(r"^(\d+) ?/(\d+)$")
# page sections under each module's sidebar, read in this order
MODULES = ("impact", "presentation", "competencies")
# a check without the hygiene star runs straight into the part of the page it is about
AREA = re.compile(r"(Personal Details|Education|Experience|Skills|Summary|Projects)$")
FAILING, PASSING = re.compile(r"^FAILING CHECKS ?(\d+)$"), re.compile(r"^PASSING CHECKS ?(\d+)$")
# scoring after an upload runs about a minute; past this the user finishes it in the window
UPLOAD_WAIT_MS = 240_000
POLL_MS = 10_000
NEWEST_FEEDBACK = "a:has-text('View Resume Feedback')"


def lines(text: str) -> list[str]:
    return [l.strip() for l in text.splitlines() if l.strip()]


def rated(rows: list[str], i: int) -> bool:
    """Row i names a check: a status follows it. Two statuses in a row are the colour legend."""
    after = rows[i + 1:i + 3]
    return rows[i] not in STATUSES and bool(after) and after[0] in STATUSES \
        and not (len(after) > 1 and after[1] in STATUSES)


def parse_summary(text: str) -> dict:
    """Summary tab text -> overall score, each module's score and each check's status, the steps."""
    rows = lines(text)
    out = {"score": None, "modules": {}, "steps": []}
    if "/100" in rows:
        out["score"] = int(rows[rows.index("/100") - 1])
    module = None
    for i, row in enumerate(rows):
        if row.startswith("How to improve"):
            break
        if (m := MODULE_SCORE.match(row)) and i + 1 < len(rows):
            module = rows[i + 1]
            out["modules"][module] = {"score": int(m.group(1)), "of": int(m.group(2)), "checks": {}}
        elif module and rated(rows, i):
            out["modules"][module]["checks"][row] = rows[i + 1].rstrip("!")
    if "Steps to Improve Your Score" in rows:
        tail = rows[rows.index("Steps to Improve Your Score") + 1:]
        out["steps"] = [f"{tail[i]}: {tail[i + 2]}" for i in range(0, len(tail) - 2, 3) if tail[i + 1].startswith("+")]
    return out


def parse_checks(text: str) -> dict:
    """A section's own page -> its status lines and its failing / passing hygiene checks."""
    rows = lines(text)
    out = {"status": {}, "failing": [], "passing": []}
    bucket = None
    for i, row in enumerate(rows):
        if FAILING.match(row):
            bucket = "failing"
        elif PASSING.match(row):
            bucket = "passing"
        elif bucket and row != "* Hygiene Check":
            # "Font Size (Name)*Personal Details": the check, then the part of the page it is about
            out[bucket].append(row.split("*")[0].strip() if "*" in row else AREA.sub("", row).strip())
        elif rated(rows, i):
            out["status"][row] = rows[i + 1].rstrip("!")
    return out


def compare(now: dict, before: dict | None) -> list[str]:
    """What moved since the last read, in plain words."""
    if not before:
        return []
    out = []
    if now["score"] != before["score"]:
        out.append(f"Overall score {before['score']} -> {now['score']}")
    for name, module in now["modules"].items():
        was = before["modules"].get(name, {})
        if was and was.get("score") != module["score"]:
            out.append(f"{name} {was['score']}/{was['of']} -> {module['score']}/{module['of']}")
        for check, status in module["checks"].items():
            if was and was.get("checks", {}).get(check) not in (None, status):
                out.append(f"{check}: {was['checks'][check]} -> {status}")
    for section, now_section in now.get("sections", {}).items():
        was = before.get("sections", {}).get(section, {}).get("status", {})
        out += [f"{name}: {was[name]} -> {status}" for name, status in now_section.get("status", {}).items()
                if was.get(name) not in (None, status)]
    before_failing = {c for s in before.get("sections", {}).values() for c in s.get("failing", [])}
    now_failing = {c for s in now.get("sections", {}).values() for c in s.get("failing", [])}
    out += [f"{c}: now passing" for c in sorted(before_failing - now_failing)]
    out += [f"{c}: now failing" for c in sorted(now_failing - before_failing)]
    return out


def report_md(now: dict, changes: list[str]) -> str:
    out = ["# Your VMock score", "", f"Read {now['read']} from {now['url']}", "",
           f"**Overall: {now['score']} out of 100**", ""]
    if changes:
        out += ["## What changed since the last score", "", *(f"- {c}" for c in changes), ""]
    for name, module in now["modules"].items():
        out += [f"## {name}: {module['score']} out of {module['of']}", ""]
        out += [f"- {check}: {status}" for check, status in module["checks"].items()]
        out.append("")
    failing = [(s, c) for s, sec in now.get("sections", {}).items() for c in sec["failing"]]
    if failing:
        out += ["## Format checks still failing", "", *(f"- {c}" for _, c in failing), ""]
    if now["steps"]:
        out += ["## VMock's suggested next steps", "", *(f"- {s}" for s in now["steps"]), ""]
    out += ["What VMock measures, and which of its advice Job Finder follows or declines and why: "
            "`app/docs/vmock.md`."]
    return "\n".join(out) + "\n"


def previous(this_dir: Path) -> dict | None:
    """The last read of any other upload: each upload is a resume id of its own on VMock."""
    reads = sorted((p for p in OUT.glob("*/feedback.json") if p.parent != this_dir), key=lambda p: p.stat().st_mtime)
    return json.loads(reads[-1].read_text(encoding="utf-8")) if reads else None


def close_popups(page) -> None:
    for _ in range(3):
        shown = [d for d in page.query_selector_all(".modal.show") if d.is_visible()]
        if not shown:
            return
        close = shown[0].query_selector("button.modal-close, button.close, .btn-close, [aria-label*=lose]")
        if close and close.is_visible():
            close.click()
        else:
            page.keyboard.press("Escape")
        page.wait_for_timeout(600)


def crawl(page, resume_id: str) -> dict:
    """Summary tab, then every section's own page. Clicks tabs and section links only."""
    page.goto(f"{BASE}/resume/{resume_id}/feedback/summary")
    page.wait_for_load_state("networkidle")
    close_popups(page)
    now = parse_summary(page.inner_text("body"))
    now["sections"], raw = {}, {"summary": page.inner_text("body")}
    page.goto(f"{BASE}/resume/{resume_id}/feedback/system")
    page.wait_for_load_state("networkidle")
    for module in MODULES:
        close_popups(page)
        page.click(f"a[href$='#{module}']")
        page.wait_for_timeout(1200)
        links = page.eval_on_selector_all("a.sidebar-link-v2", "els => els.filter(e => e.offsetParent).map(e => e.getAttribute('href'))")
        for href in links:
            close_popups(page)
            page.click(f"a.sidebar-link-v2[href='{href}']")
            page.wait_for_timeout(1200)
            body = page.query_selector(".resume-submodule-content")
            raw[href.strip("#")] = text = body.inner_text() if body else ""
            now["sections"][href.strip("#")] = parse_checks(text)
    return now | {"raw": raw}


def resume_id_from(page, url: str | None) -> str:
    if url and (m := RESUME_ID.search(url)):
        return m.group(1)
    page.goto(DASHBOARD)
    page.wait_for_load_state("networkidle")
    close_popups(page)
    href = page.get_attribute("a:has-text('View Resume Feedback')", "href") or ""
    if not (m := RESUME_ID.search(href)):
        sys.exit("No scored resume on the VMock dashboard yet - upload one first.")
    return m.group(1)


def read(url: str | None, resume_dir: Path) -> Path:
    with browser.page_at(url or DASHBOARD) as page:
        resume_id = resume_id_from(page, url)
        now = crawl(page, resume_id)
    now |= {"read": date.today().isoformat(), "url": f"{BASE}/resume/{resume_id}/feedback/system"}
    if now["score"] is None:
        sys.exit("VMock's page did not show a score - it may have signed you out. Sign in in the Job Finder window, then try again.")
    folder = OUT / resume_id
    folder.mkdir(parents=True, exist_ok=True)
    changes = compare(now, previous(folder))
    (folder / "feedback.json").write_text(json.dumps(now, indent=1, ensure_ascii=False), encoding="utf-8")
    report = resume_dir / REPORT_NAME
    report.write_text(report_md(now, changes), encoding="utf-8")
    print(f"score {now['score']}/100; " + (f"{len(changes)} change(s) since last read; " if changes else "")
          + f"report: {report}")
    return report


def upload(pdf: Path) -> str:
    """Upload `pdf` and wait for its score page. Returns the new resume's feedback URL."""
    if not pdf.exists():
        sys.exit(f"{pdf} not found")
    with browser.page_at(DASHBOARD) as page:
        page.wait_for_load_state("networkidle")
        close_popups(page)
        newest = page.get_attribute(NEWEST_FEEDBACK, "href") if page.query_selector(NEWEST_FEEDBACK) else None
        page.click("button:has-text('Upload Resume')")
        page.set_input_files("#upload-pdf-input", str(pdf))
        page.wait_for_timeout(1500)
        page.click(".modal.show button:has-text('Next')")
        # VMock scores in place: the dashboard grows a new card at the top and never opens the
        # score page itself (measured 2026-09-24), so wait for the top card to change
        for _ in range(UPLOAD_WAIT_MS // POLL_MS):
            page.wait_for_timeout(POLL_MS)
            href = page.get_attribute(NEWEST_FEEDBACK, "href") if page.query_selector(NEWEST_FEEDBACK) else None
            if href and href != newest and (m := RESUME_ID.search(href)):
                return f"{BASE}/resume/{m.group(1)}/feedback/system"
            if RESUME_ID.search(page.url):
                return f"{BASE}/resume/{RESUME_ID.search(page.url).group(1)}/feedback/system"
        sys.exit("VMock had not finished scoring after 4 minutes - it may need a step in the Job "
                 "Finder window. Once it shows the score, ask for the score to be read.")


def main() -> None:
    ap = argparse.ArgumentParser(description="VMock resume score, read in Job Finder's Chrome")
    steps = ap.add_subparsers(dest="step", required=True)
    p = steps.add_parser("read", help="read a scored resume's feedback (default: the newest one)")
    p.add_argument("url", nargs="?")
    p = steps.add_parser("upload", help="upload a PDF to be scored - spends one upload; needs --yes")
    p.add_argument("pdf", type=Path)
    p.add_argument("--yes", action="store_true", help="the user agreed to spend one of their uploads")
    args = ap.parse_args()
    if args.step == "upload" and not args.yes:
        sys.exit("Uploading spends one of the user's VMock uploads - ask them first, then pass --yes.")
    resume_dir = cfg.resume_path(cfg.load(), "master").parent
    if args.step == "upload":
        read(upload(args.pdf), resume_dir)
    else:
        read(args.url, resume_dir)


if __name__ == "__main__":
    main()
