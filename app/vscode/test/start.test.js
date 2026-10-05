// node --test app/vscode/test/*.test.js (pytest runs it too: app/tests/test_vscode_ext.py)
const test = require("node:test");
const assert = require("node:assert");
const start = require("../start");

const HOUR = 60 * 60 * 1000;
const NOW = Date.parse("2026-10-03T12:00:00Z");

// any folder opened in Job Finder's profile would get a Today tab it never asked for
test("only Job Finder's own folder gets a start page", () => {
  assert.equal(start.isJobFinder((rel) => [".data", "My Resume"].includes(rel)), true);
  assert.equal(start.isJobFinder((rel) => rel === ".data"), false);
  assert.equal(start.isJobFinder(() => false), false);
});

// wrong path or name => the loading splash never sees the signal and stays up to its cap
test("ready signal lands in the folder's .data, named as the launcher names it", () => {
  const path = require("path");
  const { file, text } = start.readyFile(path.join("/Users", "Your Name", "jobs"), NOW);
  assert.equal(file, path.join("/Users", "Your Name", "jobs", ".data", "window-ready"));
  assert.equal(text, "2026-10-03T12:00:00.000Z\n");
  assert.equal(start.READY, path.join(".data", "window-ready"));
});

// launcher picked + rebuilt the page => the window shows that one, not a guess
test("launcher's marker names the page", () => {
  assert.equal(start.choosePage({ marker: "Today.md\n", settingsExist: true, todayExists: true }), "Today.md");
  assert.equal(start.choosePage({ marker: "START HERE.md\n", settingsExist: false, todayExists: false }), "START HERE.md");
});

// a marker naming anything else (a path out of the folder) never opens it
test("marker naming another file is ignored", () => {
  for (const marker of ["../secret.md", "My Resume/Resume details.yml", "", "   "]) {
    assert.equal(start.choosePage({ marker, settingsExist: true, todayExists: true }), "Today.md");
  }
});

// opened from the Dock: returning users must not land on "type set me up"
test("no marker: Today once set up, START HERE before", () => {
  assert.equal(start.choosePage({ marker: null, settingsExist: true, todayExists: true }), "Today.md");
  assert.equal(start.choosePage({ marker: null, settingsExist: false, todayExists: true }), "START HERE.md");
  assert.equal(start.choosePage({ marker: null, settingsExist: true, todayExists: false }), "START HERE.md");
});

// launcher + extension both rebuilding => one waits a minute on today.lock, then fails
test("launcher just rebuilt Today => no second rebuild", () => {
  assert.equal(start.needsRefresh({ marker: "Today.md", settingsExist: true, todayMtime: NOW - 5 * HOUR, stampMtime: null, now: NOW }), false);
});

// before setup there is no search to build a Today page from
test("no rebuild before setup", () => {
  assert.equal(start.needsRefresh({ marker: null, settingsExist: false, todayMtime: null, stampMtime: null, now: NOW }), false);
});

// opened from the Dock days later => yesterday's news on the page
test("no marker: stale or missing Today is rebuilt, a fresh one is not", () => {
  const base = { marker: null, settingsExist: true, stampMtime: NOW - 3 * HOUR, now: NOW };
  assert.equal(start.needsRefresh({ ...base, todayMtime: null }), true);
  assert.equal(start.needsRefresh({ ...base, todayMtime: NOW - 2 * HOUR }), true);
  assert.equal(start.needsRefresh({ ...base, todayMtime: NOW - 10 * 60 * 1000 }), false);
  // older than the last launch: that launch's rebuild failed
  assert.equal(start.needsRefresh({ ...base, stampMtime: NOW - 60 * 1000, todayMtime: NOW - 5 * 60 * 1000 }), true);
});

// Dock + Desktop icon start with a short PATH: uv in ~/.local/bin would never be found
test("uv looked for where its installer puts it, then PATH", () => {
  const mac = start.uvCandidates({ platform: "darwin", home: "/Users/you", envPath: "/usr/bin:/usr/local/bin" });
  assert.deepEqual(mac, ["/Users/you/.local/bin/uv", "/opt/homebrew/bin/uv", "/usr/local/bin/uv", "/usr/bin/uv"]);
  const win = start.uvCandidates({ platform: "win32", home: "C:\\Users\\you", userProfile: "C:\\Users\\you", envPath: "C:\\Tools;C:\\Windows" });
  assert.deepEqual(win, ["C:\\Users\\you\\.local\\bin\\uv.exe", "C:\\Tools\\uv.exe", "C:\\Windows\\uv.exe"]);
});

