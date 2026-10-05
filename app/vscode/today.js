// Today dashboard: checks .data/today.json (app/today.py) and draws it as one HTML page for a
// webview. Pure (no vscode, no disk): extension.js passes what it read. Titles, companies + the why
// line come from employer postings => data, escaped, never markup. Title + company click through our
// own buttons only (posting / company website): the page sends an index, never a URL.
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
const NEXT_ORDER = [{ section: "interviews" }, { section: "waiting" }, { todo: "import" }, { section: "best" }, { todo: "morning" }];
// setup steps that stop the job search working => above the job sections, yellow; others stay last, quiet
const BLOCKERS = new Set(["import", "morning"]);
// sections past this many jobs draw as one-line rows; new jobs always do, 5 shown, rest in the chat
const ROWS_AFTER = 4;
const BEST_SHOWN = 5;
// yellow leads: Next up's main button + each Waiting on you job's - tasks. Every other button
// outlined: options (new jobs), status changes; closing quietest of all (re-critique 2026-10-04 P1)
const LEADS = new Set(["waiting"]);
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
// one click records where a job stands, never through the chat (owner 2026-10-04): say.json id ->
// status set; the status line then offers Undo for UNDO_MS. The user's click = their own record
const STATUS_SET = {
  sent: { state: "applied", done: "marked as sent" },
  heard_back: { state: "heard_back", done: "marked as heard back" },
  closed: { state: "closed", done: "marked as closed" },
};
const UNDO_MS = 10000;

// file text -> word; missing or unknown = auto (as app/look.py reads it)
function lookOf(text) {
  const word = typeof text === "string" ? text.trim().toLowerCase() : "";
  return LOOKS.some((l) => l.word === word) ? word : "auto";
}

function lookDone(word) {
  const found = LOOKS.find((l) => l.word === word);
  return found ? found.done : null;
}

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

// company website: http(s) as stored (app/companies.py keeps only these); none => plain name
function cleanSite(url) {
  if (typeof url !== "string" || url.length > 2000 || !/^https?:\/\/[^\s"'<>\\`]+$/.test(url)) return null;
  try {
    const u = new URL(url);
    return (u.protocol === "https:" || u.protocol === "http:") && u.hostname ? url : null;
  } catch {
    return null;
  }
}

// a link from the page: a tab in this window's own browser when VS Code has one (1.109+), else the
// system browser. http(s) only, anything else does nothing. hasBrowser() / inWindow(url) /
// external(url) = vscode calls; the url goes on as the same string (a rebuilt link 404s).
// Returns where it went: "window" | "external" | null
async function openLink(url, { hasBrowser, inWindow, external }) {
  let scheme;
  try {
    scheme = typeof url === "string" ? new URL(url).protocol : null;
  } catch {
    return null;
  }
  if (scheme !== "https:" && scheme !== "http:") return null;
  if (await Promise.resolve().then(hasBrowser).catch(() => false)) {
    try {
      await inWindow(url);
      return "window";
    } catch {}
  }
  await external(url);
  return "external";
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
    if (!t) return null;
    const num = jobOf(words);
    // status change: recorded here (extension runs status set), not words for the chat
    if (STATUS_SET[t.id] && num) return { id: t.id, words, label: t.label, status: true, action: act({ type: "status", id: t.id, num, words }) };
    return { id: t.id, words, label: t.label, action: act({ type: "say", words }) };
  };
  const open = (rel, how) => {
    const clean = cleanPath(rel);
    return clean ? { path: clean, action: act({ type: "open", path: clean, how }) } : null;
  };
  const card = (c) => {
    const num = Number.isInteger(c.num) && c.num > 0 ? c.num : null;
    if (!num) return null;
    const url = cleanUrl(c.url);
    const site = cleanSite(c.company_url);
    const company = str(c.company);
    return {
      num, title: str(c.title), company, detail: str(c.detail), why: str(c.why),
      say: (Array.isArray(c.say) ? c.say : []).map(sayButton).filter(Boolean),
      posting: url ? { action: act({ type: "posting", url }) } : null,
      site: site && company ? { action: act({ type: "company", url: site }) } : null,
      resume: open(c.resume, "file"),
      folder: open(c.folder, "folder"),
    };
  };
  const guideLink = (g) => {
    const o = open(g.path, "page");
    return o ? { title: str(g.title, 80), open: o } : null;
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
      guide: s.guide && typeof s.guide === "object" ? guideLink(s.guide) : null,
      cards: s.cards.map(card).filter(Boolean), more: line(s.more),
      total: Number.isInteger(s.total) && s.total > 0 ? s.total : null,
    })),
    todo: (Array.isArray(raw.todo) ? raw.todo : []).map(line).filter(Boolean),
    empty: line(raw.empty),
    // words w/o a job number => a button; "job 12" ones stay example text (job 12 may not exist)
    asks: [],
    examples: [],
    guides: (Array.isArray(raw.guides) ? raw.guides : []).map((g) => (g ? guideLink(g) : null)).filter(Boolean),
  };
  for (const ex of Array.isArray(raw.examples) ? raw.examples : []) {
    const said = (Array.isArray(ex) ? ex : []).filter((w) => templateFor(w, tpls)).map((w) => str(w, 100));
    if (said.length && said.every((w) => !/[0-9]/.test(w))) m.asks.push(...said.map(sayButton));
    else if (said.length) m.examples.push(said);
  }
  // best-next jobs past BEST_SHOWN: the rest in the chat, even when the data's own list fit
  const best = m.sections.find((x) => x.id === "best");
  const moreBest = tpls.find((t) => t.id === "more_best");
  if (best && best.cards.length > BEST_SHOWN && !best.more && moreBest) best.more = { text: "", say: sayButton(moreBest.words) };
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
// button text = the action, every AI (owner 2026-10-04: no "Copy: ..." labels); how the words reach
// the chat is said in the how-line, the tooltip and the status line
function sayText(button) {
  return button.label;
}

