"""A system's filler proved on a live form without a user: `apply-form try <link> [--next]`.

Same throwaway Chrome, context-level block and canary as `measure` (apply/lab.py); the system's
own questions, synthetic answers by key / kind only, typed through the SAME per-page path as
`apply-form fill` (form.fill_page). Prints what took, what is the applicant's own step, and every
blocked request with the box being filled when it fired - system docs cite that for "what leaves
the computer, when". Kept as JSON beside measure's files: every request the page made while each box
was filled (reads too), how each box shows its answer after the settle, and - `--upload-errors` - the
page's own words for a wrong-type and an empty resume file. Never reads the user's settings or
resume: nothing typed here is theirs.
Rules + why: app/docs/apply/apply-systems.md (Add a system).
"""
import json
import re
import sys
import tempfile
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import TimeoutError as PlaywrightTimeout

from apply import dom, form, lab, questions, systems

# a person's answers, made up: never the user's. Keys first (a name box is text by kind)
BY_KEY = {"name": "Test Applicant", "legal_name": "Test Applicant", "preferred_name": "Test Applicant",
          "first_name": "Test", "legal_first": "Test", "preferred_first": "Test",
          "last_name": "Applicant", "legal_last": "Applicant",
          "email": "test@example.com", "phone": "555-0100", "location": "New York",
          "linkedin": "https://www.linkedin.com/in/test", "github": "https://example.com", "website": "https://example.com",
          "portfolio": "https://example.com",
          "street": "1 Test St", "city": "New York", "zip": "10001"}
EDUCATION = {"school": "New York University", "degree": "Bachelor of Science", "discipline": "Economics",
             "school_start_month": "September", "school_start_year": "2016", "school_end_month": "May",
             "school_end_year": "2020"}
BY_KIND = {"email": "test@example.com", "phone": "555-0100", "url": "https://example.com", "location": "New York",
           "number": "1", "text": "Test answer", "longtext": "Test answer", "yesno": "No"}
# a choice's first option that says something: not a decline, a prefer-not or a self-describe box
DECLINE = re.compile(r"decline|prefer not|rather not|self[- ]?describ|not (?:to )?(?:say|answer|disclose|specify)|"
                     r"(?:do not|don't) wish|choose not|not listed", re.I)
DATE_FORMATS = (("mm/dd/yyyy", "%m/%d/%Y"), ("dd/mm/yyyy", "%d/%m/%Y"), ("yyyy-mm-dd", "%Y-%m-%d"))
# the only buttons --next presses; anything that could send, save or sign is the applicant's
NEXT = {"next", "continue", "next step"}
REFUSE_NEXT = re.compile(r"submit|send|save|finish|complete|apply|sign", re.I)
NEXT_NAME = re.compile(r"^\s*(?:next|continue|next\s+step)\s*$", re.I)
APPLICANT = "the applicant's own step"
# requests the page makes itself (not its pictures, styles, scripts): what a box sends as it is filled
SENT_TYPES = {"xhr", "fetch", "ping", "eventsource", "websocket", "other"}
# how a box shows its answer: its words, its boxes' values, the chosen radio / tick / button / option
READOUT = """e => { const t = x => (x.innerText || x.textContent || '').replace(/\\s+/g, ' ').trim();
  const ticks = [...e.querySelectorAll('input[type=radio], input[type=checkbox]')];
  return {text: t(e).slice(0, 300),
    boxes: [...e.querySelectorAll('input:not([type=hidden]):not([type=radio]):not([type=checkbox]), textarea, select')]
      .map(i => ({tag: i.tagName.toLowerCase(), type: i.type || '', role: i.getAttribute('role') || '',
                  value: (i.value || '').slice(0, 120), accept: i.getAttribute('accept') || ''})),
    ticked: ticks.filter(i => i.checked).map(i => (i.labels && i.labels[0] ? t(i.labels[0]) : i.value).slice(0, 80)),
    ticks: ticks.length,
    pressed: [...e.querySelectorAll('[aria-pressed]')].map(b => ({name: t(b).slice(0, 40), pressed: b.getAttribute('aria-pressed')})),
    selected: [...e.querySelectorAll('[aria-selected=true], [aria-checked=true]')].map(x => t(x).slice(0, 80))}; }"""


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
        return None, f"{questions.why_on_page(q['title'])} - {APPLICANT}"
    if kind == "file":
        return (True, None) if key in ("resume", "cover_letter") else (None, f"not the resume box - {APPLICANT}")
    if key in EDUCATION:  # before choices: a school search has no options to read
        return EDUCATION[key], None
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


def probe_files(folder: Path) -> list[tuple[str, str]]:
    """(what, path): a picture where a resume goes, and an empty PDF - mistakes a person makes."""
    png = folder / "Test_Applicant_Photo.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + bytes(64))
    empty = folder / "Test_Applicant_Empty.pdf"
    empty.write_bytes(b"")
    return [("wrong type (.png)", str(png)), ("empty file (0 bytes)", str(empty))]


