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
const jobs = require("./jobs");
const say = require("./say.json");
const setup = require("./setup");
const setupForm = require("./setup-form.json");

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
// probe only: a folder the driver drops <name>.req JSON into while the window stays up, answered in
// <name>.res: {do: "today-link", urls} = a Today click's own path, all at once; {do: "command", id,
// args}; {do: "tabs"}; {do: "quit"}. 10 min cap
const PROBE_HOLD_ENV = "JOBS_VSCODE_PROBE_HOLD";
const PROBE_COMMANDS = [/^cezJobFinder\./, /^claude-vscode\./, /^chatgpt\./, /^workbench\.action\.chat\./, /outline/i, /timeline/i, /^vscode\.moveViews$/, /^markdown\.showPreview/];
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
  context.subscriptions.push(vscode.window.registerCustomEditorProvider(today.WELCOME_TYPE, { resolveCustomTextEditor: (document, panel) =>
    showWelcome(document, panel, vscode.Uri.joinPath(context.extensionUri, ...today.FONT_DIR)) },
    // kept alive while another tab is in front: half-typed answers survive a look at the chat
    { webviewOptions: { retainContextWhenHidden: true }, supportsMultipleEditorsPerDocument: false }));
  jobsTree = showJobs(context);
  watchLinks(context);
  noteRunning(context);
  const out = process.env[PROBE_ENV];
  // probe told which pages to open => measures that alone, not the start page
  const opened = out && process.env[PROBE_OPEN_ENV] ? Promise.resolve() : openStartPage().catch(() => {});
  const shown = opened.then((root) => (root ? openJobs(context) : null)).catch(() => null);
  const warmed = shown.then(() => opened).then((root) => (root ? warmUp(root) : null)).catch(() => null);
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
  try {
    return await openPage(root, at);
  } finally {
    markReady(root);  // page up, or it failed: either way the loading splash has nothing left to wait for
  }
}

// loading splash closes on this file (start.readyFile). Job Finder's folder only; never throws
function markReady(root) {
  try {
    if (!start.isJobFinder((rel) => fs.existsSync(path.join(root, rel)))) return;
    const { file, text } = start.readyFile(root, Date.now());
    fs.writeFileSync(file, text);
  } catch {}
}

async function openPage(root, at) {
  let marker = null;
  try {
    marker = fs.readFileSync(at(start.MARKER), "utf8");
    fs.unlinkSync(at(start.MARKER));
  } catch {}
  const settingsExist = fs.existsSync(at(start.SETTINGS));
  const todayMtime = mtime(at(start.TODAY));
  const page = start.choosePage({ marker, settingsExist, todayExists: todayMtime != null });
  // welcome page says these itself, above its steps; Today gets them as corner lines
  if (page === start.TODAY) {
    // launcher found VS Code running => its own profile waits for one cold start; say how, once a window
    if (fs.existsSync(at(start.PROFILE_PENDING))) vscode.window.showInformationMessage(profilePendingLine());
    // opened w/o the Desktop icon, folder not yet trusted => say how to get the AI panel back
    if (!vscode.workspace.isTrusted) noteUntrusted();
  } else if (!vscode.workspace.isTrusted) untrustedShown = start.UNTRUSTED_LINE;
  if (start.needsRefresh({ marker, settingsExist, todayMtime, stampMtime: mtime(at(start.STAMP)), now: Date.now() })) {
    refreshToday(root);  // not awaited: the page shows now, its preview redraws once rewritten
  }
  await showPage(vscode.Uri.file(at(page)), page === start.TODAY ? today.VIEW_TYPE : today.WELCOME_TYPE);
  return root;
}

function profilePendingLine() {
  return start.PROFILE_PENDING_LINE[process.platform === "darwin" ? "darwin" : "other"];
}

let untrustedShown = null;

