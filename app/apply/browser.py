"""The user's application window: a plain Chrome with Job Finder's own profile that we attach to,
fill, and let go of. Shared by every application system.

No automation flag: the user is at this window and does every Submit, CAPTCHA and sign-in
themselves, so the page should behave as it does for them in any Chrome (the automation flag and
banner change page behaviour). Job Finder never hides itself from a site's checks beyond that. The profile lives in `.data/` - sign-ins stay on
this computer and never touch the user's everyday Chrome. Facts: app/docs/apply/apply-systems.md.
"""
import contextlib
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

import httpx

import cfg
import locks

PROFILE = cfg.DATA / "apply-browser"
# port we started Chrome on. Never --remote-debugging-port=0: Chrome then sets
# navigator.webdriver = true on every page (measured 2026-09, Chrome 154); a fixed port leaves it false
PORT_FILE = PROFILE / "job-finder-port"
# held (flock) by the one watcher that quits Job Finder's Chrome once its last window closes (watch)
WATCH_FILE = PROFILE / "job-finder-watch"
WATCH_POLL_S, IDLE_POLLS = 5, 3  # quit ~10-15 s after the last window closes
CHROME = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    # Chrome installed w/o admin rights lands per user
    str(Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe"),
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    # Chromium w/ same debugging protocol, on every Windows 10/11 => no Chrome install asked of user
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def chrome() -> str:
    for c in CHROME:
        if shutil.which(c):
            return shutil.which(c)
        if Path(c).exists():
            return c
    sys.exit("Google Chrome not found - install Chrome, or fill the form by hand from the answers file")


def live_port() -> int | None:
    """Port of a Job Finder Chrome already open, so a second application reuses its window:
    starting another Chrome on the same profile only hands the link to the first one."""
    try:
        port = int(PORT_FILE.read_text().split()[0])
    except (OSError, ValueError, IndexError):
        port = None
    if port is None or not answers(port):
        # file gone while Chrome still runs (seen 2026-09-24), or naming a Chrome that handed its
        # link to the one already open: without this, every next start only hands the link over
        # and waits on a port that never answers, until the user closes Chrome
        port = running_port()
        if port is None or not answers(port):
            return None
        PORT_FILE.write_text(str(port))
    return port


def answers(port: int) -> bool:
    try:
        httpx.get(f"http://127.0.0.1:{port}/json/version", timeout=1)
        return True
    except httpx.HTTPError:
        return False


def running() -> tuple[int, int] | None:
    """(process id, debugging port) off the command line of a Chrome running on Job Finder's profile."""
    if sys.platform == "win32":
        command = ["powershell", "-NoProfile", "-Command",
                   "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe' OR Name='msedge.exe'\" | "
                   "ForEach-Object { \"$($_.ProcessId) $($_.CommandLine)\" }"]
    else:
        command = ["ps", "-axww", "-o", "pid=,command="]
    try:
        listed = subprocess.run(command, capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for line in listed.splitlines():
        if str(PROFILE) in line and (m := re.search(r"^\s*(\d+)\s.*--remote-debugging-port=(\d+)", line)):
            return int(m.group(1)), int(m.group(2))
    return None


def running_port() -> int | None:
    """Debugging port off the command line of a Chrome running on Job Finder's profile."""
    return found[1] if (found := running()) else None


def restart() -> None:
    """Close Job Finder's Chrome so the next tab starts a fresh one. Its port still answers but
    refuses Playwright's attach ("Browser context management is not supported" - seen 2026-10-29
    on a Chrome 156 window open ~6 h with the Claude in Chrome add-on in its profile): no fill can
    reach it, and the user was left closing it by hand. A plain terminate lets Chrome save its
    session; sign-ins live in the profile and stay."""
    if not (found := running()):
        return
    pid = found[0]
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(pid)], capture_output=True, timeout=10)
        else:
            os.kill(pid, signal.SIGTERM)
    except (OSError, subprocess.SubprocessError):
        return
    for _ in range(40):  # gone before a new Chrome may take the profile
        if not running():
            break
        time.sleep(0.25)
    PORT_FILE.unlink(missing_ok=True)


def windows(port: int) -> int | None:
    """Tabs open in the Chrome on `port` (page targets; extension workers don't count). None: the
    port didn't answer."""
    try:
        return sum(t.get("type") == "page" for t in httpx.get(f"http://127.0.0.1:{port}/json/list", timeout=2).json())
    except (httpx.HTTPError, ValueError):
        return None


def watch(poll_s: float = WATCH_POLL_S, idle_polls: int = IDLE_POLLS) -> None:
    """Mac: quit Job Finder's Chrome once its last window has been closed a few polls in a row.
    Closing the last window leaves a Mac app running, and this Chrome is the same app as the
    user's own: with it running windowless, the Dock's Chrome (or a link) went to it and no window
    came up - their own Chrome could not start (2026-11-20: one left ~10 days, relaunched by
    Chrome's own update on 2026-11-10 w/ --no-startup-window, a new process id). So it is found by
    its profile every poll, never by process id. A port not answering = wait, not gone. The final
    check + close hold the open lock: no tab opening mid-close. One watcher at a time (flock)."""
    import fcntl
    WATCH_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(WATCH_FILE, os.O_CREAT | os.O_RDWR)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return  # another watcher has it
        idle = 0
        while found := running():
            idle = idle + 1 if windows(found[1]) == 0 else 0
            if idle >= idle_polls:
                try:
                    with locks.held(PROFILE.parent / "apply-browser.lock", "tab opening"):
                        if (found := running()) and windows(found[1]) == 0:
                            restart()
                            return
                except SystemExit:  # a tab kept opening past the lock's wait: look again
                    pass
                idle = 0
            time.sleep(poll_s)
    finally:
        os.close(fd)


