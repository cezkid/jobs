"""The user's application window: a plain Chrome with Job Finder's own profile that we attach to,
fill, and let go of. Shared by every application system.

No automation flag, so `navigator.webdriver` is false and the employer's spam check sees an
ordinary browser when the user clicks Submit. The profile lives in `.data/` - sign-ins stay on
this computer and never touch the user's everyday Chrome. Facts: app/docs/apply/apply-systems.md.
"""
import contextlib
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

import httpx

import cfg

PROFILE = cfg.DATA / "apply-browser"
# port we started Chrome on. Never --remote-debugging-port=0: Chrome then sets
# navigator.webdriver = true on every page (measured 2026-09, Chrome 154); a fixed port leaves it false
PORT_FILE = PROFILE / "job-finder-port"
CHROME = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
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
        # file gone while Chrome still runs (seen 2026-09-24): without this, the next start only
        # hands the link to the open window and waits on a port that never answers
        port = running_port()
    if port is None or not answers(port):
        return None
    if not PORT_FILE.exists():
        PORT_FILE.write_text(str(port))
    return port


def answers(port: int) -> bool:
    try:
        httpx.get(f"http://127.0.0.1:{port}/json/version", timeout=1)
        return True
    except httpx.HTTPError:
        return False


def running_port() -> int | None:
    """Debugging port off the command line of a Chrome running on Job Finder's profile."""
    if sys.platform == "win32":
        command = ["powershell", "-NoProfile", "-Command",
                   "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | ForEach-Object CommandLine"]
    else:
        command = ["ps", "-axww", "-o", "command="]
    try:
        listed = subprocess.run(command, capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for line in listed.splitlines():
        if str(PROFILE) in line and (m := re.search(r"--remote-debugging-port=(\d+)", line)):
            return int(m.group(1))
    return None


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def open_tab(url: str) -> int:
    """Chrome itself opens the tab (command line, or its own new-tab call): a tab Playwright opens
    reads `navigator.webdriver = true`, which an employer's spam check can flag (measured 2026-09).
    Job Finder's Chrome already open -> new tab in it: a second Chrome on the same profile only
    hands the link to the first and never opens its port."""
    if port := live_port():
        httpx.put(f"http://127.0.0.1:{port}/json/new?{quote(url, safe='')}", timeout=10).raise_for_status()
        return port
    PROFILE.mkdir(parents=True, exist_ok=True)
    port = free_port()
    PORT_FILE.write_text(str(port))
    subprocess.Popen([chrome(), f"--remote-debugging-port={port}", f"--user-data-dir={PROFILE}",
                      "--no-first-run", "--no-default-browser-check", url],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(60):
        if port := live_port():
            return port
        time.sleep(0.5)
    sys.exit("Chrome did not start")


@contextlib.contextmanager
def page_at(url: str):
    """A tab on `url` in the Job Finder Chrome. On exit we only disconnect: the tab stays open."""
    from playwright.sync_api import sync_playwright

    port = open_tab(url)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        pages = browser.contexts[0].pages
        # newest tab on this link = the one just opened (an earlier try may still be open)
        page = ([pg for pg in pages if pg.url.split("?")[0] == url.split("?")[0]] or pages)[-1]
        page.wait_for_load_state()
        page.bring_to_front()
        yield page
