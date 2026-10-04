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
const PROBE_COMMANDS = [/^claude-vscode\./, /^chatgpt\./, /^workbench\.action\.chat\./, /outline/i, /timeline/i, /^vscode\.moveViews$/, /^markdown\.showPreview/];
const PROBE_SETTINGS = [
  "workbench.colorTheme", "window.autoDetectColorScheme", "workbench.startupEditor",
  "workbench.welcomePage.walkthroughs.openOnInstall", "workbench.editorAssociations",
  "markdown.styles", "claudeCode.hideOnboarding", "claudeCode.preferredLocation",
  "workbench.secondarySideBar.defaultVisibility", "chat.commandCenter.enabled",
];

function activate(context) {
  context.subscriptions.push(vscode.window.registerCustomEditorProvider(today.VIEW_TYPE, { resolveCustomTextEditor: showToday },
    { webviewOptions: { enableFindWidget: true }, supportsMultipleEditorsPerDocument: false }));
  const out = process.env[PROBE_ENV];
  // probe told which pages to open => measures that alone, not the start page
  const opened = out && process.env[PROBE_OPEN_ENV] ? Promise.resolve() : openStartPage().catch(() => {});
  if (!out) return;
  const editor = process.env[PROBE_EDITOR_ENV];
  if (editor) {
    context.subscriptions.push(vscode.window.registerCustomEditorProvider(editor, {
      resolveCustomTextEditor(document, panel) {
        panel.webview.html = "<p>probe editor</p>";
      },
    }));
  }
  opened.then(() => probe(context, out));
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
// looked up here, checked again, never taken from the page.
function showToday(document, panel) {
  const root = path.dirname(document.uri.fsPath);
  const at = (rel) => path.join(root, ...rel.split("/"));
  panel.webview.options = { enableScripts: true, localResourceRoots: [] };
  let m = null;
  const draw = () => {
    const nonce = crypto.randomBytes(16).toString("base64");
    m = null;
    try {
      if (start.isJobFinder((rel) => fs.existsSync(at(rel)))) {
        m = today.model(JSON.parse(fs.readFileSync(at(today.DATA), "utf8")), say);
      }
    } catch {}
    // a file a button names may have moved since (job filed under another stage) => no button
    if (m) for (const s of m.sections) for (const c of s.cards) {
      if (c.resume && !fs.existsSync(at(c.resume.path))) c.resume = null;
      if (c.folder && !fs.existsSync(at(c.folder.path))) c.folder = null;
    }
    panel.webview.html = m ? today.render(m, { mode: sayModeNow(root), nonce }) : today.fallback({ nonce });
  };
  draw();
  const watcher = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(vscode.Uri.file(root), start.TODAY));
  const subs = [
    watcher, watcher.onDidChange(draw), watcher.onDidCreate(draw),
    panel.onDidChangeViewState(() => { if (panel.visible) draw(); }),
    panel.webview.onDidReceiveMessage((msg) => act(root, at, document.uri, m, msg, panel).catch(() => {})),
  ];
  panel.onDidDispose(() => subs.forEach((s) => s.dispose()));
}

function currentAi(root) {
  try {
    return fs.readFileSync(path.join(root, start.AI_FILE), "utf8").trim().toLowerCase();
  } catch {
    return null;
  }
}

function tell(panel, text) {
  panel.webview.postMessage({ type: "status", text });
}

async function act(root, at, page, m, msg, panel) {
  const index = msg && Number.isInteger(msg.action) ? msg.action : null;
  if (index === -1) return vscode.commands.executeCommand("vscode.openWith", page, start.PREVIEW_EDITOR);
  const action = m && index != null ? m.actions[index] : null;
  if (!action) return;
  if (action.type === "posting") {
    const url = today.cleanUrl(action.url);
    // a string, not a Uri: passed on exactly as written (a Uri re-encodes it; a rebuilt link 404s)
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
  if (action.type === "say") {
    if (!today.templateFor(action.words, today.templates(say))) return;
    return sayWords(root, action.words, (text) => tell(panel, text));
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

// words into the chat, never sent; returns the mode that ran (probe reads it)
async function sayWords(root, words, status) {
  const ai = currentAi(root);
  const mode = sayModeNow(root);
  if (mode === "fill") {
    try {
      // fills the box, never sends: isPartialQuery
      await vscode.commands.executeCommand("workbench.action.chat.open", { query: words, isPartialQuery: true });
      status(today.filledLine());
      return mode;
    } catch {}
  }
  if (mode === "new") {
    try {
      await vscode.commands.executeCommand(today.CLAUDE_NEW_CHAT, ...today.claudeNewChatArgs(words));
      status(today.newChatLine());
      vscode.window.setStatusBarMessage(today.newChatLine(), 8000);
      return mode;
    } catch {}
  }
  await vscode.env.clipboard.writeText(words);
  if (today.CHAT_OPEN[ai]) await Promise.resolve(vscode.commands.executeCommand(today.CHAT_OPEN[ai])).catch(() => {});
  status(today.copiedLine(process.platform));
  return "copy";
}

function refreshToday(root) {
  const uv = start.uvCandidates({
    platform: process.platform, home: os.homedir(), userProfile: process.env.USERPROFILE, envPath: process.env.PATH,
  }).find((file) => fs.existsSync(file));
  if (!uv) return;  // last page stays: still better than none
  childProcess.execFile(uv, ["run", "app/jobs.py", "today", "--refresh"],
    { cwd: root, windowsHide: true, timeout: 120000 }, () => {});
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

async function probe(context, out) {
  const started = Date.now();
  const report = { vscode: vscode.version, at: new Date().toISOString(), activatedMs: Math.round(process.uptime() * 1000) };
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
    report.say.mode = await sayWords(root, words, (text) => report.say.status.push(text));
    await new Promise((done) => setTimeout(done, 4000));
    report.say.tabsAfter = readWindow();
  }
  fs.writeFileSync(out, redact(JSON.stringify(report, null, 1)) + "\n");
  await vscode.commands.executeCommand("workbench.action.quit");
}

module.exports = { activate, deactivate };
