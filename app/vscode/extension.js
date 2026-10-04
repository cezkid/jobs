// CEZ Job Finder window extension. Plain JS, no build step, no npm deps.
// Never reads files from app/ at runtime: Windows locks them during an update. All it needs is
// inside the vsix (app/vscode_ext.py builds it).
const vscode = require("vscode");
const childProcess = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const crypto = require("crypto");
const start = require("./start");
const today = require("./today");
const say = require("./say.json");

// probe: set only by a scratch window measurement (app/docs/app-window.md "Measured"). Writes
// what the window holds to this path, then quits the window. Never set on a user's computer.
const PROBE_ENV = "JOBS_VSCODE_PROBE";
// probe only: pages to open on activation ("|" between), and how (showPreview | openWith | open)
const PROBE_OPEN_ENV = "JOBS_VSCODE_PROBE_OPEN";
const PROBE_OPEN_HOW_ENV = "JOBS_VSCODE_PROBE_OPEN_HOW";
// probe only: ms to wait for the window to settle before reading it
const PROBE_SETTLE_ENV = "JOBS_VSCODE_PROBE_SETTLE_MS";
// probe only: view type of a custom editor a scratch build contributes (customEditors), to see
// which Today.md files it takes over
const PROBE_EDITOR_ENV = "JOBS_VSCODE_PROBE_EDITOR";
// probe only: words a Today say button carries; run through the button's own path after settle
const PROBE_SAY_ENV = "JOBS_VSCODE_PROBE_SAY";
// probe only: a look word (auto | light | dark) run through the switch's own path after settle
const PROBE_LOOK_ENV = "JOBS_VSCODE_PROBE_LOOK";
// probe only: warm-up as measured: off | activate | view (default = the shipped plan)
const PROBE_WARM_ENV = "JOBS_VSCODE_PROBE_WARM";
// probe only: epoch ms the window was launched, so times read from window start
const PROBE_T0_ENV = "JOBS_VSCODE_PROBE_T0";
const PROBE_COMMANDS = [/^claude-vscode\./, /^chatgpt\./, /^workbench\.action\.chat\./, /outline/i, /timeline/i, /^vscode\.moveViews$/, /^markdown\.showPreview/];
const PROBE_SETTINGS = [
  "workbench.colorTheme", "window.autoDetectColorScheme", "workbench.startupEditor",
  "workbench.welcomePage.walkthroughs.openOnInstall", "workbench.editorAssociations",
  "markdown.styles", "claudeCode.hideOnboarding", "claudeCode.preferredLocation",
  "workbench.secondarySideBar.defaultVisibility", "chat.commandCenter.enabled",
];

function activate(context) {
  context.subscriptions.push(vscode.window.registerCustomEditorProvider(today.VIEW_TYPE, { resolveCustomTextEditor: (document, panel) =>
    showToday(document, panel, vscode.Uri.joinPath(context.extensionUri, ...today.FONT_DIR)) },
    { webviewOptions: { enableFindWidget: true }, supportsMultipleEditorsPerDocument: false }));
  const out = process.env[PROBE_ENV];
  // probe told which pages to open => measures that alone, not the start page
  const opened = out && process.env[PROBE_OPEN_ENV] ? Promise.resolve() : openStartPage().catch(() => {});
  const warmed = opened.then((root) => (root ? warmUp(root) : null)).catch(() => null);
  if (!out) return;
  const editor = process.env[PROBE_EDITOR_ENV];
  if (editor) {
    context.subscriptions.push(vscode.window.registerCustomEditorProvider(editor, {
      resolveCustomTextEditor(document, panel) {
        panel.webview.html = "<p>probe editor</p>";
      },
    }));
  }
  probe(context, out, opened, warmed);
}

function deactivate() {}

function mtime(file) {
  try { return fs.statSync(file).mtimeMs; } catch { return null; }
}

