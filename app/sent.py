"""Did the user already send it? Read off the browser history on this computer, for jobs not yet
marked applied - users forget to say, or apply to several at once.

Local only: each browser's history file is copied and read here, nothing is fetched, and only
visits matching a job in progress are printed. A sent page settles it; most systems show none,
so the rest is "likely not sent" or "can't tell" w/ where to look. Facts: app/docs/apply/sent.md.
"""
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import cfg

CHROME_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)
SAFARI_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)
# Chromium-family browsers keep one History file per profile (Default, Profile 1 ...)
CHROMIUM = {
    "darwin": ("~/Library/Application Support", ["Google/Chrome", "Google/Chrome Beta", "Chromium",
               "BraveSoftware/Brave-Browser", "Microsoft Edge", "Arc/User Data", "Vivaldi"]),
    "win32": (os.environ.get("LOCALAPPDATA", ""), ["Google/Chrome/User Data", "BraveSoftware/Brave-Browser/User Data",
              "Microsoft/Edge/User Data", "Chromium/User Data", "Vivaldi/User Data"]),
    "linux": ("~/.config", ["google-chrome", "chromium", "BraveSoftware/Brave-Browser", "microsoft-edge", "vivaldi"]),
}
FIREFOX = {"darwin": "~/Library/Application Support/Firefox/Profiles",
           "win32": os.path.join(os.environ.get("APPDATA", ""), "Mozilla/Firefox/Profiles"),
           "linux": "~/.mozilla/firefox"}
SAFARI = "~/Library/Safari/History.db"


@dataclass(frozen=True)
class System:
    name: str
    host: str
    # page the system loads only after Submit; None = it shows none (same address before + after)
    sent: re.Pattern | None
    # where a signed-in user sees what they sent, or None
    account: str | None


# measured 2026-09-30 on real histories; sent page seen for Greenhouse (2 jobs) and Workday (1)
SYSTEMS = [
    System("Greenhouse", "greenhouse.io", re.compile(r"/jobs/\d+/confirmation"),
           "my.greenhouse.io, Applications tab - lists only what was sent while signed in there"),
    System("Workday", "myworkdayjobs.com", re.compile(r"/jobTasks/completed/application"),
           "Candidate Home on that employer's Workday site"),
    System("Ashby", "ashbyhq.com", None, None),
    System("UKG", "ultipro.com", None, "My Presence, Applications on that employer's UKG site, signed in"),
    System("Rippling", "rippling.com", None, None),
]
# Workday's sent page names no job: it counts for the job whose form was open just before it
WORKDAY_PAIR = timedelta(hours=2)
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
NUMBER_ID = re.compile(r"(?:/jobs/|gh_jid=|opportunityId=|_)(\d{6,})")
GENERIC = {"the", "and", "inc", "llc", "group", "technologies", "technology", "labs", "company"}


@dataclass(frozen=True)
class Visit:
    at: datetime
    url: str
    title: str
    browser: str


def system_of(url: str) -> System | None:
    host = re.sub(r"^https?://", "", url).split("/")[0].casefold()
    return next((s for s in SYSTEMS if host == s.host or host.endswith("." + s.host)), None)


def norm(text: str | None) -> str:
    return " ".join(re.sub(r"[^0-9a-z]+", " ", (text or "").casefold()).split())


def ids(url: str | None) -> set[str]:
    """Ids a job's own link carries (posting uuid, Greenhouse job id, UKG opportunity id); a
    visit carrying one is that job, whichever page or browser it was."""
    url = url or ""
    # UKG links carry the job board's uuid too, shared by every job of that employer
    one = re.search(r"opportunityId=(" + UUID.pattern + ")", url, re.I)
    uuids = [one.group(1)] if one else UUID.findall(url)
    return {u.casefold() for u in uuids} | set(NUMBER_ID.findall(url))


def company_word(company: str | None) -> str:
    words = [w for w in norm(company).split() if w not in GENERIC and len(w) >= 3]
    return words[0] if words else ""


def matches(job: dict, v: Visit) -> bool:
    """Same id as the job's link, or company in the address + job title in the page title
    (Workday and Rippling pages carry neither id)."""
    url = v.url.casefold()
    if any(i in url for i in ids(job.get("url"))):
        return True
    word, title = company_word(job.get("company")), norm(job.get("title"))
    return bool(word and title and word in norm(v.url) and title in norm(v.title))


