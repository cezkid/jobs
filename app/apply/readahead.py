"""What an application asks, read before applying.

The job search keeps the questions of application forms it has captured - Greenhouse, Lever, Ashby,
Workable, Recruitee - at GET /jobs/<slug>/apply-form, keyless: the job's listing id goes out,
nothing about the user (AGENTS.md privacy table). Fetched when a resume is made for a listed job,
saved in the job folder, summed up in Check before sending.md, and used to draft paste-ready
answers for systems the program can't fill.

What it is (measured 2026-10-01): {provider, basics: [contact fields + resume], questions: [{text,
required, answer?}]} - `answer` names the box ("written answer", "choose one", "choose any",
"yes / no", "upload"; absent = one line), no options, no ids. A 404 = no form captured, never
"asks nothing". The job search's own count over ~100k forms (2026-08): 67% ask nothing beyond a
resume + contact details, 16% ask 1-4 questions, 16% 5-14, 1% 15 or more - one source, tech-heavy.
"""
import json
import re
from pathlib import Path

import httpx

import store
from apply import questions

FILE = "apply-form.json"
ANSWER_KIND = {"written answer": "longtext", "choose one": "choice", "choose any": "multichoice",
               "yes / no": "yesno", "upload": "file"}
def fetch(client: httpx.Client, base: str, slug: str) -> dict | None:
    """The captured form, {"found": False} when none was, None when the job search can't say."""
    try:
        resp = client.get(f"{base}/jobs/{slug}/apply-form")
    except httpx.HTTPError:
        return None
    if resp.status_code == 404:
        return {"found": False, "fetched": store.utc_now()}
    if resp.status_code != 200:
        return None
    data = resp.json().get("data") or {}
    return {"found": True, "fetched": store.utc_now(), "provider": data.get("provider"),
            "basics": data.get("basics") or [], "questions": data.get("questions") or []}


def save(folder: Path, form: dict) -> None:
    (folder / FILE).write_text(json.dumps(form, indent=1, ensure_ascii=False), encoding="utf-8")


def load(folder: Path) -> dict | None:
    path = folder / FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def basic(title: str) -> tuple[str, str | None]:
    """A contact box or upload from `basics`: its kind + key, so the resume answers it."""
    t = title.casefold()
    if "cover letter" in t or re.search(r"\b(resume|cv)\b", t):
        return "file", questions.key_from_title(title, "file")
    for word in ("email", "phone", "location"):
        if word in t:
            return word, word
    return "text", questions.key_from_title(title, "text")


def as_questions(form: dict) -> list[dict]:
    """The captured boxes in the shape every system's questions share: contact boxes + uploads
    first (`basics`, b1..: name, email, resume - all but a cover letter required, as the page
    shows them), then the employer's questions (q1..). No options: the capture has none - the
    user picks the matching one on the page."""
    out = []
    for i, title in enumerate(form.get("basics") or [], 1):
        kind, key = basic(title)
        out.append(questions.question(f"b{i}", title, kind, key != "cover_letter", key=key))
    for i, q in enumerate(form.get("questions") or [], 1):
        kind = ANSWER_KIND.get(q.get("answer"), "text")
        out.append(questions.question(f"q{i}", q["text"], kind, bool(q.get("required")),
                                      key=questions.key_from_title(q["text"], kind)))
    return out


def asks_cover_letter(form: dict) -> bool:
    return any("cover letter" in t.casefold() for t in [*form.get("basics", []), *(q["text"] for q in form.get("questions", []))])


def summary(form: dict | None) -> list[str]:
    """Plain lines for Check before sending.md."""
    if not form or not form.get("found"):
        return ["Not known ahead - its questions show when you apply."]
    asked = form.get("questions") or []
    provider = (form.get("provider") or "").title()
    out = [f"Read ahead from the employer's {provider} form on {form['fetched'][:10]} - it may change; check on the page."]
    if not asked:
        out.append("Asks nothing beyond your resume and contact details.")
    else:
        written = sum(q.get("answer") == "written answer" for q in asked)
        out.append(f"Beyond your resume and contact details: {len(asked)} question(s)"
                   + (f", {written} written answer(s)" if written else "") + ".")
        about = {t for q in asked for t in questions.topics(q["text"])}
        about |= {kind for q in asked for kind, pattern in questions.SENSITIVE if pattern.search(q["text"].casefold())}
        if about:
            out.append("Asks about: " + ", ".join(t for t in [*(name for name, _ in questions.TOPICS), *(k for k, _ in questions.SENSITIVE)]
                                                  if t in about) + ".")
    if asks_cover_letter(form):
        out.append("Has a cover letter box.")
    if form.get("provider") == "lever":
        out.append("Lever doesn't publish which questions are required.")
    return out