function noteUntrusted() {
  untrustedShown = start.UNTRUSTED_LINE;
  vscode.window.showWarningMessage(start.UNTRUSTED_LINE, start.UNTRUSTED_BUTTON).then((pick) => {
    if (pick === start.UNTRUSTED_BUTTON) vscode.commands.executeCommand(start.UNTRUSTED_COMMAND);
  }, () => {});
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

// VS Code starts an extension's view in the Explorer collapsed, whatever package.json says (measured
// 1.140, probe o) => open it once per folder, then focus back to the page; later the user's own
// collapse holds (VS Code keeps it per folder, as we do the flag)
const JOBS_SHOWN = "cez-job-finder.jobs-shown";

async function openJobs(context) {
  if (!jobsTree || context.workspaceState.get(JOBS_SHOWN)) return;
  await context.workspaceState.update(JOBS_SHOWN, true);
  if (jobsTree.view.visible) return;
  try {
    await vscode.commands.executeCommand(`${jobs.VIEW_ID}.focus`);
    await vscode.commands.executeCommand("workbench.action.focusActiveEditorGroup");
  } catch {}
}

function tabSeen(tab) {
  const input = tab.input;
  if (input instanceof vscode.TabInputText) return { kind: "text", fsPath: input.uri.fsPath, label: tab.label, tab };
  if (input instanceof vscode.TabInputCustom) return { kind: "custom", fsPath: input.uri.fsPath, viewType: input.viewType, label: tab.label, tab };
  if (input instanceof vscode.TabInputWebview) return { kind: "webview", label: tab.label, tab };
  return { kind: "other", label: tab.label, tab };
}

// viewType = the page's own view: Today's dashboard, START HERE's welcome page
async function showPage(uri, viewType) {
  const tabs = vscode.window.tabGroups.all.flatMap((group) => group.tabs.map(tabSeen));
  const { formatted, text } = start.pageTabs(tabs, uri.fsPath, process.platform);
  const stale = [];
  // restored as the plain page view (a window from before its own view) => its own view instead
  const fresh = !(formatted && formatted.viewType === viewType);
  if (fresh && formatted) stale.push(formatted.tab);
  if (fresh) await vscode.commands.executeCommand("vscode.openWith", uri, viewType, { preview: false });
  else await vscode.commands.executeCommand("vscode.openWith", uri, viewType);
  // a plain-text copy from an older launch would come back on every start; the page is generated
  stale.push(...text.map((t) => t.tab).filter((tab) => !tab.isDirty));
  if (stale.length) await vscode.window.tabGroups.close(stale, true);
}

// .data/today.json => today.model, files its buttons name checked; reason = why none (today.FALLBACK)
function readModel(root) {
  const at = (rel) => path.join(root, ...rel.split("/"));
  let m = null;
  let reason = "unreadable";
  try {
    if (start.isJobFinder((rel) => fs.existsSync(at(rel)))) {
      if (!fs.existsSync(at(today.DATA))) reason = "missing";
      else m = today.model(JSON.parse(fs.readFileSync(at(today.DATA), "utf8")), say);
    }
  } catch {}
  if (refreshing) reason = "updating";
  // a file a button names may have moved since (job filed under another stage) => no button
  const cards = m ? [...m.sections.flatMap((s) => s.cards), ...(m.next && m.next.card ? [m.next.card] : [])] : [];
  for (const c of cards) {
    if (c.resume && !fs.existsSync(at(c.resume.path))) c.resume = null;
    if (c.folder && !fs.existsSync(at(c.folder.path))) c.folder = null;
  }
  return { m, reason };
}

// I sent it / I heard back / It's closed: saved by `jobs.py status`, Undo after (today.statusKeeper)
function keeperFor(root, refresh, tellFn) {
  return today.statusKeeper({
    run: (args) => {
      const uv = findUv();
      return uv ? start.runJobs({ execFile: childProcess.execFile, uv, root, args }) : Promise.reject(new Error("no uv"));
    },
    refresh: () => refreshToday(root, refresh),
    tell: tellFn,
  });
}

// Today dashboard (custom editor on Today.md, workspace association app/workspace.py): drawn from
// .data/today.json, redrawn when the page is rewritten. Buttons send an index; what it does is
// looked up here, checked again, never taken from the page. fontDir = the installed extension's
// media/fonts (Literata): the one folder the page may load from
function showToday(document, panel, fontDir) {
  const root = path.dirname(document.uri.fsPath);
  const at = (rel) => path.join(root, ...rel.split("/"));
  const fonts = pageFonts(panel, fontDir);
  let m = null;
  const draw = () => {
    const nonce = crypto.randomBytes(16).toString("base64");
    let reason;
    ({ m, reason } = readModel(root));
    const ai = currentAi(root);
    const restart = restartNow(root);
    todayShown = { restart, at: Date.now() };
    panel.webview.html = m ? today.render(m, { mode: sayModeNow(root), ai, nonce, fonts, look: currentLook(root), ready: chatWarm(ai), restart })
      : today.fallback({ nonce, reason, fonts });
  };
  // I sent it / I heard back / It's closed: Undo in the page's status line
  const keeper = keeperFor(root, draw, (text, how) => tell(panel, text, how));
  // fallback's Try again: rebuild the list (page redraws when it's rewritten), else just read it again
  const retry = () => {
    const started = !refreshing && refreshToday(root, draw);
    draw();
    if (!started && !refreshing && !m) tell(panel, "Still not ready - it's made again at the next start.");
  };
  try {
    draw();
  } finally {
    markReady(root);  // Today restored w/ the window draws before the start page step ends
  }
  const watcher = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(vscode.Uri.file(root), start.TODAY));
  const subs = [
    watcher, watcher.onDidChange(draw), watcher.onDidCreate(draw),
    panel.onDidChangeViewState(() => { if (panel.visible) draw(); }),
    panel.webview.onDidReceiveMessage((msg) => act(root, at, document.uri, m, msg, panel, retry, keeper).catch(() => {})),
  ];
  todayDraws.add(draw);
  panel.onDidDispose(() => {
    todayDraws.delete(draw);
    subs.forEach((s) => s.dispose());
  });
}

