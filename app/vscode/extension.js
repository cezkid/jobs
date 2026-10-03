// CEZ Job Finder window extension. Plain JS, no build step, no npm deps.
// Never reads files from app/ at runtime: Windows locks them during an update. All it needs is
// inside the vsix (app/vscode_ext.py builds it).
const vscode = require("vscode");
const fs = require("fs");
const os = require("os");

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
const PROBE_COMMANDS = [/^claude-vscode\./, /^chatgpt\./, /^workbench\.action\.chat\./, /outline/i, /timeline/i, /^vscode\.moveViews$/, /^markdown\.showPreview/];
const PROBE_SETTINGS = [
  "workbench.colorTheme", "window.autoDetectColorScheme", "workbench.startupEditor",
  "workbench.welcomePage.walkthroughs.openOnInstall", "workbench.editorAssociations",
  "markdown.styles", "claudeCode.hideOnboarding", "claudeCode.preferredLocation",
  "workbench.secondarySideBar.defaultVisibility", "chat.commandCenter.enabled",
];

function activate(context) {
  const out = process.env[PROBE_ENV];
  if (!out) return;
  const editor = process.env[PROBE_EDITOR_ENV];
  if (editor) {
    context.subscriptions.push(vscode.window.registerCustomEditorProvider(editor, {
      resolveCustomTextEditor(document, panel) {
        panel.webview.html = "<p>probe editor</p>";
      },
    }));
  }
  probe(context, out);
}

function deactivate() {}

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
  fs.writeFileSync(out, redact(JSON.stringify(report, null, 1)) + "\n");
  await vscode.commands.executeCommand("workbench.action.quit");
}

module.exports = { activate, deactivate };
