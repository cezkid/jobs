"""Fill an Ashby job application (jobs.ashbyhq.com) in the user's own Chrome window - never Submit.

`prepare <slug> <url>` reads the form's questions from Ashby's public job board and writes
`<job folder>/.data/ashby-answers.json`: contact boxes answered from the resume, every other
question left blank for the AI to fill with the user. `fill <slug>` opens Chrome on the form,
types each answer, reports what took, then lets go - the window stays open for the user to check
and click Submit. Measured facts and why each rule exists: app/docs/ashby.md.
"""
import argparse
import json
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

import cfg
from resume import render, schema, tailor

GRAPHQL = "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobPosting"
QUERY = """query ApiJobPosting($organizationHostedJobsPageName: String!, $jobPostingId: String!) {
  jobPosting(organizationHostedJobsPageName: $organizationHostedJobsPageName, jobPostingId: $jobPostingId) {
    title applicationForm { sections { fieldEntries { ... on FormFieldEntry { isRequired field } } } } } }"""
POSTING_URL = re.compile(r"https?://jobs\.ashbyhq\.com/([^/?#]+)/([0-9a-f-]{36})", re.I)
ANSWERS = "ashby-answers.json"
BROWSER_PROFILE = cfg.DATA / "apply-browser"  # own Chrome profile: sign-ins stay private, never the user's main one
CHROME = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
]
# questions that are the user's to answer, never guessed (docs/ashby.md, job-apply hard limits)
ASK = "ask the user"


def parse_url(url: str) -> tuple[str, str]:
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not a jobs.ashbyhq.com posting link: {url}")
    return m.group(1), m.group(2)


def application_url(url: str) -> str:
    org, posting = parse_url(url)
    return f"https://jobs.ashbyhq.com/{org}/{posting}/application"


def fetch_form(url: str) -> list[dict]:
    org, posting = parse_url(url)
    r = httpx.post(GRAPHQL, timeout=30, json={
        "operationName": "ApiJobPosting", "query": QUERY,
        "variables": {"organizationHostedJobsPageName": org, "jobPostingId": posting}})
    r.raise_for_status()
    job = (r.json().get("data") or {}).get("jobPosting")
    if not job:
        raise ValueError("posting not found - it may have closed")
    fields = []
    for section in job["applicationForm"]["sections"]:
        for entry in section["fieldEntries"]:
            f = entry.get("field")
            if not f or f.get("isDeactivated"):
                continue
            fields.append({
                "path": f["path"], "title": f["title"], "type": f["type"], "required": bool(entry.get("isRequired")),
                "options": [v["label"] for v in f.get("selectableValues") or [] if not v.get("isArchived")],
            })
    return fields


def link(contact: dict, host: str) -> str:
    for url in contact.get("links") or []:
        if host in url.casefold():
            return url if url.startswith("http") else "https://www." + url.removeprefix("www.")
    return ""


def work_permit(field: dict, config: dict):
    """Setup's two work-permit answers, only for the same US question asked the same way (job-apply limits)."""
    wa, title = config.get("work_authorization") or {}, field["title"].casefold()
    if field["type"] != "Boolean":
        return None
    if "authorized to work in the u" in title and "without restriction" in title:
        return wa.get("authorized_us")
    if "sponsorship" in title and "future" in title and ("u.s." in title or "us" in title.split()):
        return wa.get("needs_sponsorship")
    return None


def from_resume(field: dict, contact: dict) -> str:
    """Answer only what the resume states outright; everything else is the user's (via the AI)."""
    title, kind = field["title"].casefold(), field["type"]
    if field["path"] == "_systemfield_name":
        return contact.get("name", "")
    if kind == "Email" or field["path"] == "_systemfield_email":
        return contact.get("email", "")
    if kind == "Phone":
        return contact.get("phone", "")
    if kind == "String" and "linkedin" in title:
        return link(contact, "linkedin.")
    if kind == "String" and "github" in title:
        return link(contact, "github.")
    return ""