// scripts on, fonts from the extension's media/fonts only => today.fontFaces input
function pageFonts(panel, fontDir) {
  panel.webview.options = { enableScripts: true, localResourceRoots: [fontDir] };
  const fonts = { source: panel.webview.cspSource, files: {} };
  for (const [style, file] of Object.entries(today.FONTS)) {
    fonts.files[style] = panel.webview.asWebviewUri(vscode.Uri.joinPath(fontDir, file)).toString();
  }
  return fonts;
}

// lines the welcome page shows above its steps: profile waiting on a cold start, Restricted Mode
function welcomeNotes(root) {
  const notes = [];
  if (fs.existsSync(path.join(root, start.PROFILE_PENDING))) notes.push({ text: profilePendingLine() });
  if (!vscode.workspace.isTrusted) notes.push({ text: start.UNTRUSTED_LINE, allow: start.UNTRUSTED_BUTTON });
  return notes;
}

// chat panel back on screen (closed once => VS Code keeps it closed): the AI's own view command;
// Copilot's chat is built in. Never a new chat, never words
async function showChat(root) {
  const ai = currentAi(root);
  const command = ai === "copilot" ? "workbench.action.chat.open" : today.CHAT_OPEN[ai];
  try {
    await vscode.commands.executeCommand(command || "workbench.action.focusAuxiliaryBar");
  } catch {
    try { await vscode.commands.executeCommand("workbench.action.focusAuxiliaryBar"); } catch {}
  }
}

// answers saved earlier (.data/setup-form.json), {} when none or unreadable
function savedAnswers(root) {
  try {
    const raw = JSON.parse(fs.readFileSync(path.join(root, setup.ANSWERS), "utf8"));
    return raw && typeof raw === "object" ? raw : {};
  } catch {
    return {};
  }
}

// answers file rewritten whole: what the page sent (setup.clean) + the resume picked, if any
function saveAnswers(root, answers, resume) {
  const file = path.join(root, setup.ANSWERS);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(`${file}.tmp`, setup.answersFile(answers, { resume, now: Date.now() }));
  fs.renameSync(`${file}.tmp`, file);
}

// Choose my resume file: the system's own file picker; never read here, never sent anywhere. Read at
// once by resume import's first step on this computer (`resume-import prepare --file`: copies it to My
// Resume/Original resume.<ext> + takes its text out) => a scan or a Pages file is said on this page,
// not minutes into setup, and setup starts from a resume already read. Resume details already made
// (setup run before) or no uv => copied into My Resume as it is. Returns its path inside the folder
const RESUME_MAX_BYTES = 30 * 1024 * 1024;
const RESUME_UNREADABLE = "Couldn't read the words in that file - it may be a scan or a picture of a resume. Choose a PDF saved from Word or Google Docs, or click I don't have one yet - the chat can help.";

async function chooseResume(root, busy = () => {}) {
  const picked = await vscode.window.showOpenDialog({
    canSelectMany: false, canSelectFolders: false, openLabel: "Use this resume", title: "Choose your resume",
    filters: { "Resume (PDF or Word)": setup.RESUME_KINDS },
  });
  const from = picked && picked[0] && picked[0].fsPath;
  if (!from) return { cancelled: true };
  if (!setup.isResumeKind(from)) return { error: "That isn't a PDF or Word file - choose your resume as a PDF or Word file." };
  if (fs.statSync(from).size > RESUME_MAX_BYTES) return { error: "That file is too big for a resume - choose your resume as a PDF or Word file." };
  const uv = findUv();
  if (uv && !fs.existsSync(path.join(root, setup.RESUME_DIR, setup.DETAILS))) {
    busy(true, "Reading your resume…");
    try {
      return await readResume(root, uv, from);
    } finally {
      busy(false);
    }
  }
  const dir = path.join(root, setup.RESUME_DIR);
  fs.mkdirSync(dir, { recursive: true });
  if (path.dirname(path.resolve(from)) === path.resolve(dir)) return { rel: `${setup.RESUME_DIR}/${path.basename(from)}` };
  const taken = new Set(fs.readdirSync(dir).map((n) => n.toLowerCase()));
  const name = setup.resumeName(path.basename(from), taken);
  fs.copyFileSync(from, path.join(dir, name), fs.constants.COPYFILE_EXCL);
  return { rel: `${setup.RESUME_DIR}/${name}` };
}

// resume import's first step on the picked file; {rel} = where it put the copy (its own record), or
// {error} in plain words: its refusal line for a Pages / older Word file, else RESUME_UNREADABLE
function readResume(root, uv, from) {
  return new Promise((done) => {
    childProcess.execFile(uv, ["run", "app/jobs.py", "resume-import", "prepare", "--file", from],
      { cwd: root, windowsHide: true, timeout: 120000 }, (err, stdout, stderr) => {
        if (err) return done({ error: setup.readError(String(stderr || ""), path.basename(from)) || RESUME_UNREADABLE });
        try {
          const file = JSON.parse(fs.readFileSync(path.join(root, setup.SOURCE), "utf8")).file;
          const rel = path.relative(root, file).split(path.sep).join("/");
          if (!rel.startsWith(`${setup.RESUME_DIR}/`)) return done({ error: RESUME_UNREADABLE });
          return done({ rel });
        } catch {
          return done({ error: RESUME_UNREADABLE });
        }
      });
  });
}