def watching() -> bool:
    """A watcher holds the watch file."""
    import fcntl
    try:
        fd = os.open(WATCH_FILE, os.O_RDWR)
    except OSError:
        return False
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    except OSError:
        return True
    finally:
        os.close(fd)


def start_watch() -> None:
    """The watcher as its own process (Mac only - closing the last window quits Chrome on Windows),
    outliving this run like the window does. Every tab we hand out starts one, so a Chrome started
    before the watcher existed gets one too; a second exits at once."""
    if sys.platform != "darwin" or watching():
        return
    log = cfg.DATA / "chrome-watch.log"
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "ab") as err:
            subprocess.Popen([sys.executable, str(Path(__file__).resolve().parents[1] / "jobs.py"), "apply-form", "chrome-watch"],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=err, cwd=cfg.ROOT,
                             start_new_session=True)
    except OSError:  # never stops a fill; the user can still quit Chrome by hand
        pass


def refuses_attach(error: Exception) -> bool:
    return "Browser context management is not supported" in str(error)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def open_tab(url: str) -> tuple[int, str]:
    """Chrome itself opens the tab (command line, or its own new-tab call): a tab Playwright opens
    reads `navigator.webdriver = true`, which an employer's spam check can flag (measured 2026-09).
    Job Finder's Chrome already open -> new tab in it: a second Chrome on the same profile only
    hands the link to the first and never opens its port. -> (port, the new tab's target id)."""
    # two chats applying at once => one starts Chrome, the other waits and opens a tab in it
    with locks.held(PROFILE.parent / "apply-browser.lock", "the application window is still opening - try again in a minute"):
        return _open_tab(url)


def new_tab(port: int, url: str) -> str:
    got = httpx.put(f"http://127.0.0.1:{port}/json/new?{quote(url, safe='')}", timeout=10)
    got.raise_for_status()
    return got.json()["id"]


def _open_tab(url: str) -> tuple[int, str]:
    if port := live_port():
        return port, new_tab(port, url)
    PROFILE.mkdir(parents=True, exist_ok=True)
    port = free_port()
    PORT_FILE.write_text(str(port))
    subprocess.Popen([chrome(), f"--remote-debugging-port={port}", f"--user-data-dir={PROFILE}",
                      "--no-first-run", "--no-default-browser-check", url],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    # our own port, not live_port(): its process scan would run every half second while Chrome starts
    for _ in range(60):
        if answers(port):
            return port, first_tab(port, url)
        time.sleep(0.5)
    # link handed to a Chrome already open that the port file lost track of: no id for its tab
    if found := live_port():
        return found, new_tab(found, url)
    sys.exit("Chrome did not start")


def first_tab(port: int, url: str) -> str:
    """The tab a Chrome we just started opened on `url`: its only tab. Restored tabs beside it ->
    a new tab of our own, never a guess among them."""
    tabs = [t for t in httpx.get(f"http://127.0.0.1:{port}/json/list", timeout=10).json() if t.get("type") == "page"]
    return tabs[0]["id"] if len(tabs) == 1 else new_tab(port, url)


def target_id(page) -> str:
    session = page.context.new_cdp_session(page)
    try:
        return session.send("Target.getTargetInfo")["targetInfo"]["targetId"]
    finally:
        session.detach()


def visible(page) -> bool:
    try:
        return page.evaluate("document.visibilityState") == "visible"
    except Exception:  # a tab mid-navigation can't answer: not the one in front
        return False


def pick(pages: list, match) -> object | None:
    """The user's own tab on this application: the one in front, else the newest. A tab on another
    employer's form never matches (match checks host + posting)."""
    mine = [pg for pg in pages if match(pg.url)]
    return next((pg for pg in reversed(mine) if visible(pg)), mine[-1] if mine else None)


def opened(pages_of, target: str):
    """The tab Chrome just opened, by its target id - never "the newest tab": after a redirect that
    was any tab, possibly another employer's form. A tab can take a moment to reach Playwright."""
    for _ in range(20):
        if page := next((pg for pg in pages_of() if target_id(pg) == target), None):
            return page
        time.sleep(0.25)
    sys.exit("the new tab in Job Finder's Chrome didn't answer - try again")


@contextlib.contextmanager
def page_at(url: str, match=None):
    """A tab on `url` in the Job Finder Chrome. `match(tab_url)` given and a tab matches -> that tab,
    the user's place in a multi-page form kept; else a new tab. On exit we only disconnect: the
    tab stays open."""
    from playwright.sync_api import Error, sync_playwright

    with sync_playwright() as p:
        connected = {}

        def pages(port):
            if port not in connected:
                connected[port] = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            return connected[port].contexts[0].pages

        def fresh(port, target):
            """The new tab; a Chrome refusing the attach (restart) closed and started again on `url`."""
            try:
                return opened(lambda: pages(port), target)
            except Error as e:
                if not refuses_attach(e):
                    raise
            print("Job Finder's Chrome stopped letting the filler in - closed it and opened a fresh one")
            restart()
            port, target = open_tab(url)
            return opened(lambda: pages(port), target)

        page = None
        if match and (port := live_port()):
            try:
                page = pick(pages(port), match)
            except Error as e:
                if not refuses_attach(e):
                    raise
        if page is None:
            page = fresh(*open_tab(url))
        start_watch()
        page.wait_for_load_state()
        page.bring_to_front()
        yield page
