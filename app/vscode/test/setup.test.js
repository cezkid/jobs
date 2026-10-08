// node --test app/vscode/test/*.test.js (pytest runs it too: app/tests/test_vscode_ext.py)
const test = require("node:test");
const assert = require("node:assert");
const setup = require("../setup");
const today = require("../today");
const form = require("../setup-form.json");

test("clean: only known fields + values; typed words never markup; empty = left out", () => {
  const got = setup.clean({
    training: "leave_on", work: "  Registered <b>nurse</b>\n night shift ", level: "boss", hours: ["part_time", "gig", "full_time"],
    where: "remote_first", city: "", pay: { amount: "$60,000", per: "year" }, avoid: "Acme, Example Co",
    work_permit: "citizen_or_green_card", news: "email", extra: "dropped", resume: "/etc/passwd",
  }, form);
  assert.deepStrictEqual(got, {
    training: "leave_on", work: "Registered b nurse /b night shift", hours: ["full_time", "part_time"],
    where: "remote_first", pay: { amount: 60000, per: "year" }, avoid: "Acme, Example Co",
    work_permit: "citizen_or_green_card", news: "email",
  });
  // the resume path never comes from the page
  assert.ok(!("resume" in got));
  assert.deepStrictEqual(setup.clean(null, form), {});
  assert.deepStrictEqual(setup.clean({ work: "x".repeat(500) }, form).work.length, 200);
});

test("pay: plain amounts only, per hour kept, nonsense left out (the chat asks)", () => {
  assert.strictEqual(setup.payNumber("22.50"), 22.5);
  assert.strictEqual(setup.payNumber("1,200,000"), 1200000);
  for (const bad of ["", "abc", "-5", "0", "60k", "1e9", "99999999"]) assert.strictEqual(setup.payNumber(bad), null, bad);
  assert.deepStrictEqual(setup.clean({ pay: { amount: "18", per: "hour" } }, form).pay, { amount: 18, per: "hour" });
  assert.deepStrictEqual(setup.clean({ pay: { amount: "18", per: "week" } }, form).pay, { amount: 18, per: "year" });
});

test("answers file: version, time, answers, the picked resume", () => {
  const body = JSON.parse(setup.answersFile({ work: "accountant" }, { resume: "My Resume/cv.pdf", now: Date.UTC(2026, 9, 8) }));
  assert.deepStrictEqual(body, { version: 1, saved: "2026-10-08T00:00:00.000Z", work: "accountant", resume: "My Resume/cv.pdf" });
});

test("resume copy: never over another file, odd characters out, only resume kinds", () => {
  assert.strictEqual(setup.resumeName("cv.pdf", new Set()), "cv.pdf");
  assert.strictEqual(setup.resumeName("CV.pdf", new Set(["cv.pdf", "cv (2).pdf"])), "CV (3).pdf");
  assert.strictEqual(setup.resumeName('a:b*c.docx', new Set()), "a b c.docx");
  assert.ok(setup.isResumeKind("x/Resume.PDF") && setup.isResumeKind("r.docx") && setup.isResumeKind("r.pages"));
  assert.ok(!setup.isResumeKind("r.exe") && !setup.isResumeKind("resume"));
});

test("render: every field drawn, labelled, prefilled from saved answers, escaped", () => {
  const html = setup.render(form, { saved: { work: 'say "hi" <x>', hours: ["contract"], where: "local_only", pay: { amount: 20, per: "hour" } },
    esc: today.escapeHtml, guideAction: today.guideAction });
  for (const f of setup.fields(form)) assert.ok(html.includes(`name="${f.id}"`), f.id);
  assert.ok(html.includes('value="say &quot;hi&quot; &lt;x&gt;"'));
  assert.match(html, /value="contract" checked/);
  assert.match(html, /value="local_only" checked/);
  assert.match(html, /<option value="hour" selected>/);
  // every text box has a label; every group a legend
  assert.strictEqual((html.match(/<fieldset/g) || []).length, (html.match(/<legend>/g) || []).length);
  for (const m of html.matchAll(/<input type="text" id="([^"]+)"/g)) assert.ok(html.includes(`<label for="${m[1]}">`), m[1]);
});