// restored tabs: opening again made a second Today tab beside the one that came back
test("formatted page tab from last time is found, never a second", () => {
  const page = "/home/you/jobs/Today.md";
  const tabs = [
    { kind: "text", fsPath: "/home/you/jobs/Notes.md", label: "Notes.md" },
    { kind: "custom", fsPath: page, viewType: "vscode.markdown.preview.editor", label: "Today.md" },
  ];
  assert.equal(start.pageTabs(tabs, page, "darwin").formatted, tabs[1]);
  const webview = [{ kind: "webview", label: "Preview Today.md" }];
  assert.equal(start.pageTabs(webview, page, "darwin").formatted, webview[0]);
  assert.equal(start.pageTabs([{ kind: "custom", fsPath: "/elsewhere/Today.md", label: "Today.md" }], page, "darwin").formatted, null);
});

// a plain-text Today from an older launch came back as text on every start
test("plain-text tabs of the page are picked out to close", () => {
  const page = "C:\\Users\\you\\jobs\\Today.md";
  const tabs = [
    { kind: "text", fsPath: "c:\\users\\you\\jobs\\Today.md", label: "Today.md" },
    { kind: "text", fsPath: "C:\\Users\\you\\jobs\\Notes.md", label: "Notes.md" },
  ];
  const seen = start.pageTabs(tabs, page, "win32");
  assert.deepEqual(seen.text, [tabs[0]]);
  assert.equal(seen.formatted, null);
});

// first Today button waited seconds for Claude to start (owner 2026-10-03) => started w/ the page
test("warm-up: the user's chat extension, nothing for Copilot or an unknown AI", () => {
  assert.equal(start.warmUpPlan("claude").id, "anthropic.claude-code");
  assert.equal(start.warmUpPlan("chatgpt").id, "openai.chatgpt");
  for (const ai of ["copilot", null, "nova"]) assert.equal(start.warmUpPlan(ai), null);
});

// Today's status click runs jobs.py in the Job Finder folder; a failed run must reach the page as a failure
test("runJobs: uv run app/jobs.py + args in the folder; rejects on a failed run", async () => {
  const calls = [];
  const exec = (fail) => (file, args, opts, cb) => { calls.push([file, args, opts.cwd]); cb(fail ? new Error("exit 1") : null, "ok\n"); };
  assert.equal(await start.runJobs({ execFile: exec(false), uv: "/bin/uv", root: "/jf", args: ["status", "set", "12", "applied"] }), "ok\n");
  assert.deepEqual(calls[0], ["/bin/uv", ["run", "app/jobs.py", "status", "set", "12", "applied"], "/jf"]);
  await assert.rejects(start.runJobs({ execFile: exec(true), uv: "/bin/uv", root: "/jf", args: ["status"] }));
});

// opened w/o the Desktop icon: a VS Code word ("Restricted Mode", "workspace") the user can't act on
test("untrusted window line: plain words, says the Desktop icon, one button", () => {
  for (const word of ["restricted", "workspace", "trust", "extension", "vs code"]) {
    assert.ok(!start.UNTRUSTED_LINE.toLowerCase().includes(word), word);
    assert.ok(!start.UNTRUSTED_BUTTON.toLowerCase().includes(word), word);
  }
  assert.match(start.UNTRUSTED_LINE, /Desktop icon/);
  assert.strictEqual(start.UNTRUSTED_COMMAND, "workbench.trust.manage");
});

// jobs.py open "<link>" => a tab in the window (app/jobs.py send_to_window): only its own request
// files, only http(s), never a leftover from a run that already opened the browser
test("open-link request: http(s) link from a fresh request file only", () => {
  const path = require("path");
  assert.equal(start.LINK_DIR, path.join(".data", "open-link"));
  const link = (text, now) => (start.windowRequest(text, now) || {}).url || null;
  const req = (over) => JSON.stringify({ url: "https://boards.greenhouse.io/acme/jobs/123?gh_src=a%20b", t: NOW, ...over });
  assert.deepEqual(start.windowRequest(req(), NOW), { url: "https://boards.greenhouse.io/acme/jobs/123?gh_src=a%20b" });
  assert.equal(link(req({ url: "http://example.com/about" }), NOW + 9000), "http://example.com/about");
  assert.equal(start.windowRequest(req(), NOW + start.LINK_MAX_AGE_MS + 1), null);
  for (const url of ["javascript:alert(1)", "vscode://anthropic.claude-code/open", "file:///etc/passwd", "mailto:a@b.example",
    "not a link", "", 42, null]) {
    assert.equal(start.windowRequest(req({ url }), NOW), null, String(url));
  }
  for (const text of ["{half", "null", "[]", "\"https://example.com\"", JSON.stringify({ url: "https://example.com" }),
    JSON.stringify({ url: "https://example.com", t: "now" }), req({ do: "open" })]) {
    assert.equal(start.windowRequest(text, NOW), null, text);
  }
  assert.equal(start.isLinkFile("0123456789abcdef0123456789abcdef.json"), true);
  for (const name of ["0123456789abcdef0123456789abcdef.tmp", "0123456789abcdef0123456789abcdef.json.taken", "x.json",
    "0123456789abcdef0123456789abcdef.done", "../0123456789abcdef0123456789abcdef.json", null]) {
    assert.equal(start.isLinkFile(name), false, String(name));
  }
});

