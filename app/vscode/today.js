// Today dashboard: checks .data/today.json (app/today.py) and draws it as one HTML page for a
// webview. Pure (no vscode, no disk): extension.js passes what it read. Titles, companies + the why
// line come from employer postings => data, escaped, never markup. Title + company click through our
// own buttons only (posting / company website): the page sends an index, never a URL.
// Tests: node --test app/vscode/test/*.test.js
const path = require("path");
const setup = require("./setup");

const VIEW_TYPE = "cezJobFinder.today";
// first page before setup (START HERE.md): welcome + the setup form + one button putting the answers in their AI's chat (welcome below)
const WELCOME_TYPE = "cezJobFinder.start";
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
// setup steps that stop the job search working => above the job sections, yellow; others stay last, quiet
const BLOCKERS = new Set(["import", "morning"]);
// sections past this many jobs draw as one-line rows; new jobs always do, 10 shown, rest in the chat
const ROWS_AFTER = 4;
const BEST_SHOWN = 10;
// best-next lists: one ("best"), or Today's two - remote + near them (app/today.py BEST_LISTS); each its own "more" words
const BEST_MORE = { best: "more_best", best_remote: "more_remote", best_nearby: "more_nearby" };
const isBest = (id) => Object.prototype.hasOwnProperty.call(BEST_MORE, id);
// two lists => one "Best jobs" section, tabs All · Remote · Nearby (owner 2026-10-29); All = both lists in turn,
// the data's where-first list leading. Tab picked = state.tab, kept across redraws
const BEST_TABS = [{ tab: "all", label: "All" }, { tab: "remote", id: "best_remote", label: "Remote" },
  { tab: "nearby", id: "best_nearby", label: "Nearby" }];
// yellow leads: each Waiting on you job's main button - tasks. Every other button
// outlined: options (new jobs), status changes; closing quietest of all (re-critique 2026-10-04 P1)
const LEADS = new Set(["waiting"]);
// sections drawn folded (owner 2026-10-30): heading + count shown, jobs one click away; opened = state.open
const FOLDED = new Set(["waiting", "follow_up"]);
const QUIET = new Set(["closed"]);
// Literata = the install site's face (one look from site to window; the resume keeps Caladea), shipped in
// the vsix (OFL, media/fonts/OFL-literata.txt; built by app/web/assets.py): the webview may load only from
// there. Variable: each file holds weights 400-700, so 500 + 600 are real cuts
const FONT_DIR = ["media", "fonts"];
const FONTS = { normal: "literata.woff2", italic: "literata-italic.woff2" };
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

// a job's page from Today or the Jobs panel: one pane beside the page, like a mail reader (owner
// 2026-10-13). The next job's page takes its place; the pane closed => the page gets its full
// width back (VS Code drops an empty group). Replaced only while untouched: a page clicked into may
// hold a half-filled form => kept, the next opens beside it (VS Code's own preview-tab rule).
// show(url, open): open() = the page beside. deps: tabs() = every tab now (VS Code keeps one object
// per tab), active() = the focused tab, close(tab), back() = focus to where the click came from,
// wait(ms). Clicks taken one at a time (two at once would both close the same page)
const PANE_POLLS = 40;
const PANE_POLL_MS = 50;
// a page grabs focus as it loads, after the open returns (#v: up to ~0.5 s) => focus put back
// while it settles, never counted as the user's
const PANE_SETTLE_POLLS = 12;