def verdict(job: dict, visits: list[Visit]) -> tuple[str, str]:
    """sent | likely not sent | can't tell | no visits, w/ why in plain words."""
    mine = sorted((v for v in visits if matches(job, v)), key=lambda v: v.at)
    for v in mine:
        s = system_of(v.url)
        if s and s.sent and s.sent.search(v.url):
            return "sent", f"{s.name} sent page {v.at:%Y-%m-%d} ({v.browser})"
    for done in (v for v in visits if system_of(v.url) is SYSTEMS[1] and SYSTEMS[1].sent.search(v.url)):
        host = done.url.split("/")[2]
        if any(v.url.split("/")[2] == host and "/apply" in v.url and timedelta(0) <= done.at - v.at <= WORKDAY_PAIR
               for v in mine):
            return "sent", f"Workday sent page {done.at:%Y-%m-%d} ({done.browser}), right after this job's form"
    if not mine:
        return "no visits", "never opened in a browser I can read"
    last = mine[-1]
    s = next((system_of(v.url) for v in reversed(mine) if system_of(v.url)), None)
    opened = f"last opened {last.at:%Y-%m-%d} ({last.browser})"
    if s and s.sent:
        return "likely not sent", f"{opened}; {s.name} shows a sent page after Submit and none was seen"
    if s is None:
        return "can't tell", f"{opened}; not a site I know the sent page of - check for the confirmation email"
    where = f"check {s.account}, or the confirmation email" if s.account else "check for the confirmation email"
    return "can't tell", f"{opened}; {s.name} shows no sent page - {where}"


def history_files(platform: str = sys.platform, home: Path = Path.home()) -> list[tuple[str, Path, str]]:
    """(browser, file, kind) for every history on this computer, Job Finder's window included."""
    key = "linux" if platform.startswith("linux") else platform
    expand = lambda p: Path(str(p).replace("~", str(home), 1))  # noqa: E731
    out = [("Job Finder window", f, "chromium") for f in sorted((cfg.DATA / "apply-browser").glob("*/History"))]
    if key in CHROMIUM and CHROMIUM[key][0]:
        base, browsers = CHROMIUM[key]
        for b in browsers:
            label = b.split("/")[-2 if b.endswith("User Data") else -1].removesuffix("-Browser")
            out += [(label, f, "chromium") for f in sorted(expand(Path(base) / b).glob("*/History"))]
    if key in FIREFOX and FIREFOX[key]:
        out += [("Firefox", f, "firefox") for f in sorted(expand(FIREFOX[key]).glob("*/places.sqlite"))]
    if key == "darwin" and expand(SAFARI).exists():
        out.append(("Safari", expand(SAFARI), "safari"))
    return out


QUERIES = {
    "chromium": ("SELECT v.visit_time, u.url, u.title FROM visits v JOIN urls u ON u.id = v.url",
                 lambda t: CHROME_EPOCH + timedelta(microseconds=t)),
    "firefox": ("SELECT v.visit_date, p.url, p.title FROM moz_historyvisits v JOIN moz_places p ON p.id = v.place_id",
                lambda t: datetime.fromtimestamp(t / 1e6, timezone.utc)),
    "safari": ("SELECT v.visit_time, i.url, v.title FROM history_visits v JOIN history_items i ON i.id = v.history_item",
               lambda t: SAFARI_EPOCH + timedelta(seconds=t)),
}


def read(browser: str, path: Path, kind: str) -> list[Visit]:
    """Copy first: an open browser locks its history file."""
    sql, to_time = QUERIES[kind]
    with tempfile.TemporaryDirectory() as tmp:
        for suffix in ("", "-wal"):
            if Path(f"{path}{suffix}").exists():
                shutil.copy(f"{path}{suffix}", Path(tmp) / f"h{suffix}")
        conn = sqlite3.connect(Path(tmp) / "h")
        try:
            rows = conn.execute(sql).fetchall()
        finally:
            conn.close()
    return [Visit(to_time(t).astimezone(), url, title or "", browser) for t, url, title in rows if t and url]


def all_visits() -> tuple[list[Visit], list[str]]:
    """Every readable visit + the browsers that could not be read (Safari needs Full Disk Access)."""
    visits, unread = [], []
    for browser, path, kind in history_files():
        try:
            visits += read(browser, path, kind)
        except (OSError, sqlite3.Error):
            unread.append(browser)
    return visits, sorted(set(unread))
