// Workday "My Experience" filler, run in the page via the Claude Chrome extension (javascript_tool).
// `uv run app/jobs.py apply <slug>` appends `window.__jf.run(DATA)`. Facts behind each rule:
// app/docs/workday.md. Fills only; never clicks Save and Continue or Submit.
window.__jf = (() => {
  // hidden tab (window behind others) => setTimeout throttled to ~1/min; MessageChannel is not
  const mc = new MessageChannel(), q = [];
  mc.port1.onmessage = () => q.shift()?.();
  const tick = () => new Promise((r) => { q.push(r); mc.port2.postMessage(0); });
  const sleep = async (ms) => { const t = Date.now() + ms; while (Date.now() < t) await tick(); };
  const norm = (s) => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  const txt = (el) => (el?.textContent || '').replace(/\s+/g, ' ').trim();
  const shown = (el) => !!el && el.getClientRects().length > 0;
  const S = { done: false, step: '', report: [] };
  const note = (area, field, status, detail = '') => S.report.push(`${status} ${area} > ${field}${detail ? ': ' + detail : ''}`);
  async function until(fn, ms = 4000) {
    for (const t = Date.now() + ms; Date.now() < t; await sleep(100)) { const v = fn(); if (v && (!Array.isArray(v) || v.length)) return v; }
    return null;
  }
  // value only sticks once focus leaves the field (a real click-out): focusin before, focusout after
  function put(el, v) {
    const set = Object.getOwnPropertyDescriptor(el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype, 'value').set;
    el.dispatchEvent(new FocusEvent('focusin', { bubbles: true })); el.focus();
    set.call(el, v);
    el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: v }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }
  const out = (el) => { el.dispatchEvent(new FocusEvent('blur')); el.dispatchEvent(new FocusEvent('focusout', { bubbles: true })); el.blur(); };
  const key = (el, k, code) => ['keydown', 'keyup'].forEach((t) => el.dispatchEvent(new KeyboardEvent(t, { key: k, keyCode: code, which: code, bubbles: true })));
  const click = (el) => { el.scrollIntoView({ block: 'center' }); ['mousedown', 'mouseup'].forEach((t) => el.dispatchEvent(new MouseEvent(t, { bubbles: true }))); el.click(); };
  function best(opts, wanted) {
    for (const w of wanted) {
      const n = norm(w);
      const hit = opts.find((o) => norm(txt(o)) === n) || opts.find((o) => norm(txt(o)).startsWith(n)) || opts.find((o) => n.length > 3 && norm(txt(o)).includes(n));
      if (hit) return hit;
    }
    return null;
  }
  // fields found by visible label, never by id: ids carry per-entry numbers that differ per tenant
  const labels = (root) => [...root.querySelectorAll('label, legend, [data-automation-id="formLabel"]')];
  const said = (l) => txt(l).replace(/\*$/, '').trim();
  const box = (el) => el.closest('[data-automation-id^="formField"]') || el.parentElement?.parentElement;
  function field(root, re) {
    const l = labels(root).find((x) => re.test(said(x)));
    if (!l) return null;
    return (l.htmlFor && document.getElementById(l.htmlFor)) || box(l)?.querySelector('input:not([type="hidden"]), textarea, button') || null;
  }
  const fieldBox = (root, re) => { const l = labels(root).find((x) => re.test(said(x))); return l ? box(l) : null; };
  const pills = (ctrl) => [...(box(ctrl)?.querySelectorAll('[data-automation-id="selectedItem"]') || [])];
  // entry = nearest ancestor of its anchor label holding no other anchor
  function entries(anchor) {
    return labels(document).filter((l) => anchor.test(said(l))).map((l) => {
      let el = l.parentElement;
      while (el.parentElement && labels(el.parentElement).filter((x) => anchor.test(said(x))).length === 1) el = el.parentElement;
      return el;
    });
  }
  function section(heading) {
    let el = [...document.querySelectorAll('h2, h3, h4, legend')].find((h) => heading.test(txt(h)))?.parentElement;
    while (el && ![...el.querySelectorAll('button')].some((b) => /^add( another)?$/i.test(txt(b)))) el = el.parentElement;
    return el;
  }
  async function grow(area, heading, anchor, n) {
    while (entries(anchor).length < n) {
      const add = [...(section(heading)?.querySelectorAll('button') || [])].reverse().find((b) => /^add( another)?$/i.test(txt(b)));
      const before = entries(anchor).length;
      if (!add) return note(area, 'Add', 'FAIL', 'no Add button');
      click(add);
      if (!await until(() => entries(anchor).length > before)) return note(area, 'Add', 'FAIL', 'no new entry appeared');
    }
    const extra = entries(anchor).length - n;
    if (extra > 0) note(area, 'entries', 'WARN', `${extra} more on the form than on the resume - delete by hand if duplicated`);
  }

  async function text(area, name, el, v) {
    if (!v) return;
    if (!el) return note(area, name, 'FAIL', 'field not found');
    put(el, v); out(el); await sleep(80);
    if (el.value !== v) note(area, name, 'WARN', `shows "${el.value.slice(0, 40)}"`);
  }
  async function check(area, name, b, want) {
    const cb = b?.querySelector('input[type="checkbox"]');
    if (!cb) return want && note(area, name, 'FAIL', 'checkbox not found');
    if (cb.checked !== want) { click(cb); await sleep(300); }
    if (cb.checked !== want) note(area, name, 'WARN', `checked=${cb.checked}`);
  }
  async function date(area, name, b, ym) {
    if (!ym) return;
    if (!b) return note(area, name, 'FAIL', 'field not found');
    const [y, m] = ym.split('-');
    for (const [sel, v] of [['Month', m], ['Year', y]]) {
      const el = b.querySelector(`input[data-automation-id*="${sel}" i]`);
      if (!el || !v) continue;
      put(el, v);
      if (norm(el.value).replace(/^0/, '') !== v.replace(/^0/, '')) for (const ch of v) key(el, ch, ch.charCodeAt(0));
      out(el); await sleep(80);
    }
  }
  // single-choice menu (Degree): options live in a listbox popup, not in the field
  async function menu(area, name, btn, wanted) {
    if (!btn) return note(area, name, 'FAIL', 'field not found');
    if (wanted.some((w) => norm(txt(btn)).includes(norm(w)))) return;
    click(btn);
    const opts = await until(() => [...document.querySelectorAll('[role="listbox"] [role="option"]')].filter(shown), 3000);
    if (!opts) return note(area, name, 'FAIL', 'menu did not open');
    const hit = best(opts, wanted);
    if (!hit) { key(btn, 'Escape', 27); return note(area, name, 'ASK', `no match for ${wanted[0]}; choices: ${opts.map(txt).join(' | ')}`); }
    click(hit); await sleep(400);
    note(area, name, 'OK', txt(hit));
  }
  // search-and-pick (Field of Study, Skills): type, Enter, pick a popup option outside the field's own pills
  async function pick(area, name, input, wanted, exact = false) {
    if (!input) return note(area, name, 'FAIL', 'field not found');
    if (pills(input).some((p) => wanted.some((w) => norm(txt(p)) === norm(w)))) return;
    const tried = [];
    for (const w of wanted) {
      put(input, w); key(input, 'Enter', 13); await sleep(600);
      const opts = await until(() => [...document.querySelectorAll('[data-automation-id="promptOption"]')].filter((o) => shown(o) && !box(input).contains(o) && !/no items/i.test(txt(o))), 3000);
      const hit = opts && (exact ? opts.find((o) => norm(txt(o)) === norm(w)) : best(opts, [w]));
      if (!hit) { tried.push(`${w}: ${opts ? opts.slice(0, 4).map(txt).join(' / ') : 'none'}`); continue; }
      const before = pills(input).length;
      click(hit.querySelector('input[type="checkbox"], input[type="radio"]') || hit); await sleep(400);
      put(input, ''); key(input, 'Escape', 27); out(input);
      const got = txt(hit);
      if (pills(input).length <= before) return note(area, name, 'WARN', `"${got}" click did not register`);
      return note(area, name, norm(got) === norm(wanted[0]) ? 'OK' : 'ASK', `picked "${got}"`);
    }
    put(input, ''); key(input, 'Escape', 27); out(input);
    note(area, name, 'ASK', `not on this form's list. Tried ${tried.join(' || ')}`);
  }
  async function unpick(input, re) {
    for (const p of pills(input).filter((p) => re.test(txt(p)))) { const x = p.querySelector('[data-automation-id="DELETE_charm"]'); if (x) { click(x); await sleep(300); } }
  }

  async function work(list) {
    const anchor = /^job title/i;
    await grow('Work', /^work experience$/i, anchor, list.length);
    for (const [i, w] of list.entries()) {
      const e = entries(anchor)[i], a = `Work ${i + 1}`;
      if (!e) break;
      await text(a, 'Job Title', field(e, anchor), w.title);
      await text(a, 'Company', field(e, /^company/i), w.company);
      await text(a, 'Location', field(e, /^location/i), w.location);
      await check(a, 'I currently work here', fieldBox(e, /currently work here/i), w.current);
      await sleep(300); // To box appears or goes after the checkbox
      await date(a, 'From', fieldBox(e, /^from/i), w.start);
      if (!w.current) await date(a, 'To', fieldBox(e, /^to\b/i), w.end);
      await text(a, 'Role Description', field(e, /description/i), w.description);
    }
  }
  async function education(list) {
    const anchor = /^school or university/i;
    await grow('Education', /^education$/i, anchor, list.length);
    for (const [i, d] of list.entries()) {
      const e = entries(anchor)[i], a = `Education ${i + 1}`;
      if (!e) break;
      await text(a, 'School', field(e, anchor), d.school);
      await menu(a, 'Degree', field(e, /^degree/i), d.degree);
      if (d.field.length) await pick(a, 'Field of Study', field(e, /^field of study/i), d.field);
      if (d.end) await date(a, 'To', fieldBox(e, /^to\b/i), d.end);
    }
  }
  async function skills(list, languages) {
    const l = labels(document).find((x) => /skills/i.test(said(x)));
    const input = l && ((l.htmlFor && document.getElementById(l.htmlFor)) || box(l)?.querySelector('input'));
    if (!input) return note('Skills', 'field', 'FAIL', 'not found on this step');
    // some tenants (tenant A) take languages in the Skills box as "Spanish - Fluent", listed levels only
    if (!section(/^languages$/i)) for (const g of languages) {
      await unpick(input, new RegExp(`^${g.name} - `, 'i'));
      await pick('Languages', g.name, input, g.levels.map((lv) => `${g.name} - ${lv}`), true);
    } else note('Languages', 'section', 'ASK', 'separate Languages section - not handled yet, fill by hand');
    for (const s of list) await pick('Skills', s, input, [s]);
  }

  async function run(data, only = ['work', 'education', 'skills']) {
    Object.assign(S, { done: false, report: [] });
    try {
      if (only.includes('work')) { S.step = 'work'; await work(data.work); }
      if (only.includes('education')) { S.step = 'education'; await education(data.education); }
      if (only.includes('skills')) { S.step = 'skills'; await skills(data.skills, data.languages); }
    } catch (err) { note(S.step, 'error', 'FAIL', String(err)); }
    S.step = 'done'; S.done = true;
  }
  // tool call times out at 45s => run() in background, poll status()
  const status = () => JSON.stringify({ step: S.step, done: S.done, problems: S.report.filter((r) => !r.startsWith('OK')), ok: S.report.filter((r) => r.startsWith('OK')).length });
  const errors = () => [...new Set([...document.querySelectorAll('[data-automation-id="errorMessage"]')].filter(shown).map(txt))];
  return { run, status, errors, S };
})();