// START HERE before setup, Today after, opened formatted as the window starts (no 6 s wait in the
// launcher). Launcher's marker names it; opened w/o the launcher => our own pick + a background
// rebuild when Today is stale. Never blocks the window, never fails it.
async function openStartPage() {
  const folder = (vscode.workspace.workspaceFolders || [])[0];
  if (!folder || folder.uri.scheme !== "file") return;
  const root = folder.uri.fsPath;
  const at = (rel) => path.join(root, rel);
  if (!start.isJobFinder((rel) => fs.existsSync(at(rel)))) return;
  let marker = null;
  try {
    marker = fs.readFileSync(at(start.MARKER), "utf8");
    fs.unlinkSync(at(start.MARKER));
  } catch {}
  const settingsExist = fs.existsSync(at(start.SETTINGS));
  const todayMtime = mtime(at(start.TODAY));
  const page = start.choosePage({ marker, settingsExist, todayExists: todayMtime != null });
  if (start.needsRefresh({ marker, settingsExist, todayMtime, stampMtime: mtime(at(start.STAMP)), now: Date.now() })) {
    refreshToday(root);  // not awaited: the page shows now, its preview redraws once rewritten
  }
  await showPage(vscode.Uri.file(at(page)), page === start.TODAY);
  return root;
}

// start the user's chat extension in the background, never a tab, never focus off the page
async function warmUp(root) {
  const ai = currentAi(root);
  const plan = start.warmUpPlan(ai);
  const how = process.env[PROBE_ENV] ? process.env[PROBE_WARM_ENV] : null;
  if (!plan || how === "off") return null;
  const ext = vscode.extensions.getExtension(plan.id);
  if (!ext) return null;
  const seen = { id: plan.id, how: how || "plan", startAt: Date.now() };
  try {
    if (!ext.isActive) await ext.activate();
  } catch {
    return seen;  // Restricted Mode or a broken install: the button's own path still works
  }
  seen.activeAt = Date.now();
  if (how === "view" || (how !== "activate" && plan.view)) {
    try {
      await vscode.commands.executeCommand(today.CHAT_OPEN[ai]);
      // its view takes focus => back to the page the user is reading
      await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup");
    } catch {}
    seen.viewAt = Date.now();
  }
  return seen;
}

function tabSeen(tab) {
  const input = tab.input;
  if (input instanceof vscode.TabInputText) return { kind: "text", fsPath: input.uri.fsPath, label: tab.label, tab };
  if (input instanceof vscode.TabInputCustom) return { kind: "custom", fsPath: input.uri.fsPath, viewType: input.viewType, label: tab.label, tab };
  if (input instanceof vscode.TabInputWebview) return { kind: "webview", label: tab.label, tab };
  return { kind: "other", label: tab.label, tab };
}

async function showPage(uri, isToday) {
  const tabs = vscode.window.tabGroups.all.flatMap((group) => group.tabs.map(tabSeen));
  const { formatted, text } = start.pageTabs(tabs, uri.fsPath, process.platform);
  const stale = [];
  // Today restored as the plain page view (window before the dashboard) => dashboard instead
  const dashboard = isToday && !(formatted && formatted.viewType === today.VIEW_TYPE);
  if (dashboard && formatted) stale.push(formatted.tab);
  if (formatted && !dashboard && formatted.kind === "custom") await vscode.commands.executeCommand("vscode.openWith", uri, formatted.viewType);
  else if (formatted && !dashboard) await vscode.commands.executeCommand("markdown.showPreview", uri);
  // Today: the dashboard; START HERE: always the formatted page
  else await vscode.commands.executeCommand("vscode.openWith", uri, isToday ? today.VIEW_TYPE : start.PREVIEW_EDITOR, { preview: false });
  // a plain-text copy from an older launch would come back on every start; the page is generated
  stale.push(...text.map((t) => t.tab).filter((tab) => !tab.isDirty));
  if (stale.length) await vscode.window.tabGroups.close(stale, true);
}

