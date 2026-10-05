// node --test app/vscode/test/*.test.js (pytest runs it too: app/tests/test_vscode_ext.py)
const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");
const today = require("../today");
const jobs = require("../jobs");
const say = require("../say.json");

const card = (num, title, company, sayWords, extra = {}) => ({
  num, title, company, detail: "Ready to send", url: `https://jobs.example.com/${num}`,
  resume: null, folder: null, say: sayWords, ...extra,
});
const RAW = {
  version: 1, date: "Sunday, October 4", progress: "", tiles: [],
  sections: [
    { id: "waiting", title: "Waiting on you", cards: [
      card(1, "Financial Analyst", "Example Co", ["apply to job 1", "I sent job 1"], { folder: "My Jobs/1 To apply/1 - Example Co - Financial Analyst" }),
      card(2, "FP&A Manager", "Example Co", ["apply to job 2", "I sent job 2"]),
    ] },
    { id: "follow_up", title: "Follow up", cards: [card(3, "Budget Analyst", "Placeholder Inc", ["write a follow-up for job 3", "job 3 is closed"])] },
    { id: "best", title: "Best to apply next", cards: [4, 5, 6, 7, 8, 9, 10].map((n) => card(n, `Role ${n}`, "Sample Corp", [`resume for job ${n}`])) },
  ],
  todo: [], empty: null, examples: [], guides: [],
};
const APPLIED = [
  { name: "3 - Placeholder Inc - Budget Analyst", files: ["Your_Name_Resume.pdf"] },
  { name: "11 - Demo - Partners - Tax Associate", files: ["Your_Name_Resume.pdf", "Job posting.md"] },
  { name: "notes", files: [] },
];
const build = (raw = RAW, applied = APPLIED) => {
  const m = today.model(JSON.parse(JSON.stringify(raw)), say);
  return { m, groups: jobs.tree(m, applied) };
};

// groups out of order or renamed => the panel tells a different story from the Today page
test("groups follow the dashboard: Next up, Waiting on you, Follow up, Best to apply next, Applied", () => {
  const { groups } = build();
  assert.deepStrictEqual(groups.map((g) => g.label), ["Next up", "Waiting on you", "Follow up", "Best to apply next", "Applied"]);
  assert.deepStrictEqual(groups[0].items.map((i) => i.num), [1]);  // Next up taken out of Waiting, shown once
  assert.deepStrictEqual(groups[1].items.map((i) => i.num), [2]);
});

// a job labelled differently in the panel than in chat or on Today => user can't tell they're the same
test("each job reads 'Job N - Title, Company', its number as stored", () => {
  const { groups } = build();
  assert.strictEqual(groups[0].items[0].label, "Job 1 - Financial Analyst, Example Co");
  assert.strictEqual(jobs.jobLabel(7, "", ""), "Job 7");
  assert.match(groups[0].items[0].accessible, /^Job 1 - Financial Analyst, Example Co, Ready to send$/);
});

// a long list of new jobs squeezes the file list; the rest are one chat away, as on the page
test("Best to apply next shows the top 5 only", () => {
  const { groups } = build();
  assert.deepStrictEqual(groups.find((g) => g.id === "best").items.map((i) => i.num), [4, 5, 6, 7, 8]);
});

// a row doing something the dashboard doesn't => two behaviors for one button, one untested
test("every row runs an action from today.model's own list, same index", () => {
  const { m, groups } = build();
  const rows = groups.flatMap((g) => g.items.flatMap((i) => i.rows));
  assert.ok(rows.length > 10);
  for (const r of rows) assert.ok(m.actions[r.action], `row ${r.label} has no action`);
  const next = groups[0].items[0];
  assert.deepStrictEqual(next.rows.map((r) => r.label), ["Help me apply", "I sent it", "Open the job posting", "Show its folder"]);
  assert.deepStrictEqual(next.rows.map((r) => m.actions[r.action].type), ["say", "status", "posting", "open"]);
  // same action object the page's button holds
  assert.strictEqual(next.rows[1].action, m.next.card.say[1].action);
});

