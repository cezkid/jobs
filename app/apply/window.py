"""Trial, off by default (plan-29g.9): fill a form in a tab of the Job Finder window instead of Chrome -
`apply-form fill <job> --in-window`, Greenhouse, Ashby, Lever, JazzHR, Workable, BambooHR + the multi-page Oracle,
iCIMS, Paylocity (owner's yes for Ashby + Lever 2026-10-05, plan-nko.7, plan-nko.14; JazzHR + Workable 2026-10-06,
plan-k8n.5, plan-k8n.8; BambooHR 2026-10-07, plan-k8n.11; Oracle, iCIMS + Paylocity 2026-10-07, plan-k8n.20). Route 2 of app/docs/apply/vscode-browser.md: the
window's extension attaches VS Code's JavaScript debugger to the tab and hands back its CDP proxy;
Playwright can't use that proxy (one page, no browser), so Page + Locator below speak CDP and cover
only what greenhouse.py, ashby.py, lever.py, jazzhr.py, workable.py, bamboohr.py, oracle.py, icims.py, paylocity.py
and form.fill call. Every hard limit of the Chrome path stays: never Submit,
a file chosen only after the user's yes (form.fill decides that, not this file).

Measured costs this follows (vscode-browser.md): skip every pause on attach (a site's own `debugger;`
line would freeze the fill), scroll `instant` (smooth scrolling moved the box under the click), only
our own sessions let go - never every debug session (that closes the tab), the tab picked by a
holding page only this run knows (the posting's own link may already be open in another tab: two
matches = js-debug's picker), and Restricted Mode refuses it. A form over several pages: one holder process stays attached between
runs (hold below), so the user's own tab keeps its place.
"""
import contextlib
import json
import os
import re
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from apply.cdp import CDP, Closed, ScriptError

SYSTEMS = ("Greenhouse", "Ashby", "Lever", "JazzHR", "Workable", "BambooHR", "Oracle Recruiting Cloud", "iCIMS", "Paylocity")
# never in the window, whatever SYSTEMS says: why, in plain words
REFUSED = {"UKG": "its sign-in lives in Job Finder's Chrome - a tab in the window isn't signed in"}
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
                       "go through, fill it again without --in-window (Chrome)",
             "Workable": "Workable's Turnstile check at Submit and the resume upload are untested in the window - if the "
                         "resume doesn't show as attached or Submit doesn't go through, fill it again without --in-window (Chrome)",
             "BambooHR": "BambooHR's reCAPTCHA tick-box at Submit and the resume upload are untested in the window - if "
                         "the resume doesn't show as attached, the tick-box doesn't show or take a click, or Submit doesn't "
                         "go through, fill it again without --in-window (Chrome)",
             # multi-page: only the start box / page 1 measured in the tab (plan-k8n.16, .18); Chrome starts at page 1
             "Oracle Recruiting Cloud": "Oracle's pages after Next, its resume upload and any check at Submit are untested in the "
                                        "window - if a page doesn't fill, a check doesn't show or take a click, or Submit "
                                        "doesn't go through, fill it again from the start without --in-window (Chrome)",
             "iCIMS": "iCIMS's hCaptcha check, its pages after Next and the resume upload are untested in the window - if a "
                      "page doesn't fill, the check doesn't show or take a click, the resume doesn't show as attached, or "
                      "Submit doesn't go through, fill it again from the start without --in-window (Chrome)",
             "Paylocity": "Paylocity's resume upload and its steps after the first are untested in the window - if the resume "
                          "doesn't show as attached, a step doesn't fill, or Submit doesn't go through, fill it again from the "
                          "start without --in-window (Chrome)"}
WHY = {"untrusted": "the Job Finder window is in Restricted Mode (opened without its Desktop icon)",
       "picker": "the window couldn't tell which tab to use",
       "no proxy": "the window's debugger didn't hand over the tab",
       "no tab session": "the window's debugger didn't reach the tab"}
# keys typed by name, as Playwright's: (key, code, Windows key code, text it types); macOS edits + moves only w/
# its command named (Playwright does the same)
KEYS = {"Escape": ("Escape", "Escape", 27, None, None), "Delete": ("Delete", "Delete", 46, None, "deleteForward"),
        "Enter": ("Enter", "Enter", 13, None, None), "Tab": ("Tab", "Tab", 9, None, None),
        "ArrowDown": ("ArrowDown", "ArrowDown", 40, None, "moveDown"), "Space": (" ", "Space", 32, " ", None)}
