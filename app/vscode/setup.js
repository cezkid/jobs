// Welcome page form: setup's questions answered up front (owner 2026-10-08: "a form the user can fill to
// feed it all to ai ... instead of the ai having to ask so many questions"). Pure (no vscode, no disk):
// extension.js reads setup-form.json, saves clean() to .data/setup-form.json, then puts summary() - the
// answers in plain words - in the chat; job-setup reads that file and asks only what's missing. Every
// field optional. Resume first (owner 2026-10-08: "2 should be resume upload or no resume"): a picked
// file answers the from_resume questions, so they're marked skippable; no resume => they're the ones to fill
const path = require("path");

// answers file: private (.data), read by job-setup (app/skills/job-setup.md #0)
const ANSWERS = path.join(".data", "setup-form.json");
const VERSION = 1;
// resume copied into My Resume (the folder job-setup imports from); kinds resume-import reads or
// names the one step for (Pages, older Word: "save a copy as .docx or PDF")
const RESUME_DIR = "My Resume";
const RESUME_KINDS = ["pdf", "docx", "doc", "pages", "odt", "rtf"];
// resume details (made by setup's import: picking again then copies, never re-reads over it) + the
// record resume import's first step writes: which file it read (app/resume/import_pdf.py source_record)
const DETAILS = "Resume details.yml";
const SOURCE = path.join(".data", "resume-source.json");
const PAY_MAX = 10000000;

// control characters + angle brackets out, spaces folded, cut to max: the answers are typed words, never markup
function text(value, max) {
  if (typeof value !== "string") return "";
  return value.replace(/[\u0000-\u001f\u007f<>]/g, " ").replace(/\s+/g, " ").trim().slice(0, max);
}

// "60,000" / "60000" / "22.50" => number; anything else (or out of range) => null
function payNumber(value) {
  const t = text(value, 20).replace(/[$,\s]/g, "");
  if (!/^\d+(\.\d{1,2})?$/.test(t)) return null;
  const n = Number(t);
  return n > 0 && n <= PAY_MAX ? n : null;
}

function fields(form) {
  return form.sections.flatMap((s) => s.fields);
}

// what the page sent => only known fields, only known option values; empty = left out (the chat asks).
// no_resume = they said they have none yet (the resume path itself never comes from the page)
function clean(raw, form) {
  const out = {};
  const given = raw && typeof raw === "object" ? raw : {};
  if (given.no_resume === true || given.resume_state === "none") out.no_resume = true;
  for (const f of fields(form)) {
    const v = given[f.id];
    const values = (f.options || []).map((o) => o.value);
    if (f.type === "text") {
      const t = text(v, f.max || 200);
      if (t) out[f.id] = t;
    } else if (f.type === "choice") {
      if (values.includes(v)) out[f.id] = v;
    } else if (f.type === "multi") {
      const picked = Array.isArray(v) ? values.filter((x) => v.includes(x)) : [];
      if (picked.length) out[f.id] = picked;
    } else if (f.type === "pay") {
      const n = payNumber(v && v.amount);
      const units = f.units.map((u) => u.value);
      if (n != null) out[f.id] = { amount: n, per: units.includes(v.per) ? v.per : units[0] };
    }
  }
  return out;
}

// file job-setup reads: answers + the resume picked (a path inside the folder, never from the page)
function answersFile(answers, { resume = null, now }) {
  const body = { version: VERSION, saved: new Date(now).toISOString(), ...answers };
  if (resume) body.resume = resume;
  return `${JSON.stringify(body, null, 1)}\n`;
}

