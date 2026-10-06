"""Trial, off by default (plan-29g.9): fill a form in a tab of the Job Finder window instead of Chrome -
`apply-form fill <job> --in-window`, Greenhouse, Ashby, Lever + JazzHR (owner's yes for Ashby + Lever 2026-10-05,
plan-nko.7, plan-nko.14; JazzHR 2026-10-06, plan-k8n.5). Route 2 of app/docs/apply/vscode-browser.md: the
window's extension attaches VS Code's JavaScript debugger to the tab and hands back its CDP proxy;
Playwright can't use that proxy (one page, no browser), so Page + Locator below speak CDP and cover
only what greenhouse.py, ashby.py, lever.py, jazzhr.py, workable.py and form.fill call. Every hard limit of the Chrome path stays: never Submit,
a file chosen only after the user's yes (form.fill decides that, not this file).

Measured costs this follows (vscode-browser.md): skip every pause on attach (a site's own `debugger;`
line would freeze the fill), scroll `instant` (smooth scrolling moved the box under the click), only
our own sessions let go - never every debug session (that closes the tab), the tab picked by a
holding page only this run knows (the posting's own link may already be open in another tab: two
matches = js-debug's picker), and Restricted Mode refuses it.
"""
import contextlib
import json
import re
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from apply.cdp import CDP, Closed, ScriptError

SYSTEMS = ("Greenhouse", "Ashby", "Lever", "JazzHR")
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
# a request leaves, then ends either way
NETWORK = ("Network.requestWillBeSent", "Network.loadingFinished", "Network.loadingFailed")
FALLBACK = "run fill without --in-window to fill it in Chrome"
# said after the fill: what Submit in the tab is not yet checked for (never Submit while measuring)
AT_SUBMIT = {"Lever": "Lever's hCaptcha check at Submit is untested in the window - if Submit doesn't go through, "
                      "fill it again without --in-window (Chrome)",
             "JazzHR": "JazzHR's Human Check at Submit is untested in the window - if it doesn't show or Submit doesn't "
                       "go through, fill it again without --in-window (Chrome)"}
WHY = {"untrusted": "the Job Finder window is in Restricted Mode (opened without its Desktop icon)",
       "picker": "the window couldn't tell which tab to use",
       "no proxy": "the window's debugger didn't hand over the tab",
       "no tab session": "the window's debugger didn't reach the tab"}
# keys typed by name, as Playwright's: (key, code, Windows key code, text it types); macOS edits + moves only w/
# its command named (Playwright does the same)
KEYS = {"Escape": ("Escape", "Escape", 27, None, None), "Delete": ("Delete", "Delete", 46, None, "deleteForward"),
        "Enter": ("Enter", "Enter", 13, None, None), "Tab": ("Tab", "Tab", 9, None, None),
        "ArrowDown": ("ArrowDown", "ArrowDown", 40, None, "moveDown"), "Space": (" ", "Space", 32, " ", None)}
# a script that is a function: page.evaluate calls it, as Playwright's (anything else is evaluated as written)
FUNCTION = re.compile(r"^\s*(async\s+)?(function\b|(\([^)]*\)|[\w$]+)\s*=>)")
# dispatch_event: the event each type makes, as Playwright's (bubbles, cancelable, composed unless told otherwise)
DISPATCH = """(e, [type, init]) => { const kinds = {mouse: MouseEvent, key: KeyboardEvent, pointer: PointerEvent,
    focus: FocusEvent, wheel: WheelEvent};
  const kind = /^(aux|dbl)?click$|^mouse|^contextmenu$/.test(type) ? "mouse" : /^key|^textInput$/.test(type) ? "key"
    : /^pointer|^(got|lost)pointercapture$/.test(type) ? "pointer" : /^(focus|blur|focusin|focusout)$/.test(type) ? "focus"
    : type === "wheel" ? "wheel" : null;
  e.dispatchEvent(new (kinds[kind] || Event)(type, {bubbles: true, cancelable: true, composed: true, ...(init || {})})); }"""
# a click's point: the box's middle, scrolled into view -> [x, y]; null while nothing is there to click, or (unless
# forced) something else sits on that point - Playwright's hit check, the target widened to the button or link
# it sits in
CLICK_POINT = """(e, force) => { e.scrollIntoView({block: 'center', inline: 'center', behavior: 'instant'});
  const r = e.getBoundingClientRect(); if (!r.width || !r.height) return null;
  const x = r.x + r.width / 2, y = r.y + r.height / 2; if (force) return [x, y];
  const t = e.closest('button, [role=button], a, [role=link]') || e, hit = document.elementFromPoint(x, y);
  return hit && t.contains(hit) ? [x, y] : null; }"""
