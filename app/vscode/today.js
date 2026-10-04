// Today dashboard: checks .data/today.json (app/today.py) and draws it as one HTML page for a
// webview. Pure (no vscode, no disk): extension.js passes what it read. Titles, companies + the why
// line come from employer postings => data, escaped, never a link or markup.
// Tests: node --test app/vscode/test/*.test.js
const path = require("path");

const VIEW_TYPE = "cezJobFinder.today";
const DATA = path.join(".data", "today.json");
const VERSION = 1;
// files a button may open: the user's own folders + our guides, nothing above the Job Finder folder
const OPENABLE = ["My Jobs/", "My Resume/", "Guides/"];
// Copilot's chat box takes words w/o sending (workbench.action.chat.open isPartialQuery). Claude:
// a fresh sidebar chat w/ the words typed in, not sent (owner 2026-10-03; app-window.md d, j) -
// only on the Claude versions measured + sidebar set, else copy. ChatGPT: no fill (e) => copy.
const FILL = new Set(["copilot"]);
const CHAT_OPEN = { claude: "claude-vscode.sidebar.open", chatgpt: "chatgpt.openSidebar" };
const CLAUDE_ID = "anthropic.claude-code";
// tested range: from 2.1.288 up to (not incl.) the next minor
const CLAUDE_TESTED = { from: [2, 1, 288], below: [2, 2, 0] };
const CLAUDE_NEW_CHAT = "claude-vscode.editor.open";
// Next up: the one most valuable thing today, first found in this order (data order stays
// app/today.py's). No resume yet blocks "Make my resume" => before new jobs
const NEXT_ORDER = [{ section: "interviews" }, { section: "waiting" }, { todo: "import" }, { section: "new" }, { todo: "morning" }];
// setup steps that stop the job search working => above the job sections, yellow; others stay last, quiet
const BLOCKERS = new Set(["import", "morning"]);
// sections past this many jobs draw as one-line rows; new jobs always do, 5 shown, rest in the chat
const ROWS_AFTER = 4;
const NEW_SHOWN = 5;
// status changes: outline, never yellow; closing a job quietest of all
const QUIET = new Set(["closed"]);
// Caladea, shipped in the vsix (OFL, media/fonts/OFL.txt): the webview may load only from there.
// Italic left out: the page sets none
const FONT_DIR = ["media", "fonts"];
const FONTS = { 400: "caladea-regular.woff2", 700: "caladea-bold.woff2" };
// window look (app/look.py, .data/look): word -> switch label + status line once switched.
// Clicked here => extension runs `jobs.py look WORD`; never through the chat
const LOOKS = [
  { word: "auto", label: "Match my computer", done: "Look matches your computer" },
  { word: "light", label: "Light", done: "Light look on" },
  { word: "dark", label: "Dark", done: "Dark look on" },
];
const LOOK_FILE = path.join(".data", "look");

// file text -> word; missing or unknown = auto (as app/look.py reads it)
function lookOf(text) {
  const word = typeof text === "string" ? text.trim().toLowerCase() : "";
  return LOOKS.some((l) => l.word === word) ? word : "auto";
}

function lookDone(word) {
  const found = LOOKS.find((l) => l.word === word);
  return found ? found.done : null;
}

// New section: its own title already says "today"
const ADDED_TODAY = /(^| · )added to your list today(?= · |$)/;

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function str(value, max = 400) {
  return typeof value === "string" ? value.replace(/[\u0000-\u001f\u007f]/g, " ").slice(0, max) : "";
}

// say.json templates => matcher: words exactly as a template, {n} = a job number
function templates(sayJson) {
  return (sayJson.templates || []).map((t) => {
    const parts = t.words.split("{n}").map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    return { id: t.id, label: t.label, words: t.words, re: new RegExp(`^${parts.join("[1-9][0-9]{0,5}")}$`) };
  });
}

function templateFor(words, tpls) {
  return typeof words === "string" ? tpls.find((t) => t.re.test(words)) || null : null;
}

