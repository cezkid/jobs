// Jobs side panel (view cezJobFinder.jobs, top of the file list): the dashboard's jobs as a tree.
// Pure (no vscode, no disk): extension.js passes today.model's result + the job folders it listed.
// No new behavior: every row runs one of today.model's actions (same list, same index, same
// extension.js doAction path); the Applied folders add only `open` actions, same shape + cleanPath.
// Tests: node --test app/vscode/test/*.test.js
const today = require("./today");

const VIEW_ID = "cezJobFinder.jobs";
const RUN = "cezJobFinder.jobs.run";
// stage folder whose jobs make the Applied group (app/docs/jobs/job-folders.md)
const APPLIED_DIR = "My Jobs/2 Applied";
// group order + names: the dashboard's own section titles; Next up first, Applied last
const GROUPS = [
  { id: "next", label: "Next up" },
  { id: "waiting", label: "Waiting on you" },
  { id: "interviews", label: "Interviews" },
  { id: "follow_up", label: "Follow up" },
  { id: "best", label: "Best to apply next" },
  { id: "applied", label: "Applied" },
];
// best-next past this many: the rest in the chat (today.BEST_SHOWN, same on the page)
const BEST_SHOWN = today.BEST_SHOWN;
// codicons (VS Code's own icon set), one per kind of row
const ICONS = { say: "comment", status: "check", posting: "link-external", company: "globe", resume: "file-pdf", folder: "folder" };
// job folder name: "12 - Company - Title" (app/status.py); company may itself hold " - " => the
// title is the last part, as the folder name was built
const FOLDER_RE = /^([1-9][0-9]{0,5}) - (.+) - ([^]+)$/;
const RESUME_RE = /_Resume\.pdf$/;

// "Job 12 - Financial Analyst, Example Co": one label for a job everywhere in the panel
function jobLabel(num, title, company) {
  const what = [title, company].filter(Boolean).join(", ");
  return what ? `Job ${num} - ${what}` : `Job ${num}`;
}

// a card's rows: its say buttons (status ones record it, as on the page), then its links + files
function cardRows(card) {
  const rows = card.say.map((b) => ({ label: b.label, icon: b.status ? ICONS.status : ICONS.say, action: b.action,
    tooltip: b.status ? "Saves it here, no chat - you can undo it" : `Puts "${b.words}" in the chat` }));
  if (card.posting) rows.push({ label: "Open the job posting", icon: ICONS.posting, action: card.posting.action });
  if (card.site) rows.push({ label: "Open the company website", icon: ICONS.company, action: card.site.action });
  if (card.resume) rows.push({ label: "Open its resume", icon: ICONS.resume, action: card.resume.action });
  if (card.folder) rows.push({ label: "Show its folder", icon: ICONS.folder, action: card.folder.action });
  return rows;
}

function jobItem(group, card) {
  const label = jobLabel(card.num, card.title, card.company);
  return {
    id: `${group}/${card.num}`, num: card.num, label, description: card.detail || "",
    tooltip: [label, card.detail, card.why].filter(Boolean).join("\n"),
    accessible: [label, card.detail].filter(Boolean).join(", "),
    rows: cardRows(card),
  };
}

// folders under 2 Applied => {num, company, title, folder, resume}; names not ours skipped.
// entries = [{ name, files: [file names inside] }] as extension.js listed them
function appliedFolders(entries) {
  const out = [];
  for (const e of Array.isArray(entries) ? entries : []) {
    const m = e && typeof e.name === "string" ? FOLDER_RE.exec(e.name) : null;
    if (!m) continue;
    const resume = (Array.isArray(e.files) ? e.files : []).find((f) => typeof f === "string" && RESUME_RE.test(f));
    out.push({ num: Number(m[1]), company: m[2], title: m[3], folder: `${APPLIED_DIR}/${e.name}`,
      resume: resume ? `${APPLIED_DIR}/${e.name}/${resume}` : null });
  }
  return out.sort((a, b) => b.num - a.num);
}

// today.model result (m, may be null) + appliedFolders => [{ id, label, items }] for the tree.
// m.actions grows by the Applied rows' `open` actions (cleanPath-checked, as today.model's own)
function tree(m, applied = []) {
  const actions = m ? m.actions : [];
  const groups = [];
  const shown = new Set();
  const add = (id, items) => {
    if (!items.length) return;
    const g = GROUPS.find((x) => x.id === id);
    groups.push({ id, label: g.label, items });
  };
  if (m && m.next) {
    if (m.next.card) add("next", [jobItem("next", m.next.card)]);
    else if (m.next.todo && m.next.todo.say) {
      const t = m.next.todo;
      add("next", [{ id: "next/todo", label: t.say.label, description: "", tooltip: t.text || t.say.label,
        accessible: t.text || t.say.label, rows: [], action: t.say.action, icon: ICONS.say }]);
    }
    if (m.next.card) shown.add(m.next.card.num);
  }
  for (const id of ["waiting", "interviews", "follow_up", "best"]) {
    const s = m ? m.sections.find((x) => x.id === id) : null;
    if (!s) continue;
    const cards = id === "best" ? s.cards.slice(0, BEST_SHOWN) : s.cards;
    cards.forEach((c) => shown.add(c.num));
    add(id, cards.map((c) => jobItem(id, c)));
  }
  const open = (rel, how) => {
    const clean = today.cleanPath(rel);
    return clean ? actions.push({ type: "open", path: clean, how }) - 1 : null;
  };
  add("applied", appliedFolders(applied).filter((a) => !shown.has(a.num)).map((a) => {
    const label = jobLabel(a.num, a.title, a.company);
    const rows = [];
    const resume = a.resume ? open(a.resume, "file") : null;
    const folder = open(a.folder, "folder");
    if (resume != null) rows.push({ label: "Open its resume", icon: ICONS.resume, action: resume });
    if (folder != null) rows.push({ label: "Show its folder", icon: ICONS.folder, action: folder });
    return { id: `applied/${a.num}`, num: a.num, label, description: "", tooltip: label, accessible: label, rows };
  }));
  return groups;
}

// nothing to show: the page's own empty line + its button, else a plain note
// setUp false = no search settings yet: one row that opens the welcome page (extension.js) - a
// brand-new user was told to restart ("made at the next start", adversarial review 2026-10-08)
const SETUP_ROW = { id: "empty", label: "Start setup", description: "Not set up yet",
  tooltip: "Opens the welcome page: a few answers, then the chat finds your first jobs", accessible: "Not set up yet. Start setup",
  rows: [], setup: true, icon: ICONS.say };

function emptyRow(m, setUp = true) {
  if (setUp === false) return { ...SETUP_ROW };
  if (m && m.empty && m.empty.say) {
    return { id: "empty", label: m.empty.say.label, description: m.empty.text, tooltip: m.empty.text,
      accessible: `${m.empty.text} ${m.empty.say.label}`, rows: [], action: m.empty.say.action, icon: ICONS.say };
  }
  const text = m ? "No jobs to show yet." : "Your job list isn't ready yet - it's made at the next start.";
  return { id: "empty", label: text, description: "", tooltip: text, accessible: text, rows: [] };
}

module.exports = { VIEW_ID, RUN, APPLIED_DIR, GROUPS, ICONS, SETUP_ROW, jobLabel, appliedFolders, tree, emptyRow };