HOLDING = ("<!doctype html><meta charset=utf-8><title>Opening the application form</title>"
           "<body style=\"font:16px system-ui;margin:3em;color:#333\">Opening the application form...</body>").encode()
# get_by_role: the elements each role takes besides [role=X], as Playwright's (a file box is a button);
# only the roles the fillers ask for
ROLES = {"button": "button, input[type=button], input[type=submit], input[type=reset], input[type=image], input[type=file]",
         "option": "option"}
# shown, as Playwright's: a box with width + height, not hidden by style (display: contents = any child shown)
VISIBLE = """function visible(e) { if (!e) return false; const s = getComputedStyle(e);
  if (s.display === "contents") return [...e.childNodes].some((c) => c.nodeType === 1 ? visible(c)
    : c.nodeType === 3 && (() => { const r = document.createRange(); r.selectNode(c); const b = r.getBoundingClientRect();
      return b.width > 0 && b.height > 0; })());
  if (!e.checkVisibility() || s.visibility !== "visible") return false;
  const b = e.getBoundingClientRect(); return b.width > 0 && b.height > 0; }"""
# steps -> matching elements, in the page: css (querySelectorAll under each), parts (a selector w/ ':visible', one
# [css, shown only] per comma part, together in page order), nth, text (the smallest
# elements whose text holds it, case and spacing ignored - as Playwright's get_by_text), has (the
# elements themselves, kept when their text holds a string as `text` does, or a pattern matches their
# whole text as written - as Playwright's has_text), visible (kept when shown or not, as VISIBLE), role (as get_by_role: shown to a screen reader,
# accessible name = aria-labelledby, aria-label, a button input's value, else its text; exact = the
# whole name w/ case, else part of it w/o)
RESOLVE = """(steps) => { let els = [document];
  const norm = (s) => (s || "").replace(/[\\u200b\\u00ad]/g, "").trim().replace(/\\s+/g, " ");
  const low = (s) => norm(s).toLowerCase();
  const text = (e) => e.nodeType === 3 ? e.nodeValue : ["SCRIPT", "NOSCRIPT", "STYLE"].includes(e.nodeName) ? ""
    : (e instanceof HTMLInputElement && ["submit", "button", "reset"].includes(e.type)) ? e.value
    : [...e.childNodes].map(text).join("");
  const under = (sel) => [...new Set(els.flatMap((e) => [...e.querySelectorAll(sel)]))];
  const named = (e) => { const by = (e.getAttribute("aria-labelledby") || "").split(/\\s+/).filter(Boolean);
    if (by.length) return by.map((id) => document.getElementById(id)?.textContent || "").join(" ");
    if ((e.getAttribute("aria-label") || "").trim()) return e.getAttribute("aria-label");
    return e instanceof HTMLInputElement ? e.value : e.textContent; };
  const shown = (e) => !e.closest("[aria-hidden=true]") && e.checkVisibility({visibilityProperty: true});
  for (const [k, v] of steps) {
    if (k === "css") els = under(v);
    else if (k === "nth") els = els.slice(v, v + 1);
    else if (k === "visible") els = els.filter((e) => (VISIBLE)(e) === v);
    else if (k === "parts") els = [...new Set(v.flatMap(([sel, vis]) => under(sel).filter((e) => !vis || (VISIBLE)(e))))]
      .sort((a, b) => a === b ? 0 : a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1);
    else if (k === "has") { const re = typeof v === "string" ? null : new RegExp(v.source, v.flags);
      els = els.filter((e) => re ? re.test(text(e)) : low(text(e)).includes(low(v))); }
    else if (k === "role") { const [role, name, exact] = v, extra = ROLES[role];
      els = under(extra ? `[role="${role}"], ${extra}` : `[role="${role}"]`)
        .filter((e) => (!e.hasAttribute("role") || e.getAttribute("role").trim().split(/\\s+/)[0] === role) && shown(e))
        .filter((e) => name === null || (exact ? norm(named(e)) === norm(name) : low(named(e)).includes(low(name)))); }
    else { const want = low(v), has = (e) => low(e.textContent).includes(want);
      els = [...new Set(els.flatMap((e) => [e, ...e.querySelectorAll("*")]))]
        .filter((e) => e.nodeType === 1 && has(e) && ![...e.children].some(has)); } }
  return els; }""".replace("ROLES", json.dumps(ROLES)).replace("VISIBLE", VISIBLE)


def css_parts(selector: str) -> list[tuple[str, bool]]:
    """Playwright selector -> [(plain CSS, must be shown)], one per top-level comma part. ':visible' must
    close its part: on an ancestor it would test the wrong element."""
    parts, depth, quote, start = [], 0, "", 0
    for i, ch in enumerate(selector):
        if quote:
            quote = "" if ch == quote and selector[i - 1] != "\\" else quote
        elif ch in "'\"":
            quote = ch
        elif ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == "," and not depth:
            parts.append(selector[start:i])
            start = i + 1
    parts.append(selector[start:])
    out = []
    for part in (p.strip() for p in parts):
        css = part.removesuffix(":visible")
        if re.search(r":visible(?![\w-])", re.sub(r"'[^']*'|\"[^\"]*\"", "", css)):  # quoted text aside
            raise ValueError(f"':visible' only at the end of a part: {part!r}")
        out.append((css, css != part))
    return out