# held for a combo ("ControlOrMeta+a"): its bit in CDP's modifiers, code, Windows key code
MODIFIERS = {"Alt": (1, "AltLeft", 18), "Control": (2, "ControlLeft", 17), "Meta": (4, "MetaLeft", 91), "Shift": (8, "ShiftLeft", 16)}
# macOS: a combo edits only w/ its command named, as Playwright's (only the ones the fillers press)
MAC_COMBOS = {("Meta", "KeyA"): "selectAll"}
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
# it sits in; asked of the element's own shadow root or frame (a document asked names only the host)
CLICK_POINT = """(e, force) => { e.scrollIntoView({block: 'center', inline: 'center', behavior: 'instant'});
  const r = e.getBoundingClientRect(); if (!r.width || !r.height) return null;
  const x = r.x + r.width / 2, y = r.y + r.height / 2; if (force) return [x, y];
  const t = e.closest('button, [role=button], a, [role=link]') || e, hit = e.getRootNode().elementFromPoint(x, y);
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
# steps -> matching elements under `roots`, in the page - each a port of Playwright's own engine (its injected
# script, 1.5x), so the same selector finds the same elements:
# css [[compound, shown only, combinator to the next], ...] per comma part: the last compound queried inside open
#   shadow roots too, the ones before matched walking up (a shadow root's host counts as a parent), ':scope' =
#   the root; several parts together in page order (shadow children after their host's own)
# xpath (elements only; '/...' under an element = './...'), nth (-1 = last), visible (shown or not, as VISIBLE)
# text [text, exact] (get_by_text: the smallest elements whose text holds it, case and spacing ignored, or is it
#   when exact), label [text, exact] (get_by_label: aria-labelledby, aria-label, else a box's <label>s)
# has (has_text: the elements themselves, kept when their text holds a string as `text` does, or a pattern
#   matches their whole text), inside (filter(has=): kept when the inner steps find something under them)
# role (as get_by_role: shown to a screen reader, accessible name = aria-labelledby, aria-label, a button
#   input's value, else its text; exact = the whole name w/ case, else part of it w/o)
# Text = Playwright's: script, style + <head> skipped, a button input's value, open shadow roots' text included.
RESOLVE = """(function resolve(steps, roots) {
  const norm = (s) => (s || "").replace(/[\\u200b\\u00ad]/g, "").trim().replace(/\\s+/g, " ");
  const low = (s) => norm(s).toLowerCase();
  const shownNow = VISIBLE;
  const up = (e) => e.parentElement || (e.parentNode && e.parentNode.nodeType === 11 && e.parentNode.host) || null;
  const pierce = (scope, css) => { let out = [];
    const q = (r) => { out = out.concat([...r.querySelectorAll(css)]); if (r.shadowRoot) q(r.shadowRoot);
      for (const e of r.querySelectorAll("*")) if (e.shadowRoot) q(e.shadowRoot); };
    q(scope); return out; };
  const sorted = (elements) => { const entries = new Map(), tops = [], out = [];
    const add = (e) => { let entry = entries.get(e); if (entry) return entry; const p = up(e);
      if (p) add(p).children.push(e); else tops.push(e);
      entry = {children: [], taken: false}; entries.set(e, entry); return entry; };
    for (const e of elements) add(e).taken = true;
    const visit = (e) => { const entry = entries.get(e); if (entry.taken) out.push(e);
      if (entry.children.length > 1) { const set = new Set(entry.children); entry.children = [];
        for (let c = e.firstElementChild; c && entry.children.length < set.size; c = c.nextElementSibling) if (set.has(c)) entry.children.push(c);
        for (let c = e.shadowRoot ? e.shadowRoot.firstElementChild : null; c && entry.children.length < set.size; c = c.nextElementSibling)
          if (set.has(c)) entry.children.push(c); }
      entry.children.forEach(visit); };
    tops.forEach(visit); return out; };
  const css = (root, part) => { let scope = root, orig = null;
    if (part.some(([c]) => c === ":scope") && scope.nodeType === 1 && up(scope)) { orig = scope; scope = up(scope); }
    const actual = orig || scope, me = actual.nodeType === 9 ? actual.documentElement : actual;
    const simple = (e, [c, shown]) => e !== scope && (c === ":scope" ? e === me : e.matches(c)) && (!shown || shownNow(e));
    const parent = (e) => e === scope ? null : up(e), prev = (e) => e === scope ? null : e.previousElementSibling;
    const parents = (e, i) => { if (i < 0) return true; const s = part[i], comb = s[2];
      if (comb === ">") { const p = parent(e); return !!p && simple(p, s) && parents(p, i - 1); }
      if (comb === "+") { const p = prev(e); return !!p && simple(p, s) && parents(p, i - 1); }
      const step = comb === "~" ? prev : parent;
      for (let p = step(e); p; p = step(p))
        if (simple(p, s)) { if (parents(p, i - 1)) return true; if (part[i - 1] && part[i - 1][2] === comb) break; }
      return false; };
    const [last, shown] = part[part.length - 1];
    return (last === ":scope" ? [me] : pierce(scope, last)).filter((e) => (!shown || shownNow(e)) && parents(e, part.length - 2)); };
  const xpath = (root, sel) => { if (sel.startsWith("/") && root.nodeType !== 9) sel = "." + sel;
    const doc = root.ownerDocument || root, out = [], it = doc.evaluate(sel, root, null, XPathResult.ORDERED_NODE_ITERATOR_TYPE);
    for (let n = it.iterateNext(); n; n = it.iterateNext()) if (n.nodeType === 1) out.push(n);
    return out; };
  const cache = new Map();
  const skip = (e) => ["SCRIPT", "NOSCRIPT", "STYLE"].includes(e.nodeName) || !!(e.ownerDocument && e.ownerDocument.head && e.ownerDocument.head.contains(e));
  const textOf = (root) => { let v = cache.get(root); if (v) return v;
    v = {full: "", normalized: "", immediate: []};
    if (!skip(root)) {
      if (root.nodeName === "INPUT" && ["submit", "button", "reset"].includes(root.type)) v = {full: root.value, normalized: norm(root.value), immediate: [root.value]};
      else { let now = "";
        for (let c = root.firstChild; c; c = c.nextSibling) {
          if (c.nodeType === 3) { v.full += c.nodeValue || ""; now += c.nodeValue || ""; }
          else if (c.nodeType !== 8) { if (now) v.immediate.push(now); now = ""; if (c.nodeType === 1) v.full += textOf(c).full; } }
        if (now) v.immediate.push(now);
        if (root.shadowRoot) v.full += textOf(root.shadowRoot).full;
        v.normalized = norm(v.full); } }
    cache.set(root, v); return v; };
  const matcher = (t, exact) => { if (t && typeof t === "object") { const re = new RegExp(t.source, t.flags); return (v) => re.test(v.full); }
    const want = norm(t), lower = want.toLowerCase();
    return exact ? (v) => v.normalized === want : (v) => v.normalized.toLowerCase().includes(lower); };
  const matchesText = (e, m) => { if (skip(e) || !m(textOf(e))) return "none";
    for (let c = e.firstChild; c; c = c.nextSibling) if (c.nodeType === 1 && m(textOf(c))) return "selfAndChildren";
    return e.shadowRoot && m(textOf(e.shadowRoot)) ? "selfAndChildren" : "self"; };
  const byText = (root, m, lax) => { const out = []; let miss = null;
    for (const e of [...(root.nodeType === 1 ? [root] : []), ...pierce(root, "*")]) {
      if (lax && miss && miss.contains(e)) continue;
      const got = matchesText(e, m); if (got === "none") miss = e; else if (got === "self") out.push(e); }
    return out; };
  const refs = (e, ref) => { let top = e; while (top.parentNode) top = top.parentNode;
    if (top.nodeType !== 9 && top.nodeType !== 11) return [];
    try { const out = [];
      for (const id of ref.split(" ").filter(Boolean)) { const f = top.querySelector("#" + CSS.escape(id)); if (f && !out.includes(f)) out.push(f); }
      return out; } catch (err) { return []; } };
  const labels = (e) => { const ref = e.getAttribute("aria-labelledby"), by = ref === null ? [] : refs(e, ref);
    if (by.length) return by.map(textOf);
    const al = e.getAttribute("aria-label"); if (al !== null && al.trim()) return [{full: al, normalized: norm(al), immediate: [al]}];
    if (["BUTTON", "METER", "OUTPUT", "PROGRESS", "SELECT", "TEXTAREA"].includes(e.nodeName) || (e.nodeName === "INPUT" && e.type !== "hidden"))
      return e.labels ? [...e.labels].map(textOf) : [];
    return []; };
  const named = (e) => { const by = (e.getAttribute("aria-labelledby") || "").split(/\\s+/).filter(Boolean);
    if (by.length) return by.map((id) => e.getRootNode().getElementById(id)?.textContent || "").join(" ");
    if ((e.getAttribute("aria-label") || "").trim()) return e.getAttribute("aria-label");
    return e.nodeName === "INPUT" ? e.value : e.textContent; };
  const heard = (e) => !e.closest("[aria-hidden=true]") && e.checkVisibility({visibilityProperty: true});
  let els = roots;
  for (const [k, v] of steps) {
    const each = (find) => { const out = new Set(); for (const r of els) for (const e of find(r)) out.add(e); return [...out]; };
    if (k === "css") els = each((r) => v.length === 1 ? css(r, v[0]) : sorted(v.flatMap((part) => css(r, part))));
    else if (k === "xpath") els = each((r) => xpath(r, v));
    else if (k === "nth") { const n = v === -1 ? els.length - 1 : v; els = els.slice(n, n + 1); }
    else if (k === "visible") els = els.filter((e) => shownNow(e) === v);
    else if (k === "text") { const m = matcher(v[0], v[1]); els = each((r) => byText(r, m, typeof v[0] === "string" && !v[1])); }
    else if (k === "label") { const m = matcher(v[0], v[1]); els = each((r) => pierce(r, "*").filter((e) => labels(e).some(m))); }
    else if (k === "has") { const m = matcher(v, false); els = els.filter((e) => m(textOf(e))); }
    else if (k === "inside") els = els.filter((e) => resolve(v, [e]).length > 0);
    else if (k === "role") { const [role, name, exact] = v, extra = ROLES[role];
      els = each((r) => pierce(r, extra ? `[role="${role}"], ${extra}` : `[role="${role}"]`))
        .filter((e) => (!e.hasAttribute("role") || e.getAttribute("role").trim().split(/\\s+/)[0] === role) && heard(e))
        .filter((e) => name === null || (exact ? norm(named(e)) === norm(name) : low(named(e)).includes(low(name)))); }
    else throw new Error("unknown step " + k); }
  return els; })""".replace("ROLES", json.dumps(ROLES)).replace("VISIBLE", VISIBLE)
# what Playwright reads as another engine (text=, role=, internal:...) or a chain (>>): not taken here
ENGINE = re.compile(r"^[a-zA-Z_0-9-]+\s*=|>>")
VISIBLE_PSEUDO = re.compile(r":visible(?![\w-])")


def css_steps(selector: str) -> list:
    """Playwright CSS -> [[compound, shown only, combinator to the next], ...] per top-level comma part.
    ':visible' may close any compound (`div:visible > span`), never sit inside a function; ':scope' only as
    a compound of its own. Native :has() / :not() stay plain CSS: they don't look into shadow roots."""
    parts, depth, quote, escaped, start = [], 0, "", False, 0
    for i, ch in enumerate(selector):
        if escaped:
            escaped = False
        elif ch == "\\":
            escaped = True
        elif quote:
            quote = "" if ch == quote else quote
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
    return [compounds(p.strip(), selector) for p in parts]


