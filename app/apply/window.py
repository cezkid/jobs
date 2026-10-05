"""Trial, off by default (plan-29g.9): fill a form in a tab of the Job Finder window instead of Chrome -
`apply-form fill <job> --in-window`, Greenhouse only. Route 2 of app/docs/apply/vscode-browser.md: the
window's extension attaches VS Code's JavaScript debugger to the tab and hands back its CDP proxy;
Playwright can't use that proxy (one page, no browser), so Page + Locator below speak CDP and cover
only what greenhouse.py and form.fill call. Every hard limit of the Chrome path stays: never Submit,
a file chosen only after the user's yes (form.fill decides that, not this file).

Measured costs this follows (vscode-browser.md): skip every pause on attach (a site's own `debugger;`
line would freeze the fill), scroll `instant` (smooth scrolling moved the box under the click), only
our own sessions let go - never every debug session (that closes the tab), the tab picked by a
holding page only this run knows (the posting's own link may already be open in another tab: two
matches = js-debug's picker), and Restricted Mode refuses it.
"""
import contextlib
import json
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from apply.cdp import CDP, Closed, ScriptError

SYSTEMS = ("Greenhouse",)
ATTACH, DETACH = "attach-form", "detach-form"
# holding page: the window's open-link wait + the tab's first request
OPEN_WAIT = 20
# extension.js: picker 15 s + child session 10 s + proxy 5 s, w/ margin
ATTACH_WAIT = 45
DETACH_WAIT = 15
TIMEOUT_MS = 30000
POLL = 0.1
# no network for this long = settled, as Playwright's "networkidle"
IDLE_MS = 500
FALLBACK = "run fill without --in-window to fill it in Chrome"
WHY = {"untrusted": "the Job Finder window is in Restricted Mode (opened without its Desktop icon)",
       "picker": "the window couldn't tell which tab to use",
       "no proxy": "the window's debugger didn't hand over the tab",
       "no tab session": "the window's debugger didn't reach the tab"}
# keys typed by name: (code, Windows key code); macOS edits only w/ its command named (Playwright does the same)
KEYS = {"Escape": ("Escape", 27, None), "Delete": ("Delete", 46, "deleteForward"), "Enter": ("Enter", 13, None),
        "Tab": ("Tab", 9, None)}
HOLDING = ("<!doctype html><meta charset=utf-8><title>Opening the application form</title>"
           "<body style=\"font:16px system-ui;margin:3em;color:#333\">Opening the application form...</body>").encode()
# steps -> matching elements, in the page: css (querySelectorAll under each), nth, text (the smallest
# elements whose text holds it, case and spacing ignored - as Playwright's get_by_text)
RESOLVE = """(steps) => { let els = [document];
  const norm = (s) => (s || "").replace(/\\s+/g, " ").trim().toLowerCase();
  for (const [k, v] of steps) {
    if (k === "css") els = [...new Set(els.flatMap((e) => [...e.querySelectorAll(v)]))];
    else if (k === "nth") els = els.slice(v, v + 1);
    else { const want = norm(v), has = (e) => norm(e.textContent).includes(want);
      els = [...new Set(els.flatMap((e) => [e, ...e.querySelectorAll("*")]))]
        .filter((e) => e.nodeType === 1 && has(e) && ![...e.children].some(has)); } }
  return els; }"""
VISIBLE = "(e) => !!e && e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden'"


