// Start page: which page opens as the window starts, whether Today is rebuilt first, where uv is.
// Pure (no vscode, no disk): extension.js passes what it read. Tests: node --test app/vscode/test/*.test.js
const path = require("path");

const TODAY = "Today.md";
const START_HERE = "START HERE.md";
// launcher writes both (app/launch.py mark_start_page); marker = page name, deleted once opened
const MARKER = path.join(".data", "start-page");
const STAMP = path.join(".data", "launched");
const SETTINGS = path.join("My Settings", "Search settings.yml");
// which AI the user picked (app/ai.py): claude | chatgpt | copilot
const AI_FILE = path.join(".data", "ai");
// launcher: VS Code was open, so Job Finder's own profile waits for one cold start (app/launch.py)
const PROFILE_PENDING = path.join(".data", "profile-pending");
const PROFILE_PENDING_LINE = {
  darwin: "One more step: quit VS Code (Code > Quit, or Cmd+Q), then open CEZ Job Finder again.",
  other: "One more step: close every VS Code window (File > Exit), then open CEZ Job Finder again.",
};
// folder not trusted (opened w/o the Desktop icon before the launcher marked it trusted) =>
// Restricted Mode: AI panel + PDF viewer don't run. One line + one button, no VS Code words
const UNTRUSTED_LINE = "The AI panel can't run in this window yet. Close it and open CEZ Job Finder from its Desktop icon - after that it runs however you open it.";
const UNTRUSTED_BUTTON = "Allow it here";
// VS Code's own page for it (Trust button); never a setting change
const UNTRUSTED_COMMAND = "workbench.trust.manage";
// Today older than this, window opened w/o the launcher (Dock, recent folders) => rebuilt
const STALE_MS = 60 * 60 * 1000;
const PREVIEW_EDITOR = "vscode.markdown.preview.editor";

// Job Finder's own folder: private folders the launcher makes; any other folder in this profile
// is left alone
function isJobFinder(exists) {
  return exists(".data") && exists("My Resume");
}

// marker = launcher's pick, already rebuilt; only our two pages, whatever else the file says
function choosePage({ marker, settingsExist, todayExists }) {
  const named = (marker || "").trim();
  if (named === TODAY || named === START_HERE) return named;
  return settingsExist && todayExists ? TODAY : START_HERE;
}

// launcher rebuilt it moments ago (marker) => never a second rebuild fighting over today.lock
function needsRefresh({ marker, settingsExist, todayMtime, stampMtime, now }) {
  if (marker || !settingsExist) return false;
  if (todayMtime == null) return true;
  if (stampMtime != null && todayMtime < stampMtime) return true;
  return now - todayMtime > STALE_MS;
}

// Desktop icon + Dock carry a short PATH => uv's install spots first, PATH last
function uvCandidates({ platform, home, userProfile, envPath }) {
  const win = platform === "win32";
  const join = win ? path.win32.join : path.posix.join;
  const exe = win ? "uv.exe" : "uv";
  const spots = win
    ? [userProfile || home].filter(Boolean).map((h) => join(h, ".local", "bin"))
    : [join(home, ".local", "bin"), "/opt/homebrew/bin", "/usr/local/bin"];
  const onPath = (envPath || "").split(win ? ";" : ":").filter(Boolean);
  return [...new Set([...spots, ...onPath].map((dir) => join(dir, exe)))];
}

// `uv run app/jobs.py ...args` in the Job Finder folder => Promise of its output; rejects on a
// non-zero exit or timeout. execFile = child_process.execFile (passed in: this file stays pure)
function runJobs({ execFile, uv, root, args, timeout = 60000, env = undefined }) {
  return new Promise((ok, no) => {
    execFile(uv, ["run", "app/jobs.py", ...args], { cwd: root, windowsHide: true, timeout, env },
      (err, stdout) => (err ? no(err) : ok(String(stdout || ""))));
  });
}

function samePath(a, b, platform) {
  const norm = (p) => (platform === "win32" ? path.win32.normalize(p).toLowerCase() : path.posix.normalize(p));
  return norm(a) === norm(b);
}

// tabs: [{kind: text|custom|webview, fsPath?, viewType?, label}] => the page's formatted tab, if
// one came back from last time (reveal it, never a second), and its plain-text tabs (closed)
function pageTabs(tabs, pagePath, platform) {
  const name = (platform === "win32" ? path.win32 : path.posix).basename(pagePath);
  const mine = (t) => t.fsPath && samePath(t.fsPath, pagePath, platform);
  const formatted = tabs.find((t) => (t.kind === "custom" && mine(t))
    || (t.kind === "webview" && t.label === `Preview ${name}`)) || null;
  return { formatted, text: tabs.filter((t) => t.kind === "text" && mine(t)) };
}

// chat extension started in the background once the page shows => first Today button doesn't wait
// for it (owner 2026-10-03). view = its chat view's open command, run only if activation alone
// leaves the view unloaded (app-window.md k). Copilot's chat is built in: nothing to start.
const WARM = {
  claude: { id: "anthropic.claude-code", view: true },
  chatgpt: { id: "openai.chatgpt", view: false },
};

function warmUpPlan(ai) {
  return WARM[ai] || null;
}

module.exports = {
  PROFILE_PENDING, PROFILE_PENDING_LINE, UNTRUSTED_LINE, UNTRUSTED_BUTTON, UNTRUSTED_COMMAND,
  TODAY, START_HERE, MARKER, STAMP, SETTINGS, AI_FILE, STALE_MS, PREVIEW_EDITOR, WARM,
  isJobFinder, choosePage, needsRefresh, uvCandidates, runJobs, pageTabs, warmUpPlan,
};