def compounds(part: str, selector: str) -> list:
    out, buf, comb, depth, quote, escaped = [], "", None, 0, "", False

    def flush():
        nonlocal buf, comb
        if not buf:
            return
        if out:
            out[-1][2] = comb
        css = buf.strip()
        shown = bool(VISIBLE_PSEUDO.search(top_level(css)))
        css = VISIBLE_PSEUDO.sub("", css) if shown else css
        if VISIBLE_PSEUDO.search(css):
            raise ValueError(f"':visible' inside a function: {selector!r}")
        if ":scope" in css and css != ":scope":
            raise ValueError(f"':scope' only as a part of its own: {selector!r}")
        out.append([css or "*", shown, ""])
        buf, comb = "", None

    for ch in part:
        if escaped:
            escaped = False
        elif ch == "\\":
            escaped = True
        elif quote:
            quote = "" if ch == quote else quote
        elif ch in "'\"":
            quote = ch
        elif ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif not depth and (ch.isspace() or ch in ">+~"):
            flush()
            if ch.isspace():
                comb = "" if comb is None else comb
            elif comb or not out:
                raise ValueError(f"combinator out of place: {selector!r}")
            else:
                comb = ch
            continue
        buf += ch
    flush()
    if comb or not out:
        raise ValueError(f"combinator out of place: {selector!r}")
    return out


def top_level(css: str) -> str:
    """The compound w/ quoted text and function arguments blanked: what a ':visible' found there closes."""
    out, depth, quote, escaped = [], 0, "", False
    for ch in css:
        if escaped:
            escaped = False
            out.append(" ")
            continue
        if ch == "\\":
            escaped = True
        elif quote:
            quote = "" if ch == quote else quote
        elif ch in "'\"":
            quote = ch
        elif ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
            out.append(" ")
            continue
        out.append(ch if not depth and not quote and ch not in "'\"" else " ")
    return "".join(out)