function readingPane({ tabs, active, close, back, wait }) {
  let shown = null;
  let opening = false;
  let queue = Promise.resolve();
  const once = async (url, open) => {
    const before = new Set(tabs());
    const old = shown;
    opening = true;
    try {
      await open(url);
      // the tab can turn up a moment after the command returns (#r: within 0.9 s)
      let fresh = null;
      for (let n = 0; !(fresh = tabs().find((t) => !before.has(t))) && n < PANE_POLLS; n++) await wait(PANE_POLL_MS);
      if (!fresh) return;
      shown = fresh;
      // new one first, then the old: the pane never empties (no close + reopen flicker)
      if (old && tabs().includes(old)) await Promise.resolve().then(() => close(old)).catch(() => {});
      for (let n = 0; n < PANE_SETTLE_POLLS; n++) {
        if (n === 0 || active() === fresh) await Promise.resolve().then(back).catch(() => {});
        await wait(PANE_POLL_MS * 2);
      }
    } finally {
      opening = false;
    }
  };
  return {
    show(url, open) {
      const run = queue.then(() => once(url, open));
      queue = run.catch(() => {});
      return run;
    },
    // the user's focus moved to this tab: the one shown is theirs now, never closed for them
    touched(tab) {
      if (!opening && tab && tab === shown) shown = null;
    },
    get shown() { return shown; },
  };
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
  for (const best of m.sections.filter((x) => isBest(x.id))) {
    const moreBest = tpls.find((t) => t.id === BEST_MORE[best.id]);
    if (best.cards.length > BEST_SHOWN && !best.more && moreBest) best.more = { text: "", say: sayButton(moreBest.words) };
  }
  // All tab's own "more" words (each list keeps its own)
  const moreAll = tpls.find((t) => t.id === "more_best");
  m.moreAll = moreAll && m.sections.filter((x) => isBest(x.id)).length > 1 ? sayButton(moreAll.words) : null;
  for (const t of m.todo) t.blocks = Boolean(t.say && BLOCKERS.has(t.say.id));
  m.sections = m.sections.filter((s) => s.cards.length || s.more);
  // tiles in the order of what they tell about; progress-only ones after
  const at = (t) => {
    const i = m.sections.findIndex((s) => s.id === t.section);
    return i < 0 ? m.sections.length : i;
  };
  m.tiles = m.tiles.map((t, i) => [at(t), i, t]).sort((a, b) => a[0] - b[0] || a[1] - b[1]).map((x) => x[2]);
  m.actions = actions;
  return m;
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

// what a say button's own text reads: fill/new => the label ("Apply"); copy => honest
// about what it does ("Copy: apply to job 12")
// button text = the action, every AI (owner 2026-10-04: no "Copy: ..." labels); how the words reach
// the chat is said in the how-line, the tooltip and the status line
function sayText(button) {
  return button.label;
}

// Apply = resume + form in one run, the resume uploaded w/o another ask when they chose that
// (job-apply skill, owner 2026-10-13): said before the click, not after
const APPLY_TITLE = "Makes your resume for this job and fills the employer's form with it - you check the page and click Submit. ";

function sayTitle(button, mode) {
  if (button.status) return "Saves it here, no chat - you can undo it";
  if (button.id === "apply") return (APPLY_TITLE + sayTitle({ ...button, id: null }, mode)).trim();
  if (mode === "fill") return `Puts "${button.words}" in the chat box`;
  if (mode === "new") return "Opens a new chat with these words typed in - press Enter to start";
  return "";
}

function howLine(mode) {
  if (mode === "fill") return "Buttons put the words in the chat box. Nothing is sent until you press Enter.";
  if (mode === "new") return "Buttons open a new chat with the words typed in. Nothing is sent until you press Enter.";
  return "Buttons copy the words. Paste them in the chat box and press Enter.";
}

// job the words name ("apply to job 12" => 12), null for plain asks
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
// lines(ran) => { text, done }: a page's own words once they're in (the welcome page's), else Today's
async function say({ ai, mode, words, platform, exec, copy, status, busy, wait = setTimeout, clear = clearTimeout, warm = false, lines = null }) {
  const num = jobOf(words);
  const ready = (ran) => {
    const own = lines ? lines(ran) : null;
    status(own ? own.text : readyLine(ran, num, platform), { done: own ? own.done : doneLabel(ran) });
  };
  busy(true, busyLabel(ai, warm));
  const slow = wait(() => status(startingLine(ai, warm), { hold: true }), SLOW_MS);
  try {
    // send = Copilot from the welcome page's start button (owner 2026-10-08: "automatic"): fill first -
    // a fill never waits on a signed-out Copilot (a send w/o isPartialQuery waits up to 60 s for its
    // agent) - then VS Code's own Send on what's in the box. Send failed => the words stay, said as a fill.
    // Claude + ChatGPT can't: their chat boxes fill only (app-window.md #v)
    if (mode === "send") {
      let filled = false;
      try {
        await exec("workbench.action.chat.open", { query: words, isPartialQuery: true });
        filled = true;
        await exec("workbench.action.chat.submit");
        ready(mode);
        return mode;
      } catch {}
      if (filled) {
        ready("fill");
        return "fill";
      }
    }
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

// colors = app/window/brand.py tokens (test checks every hex); yellow only on buttons + the last job clicked.
// Paper look like the install site (docs/index.html): ink on paper, sections = heading + rule, jobs
// split by rules - no grey panels, no boxed cards.
// --edge = every control's border: ink-2, >= 3:1 on paper + desk (WCAG 1.4.11); yellow button's own
// edge in light = ink-2 too (yellow on paper 1.28:1)
const CSS = `
body.vscode-light { --desk: #ffffff; --text: #000000; --text-2: #3a3a3a; --line: #c8c8c8; --tint: #f3f3f1;
  --edge: #3a3a3a; --go-edge: #3a3a3a; --mark: #ffe433; --mark-2: #f2cf00; --mark-text: #000000;
  --hl: rgba(255, 228, 51, 0.32); }
body.vscode-dark { --desk: #1c1c1e; --text: #f2f2f2; --text-2: #bdbdbd; --line: #48484a; --tint: #2c2c2e;
  --edge: #bdbdbd; --go-edge: #ffe433; --mark: #ffe433; --mark-2: #f2cf00; --mark-text: #000000;
  --hl: rgba(255, 228, 51, 0.16); }
body.vscode-high-contrast { --desk: var(--vscode-editor-background); --text: var(--vscode-editor-foreground);
  --text-2: var(--vscode-editor-foreground); --line: var(--vscode-contrastBorder, currentColor);
  --tint: transparent; --edge: var(--vscode-contrastBorder, currentColor); --go-edge: var(--edge); --mark: transparent;
  --mark-2: transparent; --mark-text: var(--vscode-editor-foreground); --hl: transparent; }
* { box-sizing: border-box; }
body { margin: 0; padding: 0 20px; background: var(--desk); color: var(--text);
  font-family: Literata, Georgia, "Times New Roman", serif; font-size: 16px; line-height: 1.45;
  font-variant-numeric: lining-nums; }
::selection { background: var(--text); color: var(--desk); }
main { max-width: 52rem; margin: 0 auto; padding: 24px 0 48px; }
h1 { font-size: 2rem; line-height: 1.1; font-weight: 700; letter-spacing: -0.012em; margin: 0 0 4px; }
h1, h2, h3 { text-wrap: balance; }
/* the site's weights (app/docs/site.md): display line bold, headings + bold + labels + controls semibold, quiet
   small lines medium (thin strokes in grey read faint at regular) */
h2, h3, b, strong { font-weight: 600; }
.sub, .look, .how, .note, .figures span, .detail, .meta, .later, .hint, .peek, .after-help, .after-or { font-weight: 500; }
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
section > h2, .fold > summary h2 { font-size: 1.2rem; margin: 0; padding: 0 0 6px; border-bottom: 1px solid var(--text); }
/* folded section: the heading is the toggle, a triangle before it turns when open */
.fold > summary { list-style: none; cursor: pointer; }
.fold > summary::-webkit-details-marker { display: none; }
.fold > summary h2::before { content: "\\25B8"; display: inline-block; width: 1.1em; transition: transform 0.15s; }
.fold[open] > summary h2::before { transform: rotate(90deg); }
.fold > summary .count { color: var(--text-2); font-size: 0.9rem; font-weight: 500; font-variant-numeric: lining-nums tabular-nums; }
.fold > summary:focus-visible { outline: 3px solid var(--text); outline-offset: 4px; }
.note { color: var(--text-2); font-size: 0.92rem; margin: 10px 0 0; max-width: 65ch; }
.figures { display: flex; flex-wrap: wrap; gap: 2px 20px; margin: 6px 0 0; padding: 0; list-style: none; }
.figures li { display: flex; align-items: baseline; gap: 6px; }
.figures b { font-size: 1.15rem; line-height: 1.2; }
.figures span { color: var(--text-2); font-size: 0.92rem; }
.num, .figures b, .rows h3 b { font-variant-numeric: lining-nums tabular-nums; }
.cards { display: grid; grid-template-columns: 1fr; }
.card { display: flex; flex-direction: column; gap: 2px; min-width: 0; padding: 14px 0; }
.card + .card { border-top: 1px solid var(--line); }
.card h3 { font-size: 1.05rem; line-height: 1.3; margin: 0; overflow-wrap: anywhere; }
.num { display: block; font-size: 1rem; font-weight: 600; color: var(--text); }
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
.rows h3 b { font-weight: 600; }
/* last job clicked: soft yellow behind it, so it's found again after the page rewraps (user picked it
   2026-10-29 over a ring, bar, tag + highlighted number). Reaches 12px past the text left + right (body
   gutter is 20px), never over the rules above + below */
.last { background: var(--hl); border-radius: 6px; }
.rows .last, .cards .card.last { margin: 0 -12px; padding-left: 12px; padding-right: 12px; }
.rows .last + li, .card.last + .card { border-top-color: transparent; }
body.vscode-high-contrast .last { outline: 2px solid var(--edge); }
.list { list-style: none; padding: 0; margin: 12px 0 0; display: grid; gap: 8px; }
.list li { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; }
/* Best jobs tabs: stick to the window's top while its list scrolls by; picked one ink + underlined, like Look */
.tabs { position: sticky; top: 0; z-index: 1; display: flex; flex-wrap: wrap; gap: 0 22px; margin: 0;
  padding: 6px 0 0; background: var(--desk); border-bottom: 1px solid var(--line); }
.tabs button { border: 0; border-radius: 0; background: none; padding: 8px 2px 6px; margin-bottom: -1px;
  border-bottom: 3px solid transparent; color: var(--text-2); font-size: 1rem; font-weight: 500; }
.tabs button:hover { background: none; box-shadow: none; color: var(--text); border-bottom-color: var(--line); }
.tabs button:active { box-shadow: none; transform: none; }
.tabs button[aria-selected="true"] { color: var(--text); font-weight: 600; border-bottom-color: var(--text); }
.tabs .count { color: var(--text-2); font-size: 0.85rem; font-weight: 500; font-variant-numeric: lining-nums tabular-nums; }
body.vscode-high-contrast .tabs button { border: 0; border-bottom: 3px solid transparent; }
body.vscode-high-contrast .tabs button[aria-selected="true"] { border-bottom-color: var(--edge); }
.more { margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--line); }
.later { font-size: 0.92rem; color: var(--text-2); }
.later .acts { padding-top: 12px; }
.says { color: var(--text-2); margin: 12px 0 0; }
.says q { color: var(--text); font-weight: 600; }
.later h3 { font-size: 0.92rem; color: var(--text); margin: 18px 0 0; }
.guides { list-style: none; margin: 4px 0 0; padding: 0; display: flex; flex-wrap: wrap; gap: 4px 20px; }
button { font: inherit; font-size: 0.92rem; font-weight: 600; line-height: 1.3; cursor: pointer; border-radius: 6px;
  padding: 5px 12px; border: 1px solid var(--edge); background: transparent; color: var(--text); text-align: center; }
button:hover { background: var(--tint); box-shadow: inset 0 0 0 1px var(--text); }
button:active { box-shadow: inset 0 0 0 2px var(--text); transform: translateY(1px); }
button.go { background: var(--mark); color: var(--mark-text); border-color: var(--go-edge); }
button.go:hover { background: var(--mark-2); box-shadow: inset 0 0 0 1px var(--mark-text); }
button.go:active { background: var(--mark-2); box-shadow: inset 0 0 0 2px var(--mark-text); }
button.quiet { color: var(--text-2); font-weight: 500; }
button.link { border: 0; padding: 0; background: none; font-weight: inherit; color: var(--text); text-align: left;
  text-decoration: underline; text-underline-offset: 2px; }
/* text-link buttons + summaries: 19px of text, a 25px box to hit (WCAG 2.2 target size 24px) - padding out, the same
   margin back in, so nothing on the page moves */
button.link, summary { padding: 3px 2px; margin: -3px -2px; }
button.link:hover { background: none; box-shadow: none; text-decoration-thickness: 2px; }
button.link:active { box-shadow: none; text-decoration-thickness: 3px; }
button.named { font-size: inherit; font-weight: inherit; line-height: inherit; overflow-wrap: anywhere; }
button[disabled] { cursor: progress; opacity: 0.75; }
button.done, button.done:hover, button.done:active { border-color: transparent; background: none; box-shadow: none;
  transform: none; color: var(--text-2); font-weight: 500; cursor: default; }
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
/* the line rises into place + fades in, and leaves the way it came (Apple: exit along the entry path), its last words
   still on it (data-gone, set as it clears) until it has gone. 180 ms; reduced motion: the fade alone */
.bar { transition: opacity 180ms ease-out, display 180ms allow-discrete; }
.bar:has(#status:empty) { opacity: 0; }
@starting-style { .bar { opacity: 0; } }
.bar:has(#status:empty)::before { content: attr(data-gone); flex: 1 1 16rem; font-weight: 600; }
.bar:has(#status:empty) #status { display: none; }
@media (prefers-reduced-motion: no-preference) {
  .bar { transition: opacity 180ms ease-out, transform 180ms ease-out, display 180ms allow-discrete; }
  .bar:has(#status:empty) { transform: translateY(8px); }
  @starting-style { .bar { transform: translateY(8px); } }
}
#status { margin: 0; font-weight: 600; flex: 1 1 16rem; }
.steps { list-style: none; counter-reset: step; margin: 28px 0 0; padding: 0; display: grid; gap: 26px; }
.steps > li { counter-increment: step; display: grid; grid-template-columns: 32px minmax(0, 1fr); gap: 0 14px; }
.steps > li::before { content: counter(step); width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center;
  background: var(--text); color: var(--desk); font-weight: 600; font-size: 1.05rem; }
.steps > li > * { grid-column: 2; }
.steps h2 { font-size: 1.25rem; line-height: 1.2; margin: 3px 0 6px; }
.steps p { margin: 0; max-width: 62ch; }
.steps .acts { padding-top: 12px; }
button.big { font-size: 1.15rem; padding: 10px 24px; }
.alert { border: 1px solid var(--text); border-radius: 8px; padding: 12px 16px; margin: 20px 0 0; }
.alert p { margin: 0; }
`;

// webview URI of each shipped face + the webview's own source (extension.js: asWebviewUri, cspSource)
// => @font-face rules; a URI that could break out of url("") => left out, Georgia instead
function fontFaces(fonts) {
  const safe = (u) => typeof u === "string" && /^[a-z][a-z0-9+.-]*:[^\s"'()\\<>;{}]+$/i.test(u);
  return Object.entries((fonts && fonts.files) || {}).filter(([style, u]) => style in FONTS && safe(u)).map(([style, u]) =>
    `@font-face { font-family: Literata; src: url("${u}") format("woff2"); font-weight: 400 700; font-style: ${style}; font-display: swap; }`)
    .join("\n");
}

// webview page: one inline script + style (nonce); fonts from the webview's own source only
// (the extension's media/fonts, localResourceRoots), nothing else loaded from anywhere
function csp(nonce, fontSource = "") {
  const fonts = typeof fontSource === "string" && /^[^\s;'"<>]+$/.test(fontSource) ? ` font-src ${fontSource};` : "";
  return `default-src 'none'; style-src 'nonce-${nonce}'; script-src 'nonce-${nonce}';${fonts}`;
}

// <head> every page shares
function head(nonce, fonts, title = "Today", css = "") {
  return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${csp(nonce, fonts && fonts.source)}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeHtml(title)}</title><style nonce="${nonce}">${fontFaces(fonts)}${CSS}${css}</style></head>`;
}

// page side, sent as its source text (runs in the webview, nothing from this file in scope).
// Keeps scroll, the status line + the pressed button's done state across redraws: the extension
// replaces the html on every show + Today rewrite; vscode.getState survives that (cheaper than
// retainContextWhenHidden, which keeps the whole page alive while hidden)
function page(vscode, doc, win, clearMs, undoMs, now = () => Date.now()) {
  const state = Object.assign({ y: 0, status: "", until: 0, done: null, undo: false, day: "", last: "" }, vscode.getState() || {});
  // kept for Today's own day only: "Ready in chat" from yesterday would read as still waiting
  const day = (doc.body && doc.body.dataset.day) || "";
  // (fallback page: no day => nothing reset)
  const save = () => vscode.setState(state);
  if (day && state.day !== day) { Object.assign(state, { y: 0, status: "", until: 0, done: null, undo: false, day, last: "" }); save(); }
  const box = doc.getElementById("status");
  const undoBtn = doc.getElementById("undo");
  let timer = null;
  let pressed = null;
  // until = when it clears (0 = stays: a still-running "Starting Claude" line); undo = its Undo
  // button shows as long as the line. Line gone => pressed button's done state goes too
  const show = (text, until, undo = false) => {
    win.clearTimeout(timer);
    // leaving: the bar keeps its last words drawn while it fades (CSS reads data-gone; the live line itself is empty)
    const bar = box.parentElement;
    if (bar && bar.dataset && !text && box.textContent) bar.dataset.gone = box.textContent;
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
  // where you left off: the job last clicked keeps a soft yellow highlight (state.last), and a
  // posting opening beside Today (page narrows, every line rewraps) or closing again leaves the
  // job on screen where it was - pixel scroll alone lands somewhere else (user report 2026-10-29)
  const jobs = () => Array.from(doc.querySelectorAll("[data-job]"));
  const markLast = () => {
    for (const j of jobs()) {
      const on = Boolean(state.last) && j.dataset.job === state.last;
      j.classList[on ? "add" : "remove"]("last");
      if (on) j.setAttribute("aria-current", "true");
      else j.removeAttribute("aria-current");
    }
  };
  // anchor = the last-opened job while on screen, else the first job on screen + its top
  let anchor = null;
  const hold = () => {
    const seen = (j) => { const r = j.getBoundingClientRect(); return r.bottom > 0 && r.top < win.innerHeight; };
    const on = jobs().filter(seen);
    const el = win.scrollY > 0 ? on.find((j) => j.dataset.job === state.last) || on[0] : null;
    anchor = el ? { el, top: el.getBoundingClientRect().top } : null;
  };
  // Best jobs tabs: the one picked shows, the others' panels hide; arrows move along them (WAI-ARIA tabs)
  const tabs = () => Array.from(doc.querySelectorAll("button[data-tab]"));
  const pick = (want, focus = false) => {
    const all = tabs();
    const on = all.find((t) => t.dataset.tab === want) || all[0];
    if (!on) return null;
    for (const t of all) {
      t.setAttribute("aria-selected", String(t === on));
      t.setAttribute("tabindex", t === on ? "0" : "-1");
      const p = doc.getElementById(t.getAttribute("aria-controls"));
      if (p) p.hidden = t !== on;
    }
    if (focus) on.focus();
    return on;
  };
  // tabs stuck at the top: the new list starts right under them, not part way down
  const choose = (want, focus = false) => {
    const on = pick(want, focus);
    if (!on) return;
    state.tab = on.dataset.tab;
    save();
    const p = doc.getElementById(on.getAttribute("aria-controls"));
    const bar = on.parentElement;
    if (p && bar && bar.getBoundingClientRect) {
      const gap = p.getBoundingClientRect().top - bar.getBoundingClientRect().bottom;
      if (gap < 0) win.scrollBy(0, gap);
    }
    hold();
  };
  pick(state.tab);
  // folded sections: closed by default, the ones opened stay open across redraws
  const opened = new Set(Array.isArray(state.open) ? state.open : []);
  for (const d of doc.querySelectorAll("details[data-fold]")) {
    d.open = opened.has(d.dataset.fold);
    d.addEventListener("toggle", () => {
      if (d.open) opened.add(d.dataset.fold); else opened.delete(d.dataset.fold);
      state.open = [...opened];
      save();
    });
  }
  markLast();
  if (state.y) win.scrollTo(0, state.y);
  hold();
  let saving = false;
  win.addEventListener("scroll", () => {
    if (saving) return;
    saving = true;
    win.setTimeout(() => { saving = false; state.y = win.scrollY; save(); hold(); }, 100);
  });
  win.addEventListener("resize", () => {
    if (!anchor || !anchor.el.isConnected) return;
    win.scrollBy(0, anchor.el.getBoundingClientRect().top - anchor.top);
  });
  doc.addEventListener("click", (e) => {
    const job = e.target.closest("[data-job]");
    if (job && job.dataset.job !== state.last) {
      state.last = job.dataset.job;
      save();
      markLast();
    }
    if (job) anchor = { el: job, top: job.getBoundingClientRect().top };
    const tab = e.target.closest("button[data-tab]");
    if (tab) { choose(tab.dataset.tab); return; }
    const jump = e.target.closest("button[data-jump]");
    if (jump) {
      const to = doc.getElementById(jump.dataset.jump);
      const fold = to && to.closest("details");
      if (fold) fold.open = true;
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
  doc.addEventListener("keydown", (e) => {
    const t = e.target && e.target.closest ? e.target.closest("button[data-tab]") : null;
    if (!t) return;
    const all = tabs();
    const i = all.indexOf(t);
    const to = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: all.length - 1 }[e.key];
    if (to === undefined) return;
    e.preventDefault();
    choose(all[(to + all.length) % all.length].dataset.tab, true);
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
// restart = start.restartLine when a newer copy of the window extension waits (quiet, never yellow)
function render(m, { mode, nonce, ai = null, fonts = null, look = "auto", ready = false, restart = null }) {
  const h = escapeHtml;
  const btn = (text, action, { cls = "", title = "", busy = "", name = "", key = "", about = "" } = {}) =>
    `<button type="button" data-a="${action}"${key ? ` data-k="${h(key)}"` : ""}${busy ? ` data-busy="${h(busy)}"` : ""}`
    + `${cls ? ` class="${cls}"` : ""}${title ? ` title="${h(title)}"` : ""}${name ? ` aria-label="${h(name)}"` : ""}`
    + `${about ? ` aria-describedby="${h(about)}"` : ""}>${h(text)}</button>`;
  // accessible name carries the job: 10 "Apply" buttons read the same to a screen reader
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
  const card = (c, lead) => `<article class="card" aria-labelledby="j-${c.num}" data-job="${c.num}"><h3 id="j-${c.num}"><span class="num">Job ${c.num}</span> `
    + `${title(c)}</h3>` + (c.company ? `<p>${company(c)}</p>` : "") + (facts(c) ? `<p class="detail">${h(facts(c))}</p>` : "")
    + `<div class="acts">${acts(c, lead)}${meta(c)}</div></article>`;
  // one line a job where it fits: number, title, company, detail/why + its buttons + links
  // pre: a job shown in two tabs (All + its own) keeps each heading id its own
  const row = (c, lead, pre = "") => `<li data-job="${c.num}"><div class="what"><h3 id="${pre}j-${c.num}"><b>Job ${c.num}</b> - ${title(c)}`
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
  // best-next list: shown jobs + how many past them
  const bestLeft = (s) => {
    const shown = s.cards.slice(0, BEST_SHOWN);
    return { shown, left: Math.max(0, (s.total || s.cards.length) - shown.length) };
  };
  const moreLine = (more, left) => (more && left > 0 ? { ...more, text: `${left} more ${left === 1 ? "job" : "jobs"} to apply to.` } : null);
  const bests = m.sections.filter((s) => isBest(s.id));
  const tabbed = bests.length > 1;
  const bestTabs = () => {
    const lists = bests.map((s) => ({ s, ...bestLeft(s) }));
    const all = [];
    for (let i = 0; lists.some((l) => i < l.shown.length); i++) for (const l of lists) if (i < l.shown.length) all.push(l.shown[i]);
    const leftAll = lists.reduce((n, l) => n + l.left, 0);
    const panels = BEST_TABS.map((t) => {
      const l = t.id ? lists.find((x) => x.s.id === t.id) : null;
      if (t.id && !l) return null;
      const shown = l ? l.shown : all;
      const left = l ? l.left : leftAll;
      return { ...t, shown, count: shown.length + left, more: moreLine(l ? l.s.more : m.moreAll && { say: m.moreAll }, left) };
    }).filter(Boolean);
    jumps.push(["s-best", "Best jobs"]);
    const s0 = bests[0];
    const note = [s0.note ? h(s0.note) : "", s0.guide ? guideBtn(s0.guide, `Open the guide ${s0.guide.title}`) : ""].filter(Boolean).join(" ");
    const tabs = `<div class="tabs" role="tablist" aria-labelledby="s-best">${panels.map((p, i) =>
      `<button type="button" role="tab" id="t-best-${p.tab}" data-tab="${p.tab}" aria-controls="p-best-${p.tab}" `
      + `aria-selected="${i === 0}" tabindex="${i === 0 ? 0 : -1}">${h(p.label)} <span class="count">${p.count}</span></button>`).join("")}</div>`;
    const body = panels.map((p, i) => `<div role="tabpanel" id="p-best-${p.tab}" aria-labelledby="t-best-${p.tab}"${i ? " hidden" : ""}>`
      + `<ul class="rows">${p.shown.map((c) => row(c, false, i ? `${p.tab}-` : "")).join("")}</ul>`
      + (p.more ? `<ul class="list more">${line(p.more, false)}</ul>` : "") + "</div>").join("");
    return `<section class="best" aria-labelledby="s-best">${heading("s-best", "Best jobs")}`
      + (note ? `<p class="note">${note}</p>` : "") + tabs + body + "</section>";
  };
  const section = (s) => {
    const best = isBest(s.id);
    if (best && tabbed) return s === bests[0] ? bestTabs() : "";
    const rows = best || s.cards.length > ROWS_AFTER;
    const shown = best ? s.cards.slice(0, BEST_SHOWN) : s.cards;
    let more = s.more;
    if (more && best) more = moreLine(more, bestLeft(s).left);
    // "Show the rest" under two sections => named by its section; "Show more jobs" says it already
    const moreName = more && more.say && !best ? `${sayText(more.say, mode)}: ${s.title}` : "";
    jumps.push([`s-${s.id}`, s.title]);
    const lead = LEADS.has(s.id);
    const note = [s.note ? h(s.note) : "", s.guide ? guideBtn(s.guide, `Open the guide ${s.guide.title}`) : ""].filter(Boolean).join(" ");
    const body = (note ? `<p class="note">${note}</p>` : "")
      + (rows ? `<ul class="rows">${shown.map((c) => row(c, lead)).join("")}</ul>`
        : `<div class="cards">${shown.map((c) => card(c, lead)).join("")}</div>`)
      + (more ? `<ul class="list more">${line(more, false, moreName)}</ul>` : "");
    // folded: heading (+ job count) is the toggle; closed until clicked, opened ones stay open on redraw
    if (FOLDED.has(s.id)) {
      const n = s.total || s.cards.length;
      return `<section aria-labelledby="s-${h(s.id)}"><details class="fold" data-fold="${h(s.id)}"><summary>`
        + `<h2 id="s-${h(s.id)}" tabindex="-1">${h(s.title)} <span class="count">${n}</span></h2></summary>${body}</details></section>`;
    }
    return `<section aria-labelledby="s-${h(s.id)}">${heading(`s-${h(s.id)}`, s.title)}${body}</section>`;
  };
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
<body data-day="${h(m.date)}">${skip}<main><div class="top"><div><h1>Today</h1><p class="sub">${h(m.date)}</p>${restart ? `<p class="note restart">${h(restart)}</p>` : ""}${tiles}</div></div>
<p class="how" id="how">${h(howLine(mode))}</p>
${setup}${sections}${todo}${empty}
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
// welcome page's buttons (fixed: no model behind the page)
const SHOW_CHAT = -4;
const ALLOW_HERE = -5;
const CHOOSE_RESUME = -6;
const WELCOME_GUIDES = [
  { action: -7, title: "What you can ask", path: "Guides/What you can ask.md" },
  { action: -8, title: "Who sees what", path: "Guides/Who sees what.md" },
  { action: -9, title: "Keep your chats out of AI training", path: "Guides/Keep your chats out of AI training.md" },
];

function guideAction(rel) {
  const g = WELCOME_GUIDES.find((x) => x.path === rel);
  if (!g) throw new Error(`no welcome guide for ${rel}`);
  return g.action;
}

// where to sign in, per AI (.data/ai): the chat panel sits on the right for all three
// (app/workspace.py secondary sidebar; ChatGPT app-window.md #e). Unknown AI => the plain line
const SIGN_IN = {
  claude: "Look at the chat on the right. Asked to sign in? Click Sign in and use your Claude Pro or Max account.",
  chatgpt: "Look at the chat on the right. Asked to sign in? Click Sign in and use your ChatGPT Plus or Pro account.",
  copilot: "Look at the chat on the right. Asked to sign in? Click Sign in with your GitHub account, then pick Claude Sonnet in the model list under the chat box.",
};
const SIGN_IN_ANY = "Look at the chat on the right. Asked to sign in? Sign in with your AI account.";

// the start button's own words: what it really does, to which AI by name (owner 2026-10-08: "Set me up"
// + a bare "set me up" in the chat box was "not clear or intuitive"; "Start setup in the chat" promised a
// start Claude + ChatGPT can't make - the user still sends). Never "prompt" (jargon); "Send" only where
// it sends (Copilot)
const AI_NAMES = { claude: "Claude", chatgpt: "ChatGPT", copilot: "Copilot" };
const START_LABELS = {
  send: "Send my answers to {ai}",
  new: "Put my answers in {ai}'s chat",
  fill: "Put my answers in {ai}'s chat",
  copy: "Copy my answers for {ai}",
};

function startLabel(ai, mode) {
  const name = AI_NAMES[ai];
  if (!name) return mode === "copy" ? "Copy my answers for the chat" : "Put my answers in the chat";
  return (START_LABELS[mode] || START_LABELS.new).replace("{ai}", name);
}

// before the press: one short line (owner 2026-10-08: the drawing + several instructions were "not
// intuitive at all" - one thing at a time). send = Copilot: it starts by itself
function setupLine(mode) {
  return mode === "send" ? "Your answers go to the chat on the right, and setup starts by itself."
    : "Your answers go into the chat on the right.";
}

// after the press, by what really ran (a send that failed fills; a new chat that failed copies): the
// button's place turns into the one next step. text = the bottom status line (empty: the step says it)
function setupReady(mode, platform = "darwin") {
  const keys = platform === "darwin" ? "Cmd and V" : "Ctrl and V";
  if (mode === "send") return { text: "", done: "Started", title: "Setup has started in the chat", box: null, steps: ["Answer its questions there."] };
  if (mode === "copy") {
    return { text: "", done: "Copied", title: "Your answers are copied", box: "empty",
      steps: ["Click in that box.", `Paste: press ${keys} together.`, "Click the send button at the right end of the box."], or: "Or press Enter instead of the send button." };
  }
  // one click, no keyboard: the new chat opens w/o the keyboard in it (focus stays on this page, #j), so
  // Enter alone would land here; Claude's box has its own send button (its label: "Send message", 2.1.292)
  return { text: "", done: "Ready", title: "Your answers are in the chat", box: "words", steps: ["Click the send button at the right end of that box."],
    or: "Or click in the box and press Enter." };
}

// the next step, drawn where the button was: a title w/ an arrow toward the chat (it really sits right
// of this page), a plain drawing of the one thing to find - the chat's typing box, w/ their own words in
// it - and the moves left. Never a screenshot: the AIs' own panels change often + carry their makers'
// marks. One block per outcome, hidden; the page shows the one that ran (setup.page)
function afterStart(platform = "darwin") {
  const h = escapeHtml;
  return ["send", "words", "copy"].map((kind) => {
    const r = setupReady(kind === "words" ? "new" : kind, platform);
    const find = '<p class="find">Look for this box at the bottom of the chat on the right:</p>';
    // the send button drawn plainly (circle + up arrow) and marked: the one thing to click
    const send = '<span class="mock-send" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 18V6M6.5 11.5 12 6l5.5 5.5"/></svg></span>';
    const box = r.box === "words" ? `${find}<div class="mock"><span class="mock-text" data-words="1"></span>${send}</div>`
      : r.box === "empty" ? `${find}<div class="mock empty"><span class="mock-text">(empty)</span>${send}</div>` : "";
    // one move left => a plain line; several => numbered
    const steps = r.steps.length > 1
      ? `<ol class="after-steps">${r.steps.map((x) => `<li>${h(x).replace("Enter", "<kbd>Enter</kbd>")}</li>`).join("")}</ol>`
      : `<p class="after-steps">${h(r.steps[0])}</p>`;
    const or = r.or ? `<p class="after-or">${h(r.or).replace("Enter", "<kbd>Enter</kbd>")}</p>` : "";
    // sent already => never "again" (a 2nd setup in the same chat)
    const again = kind === "send" ? "" : ' · <button type="submit" class="link again">Put my answers in again</button>';
    return `<div class="after" data-after="${kind}" hidden tabindex="-1"><p class="after-title">${h(r.title)}<span class="arrow" aria-hidden="true">→</span></p>`
      + `${box}${steps}${or}`
      + `<p class="after-help">Can't see the chat? <button type="button" class="link" data-a="${SHOW_CHAT}">Show me the chat</button>${again}</p></div>`;
  }).join("");
}

const FORM_CSS = `
.form-part { margin: 22px 0 0; }
.form-part h3 { font-size: 1.05rem; margin: 0 0 4px; padding: 0 0 4px; border-bottom: 1px solid var(--line); }
.field { border: 0; margin: 14px 0 0; padding: 0; min-width: 0; }
.field > label, .field legend { display: block; font-weight: 600; padding: 0; margin: 0 0 4px; }
.hint { color: var(--text-2); font-size: 0.92rem; margin: 0 0 6px; max-width: 62ch; }
.opts { display: grid; gap: 4px; }
.opt { display: flex; align-items: flex-start; gap: 8px; cursor: pointer; padding: 2px 0; }
.opt input { margin: 3px 0 0; width: 16px; height: 16px; flex: none; accent-color: var(--text); }
input[type="text"], select { font: inherit; color: var(--text); background: var(--desk); border: 1px solid var(--edge);
  border-radius: 6px; padding: 6px 10px; }
input[type="text"] { width: 100%; max-width: 34rem; }
input:focus-visible, select:focus-visible { outline: 3px solid var(--text); outline-offset: 1px; }
.pay { display: flex; align-items: center; gap: 8px; }
.pay input[type="text"] { width: 9rem; }
.resume { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; }
#resume-name { font-weight: 600; margin: 0; }
button[aria-pressed="true"] { box-shadow: inset 0 0 0 2px var(--text); }
/* a picked resume answers these: said under each (owner 2026-10-08: resume first, so less to fill) */
.rnote { display: none; }
form[data-resume="picked"] .rnote { display: block; font-weight: 600; color: var(--text); }
.preview-label { font-weight: 600; margin: 10px 0 4px; }
.preview { margin: 0; padding: 10px 14px; max-width: 62ch; border-left: 3px solid var(--text); background: var(--tint);
  border-radius: 0 6px 6px 0; overflow-wrap: anywhere; }
button.go.done { color: var(--text); }
.peek { margin: 8px 0 0; color: var(--text-2); font-size: 0.92rem; }
.peek summary { cursor: pointer; width: fit-content; }
.peek .preview { margin-top: 6px; color: var(--text); font-size: 1rem; }
/* after the press: the one next step where the button was */
.after { margin: 12px 0 0; padding: 16px 18px; border: 2px solid var(--text); border-radius: 10px; max-width: 34rem; }
.after:focus { outline: none; }
.after:focus-visible { outline: 3px solid var(--text); outline-offset: 3px; }
.after-title { display: flex; align-items: center; gap: 12px; margin: 0; font-size: 1.35rem; font-weight: 600; line-height: 1.2; }
.after-title .arrow { margin-left: auto; font-size: 2.4rem; line-height: 1; padding: 0 6px; background: var(--mark); color: var(--mark-text); border-radius: 8px; }
@media (prefers-reduced-motion: no-preference) { .after:not([hidden]) .arrow { animation: nudge 1.2s ease-in-out 3; } }
@keyframes nudge { 50% { transform: translateX(8px); } }
.find { margin: 14px 0 6px; }
.mock { display: flex; align-items: center; gap: 10px; padding: 12px 14px; border: 3px solid var(--mark-2); border-radius: 10px;
  background: var(--desk); box-shadow: 0 0 0 4px var(--mark); margin: 4px 4px 0; }
.mock-text { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mock.empty .mock-text { color: var(--text-2); font-style: italic; }
.mock-send { flex: none; display: grid; place-items: center; width: 34px; height: 34px; border-radius: 50%; background: var(--text);
  box-shadow: 0 0 0 4px var(--desk), 0 0 0 8px var(--mark); }
.mock-send svg { width: 20px; height: 20px; fill: none; stroke: var(--desk); stroke-width: 2.6; stroke-linecap: round; stroke-linejoin: round; }
.after-or { margin: 6px 0 0; color: var(--text-2); }
.after-steps { margin: 16px 0 0; padding-left: 1.5em; font-size: 1.1rem; font-weight: 600; }
p.after-steps { padding-left: 0; }
.after-steps li + li { margin-top: 4px; }
kbd { font: inherit; padding: 1px 8px; border: 1px solid var(--text); border-bottom-width: 3px; border-radius: 6px; background: var(--tint); }
.after-help { margin: 18px 0 0; color: var(--text-2); font-size: 0.92rem; }
body.vscode-high-contrast .mock { border-color: var(--text); box-shadow: none; }
body.vscode-high-contrast .after-title .arrow { background: none; border: 2px solid var(--text); }
`;

// owner 2026-10-08: people didn't know what to do or where to type after install, and setup asked
// question after question in the chat. First page before setup: 1 sign in (+ the AI-training
// question), 2 the resume - a file or "I don't have one yet" (a file answers some questions, marked
// skippable), 3 the rest of the form (all optional, setup-form.json), 4 the start button - answers
// saved here, their answers in plain words put in the chat (setup.summary, shown live above the
// button; say(), as on Today; owner: a bare "set me up" in the box "not clear or intuitive"); the
// chat asks only what's left.
// notes = lines the window must say first ({text, allow}: allow => "Allow it here");
// saved = answers already saved (prefilled); resume = file already picked (its name)
function welcome({ mode, nonce, ai = null, fonts = null, ready = false, notes = [], platform = "darwin", form = null, saved = {}, resume = "" }) {
  const h = escapeHtml;
  const alerts = notes.map((n) => `<div class="alert" role="note"><p>${h(n.text)}</p>`
    + (n.allow ? `<div class="acts"><button type="button" data-a="${ALLOW_HERE}">${h(n.allow)}</button></div>` : "") + "</div>").join("");
  const guides = WELCOME_GUIDES.slice(0, 2).map((g) => `<li><button type="button" class="link" data-a="${g.action}">${h(g.title)}</button></li>`).join("");
  const f = form || { sections: [] };
  // the AI-account question sits with signing in; the rest after the resume (it answers some of them)
  const part = (ids) => setup.render(f, { saved, esc: h, guideAction, only: ids });
  const aiPart = part(["privacy"]);
  const rest = part(f.sections.map((x) => x.id).filter((id) => id !== "privacy"));
  const none = saved.no_resume === true && !resume;
  return `${head(nonce, fonts, "Welcome", FORM_CSS)}
<body><main><h1>Welcome to CEZ Job Finder</h1>
<p class="sub">Four short steps, about 3 minutes. Then the chat checks how many jobs match and shows your first jobs. Skip anything you like - the chat asks about it.</p>
${alerts}<form id="setup" novalidate data-resume="${resume ? "picked" : none ? "none" : ""}"><ol class="steps">
<li><h2>Sign in to your AI</h2><p>${h(SIGN_IN[ai] || SIGN_IN_ANY)}</p>
<div class="acts"><button type="button" data-a="${SHOW_CHAT}">Show me the chat</button></div>${aiPart}</li>
<li><h2>Your resume</h2><p>A PDF or Word file. A copy goes in My Resume, on this computer only. With it, you can skip the questions it answers.</p>
<div class="acts resume"><button type="button" class="go" data-a="${CHOOSE_RESUME}">Choose my resume file</button>
<button type="button" id="no-resume" aria-pressed="${none}">I don't have one yet</button>
<p id="resume-name" role="status" data-name="${h(resume)}">${resume ? `Added: ${h(resume)}` : ""}</p></div></li>
<li><h2>What you want</h2>${rest}</li>
<li><h2>Start setup</h2><div id="start"><p id="how">${h(setupLine(mode))}</p>
<div class="acts"><button type="submit" id="go" class="go big" aria-describedby="how" data-busy="${h(busyLabel(ai, ready))}">${h(startLabel(ai, mode))}</button></div>
<details class="peek"><summary>See what goes in the chat</summary><p class="preview" id="preview">${h(setup.summary(saved, f, resume))}</p></details></div>
${afterStart(platform)}</li>
</ol></form>
<section class="later" aria-labelledby="s-after"><h2 id="s-after">After that</h2>
<p class="note">Next time, open CEZ Job Finder from its icon on your Desktop. This page becomes Today: your new jobs each morning, with buttons for what to do next.</p>
<h3>Guides</h3><ul class="guides">${guides}</ul></section>
${BAR}</main>
<script nonce="${nonce}">const cezApi = acquireVsCodeApi();
(${page})(cezApi, document, window, ${CLEAR_MS}, ${UNDO_MS});
(${setup.page})(cezApi, document, ${JSON.stringify(f).replace(/</g, "\\u003c")}, ${setup.summary}, ${CLEAR_MS});</script></body></html>`;
}

module.exports = {
  VIEW_TYPE, WELCOME_TYPE, AI_NAMES, START_LABELS, startLabel, setupReady, afterStart, SHOW_CHAT, ALLOW_HERE, CHOOSE_RESUME, WELCOME_GUIDES, guideAction, SIGN_IN, SIGN_IN_ANY, setupLine, welcome,
  DATA, VERSION, OPENABLE, FONT_DIR, FONTS, fontFaces, BEST_SHOWN, isBest, ROWS_AFTER, CHAT_OPEN, CLAUDE_ID, CLAUDE_TESTED, CLAUDE_NEW_CHAT,
  escapeHtml, templates, templateFor, cleanUrl, cleanSite, openLink, readingPane, cleanPath, model, claudeTested, sayMode, claudeNewChatArgs, sayText, sayTitle,
  howLine, jobOf, readyLine, doneLabel, CLEAR_MS, SLOW_MS, busyLabel, startingLine, say, STILL_OPENING, STILL_SAVING,
  STATUS_SET, UNDO_MS, statusLine, undoneLine, statusFailed, UNDO_FAILED, statusKeeper,
  LOOKS, LOOK_FILE, lookOf, lookDone, lookSwitch, csp, page, render, FALLBACK, SHOW_PAGE, TRY_AGAIN, fallback,
};