def new_lines(before: str, after: str, keep: int = 10) -> list[str]:
    """Lines the page shows now that it didn't before: an error it raised."""
    had = {" ".join(x.split()) for x in before.splitlines()}
    out = [" ".join(x.split())[:200] for x in after.splitlines()]
    return list(dict.fromkeys(x for x in out if x and x not in had))[:keep]


def body_text(page) -> str:
    try:
        return page.evaluate("() => document.body.innerText || ''")
    except Exception:
        return ""


def upload_errors(page, system, qs: list[dict], folder: Path, block: lab.Block) -> list[dict]:
    """The page's own words for each mistaken resume file, chosen in the resume box before the real
    one. With every write blocked, words that come only after a send are the block's, not the page's:
    `blocked` says whether one fired."""
    resume = next((q for q in qs if q["kind"] == "file" and q.get("key") == "resume"), None)
    if resume is None:
        return [{"probe": "none", "said": ["no resume box in the questions"]}]
    out = []
    for what, path in probe_files(folder):
        before, step = body_text(page), f"upload probe: {what}"
        block.step = step
        result = form.put(page, system, resume | {"answer": True}, path)
        page.wait_for_timeout(form.SETTLE_MS)
        out.append({"probe": what, "fill": result, "said": new_lines(before, body_text(page)),
                    "blocked": [f"{b['method']} {urlsplit(b['url']).hostname}{urlsplit(b['url']).path}"
                                for b in block.log if b["after"] == step]})
    return out


def readout(page, system, qs: list[dict]) -> list[dict]:
    """How each box shows its answer, read off the page: systems with `box_of(page, q)` only."""
    if not hasattr(system, "box_of"):
        return []
    out = []
    for q in qs:
        try:
            shows = system.box_of(page, q).evaluate(READOUT, timeout=3000)
        except Exception as e:
            shows = {"error": type(e).__name__}
        out.append({"id": q["id"], "title": q["title"], "kind": q["kind"], "native": q.get("native"),
                    "answer": q.get("answer"), "shows": shows})
    return out


def keep(record: dict, host: str) -> Path:
    out = lab.OUT / f"{host}-try-{datetime.now():%Y%m%d-%H%M%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"written: {out}")
    return out


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


# what sits on the button's centre: the dialog / banner it belongs to, by tag, id, role and its first line
COVERING = """b => { b.scrollIntoView({block: 'center'}); const r = b.getBoundingClientRect();
  const e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  if (!e || b === e || b.contains(e)) return '';
  const box = e.closest('dialog,[role=dialog],[role=alertdialog],[aria-modal=true],[id*=onetrust],[class*=modal],[class*=cookie]') || e;
  const head = box.getAttribute('aria-label') || (box.querySelector('h1,h2,h3,h4,[role=heading]') || box).innerText || '';
  const line = head.trim().split('\\n')[0].slice(0, 60);
  return box.tagName.toLowerCase() + (box.id ? '#' + box.id : '') + (box.getAttribute('role') ? ' role=' + box.getAttribute('role') : '')
    + (line ? ` "${line}"` : ''); }"""


def covering(button) -> str:
    """Names what covers the button, '' when nothing does or the page won't say."""
    try:
        return f"covered by {said}" if (said := button.evaluate(COVERING)) else ""
    except Exception:
        return ""


def press_next(page, block: lab.Block) -> None:
    """The one visible Next / Continue / Next Step button, pressed once with the block on. Page
    unchanged -> it needed a server write (blocked): said, never worked around."""
    # by accessible name: a web component's label is slotted text, its inner <button> reads ""
    # (SmartRecruiters' Spark buttons, 2026-10-03)
    found = page.get_by_role("button", name=NEXT_NAME).filter(visible=True).all()
    if len(found) != 1:
        print(f"--next: {len(found)} visible Next / Continue buttons - pressed none")
        return
    before = dom.snapshot(page)
    block.step = "--next"
    try:
        found[0].click(timeout=15000)
    except PlaywrightTimeout:  # a layer over the form's foot took the pointer (SmartRecruiters, 2026-10-03)
        try:
            found[0].focus()
            found[0].press("Enter")
        except Exception as e:  # a dialog / cookie banner over it (Paylocity's upload dialog + OneTrust, 2026-10-03)
            print(f"--next: Next not reachable while blocked: {covering(found[0]) or type(e).__name__}")
            return
    except Exception as e:
        print(f"--next: Next not reachable while blocked: {covering(found[0]) or type(e).__name__}")
        return
    lab.idle(page)
    after = dom.snapshot(page)
    if after["url"] == before["url"] and [c["hook"] for c in shown(after)] == [c["hook"] for c in shown(before)]:
        print("--next: page didn't change - not measurable while blocked (it likely needs a server write)")
        return
    lab.check_page(page)
    print(f"--next: new page {urlsplit(after['url']).path}: {controls(after)}")
    for step in dom.user_steps(after):
        print(f"  {APPLICANT}: {step}")