def draft(fields: list[dict], contact: dict, old: list[dict] | None = None, config: dict | None = None) -> list[dict]:
    """Form questions + answers. Answers already written (by an earlier prepare or the AI) are kept."""
    kept = {a["path"]: a for a in old or [] if a.get("answer") not in (None, "", [])}
    out = []
    for f in fields:
        if f["path"] in kept:
            out.append({**f, "answer": kept[f["path"]]["answer"], "source": kept[f["path"]].get("source", "")})
            continue
        permit = work_permit(f, config or {})
        if permit is not None:
            out.append({**f, "answer": "Yes" if permit else "No", "source": "search settings - name it to the user"})
            continue
        answer = from_resume(f, contact)
        out.append({**f, "answer": answer or None, "source": "resume" if answer else ASK})
    return out


def missing(answers: list[dict]) -> list[dict]:
    return [a for a in answers if a["required"] and a.get("answer") in (None, "", [])]


def job_dir(config: dict, slug: str) -> Path:
    found = tailor.find_job_dir(cfg.resume_path(config, "jobs_dir"), slug)
    if found is None:
        sys.exit(f"no job folder for {slug}; run tailor first")
    return found


def prepare(slug: str, url: str) -> None:
    config = cfg.load()
    master = schema.load(cfg.resume_path(config, "master"))
    folder = job_dir(config, slug)
    out = folder / tailor.JOB_DATA / ANSWERS
    old = json.loads(out.read_text(encoding="utf-8"))["answers"] if out.exists() else None
    answers = draft(fetch_form(url), master["contact"], old, config)
    resume = folder / render.file_name(master)
    out.write_text(json.dumps({"url": application_url(url), "resume_file": str(resume) if resume.exists() else None,
                               "answers": answers}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out}: {len(answers)} questions, {len(missing(answers))} required still blank")
    for a in answers:
        state = "ok" if a["answer"] not in (None, "", []) else ("NEEDED" if a["required"] else "optional")
        opts = f" options={a['options']}" if a["options"] else ""
        print(f"  [{state}] {a['type']}: {a['title']}{opts}")
    print("Write answers into the file (File type: answer = true only after the user said yes to uploading), "
          f"then: uv run app/jobs.py apply-ashby fill {slug}")


def chrome() -> str:
    for c in CHROME:
        if Path(c).exists() or shutil.which(c):
            return shutil.which(c) or c
    sys.exit("Google Chrome not found - install Chrome, or fill the form by hand from the answers file")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def open_chrome(url: str) -> int:
    """A plain Chrome window (no automation banner or flags) we attach to, fill, and let go of."""
    port = free_port()
    BROWSER_PROFILE.mkdir(parents=True, exist_ok=True)
    subprocess.Popen([chrome(), f"--remote-debugging-port={port}", f"--user-data-dir={BROWSER_PROFILE}",
                      "--no-first-run", "--no-default-browser-check", url],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(60):
        try:
            httpx.get(f"http://127.0.0.1:{port}/json/version", timeout=1)
            return port
        except httpx.HTTPError:
            time.sleep(0.5)
    sys.exit("Chrome did not start")


def entry(page, path: str):
    return page.locator(f'[data-field-path="{path}"]').first


def put_text(box, value: str) -> str:
    field = box.locator("textarea, input:not([type=file]):not([type=checkbox]):not([type=radio])").first
    field.fill(str(value))
    field.blur()
    return "ok" if field.input_value() == str(value) else "FAIL value did not stick"


def put_location(box, value: str) -> str:
    field = box.locator("input[role=combobox], input").first
    field.fill("")
    field.press_sequentially(value, delay=60)
    options = box.page.locator("[role=option]")
    try:
        options.first.wait_for(timeout=8000)
    except Exception:
        return f"ASK no place matched '{value}'"
    texts = options.all_inner_texts()
    wanted = value.split(",")[0].strip().casefold()
    pick = next((i for i, t in enumerate(texts) if t.casefold().startswith(wanted)), 0)
    options.nth(pick).click()
    return "ok" if pick == 0 or texts[pick].casefold().startswith(wanted) else f"ASK picked '{texts[pick]}'"


def put_yes_no(box, value) -> str:
    word = "Yes" if value in (True, "Yes", "yes", "true") else "No"
    box.get_by_role("button", name=word, exact=True).click()
    ticked = box.locator("input[type=checkbox]").first
    return "ok" if ticked.count() == 0 or ticked.is_checked() == (word == "Yes") else "FAIL choice did not stick"


def put_choice(box, value) -> str:
    wanted = value if isinstance(value, list) else [value]
    for v in wanted:
        label = box.locator("label", has_text=re.compile(rf"^\s*{re.escape(str(v))}\s*$"))
        if label.count():
            label.first.click()
            continue
        combo = box.locator("input[role=combobox]")  # long lists show as a search box
        if not combo.count():
            return f"FAIL no option '{v}'"
        combo.first.fill(str(v))
        option = box.page.get_by_role("option", name=str(v), exact=True)
        if not option.count():
            return f"FAIL no option '{v}'"
        option.first.click()
    return "ok"


def put_file(box, path: str) -> str:
    box.locator("input[type=file]").first.set_input_files(path)
    try:
        box.get_by_text(Path(path).name).first.wait_for(timeout=20000)
    except Exception:
        return "ASK upload not confirmed on page - check the resume box"
    return "ok"


def fill_one(page, a: dict, resume_file: str | None) -> str:
    box = entry(page, a["path"])
    if not box.count():
        return "FAIL question not on page"
    box.scroll_into_view_if_needed()
    kind, value = a["type"], a["answer"]
    if kind == "File":
        return put_file(box, resume_file) if value is True and resume_file else "skipped - upload not approved"
    if a["path"] == "_systemfield_location" or kind == "Location":
        return put_location(box, value)
    if kind == "Boolean":
        return put_yes_no(box, value)
    if kind in ("ValueSelect", "MultiValueSelect"):
        return put_choice(box, value)
    return put_text(box, value)


def fill(slug: str) -> None:
    from playwright.sync_api import sync_playwright

    config = cfg.load()
    saved = job_dir(config, slug) / tailor.JOB_DATA / ANSWERS
    if not saved.exists():
        sys.exit(f"no answers yet; run: uv run app/jobs.py apply-ashby prepare {slug} <link>")
    data = json.loads(saved.read_text(encoding="utf-8"))
    if gaps := missing(data["answers"]):
        sys.exit("required questions still blank: " + "; ".join(a["title"] for a in gaps))
    port = open_chrome(data["url"])
    report = []
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        page = next((pg for c in browser.contexts for pg in c.pages if "ashbyhq.com" in pg.url), None)
        if page is None:
            page = browser.contexts[0].new_page()
            page.goto(data["url"])
        page.locator("[data-field-path]").first.wait_for(timeout=30000)
        # resume first: a later upload must never re-trigger anything over typed answers
        order = sorted(data["answers"], key=lambda a: a["type"] != "File")
        for a in order:
            if a.get("answer") in (None, "", []):
                continue
            try:
                result = fill_one(page, a, data.get("resume_file"))
            except Exception as e:  # one stuck box never stops the rest
                result = f"FAIL {type(e).__name__}: {str(e).splitlines()[0][:120]}"
            report.append((a["title"], result))
        on_page = page.eval_on_selector_all("[data-field-path]", "es => es.map(e => e.dataset.fieldPath)")
        extra = [p for p in on_page if p not in {a["path"] for a in data["answers"]}]
        # disconnect only: Chrome stays open with the filled form; Submit is the user's click
    for title, result in report:
        print(f"  [{result}] {title}")
    if extra:
        print(f"  {len(extra)} question(s) on the page not in the answers file - user answers them on screen")
    print("Chrome is open on the filled form. Nothing is sent until the user clicks Submit.")


def main() -> None:
    ap = argparse.ArgumentParser(description="fill an Ashby job application in Chrome, stopping before Submit")
    sub = ap.add_subparsers(dest="step", required=True)
    p = sub.add_parser("prepare", help="read the form's questions, answer what the resume states")
    p.add_argument("slug")
    p.add_argument("url")
    f = sub.add_parser("fill", help="open Chrome and fill the form from the answers file")
    f.add_argument("slug")
    args = ap.parse_args()
    prepare(args.slug, args.url) if args.step == "prepare" else fill(args.slug)


if __name__ == "__main__":
    main()
