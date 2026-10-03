"""A system's filler proved on a live form without a user: `apply-form try <link> [--next]`.

Same throwaway Chrome, context-level block and canary as `measure` (apply/lab.py); the system's
own questions, synthetic answers by key / kind only, typed through the SAME per-page path as
`apply-form fill` (form.fill_page). Prints what took, what is the applicant's own step, and every
blocked request with the box being filled when it fired - system docs cite that for "what leaves
the computer, when". Never reads the user's settings or resume: nothing typed here is theirs.
Rules + why: app/docs/apply/apply-systems.md (Add a system).
"""
import re
import sys
import tempfile
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from apply import dom, form, lab, questions, systems

# a person's answers, made up: never the user's. Keys first (a name box is text by kind)
BY_KEY = {"name": "Test Applicant", "legal_name": "Test Applicant", "preferred_name": "Test Applicant",
          "first_name": "Test", "legal_first": "Test", "preferred_first": "Test",
          "last_name": "Applicant", "legal_last": "Applicant",
          "email": "test@example.com", "phone": "555-0100", "location": "New York",
          "linkedin": "https://www.linkedin.com/in/test", "github": "https://example.com", "website": "https://example.com",
          "street": "1 Test St", "city": "New York", "zip": "10001"}
BY_KIND = {"email": "test@example.com", "phone": "555-0100", "url": "https://example.com", "location": "New York",
           "number": "1", "text": "Test answer", "longtext": "Test answer", "yesno": "No"}
# a choice's first option that says something: not a decline, a prefer-not or a self-describe box
DECLINE = re.compile(r"decline|prefer not|rather not|self[- ]?describ|not (?:to )?(?:say|answer|disclose|specify)|"
                     r"(?:do not|don't) wish|choose not|not listed", re.I)
DATE_FORMATS = (("mm/dd/yyyy", "%m/%d/%Y"), ("dd/mm/yyyy", "%d/%m/%Y"), ("yyyy-mm-dd", "%Y-%m-%d"))
# the only buttons --next presses; anything that could send, save or sign is the applicant's
NEXT = {"next", "continue", "next step"}
REFUSE_NEXT = re.compile(r"submit|send|save|finish|complete|apply|sign", re.I)
APPLICANT = "the applicant's own step"


def pick_option(options: list[str]) -> str | None:
    return next((o for o in options if not DECLINE.search(o)), None)


def when(q: dict, day: date) -> str:
    """`day` in the format the box names; a native date input takes ISO; else US month first."""
    t = q["title"].casefold()
    fmt = next((f for said, f in DATE_FORMATS if said in t), None)
    if fmt is None:
        fmt = "%Y-%m-%d" if str(q.get("native") or "").endswith(":date") else "%m/%d/%Y"
    return day.strftime(fmt)


def synthetic(q: dict, today: date | None = None) -> tuple[object, str | None]:
    """(answer, None), or (None, why it is left) - by the question's key and kind, never anyone's facts."""
    kind, key, options = q["kind"], q.get("key"), q.get("options") or []
    if questions.signs(q["title"]):
        return None, f"agreeing, consenting or signing - {APPLICANT}"
    if kind == "file":
        return (True, None) if key in ("resume", "cover_letter") else (None, f"not the resume box - {APPLICANT}")
    if key == "state":
        return next((s for s in ("New York", "NY") if s in options), None if options else "New York"), \
            None if not options or {"New York", "NY"} & set(options) else "no New York / NY option"
    if kind in ("choice", "multichoice"):
        if not options:  # a list read only on the page (Greenhouse's phone Country)
            return ("United States", None) if "country" in q["title"].casefold() else (None, "options not read")
        first = pick_option(options)
        if first is None:
            return None, "only decline options"
        return ([first] if kind == "multichoice" else first), None
    if key in BY_KEY:
        return BY_KEY[key], None
    if kind == "date":
        return when(q, (today or date.today()) + timedelta(days=30)), None
    if kind in BY_KIND:
        return BY_KIND[kind], None
    return None, f"no test answer for {key or kind}"


def test_pdf(path: Path, title: str, lines: list[str]) -> str:
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 90), title, fontsize=16)
    for i, line in enumerate(lines):
        page.insert_text((72, 130 + 18 * i), line, fontsize=11)
    doc.save(path)
    doc.close()
    return str(path)


def files(folder: Path) -> tuple[str, str]:
    """(resume, cover letter): generated one-pagers, in the run's temp dir."""
    resume = test_pdf(folder / "Test_Applicant_Resume.pdf", "Test Applicant - Test Resume",
                      ["test@example.com - 555-0100 - New York", "", "Test Role, Example Co, 2020 - 2025",
                       "- Test answer."])
    letter = test_pdf(folder / "Test_Applicant_Cover_Letter.pdf", "Test Applicant - Test Cover Letter",
                      ["Dear hiring team,", "", "Test answer.", "", "Test Applicant"])
    return resume, letter


def next_ok(text: str) -> bool:
    return " ".join(text.split()).casefold() in NEXT and not REFUSE_NEXT.search(text)


def ask(system, url: str, page) -> tuple[list[dict], str]:
    """The system's own questions: read off the opened tab, else its plain HTTP read. A system that
    reads only through the user's window (none yet) can't be tried: it would open theirs."""
    if hasattr(system, "read"):
        return system.read(page), "read off the page"
    if getattr(system, "QUESTIONS_OVER_HTTP", False):
        return system.questions(url), f"read over HTTP from {system.NAME}'s own job board (outside the browser, a read)"
    sys.exit(f"{system.NAME}: questions() isn't a plain HTTP read and there's no read(page) - add read(page) to try it")