// Welcome page (custom editor on START HERE.md, association app/workspace.py): sign in, a short form
// (setup-form.json), the resume file, then the yellow button (today.startLabel) = answers saved to
// .data/setup-form.json + their answers in plain words (setup.summary) into the chat by the Today
// buttons' own path (sayOnce -> say); job-setup reads the file and asks only what's missing. Buttons send a fixed number; what it does is decided here.
// W/o this extension VS Code drops the association => START HERE.md as the formatted page
function showWelcome(document, panel, fontDir) {
  const root = path.dirname(document.uri.fsPath);
  const at = (rel) => path.join(root, ...rel.split("/"));
  const fonts = pageFonts(panel, fontDir);
  const saved = savedAnswers(root);
  let resume = typeof saved.resume === "string" && fs.existsSync(at(saved.resume)) ? saved.resume : null;
  // drawn once: a redraw would wipe what they typed (the panel stays alive while hidden)
  const ai = currentAi(root);
  // Copilot: its start button sends (today.say "send"); Claude + ChatGPT fill only (app-window.md #v)
  const mode = () => (ai === "copilot" ? "send" : sayModeNow(root));
  panel.webview.html = today.welcome({ mode: mode(), ai, nonce: crypto.randomBytes(16).toString("base64"), fonts,
    ready: chatWarm(ai), notes: welcomeNotes(root), platform: process.platform, form: setupForm,
    saved: setup.clean(saved, setupForm), resume: resume ? path.basename(resume) : "" });
  const ui = {
    tell: (text, how) => tell(panel, text, how),
    busy: (on, label) => panel.webview.postMessage({ type: "busy", on, label }),
    keeper: null,
  };
  const act = async (msg) => {
    if (msg && msg.form && typeof msg.form === "object") {
      const answers = setup.clean(msg.form, setupForm);
      try {
        saveAnswers(root, answers, resume);
      } catch {
        ui.busy(false);
        return ui.tell("Couldn't save your answers here. Type set me up in the chat instead - it asks them there.", { hold: true });
      }
      // the words rebuilt here from what was cleaned + saved, never the page's own text
      const words = setup.summary(answers, setupForm, resume ? path.basename(resume) : "");
      const ran = await sayOnce(root, words, ui, (how) => today.setupReady(how, process.platform), mode());
      // what really ran (send / fill / new / copy) => the page shows that next step where the button was
      if (ran) panel.webview.postMessage({ type: "started", mode: ran });
      return ran;
    }
    const index = msg && Number.isInteger(msg.action) ? msg.action : null;
    if (index === today.SHOW_CHAT) return showChat(root);
    if (index === today.ALLOW_HERE) return vscode.commands.executeCommand(start.UNTRUSTED_COMMAND);
    if (index === today.CHOOSE_RESUME) {
      let got;
      try {
        got = await chooseResume(root, ui.busy);
      } catch {
        got = { error: "Couldn't copy that file. Drag your resume onto My Resume in the file list instead." };
      }
      if (got.error) return ui.tell(got.error, { hold: true });
      if (!got.rel) return;
      resume = got.rel;
      // on file at once: "set me up" typed by hand (no button) still finds it
      try { saveAnswers(root, setup.clean(savedAnswers(root), setupForm), resume); } catch {}
      panel.webview.postMessage({ type: "resume", name: path.basename(resume) });
      return ui.tell(`Resume read: ${path.basename(resume)} - in My Resume, on this computer only. You can skip the questions it answers.`);
    }
    const guide = today.WELCOME_GUIDES.find((g) => g.action === index);
    if (guide) return doAction(root, at, { type: "open", path: guide.path, how: "page" }, ui);
  };
  const subs = [panel.webview.onDidReceiveMessage((msg) => act(msg).catch(() => ui.busy(false)))];
  panel.onDidDispose(() => subs.forEach((s) => s.dispose()));
}

// Jobs side panel (jobs.js, view at the top of the file list): same model + actions as the
// dashboard, redrawn when Today's data or a job folder changes. Rows carry the model's generation +
// an action index; a click on a row drawn from an older model does nothing
let jobsTree = null;