// posting link: https only, copied as is (AGENTS.md: a rebuilt one 404s); anything else => no button
function cleanUrl(url) {
  if (typeof url !== "string" || url.length > 2000 || !/^https:\/\/[^\s"'<>\\]+$/.test(url)) return null;
  try {
    return new URL(url).protocol === "https:" ? url : null;
  } catch {
    return null;
  }
}

// relative path under one of OPENABLE, `/` between parts, no way out of the folder
function cleanPath(rel) {
  if (typeof rel !== "string" || !rel || rel.length > 500 || rel.includes("\\") || rel.includes("\0")) return null;
  if (rel.startsWith("/") || /^[a-zA-Z]:/.test(rel)) return null;
  const parts = rel.split("/");
  if (parts.some((p) => p === ".." || p === "." || p === "")) return null;
  return OPENABLE.some((prefix) => rel.startsWith(prefix)) ? rel : null;
}

// raw today.json => what the page draws + the list of things its buttons do (webview sends an index
// only: words, links + paths never come back from the page)
function model(raw, sayJson) {
  if (!raw || raw.version !== VERSION || !Array.isArray(raw.sections)) return null;
  const tpls = templates(sayJson);
  const actions = [];
  const act = (a) => actions.push(a) - 1;
  const sayButton = (words) => {
    const t = templateFor(words, tpls);
    return t ? { id: t.id, words, label: t.label, action: act({ type: "say", words }) } : null;
  };
  const open = (rel, how) => {
    const clean = cleanPath(rel);
    return clean ? { path: clean, action: act({ type: "open", path: clean, how }) } : null;
  };
  const card = (c) => {
    const num = Number.isInteger(c.num) && c.num > 0 ? c.num : null;
    if (!num) return null;
    const url = cleanUrl(c.url);
    return {
      num, title: str(c.title), company: str(c.company), detail: str(c.detail),
      say: (Array.isArray(c.say) ? c.say : []).map(sayButton).filter(Boolean),
      posting: url ? { action: act({ type: "posting", url }) } : null,
      resume: open(c.resume, "file"),
      folder: open(c.folder, "folder"),
    };
  };
  const line = (x) => (x && typeof x === "object" ? { text: str(x.text), say: x.say ? sayButton(x.say) : null } : null);
  const m = {
    date: str(raw.date, 80),
    progress: str(raw.progress, 200),
    tiles: (Array.isArray(raw.tiles) ? raw.tiles : [])
      .filter((t) => t && Number.isInteger(t.value) && t.value > 0)
      .map((t) => ({ label: str(t.label, 60), value: t.value, section: str(t.section, 30) })),
    sections: raw.sections.filter((s) => s && Array.isArray(s.cards)).map((s) => ({
      id: str(s.id, 30), title: str(s.title, 80), note: str(s.note, 600),
      cards: s.cards.map(card).filter(Boolean), more: line(s.more),
    })),
    todo: (Array.isArray(raw.todo) ? raw.todo : []).map(line).filter(Boolean),
    empty: line(raw.empty),
    // words w/o a job number => a button; "job 12" ones stay example text (job 12 may not exist)
    asks: [],
    examples: [],
    guides: (Array.isArray(raw.guides) ? raw.guides : [])
      .map((g) => (g ? { title: str(g.title, 80), open: open(g.path, "page") } : null))
      .filter((g) => g && g.open),
  };
  for (const ex of Array.isArray(raw.examples) ? raw.examples : []) {
    const said = (Array.isArray(ex) ? ex : []).filter((w) => templateFor(w, tpls)).map((w) => str(w, 100));
    if (said.length && said.every((w) => !/[0-9]/.test(w))) m.asks.push(...said.map(sayButton));
    else if (said.length) m.examples.push(said);
  }
  // new jobs past NEW_SHOWN: the rest in the chat, even when the data's own list fit
  const fresh = m.sections.find((x) => x.id === "new");
  if (fresh) for (const c of fresh.cards) c.detail = c.detail.replace(ADDED_TODAY, "").replace(/^ · /, "");
  const moreNew = tpls.find((t) => t.id === "more_new");
  if (fresh && fresh.cards.length > NEW_SHOWN && !fresh.more && moreNew) fresh.more = { text: "", say: sayButton(moreNew.words) };
  for (const t of m.todo) t.blocks = Boolean(t.say && BLOCKERS.has(t.say.id));
  m.next = nextUp(m);
  m.sections = m.sections.filter((s) => s.cards.length || s.more);
  // tiles in the order of what they tell about (Next up first); progress-only ones after
  const at = (t) => {
    if (m.next && t.section && m.next.section === t.section) return -1;
    const i = m.sections.findIndex((s) => s.id === t.section);
    return i < 0 ? m.sections.length : i;
  };
  m.tiles = m.tiles.map((t, i) => [at(t), i, t]).sort((a, b) => a[0] - b[0] || a[1] - b[1]).map((x) => x[2]);
  m.actions = actions;
  return m;
}

// takes the Next-up item out of its section or setup list (shown once, at the top)
function nextUp(m) {
  for (const want of NEXT_ORDER) {
    const s = want.section && m.sections.find((x) => x.id === want.section && x.cards.length);
    if (s) return { section: s.id, card: s.cards.shift() };
    const i = want.todo ? m.todo.findIndex((t) => t.say && t.say.id === want.todo) : -1;
    if (i >= 0) return { todo: m.todo.splice(i, 1)[0] };
  }
  return null;
}

function versionParts(text) {
  const m = /^(\d+)\.(\d+)\.(\d+)/.exec(String(text || ""));
  return m ? m.slice(1).map(Number) : null;
}

function before(a, b) {
  for (let i = 0; i < 3; i++) if (a[i] !== b[i]) return a[i] < b[i];
  return false;
}

function claudeTested(version) {
  const v = versionParts(version);
  return Boolean(v) && !before(v, CLAUDE_TESTED.from) && before(v, CLAUDE_TESTED.below);
}

// fill = Copilot's box; new = fresh Claude sidebar chat; copy = everything else.
// claude = { version, location } of the installed Claude extension + claudeCode.preferredLocation:
// "panel" would put the new chat in an editor tab over Today => copy instead
function sayMode(ai, claude = {}) {
  if (FILL.has(ai)) return "fill";
  if (ai === "claude" && claudeTested(claude.version) && claude.location === "sidebar") return "new";
  return "copy";
}

// args for claude-vscode.editor.open: no session + words => fresh chat, words typed in, not
// sent; honor-preferred-location => sidebar, never a tab (bundle read: app-window.md d, j)
function claudeNewChatArgs(words) {
  return [undefined, words, undefined, undefined, false, { programmatic: "honor-preferred-location" }];
}

// what a say button's own text reads: fill/new => the label ("Make my resume"); copy => honest
// about what it does ("Copy: resume for job 12")
function sayText(button, mode) {
  return mode === "copy" ? `Copy: ${button.words}` : button.label;
}

function sayTitle(button, mode) {
  if (mode === "fill") return `Puts "${button.words}" in the chat box`;
  if (mode === "new") return "Opens a new chat with these words typed in - press Enter to start";
  return "";
}

function howLine(mode) {
  if (mode === "fill") return "Buttons put the words in the chat box. Nothing is sent until you press Enter.";
  if (mode === "new") return "Buttons open a new chat with the words typed in. Nothing is sent until you press Enter.";
  return "Buttons copy the words. Paste them in the chat box and press Enter.";
}

// job the words name ("resume for job 12" => 12), null for plain asks
function jobOf(words) {
  const m = /\bjob ([1-9][0-9]{0,5})\b/.exec(String(words || ""));
  return m ? Number(m[1]) : null;
}

// status line once the words are in: names the job + where to look (critique P3). Clears after
// CLEAR_MS on the page; the button pressed keeps doneLabel until the next press
function readyLine(mode, num = null, platform = "darwin") {
  const keys = platform === "darwin" ? "Cmd+V" : "Ctrl+V";
  const line = mode === "fill" ? "the words are in the chat box - press Enter to send them."
    : mode === "new" ? "new chat ready on the right - press Enter"
      : `copied - click the chat box, paste (${keys}), press Enter.`;
  return num ? `Job ${num}: ${line}` : line[0].toUpperCase() + line.slice(1);
}

function doneLabel(mode) {
  return mode === "fill" ? "In the chat box" : mode === "new" ? "Ready in chat" : "Copied";
}

const CLEAR_MS = 8000;

// a cold window: Claude starts on the first click (seconds) => the button says so at once, the
// status line once it's slower than SLOW_MS (owner 2026-10-03: "takes long time to load")
const SLOW_MS = 400;

function busyLabel(ai) {
  return ai === "claude" ? "Starting Claude\u2026" : "Opening the chat\u2026";
}

function startingLine(ai) {
  return `${ai === "claude" ? "Starting Claude" : "Opening the chat"} - the first time takes a few seconds`;
}

// one say button press: words into the chat, never sent; returns the mode that ran.
// exec(command, ...args) + copy(text) = vscode calls; busy(on) + status(text, { done, hold }) =
// page feedback (done = the pressed button's label after; hold = line stays until the next one).
// busy at once; starting line if still waiting after SLOW_MS; then ready line, or copy fallback
async function say({ ai, mode, words, platform, exec, copy, status, busy, wait = setTimeout, clear = clearTimeout }) {
  const num = jobOf(words);
  const ready = (ran) => status(readyLine(ran, num, platform), { done: doneLabel(ran) });
  busy(true);
  const slow = wait(() => status(startingLine(ai), { hold: true }), SLOW_MS);
  try {
    if (mode === "fill") {
      try {
        // fills the box, never sends: isPartialQuery
        await exec("workbench.action.chat.open", { query: words, isPartialQuery: true });
        ready(mode);
        return mode;
      } catch {}
    }
    if (mode === "new") {
      try {
        await exec(CLAUDE_NEW_CHAT, ...claudeNewChatArgs(words));
        ready(mode);
        return mode;
      } catch {}
    }
    await copy(words);
    if (CHAT_OPEN[ai]) await Promise.resolve().then(() => exec(CHAT_OPEN[ai])).catch(() => {});
    ready("copy");
    return "copy";
  } finally {
    clear(slow);
    busy(false);
  }
}

// colors = app/window/brand.py tokens (test checks every hex); yellow only on buttons.
// Paper look like the install site (docs/index.html): ink on paper, sections = heading + rule, jobs
// split by rules - no grey panels, no boxed cards; Next up alone keeps one quiet frame.
// --edge = every control's border: ink-2, >= 3:1 on paper + desk (WCAG 1.4.11); yellow button's own
// edge in light = ink-2 too (yellow on paper 1.28:1)
const CSS = `
body.vscode-light { --desk: #ffffff; --text: #000000; --text-2: #3a3a3a; --line: #c8c8c8; --tint: #f3f3f1;
  --edge: #3a3a3a; --go-edge: #3a3a3a; --mark: #ffe433; --mark-2: #f2cf00; --mark-text: #000000; }
body.vscode-dark { --desk: #1c1c1e; --text: #f2f2f2; --text-2: #bdbdbd; --line: #48484a; --tint: #2c2c2e;
  --edge: #bdbdbd; --go-edge: #ffe433; --mark: #ffe433; --mark-2: #f2cf00; --mark-text: #000000; }
body.vscode-high-contrast { --desk: var(--vscode-editor-background); --text: var(--vscode-editor-foreground);
  --text-2: var(--vscode-editor-foreground); --line: var(--vscode-contrastBorder, currentColor);
  --tint: transparent; --edge: var(--vscode-contrastBorder, currentColor); --go-edge: var(--edge); --mark: transparent;
  --mark-2: transparent; --mark-text: var(--vscode-editor-foreground); }
* { box-sizing: border-box; }
body { margin: 0; padding: 0 20px; background: var(--desk); color: var(--text);
  font-family: Caladea, Georgia, "Times New Roman", serif; font-size: 16px; line-height: 1.45;
  font-variant-numeric: lining-nums; }
::selection { background: var(--text); color: var(--desk); }
main { max-width: 52rem; margin: 0 auto; padding: 24px 0 48px; }
h1 { font-size: 2rem; line-height: 1.1; margin: 0 0 4px; }
h1, h2, h3 { text-wrap: balance; }
[tabindex="-1"]:focus { outline: none; }
.skip { position: absolute; left: -10000px; top: 0; }
.skip:focus-within { position: static; display: flex; flex-wrap: wrap; gap: 4px 16px; margin: 0 0 12px; }
.sub { color: var(--text-2); margin: 0 0 2px; }
.top { display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 8px 16px; }
.look { display: inline-flex; border: 1px solid var(--edge); border-radius: 6px; overflow: hidden; margin-top: 6px; }
.look button { border: 0; border-radius: 0; font-weight: 400; padding: 3px 10px; color: var(--text-2); }
.look button + button { border-left: 1px solid var(--edge); }
.look button[aria-pressed="true"] { background: var(--text); color: var(--desk); font-weight: 700; }
.look button[aria-pressed="true"]:hover { background: var(--text); box-shadow: none; }
.how { color: var(--text-2); font-size: 0.92rem; margin: 0 0 20px; }
section { margin: 32px 0 0; }
section > h2 { font-size: 1.2rem; margin: 0; padding: 0 0 6px; border-bottom: 1px solid var(--text); }
.note { color: var(--text-2); font-size: 0.92rem; margin: 10px 0 0; max-width: 42rem; }
.figures { display: flex; flex-wrap: wrap; gap: 4px 28px; margin: 24px 0 0; padding: 0; list-style: none; }
.figures li { display: flex; align-items: baseline; gap: 8px; }
.figures b { font-size: 1.6rem; line-height: 1.1; }
.figures span { color: var(--text-2); font-size: 0.92rem; }
.num, .figures b, .rows h3 b { font-variant-numeric: lining-nums tabular-nums; }
.cards { display: grid; grid-template-columns: 1fr; }
.card { display: flex; flex-direction: column; gap: 2px; min-width: 0; padding: 14px 0; }
.card + .card { border-top: 1px solid var(--line); }
.next .card { border: 1px solid var(--line); border-radius: 8px; padding: 14px 18px; margin-top: 12px; }
.next .card h3 { font-size: 1.3rem; }
.card h3 { font-size: 1.05rem; line-height: 1.3; margin: 0; overflow-wrap: anywhere; }
.num { display: block; font-size: 0.85rem; color: var(--text-2); }
.card p { margin: 0; overflow-wrap: anywhere; }
.detail { color: var(--text-2); font-size: 0.92rem; }
.acts { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: auto; padding-top: 8px; }
.meta { font-size: 0.9rem; color: var(--text-2); margin-left: auto; }
.card .meta { margin: 0 0 0 auto; padding-left: 6px; }
.rows { list-style: none; margin: 0; padding: 0; }
.rows li { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 4px 12px;
  padding: 10px 0; }
.rows li + li { border-top: 1px solid var(--line); }
.rows .what { min-width: 0; flex: 1 1 18rem; overflow-wrap: anywhere; }
.rows .acts { padding-top: 0; }
.rows h3 { display: inline; font: inherit; margin: 0; }
.rows h3 b { font-weight: 700; }
.list { list-style: none; padding: 0; margin: 12px 0 0; display: grid; gap: 8px; }
.list li { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; }
.more { margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--line); }
.later { font-size: 0.92rem; color: var(--text-2); }
.later .acts { padding-top: 12px; }
.says { color: var(--text-2); margin: 12px 0 0; }
.says q { color: var(--text); font-weight: 700; }
.later h3 { font-size: 0.92rem; color: var(--text); margin: 18px 0 0; }
.guides { list-style: none; margin: 4px 0 0; padding: 0; display: flex; flex-wrap: wrap; gap: 4px 20px; }
button { font: inherit; font-size: 0.92rem; font-weight: 700; line-height: 1.3; cursor: pointer; border-radius: 6px;
  padding: 5px 12px; border: 1px solid var(--edge); background: transparent; color: var(--text); text-align: center; }
button:hover { background: var(--tint); box-shadow: inset 0 0 0 1px var(--text); }
button:active { box-shadow: inset 0 0 0 2px var(--text); transform: translateY(1px); }
button.go { background: var(--mark); color: var(--mark-text); border-color: var(--go-edge); }
button.go:hover { background: var(--mark-2); box-shadow: inset 0 0 0 1px var(--mark-text); }
button.go:active { background: var(--mark-2); box-shadow: inset 0 0 0 2px var(--mark-text); }
button.quiet { color: var(--text-2); font-weight: 400; }
button.link { border: 0; padding: 0; background: none; font-weight: 400; color: var(--text); text-align: left;
  text-decoration: underline; text-underline-offset: 2px; }
button.link:hover { background: none; box-shadow: none; text-decoration-thickness: 2px; }
button.link:active { box-shadow: none; text-decoration-thickness: 3px; }
button[disabled] { cursor: progress; opacity: 0.75; }
button:focus-visible { outline: 3px solid var(--text); outline-offset: 2px; }
body.vscode-high-contrast button { border-color: var(--edge); }
body.vscode-high-contrast button.go { border-width: 3px; padding: 3px 10px; }
body.vscode-high-contrast button.quiet { border-style: dashed; }
body.vscode-high-contrast button.link { border: 0; }
body.vscode-high-contrast .look button[aria-pressed="true"] { text-decoration: underline; text-underline-offset: 3px;
  text-decoration-thickness: 2px; }
#status { position: sticky; bottom: 0; margin: 16px 0 0; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--text);
  background: var(--desk); color: var(--text); font-weight: 700; }
#status:empty { display: none; }
`;

// webview URI of each shipped face + the webview's own source (extension.js: asWebviewUri, cspSource)
// => @font-face rules; a URI that could break out of url("") => left out, Georgia instead
function fontFaces(fonts) {
  const safe = (u) => typeof u === "string" && /^[a-z][a-z0-9+.-]*:[^\s"'()\\<>;{}]+$/i.test(u);
  return Object.entries((fonts && fonts.files) || {}).filter(([, u]) => safe(u)).map(([weight, u]) =>
    `@font-face { font-family: Caladea; src: url("${u}") format("woff2"); font-weight: ${Number(weight)}; font-style: normal; font-display: swap; }`)
    .join("\n");
}

// webview page: one inline script + style (nonce); fonts from the webview's own source only
// (the extension's media/fonts, localResourceRoots), nothing else loaded from anywhere
function csp(nonce, fontSource = "") {
  const fonts = typeof fontSource === "string" && /^[^\s;'"<>]+$/.test(fontSource) ? ` font-src ${fontSource};` : "";
  return `default-src 'none'; style-src 'nonce-${nonce}'; script-src 'nonce-${nonce}';${fonts}`;
}

// <head> both pages share
function head(nonce, fonts) {
  return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${csp(nonce, fonts && fonts.source)}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Today</title><style nonce="${nonce}">${fontFaces(fonts)}${CSS}</style></head>`;
}

// page side, sent as its source text (runs in the webview, nothing from this file in scope).
// Keeps scroll, the status line + the pressed button's done state across redraws: the extension
// replaces the html on every show + Today rewrite; vscode.getState survives that (cheaper than
// retainContextWhenHidden, which keeps the whole page alive while hidden)
function page(vscode, doc, win, clearMs, now = () => Date.now()) {
  const state = Object.assign({ y: 0, status: "", until: 0, done: null }, vscode.getState() || {});
  const save = () => vscode.setState(state);
  const box = doc.getElementById("status");
  let timer = null;
  let pressed = null;
  // until = when it clears (0 = stays: a still-running "Starting Claude" line)
  const show = (text, until) => {
    win.clearTimeout(timer);
    box.textContent = text;
    state.status = text;
    state.until = until;
    save();
    if (text && until) timer = win.setTimeout(() => show("", 0), Math.max(0, until - now()));
  };
  // a button's own words, kept before the first change
  const keep = (b) => {
    if (b.dataset.text == null) {
      b.dataset.text = b.textContent;
      b.dataset.name = b.getAttribute("aria-label") || "";
    }
  };
  const label = (b, text) => {
    b.textContent = text;
    if (b.dataset.name) b.setAttribute("aria-label", text + b.dataset.name.slice(b.dataset.text.length));
  };
  // done state: the pressed button reads e.g. "Ready in chat" until the next press
  const mark = () => {
    for (const b of doc.querySelectorAll("button[data-k]")) {
      if (b.getAttribute("aria-busy")) continue;
      const on = Boolean(state.done && state.done.key === b.dataset.k);
      if (!on && !b.dataset.done) continue;
      keep(b);
      label(b, on ? state.done.label : b.dataset.text);
      if (on) b.dataset.done = "1";
      else delete b.dataset.done;
    }
  };
  if (state.status && state.until > now()) show(state.status, state.until);
  else if (state.status) show("", 0);
  mark();
  if (state.y) win.scrollTo(0, state.y);
  let saving = false;
  win.addEventListener("scroll", () => {
    if (saving) return;
    saving = true;
    win.setTimeout(() => { saving = false; state.y = win.scrollY; save(); }, 100);
  });
  doc.addEventListener("click", (e) => {
    const jump = e.target.closest("button[data-jump]");
    if (jump) {
      const to = doc.getElementById(jump.dataset.jump);
      if (to) { to.focus(); to.scrollIntoView({ block: "start" }); }
      return;
    }
    const lk = e.target.closest("button[data-look]");
    if (lk) {
      // marked at once; the window's colors follow when the extension has switched
      for (const o of doc.querySelectorAll("button[data-look]")) o.setAttribute("aria-pressed", String(o === lk));
      vscode.postMessage({ look: lk.dataset.look });
      return;
    }
    const b = e.target.closest("button[data-a]");
    if (!b || b.disabled) return;
    if (state.done) { state.done = null; save(); mark(); }
    pressed = b.dataset.k || null;
    // say button: busy at once, before the chat answers (first one can take seconds)
    if (b.dataset.busy) {
      keep(b);
      label(b, b.dataset.busy);
      b.disabled = true;
      b.setAttribute("aria-busy", "true");
    }
    vscode.postMessage({ action: Number(b.dataset.a) });
  });
  win.addEventListener("message", (e) => {
    const d = e.data || {};
    if (d.type === "status") {
      show(String(d.text || ""), d.hold ? 0 : now() + clearMs);
      if (d.done && pressed) { state.done = { key: pressed, label: String(d.done) }; save(); }
      mark();
    }
    if (d.type === "look") {
      for (const o of doc.querySelectorAll("button[data-look]")) o.setAttribute("aria-pressed", String(o.dataset.look === d.word));
    }
    if (d.type === "busy" && !d.on) {
      for (const b of doc.querySelectorAll("button[aria-busy]")) {
        label(b, b.dataset.text);
        b.disabled = false;
        b.removeAttribute("aria-busy");
      }
      mark();
    }
  });
}

const SCRIPT = `(${page})(acquireVsCodeApi(), document, window, ${CLEAR_MS});`;

// fonts = { source: webview.cspSource, files: { 400: uri, 700: uri } }; none => Georgia
// look = auto | light | dark (lookOf), marked on the switch
function render(m, { mode, nonce, ai = null, fonts = null, look = "auto" }) {
  const h = escapeHtml;
  const btn = (text, action, { cls = "", title = "", busy = "", name = "", key = "", about = "" } = {}) =>
    `<button type="button" data-a="${action}"${key ? ` data-k="${h(key)}"` : ""}${busy ? ` data-busy="${h(busy)}"` : ""}`
    + `${cls ? ` class="${cls}"` : ""}${title ? ` title="${h(title)}"` : ""}${name ? ` aria-label="${h(name)}"` : ""}`
    + `${about ? ` aria-describedby="${h(about)}"` : ""}>${h(text)}</button>`;
  // accessible name carries the job: 10 "Make my resume" buttons read the same to a screen reader
  const named = (text, num) => (num && !text.toLowerCase().includes(`job ${num}`) ? `${text}, Job ${num}` : "");
  // one yellow per card: its first say; status changes outline, closing quieter still
  const say = (b, go, { num = null, name = "", about = "" } = {}) => {
    const text = sayText(b, mode);
    return btn(text, b.action, { cls: go ? "go" : QUIET.has(b.id) ? "quiet" : "", title: sayTitle(b, mode), busy: busyLabel(ai),
      name: name || named(text, num), key: `${num || ""}:${b.id}`, about });
  };
  const acts = (c) => c.say.map((b, i) => say(b, i === 0, { num: c.num })).join("");
  // posting, resume, folder: places to look, not things to do => ink links on one line
  const meta = (c) => {
    const link = (x, text, what) => x && btn(text, x.action, { cls: "link", name: `Open the ${what} for Job ${c.num}` });
    const links = [link(c.posting, "Posting", "posting"), link(c.resume, "Resume", "resume"), link(c.folder, "Folder", "folder")]
      .filter(Boolean);
    return links.length ? `<span class="meta">${links.join(" · ")}</span>` : "";
  };
  const card = (c) => `<article class="card" aria-labelledby="j-${c.num}"><h3 id="j-${c.num}"><span class="num">Job ${c.num}</span> `
    + `${h(c.title)}</h3>` + (c.company ? `<p>${h(c.company)}</p>` : "") + (c.detail ? `<p class="detail">${h(c.detail)}</p>` : "")
    + `<div class="acts">${acts(c)}${meta(c)}</div></article>`;
  // one line a job: number, title, company, detail + its buttons
  const row = (c, links) => `<li><div class="what"><h3 id="j-${c.num}"><b>Job ${c.num}</b> - ${h(c.title)}`
    + `${c.company ? `, ${h(c.company)}` : ""}</h3>${c.detail ? ` <span class="detail">- ${h(c.detail)}</span>` : ""}</div>`
    + `<span class="acts">${acts(c)}${links ? meta(c) : ""}</span></li>`;
  // a line w/ one button: the button's description = the line's own words ("Turn it on" - what?)
  let lines = 0;
  const line = (x, go, name = "") => {
    const id = `l-${lines++}`;
    return `<li><span id="${id}">${h(x.text)}</span>${x.say ? say(x.say, go, { name, about: x.text ? id : "" }) : ""}</li>`;
  };
  const tile = (id) => m.tiles.find((t) => t.section === id);
  const heading = (id, title) => `<h2 id="${id}" tabindex="-1">${h(title)}</h2>`;
  const jumps = [];
  const section = (s) => {
    const rows = s.id === "new" || s.cards.length > ROWS_AFTER;
    const shown = s.id === "new" ? s.cards.slice(0, NEW_SHOWN) : s.cards;
    let more = s.more;
    if (more && s.id === "new") {
      const total = tile("new") ? tile("new").value : s.cards.length;
      const left = total - shown.length - (m.next && m.next.section === "new" ? 1 : 0);
      more = left > 0 ? { ...more, text: `${left} more new ${left === 1 ? "job" : "jobs"}.` } : null;
    }
    // "Show the rest" under two sections => named by its section
    const moreName = more && more.say ? `${sayText(more.say, mode)}: ${s.title}` : "";
    jumps.push([`s-${s.id}`, s.title]);
    return `<section aria-labelledby="s-${h(s.id)}">${heading(`s-${h(s.id)}`, s.title)}`
      + (s.note ? `<p class="note">${h(s.note)}</p>` : "")
      + (rows ? `<ul class="rows">${shown.map((c) => row(c, s.id !== "new")).join("")}</ul>`
        : `<div class="cards">${shown.map(card).join("")}</div>`)
      + (more ? `<ul class="list more">${line(more, false, moreName)}</ul>` : "") + "</section>";
  };
  if (m.next) jumps.push(["s-next", "Next up"]);
  const next = m.next
    ? `<section class="next" aria-labelledby="s-next">${heading("s-next", "Next up")}`
      + (m.next.card ? `<div class="cards">${card(m.next.card)}</div>`
        : `<ul class="list">${line(m.next.todo, true)}</ul>`) + "</section>"
    : "";
  const tiles = m.tiles.length
    ? `<ul class="figures" aria-label="In numbers">${m.tiles.map((t) => `<li><b>${t.value}</b><span>${h(t.label)}</span></li>`).join("")}</ul>` : "";
  const blocking = m.todo.filter((t) => t.blocks);
  const later = m.todo.filter((t) => !t.blocks);
  if (blocking.length) jumps.push(["s-setup", "Finish setting up"]);
  const setup = blocking.length
    ? `<section aria-labelledby="s-setup">${heading("s-setup", "Finish setting up")}<ul class="list">${blocking.map((t) => line(t, true)).join("")}</ul></section>` : "";
  const sections = m.sections.map(section).join("");
  if (later.length) jumps.push(["s-later", "Not finished"]);
  const todo = later.length
    ? `<section class="later" aria-labelledby="s-later">${heading("s-later", "Not finished")}<ul class="list">${later.map((t) => line(t, false)).join("")}</ul></section>` : "";
  const empty = m.empty ? `<section aria-label="Nothing new"><ul class="list">${line(m.empty, true)}</ul></section>` : "";
  jumps.push(["s-say", "What you can say"]);
  const asks = m.asks.length ? `<div class="acts">${m.asks.map((b) => say(b, false)).join("")}</div>` : "";
  const examples = m.examples.length
    ? `<p class="says">For example: ${m.examples.map((ex) => ex.map((w) => `<q>${h(w)}</q>`).join(" or ")).join(" · ")}</p>` : "";
  const guides = m.guides.length
    ? `<h3>Guides</h3><ul class="guides">${m.guides.map((g) => `<li>${btn(g.title, g.open.action, { cls: "link", name: `Open the guide ${g.title}` })}</li>`).join("")}</ul>` : "";
  // keyboard: skip past the header to any section (shown once focused; Tab order = reading order)
  const skip = `<nav class="skip" aria-label="Jump to">${jumps.map(([id, title], i) =>
    `<button type="button" class="link" data-jump="${h(id)}">${i ? "" : "Skip to "}${h(title)}</button>`).join("")}</nav>`;
  return `${head(nonce, fonts)}
<body>${skip}<main><div class="top"><div><h1>Today</h1><p class="sub">${h(m.date)}</p></div>${lookSwitch(lookOf(look))}</div>
<p class="how" id="how">${h(howLine(mode))}</p>
${next}${tiles}${setup}${sections}${todo}${empty}
<section class="later" aria-labelledby="s-say">${heading("s-say", "What you can say")}${asks}${examples}${guides}</section>
<p id="status" role="status" aria-live="polite"></p></main>
<script nonce="${nonce}">${SCRIPT}</script></body></html>`;
}

// Match my computer · Light · Dark: one pressed, in ink (not yellow: yellow = something to do)
function lookSwitch(look) {
  return `<div class="look" role="group" aria-label="Look">${LOOKS.map((l) =>
    `<button type="button" data-look="${l.word}" aria-pressed="${l.word === look}">${escapeHtml(l.label)}</button>`).join("")}</div>`;
}

// why the dashboard can't show (extension.js decides): plain words, what happens next
const FALLBACK = {
  missing: "Today's list isn't made yet. Job Finder makes it when it starts and after each morning check.",
  updating: "Today's list is being updated - this takes a few seconds.",
  unreadable: "Today's list couldn't be read. Trying again usually fixes it.",
};

// shown when today.json is missing, old or broken: Try again rebuilds it; the page view still has everything
function fallback({ nonce, reason = "unreadable", fonts = null }) {
  const why = FALLBACK[reason] || FALLBACK.unreadable;
  return `${head(nonce, fonts)}
<body><main><h1>Today</h1><p class="sub">${escapeHtml(why)}</p>
<div class="acts"><button type="button" class="go" data-a="${TRY_AGAIN}">Try again</button>
<button type="button" data-a="${SHOW_PAGE}">Show the Today page</button></div>
<p id="status" role="status" aria-live="polite"></p></main>
<script nonce="${nonce}">${SCRIPT}</script></body></html>`;
}

// fallback buttons' own action numbers (data actions are 0 up)
const SHOW_PAGE = -1;
const TRY_AGAIN = -2;

module.exports = {
  VIEW_TYPE, DATA, VERSION, OPENABLE, FONT_DIR, FONTS, fontFaces, NEXT_ORDER, NEW_SHOWN, ROWS_AFTER, CHAT_OPEN, CLAUDE_ID, CLAUDE_TESTED, CLAUDE_NEW_CHAT,
  escapeHtml, templates, templateFor, cleanUrl, cleanPath, model, claudeTested, sayMode, claudeNewChatArgs, sayText, sayTitle,
  howLine, jobOf, readyLine, doneLabel, CLEAR_MS, SLOW_MS, busyLabel, startingLine, say,
  LOOKS, LOOK_FILE, lookOf, lookDone, lookSwitch, csp, page, render, FALLBACK, SHOW_PAGE, TRY_AGAIN, fallback,
};