// a picked file's name in My Resume: same name taken by another file => " (2)", " (3)" ...
function resumeName(base, taken) {
  const ext = path.extname(base);
  const stem = base.slice(0, base.length - ext.length).replace(/[\\/:*?"<>|\u0000-\u001f]/g, " ").trim() || "Resume";
  for (let i = 1; ; i++) {
    const name = i === 1 ? `${stem}${ext}` : `${stem} (${i})${ext}`;
    if (!taken.has(name.toLowerCase())) return name;
  }
}

// resume import's error output => the line to show, or null (=> the page's own plain line). Only its
// refusal line passes ("<file> is a Pages file. Save a copy ..."): plain words, the file's own name;
// anything else names paths or internals
function readError(stderr, name) {
  const line = String(stderr || "").split(/\r?\n/).map((l) => l.trim()).filter(Boolean).pop() || "";
  if (!name || !line.startsWith(`${name} is `) || line.length > 300 || /[\\/]/.test(line.slice(name.length))) return null;
  // its last step names the file list; here the file is chosen with the button
  return line.replace(/then drag that onto My Resume\.$/, "then choose that file here.");
}

function isResumeKind(file) {
  return RESUME_KINDS.includes(path.extname(file).slice(1).toLowerCase());
}

// the answers in plain words: what goes in the chat, shown live above the start button (the user sees
// what they send). Self-contained - the page runs this same source (no outer names). answers = raw
// page values or clean() output; resume = the picked file's name. Empty answers => "ask me"
function summary(answers, form, resume) {
  const a = answers || {};
  const all = [];
  for (const s of form.sections || []) for (const f of s.fields || []) all.push(f);
  const label = (f, v) => {
    const o = (f.options || []).find((x) => x.value === v);
    return o ? o.label : "";
  };
  const plain = (v) => String(v == null ? "" : v).replace(/[\u0000-\u001f\u007f<>]/g, " ").replace(/\s+/g, " ").trim();
  const said = [];
  const unsaid = [];
  for (const f of all) {
    const v = a[f.id];
    let t = "";
    if (f.type === "text") t = plain(v).slice(0, f.max || 200);
    else if (f.type === "choice") t = label(f, v);
    else if (f.type === "multi") t = (Array.isArray(v) ? v : []).map((x) => label(f, x)).filter(Boolean).join(", ");
    else if (f.type === "pay" && v && plain(v.amount)) {
      const unit = (f.units || []).find((u) => u.value === v.per) || (f.units || [])[0] || { label: "" };
      t = `$${plain(v.amount).replace(/^\$/, "")} ${unit.label}`.trim();
    }
    if (t) said.push(`${f.short}: ${t}.`);
    else if (f.from_resume) unsaid.push(f.from_resume);
  }
  const file = plain(resume);
  const list = (xs) => (xs.length < 2 ? xs.join("") : `${xs.slice(0, -1).join(", ")} and ${xs[xs.length - 1]}`);
  if (file) said.push(`My resume: ${file}${unsaid.length ? ` - read ${list(unsaid)} from it` : ""}.`);
  else if (a.no_resume === true || a.resume_state === "none") said.push("I don't have a resume yet - help me make one.");
  if (!said.length) return "Set me up - I left the welcome page empty, so ask me.";
  return `Set me up with my answers: ${said.join(" ")}`;
}

// the form's sections as HTML. saved = earlier answers (prefilled); esc = today.escapeHtml.
// guideAction(path) => the button number that opens a guide (extension decides what it opens).
// only = section ids to draw (the welcome page splits them across its steps); none = all
function render(form, { saved = {}, esc, guideAction, only = null }) {
  const h = esc;
  const field = (f) => {
    const id = `f-${f.id}`;
    // shown once a resume is picked (CSS on the form's data-resume): skippable, said plainly
    const rnote = f.from_resume ? `<p class="hint rnote" id="${id}-rnote">You can skip this - the chat reads it from your resume.</p>` : "";
    const hint = (f.hint ? `<p class="hint" id="${id}-hint">${h(f.hint)}</p>` : "") + rnote;
    const about = f.hint || f.from_resume ? ` aria-describedby="${[f.hint ? `${id}-hint` : "", rnote ? `${id}-rnote` : ""].filter(Boolean).join(" ")}"` : "";
    if (f.type === "text") {
      return `<div class="field"><label for="${id}">${h(f.label)}</label>${hint}`
        + `<input type="text" id="${id}" name="${h(f.id)}" maxlength="${Number(f.max) || 200}" autocomplete="off"${about} value="${h(saved[f.id] || "")}"></div>`;
    }
    if (f.type === "pay") {
      const was = saved[f.id] || {};
      const units = f.units.map((u) => `<option value="${h(u.value)}"${was.per === u.value ? " selected" : ""}>${h(u.label)}</option>`).join("");
      return `<div class="field"><label for="${id}">${h(f.label)}</label>${hint}<div class="pay"><span aria-hidden="true">$</span>`
        + `<input type="text" inputmode="decimal" id="${id}" name="${h(f.id)}" maxlength="${Number(f.max) || 12}" autocomplete="off"${about} value="${h(was.amount != null ? String(was.amount) : "")}">`
        + `<select name="${h(f.id)}-per" aria-label="Per">${units}</select></div></div>`;
    }
    const multi = f.type === "multi";
    const picked = (v) => (multi ? (saved[f.id] || []).includes(v) : saved[f.id] === v);
    const guide = f.guide ? `<p class="hint"><button type="button" class="link" data-a="${guideAction(f.guide.path)}">${h(f.guide.title)}</button></p>` : "";
    const opts = f.options.map((o) => `<label class="opt"><input type="${multi ? "checkbox" : "radio"}" name="${h(f.id)}" value="${h(o.value)}"`
      + `${picked(o.value) ? " checked" : ""}> ${h(o.label)}</label>`).join("");
    return `<fieldset class="field"${about}><legend>${h(f.label)}</legend>${hint}${guide}<div class="opts">${opts}</div></fieldset>`;
  };
  return form.sections.filter((s) => !only || only.includes(s.id)).map((s) => `<section class="form-part" aria-labelledby="p-${h(s.id)}"><h3 id="p-${h(s.id)}">${h(s.title)}</h3>`
    + (s.note ? `<p class="hint">${h(s.note)}</p>` : "") + s.fields.map(field).join("") + "</section>").join("");
}

// page side (runs in the webview, sent as source text): the preview above the start button follows every
// answer; the start button sends them all at once; Enter in a box never sends the form early; the resume
// choice (picked file / none) marks the questions a resume answers. summary = summary() above, as source
function page(vscode, doc, form, summary, clearMs) {
  const box = doc.getElementById("setup");
  if (!box) return;
  const state = Object.assign({ resume: "", none: false }, { resume: (doc.getElementById("resume-name") || { dataset: {} }).dataset.name || "" });
  const answers = () => {
    const out = {};
    for (const el of box.elements) {
      if (!el.name || el.disabled || el.name === "resume_state") continue;
      if (el.type === "radio") { if (el.checked) out[el.name] = el.value; continue; }
      if (el.type === "checkbox") { if (el.checked) (out[el.name] = out[el.name] || []).push(el.value); continue; }
      if (el.name.endsWith("-per")) continue;
      if (el.getAttribute("inputmode") === "decimal") {
        const per = box.elements[`${el.name}-per`];
        out[el.name] = { amount: el.value, per: per ? per.value : "" };
        continue;
      }
      out[el.name] = el.value;
    }
    if (state.none && !state.resume) out.no_resume = true;
    return out;
  };
  const show = () => {
    box.dataset.resume = state.resume ? "picked" : state.none ? "none" : "";
    const none = doc.getElementById("no-resume");
    if (none) none.setAttribute("aria-pressed", String(state.none && !state.resume));
    const preview = doc.getElementById("preview");
    if (preview) preview.textContent = summary(answers(), form, state.resume);
  };
  box.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.target.tagName === "INPUT") e.preventDefault();
  });
  box.addEventListener("input", show);
  box.addEventListener("change", show);
  box.addEventListener("click", (e) => {
    if (e.target.closest && e.target.closest("#no-resume")) { state.none = !state.none; show(); }
  });
  box.addEventListener("submit", (e) => {
    e.preventDefault();
    const go = doc.getElementById("go");
    if (go.getAttribute("aria-busy")) return;
    // "Put my answers in again" (after a start): the button's place comes back while it runs
    const start = doc.getElementById("start");
    if (start && start.hidden && doc.querySelectorAll) {
      start.hidden = false;
      for (const b of doc.querySelectorAll("[data-after]")) b.hidden = true;
    }
    go.dataset.text = go.dataset.text || go.textContent;
    go.textContent = go.dataset.busy || go.textContent;
    go.disabled = true;
    go.setAttribute("aria-busy", "true");
    vscode.postMessage({ form: answers() });
  });
  addEventListener("message", (e) => {
    const d = e.data || {};
    // the start button ran (extension: what really happened) => its place turns into the next step
    if (d.type === "started" && typeof d.mode === "string") {
      const kind = d.mode === "send" ? "send" : d.mode === "copy" ? "copy" : "words";
      const start = doc.getElementById("start");
      if (start) start.hidden = true;
      for (const b of doc.querySelectorAll("[data-after]")) b.hidden = b.dataset.after !== kind;
      const shown = doc.querySelector(`[data-after="${kind}"]`);
      const words = shown && shown.querySelector("[data-words]");
      const preview = doc.getElementById("preview");
      if (words && preview) words.textContent = preview.textContent;
      if (shown) shown.focus();
    }
    if (d.type === "resume" && typeof d.name === "string") {
      state.resume = d.name;
      if (d.name) state.none = false;
      const line = doc.getElementById("resume-name");
      if (line) { line.dataset.name = d.name; line.textContent = d.name ? `Added: ${d.name}` : ""; }
      show();
    }
  });
  show();
}

module.exports = { ANSWERS, VERSION, RESUME_DIR, RESUME_KINDS, DETAILS, SOURCE, PAY_MAX, readError, text, payNumber, fields, clean, answersFile, resumeName, isResumeKind, summary, render, page };