// a job shown twice in the panel reads like two jobs; a folder that isn't a job => a broken row
test("Applied lists job folders not already shown above, newest first, with resume + folder", () => {
  const { m, groups } = build();
  const applied = groups.find((g) => g.id === "applied");
  assert.deepStrictEqual(applied.items.map((i) => i.label), ["Job 11 - Tax Associate, Demo - Partners"]);
  const acts = applied.items[0].rows.map((r) => m.actions[r.action]);
  assert.deepStrictEqual(acts, [
    { type: "open", path: "My Jobs/2 Applied/11 - Demo - Partners - Tax Associate/Your_Name_Resume.pdf", how: "file" },
    { type: "open", path: "My Jobs/2 Applied/11 - Demo - Partners - Tax Associate", how: "folder" },
  ]);
});

// a folder name reaching outside My Jobs => a row that opens a file it shouldn't
test("Applied folder names that leave the folder are dropped by cleanPath", () => {
  const { groups } = build(RAW, [{ name: "12 - A - B\\..\\..", files: [] }]);
  const applied = groups.find((g) => g.id === "applied");
  assert.ok(!applied || applied.items.every((i) => i.rows.length === 0));
});

// an empty panel looks broken: say why + offer the page's own next step
test("nothing to show: the page's empty line + its button, or a plain not-ready line", () => {
  const raw = { ...RAW, sections: [], empty: { text: "Nothing new since the last check.", say: "find new jobs" } };
  const { m, groups } = build(raw, []);
  assert.deepStrictEqual(groups, []);
  const row = jobs.emptyRow(m);
  assert.strictEqual(row.label, "Find new jobs");
  assert.strictEqual(m.actions[row.action].words, "find new jobs");
  assert.match(jobs.emptyRow(null).label, /isn't ready yet/);
});

// a setup step as Next up (no resume yet) must still show + work from the panel
test("Next up without a job: the setup step's own button", () => {
  const raw = { ...RAW, sections: [], todo: [{ text: "Add your resume to rank jobs by it.", say: "import my resume" }] };
  const { m, groups } = build(raw, []);
  assert.strictEqual(groups[0].label, "Next up");
  assert.strictEqual(groups[0].items[0].label, "Add my resume");
  assert.strictEqual(m.actions[groups[0].items[0].action].words, "import my resume");
});

// a second click path in extension.js => panel + page drift apart (owner: no new behaviors)
test("extension runs panel rows and page buttons through the one doAction", () => {
  const src = fs.readFileSync(path.join(__dirname, "..", "extension.js"), "utf8");
  const body = (name) => src.split(`function ${name}(`)[1].split("\n}\n")[0];
  assert.match(body("act"), /return doAction\(root, at, action, \{/);
  assert.match(body("showJobs"), /doAction\(root, at, action, ui\)/);
  // links, files, status + chat words happen only inside doAction; links through openLink alone,
  // from doAction + takeLink (`jobs.py open "<link>"`, a request start.linkRequest checked)
  assert.match(body("takeLink"), /url = start\.linkRequest\([^\n]*\n[\s\S]*if \(url\) await openLink\(url\);$/);
  const outside = src.replace(body("doAction"), "").replace(body("openLink"), "").replace(body("takeLink"), "");
  for (const call of ["openExternal(", "executeCommand(BROWSER_OPEN", "keeper.set(", "sayWords(root, action.words", "revealInExplorer"]) {
    assert.ok(!outside.includes(call), `${call} outside doAction`);
  }
  assert.strictEqual(outside.split("openLink(").length, 2, "openLink called outside doAction + takeLink");
  assert.strictEqual(jobs.tree.length, 1);
  assert.match(fs.readFileSync(path.join(__dirname, "..", "jobs.js"), "utf8"), /require\("\.\/today"\)/);
});