function sayTitle(button, mode) {
  if (button.status) return "Saves it here, no chat - you can undo it";
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

// ready = the chat extension already running (window warm-up, extension.js): "Starting Claude"
// only when it really is starting (re-critique 2026-10-04)
function busyLabel(ai, ready = false) {
  return ai === "claude" && !ready ? "Starting Claude\u2026" : "Opening the chat\u2026";
}

function startingLine(ai, ready = false) {
  return ai === "claude" && !ready ? "Starting Claude - the first time takes a few seconds" : "Opening the chat - one moment";
}

// a 2nd chat button while one is opening: said, never silently dropped
const STILL_OPENING = "One moment - the last one is still opening.";
const STILL_SAVING = "One moment - the last change is still being saved.";

// status line once a click recorded it / took it back / failed
function statusLine(id, num) {
  return `Job ${num} ${STATUS_SET[id].done}.`;
}

function undoneLine(num) {
  return `Undone - Job ${num} is back where it was.`;
}

function statusFailed(id, num, words) {
  return `Couldn't save that for Job ${num}. Try again, or say "${words}" in the chat.`;
}

const UNDO_FAILED = "Couldn't undo that - tell the chat where the job really stands.";

// one-click status, no chat. run(args) = `jobs.py ...args`, rejects on failure; refresh() =
// rebuild Today (page redraws from it); tell(text, { undo }) = status line, undo => its Undo button.
// One change at a time; Undo takes back the last one only, within UNDO_MS, by the state it set
// (status undo --from: never a later change made in a chat)
function statusKeeper({ run, refresh, tell, now = () => Date.now() }) {
  let busy = false;
  let last = null;
  const once = async (fn) => {
    if (busy) return tell(STILL_SAVING);
    busy = true;
    try { await fn(); } finally { busy = false; }
  };
  return {
    set: (num, id, words = "") => once(async () => {
      const s = STATUS_SET[id];
      if (!s || !Number.isInteger(num) || num < 1) return;
      try {
        await run(["status", "set", String(num), s.state]);
      } catch {
        return tell(statusFailed(id, num, words));
      }
      last = { num, state: s.state, until: now() + UNDO_MS };
      tell(statusLine(id, num), { undo: true });
      refresh();
    }),
    undo: () => once(async () => {
      const was = last;
      last = null;
      if (!was || now() > was.until) return;
      try {
        await run(["status", "undo", String(was.num), "--from", was.state]);
      } catch {
        return tell(UNDO_FAILED);
      }
      tell(undoneLine(was.num));
      refresh();
    }),
  };
}

// one say button press: words into the chat, never sent; returns the mode that ran.
// exec(command, ...args) + copy(text) = vscode calls; busy(on) + status(text, { done, hold }) =
// page feedback (done = the pressed button's label after; hold = line stays until the next one).
// busy at once; starting line if still waiting after SLOW_MS; then ready line, or copy fallback
async function say({ ai, mode, words, platform, exec, copy, status, busy, wait = setTimeout, clear = clearTimeout, warm = false }) {
  const num = jobOf(words);
  const ready = (ran) => status(readyLine(ran, num, platform), { done: doneLabel(ran) });
  busy(true, busyLabel(ai, warm));
  const slow = wait(() => status(startingLine(ai, warm), { hold: true }), SLOW_MS);
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
[tabindex="-1"]:focus { outline: 3px solid var(--text); outline-offset: 4px; }
.skip { position: absolute; left: -10000px; top: 0; }
.skip:focus-within { position: static; display: flex; flex-wrap: wrap; gap: 4px 16px; margin: 0 0 12px; }
.sub { color: var(--text-2); margin: 0 0 2px; }
.top { display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 8px 16px; }
.look { color: var(--text-2); font-size: 0.9rem; margin: 18px 0 0; }
.look button { font-size: 0.9rem; color: var(--text-2); }
.look button[aria-pressed="true"] { color: var(--text); font-weight: 700; text-decoration: none;
  text-decoration-thickness: 2px; text-underline-offset: 4px; }
.how { color: var(--text-2); font-size: 0.92rem; margin: 10px 0 20px; }
section { margin: 32px 0 0; }
section > h2 { font-size: 1.2rem; margin: 0; padding: 0 0 6px; border-bottom: 1px solid var(--text); }
.note { color: var(--text-2); font-size: 0.92rem; margin: 10px 0 0; max-width: 65ch; }
.figures { display: flex; flex-wrap: wrap; gap: 2px 20px; margin: 6px 0 0; padding: 0; list-style: none; }
.figures li { display: flex; align-items: baseline; gap: 6px; }
.figures b { font-size: 1.15rem; line-height: 1.2; }
.figures span { color: var(--text-2); font-size: 0.92rem; }
.num, .figures b, .rows h3 b { font-variant-numeric: lining-nums tabular-nums; }
.cards { display: grid; grid-template-columns: 1fr; }
.card { display: flex; flex-direction: column; gap: 2px; min-width: 0; padding: 14px 0; }
.card + .card { border-top: 1px solid var(--line); }
.next .card { border: 1px solid var(--edge); border-radius: 8px; padding: 14px 18px; margin-top: 12px; }
.next .card h3 { font-size: 1.3rem; }
.card h3 { font-size: 1.05rem; line-height: 1.3; margin: 0; overflow-wrap: anywhere; }
.num { display: block; font-size: 1rem; font-weight: 700; color: var(--text); }
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
.rows .meta { margin-left: 4px; }
.rows .detail { display: inline-block; }
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
button.named { font-size: inherit; font-weight: inherit; line-height: inherit; overflow-wrap: anywhere; }
button[disabled] { cursor: progress; opacity: 0.75; }
button.done, button.done:hover, button.done:active { border-color: transparent; background: none; box-shadow: none;
  transform: none; color: var(--text-2); font-weight: 400; cursor: default; }
button:focus-visible { outline: 3px solid var(--text); outline-offset: 2px; }
body.vscode-high-contrast button { border-color: var(--edge); }
body.vscode-high-contrast button.go { border-width: 3px; padding: 3px 10px; }
body.vscode-high-contrast button.quiet { border-style: dashed; }
body.vscode-high-contrast button.link { border: 0; }
body.vscode-high-contrast .look button[aria-pressed="true"] { text-decoration: underline; text-underline-offset: 3px;
  text-decoration-thickness: 2px; }
.bar { position: sticky; bottom: 0; display: flex; flex-wrap: wrap; align-items: center; gap: 6px 14px; margin: 16px 0 0;
  padding: 10px 14px; border-radius: 8px; border: 1px solid var(--text); background: var(--desk); color: var(--text); }
.bar:has(#status:empty) { display: none; }
#status { margin: 0; font-weight: 700; flex: 1 1 16rem; }
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
function page(vscode, doc, win, clearMs, undoMs, now = () => Date.now()) {
  const state = Object.assign({ y: 0, status: "", until: 0, done: null, undo: false, day: "" }, vscode.getState() || {});
  // kept for Today's own day only: "Ready in chat" from yesterday would read as still waiting
  const day = (doc.body && doc.body.dataset.day) || "";
  // (fallback page: no day => nothing reset)
  const save = () => vscode.setState(state);
  if (day && state.day !== day) { Object.assign(state, { y: 0, status: "", until: 0, done: null, undo: false, day }); save(); }
  const box = doc.getElementById("status");
  const undoBtn = doc.getElementById("undo");
  let timer = null;
  let pressed = null;
  // until = when it clears (0 = stays: a still-running "Starting Claude" line); undo = its Undo
  // button shows as long as the line. Line gone => pressed button's done state goes too
  const show = (text, until, undo = false) => {
    win.clearTimeout(timer);
    box.textContent = text;
    state.status = text;
    state.until = until;
    state.undo = Boolean(text && undo);
    if (undoBtn) {
      undoBtn.hidden = !state.undo;
      if (state.undo) undoBtn.setAttribute("aria-label", `Undo: ${text}`);
    }
    if (!text) state.done = null;
    save();
    if (text && until) timer = win.setTimeout(() => { show("", 0); mark(); }, Math.max(0, until - now()));
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
  // done state: the pressed button reads e.g. "Ready in chat" - plain text, not a button to press
  // again (a 2nd press = a 2nd chat) - until its status line clears or another button is pressed
  const mark = () => {
    for (const b of doc.querySelectorAll("button[data-k]")) {
      if (b.getAttribute("aria-busy")) continue;
      const on = Boolean(state.done && state.done.key === b.dataset.k);
      if (!on && !b.dataset.done) continue;
      keep(b);
      label(b, on ? state.done.label : b.dataset.text);
      if (on) {
        b.dataset.done = "1";
        b.classList.add("done");
        b.setAttribute("aria-disabled", "true");
      } else {
        delete b.dataset.done;
        b.classList.remove("done");
        b.removeAttribute("aria-disabled");
      }
    }
  };
  if (state.status && state.until > now()) show(state.status, state.until, state.undo);
  else if (state.status || state.done) show("", 0);
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
    if (e.target.closest("button[data-undo]")) {
      // once: the button goes at once, the extension's line says how it went
      show(state.status, state.until, false);
      vscode.postMessage({ undo: true });
      return;
    }
    const b = e.target.closest("button[data-a]");
    if (!b || b.disabled || b.dataset.done) return;
    if (state.done) { state.done = null; save(); mark(); }
    pressed = b.dataset.k || null;
    // say button: busy at once, before the chat answers (first one can take seconds)
    // (one already opening => this one isn't marked: the extension says "One moment")
    if (b.dataset.busy && !doc.querySelectorAll("button[aria-busy]").length) {
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
      show(String(d.text || ""), d.hold ? 0 : now() + (d.undo ? undoMs : clearMs), Boolean(d.undo));
      if (d.done && pressed) { state.done = { key: pressed, label: String(d.done) }; save(); }
      mark();
    }
    if (d.type === "look") {
      for (const o of doc.querySelectorAll("button[data-look]")) o.setAttribute("aria-pressed", String(o.dataset.look === d.word));
    }
    // label = the extension's word for it (Claude already running => no "Starting Claude")
    if (d.type === "busy" && d.on && d.label) {
      for (const b of doc.querySelectorAll("button[aria-busy]")) label(b, String(d.label));
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

const SCRIPT = `(${page})(acquireVsCodeApi(), document, window, ${CLEAR_MS}, ${UNDO_MS});`;

// fonts = { source: webview.cspSource, files: { 400: uri, 700: uri } }; none => Georgia
// look = auto | light | dark (lookOf), marked on the switch
// ready = the chat extension already running (busy label says "Opening", not "Starting Claude")
function render(m, { mode, nonce, ai = null, fonts = null, look = "auto", ready = false }) {
  const h = escapeHtml;
  const btn = (text, action, { cls = "", title = "", busy = "", name = "", key = "", about = "" } = {}) =>
    `<button type="button" data-a="${action}"${key ? ` data-k="${h(key)}"` : ""}${busy ? ` data-busy="${h(busy)}"` : ""}`
    + `${cls ? ` class="${cls}"` : ""}${title ? ` title="${h(title)}"` : ""}${name ? ` aria-label="${h(name)}"` : ""}`
    + `${about ? ` aria-describedby="${h(about)}"` : ""}>${h(text)}</button>`;
  // accessible name carries the job: 10 "Make my resume" buttons read the same to a screen reader
  const named = (text, num) => (num && !text.toLowerCase().includes(`job ${num}`) ? `${text}, Job ${num}` : "");
  // yellow = a task (lead): its first say; status changes outline, closing quieter still
  const say = (b, go, { num = null, name = "", about = "" } = {}) => {
    const text = sayText(b, mode);
    // status change: never yellow, never busy (no chat to wait on)
    return btn(text, b.action, { cls: go && !b.status ? "go" : QUIET.has(b.id) ? "quiet" : "", title: sayTitle(b, mode),
      busy: b.status ? "" : busyLabel(ai, ready),
      name: name || named(text, num), key: `${num || ""}:${b.id}`, about });
  };
  const acts = (c, lead) => c.say.map((b, i) => say(b, lead && i === 0, { num: c.num })).join("");
  // resume, folder: places to look, not things to do => ink links on one line
  const meta = (c) => {
    const link = (x, text, what) => x && btn(text, x.action, { cls: "link", name: `Open the ${what} for Job ${c.num}` });
    const links = [link(c.resume, "Resume", "resume"), link(c.folder, "Folder", "folder")].filter(Boolean);
    return links.length ? `<span class="meta">${links.join(" · ")}</span>` : "";
  };
  // title opens the posting, company its website on record (owner 2026-10-03); no link on record
  // => plain words, never a web search
  const title = (c) => (c.posting ? btn(c.title, c.posting.action, { cls: "link named", title: "Open the posting",
    name: `Open the posting for Job ${c.num}: ${c.title}` }) : h(c.title));
  const company = (c) => {
    if (!c.site) return h(c.company);
    const what = `Company website: ${c.company}`;
    return btn(c.company, c.site.action, { cls: "link named", title: what, name: what });
  };
  // detail = where it stands; why = the row's reasons (new jobs)
  const facts = (c) => [c.detail, c.why].filter(Boolean).join(" · ");
  // job number = its id in the chat: bold, body size, same on cards + rows
  const card = (c, lead) => `<article class="card" aria-labelledby="j-${c.num}"><h3 id="j-${c.num}"><span class="num">Job ${c.num}</span> `
    + `${title(c)}</h3>` + (c.company ? `<p>${company(c)}</p>` : "") + (facts(c) ? `<p class="detail">${h(facts(c))}</p>` : "")
    + `<div class="acts">${acts(c, lead)}${meta(c)}</div></article>`;
  // one line a job where it fits: number, title, company, detail/why + its buttons + links
  const row = (c, lead) => `<li><div class="what"><h3 id="j-${c.num}"><b>Job ${c.num}</b> - ${title(c)}`
    + `${c.company ? `, ${company(c)}` : ""}</h3>${facts(c) ? ` <span class="detail">- ${h(facts(c))}</span>` : ""}</div>`
    + `<span class="acts">${acts(c, lead)}${meta(c)}</span></li>`;
  // a line w/ one button: the button's description = the line's own words ("Turn it on" - what?)
  let lines = 0;
  const line = (x, go, name = "") => {
    const id = `l-${lines++}`;
    return `<li><span id="${id}">${h(x.text)}</span>${x.say ? say(x.say, go, { name, about: x.text ? id : "" }) : ""}</li>`;
  };
  const guideBtn = (g, name) => btn(g.title, g.open.action, { cls: "link", name });
  const heading = (id, title) => `<h2 id="${id}" tabindex="-1">${h(title)}</h2>`;
  const jumps = [];
  const section = (s) => {
    const rows = s.id === "best" || s.cards.length > ROWS_AFTER;
    const shown = s.id === "best" ? s.cards.slice(0, BEST_SHOWN) : s.cards;
    let more = s.more;
    if (more && s.id === "best") {
      const total = s.total || s.cards.length;
      const left = total - shown.length - (m.next && m.next.section === "best" ? 1 : 0);
      more = left > 0 ? { ...more, text: `${left} more ${left === 1 ? "job" : "jobs"} to apply to.` } : null;
    }
    // "Show the rest" under two sections => named by its section; "Show more jobs" says it already
    const moreName = more && more.say && s.id !== "best" ? `${sayText(more.say, mode)}: ${s.title}` : "";
    jumps.push([`s-${s.id}`, s.title]);
    const lead = LEADS.has(s.id);
    const note = [s.note ? h(s.note) : "", s.guide ? guideBtn(s.guide, `Open the guide ${s.guide.title}`) : ""].filter(Boolean).join(" ");
    return `<section aria-labelledby="s-${h(s.id)}">${heading(`s-${h(s.id)}`, s.title)}`
      + (note ? `<p class="note">${note}</p>` : "")
      + (rows ? `<ul class="rows">${shown.map((c) => row(c, lead)).join("")}</ul>`
        : `<div class="cards">${shown.map((c) => card(c, lead)).join("")}</div>`)
      + (more ? `<ul class="list more">${line(more, false, moreName)}</ul>` : "") + "</section>";
  };
  if (m.next) jumps.push(["s-next", "Next up"]);
  const next = m.next
    ? `<section class="next" aria-labelledby="s-next">${heading("s-next", "Next up")}`
      + (m.next.card ? `<div class="cards">${card(m.next.card, true)}</div>`
        : `<ul class="list">${line(m.next.todo, true)}</ul>`) + "</section>"
    : "";
  const tiles = m.tiles.length
    ? `<ul class="figures" aria-label="So far">${m.tiles.map((t) => `<li><b>${t.value}</b><span>${h(t.label)}</span></li>`).join("")}</ul>` : "";
  const blocking = m.todo.filter((t) => t.blocks);
  const later = m.todo.filter((t) => !t.blocks);
  if (blocking.length) jumps.push(["s-setup", "Finish setting up"]);
  const setup = blocking.length
    ? `<section aria-labelledby="s-setup">${heading("s-setup", "Finish setting up")}<ul class="list">${blocking.map((t) => line(t, false)).join("")}</ul></section>` : "";
  const sections = m.sections.map(section).join("");
  if (later.length) jumps.push(["s-later", "Not finished"]);
  const todo = later.length
    ? `<section class="later" aria-labelledby="s-later">${heading("s-later", "Not finished")}<ul class="list">${later.map((t) => line(t, false)).join("")}</ul></section>` : "";
  // nothing else on the page => its one button leads
  const empty = m.empty ? `<section aria-label="Nothing new"><ul class="list">${line(m.empty, true)}</ul></section>` : "";
  jumps.push(["s-say", "What you can say"]);
  const asks = m.asks.length ? `<div class="acts">${m.asks.map((b) => say(b, false)).join("")}</div>` : "";
  const examples = m.examples.length
    ? `<p class="says">For example: ${m.examples.map((ex) => ex.map((w) => `<q>${h(w)}</q>`).join(" or ")).join(" · ")}</p>` : "";
  const guides = m.guides.length
    ? `<h3>Guides</h3><ul class="guides">${m.guides.map((g) => `<li>${guideBtn(g, `Open the guide ${g.title}`)}</li>`).join("")}</ul>` : "";
  // keyboard: skip past the header to any section (shown once focused; Tab order = reading order)
  const skip = `<nav class="skip" aria-label="Jump to">${jumps.map(([id, title], i) =>
    `<button type="button" class="link" data-jump="${h(id)}">${i ? "" : "Skip to "}${h(title)}</button>`).join("")}</nav>`;
  return `${head(nonce, fonts)}
<body data-day="${h(m.date)}">${skip}<main><div class="top"><div><h1>Today</h1><p class="sub">${h(m.date)}</p>${tiles}</div></div>
<p class="how" id="how">${h(howLine(mode))}</p>
${next}${setup}${sections}${todo}${empty}
<section class="later" aria-labelledby="s-say">${heading("s-say", "What you can say")}${asks}${examples}${guides}${lookSwitch(lookOf(look))}</section>
${BAR}</main>
<script nonce="${nonce}">${SCRIPT}</script></body></html>`;
}

// status line + its Undo (shown only after a status click), stuck to the window's bottom
const BAR = `<div class="bar"><p id="status" role="status" aria-live="polite"></p><button type="button" id="undo" data-undo="1" hidden>Undo</button></div>`;

// Match my computer · Light · Dark: one pressed, in ink (not yellow: yellow = something to do)
// owner 2026-10-04: picked once, so a quiet line at the bottom, not a control in the header
function lookSwitch(look) {
  return `<p class="look" role="group" aria-label="Look"><span>Look:</span> ${LOOKS.map((l) =>
    `<button type="button" class="link" data-look="${l.word}" aria-pressed="${l.word === look}">${escapeHtml(l.label)}</button>`).join(" · ")}</p>`;
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
${BAR}</main>
<script nonce="${nonce}">${SCRIPT}</script></body></html>`;
}

// fallback buttons' own action numbers (data actions are 0 up)
const SHOW_PAGE = -1;
const TRY_AGAIN = -2;

module.exports = {
  VIEW_TYPE, DATA, VERSION, OPENABLE, FONT_DIR, FONTS, fontFaces, NEXT_ORDER, BEST_SHOWN, ROWS_AFTER, CHAT_OPEN, CLAUDE_ID, CLAUDE_TESTED, CLAUDE_NEW_CHAT,
  escapeHtml, templates, templateFor, cleanUrl, cleanSite, openLink, cleanPath, model, claudeTested, sayMode, claudeNewChatArgs, sayText, sayTitle,
  howLine, jobOf, readyLine, doneLabel, CLEAR_MS, SLOW_MS, busyLabel, startingLine, say, STILL_OPENING, STILL_SAVING,
  STATUS_SET, UNDO_MS, statusLine, undoneLine, statusFailed, UNDO_FAILED, statusKeeper,
  LOOKS, LOOK_FILE, lookOf, lookDone, lookSwitch, csp, page, render, FALLBACK, SHOW_PAGE, TRY_AGAIN, fallback,
};