def mark_blocked(qs: list[dict], report: list[tuple], log: list[dict]) -> list[tuple]:
    """A box that didn't take while a write it fired was blocked: say so - the block, not the
    filler, may be why (an upload goes to storage by POST)."""
    title = {q["id"]: q["title"] for q in qs}
    hit = {b["after"] for b in log}
    return [(id, r if r == "ok" or r.startswith(questions.LATER) or f"filling {title[id]!r}" not in hit
             else f"{r} (a write it fired was blocked)") for id, r in report]


def blocked_lines(log: list[dict]) -> list[str]:
    seen = Counter((b["method"], (urlsplit(b["url"]).hostname or "") + urlsplit(b["url"]).path, b["after"])
                   for b in log if b["after"] != "canary")
    return [f"  {m} {where} while {after}" + (f" (x{n})" if n > 1 else "") for (m, where, after), n in seen.items()]


def shown(snap: dict) -> list[dict]:
    # a step-by-step form often keeps every page in the document and hides the rest: the hooks alone
    # match before and after a working Next (local test form, 2026-10-03) - what shows is the page
    return [c for c in snap["controls"] if c["visible"]]


def controls(snap: dict) -> str:
    seen = shown(snap)
    kinds = Counter(c["control"] for c in seen)
    return (f"{len(seen)} controls ({', '.join(f'{k} {n}' for k, n in kinds.most_common())}), "
            f"required {sum(c['required'] for c in seen)}")


def press_next(page, block: lab.Block) -> None:
    """The one visible Next / Continue / Next Step button, pressed once with the block on. Page
    unchanged -> it needed a server write (blocked): said, never worked around."""
    found = [b for b in page.get_by_role("button").filter(visible=True).all()
             if next_ok(b.inner_text() or b.get_attribute("value") or "")]
    if len(found) != 1:
        print(f"--next: {len(found)} visible Next / Continue buttons - pressed none")
        return
    before = dom.snapshot(page)
    block.step = "--next"
    found[0].click(timeout=15000)
    lab.idle(page)
    after = dom.snapshot(page)
    if after["url"] == before["url"] and [c["hook"] for c in shown(after)] == [c["hook"] for c in shown(before)]:
        print("--next: page didn't change - not measurable while blocked (it likely needs a server write)")
        return
    lab.check_page(page)
    print(f"--next: new page {urlsplit(after['url']).path}: {controls(after)}")
    for step in dom.user_steps(after):
        print(f"  {APPLICANT}: {step}")


def trial(url: str, go_next: bool = False, headless: bool = False) -> None:
    system = systems.for_url(url)
    if system is None:
        sys.exit("no system matches this link - try runs a system's own filler; add the system first")
    app_url, per_page = system.application_url(url), getattr(system, "PER_PAGE", False)
    with tempfile.TemporaryDirectory() as tmp, lab.throwaway(headless) as page:
        page.on("dialog", lambda d: d.dismiss())  # a leave-page prompt never holds the tab open
        block, loads = lab.Block(), []
        block.install(page)
        page.on("request", lambda r: loads.append(r.url) if r.is_navigation_request() and r.frame == page.main_frame
                and r.url.startswith("http") and block.step != "canary" else None)
        if failed := lab.canary_failed(lab.canary(page, block)):
            sys.exit(f"{failed}. Nothing tried")
        print(f"canary ok: 0 of {len(lab.KINDS)} kinds of test write got through, each blocked")
        try:
            block.step = "load"
            page.goto(app_url, wait_until="load")
            lab.idle(page)
            lab.check_page(page)
            if said := form.closed(page):
                sys.exit(f"the posting says it's closed (\"{said}\") - try another")
            block.step = "open form"
            form.open_form(page, system, url)
            lab.check_page(page)
        except lab.Refused as e:
            sys.exit(f"refused: {e}")
        except Exception as e:  # READY never showed: a write it needed was blocked, or a wall
            print(f"form never showed ({type(e).__name__}) - not measurable while blocked")
            print("\n".join(["blocked:", *blocked_lines(block.log)]))
            return
        print(f"page loads: {len(loads)} (budget: 10 per site per bead)")
        snap = dom.snapshot(page)
        lab.record_tenants(lab.OUT / "tenants.txt", lab.tenants(url, lab.employer(page), snap))
        try:
            qs, how = ask(system, url, page)
        except SystemExit as e:  # a sign-in wall: the applicant's own step
            print(f"{APPLICANT}: {e}")
            return
        print(f"questions: {len(qs)}, {how}")
        resume, letter = files(Path(tmp))
        left = []
        for q in qs:
            q["answer"], why = synthetic(q)
            if why:
                left.append(f"  left: {q['title']} - {why}")
        shown = set(system.ids_on_page(page)) if per_page else set()
        report, extra = form.fill_page(page, system, qs, resume, letter,
                                       before=lambda q: setattr(block, "step", f"filling {q['title']!r}" if q else "after filling"))
        lines, other = form.page_report(qs, mark_blocked(qs, report, block.log), shown, per_page)
        print("\n".join(lines))
        if other:
            print(f"LATER: {len(other)} question(s) on other pages")
        if extra:
            print(f"on the page, not in the questions: {len(extra)} ({', '.join(extra[:8])})")
        print("\n".join(left + [f"  {APPLICANT}: {step}" for step in dom.user_steps(snap)]))
        if go_next:
            press_next(page, block)
        log = [b for b in block.log if b["after"] != "canary"]
        print("\n".join([f"blocked: {len(log)}", *blocked_lines(log)]))
        print(f"sent: 0 writes - every non-read request blocked at the browser ({len(log)})")
    # throwaway closes Chrome itself (Browser.close: no leave-page prompt); a page.close() of our own
    # here left Chrome running with no tab and the run hung (2026-10-03, a live form, headed)