// jobs.py clear-signins (before removing the app): same folder, fresh requests only, answered in
// <id>.done written whole (jobs.py reads it the moment the name appears)
test("clear-signins request: fresh only, answered beside it", () => {
  const clear = (over) => JSON.stringify({ do: start.CLEAR_REQUEST, t: NOW, ...over });
  assert.equal(start.CLEAR_REQUEST, "clear-signins");
  assert.deepEqual(start.windowRequest(clear(), NOW), { clear: true });
  assert.deepEqual(start.windowRequest(clear({ url: "https://example.com" }), NOW), { clear: true });
  assert.equal(start.windowRequest(clear(), NOW + start.LINK_MAX_AGE_MS + 1), null);
  assert.equal(start.windowRequest(clear({ t: "now" }), NOW), null);
  const file = "/f/.data/open-link/0123456789abcdef0123456789abcdef.json";
  assert.deepEqual(start.answerFor(file, { ok: true }), {
    temp: "/f/.data/open-link/0123456789abcdef0123456789abcdef.done.tmp",
    done: "/f/.data/open-link/0123456789abcdef0123456789abcdef.done",
    text: "{\"ok\":true}",
  });
});

// in-window fill trial (app/apply/window.py): attach only to jobs.py's own loopback holding page -
// a request naming any site's tab is dropped; detach only by a session id's shape
test("in_window attach-form: only jobs.py's holding page, detach-form: only a session id", () => {
  const ask = (over) => JSON.stringify({ t: NOW, ...over });
  const page = "http://127.0.0.1:52817/jf-0123456789abcdef0123456789abcdef";
  assert.equal(start.ATTACH_REQUEST, "attach-form");
  assert.equal(start.DETACH_REQUEST, "detach-form");
  assert.deepEqual(start.windowRequest(ask({ do: "attach-form", url: page }), NOW), { attach: page });
  for (const url of ["https://job-boards.greenhouse.io/acme/jobs/123", "http://localhost:52817/jf-0123456789abcdef0123456789abcdef",
    "http://127.0.0.1:52817/jf-0123456789abcdef0123456789abcdef/x", "http://127.0.0.1:52817/jf-0123", `${page}?a=1`,
    "http://127.0.0.1.evil.com:52817/jf-0123456789abcdef0123456789abcdef", undefined, 5]) {
    assert.equal(start.windowRequest(ask({ do: "attach-form", url }), NOW), null, String(url));
  }
  assert.equal(start.windowRequest(ask({ do: "attach-form", url: page, t: NOW - start.LINK_MAX_AGE_MS - 1 }), NOW), null);
  assert.deepEqual(start.windowRequest(ask({ do: "detach-form", session: "a1b2-c3_d4" }), NOW), { detach: "a1b2-c3_d4" });
  for (const session of ["", "a b", "../x", "x".repeat(65), undefined, 7]) {
    assert.equal(start.windowRequest(ask({ do: "detach-form", session }), NOW), null, String(session));
  }
});

// update installed a newer copy while the window ran => one quiet line; same or older => none
test("restart line only when a newer copy is installed than the one running", () => {
  assert.equal(start.restartLine({ own: "0.25.0", installed: "0.25.1\n" }), start.RESTART_LINE);
  assert.equal(start.restartLine({ own: "0.24.0", installed: "0.25.0" }), start.RESTART_LINE);
  assert.equal(start.restartLine({ own: "0.9.0", installed: "0.10.0" }), start.RESTART_LINE);
  assert.equal(start.restartLine({ own: "0.25.0", installed: "0.25.0\n" }), null);
  assert.equal(start.restartLine({ own: "0.25.1", installed: "0.25.0" }), null);
  assert.equal(start.restartLine({ own: "0.25.0", installed: "" }), null);
  assert.equal(start.restartLine({ own: null, installed: "0.25.0" }), null);
  assert.match(start.RESTART_LINE, /close its window/);
  assert.deepEqual(start.versionParts("1.2.3"), [1, 2, 3]);
  assert.equal(start.versionParts("1.x"), null);
});

// jobs.py reads it (app/launch.py window_behind): version + extension host pid, in the folder's .data
test("running record names this window's version + extension host", () => {
  const path = require("path");
  const { file, text } = start.runningRecord(path.join("/Users", "Your Name", "jobs"), { version: "0.25.0", pid: 4242, now: NOW });
  assert.equal(file, path.join("/Users", "Your Name", "jobs", ".data", "window-running.json"));
  assert.deepEqual(JSON.parse(text), { version: "0.25.0", pid: 4242, at: "2026-10-03T12:00:00.000Z" });
  assert.equal(start.INSTALLED, path.join(".data", "window-installed"));
});