def trial(url: str, go_next: bool = False, headless: bool = False, upload: bool = True, probe: bool = False) -> None:
    """`upload=False`: file boxes left - an upload goes out on choosing the file on some systems, and
    blocked it can take the form down with it (Workable, 2026-10-03): the rest is then tried without it.
    `probe`: a wrong-type + an empty file in the resume box first (upload_errors)."""
    system = systems.for_url(url)
    if system is None:
        sys.exit("no system matches this link - try runs a system's own filler; add the system first")
    app_url, per_page = system.application_url(url), getattr(system, "PER_PAGE", False)
    with tempfile.TemporaryDirectory() as tmp, lab.throwaway(headless) as page:
        page.on("dialog", lambda d: d.dismiss())  # a leave-page prompt never holds the tab open
        block, loads, sent = lab.Block(), [], []
        block.install(page)
        page.on("request", lambda r: loads.append(r.url) if r.is_navigation_request() and r.frame == page.main_frame
                and r.url.startswith("http") and block.step != "canary" else None)
        page.on("request", lambda r: sent.append({"method": r.method, "url": (urlsplit(r.url).hostname or "") + urlsplit(r.url).path[:120],
                                                  "type": r.resource_type, "op": parse_qs(urlsplit(r.url).query).get("op", [""])[0],
                                                  "after": block.step})
                if r.resource_type in SENT_TYPES and r.url.startswith("http") and block.step not in ("canary", "load") else None)
        test = lab.canary(page, block)
        if failed := lab.canary_failed(test):
            sys.exit(f"{failed}. Nothing tried")
        print(f"canary ok: 0 of {len(lab.KINDS)} kinds of test write got through, each blocked")
        record = {"url": url, "system": system.NAME, "canary": test, "upload": upload}

        def done(**more) -> None:
            log = [b for b in block.log if b["after"] != "canary"]
            keep(record | more | {"loads": len(loads), "blocked": log, "named_reads": block.passed, "requests": sent},
                 urlsplit(url).hostname or "page")
        try:
            block.step = "load"
            page.goto(app_url, wait_until="load")
            lab.idle(page)
            lab.check_page(page)
            if said := form.closed(page, system, url):
                sys.exit(f"{said} - try another")
            block.step = "open form"
            form.open_form(page, system, url)
            lab.check_page(page)
        except lab.Refused as e:
            sys.exit(f"refused: {e}")
        except Exception as e:  # READY never showed: a write it needed was blocked, or a wall
            print(f"form never showed ({type(e).__name__}) - not measurable while blocked")
            print("\n".join(["blocked:", *blocked_lines(block.log)]))
            print(f"page loads: {len(loads)} (budget: 10 per site per bead)")
            done(form_shown=False, page_text=body_text(page)[:lab.TEXT_KEEP])
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
            q["answer"], why = synthetic(q) if upload or q["kind"] != "file" else (None, "upload left (--no-upload)")
            if why:
                left.append(f"  left: {q['title']} - {why}")
        shown = set(system.ids_on_page(page)) if per_page else set()
        probes = upload_errors(page, system, qs, Path(tmp), block) if probe else []
        for p in probes:
            print(f"upload probe, {p['probe']}: [{p.get('fill', '')}] page says: {' | '.join(p['said']) or 'nothing new'}"
                  + (f"; blocked: {', '.join(p['blocked'])}" if p.get("blocked") else ""))
        report, extra = form.fill_page(page, system, qs, resume, letter,
                                       before=lambda q: setattr(block, "step", f"filling {q['title']!r}" if q else "after filling"))
        lines, other = form.page_report(qs, mark_blocked(qs, report, block.log), shown, per_page)
        print("\n".join(lines))
        if other:
            print(f"LATER: {len(other)} question(s) on other pages")
        if extra:
            print(f"on the page, not in the questions: {len(extra)} ({', '.join(extra[:8])})")
        print("\n".join(left + [f"  {APPLICANT}: {step}" for step in dom.user_steps(snap)]))
        shows = readout(page, system, qs)
        if go_next:
            press_next(page, block)
        done(form_shown=True, questions=[{k: q.get(k) for k in ("id", "title", "kind", "native", "required", "key", "answer")} for q in qs],
             report=dict(report), extra=extra, left=left, probes=probes, readout=shows)
        log = [b for b in block.log if b["after"] != "canary"]
        print("\n".join([f"blocked: {len(log)}", *blocked_lines(log)]))
        passed = ", ".join(sorted({p["op"] for p in block.passed}))
        print(f"sent: 0 writes - every non-read request blocked at the browser ({len(log)})"
              + (f"; named reads let through: {len(block.passed)} ({passed})" if passed else ""))
    # throwaway closes Chrome itself (Browser.close: no leave-page prompt); a page.close() of our own
    # here left Chrome running with no tab and the run hung (2026-10-03, a live form, headed)