function showJobs(context) {
  const folder = (vscode.workspace.workspaceFolders || [])[0];
  const root = folder && folder.uri.scheme === "file" ? folder.uri.fsPath : null;
  const at = (rel) => path.join(root, ...rel.split("/"));
  const changed = new vscode.EventEmitter();
  const state = { m: null, groups: [], gen: 0 };
  const load = () => {
    state.gen += 1;
    state.m = null;
    state.groups = [];
    if (root && start.isJobFinder((rel) => fs.existsSync(at(rel)))) {
      state.m = readModel(root).m;
      state.groups = jobs.tree(state.m, listApplied(at(jobs.APPLIED_DIR)));
      state.setUp = fs.existsSync(at(start.SETTINGS.split(path.sep).join("/")));
      state.ready = true;
    }
    changed.fire();
  };
  const run = (action) => (action != null ? { command: jobs.RUN, title: "", arguments: [{ gen: state.gen, action }] } : undefined);
  const provider = {
    onDidChangeTreeData: changed.event,
    getChildren(el) {
      if (!root || !state.ready) return [];
      if (!el) return state.groups.length ? state.groups.map((g) => ({ group: g })) : [{ job: jobs.emptyRow(state.m, state.setUp) }];
      if (el.group) return el.group.items.map((j) => ({ job: j }));
      if (el.job) return el.job.rows.map((r) => ({ row: r, parent: el.job.id }));
      return [];
    },
    getTreeItem(el) {
      const None = vscode.TreeItemCollapsibleState.None;
      if (el.group) {
        const item = new vscode.TreeItem(el.group.label, vscode.TreeItemCollapsibleState.Expanded);
        item.id = `group/${el.group.id}`;
        item.description = String(el.group.items.length);
        item.accessibilityInformation = { label: `${el.group.label}, ${el.group.items.length}` };
        return item;
      }
      if (el.job) {
        const j = el.job;
        const item = new vscode.TreeItem(j.label, j.rows.length ? vscode.TreeItemCollapsibleState.Collapsed : None);
        item.id = j.id;
        item.description = j.description;
        item.tooltip = j.tooltip;
        item.accessibilityInformation = { label: j.accessible };
        if (j.icon) item.iconPath = new vscode.ThemeIcon(j.icon);
        item.command = j.setup ? { command: jobs.RUN, title: "", arguments: [{ setup: true }] } : run(j.action);
        return item;
      }
      const r = el.row;
      const item = new vscode.TreeItem(r.label, None);
      item.id = `${el.parent}/${r.action}`;
      item.iconPath = new vscode.ThemeIcon(r.icon);
      if (r.tooltip) item.tooltip = r.tooltip;
      item.command = run(r.action);
      return item;
    },
  };
  const view = vscode.window.createTreeView(jobs.VIEW_ID, { treeDataProvider: provider, showCollapseAll: true });
  // the panel's own lines: a toast, Undo as its button; "starting" lines in the status bar
  const tellJobs = (text, how = {}) => {
    if (how.undo) {
      vscode.window.showInformationMessage(text, "Undo").then((pick) => { if (pick) keeper.undo(); }, () => {});
    } else if (how.hold) vscode.window.setStatusBarMessage(text, today.CLEAR_MS);
    else vscode.window.showInformationMessage(text);
  };
  let busyLine = null;
  const ui = {
    tell: tellJobs,
    busy: (on, label) => {
      if (busyLine) busyLine.dispose();
      busyLine = on ? vscode.window.setStatusBarMessage(label) : null;
    },
    keeper: null,
  };
  const keeper = root ? keeperFor(root, load, tellJobs) : null;
  ui.keeper = keeper;
  let timer = null;
  const soon = () => { clearTimeout(timer); timer = setTimeout(load, 300); };
  const subs = [view, changed,
    vscode.commands.registerCommand(jobs.RUN, (arg) => {
      // not set up yet: the panel's one row opens the welcome page (sign in, the form, Set me up)
      if (root && arg && arg.setup === true && !state.setUp) {
        return vscode.commands.executeCommand("vscode.openWith", vscode.Uri.file(at(start.START_HERE)), today.WELCOME_TYPE).then(undefined, () => {});
      }
      if (!root || !state.m || !arg || arg.gen !== state.gen || !Number.isInteger(arg.action)) return;
      const action = state.m.actions[arg.action];
      if (action) return doAction(root, at, action, ui).catch(() => {});
    })];
  if (root) {
    // search settings saved by setup => the Set me up row goes
    for (const glob of [today.DATA.split(path.sep).join("/"), `${jobs.APPLIED_DIR.split("/")[0]}/**`, start.SETTINGS.split(path.sep).join("/")]) {
      const w = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(folder.uri, glob));
      subs.push(w, w.onDidChange(soon), w.onDidCreate(soon), w.onDidDelete(soon));
    }
  }
  context.subscriptions.push(...subs, { dispose: () => clearTimeout(timer) });
  load();
  return { view, state };
}

