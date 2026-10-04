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

function copiedLine(platform) {
  const keys = platform === "darwin" ? "Cmd+V" : "Ctrl+V";
  return `Copied - click the chat box, paste (${keys}), press Enter.`;
}

function filledLine() {
  return "The words are in the chat box - press Enter to send them.";
}

function newChatLine() {
  return "New chat ready - press Enter";
}

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
// exec(command, ...args) + copy(text) = vscode calls; busy(on) + status(text) = page feedback.
// busy at once; starting line if still waiting after SLOW_MS; then ready line, or copy fallback
async function say({ ai, mode, words, platform, exec, copy, status, busy, wait = setTimeout, clear = clearTimeout }) {
  busy(true);
  const slow = wait(() => status(startingLine(ai)), SLOW_MS);
  try {
    if (mode === "fill") {
      try {
        // fills the box, never sends: isPartialQuery
        await exec("workbench.action.chat.open", { query: words, isPartialQuery: true });
        status(filledLine());
        return mode;
      } catch {}
    }
    if (mode === "new") {
      try {
        await exec(CLAUDE_NEW_CHAT, ...claudeNewChatArgs(words));
        status(newChatLine());
        return mode;
      } catch {}
    }
    await copy(words);
    if (CHAT_OPEN[ai]) await Promise.resolve().then(() => exec(CHAT_OPEN[ai])).catch(() => {});
    status(copiedLine(platform));
    return "copy";
  } finally {
    clear(slow);
    busy(false);
  }
}

// colors = app/window/brand.py tokens (test checks every hex); yellow only on buttons
const CSS = `
body.vscode-light { --desk: #ffffff; --text: #000000; --text-2: #3a3a3a; --line: #c8c8c8; --card: #ffffff; --tint: #f3f3f1;
  --mark: #ffe433; --mark-2: #f2cf00; --mark-text: #000000; }
body.vscode-dark { --desk: #1c1c1e; --text: #f2f2f2; --text-2: #bdbdbd; --line: #48484a; --card: #2c2c2e; --tint: #2c2c2e;
  --mark: #ffe433; --mark-2: #f2cf00; --mark-text: #000000; }
body.vscode-high-contrast { --desk: var(--vscode-editor-background); --text: var(--vscode-editor-foreground);
  --text-2: var(--vscode-editor-foreground); --line: var(--vscode-contrastBorder, currentColor); --card: transparent;
  --tint: transparent; --mark: transparent; --mark-2: transparent; --mark-text: var(--vscode-editor-foreground); }
* { box-sizing: border-box; }
body { margin: 0; padding: 0 20px; background: var(--desk); color: var(--text);
  font-family: Caladea, Georgia, "Times New Roman", serif; font-size: 16px; line-height: 1.45; }
main { max-width: 60rem; margin: 0 auto; padding: 24px 0 48px; }
h1 { font-size: 2rem; line-height: 1.1; margin: 0 0 4px; }
.sub { color: var(--text-2); margin: 0 0 2px; }
.how { color: var(--text-2); font-size: 0.9rem; margin: 0 0 20px; }
section { margin: 24px 0 0; }
section > h2 { font-size: 1.2rem; margin: 0 0 10px; padding-top: 10px; border-top: 1px solid var(--line); }
.note { color: var(--text-2); font-size: 0.92rem; margin: -2px 0 12px; max-width: 42rem; }
.figures { display: flex; flex-wrap: wrap; gap: 4px 28px; margin: 22px 0 0; padding: 0; list-style: none; }
.figures li { display: flex; align-items: baseline; gap: 8px; }
.figures b { font-size: 1.6rem; line-height: 1.1; }
.figures span { color: var(--text-2); font-size: 0.92rem; }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 18rem), 1fr)); gap: 12px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px;
  display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.next .cards { grid-template-columns: 1fr; }
.next .card { padding: 14px 18px; }
.next .card h3 { font-size: 1.3rem; }
.card h3 { font-size: 1.05rem; line-height: 1.3; margin: 0; overflow-wrap: anywhere; }
.num { display: block; font-size: 0.85rem; color: var(--text-2); }
.card p { margin: 0; overflow-wrap: anywhere; }
.detail { color: var(--text-2); font-size: 0.92rem; }
.acts { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: auto; padding-top: 6px; }
.meta { font-size: 0.9rem; color: var(--text-2); margin-left: auto; }
.card .meta { margin: 0 0 0 auto; padding-left: 6px; }
.rows { list-style: none; margin: 0; padding: 0; }
.rows li { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 4px 12px;
  padding: 8px 0; border-bottom: 1px solid var(--line); }
.rows li:first-child { border-top: 1px solid var(--line); }
.rows .what { min-width: 0; flex: 1 1 18rem; overflow-wrap: anywhere; }
.rows .what b { font-weight: 700; }
.list { list-style: none; padding: 0; margin: 0; display: grid; gap: 8px; }
.list li { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; }
.more { margin-top: 10px; }
.later { font-size: 0.92rem; color: var(--text-2); }
.says { color: var(--text-2); margin: 10px 0 0; }
.says q { color: var(--text); font-weight: 700; }
button { font: inherit; font-size: 0.92rem; font-weight: 700; cursor: pointer; border-radius: 6px; padding: 5px 12px;
  border: 1px solid var(--text-2); background: transparent; color: var(--text); text-align: center; }
button:hover { background: var(--tint); }
button.go { background: var(--mark); color: var(--mark-text); border-color: var(--mark); }
button.go:hover { background: var(--mark-2); border-color: var(--mark-2); }
button.quiet { border-color: var(--line); color: var(--text-2); font-weight: 400; }
button.link { border: 0; border-radius: 2px; padding: 0; background: none; font-weight: 400; color: var(--text);
  text-decoration: underline; text-underline-offset: 2px; }
button.link:hover { background: none; text-decoration-thickness: 2px; }
button[disabled] { cursor: progress; opacity: 0.75; }
button:focus-visible { outline: 3px solid var(--text); outline-offset: 2px; }
body.vscode-high-contrast button.go { border-color: var(--line); }
#status { position: sticky; bottom: 0; margin: 16px 0 0; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--text);
  background: var(--card); color: var(--text); font-weight: 700; }
#status:empty { display: none; }
`;