// Today dashboard (custom editor on Today.md, workspace association app/workspace.py): drawn from
// .data/today.json, redrawn when the page is rewritten. Buttons send an index; what it does is
// looked up here, checked again, never taken from the page. fontDir = the installed extension's
// media/fonts (Caladea): the one folder the page may load from
function showToday(document, panel, fontDir) {
  const root = path.dirname(document.uri.fsPath);
  const at = (rel) => path.join(root, ...rel.split("/"));
  panel.webview.options = { enableScripts: true, localResourceRoots: [fontDir] };
  const fonts = { source: panel.webview.cspSource, files: {} };
  for (const [weight, file] of Object.entries(today.FONTS)) {
    fonts.files[weight] = panel.webview.asWebviewUri(vscode.Uri.joinPath(fontDir, file)).toString();
  }
  let m = null;
  const draw = () => {
    const nonce = crypto.randomBytes(16).toString("base64");
    m = null;
    // why no dashboard, in the fallback's words (today.FALLBACK)
    let reason = "unreadable";
    try {
      if (start.isJobFinder((rel) => fs.existsSync(at(rel)))) {
        if (!fs.existsSync(at(today.DATA))) reason = "missing";
        else m = today.model(JSON.parse(fs.readFileSync(at(today.DATA), "utf8")), say);
      }
    } catch {}
    if (refreshing) reason = "updating";
    // a file a button names may have moved since (job filed under another stage) => no button
    if (m) for (const s of m.sections) for (const c of s.cards) {
      if (c.resume && !fs.existsSync(at(c.resume.path))) c.resume = null;
      if (c.folder && !fs.existsSync(at(c.folder.path))) c.folder = null;
    }
    const ai = currentAi(root);
    panel.webview.html = m ? today.render(m, { mode: sayModeNow(root), ai, nonce, fonts, look: currentLook(root), ready: chatWarm(ai) })
      : today.fallback({ nonce, reason, fonts });
  };
  // fallback's Try again: rebuild the list (page redraws when it's rewritten), else just read it again
  // I sent it / I heard back / It's closed: saved here, Undo in the status line (today.statusKeeper)
  const keeper = today.statusKeeper({
    run: (args) => {
      const uv = findUv();
      return uv ? start.runJobs({ execFile: childProcess.execFile, uv, root, args }) : Promise.reject(new Error("no uv"));
    },
    refresh: () => refreshToday(root, draw),
    tell: (text, how) => tell(panel, text, how),
  });
  const retry = () => {
    const started = !refreshing && refreshToday(root, draw);
    draw();
    if (!started && !refreshing && !m) tell(panel, "Still not ready - it's made again at the next start.");
  };
  draw();
  const watcher = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(vscode.Uri.file(root), start.TODAY));
  const subs = [
    watcher, watcher.onDidChange(draw), watcher.onDidCreate(draw),
    panel.onDidChangeViewState(() => { if (panel.visible) draw(); }),
    panel.webview.onDidReceiveMessage((msg) => act(root, at, document.uri, m, msg, panel, retry, keeper).catch(() => {})),
  ];
  panel.onDidDispose(() => subs.forEach((s) => s.dispose()));
}

function currentLook(root) {
  try {
    return today.lookOf(fs.readFileSync(path.join(root, today.LOOK_FILE), "utf8"));
  } catch {
    return "auto";
  }
}

// look switch: `jobs.py look WORD` saves .data/look + rewrites the window's settings => VS Code
// switches at once. One run at a time; a click during one runs after it (last click wins)
const LOOK_FAILED = "Couldn't switch the look - say \"dark mode\" or \"light mode\" in the chat.";
let looking = null;
let lookNext = null;

// page marks the click at once; told the look that holds once done (the old one if it failed)
function switchLook(root, word, panel) {
  const held = (text) => {
    panel.webview.postMessage({ type: "look", word: currentLook(root) });
    tell(panel, text);
  };
  if (looking) { lookNext = word; return; }
  const uv = findUv();
  if (!uv) return held(LOOK_FAILED);
  looking = word;
  childProcess.execFile(uv, ["run", "app/jobs.py", "look", word], { cwd: root, windowsHide: true, timeout: 60000 }, (err) => {
    looking = null;
    if (lookNext && lookNext !== word) { const next = lookNext; lookNext = null; return switchLook(root, next, panel); }
    lookNext = null;
    held(err ? LOOK_FAILED : today.lookDone(word));
  });
}