// job folders under 2 Applied + the files in each (jobs.appliedFolders reads the names)
function listApplied(dir) {
  try {
    return fs.readdirSync(dir, { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => {
      let files = [];
      try { files = fs.readdirSync(path.join(dir, d.name)); } catch {}
      return { name: d.name, files };
    });
  } catch {
    return [];
  }
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

// launcher installed a newer copy of this extension than the one running => Today's quiet line
function restartNow(root) {
  try {
    return start.restartLine({ own: ownVersion, installed: fs.readFileSync(path.join(root, start.INSTALLED), "utf8") });
  } catch {
    return null;
  }
}

// this window's version (start.RUNNING) for jobs.py, and Today redrawn when the launcher records
// a newer copy (start.INSTALLED). Only a new window loads that copy => say so, never
// reload mid-chat. Job Finder's folder only; never throws
let ownVersion = null;
const todayDraws = new Set();
let todayShown = null;

function noteRunning(context) {
  ownVersion = context.extension.packageJSON.version;
  const folder = (vscode.workspace.workspaceFolders || [])[0];
  if (!folder || folder.uri.scheme !== "file") return;
  const root = folder.uri.fsPath;
  if (!start.isJobFinder((rel) => fs.existsSync(path.join(root, rel)))) return;
  try {
    const { file, text } = start.runningRecord(root, { version: ownVersion, pid: process.pid, now: Date.now() });
    fs.writeFileSync(file, text);
  } catch {}
  const installed = path.join(root, start.INSTALLED);
  // plain pattern on the .data folder itself, as watchLinks: never cut by files.watcherExclude
  const watcher = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(vscode.Uri.file(path.dirname(installed)), path.basename(installed)));
  const redraw = () => todayDraws.forEach((draw) => {
    try {
      draw();
    } catch {}
  });
  context.subscriptions.push(watcher, watcher.onDidCreate(redraw), watcher.onDidChange(redraw));
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
  return doAction(root, at, action, {
    tell: (text, how) => tell(panel, text, how),
    busy: (on, label) => panel.webview.postMessage({ type: "busy", on, label }),
    keeper,
  });
}

// VS Code's Integrated Browser (1.109+): a url string, never { reuseUrlFilter } - a matching tab
// would be re-navigated, wiping a half-filled form (app/docs/app-window.md)
const BROWSER_OPEN = "workbench.action.browser.open";

// palette "Browser: Clear Storage (Workspace)": empties this folder's sign-ins + site data, kept
// by VS Code outside the folder (app/docs/app-window.md #s); no dialog, no tab needed (#t)
const CLEAR_STORAGE = "workbench.action.browser.clearWorkspaceStorage";

async function hasBrowser() {
  return (await vscode.commands.getCommands(true)).includes(BROWSER_OPEN);
}

// posting / company link => a tab in this window, system browser when VS Code has no browser.
// A string, not a Uri: passed on exactly as written (a Uri re-encodes it; a rebuilt link 404s)
function openLink(url) {
  return today.openLink(url, {
    hasBrowser,
    inWindow: (link) => vscode.commands.executeCommand(BROWSER_OPEN, link),
    external: (link) => vscode.env.openExternal(link),
  });
}

// `jobs.py open "<link>"` (every AI shows a link with it) => a tab here; `jobs.py clear-signins` =>
// this window's sign-ins emptied; `apply-form fill --in-window` (trial) => attach / detach. Job
// Finder's folder only.
// Requests already waiting as the window starts: fresh ones opened, leftovers deleted unseen
function watchLinks(context) {
  const folder = (vscode.workspace.workspaceFolders || [])[0];
  if (!folder || folder.uri.scheme !== "file") return;
  const root = folder.uri.fsPath;
  if (!start.isJobFinder((rel) => fs.existsSync(path.join(root, rel)))) return;
  const dir = path.join(root, start.LINK_DIR);
  try {
    fs.mkdirSync(dir, { recursive: true });
  } catch {
    return;
  }
  // plain pattern on the folder itself: a non-recursive watcher, never cut by files.watcherExclude
  const watcher = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(vscode.Uri.file(dir), start.LINK_GLOB));
  const take = (uri) => takeLink(uri.fsPath).catch(() => {});
  context.subscriptions.push(watcher, watcher.onDidCreate(take), watcher.onDidChange(take),
    vscode.debug.onDidStartDebugSession((s) => debugSessions.set(s.id, s)),
    vscode.debug.onDidTerminateDebugSession((s) => debugSessions.delete(s.id)));
  let names = [];
  try {
    names = fs.readdirSync(dir);
  } catch {}
  for (const name of names) if (start.isLinkFile(name)) takeLink(path.join(dir, name)).catch(() => {});
}

// claim by rename: jobs.py deletes the same name when its wait ends => only one side opens it
async function takeLink(file) {
  if (!start.isLinkFile(path.basename(file))) return;
  // no browser in this VS Code (before 1.109) => left alone: jobs.py opens the system browser
  // after its wait and says so
  if (!(await hasBrowser().catch(() => false))) return;
  const taken = `${file}.taken`;
  for (let tries = 5; ; tries--) {
    try {
      fs.renameSync(file, taken);
      break;
    } catch (e) {
      // gone = jobs.py took it back, or another event of ours already has it
      if (!tries || !["EBUSY", "EPERM", "EACCES"].includes(e && e.code)) return;
      await new Promise((ok) => setTimeout(ok, 50));
    }
  }
  let req = null;
  try {
    req = start.windowRequest(fs.readFileSync(taken, "utf8"), Date.now());
  } catch {}
  try {
    fs.unlinkSync(taken);
  } catch {}
  if (req && req.clear) return clearSignins(file);
  if (req && req.attach) return answer(file, await attachForm(req.attach));
  if (req && req.detach) return answer(file, await detachForm(req.detach));
  const url = req && req.url;
  if (url) await openLink(url);
}

