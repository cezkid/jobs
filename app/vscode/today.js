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
    return t ? { words, label: t.label, action: act({ type: "say", words }) } : null;
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
      .map((t) => ({ label: str(t.label, 60), value: t.value })),
    sections: raw.sections.filter((s) => s && Array.isArray(s.cards)).map((s) => ({
      id: str(s.id, 30), title: str(s.title, 80), note: str(s.note, 600),
      cards: s.cards.map(card).filter(Boolean), more: line(s.more),
    })),
    todo: (Array.isArray(raw.todo) ? raw.todo : []).map(line).filter(Boolean),
    empty: line(raw.empty),
    examples: (Array.isArray(raw.examples) ? raw.examples : [])
      .map((ex) => (Array.isArray(ex) ? ex : []).filter((w) => templateFor(w, tpls)).map((w) => str(w, 100)))
      .filter((ex) => ex.length),
    guides: (Array.isArray(raw.guides) ? raw.guides : [])
      .map((g) => (g ? { title: str(g.title, 80), open: open(g.path, "page") } : null))
      .filter((g) => g && g.open),
  };
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
main { max-width: 72rem; margin: 0 auto; padding: 24px 0 56px; }
h1 { font-size: 2rem; line-height: 1.1; margin: 0 0 4px; }
.sub { color: var(--text-2); margin: 0 0 4px; }
.how { color: var(--text-2); font-size: 0.9rem; margin: 0 0 20px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(8.5rem, 1fr)); gap: 10px; margin: 0 0 24px; }
.tile { border: 1px solid var(--line); border-radius: 8px; padding: 10px 14px; background: var(--card); }
.tile b { display: block; font-size: 1.9rem; line-height: 1.1; }
.tile span { color: var(--text-2); font-size: 0.9rem; }
.panel { border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px 16px; margin: 0 0 18px; background: var(--tint); }
.panel h2 { font-size: 1.25rem; margin: 0 0 10px; }
.note { color: var(--text-2); font-size: 0.92rem; margin: -4px 0 12px; }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 17rem), 1fr)); gap: 12px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px;
  display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.num { font-size: 0.85rem; font-weight: 700; color: var(--text-2); letter-spacing: 0.02em; }
.title { font-weight: 700; font-size: 1.05rem; overflow-wrap: anywhere; }
.company { overflow-wrap: anywhere; }
.detail { color: var(--text-2); font-size: 0.92rem; overflow-wrap: anywhere; }
.row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: auto; padding-top: 4px; }
button { font: inherit; font-size: 0.92rem; font-weight: 700; cursor: pointer; border-radius: 6px; padding: 5px 12px;
  border: 1px solid var(--line); background: var(--card); color: var(--text); text-align: left; }
button:hover { border-color: var(--text); }
button.go { background: var(--mark); color: var(--mark-text); border-color: var(--mark); }
button.go:hover { background: var(--mark-2); border-color: var(--mark-2); }
button[disabled] { cursor: progress; opacity: 0.75; }
button:focus-visible { outline: 3px solid var(--text); outline-offset: 2px; }
body.vscode-high-contrast button.go { border-color: var(--line); }
.list { list-style: none; padding: 0; margin: 0; display: grid; gap: 8px; }
.list li { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; }
.more { margin-top: 12px; }
.note.guides { margin: 12px 0 8px; }
.says { color: var(--text-2); margin: 0; padding-left: 1.2em; }
.says q { color: var(--text); font-weight: 700; }
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
  const btn = (text, action, go = false, title = "", busy = "") =>
    `<button type="button" data-a="${action}"${busy ? ` data-busy="${h(busy)}"` : ""}${go ? ' class="go"' : ""}`
    + `${title ? ` title="${h(title)}"` : ""}>${h(text)}</button>`;
  const say = (b, go) => btn(sayText(b, mode), b.action, go, sayTitle(b, mode), busyLabel(ai));
  const card = (c) => {
    const buttons = [
      ...c.say.map((b, i) => say(b, i === 0)),
      c.posting ? btn("Open the posting", c.posting.action) : "",
      c.resume ? btn("Open resume", c.resume.action) : "",
      c.folder ? btn("Open folder", c.folder.action) : "",
    ].join("");
    return `<article class="card"><div class="num">Job ${c.num}</div><div class="title">${h(c.title)}</div>`
      + (c.company ? `<div class="company">${h(c.company)}</div>` : "")
      + (c.detail ? `<div class="detail">${h(c.detail)}</div>` : "")
      + `<div class="row">${buttons}</div></article>`;
  };
  const line = (x) => `<li><span>${h(x.text)}</span>${x.say ? say(x.say, true) : ""}</li>`;
  const sections = m.sections.map((s) => `<section class="panel" aria-labelledby="s-${h(s.id)}">`
    + `<h2 id="s-${h(s.id)}">${h(s.title)}</h2>${s.note ? `<p class="note">${h(s.note)}</p>` : ""}`
    + `<div class="cards">${s.cards.map(card).join("")}</div>`
    + (s.more ? `<ul class="list more">${line(s.more)}</ul>` : "")
    + "</section>").join("");
  const tiles = m.tiles.length
    ? `<div class="tiles">${m.tiles.map((t) => `<div class="tile"><b>${t.value}</b><span>${h(t.label)}</span></div>`).join("")}</div>`
    : "";
  const todo = m.todo.length
    ? `<section class="panel"><h2>Not finished</h2><ul class="list">${m.todo.map(line).join("")}</ul></section>` : "";
  const empty = m.empty ? `<section class="panel"><ul class="list">${line(m.empty)}</ul></section>` : "";
  const examples = m.examples.length
    ? `<ul class="says">${m.examples.map((ex) => `<li>${ex.map((w) => `<q>${h(w)}</q>`).join(" / ")}</li>`).join("")}</ul>` : "";
  const guides = m.guides.length ? `<div class="row">${m.guides.map((g) => btn(g.title, g.open.action)).join("")}</div>` : "";
  return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${csp(nonce)}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Today</title><style nonce="${nonce}">${CSS}</style></head>
<body><main><h1>Today</h1><p class="sub">${h(m.date)}.</p><p class="how">${h(howLine(mode))}</p>
${tiles}${sections}${todo}${empty}
<section class="panel"><h2>What you can say</h2>${examples}<p class="note guides">Guides:</p>${guides}</section>
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
  VIEW_TYPE, DATA, VERSION, OPENABLE, CHAT_OPEN, CLAUDE_ID, CLAUDE_TESTED, CLAUDE_NEW_CHAT,
  escapeHtml, templates, templateFor, cleanUrl, cleanPath, model, claudeTested, sayMode, claudeNewChatArgs, sayText, sayTitle,
  howLine, copiedLine, filledLine, newChatLine, SLOW_MS, busyLabel, startingLine, say,
  csp, render, fallback,
};