function currentAi(root) {
  try {
    return fs.readFileSync(path.join(root, start.AI_FILE), "utf8").trim().toLowerCase();
  } catch {
    return null;
  }
}

// status line on the page: clears after today.CLEAR_MS unless hold; done = pressed button's label;
// undo = an Undo button beside it, both gone after today.UNDO_MS
function tell(panel, text, { done = null, hold = false, undo = false } = {}) {
  panel.webview.postMessage({ type: "status", text, done, hold, undo });
}

async function act(root, at, page, m, msg, panel, retry, keeper) {
  if (msg && typeof msg.look === "string") {
    if (today.LOOKS.some((l) => l.word === msg.look)) switchLook(root, msg.look, panel);
    return;
  }
  if (msg && msg.undo === true) return keeper.undo();
  const index = msg && Number.isInteger(msg.action) ? msg.action : null;
  if (index === today.SHOW_PAGE) return vscode.commands.executeCommand("vscode.openWith", page, start.PREVIEW_EDITOR);
  if (index === today.TRY_AGAIN) return retry();
  const action = m && index != null ? m.actions[index] : null;
  if (!action) return;
  if (action.type === "posting") {
    const url = today.cleanUrl(action.url);
    // a string, not a Uri: passed on exactly as written (a Uri re-encodes it; a rebuilt link 404s)
    if (url) await vscode.env.openExternal(url);
    return;
  }
  if (action.type === "company") {
    const url = today.cleanSite(action.url);
    if (url) await vscode.env.openExternal(url);
    return;
  }
  if (action.type === "open") {
    const rel = today.cleanPath(action.path);
    if (!rel) return;
    const file = at(rel);
    let real;
    try { real = fs.realpathSync(file); } catch { return tell(panel, "That file has moved - the page updates at the next check."); }
    if (!real.startsWith(fs.realpathSync(root) + path.sep)) return;
    const uri = vscode.Uri.file(file);
    if (action.how === "folder") return vscode.commands.executeCommand("revealInExplorer", uri);
    if (action.how === "page") return vscode.commands.executeCommand("vscode.openWith", uri, start.PREVIEW_EDITOR);
    return vscode.commands.executeCommand("vscode.open", uri, { preview: false });
  }
  if (action.type === "status") return keeper.set(action.num, action.id, action.words);
  if (action.type === "say") {
    if (!today.templateFor(action.words, today.templates(say))) return;
    // one at a time: a 2nd click would open a 2nd new chat => said, never silently dropped
    if (saying) return tell(panel, today.STILL_OPENING);
    saying = true;
    try {
      return await sayWords(root, action.words, (text, how) => tell(panel, text, how),
        (on, label) => panel.webview.postMessage({ type: "busy", on, label }));
    } finally {
      saying = false;
    }
  }
}

// installed Claude's version + where it opens chats: decides "new" vs "copy" (today.sayMode)
function claudeSeen() {
  const ext = vscode.extensions.getExtension(today.CLAUDE_ID);
  return {
    version: ext ? ext.packageJSON.version : null,
    location: vscode.workspace.getConfiguration("claudeCode").get("preferredLocation"),
  };
}

function sayModeNow(root) {
  return today.sayMode(currentAi(root), claudeSeen());
}

let saying = false;

// chat extension already running (window warm-up or an earlier click) => "Opening the chat", not
// "Starting Claude"; Copilot's chat is built in. Not installed => the copy path, nothing starts
function chatWarm(ai) {
  const plan = start.warmUpPlan(ai);
  if (!plan) return true;
  const ext = vscode.extensions.getExtension(plan.id);
  return !ext || ext.isActive;
}