// `jobs.py clear-signins` (before removing the app): only this window can empty them; jobs.py
// waits for the answer so the AI never says cleared when it wasn't
async function clearSignins(file) {
  let result;
  try {
    await vscode.commands.executeCommand(CLEAR_STORAGE);
    result = { ok: true };
  } catch (e) {
    result = { error: String((e && e.message) || e) };
  }
  return answer(file, result);
}

// <id>.done written whole: jobs.py reads it the moment the name appears
function answer(file, result) {
  const { temp, done, text } = start.answerFor(file, result);
  try {
    fs.writeFileSync(temp, text);
    fs.renameSync(temp, done);
  } catch {}
}

// in-window fill trial (app/apply/window.py, app/docs/apply/vscode-browser.md "Trial"): js-debug's
// "attach to an Integrated Browser tab" on jobs.py's holding page, then its CDP proxy for that tab.
// Measured route 2: a tab matched by urlFilter (query kept, #hash dropped) attaches at once; none
// or two => js-debug's own picker, which startDebugging waits on - closed after ATTACH_PICKER_MS
const debugSessions = new Map();
const ATTACH_PICKER_MS = 15000;
const ATTACH_CHILD_MS = 10000;
// the parent session has no target: js-debug never answers for it (measured) => the child's
const PROXY_MS = 5000;
const DETACH_SETTLE_MS = 2000;
const FORM_SESSION = "Job Finder form";

function late(ms, value) {
  return new Promise((ok) => setTimeout(() => ok(value), ms));
}

async function attachForm(url) {
  // Restricted Mode: js-debug won't start (measured, restricted.json)
  if (!vscode.workspace.isTrusted) return { error: "untrusted" };
  const folder = (vscode.workspace.workspaceFolders || [])[0];
  const config = { type: "pwa-editor-browser", request: "attach", name: FORM_SESSION, urlFilter: url, internalConsoleOptions: "neverOpen" };
  const ours = (s) => !s.parentSession && s.configuration && s.configuration.urlFilter === url;
  try {
    const started = await Promise.race([vscode.debug.startDebugging(folder, config,
      { suppressDebugToolbar: true, suppressDebugStatusbar: true, suppressDebugView: true }), late(ATTACH_PICKER_MS, "picker")]);
    if (started === "picker") {
      await vscode.commands.executeCommand("workbench.action.closeQuickOpen");
      return { error: "picker" };
    }
    if (!started) return { error: "not started" };
  } catch (e) {
    return { error: String((e && e.message) || e) };
  }
  for (const end = Date.now() + ATTACH_CHILD_MS; Date.now() < end; await late(100)) {
    const parent = [...debugSessions.values()].find(ours);
    const child = parent && [...debugSessions.values()].find((s) => s.parentSession === parent);
    if (!child) continue;
    let proxy;
    try {
      proxy = await Promise.race([vscode.commands.executeCommand("extension.js-debug.requestCDPProxy", child.id), late(PROXY_MS)]);
    } catch (e) {
      proxy = null;
    }
    if (!proxy || !proxy.port) {
      await detachForm(child.id);
      return { error: "no proxy" };
    }
    return { ok: true, session: child.id, proxy: { host: proxy.host, port: proxy.port, path: proxy.path } };
  }
  return { error: "no tab session" };
}

// let the tab go, never close it: stop on an attach = disconnect w/ terminateDebuggee (closes the
// tab, measured), and stopDebugging() w/o a session ends every one - so disconnect each of ours
// w/ terminateDebuggee false, deepest first. Ours = the attach's whole tree: a cross-site frame in
// the form (reCAPTCHA, Turnstile) is a session under the tab's; left on, it kept the attach itself
// alive after the tab's let go - 3 of 3 on the local form (plan-k8n.34). Frames still loading get
// a session after the first pass => look again
const DETACH_PASSES = 3;

function under(s, rootId) {
  for (let p = s; p; p = p.parentSession) if (p.id === rootId) return true;
  return false;
}

function depth(s) {
  let n = 0;
  for (let p = s.parentSession; p; p = p.parentSession) n++;
  return n;
}

async function detachForm(id) {
  const child = debugSessions.get(id);
  if (!child) return { ok: true, left: 0 };
  const rootId = (child.parentSession || child).id;
  const ours = () => [...debugSessions.values(), child, child.parentSession]
    .filter((s, i, all) => s && under(s, rootId) && all.findIndex((t) => t && t.id === s.id) === i && debugSessions.has(s.id));
  for (let pass = 0; pass < DETACH_PASSES && ours().length; pass++) {
    for (const s of ours().sort((a, b) => depth(b) - depth(a))) {
      try {
        await Promise.race([s.customRequest("disconnect", { terminateDebuggee: false }), late(PROXY_MS)]);
      } catch {}
    }
    await late(DETACH_SETTLE_MS);
  }
  return { ok: true, left: ours().length };
}

