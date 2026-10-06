// Scratch-only measuring extension (plan-29g.7), never shipped: serves the driver's requests from
// JF_PROBE_HOLD (<n>.req -> <n>.res), opens window tabs, starts js-debug's "Integrated Browser:
// Attach" on one and asks js-debug for its CDP proxy (extension.js-debug.requestCDPProxy).
const vscode = require("vscode");
const fs = require("fs");
const path = require("path");

const sessions = new Map();
const events = [];

function info(s) {
  return { id: s.id, type: s.type, name: s.name, parent: s.parentSession ? s.parentSession.id : null };
}

function readTabs() {
  return vscode.window.tabGroups.all.map((g) => ({
    viewColumn: g.viewColumn,
    active: g.isActive,
    tabs: g.tabs.map((t) => ({ label: t.label, active: t.isActive, input: t.input ? t.input.constructor.name : null })),
  }));
}

// the parent session of an attach has no target: js-debug never answers it (measured) - give up after 5 s
async function proxyFor(id, ms = 5000) {
  try {
    const late = new Promise((ok) => setTimeout(() => ok({ error: `no answer in ${ms} ms` }), ms));
    return await Promise.race([vscode.commands.executeCommand("extension.js-debug.requestCDPProxy", id), late]);
  } catch (err) {
    return { error: String(err) };
  }
}

async function handle(req, folder) {
  if (req.do === "open") {
    await vscode.commands.executeCommand("workbench.action.browser.open", req.url);
    return {};
  }
  if (req.do === "attach") {
    const before = new Set(sessions.keys());
    const config = { type: "pwa-editor-browser", request: "attach", name: req.name || "Job Finder form", urlFilter: req.urlFilter, ...(req.extra || {}) };
    let ok;
    let error;
    // no tab (or two) matching urlFilter -> js-debug shows "Select a browser tab to debug" and
    // startDebugging waits on it (measured): close the picker after startMs
    try {
      const late = new Promise((ok) => setTimeout(() => ok("picker"), req.startMs || 15000));
      ok = await Promise.race([vscode.debug.startDebugging(folder, config, req.options || {}), late]);
      if (ok === "picker") await vscode.commands.executeCommand("workbench.action.closeQuickOpen");
    } catch (err) {
      error = String(err);
    }
    const end = Date.now() + (req.waitMs || 8000);
    while (Date.now() < end && ![...sessions.keys()].some((id) => !before.has(id))) await new Promise((r) => setTimeout(r, 100));
    await new Promise((r) => setTimeout(r, req.settleMs || 1500));
    const started = [...sessions.values()].filter((s) => !before.has(s.id));
    const proxies = {};
    await Promise.all(started.map(async (s) => (proxies[s.id] = (await proxyFor(s.id)) || { error: "undefined" })));
    return { ok, error, sessions: started.map(info), proxies };
  }
  if (req.do === "proxy") return { proxy: await proxyFor(req.id) };
  if (req.do === "sessions") return { sessions: [...sessions.values()].map(info) };
  if (req.do === "stop") {
    await vscode.debug.stopDebugging(req.id ? sessions.get(req.id) : undefined);
    return {};
  }
  // as the shipped extension's detachForm (plan-k8n.12): disconnect w/o ending the tab, child first
  if (req.do === "detach") {
    const child = sessions.get(req.id);
    for (const s of [child, child && child.parentSession].filter(Boolean)) {
      try {
        await Promise.race([s.customRequest("disconnect", { terminateDebuggee: false }), new Promise((ok) => setTimeout(ok, 5000))]);
      } catch {}
    }
    await new Promise((ok) => setTimeout(ok, 2000));
    return { sessions: [...sessions.values()].map(info) };
  }
  if (req.do === "command") return { value: await vscode.commands.executeCommand(req.id, ...(req.args || [])) };
  if (req.do === "trust") return { trusted: vscode.workspace.isTrusted };
  return {};
}

async function hold(dir, folder) {
  for (const end = Date.now() + 1800000; Date.now() < end; await new Promise((ok) => setTimeout(ok, 100))) {
    let names = [];
    try {
      names = fs.readdirSync(dir).filter((name) => name.endsWith(".req")).sort();
    } catch {}
    for (const name of names) {
      const file = path.join(dir, name);
      const begun = Date.now();
      let req = null;
      let res;
      try {
        req = JSON.parse(fs.readFileSync(file, "utf8"));
        fs.unlinkSync(file);
        res = { req, ...(await handle(req, folder)) };
      } catch (err) {
        res = { req, error: String(err) };
      }
      res.ms = Date.now() - begun;
      res.tabs = readTabs();
      res.events = events.splice(0);
      fs.writeFileSync(path.join(dir, name.replace(/\.req$/, ".tmp")), JSON.stringify(res));
      fs.renameSync(path.join(dir, name.replace(/\.req$/, ".tmp")), path.join(dir, name.replace(/\.req$/, ".res")));
      if (req && req.do === "quit") return vscode.commands.executeCommand("workbench.action.quit");
    }
  }
}

function activate(context) {
  const dir = process.env.JF_PROBE_HOLD;
  if (!dir) return;
  context.subscriptions.push(
    vscode.debug.onDidStartDebugSession((s) => {
      sessions.set(s.id, s);
      events.push({ t: Date.now(), started: info(s) });
    }),
    vscode.debug.onDidTerminateDebugSession((s) => {
      sessions.delete(s.id);
      events.push({ t: Date.now(), ended: info(s) });
    }),
  );
  const folder = (vscode.workspace.workspaceFolders || [])[0];
  fs.writeFileSync(path.join(dir, "up.json"), JSON.stringify({ t: Date.now(), trusted: vscode.workspace.isTrusted, folder: folder && folder.uri.fsPath }));
  hold(dir, folder);
}

module.exports = { activate, deactivate() {} };