// words into the chat, never sent (today.say); returns the mode that ran (probe reads it)
async function sayWords(root, words, status, busy = () => {}) {
  const ai = currentAi(root);
  const mode = await today.say({
    ai, mode: sayModeNow(root), words, platform: process.platform, status, busy, warm: chatWarm(ai),
    exec: (command, ...args) => vscode.commands.executeCommand(command, ...args),
    copy: (text) => vscode.env.clipboard.writeText(text),
  });
  if (mode === "new") vscode.window.setStatusBarMessage(today.readyLine(mode, today.jobOf(words)), today.CLEAR_MS);
  return mode;
}

// true while a rebuild runs: the fallback says "being updated", not "couldn't be read"
let refreshing = false;

// rebuilds Today in the background; done() once it ends. false = couldn't start (no uv)
function findUv() {
  return start.uvCandidates({
    platform: process.platform, home: os.homedir(), userProfile: process.env.USERPROFILE, envPath: process.env.PATH,
  }).find((file) => fs.existsSync(file)) || null;
}

function refreshToday(root, done = () => {}) {
  const uv = findUv();
  if (!uv) return false;  // last page stays: still better than none
  refreshing = true;
  childProcess.execFile(uv, ["run", "app/jobs.py", "today", "--refresh"],
    { cwd: root, windowsHide: true, timeout: 120000 }, () => { refreshing = false; done(); });
  return true;
}

function redact(text) {
  const home = os.homedir();
  return home ? text.split(home).join("~") : text;
}

function tabInput(input) {
  if (!input) return { type: "unknown" };
  if (input instanceof vscode.TabInputText) return { type: "text", uri: input.uri.toString() };
  if (input instanceof vscode.TabInputTextDiff) return { type: "diff", uri: input.modified.toString() };
  if (input instanceof vscode.TabInputCustom) return { type: "custom", viewType: input.viewType, uri: input.uri.toString() };
  if (input instanceof vscode.TabInputWebview) return { type: "webview", viewType: input.viewType };
  if (input instanceof vscode.TabInputNotebook) return { type: "notebook", uri: input.uri.toString() };
  if (input instanceof vscode.TabInputTerminal) return { type: "terminal" };
  return { type: "other" };
}

function readWindow() {
  return vscode.window.tabGroups.all.map((group) => ({
    viewColumn: group.viewColumn,
    isActive: group.isActive,
    tabs: group.tabs.map((tab) => ({ label: tab.label, isActive: tab.isActive, ...tabInput(tab.input) })),
  }));
}