class Keyboard:
    """page.keyboard, as Playwright's: a key pressed wherever focus is."""
    def __init__(self, page: "Page"):
        self.page = page

    def press(self, key: str) -> None:
        self.page.key(key)


class Page:
    def __init__(self, cdp: CDP):
        self.cdp = cdp
        # requests in flight, as the tab reports them: idle = none for IDLE_MS (Greenhouse readies its
        # upload with a request after the page has loaded, plan-29g.25)
        self.inflight, self.moved, self.lock = set(), time.monotonic(), threading.Lock()
        for name in NETWORK:
            cdp.on(name, self._network)
        # js-debug's proxy passes a domain's events on only when asked (adds to what Block asked for);
        # a tab's own CDP (the tests) has no such command and sends them anyway
        for method, params in (("JsDebug.subscribe", {"events": list(NETWORK)}), ("Network.enable", {})):
            with contextlib.suppress(RuntimeError, TimeoutError, Closed):
                cdp.send(method, params, 5)

    def _network(self, params: dict, msg: dict) -> None:
        with self.lock:
            (self.inflight.add if msg["method"] == "Network.requestWillBeSent" else self.inflight.discard)(params.get("requestId"))
            self.moved = time.monotonic()

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

    @property
    def keyboard(self) -> Keyboard:
        return Keyboard(self)

    def evaluate(self, expr: str, arg=None):
        """As Playwright's: a function is called w/ `arg`, anything else evaluated as written."""
        return self.run(f"({expr})({json.dumps(arg)})" if FUNCTION.match(expr) else expr)

    def locator(self, selector: str, has_text=None) -> "Locator":
        return Locator(self, []).locator(selector, has_text)

    def get_by_role(self, role: str, name: str | None = None, exact: bool = False) -> "Locator":
        return Locator(self, []).get_by_role(role, name, exact)

    def goto(self, url: str, timeout: float = TIMEOUT_MS) -> None:
        # the old page marked: done = a page without the mark, loaded
        with contextlib.suppress(RuntimeError, TimeoutError):
            self.run("window.__jfLeaving = true", 5)
        with self.lock:  # the old page's requests end with it, unreported
            self.inflight.clear()
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
            # requests seen leaving and ending, never the page's own list of finished ones (it misses
            # the one still out, and stops counting at 250)
            deadline = time.monotonic() + timeout / 1000
            while True:
                with self.lock:
                    busy, quiet = bool(self.inflight), time.monotonic() - self.moved
                if not busy and quiet >= IDLE_MS / 1000:
                    return
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"networkidle: not after {timeout} ms")
                time.sleep(POLL)

    def wait_for_timeout(self, ms: float) -> None:
        time.sleep(ms / 1000)

    def eval_on_selector_all(self, selector: str, fn: str, arg=None):
        return self.locator(selector).evaluate_all(fn, arg)

    def bring_to_front(self) -> None:
        pass  # the tab is the one the window just opened

    def click_at(self, x: float, y: float) -> None:
        self.cdp.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
        for kind in ("mousePressed", "mouseReleased"):
            self.cdp.send("Input.dispatchMouseEvent", {"type": kind, "x": x, "y": y, "button": "left", "clickCount": 1})

    def key(self, name: str, text: str | None = None) -> None:
        key, code, vk, typed, command = KEYS.get(name, (name, None, None, None, None))
        text = text or typed
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

    def locator(self, selector: str, has_text: "str | re.Pattern | None" = None) -> "Locator":
        parts = css_parts(selector)
        found = self._with(("parts", parts) if any(shown for _, shown in parts) else ("css", selector))
        if has_text is None:
            return found
        if isinstance(has_text, str):
            return found._with(("has", has_text))
        # a Python pattern as a JS RegExp, as Playwright passes one: its flags i, s, m only
        if has_text.flags & ~(re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):
            raise ValueError(f"has_text: flags JavaScript can't take: {has_text!r}")
        flags = "".join(f for f, bit in (("i", re.IGNORECASE), ("s", re.DOTALL), ("m", re.MULTILINE)) if has_text.flags & bit)
        return found._with(("has", {"source": has_text.pattern, "flags": flags}))

    def filter(self, visible: bool) -> "Locator":
        return self._with(("visible", visible))

    def all(self) -> list["Locator"]:
        """One locator per element there now - no wait, as Playwright's."""
        return [self.nth(i) for i in range(self.count())]

    def get_by_text(self, text: str) -> "Locator":
        return self._with(("text", text))

    def get_by_role(self, role: str, name: str | None = None, exact: bool = False) -> "Locator":
        return self._with(("role", [role, name, exact]))

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

    def evaluate_all(self, fn: str, arg=None):
        return self._all(f"(els, arg) => ({fn})(els, arg)", arg)

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

    def is_visible(self) -> bool:
        """Shown now, as Playwright's: no wait, nothing there = False."""
        return self._all(f"(els) => els.length > 0 && ({VISIBLE})(els[0])")

    def is_checked(self, timeout: float | None = None) -> bool:
        return self._one("""(e) => { if (e.matches("input[type=checkbox], input[type=radio]")) return e.checked;
          const on = e.getAttribute("aria-checked"); if (on === null) throw new Error("Not a checkbox or radio button");
          return on === "true"; }""", timeout=timeout)

    def focus(self, timeout: float | None = None) -> None:
        self._one("(e) => e.focus()", timeout=timeout)

    def blur(self, timeout: float | None = None) -> None:
        self._one("(e) => e.blur()", timeout=timeout)

    def scroll_into_view_if_needed(self, timeout: float | None = None) -> None:
        self._one("(e) => e.scrollIntoView({block: 'center', inline: 'center', behavior: 'instant'})", timeout=timeout)

    def click(self, timeout: float | None = None, force: bool = False) -> None:
        """A real click at the box's middle, as a person's: the page's own handlers run. As Playwright's: once
        shown and nothing else sits on that point, else TimeoutError; `force` skips both checks - whatever is
        on top there takes the click."""
        timeout = TIMEOUT_MS if timeout is None else timeout
        deadline = time.monotonic() + timeout / 1000
        while True:
            at = self._one(CLICK_POINT, force, visible=not force, timeout=max(0.0, (deadline - time.monotonic()) * 1000))
            if at:
                return self.page.click_at(*at)
            if time.monotonic() >= deadline:
                raise TimeoutError(f"{self.steps}: something else sits over it after {timeout} ms")
            time.sleep(POLL)

    def dispatch_event(self, type: str, event_init: dict | None = None, timeout: float | None = None) -> None:
        """The event fired on the element itself, as Playwright's: no click point, nothing on top matters."""
        self._one(DISPATCH, [type, event_init], timeout=timeout)

    def fill(self, value: str, timeout: float | None = None) -> None:
        self._one("(e) => { e.focus(); if (e.select) e.select(); }", visible=True, timeout=timeout)
        if value:
            self.page.cdp.send("Input.insertText", {"text": value})
        else:
            self.page.key("Delete")

    def select_option(self, value: "str | list[str] | None" = None, *, label: "str | list[str] | None" = None,
                      timeout: float | None = None) -> list[str]:
        """Options picked by value or by label, as Playwright's: waits for the box shown and each option
        there, then sets them and tells the page (input + change) -> their values."""
        if (value is None) == (label is None):
            raise ValueError("select_option: give value or label")
        by, wants = ("value", value) if label is None else ("label", label)
        wants = [wants] if isinstance(wants, str) else list(wants)
        deadline = time.monotonic() + (TIMEOUT_MS if timeout is None else timeout) / 1000
        while True:
            picked = self._one("""(e, [by, wants]) => { if (e.nodeName !== "SELECT") throw new Error("Element is not a <select> element");
              const pick = wants.map((w) => [...e.options].find((o) => o[by] === w));
              if (pick.some((o) => !o)) return null;
              if (pick.length > 1 && !e.multiple) throw new Error("Non-multiple select element");
              e.value = undefined; pick.forEach((o) => { o.selected = true; });
              e.dispatchEvent(new Event("input", {bubbles: true, composed: true}));
              e.dispatchEvent(new Event("change", {bubbles: true}));
              return pick.map((o) => o.value); }""", [by, wants], visible=True,
                               timeout=max(0.0, (deadline - time.monotonic()) * 1000))
            if picked is not None:
                return picked
            if time.monotonic() >= deadline:
                raise TimeoutError(f"{self.steps}: no option {by} {wants} after {timeout} ms")
            time.sleep(POLL)

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
    unused (Greenhouse, Ashby, Lever + JazzHR are one page each); `before_load(cdp)` runs before the form opens (measuring)."""
    import cfg
    import jobs
    import launch
    if not launch.vscode_running():
        sys.exit(f"not filled: the Job Finder window isn't open - open CEZ Job Finder, or {FALLBACK}")
    # extension from before an update => no link watcher or debugger hand-off: say so, not a timeout
    if launch.window_behind():
        sys.exit(f"not filled: {launch.BEHIND} - {FALLBACK}. {launch.RESTART_LINE}")
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