// webview page: one inline script + style (nonce), nothing loaded from anywhere
function csp(nonce) {
  return `default-src 'none'; style-src 'nonce-${nonce}'; script-src 'nonce-${nonce}';`;
}

const SCRIPT = `
const vscode = acquireVsCodeApi();
document.addEventListener("click", (e) => {
  const b = e.target.closest("button[data-a]");
  if (!b || b.disabled) return;
  // say button: busy at once, before the chat answers (first one can take seconds)
  if (b.dataset.busy) {
    b.dataset.text = b.textContent;
    b.textContent = b.dataset.busy;
    b.disabled = true;
    b.setAttribute("aria-busy", "true");
  }
  vscode.postMessage({ action: Number(b.dataset.a) });
});
window.addEventListener("message", (e) => {
  if (e.data && e.data.type === "status") document.getElementById("status").textContent = String(e.data.text);
  if (e.data && e.data.type === "busy" && !e.data.on) {
    for (const b of document.querySelectorAll("button[aria-busy]")) {
      b.textContent = b.dataset.text;
      b.disabled = false;
      b.removeAttribute("aria-busy");
    }
  }
});
`;

function render(m, { mode, nonce, ai = null }) {
  const h = escapeHtml;
  const btn = (text, action, cls = "", title = "", busy = "") =>
    `<button type="button" data-a="${action}"${busy ? ` data-busy="${h(busy)}"` : ""}${cls ? ` class="${cls}"` : ""}`
    + `${title ? ` title="${h(title)}"` : ""}>${h(text)}</button>`;
  // one yellow per card: its first say; status changes outline, closing quieter still
  const say = (b, go) => btn(sayText(b, mode), b.action, go ? "go" : QUIET.has(b.id) ? "quiet" : "", sayTitle(b, mode), busyLabel(ai));
  const acts = (c) => c.say.map((b, i) => say(b, i === 0)).join("");
  // posting, resume, folder: places to look, not things to do => ink links on one line
  const meta = (c) => {
    const links = [c.posting && btn("Posting", c.posting.action, "link"), c.resume && btn("Resume", c.resume.action, "link"),
      c.folder && btn("Folder", c.folder.action, "link")].filter(Boolean);
    return links.length ? `<span class="meta">${links.join(" · ")}</span>` : "";
  };
  const card = (c) => `<article class="card"><h3><span class="num">Job ${c.num}</span>${h(c.title)}</h3>`
    + (c.company ? `<p>${h(c.company)}</p>` : "") + (c.detail ? `<p class="detail">${h(c.detail)}</p>` : "")
    + `<div class="acts">${acts(c)}${meta(c)}</div></article>`;
  // one line a job: number, title, company, detail + its buttons
  const row = (c, links) => `<li><span class="what"><b>Job ${c.num}</b> - ${h(c.title)}${c.company ? `, ${h(c.company)}` : ""}`
    + `${c.detail ? ` <span class="detail">- ${h(c.detail)}</span>` : ""}</span><span class="acts">${acts(c)}`
    + `${links ? meta(c) : ""}</span></li>`;
  const line = (x, go) => `<li><span>${h(x.text)}</span>${x.say ? say(x.say, go) : ""}</li>`;
  const tile = (id) => m.tiles.find((t) => t.section === id);
  const section = (s) => {
    const rows = s.id === "new" || s.cards.length > ROWS_AFTER;
    const shown = s.id === "new" ? s.cards.slice(0, NEW_SHOWN) : s.cards;
    let more = s.more;
    if (more && s.id === "new") {
      const total = tile("new") ? tile("new").value : s.cards.length;
      const left = total - shown.length - (m.next && m.next.section === "new" ? 1 : 0);
      more = left > 0 ? { ...more, text: `${left} more new ${left === 1 ? "job" : "jobs"}.` } : null;
    }
    return `<section aria-labelledby="s-${h(s.id)}"><h2 id="s-${h(s.id)}">${h(s.title)}</h2>`
      + (s.note ? `<p class="note">${h(s.note)}</p>` : "")
      + (rows ? `<ul class="rows">${shown.map((c) => row(c, s.id !== "new")).join("")}</ul>`
        : `<div class="cards">${shown.map(card).join("")}</div>`)
      + (more ? `<ul class="list more">${line(more, false)}</ul>` : "") + "</section>";
  };
  const next = m.next
    ? `<section class="next" aria-labelledby="s-next"><h2 id="s-next">Next up</h2>`
      + (m.next.card ? `<div class="cards">${card(m.next.card)}</div>`
        : `<ul class="list">${line(m.next.todo, true)}</ul>`) + "</section>"
    : "";
  const tiles = m.tiles.length
    ? `<ul class="figures">${m.tiles.map((t) => `<li><b>${t.value}</b><span>${h(t.label)}</span></li>`).join("")}</ul>` : "";
  const blocking = m.todo.filter((t) => t.blocks);
  const later = m.todo.filter((t) => !t.blocks);
  const setup = blocking.length
    ? `<section><h2>Finish setting up</h2><ul class="list">${blocking.map((t) => line(t, true)).join("")}</ul></section>` : "";
  const todo = later.length
    ? `<section class="later"><h2>Not finished</h2><ul class="list">${later.map((t) => line(t, false)).join("")}</ul></section>` : "";
  const empty = m.empty ? `<section><ul class="list">${line(m.empty, true)}</ul></section>` : "";
  const asks = m.asks.length ? `<div class="acts">${m.asks.map((b) => say(b, false)).join("")}</div>` : "";
  const examples = m.examples.length
    ? `<p class="says">For example: ${m.examples.map((ex) => ex.map((w) => `<q>${h(w)}</q>`).join(" or ")).join(" · ")}</p>` : "";
  const guides = m.guides.length
    ? `<p class="says">Guides: ${m.guides.map((g) => btn(g.title, g.open.action, "link")).join(" · ")}</p>` : "";
  return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${csp(nonce)}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Today</title><style nonce="${nonce}">${CSS}</style></head>
<body><main><h1>Today</h1><p class="sub">${h(m.date)}</p><p class="how">${h(howLine(mode))}</p>
${next}${tiles}${setup}${m.sections.map(section).join("")}${todo}${empty}
<section class="later"><h2>What you can say</h2>${asks}${examples}${guides}</section>
<p id="status" role="status" aria-live="polite"></p></main>
<script nonce="${nonce}">${SCRIPT}</script></body></html>`;
}

// shown when today.json is missing, old or broken: the page view still has everything
function fallback({ nonce }) {
  return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${csp(nonce)}">
<title>Today</title><style nonce="${nonce}">${CSS}</style></head>
<body><main><h1>Today</h1><p class="sub">Getting today's list ready.</p>
<div class="row"><button type="button" class="go" data-a="-1">Show the page</button></div>
<p id="status" role="status" aria-live="polite"></p></main>
<script nonce="${nonce}">${SCRIPT}</script></body></html>`;
}

module.exports = {
  VIEW_TYPE, DATA, VERSION, OPENABLE, NEXT_ORDER, NEW_SHOWN, ROWS_AFTER, CHAT_OPEN, CLAUDE_ID, CLAUDE_TESTED, CLAUDE_NEW_CHAT,
  escapeHtml, templates, templateFor, cleanUrl, cleanPath, model, claudeTested, sayMode, claudeNewChatArgs, sayText, sayTitle,
  howLine, copiedLine, filledLine, newChatLine, SLOW_MS, busyLabel, startingLine, say,
  csp, render, fallback,
};