test("summary: their answers in plain words, by each question's short name; empty => ask me", () => {
  assert.strictEqual(setup.summary({}, form, ""), "Set me up - I left the welcome page empty, so ask me.");
  const got = setup.summary({ work: " registered <b>nurse</b> ", hours: ["full_time", "contract", "gig"], where: "remote_first",
    pay: { amount: "$60,000", per: "year" }, work_permit: "citizen_or_green_card", level: "nope" }, form, "Jane.pdf");
  assert.strictEqual(got, "Set me up with my answers: Job: registered b nurse /b. Kind of job: Full time, Contract. Where: Remote first, near me too. "
    + "Lowest pay: $60,000 a year. Work in the US: US citizen or green card holder. My resume: Jane.pdf - read my career level, my town or city and my languages from it.");
  assert.strictEqual(setup.summary({ no_resume: true }, form, ""), "Set me up with my answers: I don't have a resume yet - help me make one.");
  // cleaned answers (numbers) read the same as the page's raw ones
  assert.strictEqual(setup.summary(setup.clean({ pay: { amount: "18", per: "hour" } }, form), form, ""), "Set me up with my answers: Lowest pay: $18 an hour.");
  // every field has its short name; a resume-answered one says what it reads
  for (const f of setup.fields(form)) assert.ok(f.short, f.id);
  assert.deepStrictEqual(setup.fields(form).filter((f) => f.from_resume).map((f) => f.id), ["work", "level", "city", "languages"]);
  // the page runs it as source text: no outer names
  assert.doesNotThrow(() => new Function(`return (${setup.summary})`)()({}, form, ""));
});

test("render: resume-answered questions carry their skip line; only draws the sections asked", () => {
  const html = setup.render(form, { esc: today.escapeHtml, guideAction: today.guideAction, only: ["search"] });
  assert.ok(!html.includes('name="training"') && !html.includes('name="work_permit"') && html.includes('name="work"'));
  assert.match(html, /id="f-work-rnote">You can skip this - the chat reads it from your resume\./);
  assert.match(html, /aria-describedby="f-work-hint f-work-rnote"/);
  assert.ok(!html.includes("f-pay-rnote"));
});

test("readError: only resume import's own refusal line shows; paths + internals never", () => {
  const refusal = "CV.pages is a Pages file. Open it and save a copy as Word Document (.docx) or PDF, then drag that onto My Resume.";
  assert.strictEqual(setup.readError(`noise\n${refusal}\n`, "CV.pages"),
    "CV.pages is a Pages file. Open it and save a copy as Word Document (.docx) or PDF, then choose that file here.");
  assert.strictEqual(setup.readError("/Users/x/My Resume/Original resume.pdf: no text layer (scanned?)", "CV.pdf"), null);
  assert.strictEqual(setup.readError("Traceback ...\nValueError: boom", "CV.pdf"), null);
  assert.strictEqual(setup.readError("CV.pdf is in /tmp/x", "CV.pdf"), null);
  assert.strictEqual(setup.readError("", "CV.pdf"), null);
});

function fakePage({ resumeName = "" } = {}) {
  const posted = [];
  const handlers = {};
  const winHandlers = {};
  const el = (props) => ({ dataset: {}, getAttribute: (k) => props.attrs?.[k] ?? null, disabled: false, ...props });
  const elements = [
    el({ name: "work", type: "text", value: "nurse" }),
    el({ name: "where", type: "radio", value: "remote_only", checked: true }),
    el({ name: "where", type: "radio", value: "local_only", checked: false }),
    el({ name: "hours", type: "checkbox", value: "full_time", checked: true }),
    el({ name: "pay", type: "text", value: "30", attrs: { inputmode: "decimal" } }),
    el({ name: "pay-per", type: "select-one", value: "hour" }),
  ];
  elements["pay-per"] = elements[5];
  const attrs = (o) => ({ attrs: {}, getAttribute(k) { return this.attrs[k] ?? null; }, setAttribute(k, v) { this.attrs[k] = v; }, ...o });
  const go = attrs({ dataset: { busy: "Starting Claude…" }, textContent: "Start setup in the chat", disabled: false });
  const preview = { textContent: "" };
  const noResume = attrs({});
  const line = { dataset: { name: resumeName }, textContent: "" };
  const box = { elements, dataset: {}, addEventListener: (type, fn) => { handlers[type] = fn; } };
  const start = { hidden: false };
  const mockWords = { textContent: "" };
  const afters = ["send", "words", "copy"].map((kind) => ({ dataset: { after: kind }, hidden: true, focused: false,
    focus() { this.focused = true; }, querySelector: (sel) => (sel === "[data-words]" && kind === "words" ? mockWords : null) }));
  const ids = { setup: box, go, preview, "no-resume": noResume, "resume-name": line, start };
  const doc = { getElementById: (id) => ids[id] || null,
    querySelectorAll: (sel) => (sel === "[data-after]" ? afters : []),
    querySelector: (sel) => afters.find((a) => sel === `[data-after="${a.dataset.after}"]`) || null };
  global.addEventListener = (type, fn) => { winHandlers[type] = fn; };
  setup.page({ postMessage: (m) => posted.push(m) }, doc, form, setup.summary, 8000);
  delete global.addEventListener;
  return { posted, handlers, winHandlers, go, preview, box, noResume, line, start, afters, mockWords };
}