// one action of today.model's list, from the dashboard or the Jobs panel: the only place a click
// opens a link or file, records a status or puts words in the chat. ui = { tell(text, how),
// busy(on, label), keeper (today.statusKeeper) } of the surface clicked
async function doAction(root, at, action, ui) {
  if (action.type === "posting") {
    const url = today.cleanUrl(action.url);
    if (url) await openLink(url);
    return;
  }
  if (action.type === "company") {
    const url = today.cleanSite(action.url);
    if (url) await openLink(url);
    return;
  }
  if (action.type === "open") {
    const rel = today.cleanPath(action.path);
    if (!rel) return;
    const file = at(rel);
    let real;
    try { real = fs.realpathSync(file); } catch { return ui.tell("That file has moved - the page updates at the next check."); }
    if (!real.startsWith(fs.realpathSync(root) + path.sep)) return;
    const uri = vscode.Uri.file(file);
    if (action.how === "folder") return vscode.commands.executeCommand("revealInExplorer", uri);
    if (action.how === "page") return vscode.commands.executeCommand("vscode.openWith", uri, start.PREVIEW_EDITOR);
    return vscode.commands.executeCommand("vscode.open", uri, { preview: false });
  }
  if (action.type === "status") return ui.keeper.set(action.num, action.id, action.words);
  if (action.type === "say") {
    if (!today.templateFor(action.words, today.templates(say))) return;
    return sayOnce(root, action.words, ui);
  }
}

// one at a time: a 2nd click would open a 2nd new chat => said, never silently dropped.
// lines = the page's own ready words (today.say)
async function sayOnce(root, words, ui, lines = null, mode = null) {
  if (saying) {
    ui.busy(false);
    return ui.tell(today.STILL_OPENING);
  }
  saying = true;
  try {
    return await sayWords(root, words, ui.tell, ui.busy, lines, mode);
  } finally {
    saying = false;
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
async function sayWords(root, words, status, busy = () => {}, lines = null, how = null) {
  const ai = currentAi(root);
  const mode = await today.say({
    ai, mode: how || sayModeNow(root), words, platform: process.platform, status, busy, warm: chatWarm(ai), lines,
    exec: (command, ...args) => vscode.commands.executeCommand(command, ...args),
    copy: (text) => vscode.env.clipboard.writeText(text),
  });
  if (mode === "new") vscode.window.setStatusBarMessage(lines ? lines(mode).text : today.readyLine(mode, today.jobOf(words)), today.CLEAR_MS);
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
  // Jobs panel as the window shows it at settle: VS Code's own visible flag + what it lists
  report.jobsView = jobsTree ? { visible: jobsTree.view.visible, groups: jobsTree.state.groups
    .map((g) => ({ label: g.label, items: g.items.map((i) => i.label) })) } : null;
  report.theme = { kind: vscode.window.activeColorTheme.kind, name: vscode.workspace.getConfiguration("workbench").get("colorTheme") };
  report.folders = (vscode.workspace.workspaceFolders || []).map((f) => f.uri.toString());
  report.trusted = vscode.workspace.isTrusted;
  report.untrustedLine = untrustedShown;
  report.claudeActive.atEnd = Boolean(watched && watched.isActive);
  report.active = vscode.extensions.all.filter((e) => e.isActive && !e.packageJSON.isBuiltin && !e.id.startsWith("vscode."))
    .map((e) => e.id).sort();
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
  const hold = process.env[PROBE_HOLD_ENV];
  if (hold && folder) report.hold = await holdFor(hold, folder.uri.fsPath);
  fs.writeFileSync(out, redact(JSON.stringify(report, null, 1)) + "\n");
  await vscode.commands.executeCommand("workbench.action.quit");
}

// probe only: serves the driver's requests (PROBE_HOLD_ENV) until {do: "quit"} or 10 min
async function holdFor(dir, root) {
  const log = [];
  const at = (rel) => path.join(root, rel);
  const ui = { tell() {}, busy() {} };
  for (const end = Date.now() + 600000; Date.now() < end; await new Promise((ok) => setTimeout(ok, 100))) {
    let names = [];
    try {
      names = fs.readdirSync(dir).filter((name) => name.endsWith(".req")).sort();
    } catch {}
    for (const name of names) {
      const reqFile = path.join(dir, name);
      const begun = Date.now();
      let req = null;
      let res;
      try {
        req = JSON.parse(fs.readFileSync(reqFile, "utf8"));
        fs.unlinkSync(reqFile);
        // company link = http(s) as stored (cleanSite) => a local http test page takes this path
        if (req.do === "today-link") await Promise.all(req.urls.map((url) => doAction(root, at, { type: "company", url }, ui)));
        else if (req.do === "command") await vscode.commands.executeCommand(req.id, ...(req.args || []));
        res = { req, ms: Date.now() - begun, tabs: readWindow() };
        // last Today drawn: its restart line (null = none) + this window's version
        if (req.do === "today") Object.assign(res, { today: todayShown, own: ownVersion });
      } catch (err) {
        res = { req, ms: Date.now() - begun, error: String(err), tabs: readWindow() };
      }
      log.push(res);
      fs.writeFileSync(path.join(dir, name.replace(/\.req$/, ".res")), JSON.stringify(res));
      if (req && req.do === "quit") return log;
    }
  }
  log.push({ capped: true });
  return log;
}

module.exports = { activate, deactivate };