class Page:
    def __init__(self, cdp: CDP):
        self.cdp = cdp

    def quiet(self) -> None:
        """No breakpoint or `debugger;` line in the site's code pauses the page under us - again after
        each navigation: another site's page may be another process, the setting gone with it."""
        try:
            self.cdp.send("Debugger.setSkipAllPauses", {"skip": True}, 5)
        except (RuntimeError, TimeoutError, Closed):
            pass

    def run(self, expr: str, timeout: float = 15):
        return self.cdp.evaluate(expr, timeout)

    def until(self, expr: str, timeout_ms: float, what: str) -> None:
        deadline = time.monotonic() + timeout_ms / 1000
        while True:
            try:
                if self.run(expr, 5):
                    return
            except (RuntimeError, TimeoutError):  # page mid-navigation
                pass
            if time.monotonic() >= deadline:
                raise TimeoutError(f"{what}: not after {timeout_ms} ms")
            time.sleep(POLL)

    @property
    def url(self) -> str:
        return self.run("location.href")

    def locator(self, selector: str) -> "Locator":
        return Locator(self, [("css", selector)])

    def goto(self, url: str, timeout: float = TIMEOUT_MS) -> None:
        # the old page marked: done = a page without the mark, loaded
        with contextlib.suppress(RuntimeError, TimeoutError):
            self.run("window.__jfLeaving = true", 5)
        r = self.cdp.send("Page.navigate", {"url": url}, timeout / 1000)
        if r.get("errorText"):
            raise RuntimeError(f"couldn't open the form: {r['errorText']}")
        self.until("!window.__jfLeaving && document.readyState === 'complete'", timeout, "page load")
        self.quiet()

    def wait_for_load_state(self, state: str = "load", timeout: float = TIMEOUT_MS) -> None:
        if state == "domcontentloaded":
            return self.until("document.readyState !== 'loading'", timeout, state)
        self.until("document.readyState === 'complete'", timeout, state)
        if state == "networkidle":
            deadline, last, since = time.monotonic() + timeout / 1000, None, time.monotonic()
            while time.monotonic() < deadline:
                n = self.run("performance.getEntriesByType('resource').length", 5)
                if n != last:
                    last, since = n, time.monotonic()
                elif time.monotonic() - since >= IDLE_MS / 1000:
                    return
                time.sleep(POLL)
            raise TimeoutError(f"networkidle: not after {timeout} ms")

    def wait_for_timeout(self, ms: float) -> None:
        time.sleep(ms / 1000)

    def eval_on_selector_all(self, selector: str, fn: str):
        return self.locator(selector).evaluate_all(fn)

    def bring_to_front(self) -> None:
        pass  # the tab is the one the window just opened

    def click_at(self, x: float, y: float) -> None:
        self.cdp.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
        for kind in ("mousePressed", "mouseReleased"):
            self.cdp.send("Input.dispatchMouseEvent", {"type": kind, "x": x, "y": y, "button": "left", "clickCount": 1})

    def key(self, key: str, text: str | None = None) -> None:
        code, vk, command = KEYS.get(key, (None, None, None))
        down = {"type": "keyDown", "key": key}
        if code:
            down |= {"code": code, "windowsVirtualKeyCode": vk}
        if text:
            down |= {"text": text, "unmodifiedText": text}
        if command and sys.platform == "darwin":
            down["commands"] = [command]
        self.cdp.send("Input.dispatchKeyEvent", down)
        self.cdp.send("Input.dispatchKeyEvent", {"type": "keyUp", "key": key} | ({"code": code, "windowsVirtualKeyCode": vk} if code else {}))


class Locator:
    def __init__(self, page: Page, steps: list):
        self.page, self.steps = page, steps

    def _with(self, step) -> "Locator":
        return Locator(self.page, [*self.steps, step])

    @property
    def first(self) -> "Locator":
        return self.nth(0)

    def nth(self, i: int) -> "Locator":
        return self._with(("nth", i))

    def locator(self, selector: str) -> "Locator":
        return self._with(("css", selector))

    def get_by_text(self, text: str) -> "Locator":
        return self._with(("text", text))

    def _all(self, fn: str, arg=None):
        """fn(elements, arg) in the page, now - no wait."""
        return self.page.run(f"({fn})(({RESOLVE})({json.dumps(self.steps)}), {json.dumps(arg)})")

    def _one(self, fn: str, arg=None, visible: bool = False, timeout: float | None = None):
        """fn(first element, arg) once there is one (shown, when `visible`)."""
        timeout = TIMEOUT_MS if timeout is None else timeout
        ready = f"(els) => els.length > 0 && {'(' + VISIBLE + ')(els[0])' if visible else 'true'}"
        deadline = time.monotonic() + timeout / 1000
        while True:
            try:
                if self._all(ready):
                    return self._all(f"(els, arg) => ({fn})(els[0], arg)", arg)
            except ScriptError:
                raise
            except (RuntimeError, TimeoutError):  # page mid-navigation
                pass
            if time.monotonic() >= deadline:
                raise TimeoutError(f"{self.steps}: not {'shown' if visible else 'on the page'} after {timeout} ms")
            time.sleep(POLL)

    def count(self) -> int:
        return self._all("(els) => els.length")

    def all_inner_texts(self) -> list[str]:
        return self._all("(els) => els.map((e) => e.innerText)")

    def evaluate_all(self, fn: str):
        return self._all(f"(els) => ({fn})(els)")

    def evaluate(self, fn: str, arg=None):
        return self._one(f"(e, arg) => ({fn})(e, arg)", arg)

    def wait_for(self, timeout: float | None = None) -> None:
        self._one("(e) => true", visible=True, timeout=timeout)

    def inner_text(self, timeout: float | None = None) -> str:
        return self._one("(e) => e.innerText", timeout=timeout)

    def input_value(self, timeout: float | None = None) -> str:
        return self._one("(e) => e.value", timeout=timeout)

    def get_attribute(self, name: str, timeout: float | None = None):
        return self._one("(e, n) => e.getAttribute(n)", name, timeout=timeout)

    def focus(self, timeout: float | None = None) -> None:
        self._one("(e) => e.focus()", timeout=timeout)

    def blur(self, timeout: float | None = None) -> None:
        self._one("(e) => e.blur()", timeout=timeout)

    def scroll_into_view_if_needed(self, timeout: float | None = None) -> None:
        self._one("(e) => e.scrollIntoView({block: 'center', inline: 'center', behavior: 'instant'})", timeout=timeout)

    def click(self, timeout: float | None = None) -> None:
        # a real click at the box's middle, as a person's: the page's own handlers run
        x, y = self._one("""(e) => { e.scrollIntoView({block: 'center', inline: 'center', behavior: 'instant'});
          const r = e.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }""", visible=True, timeout=timeout)
        self.page.click_at(x, y)

    def fill(self, value: str, timeout: float | None = None) -> None:
        self._one("(e) => { e.focus(); if (e.select) e.select(); }", visible=True, timeout=timeout)
        if value:
            self.page.cdp.send("Input.insertText", {"text": value})
        else:
            self.page.key("Delete")

    def press(self, key: str, timeout: float | None = None) -> None:
        self.focus(timeout)
        self.page.key(key)

    def press_sequentially(self, text: str, delay: float = 0, timeout: float | None = None) -> None:
        self.focus(timeout)
        for ch in text:
            self.page.key(ch, text=ch)
            time.sleep(delay / 1000)

    def set_input_files(self, path: str, timeout: float | None = None) -> None:
        self._one("(e) => true", timeout=timeout)
        r = self.page.cdp.send("Runtime.evaluate", {"expression": f"({RESOLVE})({json.dumps(self.steps)})[0]"})
        oid = r.get("result", {}).get("objectId")
        if not oid:
            raise RuntimeError("file box gone")
        self.page.cdp.send("DOM.setFileInputFiles", {"files": [str(Path(path).resolve())], "objectId": oid})