def text_arg(text: "str | re.Pattern"):
    """A string as is, a Python pattern as a JS RegExp, as Playwright passes one: its flags i, s, m only."""
    if isinstance(text, str):
        return text
    if text.flags & ~(re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):
        raise ValueError(f"flags JavaScript can't take: {text!r}")
    flags = "".join(f for f, bit in (("i", re.IGNORECASE), ("s", re.DOTALL), ("m", re.MULTILINE)) if text.flags & bit)
    return {"source": text.pattern, "flags": flags}


def steps_of(selector: str) -> tuple:
    """One Playwright selector -> its step: xpath= (or one starting // or ..), css= or plain CSS."""
    if selector.startswith("xpath="):
        return ("xpath", selector[len("xpath="):])
    if selector.startswith(("//", "..")):
        return ("xpath", selector)
    selector = selector.removeprefix("css=")
    if ENGINE.search(top_level(selector)):
        raise ValueError(f"selector engine not taken in the window: {selector!r}")
    return ("css", css_steps(selector))


class Keyboard:
    """page.keyboard, as Playwright's: a key pressed wherever focus is."""
    def __init__(self, page: "Page"):
        self.page = page

    def press(self, key: str) -> None:
        self.page.key(key)


class Session:
    """page.context.new_cdp_session(page), as Playwright's: the tab's own CDP (dom.closed_shadow)."""
    def __init__(self, cdp: CDP):
        self.cdp = cdp

    def send(self, method: str, params: dict | None = None) -> dict:
        return self.cdp.send(method, params, 30)

    def detach(self) -> None:
        pass  # the connection is the fill's own


class Context:
    def new_cdp_session(self, page: "Page") -> Session:
        return Session(page.cdp)