test("page: preview follows the answers; the start button sends them all at once; Enter in a box never sends early", () => {
  const { posted, handlers, go, preview } = fakePage();
  assert.match(preview.textContent, /^Set me up with my answers: Job: nurse\. Kind of job: Full time\. Where: Remote only\. Lowest pay: \$30 an hour\./);
  let stopped = false;
  handlers.keydown({ key: "Enter", target: { tagName: "INPUT" }, preventDefault: () => { stopped = true; } });
  assert.ok(stopped);
  handlers.submit({ preventDefault() {} });
  assert.deepStrictEqual(posted, [{ form: { work: "nurse", where: "remote_only", hours: ["full_time"], pay: { amount: "30", per: "hour" } } }]);
  assert.ok(go.disabled && go.textContent === "Starting Claude…");
  handlers.submit({ preventDefault() {} });  // busy => never a 2nd send
  assert.strictEqual(posted.length, 1);
});

test("page: resume choice - none toggles + is sent; a picked file wins, marks the form, names the file", () => {
  const { posted, handlers, winHandlers, preview, box, noResume, line } = fakePage();
  assert.strictEqual(box.dataset.resume, "");
  handlers.click({ target: { closest: (sel) => (sel === "#no-resume" ? noResume : null) } });
  assert.strictEqual(box.dataset.resume, "none");
  assert.strictEqual(noResume.attrs["aria-pressed"], "true");
  assert.match(preview.textContent, /I don't have a resume yet - help me make one\.$/);
  winHandlers.message({ data: { type: "resume", name: "Original resume.pdf" } });
  assert.strictEqual(box.dataset.resume, "picked");
  assert.strictEqual(noResume.attrs["aria-pressed"], "false");
  assert.strictEqual(line.textContent, "Added: Original resume.pdf");
  assert.match(preview.textContent, /My resume: Original resume\.pdf - read my career level, my town or city and my languages from it\.$/);
  handlers.submit({ preventDefault() {} });
  assert.ok(!("no_resume" in posted[0].form));
  // a resume already picked when the page was drawn counts from the start
  assert.strictEqual(fakePage({ resumeName: "cv.pdf" }).box.dataset.resume, "picked");
});

test("page: after the press the button's place shows the step that really ran; again brings the button back", () => {
  const { winHandlers, handlers, start, afters, mockWords, preview, posted } = fakePage();
  const shown = () => afters.filter((a) => !a.hidden).map((a) => a.dataset.after);
  // Claude's new chat (or a Copilot send that fell back to a fill) => the words block, their words drawn in it
  winHandlers.message({ data: { type: "started", mode: "new" } });
  assert.ok(start.hidden);
  assert.deepStrictEqual(shown(), ["words"]);
  assert.equal(mockWords.textContent, preview.textContent);
  assert.ok(afters[1].focused);
  winHandlers.message({ data: { type: "started", mode: "fill" } });
  assert.deepStrictEqual(shown(), ["words"]);
  winHandlers.message({ data: { type: "started", mode: "copy" } });
  assert.deepStrictEqual(shown(), ["copy"]);
  winHandlers.message({ data: { type: "started", mode: "send" } });
  assert.deepStrictEqual(shown(), ["send"]);
  // "Put my answers in again" submits: the button's place is back while it runs, the answers go again
  handlers.submit({ preventDefault() {} });
  assert.ok(!start.hidden);
  assert.deepStrictEqual(shown(), []);
  assert.equal(posted.length, 1);
});