@contextlib.contextmanager
def holding_page():
    """A blank page on this computer only this run knows -> (its link, Event set once a tab asked for it)."""
    path, seen = f"/jf-{secrets.token_hex(16)}", threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            mine = self.path == path
            self.send_response(200 if mine else 404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if mine:
                self.wfile.write(HOLDING)
                seen.set()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}{path}", seen
    finally:
        server.shutdown()
        server.server_close()


def ask(request: dict, wait: float):
    """The window's answer to a request, None when it never took it or never answered."""
    import cfg
    import jobs
    name = jobs.send_request(request, cfg.ROOT)
    if not name:
        return None
    try:
        return jobs.window_answer(name, cfg.ROOT, wait)
    except TimeoutError:
        return None


def let_go(session: str) -> None:
    answer = ask({"do": DETACH, "session": session}, DETACH_WAIT)
    if not isinstance(answer, dict) or answer.get("ok") is not True or answer.get("left"):
        print("note: the window may still be holding the form tab - closing that tab after Submit lets it go")


@contextlib.contextmanager
def page_at(url: str, match=None, before_load=None):
    """A tab on `url` in the Job Finder window, as browser.page_at gives one in Chrome. `match` is
    unused (Greenhouse is one page); `before_load(cdp)` runs before the form opens (measuring)."""
    import cfg
    import jobs
    import launch
    if not launch.vscode_running():
        sys.exit(f"not filled: the Job Finder window isn't open - open CEZ Job Finder, or {FALLBACK}")
    with holding_page() as (local, seen):
        if not jobs.send_request({"url": local}, cfg.ROOT) or not seen.wait(OPEN_WAIT):
            sys.exit(f"not filled: the Job Finder window didn't open a tab for the form - {FALLBACK}")
        answer = ask({"do": ATTACH, "url": local}, ATTACH_WAIT)
        if not isinstance(answer, dict) or answer.get("ok") is not True:
            error = answer.get("error") if isinstance(answer, dict) else None
            sys.exit(f"not filled: {WHY.get(error, 'the window could not reach the tab')} - {FALLBACK}")
        session, proxy = answer["session"], answer.get("proxy") or {}
        try:
            cdp = CDP(proxy["host"], int(proxy["port"]), proxy["path"])
        except (KeyError, ValueError, TypeError, OSError, Closed):
            let_go(session)
            sys.exit(f"not filled: the window's debugger didn't let us in - {FALLBACK}")
    try:
        page = Page(cdp)
        page.quiet()
        if before_load:
            before_load(cdp)
        page.goto(url)
        yield page
    finally:
        cdp.close()
        let_go(session)
