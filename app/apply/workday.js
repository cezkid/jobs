// Workday "My Experience" filler, run in the page via the Claude Chrome extension (javascript_tool).
// `uv run app/jobs.py apply <slug>` appends `window.__jf.run(DATA)`. Facts behind each rule:
// app/docs/apply/workday.md. Fills only; never clicks Save and Continue or Submit.
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
  // where the form is: a synthetic Enter must never move it on (that is a Save the user never clicked)
  const where = () => `${location.href}|${txt(document.querySelector('[data-automation-id="progressBarActiveStep"]'))}`;
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
  const pills = (ctrl) => [...((ctrl && box(ctrl))?.querySelectorAll('[data-automation-id="selectedItem"]') || [])];
  // entry = nearest ancestor of its anchor label holding no other anchor
  function entries(anchor) {
    return labels(document).filter((l) => anchor.test(said(l))).map((l) => {
      let el = l.parentElement;
      while (el.parentElement && labels(el.parentElement).filter((x) => anchor.test(said(x))).length === 1) el = el.parentElement;
      return el;
    });
  }
  // finder for a box inside entry i, run again at verify (a re-render may swap the element)
  const within = (anchor, i, find, re) => () => { const e = entries(anchor)[i]; return e ? find(e, re) : null; };
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

  // every answer that showed once filled, for verify(): ok() reads it again, redo() refills it once
  // (none for pills: pick() presses Enter, which could move the step)
  const kept = [];
  const keep = (area, name, ok, redo = null) => kept.push({ area, name, ok, redo });

  async function text(area, name, find, v) {
    if (!v) return;
    const el = find();
    if (!el) return note(area, name, 'FAIL', 'field not found');
    put(el, v); out(el); await sleep(80);
    if (el.value !== v) return note(area, name, 'WARN', `shows "${el.value.slice(0, 40)}"`);
    keep(area, name, () => find()?.value === v, () => { const e = find(); if (e) { put(e, v); out(e); } });
  }
  async function check(area, name, find, want) {
    const cb = () => find()?.querySelector('input[type="checkbox"]');
    const el = cb();
    if (!el) return want && note(area, name, 'FAIL', 'checkbox not found');
    if (el.checked !== want) { click(el); await sleep(300); }
    if (el.checked !== want) return note(area, name, 'WARN', `checked=${el.checked}`);
    keep(area, name, () => cb()?.checked === want, () => { const e = cb(); if (e && e.checked !== want) click(e); });
  }
  async function date(area, name, find, ym) {
    if (!ym) return;
    if (!find()) return note(area, name, 'FAIL', 'field not found');
    const [y, m] = ym.split('-');
    for (const [sel, v] of [['Month', m], ['Year', y]]) {
      const get = () => find()?.querySelector(`input[data-automation-id*="${sel}" i]`);
      const same = (el) => !!el && norm(el.value).replace(/^0/, '') === v.replace(/^0/, '');
      const fill = (el) => { put(el, v); if (!same(el)) for (const ch of v) key(el, ch, ch.charCodeAt(0)); out(el); };
      const el = get();
      if (!el || !v) continue;
      fill(el); await sleep(80);
      if (same(el)) keep(area, `${name} ${sel}`, () => same(get()), () => { const e = get(); if (e) fill(e); });
    }
  }
  // single-choice menu (Degree): options live in a listbox popup, not in the field
  async function choose(btn, wanted) {
    click(btn);
    const opts = await until(() => [...document.querySelectorAll('[role="listbox"] [role="option"]')].filter(shown), 3000);
    if (!opts) return { why: 'menu did not open' };
    const hit = best(opts, wanted);
    if (!hit) { key(btn, 'Escape', 27); return { ask: `no match for ${wanted[0]}; choices: ${opts.map(txt).join(' | ')}` }; }
    click(hit); await sleep(400);
    return { got: txt(hit) };
  }
  async function menu(area, name, find, wanted) {
    const btn = find();
    if (!btn) return note(area, name, 'FAIL', 'field not found');
    const shows = (w) => { const b = find(); return !!b && norm(txt(b)).includes(norm(w)); };
    const already = wanted.find(shows);
    if (already) return keep(area, name, () => shows(already), async () => { const b = find(); if (b) await choose(b, [already]); });
    const { why, ask, got } = await choose(btn, wanted);
    if (why) return note(area, name, 'FAIL', why);
    if (ask) return note(area, name, 'ASK', ask);
    note(area, name, 'OK', got);
    keep(area, name, () => shows(got), async () => { const b = find(); if (b) await choose(b, [got]); });
  }
  // search-and-pick (Field of Study, Skills): type, Enter, pick a popup option outside the field's own pills
  async function pick(area, name, find, wanted, exact = false) {
    const input = find();
    if (!input) return note(area, name, 'FAIL', 'field not found');
    const has = (w) => pills(find()).some((p) => norm(txt(p)) === norm(w));
    const already = wanted.find(has);
    if (already) return keep(area, name, () => has(already));
    const tried = [];
    for (const w of wanted) {
      const at = where();
      put(input, w); key(input, 'Enter', 13); await sleep(600);
      if (where() !== at || !document.contains(input)) throw new Error('Enter moved the form to another step - stopped filling; tell the user to check the page');
      const opts = await until(() => [...document.querySelectorAll('[data-automation-id="promptOption"]')].filter((o) => shown(o) && !box(input).contains(o) && !/no items/i.test(txt(o))), 3000);
      const hit = opts && (exact ? opts.find((o) => norm(txt(o)) === norm(w)) : best(opts, [w]));
      if (!hit) { tried.push(`${w}: ${opts ? opts.slice(0, 4).map(txt).join(' / ') : 'none'}`); continue; }
      const before = pills(input).length;
      click(hit.querySelector('input[type="checkbox"], input[type="radio"]') || hit); await sleep(400);
      put(input, ''); key(input, 'Escape', 27); out(input);
      const got = txt(hit);
      if (pills(input).length <= before) return note(area, name, 'WARN', `"${got}" click did not register`);
      keep(area, name, () => has(got));
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
      const f = (re) => within(anchor, i, field, re), fb = (re) => within(anchor, i, fieldBox, re);
      await text(a, 'Job Title', f(anchor), w.title);
      await text(a, 'Company', f(/^company/i), w.company);
      await text(a, 'Location', f(/^location/i), w.location);
      await check(a, 'I currently work here', fb(/currently work here/i), w.current);
      await sleep(300); // To box appears or goes after the checkbox
      await date(a, 'From', fb(/^from/i), w.start);
      if (!w.current) await date(a, 'To', fb(/^to\b/i), w.end);
      await text(a, 'Role Description', f(/description/i), w.description);
    }
  }
  async function education(list) {
    const anchor = /^school or university/i;
    await grow('Education', /^education$/i, anchor, list.length);
    for (const [i, d] of list.entries()) {
      const e = entries(anchor)[i], a = `Education ${i + 1}`;
      if (!e) break;
      const f = (re) => within(anchor, i, field, re);
      await text(a, 'School', f(anchor), d.school);
      await menu(a, 'Degree', f(/^degree/i), d.degree);
      if (d.field.length) await pick(a, 'Field of Study', f(/^field of study/i), d.field);
      if (d.end) await date(a, 'To', within(anchor, i, fieldBox, /^to\b/i), d.end);
    }
  }
  async function skills(list, languages) {
    const find = () => { const l = labels(document).find((x) => /skills/i.test(said(x))); return l && ((l.htmlFor && document.getElementById(l.htmlFor)) || box(l)?.querySelector('input')); };
    const input = find();
    if (!input) return note('Skills', 'field', 'FAIL', 'not found on this step');
    // some tenants (tenant A) take languages in the Skills box as "Spanish - Fluent", listed levels only
    if (!section(/^languages$/i)) for (const g of languages) {
      await unpick(input, new RegExp(`^${g.name} - `, 'i'));
      await pick('Languages', g.name, find, g.levels.map((lv) => `${g.name} - ${lv}`), true);
    } else note('Languages', 'section', 'ASK', 'separate Languages section - not handled yet, fill by hand');
    for (const s of list) await pick('Skills', s, find, [s]);
  }
  // after the page settles, read every answer again: a re-render can clear one that showed when
  // filled. Refill once, still gone -> FAIL. Catches cleared values only, not every unkept one (workday.md)
  async function verify(settle = 2500) {
    await sleep(settle);
    const dropped = kept.filter((k) => !k.ok());
    for (const k of dropped) if (k.redo) await k.redo(); else note(k.area, k.name, 'ASK', 'answer dropped after the page settled - pick it again by hand');
    const redone = dropped.filter((k) => k.redo);
    if (redone.length) await sleep(settle);
    for (const k of redone) note(k.area, k.name, k.ok() ? 'OK' : 'FAIL', k.ok() ? 'dropped after the page settled, refilled once - kept' : 'answer dropped - refilled once, still not kept; fill by hand');
    note('Verify', 'answers', 'OK', `${kept.length} read again after the page settled, ${dropped.length} dropped`);
  }

  async function run(data, only = ['work', 'education', 'skills']) {
    Object.assign(S, { done: false, report: [] });
    kept.length = 0;
    try {
      if (only.includes('work')) { S.step = 'work'; await work(data.work); }
      if (only.includes('education')) { S.step = 'education'; await education(data.education); }
      if (only.includes('skills')) { S.step = 'skills'; await skills(data.skills, data.languages); }
      S.step = 'verify'; await verify();
    } catch (err) { note(S.step, 'error', 'FAIL', String(err)); }
    S.step = 'done'; S.done = true;
  }
  // tool call times out at 45s => run() in background, poll status()
  const status = () => JSON.stringify({ step: S.step, done: S.done, problems: S.report.filter((r) => !r.startsWith('OK')), ok: S.report.filter((r) => r.startsWith('OK')).length });
  const errors = () => [...new Set([...document.querySelectorAll('[data-automation-id="errorMessage"]')].filter(shown).map(txt))];
  // Resume/CV box = smallest block holding a file input + a "Resume" / "CV" heading or label
  function resumeBox() {
    const has = (el) => [...el.querySelectorAll('h2, h3, h4, legend, label, [data-automation-id="formLabel"]')].some((h) => /resume|\bcv\b/i.test(txt(h)));
    const found = [...document.querySelectorAll('input[type="file"]')].map((f) => {
      let el = f.parentElement;
      while (el && el !== document.body && !has(el)) el = el.parentElement;
      return el !== document.body && el;
    }).filter(Boolean);
    return found.sort((a, b) => a.querySelectorAll('*').length - b.querySelectorAll('*').length)[0] || null;
  }
  // after the extension's file upload: wait for the box to show the file's name or Workday's own
  // error under it (an error wins). 'ok' / the page's words / 'not confirmed'. Fixture-modelled; live
  // widget + whether the file leaves on choosing unmeasured (workday.md #Resume upload)
  async function uploaded(name, ms = 20000) {
    if (!resumeBox()) return 'no Resume/CV box on this page';
    const err = () => { const b = resumeBox(); return b ? [...new Set([...b.querySelectorAll('[data-automation-id="errorMessage"]')].filter(shown).map(txt))].join(' ') : ''; };
    const named = () => !!norm(name) && norm(txt(resumeBox())).includes(norm(name));
    if (!await until(() => err() || named(), ms)) return 'not confirmed';
    await sleep(1000); // an error can follow the name (file checked after it shows)
    return err() || (named() ? 'ok' : 'not confirmed');
  }
  // posting page, before Apply + sign-in: closed only when no Apply button shows AND the page says
  // so. The page draws itself seconds after load (blank before) - wait for either. Workday wording
  // measured 2026-10-05 (workday.md #Closed posting); the rest is form.CLOSED's, unmeasured here
  const CLOSED = /page you are looking for doesn['’]t exist|no longer (?:accepting applications|available|open)|(?:this )?job (?:post(?:ing)? )?(?:is )?closed|not accepting applications|posting (?:has )?expired/i;
  const apply = () => document.querySelector('[data-automation-id="adventureButton"]');
  async function closed(ms = 10000) {
    await until(() => shown(apply()) || shown(document.querySelector('[data-automation-id="errorContainer"]')) || CLOSED.test(txt(document.body)), ms);
    return !shown(apply()) && CLOSED.test(document.body.innerText || '');
  }
  return { run, status, errors, uploaded, closed, S };
})();