class Frame:
    """page.frames / page.main_frame, as Playwright's. The main frame runs in the page's own scripts' world; a
    frame inside it in a world of our own (Page.createIsolatedWorld): its page, never its scripts' globals."""
    def __init__(self, page: "Page", frame_id: str | None = None, url: str = ""):
        self.page, self.id, self._url, self.world = page, frame_id, url, None

    @property
    def main(self) -> bool:
        return self is self.page.main_frame

    @property
    def url(self) -> str:
        return self.page.url if self.main else self._url

    def _send(self, method: str, params: dict, timeout: float = 15) -> dict:
        if self.main or "objectId" in params:
            return self.page.cdp.send(method, params, timeout)
        for again in (False, True):
            if self.world is None:
                self.world = self.page.cdp.send("Page.createIsolatedWorld", {"frameId": self.id, "worldName": "jf"})["executionContextId"]
            try:
                return self.page.cdp.send(method, params | {"contextId": self.world}, timeout)
            except RuntimeError as e:  # the frame loaded again: its old world went with it
                if again or "context" not in str(e).lower():
                    raise
                self.world = None

    def call(self, fn: str, *args, root: str | None = None, by_value: bool = True, timeout: float = 15):
        """fn(root, *args) in this frame -> its value (`by_value`), else CDP's handle on it. root = an object's id,
        else the frame's document."""
        common = {"returnByValue": by_value, "awaitPromise": True, "objectGroup": "jf"}
        if root:
            r = self._send("Runtime.callFunctionOn", {"objectId": root, "arguments": [{"value": a} for a in args],
                           "functionDeclaration": f"function (...a) {{ return ({fn})(this, ...a); }}"} | common, timeout)
        else:
            r = self._send("Runtime.evaluate", {"expression": f"({fn})(document, {', '.join(json.dumps(a) for a in args)})"} | common, timeout)
        if "exceptionDetails" in r:
            d = r["exceptionDetails"]
            raise ScriptError(d.get("exception", {}).get("description") or d.get("text"))
        return r.get("result", {}).get("value") if by_value else r.get("result", {})

    def run(self, expr: str, timeout: float = 15):
        if self.main:
            return self.page.run(expr, timeout)
        r = self._send("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True}, timeout)
        if "exceptionDetails" in r:
            d = r["exceptionDetails"]
            raise ScriptError(d.get("exception", {}).get("description") or d.get("text"))
        return r.get("result", {}).get("value")

    def evaluate(self, expr: str, arg=None):
        """As Playwright's: a function is called w/ `arg`, anything else evaluated as written."""
        return self.run(f"({expr})({json.dumps(arg)})" if FUNCTION.match(expr) else expr)

    def evaluate_handle(self, expr: str, arg=None) -> "JSHandle":
        fn = f"(d, arg) => ({expr})(arg)" if FUNCTION.match(expr) else f"(d) => ({expr})"
        return JSHandle.of(self, self.call(fn, arg, by_value=False))

    def locator(self, selector: str, has_text=None) -> "Locator":
        return Locator(self, []).locator(selector, has_text)

    def get_by_role(self, role: str, name: str | None = None, exact: bool = False) -> "Locator":
        return Locator(self, []).get_by_role(role, name, exact)

    def get_by_text(self, text: "str | re.Pattern", exact: bool = False) -> "Locator":
        return Locator(self, []).get_by_text(text, exact)

    def get_by_label(self, text: "str | re.Pattern", exact: bool = False) -> "Locator":
        return Locator(self, []).get_by_label(text, exact)

    def click_at(self, x: float, y: float) -> None:
        """A frame's point -> the tab's: plus where the frame's box sits (in-process frames, one level measured)."""
        if not self.main:
            owner = self.page.cdp.send("DOM.getFrameOwner", {"frameId": self.id})
            box = self.page.cdp.send("DOM.getBoxModel", {"backendNodeId": owner["backendNodeId"]})["model"]["content"]
            x, y = x + box[0], y + box[1]
        self.page.click_at(x, y)


class Page:
    def __init__(self, cdp: CDP):
        self.cdp = cdp
        self.main_frame, self._frames = Frame(self), {}
        # requests in flight, as the tab reports them: idle = none for IDLE_MS (Greenhouse readies its
        # upload with a request after the page has loaded, plan-29g.25)
        # request id -> its frame
        self.inflight, self.moved, self.lock = {}, time.monotonic(), threading.Lock()
        for name in NETWORK:
            cdp.on(name, self._network)
        # js-debug's proxy passes a domain's events on only when asked (adds to what Block asked for);
        # a tab's own CDP (the tests) has no such command and sends them anyway
        for method, params in (("JsDebug.subscribe", {"events": list(NETWORK)}), ("Network.enable", {})):
            with contextlib.suppress(RuntimeError, TimeoutError, Closed):
                cdp.send(method, params, 5)

    def _network(self, params: dict, msg: dict) -> None:
        with self.lock:
            if msg["method"] == "Network.requestWillBeSent":
                self.inflight[params.get("requestId")] = params.get("frameId")
            else:
                self.inflight.pop(params.get("requestId"), None)
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

    @property
    def context(self) -> Context:
        return Context()

    @property
    def frames(self) -> list[Frame]:
        """The main frame, then each frame inside, depth first. The tab's frame tree lists only frames in its
        own process: another site's frame runs in its own (measured, headless Chrome 154) - named by the
        browser's target list, after its parent's other frames; it has a url, never a page to read."""
        try:
            tree = self.cdp.send("Page.getFrameTree", {}, 5)["frameTree"]
        except (RuntimeError, TimeoutError):  # unmeasured through the window's proxy: the page alone
            return [self.main_frame]
        with contextlib.suppress(RuntimeError, TimeoutError):  # unmeasured through the window's proxy
            apart = [t for t in self.cdp.send("Target.getTargets", {}, 5)["targetInfos"] if t["type"] == "iframe"]
            nodes, todo = {}, [tree]
            while todo:
                node = todo.pop()
                nodes[node["frame"]["id"]] = node
                todo += node.get("childFrames") or []
            while add := [t for t in apart if t.get("parentFrameId") in nodes and t["targetId"] not in nodes]:
                for t in add:
                    nodes[t["targetId"]] = {"frame": {"id": t["targetId"], "url": t["url"]}}
                    nodes[t["parentFrameId"]].setdefault("childFrames", []).append(nodes[t["targetId"]])
        out, todo = [], [tree]
        while todo:
            node = todo.pop()
            f, fid = node["frame"], node["frame"]["id"]
            if not out:
                self.main_frame.id = fid
                frame = self.main_frame
            else:
                frame = self._frames.setdefault(fid, Frame(self, fid))
                if frame._url != (url := f.get("url", "") + f.get("urlFragment", "")):
                    frame._url, frame.world = url, None
            out.append(frame)
            todo += reversed(node.get("childFrames") or [])
        return out

    def evaluate(self, expr: str, arg=None):
        return self.main_frame.evaluate(expr, arg)

    def evaluate_handle(self, expr: str, arg=None) -> "JSHandle":
        return self.main_frame.evaluate_handle(expr, arg)

    def locator(self, selector: str, has_text=None) -> "Locator":
        return self.main_frame.locator(selector, has_text)

    def get_by_role(self, role: str, name: str | None = None, exact: bool = False) -> "Locator":
        return self.main_frame.get_by_role(role, name, exact)

    def get_by_text(self, text: "str | re.Pattern", exact: bool = False) -> "Locator":
        return self.main_frame.get_by_text(text, exact)

    def get_by_label(self, text: "str | re.Pattern", exact: bool = False) -> "Locator":
        return self.main_frame.get_by_label(text, exact)

    def goto(self, url: str, timeout: float = TIMEOUT_MS, wait_until: str = "load") -> None:
        """As Playwright's: done at `wait_until` - commit (the new page answered), domcontentloaded, load or
        networkidle."""
        if wait_until not in ("commit", "domcontentloaded", "load", "networkidle"):
            raise ValueError(f"wait_until: {wait_until!r}")
        # the old page marked: done = a page without the mark, loaded
        with contextlib.suppress(RuntimeError, TimeoutError):
            self.run("window.__jfLeaving = true", 5)
        with self.lock:  # the old page's requests end with it, unreported
            self.inflight.clear()
        r = self.cdp.send("Page.navigate", {"url": url}, timeout / 1000)
        if r.get("errorText"):
            raise RuntimeError(f"couldn't open the form: {r['errorText']}")
        if wait_until == "commit":
            return self.quiet()
        ready = "document.readyState !== 'loading'" if wait_until == "domcontentloaded" else "document.readyState === 'complete'"
        self.until(f"!window.__jfLeaving && {ready}", timeout, "page load")
        self.quiet()
        if wait_until == "networkidle":
            self.idle(timeout)

    def wait_for_load_state(self, state: str = "load", timeout: float = TIMEOUT_MS) -> None:
        if state == "domcontentloaded":
            return self.until("document.readyState !== 'loading'", timeout, state)
        self.until("document.readyState === 'complete'", timeout, state)
        if state == "networkidle":
            self.idle(timeout)

    def idle(self, timeout: float) -> None:
        # requests seen leaving and ending, never the page's own list of finished ones (it misses
        # the one still out, and stops counting at 250)
        deadline = time.monotonic() + timeout / 1000
        while True:
            with self.lock:
                busy, quiet = bool(self.inflight), time.monotonic() - self.moved
            if busy:
                self.gone()
                with self.lock:
                    busy = bool(self.inflight)
            if not busy and quiet >= IDLE_MS / 1000:
                return
            if time.monotonic() >= deadline:
                raise TimeoutError(f"networkidle: not after {timeout} ms")
            time.sleep(POLL)

    def gone(self) -> None:
        """Requests of a frame no longer in the tab's tree: another site's frame started loading here and
        finished in its own process, where this tab never hears it end (measured, headless Chrome 154)."""
        with contextlib.suppress(RuntimeError, TimeoutError):
            todo, ids = [self.cdp.send("Page.getFrameTree", {}, 5)["frameTree"]], set()
            while todo:
                node = todo.pop()
                ids.add(node["frame"]["id"])
                todo += node.get("childFrames") or []
            with self.lock:
                for rid in [r for r, f in self.inflight.items() if f and f not in ids]:
                    del self.inflight[rid]

    def wait_for_timeout(self, ms: float) -> None:
        time.sleep(ms / 1000)

    def eval_on_selector_all(self, selector: str, fn: str, arg=None):
        return self.locator(selector).evaluate_all(fn, arg)

    def bring_to_front(self) -> None:
        pass  # the tab is the one the window just opened

    def release(self) -> None:
        """Let go of every handle this fill took."""
        with contextlib.suppress(RuntimeError, TimeoutError, Closed):
            self.cdp.send("Runtime.releaseObjectGroup", {"objectGroup": "jf"}, 5)

    def click_at(self, x: float, y: float) -> None:
        self.cdp.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
        for kind in ("mousePressed", "mouseReleased"):
            self.cdp.send("Input.dispatchMouseEvent", {"type": kind, "x": x, "y": y, "button": "left", "clickCount": 1})

    def key(self, name: str, text: str | None = None) -> None:
        """A key, or a combo as Playwright writes one ("ControlOrMeta+a"): modifiers held, the key pressed,
        let go in reverse. Held Control / Alt / Meta = nothing typed (Playwright's)."""
        held, name = re.fullmatch(r"((?:\w+\+)*)(.+)", name, re.DOTALL).groups()
        held = [("Meta" if sys.platform == "darwin" else "Control") if m == "ControlOrMeta" else m for m in held.split("+") if m]
        if unknown := [m for m in held if m not in MODIFIERS]:
            raise ValueError(f"unknown modifier {unknown[0]!r}")
        key, code, vk, typed, command = KEYS.get(name, (name, None, None, None, None))
        if not code and len(name) == 1 and name.isascii() and name.isalnum():
            code, vk = (f"Digit{name}" if name.isdigit() else f"Key{name.upper()}"), ord(name.upper())
        text = text or typed or (name if len(name) == 1 else None)
        bits = 0
        for m in held:
            bit, mcode, mvk = MODIFIERS[m]
            bits |= bit
            self.cdp.send("Input.dispatchKeyEvent", {"type": "keyDown", "key": m, "code": mcode, "windowsVirtualKeyCode": mvk, "modifiers": bits})
        if held:
            command = MAC_COMBOS.get(("+".join(held), code))
        down = {"type": "keyDown", "key": key, "modifiers": bits} | ({"code": code, "windowsVirtualKeyCode": vk} if code else {})
        if text and not bits & ~MODIFIERS["Shift"][0]:
            down |= {"text": text, "unmodifiedText": text}
        if command and sys.platform == "darwin":
            down["commands"] = [command]
        self.cdp.send("Input.dispatchKeyEvent", down)
        self.cdp.send("Input.dispatchKeyEvent", {"type": "keyUp", "key": key, "modifiers": bits}
                      | ({"code": code, "windowsVirtualKeyCode": vk} if code else {}))
        for m in reversed(held):
            bit, mcode, mvk = MODIFIERS[m]
            bits &= ~bit
            self.cdp.send("Input.dispatchKeyEvent", {"type": "keyUp", "key": m, "code": mcode, "windowsVirtualKeyCode": mvk, "modifiers": bits})


class Locator:
    def __init__(self, frame: Frame, steps: list, root: str | None = None):
        self.frame, self.steps, self.root = frame, steps, root

    @property
    def page(self) -> Page:
        return self.frame.page

    def _with(self, step) -> "Locator":
        return Locator(self.frame, [*self.steps, step], self.root)

    @property
    def first(self) -> "Locator":
        return self.nth(0)

    @property
    def last(self) -> "Locator":
        return self.nth(-1)

    def nth(self, i: int) -> "Locator":
        return self._with(("nth", i))

    def locator(self, selector: str, has_text: "str | re.Pattern | None" = None) -> "Locator":
        found = self._with(steps_of(selector))
        return found if has_text is None else found._with(("has", text_arg(has_text)))

    def filter(self, has_text: "str | re.Pattern | None" = None, has: "Locator | None" = None,
               visible: bool | None = None) -> "Locator":
        """As Playwright's, in its order: text held, then something found inside, then shown or not."""
        out = self
        if has_text is not None:
            out = out._with(("has", text_arg(has_text)))
        if has is not None:
            if has.frame is not self.frame or has.root:
                raise ValueError('Inner "has" locator must belong to the same frame.')
            out = out._with(("inside", has.steps))
        return out if visible is None else out._with(("visible", visible))

    def all(self) -> list["Locator"]:
        """One locator per element there now - no wait, as Playwright's."""
        return [self.nth(i) for i in range(self.count())]

    def get_by_text(self, text: "str | re.Pattern", exact: bool = False) -> "Locator":
        return self._with(("text", [text_arg(text), exact]))

    def get_by_label(self, text: "str | re.Pattern", exact: bool = False) -> "Locator":
        return self._with(("label", [text_arg(text), exact]))

    def get_by_role(self, role: str, name: str | None = None, exact: bool = False) -> "Locator":
        return self._with(("role", [role, name, exact]))

    def _all(self, fn: str, arg=None):
        """fn(elements, arg) in the frame, now - no wait."""
        return self.frame.call(f"(root, steps, arg) => ({fn})({RESOLVE}(steps, [root]), arg)", self.steps, arg, root=self.root)

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

    def check(self, timeout: float | None = None, force: bool = False) -> None:
        self._set_checked(True, timeout, force)

    def uncheck(self, timeout: float | None = None, force: bool = False) -> None:
        self._set_checked(False, timeout, force)

    def _set_checked(self, on: bool, timeout: float | None, force: bool) -> None:
        """As Playwright's: ticked already = nothing; else one click, and a tick that didn't change is an error."""
        if self.is_checked(timeout) == on:
            return
        self.click(timeout=timeout, force=force)
        if self.is_checked(timeout) != on:
            raise RuntimeError("Clicking the checkbox did not change its state")

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
                return self.frame.click_at(*at)
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

    def type(self, text: str, delay: float = 0, timeout: float | None = None) -> None:
        """Playwright's older name for press_sequentially (dom.put_combo, the systems' location boxes)."""
        self.press_sequentially(text, delay, timeout)

    def set_input_files(self, path: str, timeout: float | None = None) -> None:
        self._one("(e) => true", timeout=timeout)
        got = self.frame.call(f"(root, steps) => {RESOLVE}(steps, [root])[0]", self.steps, root=self.root, by_value=False)
        if not got.get("objectId"):
            raise RuntimeError("file box gone")
        self.page.cdp.send("DOM.setFileInputFiles", {"files": [str(Path(path).resolve())], "objectId": got["objectId"]})


class JSHandle:
    """What page / frame.evaluate_handle give, as Playwright's: an object left in the page, read when asked."""
    def __init__(self, frame: Frame, remote: dict):
        self.frame, self.remote = frame, remote

    @staticmethod
    def of(frame: Frame, remote: dict) -> "JSHandle":
        return ElementHandle(frame, remote) if remote.get("subtype") == "node" else JSHandle(frame, remote)

    @property
    def _id(self) -> str | None:
        return self.remote.get("objectId")

    def evaluate(self, fn: str, arg=None):
        if not self._id:  # a plain value: nothing left in the page
            return self.frame.call(f"(d, v, arg) => ({fn})(v, arg)", self.remote.get("value"), arg)
        return self.frame.call(f"(h, arg) => ({fn})(h, arg)", arg, root=self._id)

    def json_value(self):
        return self.frame.call("(h) => h", root=self._id) if self._id else self.remote.get("value")

    def get_property(self, name: str) -> "JSHandle":
        if not self._id:
            return JSHandle.of(self.frame, self.frame.call("(d, v, n) => v[n]", self.remote.get("value"), name, by_value=False))
        return JSHandle.of(self.frame, self.frame.call("(h, n) => h[n]", name, root=self._id, by_value=False))

    def get_properties(self) -> dict[str, "JSHandle"]:
        """Its own enumerable properties (an array's items), as Playwright's."""
        if not self._id:
            return {}
        got = self.frame.page.cdp.send("Runtime.getProperties", {"objectId": self._id, "ownProperties": True})
        return {p["name"]: JSHandle.of(self.frame, p["value"]) for p in got.get("result", []) if p.get("enumerable") and "value" in p}

    def as_element(self) -> "ElementHandle | None":
        return None

    def dispose(self) -> None:
        if self._id:
            with contextlib.suppress(RuntimeError, TimeoutError, Closed):
                self.frame.page.cdp.send("Runtime.releaseObject", {"objectId": self._id}, 5)


class ElementHandle(Locator, JSHandle):
    """One element held, as Playwright's: every Locator method, aimed at that element alone."""
    def __init__(self, frame: Frame, remote: dict):
        Locator.__init__(self, frame, [], remote["objectId"])
        self.remote = remote

    def as_element(self) -> "ElementHandle":
        return self


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
    """A tab on `url` in the Job Finder window, as browser.page_at gives one in Chrome. `match` (a
    multi-page form: the user's own tab, where they are) inside the holder: a held tab it fits ->
    that tab, their place kept; else a fresh tab, held after this run (a fresh tab is page 1 again).
    `before_load(cdp)` runs before the form opens (measuring)."""
    keep = match is not None and holding()
    if keep:
        for tab in [t for t in held if not fits(t)]:  # the user closed it or left the form
            drop(tab)
        if tab := next((t for t in held if fits(t, match)), None):
            try:
                yield tab["page"]
            finally:
                tab["page"].release()
            return
    cdp, session = attach()
    page, tab = Page(cdp), None
    try:
        page.quiet()
        if keep:
            tab = keep_tab(page, session, match)
        if before_load:
            before_load(cdp)
        page.goto(url)
        yield page
    finally:
        page.release()
        if tab is None:
            cdp.close()
            let_go(session)


def attach() -> tuple[CDP, str]:
    """A new tab in the window, our debugger on it -> (its CDP, the session to let go of)."""
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
            return CDP(proxy["host"], int(proxy["port"]), proxy["path"]), session
        except (KeyError, ValueError, TypeError, OSError, Closed):
            let_go(session)
            sys.exit(f"not filled: the window's debugger didn't let us in - {FALLBACK}")


# --- the holder: a multi-page form in the window (plan-k8n.13 F2 = (c), owner 2026-10-07) ---
# One background process stays attached to the form tab between runs, so the user's Next never
# loses their place and no debug session starts or ends under them (each attach / let go flashed
# VS Code's debug toolbar + status bar, measured plan-k8n.12). It skips pauses again after each
# new page and resumes any pause (a site's `debugger;` line would freeze the page while nobody
# runs). `apply-form fill / prepare --in-window` on a multi-page system hand their run to it.
HOLD_STATE, HOLD_LOCK, HOLD_LOG = "window-form.json", "window-form.lock", "window-form.log"
HOLD_IDLE = 30  # s: nothing held + no request -> it exits
HOLD_MAX = 2 * 3600  # s since the last request: lets go of every tab + exits
HOLD_START = 15  # s for a started holder to answer
HOLD_TICK = 1  # s between looks at the held tabs while idle
HELPER = "the window's form helper"
QUIET_ON = ("Debugger.paused", "Page.frameNavigated", "Page.navigatedWithinDocument")

held: list[dict] = []  # tabs kept between runs: {page, session, match}
inside = threading.local()  # set in the thread serving the holder's requests


def holding() -> bool:
    return getattr(inside, "on", False)


def fits(tab: dict, match=None) -> bool:
    """Its tab still open and on the form `match` (default: its own) checks for."""
    if tab["page"].cdp.closed:
        return False
    try:
        return bool((match or tab["match"])(tab["page"].cdp.evaluate("location.href", 5)))
    except (RuntimeError, TimeoutError, Closed, OSError):
        return False


def keep_tab(page: Page, session: str, match) -> dict:
    """Hold this tab: pauses skipped again on each new main-frame page, any pause resumed (measured
    keep_quiet, vscode-browser/measure.py)."""
    cdp = page.cdp
    cdp.keep_events = False  # held for hours: no event log growing

    def requiet(params, msg):
        if msg["method"] == "Debugger.paused":
            cdp.post("Debugger.setSkipAllPauses", {"skip": True})
            cdp.post("Debugger.resume")
        elif not (params.get("frame") or {}).get("parentId"):
            cdp.post("Debugger.setSkipAllPauses", {"skip": True})
    for name in QUIET_ON:
        cdp.on(name, requiet)
    for method, params in (("JsDebug.subscribe", {"events": list(QUIET_ON)}), ("Page.enable", {})):
        with contextlib.suppress(RuntimeError, TimeoutError, Closed):
            cdp.send(method, params, 5)
    tab = {"page": page, "session": session, "match": match}
    held.append(tab)
    return tab


def drop(tab: dict) -> None:
    held.remove(tab)
    tab["page"].cdp.close()
    let_go(tab["session"])


def serve(request: dict) -> tuple[str, "str | int | None"]:
    """One run of form.fill / form.prepare here -> (what it printed, its exit)."""
    import io
    from apply import form
    out, code = io.StringIO(), 0
    try:
        with contextlib.redirect_stdout(out):
            if request.get("step") == "fill":
                form.fill(request["slug"], in_window=True)
            elif request.get("step") == "prepare":
                form.prepare(request["slug"], request["url"], in_window=True)
            else:
                code = f"{HELPER} doesn't know {request.get('step')!r}"
    except SystemExit as e:
        code = e.code
    except Exception as e:  # never a traceback to the user: one line + the Chrome way
        code = f"not filled: {HELPER} hit a problem ({type(e).__name__}) - {FALLBACK}"
    return out.getvalue(), code


def hold() -> None:
    """The holder (`apply-form hold`, started by forward): requests one at a time on this computer
    only, each carrying the token in its state file; exits idle, after HOLD_MAX, or on let-go."""
    import socket
    import cfg
    import locks
    state = cfg.ROOT / ".data" / HOLD_STATE
    server = socket.create_server(("127.0.0.1", 0))
    server.settimeout(HOLD_TICK)
    token = secrets.token_hex(16)
    me = {"pid": os.getpid(), "port": server.getsockname()[1], "token": token}
    state.parent.mkdir(parents=True, exist_ok=True)
    locks.write_atomic(state, json.dumps(me))
    inside.on, last = True, time.monotonic()
    try:
        while True:
            idle = time.monotonic() - last
            if idle > HOLD_MAX or (not held and idle > HOLD_IDLE):
                break
            try:
                conn, _ = server.accept()
            except TimeoutError:
                for tab in [t for t in held if not fits(t)]:
                    drop(tab)
                continue
            with conn:
                conn.settimeout(10)
                try:
                    conn.sendall(b'{"holder": true}\n')
                    request = json.loads(conn.makefile("rb").readline())
                except (OSError, ValueError):
                    continue
                if not isinstance(request, dict) or not secrets.compare_digest(str(request.get("token")), token):
                    continue
                if request.get("step") == "let-go":
                    with contextlib.suppress(OSError):
                        conn.sendall(json.dumps({"out": f"{HELPER} let go of {len(held)} tab(s)\n", "exit": 0}).encode() + b"\n")
                    break
                out, code = serve(request)
                last = time.monotonic()
                with contextlib.suppress(OSError):
                    conn.sendall(json.dumps({"out": out, "exit": code}).encode() + b"\n")
    finally:
        for tab in list(held):
            drop(tab)
        inside.on = False
        server.close()
        with contextlib.suppress(OSError, ValueError):
            if json.loads(state.read_text(encoding="utf-8")) == me:
                state.unlink()


def reach(wait: float = 600):
    """The running holder -> (its socket, token), None when none answers. A busy one (another
    chat's fill) takes up to `wait` s to say hello."""
    import socket
    import cfg
    try:
        known = json.loads((cfg.ROOT / ".data" / HOLD_STATE).read_text(encoding="utf-8"))
        conn = socket.create_connection(("127.0.0.1", int(known["port"])), 2)
    except (OSError, ValueError, KeyError, TypeError):
        return None
    try:
        conn.settimeout(wait)
        if json.loads(conn.makefile("rb").readline()).get("holder") is True:
            conn.settimeout(None)
            return conn, known["token"]
    except (OSError, ValueError, AttributeError):
        pass
    conn.close()
    return None


def start() -> None:
    """The holder as its own process, outliving this run (the terminal's run ends; the tab stays held)."""
    import subprocess
    import cfg
    detach = ({"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt"
              else {"start_new_session": True})
    log = cfg.ROOT / ".data" / HOLD_LOG
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "ab") as err:
        subprocess.Popen([sys.executable, str(Path(__file__).resolve().parents[1] / "jobs.py"), "apply-form", "hold"],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=err, cwd=cfg.ROOT, **detach)


def forward(step: str, slug: str, url: str | None = None) -> None:
    """This run, done by the holder (started first when none runs): its lines printed, its exit ours."""
    import cfg
    import locks
    found = reach()
    if found is None:
        with locks.held(cfg.ROOT / ".data" / HOLD_LOCK, f"another chat is starting {HELPER} - try again in a minute", 30):
            if (found := reach()) is None:
                start()
                deadline = time.monotonic() + HOLD_START
                while (found := reach(5)) is None and time.monotonic() < deadline:
                    time.sleep(0.2)
    if found is None:
        sys.exit(f"not filled: {HELPER} didn't start - {FALLBACK}")
    conn, token = found
    with conn:
        conn.sendall(json.dumps({"token": token, "step": step, "slug": slug, "url": url}).encode() + b"\n")
        try:
            reply = json.loads(conn.makefile("rb").readline())
        except (OSError, ValueError):
            reply = None
    if not isinstance(reply, dict):
        sys.exit(f"not filled: {HELPER} stopped before it answered - {FALLBACK}")
    print(reply.get("out", ""), end="")
    if reply.get("exit") not in (None, 0):
        sys.exit(reply["exit"])


def let_go_all() -> None:
    """`apply-form let-go`: the holder lets go of every tab it keeps and exits."""
    if (found := reach(30)) is None:
        print(f"{HELPER} isn't running - nothing held")
        return
    conn, token = found
    with conn:
        conn.sendall(json.dumps({"token": token, "step": "let-go"}).encode() + b"\n")
        with contextlib.suppress(OSError, ValueError):
            print(json.loads(conn.makefile("rb").readline()).get("out", ""), end="")