async function probe(context, out, opened, warmed) {
  const started = Date.now();
  const t0 = Number(process.env[PROBE_T0_ENV]) || null;
  const since = (at) => (t0 && at ? at - t0 : null);
  const report = { vscode: vscode.version, at: new Date().toISOString(), activatedMs: Math.round(process.uptime() * 1000), t0 };
  // when the chat extension turns active, from window launch (t0) - with or w/o our warm-up
  const watched = vscode.extensions.getExtension(today.CLAUDE_ID);
  report.claudeActive = { launchToOursMs: since(started), atOurActivation: Boolean(watched && watched.isActive) };
  const poll = setInterval(() => {
    if (watched && watched.isActive && report.claudeActive.launchToActiveMs == null) report.claudeActive.launchToActiveMs = since(Date.now());
  }, 50);
  await opened;
  report.claudeActive.launchToPageMs = since(Date.now());
  report.tabsAtActivation = readWindow();
  const pages = (process.env[PROBE_OPEN_ENV] || "").split("|").filter(Boolean);
  if (pages.length) {
    const how = process.env[PROBE_OPEN_HOW_ENV] || "showPreview";
    report.open = [];
    for (const page of pages) {
      const uri = vscode.Uri.file(page);
      try {
        if (how === "openWith") await vscode.commands.executeCommand("vscode.openWith", uri, "vscode.markdown.preview.editor");
        else if (how === "open") await vscode.commands.executeCommand("vscode.open", uri, { preview: false });
        else await vscode.commands.executeCommand("markdown.showPreview", uri);
        report.open.push({ how, page: uri.toString(), ok: true, ms: Date.now() - started });
      } catch (err) {
        report.open.push({ how, page: uri.toString(), ok: false, error: String(err) });
      }
    }
    report.tabsAfterOpen = readWindow();
  }
  const settle = Number(process.env[PROBE_SETTLE_ENV] || 6000);
  await new Promise((done) => setTimeout(done, settle));
  report.settleMs = settle;
  clearInterval(poll);
  const warm = await Promise.race([warmed, new Promise((done) => setTimeout(() => done("pending"), 1))]);
  report.warm = warm && typeof warm === "object"
    ? { id: warm.id, how: warm.how, launchToStartMs: since(warm.startAt), launchToActiveMs: since(warm.activeAt), launchToViewMs: since(warm.viewAt) }
    : warm;
  report.tabs = readWindow();
  report.theme = { kind: vscode.window.activeColorTheme.kind, name: vscode.workspace.getConfiguration("workbench").get("colorTheme") };
  report.folders = (vscode.workspace.workspaceFolders || []).map((f) => f.uri.toString());
  report.extensions = vscode.extensions.all
    .filter((e) => !e.packageJSON.isBuiltin && !e.id.startsWith("vscode."))
    .map((e) => `${e.id}@${e.packageJSON.version}`).sort();
  const commands = await vscode.commands.getCommands(true);
  report.commands = commands.filter((c) => PROBE_COMMANDS.some((re) => re.test(c))).sort();
  const settings = {};
  for (const key of PROBE_SETTINGS) {
    const seen = vscode.workspace.getConfiguration().inspect(key);
    if (seen) settings[key] = { value: vscode.workspace.getConfiguration().get(key), user: seen.globalValue, workspace: seen.workspaceValue };
  }
  report.settings = settings;
  const words = process.env[PROBE_SAY_ENV];
  const folder = (vscode.workspace.workspaceFolders || [])[0];
  if (words && folder) {
    const root = folder.uri.fsPath;
    report.say = { words, ai: currentAi(root), claude: claudeSeen(), status: [] };
    report.say.tabsBefore = readWindow();
    report.say.claudeActiveBefore = Boolean(watched && watched.isActive);
    const pressed = Date.now();
    report.say.busy = [];
    report.say.mode = await sayWords(root, words, (text) => report.say.status.push({ text, ms: Date.now() - pressed }),
      (on) => report.say.busy.push({ on, ms: Date.now() - pressed }));
    report.say.pressToReadyMs = Date.now() - pressed;
    report.say.pressedLaunchMs = since(pressed);
    await new Promise((done) => setTimeout(done, 4000));
    report.say.tabsAfter = readWindow();
  }
  const word = process.env[PROBE_LOOK_ENV];
  if (word && folder) {
    const theme = () => ({ kind: vscode.window.activeColorTheme.kind, name: vscode.workspace.getConfiguration("workbench").get("colorTheme"),
      autoDetect: vscode.workspace.getConfiguration("window").get("autoDetectColorScheme") });
    report.look = { word, before: theme(), messages: [], changes: [] };
    const pressed = Date.now();
    const sub = vscode.window.onDidChangeActiveColorTheme((t) => report.look.changes.push({ kind: t.kind, ms: Date.now() - pressed }));
    await new Promise((done) => {
      const panel = { webview: { postMessage: (msg) => {
        report.look.messages.push({ ...msg, ms: Date.now() - pressed });
        if (msg.type === "status") done();
      } } };
      switchLook(folder.uri.fsPath, word, panel);
    });
    await new Promise((done) => setTimeout(done, 3000));
    sub.dispose();
    report.look.after = theme();
    report.look.tabsAfter = readWindow();  // same extension host still running => no window reload
  }
  fs.writeFileSync(out, redact(JSON.stringify(report, null, 1)) + "\n");
  await vscode.commands.executeCommand("workbench.action.quit");
}

module.exports = { activate, deactivate };
