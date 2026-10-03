"""Any form page read as plain HTML: one snapshot of every form control (frames + open shadow roots),
questions in the shared shape, and a filler that finds each box again by a hook that survives a
reload. For systems whose forms are standard HTML (JazzHR, Paylocity, Dayforce, start boxes of
Paycom / ADP / Oracle / iCIMS) and for apply-form measure - one tested reader, no put_text copies.

Not a system module (systems/ is imported whole by the contract test): systems call it.
"""
import re
from pathlib import Path
from urllib.parse import urlsplit

from apply import answers
from apply.questions import LATER, key_from_title, question, signs

# security checks are the applicant's own step: listed "not readable", never read as zero questions
CAPTCHA_HOSTS = ("hcaptcha.com", "recaptcha.net", "challenges.cloudflare.com")
CAPTCHA_PATHS = {"google.com": "/recaptcha", "www.google.com": "/recaptcha"}
# ids a framework makes per load (Ant rc_select_4, Paylocity spl-form-element_12, React :r3:,
# react-select-5-input, MUI mui-123): on the next load they can name another box, never a hook
GENERATED = [r"^rc_select_\d+$", r"^spl-form-element_\d+$", r"^:r[0-9a-z]+:$", r"react-select-\d+", r"mui-\d+",
             r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", r"\d{3,}"]
DATA_HOOKS = ["data-automation-id", "data-automation", "data-testid", "data-test", "data-qa", "data-cy", "data-field-path"]
AUTOCOMPLETE = {"given-name": "first_name", "family-name": "last_name", "email": "email", "tel": "phone",
                "address-line1": "street", "address-level2": "city", "address-level1": "state", "postal-code": "zip"}
INPUT_KIND = {"email": "email", "tel": "phone", "url": "url", "number": "number", "date": "date", "file": "file"}
REQUIRED_MARK = re.compile(r"\s*(?:\*|\(required\))\s*$", re.I)

# shared by snapshot + fill (runs in each frame): controls, their names and hooks, worked out once
LIB = r"""
const GEN = %s.map(s => new RegExp(s, 'i'));
const DATA = %s;
const norm = s => (s || '').replace(/\s+/g, ' ').trim();
const roots = doc => { const out = [doc];
  for (let i = 0; i < out.length; i++)
    for (const e of out[i].querySelectorAll('*')) if (e.shadowRoot) out.push(e.shadowRoot);
  return out; };
const textOf = e => { if (!e) return ''; const c = e.cloneNode(true);
  for (const x of c.querySelectorAll('input, select, textarea, option, [role=listbox]')) x.remove();
  return norm(c.textContent); };
const byIds = (e, ids) => norm((ids || '').split(/\s+/).map(id => textOf(e.getRootNode().getElementById(id))).join(' '));
// label[for] never crosses a shadow boundary: look in the box's own tree
const nameOf = e => byIds(e, e.getAttribute('aria-labelledby')) || norm(e.getAttribute('aria-label'))
  || (e.id && textOf([...e.getRootNode().querySelectorAll('label')].find(l => l.htmlFor === e.id)))
  || textOf(e.closest('label'))
  || (/^(radio|checkbox|option|switch)$/.test(e.getAttribute('role') || '') ? textOf(e) : '')  // named by their own text
  || norm(e.getAttribute('title')) || norm(e.getAttribute('placeholder')) || '';
const groupName = (box, first) => { const f = box && box.closest ? box : null;
  const lg = f && f.tagName === 'FIELDSET' ? f.querySelector(':scope > legend') : null;
  return (f && f.getAttribute('role') ? nameOf(f) : '') || textOf(lg) || (first && first.name) || ''; };
const shown = e => e.checkVisibility ? e.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}) : !!e.getClientRects().length;
const CAPTCHA = '.g-recaptcha, .h-captcha, .cf-turnstile, [name=g-recaptcha-response], [name=h-captcha-response], [name=cf-turnstile-response]';
// a fieldset's legend names only what is inside it; else the last heading above the box
const section = e => { const f = e.closest('fieldset'), lg = f && f.querySelector(':scope > legend');
  if (lg && !lg.contains(e)) return textOf(lg);
  let root = e.getRootNode(), at = e;
  while (true) { const hs = [...root.querySelectorAll('h1, h2, h3, h4, h5, h6, [role=heading]')]
      .filter(h => h.compareDocumentPosition(at) & Node.DOCUMENT_POSITION_FOLLOWING && !h.contains(at));
    if (hs.length) return textOf(hs[hs.length - 1]);
    if (!root.host) return ''; at = root.host; root = at.getRootNode(); } };
// every control, radio + checkbox sets as one each, in page order
const controls = () => { const out = [], seen = new Set();
  for (const root of roots(document)) {
    for (const e of root.querySelectorAll('input, select, textarea, [role=combobox], [role=radiogroup], [contenteditable=true], [contenteditable=""]')) {
      if (seen.has(e) || e.matches(CAPTCHA) || e.closest(CAPTCHA)) continue;
      const tag = e.tagName.toLowerCase(), role = e.getAttribute('role');
      if (tag === 'input' && e.type === 'hidden') continue;
      if (e.isContentEditable && e.parentElement && e.parentElement.isContentEditable) continue;
      // a radiogroup of native radios (no [role=radio] inside) is read as those radios: an empty
      // rolegroup crashed the whole read (BambooHR, 2026-10-03)
      if (role === 'radiogroup') { const ms = [...e.querySelectorAll('[role=radio]')];
        if (!ms.length) continue;
        ms.forEach(m => seen.add(m)); out.push({kind: 'rolegroup', box: e, members: ms}); continue; }
      if (tag === 'input' && (e.type === 'radio' || e.type === 'checkbox')) {
        const box = e.closest('fieldset, [role=group]');
        const ms = e.name ? [...root.querySelectorAll(`input[type=${e.type}]`)].filter(m => m.name === e.name)
          : box ? [...box.querySelectorAll(`input[type=${e.type}]`)].filter(m => !m.name) : [e];
        ms.forEach(m => seen.add(m));
        out.push({kind: e.type === 'radio' ? 'radio' : (ms.length > 1 ? 'checkboxes' : 'checkbox'), box, members: ms}); continue; }
      seen.add(e);
      const combo = role === 'combobox' || /^react-select-\d+-input$/.test(e.id);
      out.push({kind: combo ? 'combobox' : tag === 'select' ? 'select' : tag === 'textarea' ? 'textarea'
        : e.isContentEditable && tag !== 'input' ? 'editable' : 'input', box: null, members: [e]});
    } }
  return out; };
const first = c => c.members[0];
const labelOf = c => c.kind === 'rolegroup' ? nameOf(c.box)
  : c.kind === 'radio' || c.kind === 'checkboxes' ? groupName(c.box, first(c)) : nameOf(first(c));
const ok = v => v && !GEN.some(r => r.test(v));
// hook: id, else name, else a data-* the page sets, else role + section + label - each only when no
// other control on this frame shares it
const hooks = cs => { const tried = cs.map(c => { const e = c.kind === 'rolegroup' ? c.box : first(c), group = c.members.length > 1;
    const out = [];
    if (!group && ok(e.id)) out.push(`[id="${e.id}"]`);
    if (group && c.box && ok(c.box.id)) out.push(`[id="${c.box.id}"]`);
    if (ok(e.getAttribute('name'))) out.push(`[name="${e.getAttribute('name')}"]`);
    for (const d of DATA) { const x = e.getAttribute(d) || (c.box && c.box.getAttribute(d)); if (ok(x)) out.push(`[${d}="${x}"]`); }
    out.push(`role=${e.getAttribute('role') || c.kind}|${section(e)}|${labelOf(c)}`);
    return out; });
  const count = {}; for (const t of tried) for (const h of t) count[h] = (count[h] || 0) + 1;
  return tried.map(t => t.find(h => count[h] === 1) || t[t.length - 1]); };
"""


def lib() -> str:
    import json
    return LIB % (json.dumps(GENERATED), json.dumps(DATA_HOOKS))


SNAPSHOT = """() => { %s
  const cs = controls(), hs = hooks(cs);
  const opt = m => nameOf(m) || norm(m.value);
  return {captcha: [...document.querySelectorAll(CAPTCHA)].map(e => e.className || e.getAttribute('name')),
    controls: cs.map((c, i) => { const e = first(c), box = c.kind === 'rolegroup' ? c.box : e, ac = norm(e.getAttribute('autocomplete'));
      const data = {}; for (const d of DATA) if (box.getAttribute(d)) data[d] = box.getAttribute(d);
      const label = labelOf(c);
      const options = c.kind === 'select' ? [...e.options].filter(o => o.value !== '').map(o => norm(o.text))
        : c.kind === 'radio' || c.kind === 'checkboxes' || c.kind === 'rolegroup' ? c.members.map(opt) : [];
      const value = c.kind === 'select' ? [...e.selectedOptions].filter(o => o.value !== '').map(o => norm(o.text)).join(', ')
        : ['radio', 'checkboxes', 'checkbox'].includes(c.kind) ? c.members.filter(m => m.checked).map(opt).join(', ')
        : c.kind === 'rolegroup' ? c.members.filter(m => m.getAttribute('aria-checked') === 'true').map(opt).join(', ')
        : c.kind === 'editable' ? norm(e.innerText) : c.kind === 'input' && e.type === 'file' ? '' : (e.value || '');
      return {hook: hs[i], control: c.kind, tag: box.tagName.toLowerCase(),
        type: c.kind === 'rolegroup' || c.kind === 'combobox' && e.tagName !== 'INPUT' ? box.getAttribute('role') : (e.type || ''),
        id: box.id || '', name: e.getAttribute('name') || '', autocomplete: ac, data, label, section: section(box),
        required: !!(c.members.some(m => m.required) || box.getAttribute('aria-required') === 'true' || /\\*|\\(required\\)/i.test(label)),
        options, options_hidden: c.kind === 'combobox', multiple: !!e.multiple,
        visible: c.members.some(shown) || (c.box ? shown(c.box) : false) || c.members.some(m => m.closest('label') && shown(m.closest('label'))),
        value, password: e.type === 'password', in_shadow: e.getRootNode() !== document}; })}; }"""

# the control a hook names, with what fill needs: its kind, label, members (radio / checkbox sets)
FIND = """(hook) => { %s
  const cs = controls(), hs = hooks(cs), i = hs.indexOf(hook);
  if (i < 0) return null;
  const c = cs[i];
  return {kind: c.kind, label: labelOf(c), password: first(c).type === 'password', members: c.members,
    names: c.members.map(m => nameOf(m) || norm(m.value))}; }"""


def captcha_frame(url: str) -> bool:
    u = urlsplit(url)
    host = (u.hostname or "").casefold()
    return any(host == h or host.endswith("." + h) for h in CAPTCHA_HOSTS) or \
        any(host == h and u.path.startswith(p) for h, p in CAPTCHA_PATHS.items())


def site(url: str) -> str:
    """Registrable part, near enough: careers.acme.com and apply.acme.com are one site."""
    host = (urlsplit(url).hostname or "").casefold()
    return ".".join(host.split(".")[-2:])


def frames(page) -> tuple[list, list[dict], list[dict]]:
    """(frames to read, captcha frames, frames on another site). about:blank / srcdoc frames belong
    to the page that made them."""
    home, read, blocked, other = site(page.url), [], [], []
    for frame in page.frames:
        url = frame.url
        if captcha_frame(url):
            blocked.append({"url": url, "why": "not readable - a security check, the applicant's own step"})
        elif frame is page.main_frame or url.startswith(("about:", "data:")) or site(url) == home:
            read.append(frame)
        else:
            other.append({"url": url, "why": "another site's frame - not read"})
    return read, blocked, other


def closed_shadow(page) -> list[dict]:
    """Closed shadow roots: script can't reach inside, Chrome's own tree still names their host."""
    try:
        session = page.context.new_cdp_session(page)
    except Exception:  # not Chrome: nothing to say either way
        return []
    try:
        root = session.send("DOM.getDocument", {"depth": -1, "pierce": True})["root"]
    finally:
        session.detach()
    out, todo = [], [(root, root.get("documentURL", ""))]
    while todo:
        node, url = todo.pop()
        url = node.get("documentURL") or url
        for s in node.get("shadowRoots") or []:
            if s.get("shadowRootType") == "closed":
                out.append({"url": url, "host": node.get("localName", ""), "why": "closed shadow root - not readable"})
        todo += [(c, url) for c in (node.get("children") or []) + (node.get("shadowRoots") or [])
                 + ([node["contentDocument"]] if node.get("contentDocument") else [])]
    return out


def snapshot(page) -> dict:
    """Every form control on the page as read, never opened or typed into. Custom dropdowns (Ant,
    react-select) list nothing until opened: options_hidden, left shut."""
    read, blocked, other = frames(page)
    out = {"url": page.url, "controls": [], "captcha": [], "blocked_frames": blocked, "other_frames": other,
           "not_readable": closed_shadow(page)}
    for frame in read:
        try:
            got = frame.evaluate(SNAPSHOT % lib())
        except Exception as e:  # frame navigating away mid-read
            out["not_readable"].append({"url": frame.url, "why": f"frame could not be read ({type(e).__name__}: {str(e)[:300]})"})
            continue
        out["controls"] += [c | {"frame": frame.url} for c in got["controls"]]
        out["captcha"] += [{"url": frame.url, "marker": m} for m in got["captcha"]]
    return out


def title(label: str) -> str:
    return REQUIRED_MARK.sub("", label).strip()


def kind_of(c: dict) -> str:
    control, options = c["control"], c["options"]
    if control in ("radio", "rolegroup") or (control == "select" and not c["multiple"]):
        return "yesno" if sorted(options) == ["No", "Yes"] else "choice"
    if control in ("checkboxes",) or control == "select":
        return "multichoice"
    if control == "checkbox":
        return "yesno"
    if control == "combobox":
        return "location" if re.search(r"\blocation\b", c["label"], re.I) else "choice"
    if control in ("textarea", "editable"):
        return "longtext"
    return INPUT_KIND.get(c["type"], "text")


def questions(snap: dict, page: str | None = None) -> list[dict]:
    """Shared-shape questions off a snapshot, id = hook. Password + captcha boxes are never
    questions: user_steps names them. A box the page hides that isn't a file or a tick (a
    honeypot, a select behind its custom widget) is left out."""
    out = []
    for c in snap["controls"]:
        if c["password"] or not (c["visible"] or c["control"] in ("radio", "checkbox", "checkboxes") or c["type"] == "file"):
            continue
        kind, name = kind_of(c), title(c["label"])
        key = AUTOCOMPLETE.get(c["autocomplete"].split()[-1] if c["autocomplete"] else "")
        key = key or ("location" if kind == "location" else key_from_title(name, kind))
        out.append(question(c["hook"], name, kind, c["required"], c["options"], key,
                            f"dom:{c['tag']}:{c['type'] or c['control']}", page=page))
    return out


def user_steps(snap: dict) -> list[str]:
    """What the applicant does on the page themselves: passwords, security checks, unreadable parts."""
    steps = [f"password box '{title(c['label']) or c['hook']}' - yours to type" for c in snap["controls"] if c["password"]]
    if snap["captcha"] or snap["blocked_frames"]:
        steps.append("security check (captcha) - yours to do")
    steps += [f"{n['why']}: {n.get('host') or n['url']}" for n in snap["not_readable"]]
    return steps


def find(page, hook: str):
    """(info, member handles) for the control `hook` names, in whichever readable frame shows it."""
    for frame in frames(page)[0]:
        try:
            got = frame.evaluate_handle(FIND % lib(), hook)
        except Exception:
            continue
        if got.evaluate("x => x === null"):
            continue
        info = {k: got.get_property(k).json_value() for k in ("kind", "label", "password", "names")}
        members = [h.as_element() for h in got.get_property("members").get_properties().values()]
        return frame, info, members
    return None


def digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def put_text(el, value: str, kind: str, editable: bool) -> str:
    el.fill(str(value))
    # the page's own checks run on change / blur, not on the typing alone
    el.evaluate("e => { e.dispatchEvent(new Event('change', {bubbles: true})); e.blur(); }")
    got = norm(el.inner_text()) if editable else el.input_value()
    same = digits(got) == digits(str(value)) if kind == "phone" else got == str(value).strip() if editable else got == str(value)
    return "ok" if same else f"FAIL shows '{got}'"


def norm(s: str) -> str:
    return " ".join(s.split())


def put_select(el, value) -> str:
    want = [str(v).strip() for v in (value if isinstance(value, list) else [value])]
    texts = el.evaluate("e => [...e.options].map(o => o.text.replace(/\\s+/g, ' ').trim())")
    if missing := [v for v in want if v not in texts]:
        return f"ASK no option '{missing[0]}'; offered: {', '.join(t for t in texts if t)[:200]}"
    el.select_option(label=want)
    got = el.evaluate("e => [...e.selectedOptions].map(o => o.text.replace(/\\s+/g, ' ').trim())")
    return "ok" if sorted(got) == sorted(want) else f"FAIL shows '{', '.join(got)}'"


def checked(el, role: bool) -> bool:
    return el.get_attribute("aria-checked") == "true" if role else el.evaluate("e => e.checked")


def put_ticks(members, names: list[str], want: list[str], role: bool, single: bool) -> str:
    """Radio / checkbox sets by each option's exact label; ticked by a click like a person's (the
    page's own handlers run), only where the state differs."""
    if missing := [v for v in want if v not in names]:
        return f"ASK no option '{missing[0]}'; offered: {', '.join(names)[:200]}"
    for el, name in zip(members, names):
        if (name in want) != checked(el, role) and not (single and name not in want):
            el.evaluate("e => e.click()")
    wrong = [n for el, n in zip(members, names) if (n in want) != checked(el, role)]
    return "ok" if not wrong else f"FAIL '{wrong[0]}' shows the wrong tick"


def yes(value) -> bool:
    return str(value).strip().casefold() in ("yes", "true")


def put_file(el, path: str) -> str:
    el.set_input_files(path)
    got = el.evaluate("e => e.files[0] ? e.files[0].name : ''")
    return "ok" if got == Path(path).name else "ASK upload not confirmed on page - check the box"


def put_combo(frame, el, value: str, starts: bool) -> str:
    """Type, wait for the list, click the option that is the answer - never the first offered.
    `starts`: Location options carry the region ("Springfield, Illinois, United States")."""
    v = str(value).strip()
    el.click()
    el.fill("")
    el.type(v.split(",")[0] if starts else v[:40], delay=30)
    options = frame.locator("[role=option]")
    try:
        options.first.wait_for(timeout=8000)
    except Exception:
        el.press("Escape")
        return f"ASK nothing on the list matches '{v}'"
    texts = [norm(t) for t in options.all_inner_texts()]
    want = v.casefold()
    hit = next((i for i, t in enumerate(texts) if t.casefold() == want), None)
    if hit is None and starts:
        hit = next((i for i, t in enumerate(texts) if t.casefold().startswith(want)), None)
    if hit is None:
        el.fill("")
        el.press("Escape")
        return f"ASK no option '{v}'; offered: {', '.join(texts[:5])}"
    chosen = texts[hit]
    options.nth(hit).click()
    frame.page.wait_for_timeout(200)
    # an input shows the pick as its value; react-select-like widgets show it beside the input
    shown = el.evaluate("e => [e.value || '', (e.closest('[class*=control], [class*=select]') || e.parentElement).innerText || '']")
    return "ok" if any(chosen.casefold() in norm(s).casefold() for s in shown) else f"FAIL '{chosen}' not selected"


def fill(page, q: dict, resume_file: str | None, later: bool = False) -> str:
    """Type q["answer"] into the box its hook names -> "ok" | "ASK ..." | "FAIL ..." | "LATER ...".
    `later`: a multi-page caller - a box not on this page is filled after Next, not a failure."""
    if signs(q["title"]):
        return "ASK yours to do on the page - agreeing, consenting or signing"
    found = find(page, q["id"])
    if found is None:
        return f"{LATER} on another page of the form" if later else "FAIL question not on page"
    frame, info, members = found
    if info["password"]:
        return "FAIL password box - the user types it"
    # the hook names a box; the label proves it is still the same question (ids get reused)
    if answers.fold(title(info["label"])) != answers.fold(q["title"]):
        return f"FAIL box label changed ('{title(info['label'])}') - read the page again"
    kind, value, control = q["kind"], q["answer"], info["kind"]
    el = members[0]
    if control not in ("radio", "checkboxes", "checkbox"):  # those inputs often sit hidden under a styled label
        el.scroll_into_view_if_needed()
    if kind == "file":
        if q.get("key") not in ("resume", "cover_letter"):
            return f"ASK not the resume box ({q['title']}) - the user uploads their own file there"
        return put_file(el, resume_file) if value is True and resume_file else "skipped - upload not approved"
    if control == "select":
        return put_select(el, "Yes" if kind == "yesno" and yes(value) else "No" if kind == "yesno" else value)
    if control == "checkbox":
        return put_ticks(members, ["yes"], ["yes"] if yes(value) else [], role=False, single=False)
    if control in ("radio", "rolegroup", "checkboxes"):
        want = value if isinstance(value, list) else [("Yes" if yes(value) else "No") if kind == "yesno" else str(value).strip()]
        return put_ticks(members, info["names"], want, role=control == "rolegroup", single=control != "checkboxes")
    if control == "combobox":
        return put_combo(frame, el, value, starts=kind == "location")
    return put_text(el, value, kind, editable=control == "editable")
