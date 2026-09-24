"""The answers file every application system shares: questions in one common shape, answered from
the resume and setup where they state it outright, the rest left for the AI to ask the user.

A system (`apply/systems/<name>.py`) turns its own form into these questions; everything below
works the same for every system. How to add one: app/docs/apply/apply-systems.md.
"""
import json
from pathlib import Path

# what a question asks for, whatever the system calls it; a system maps each of its types to one
KINDS = {"text", "longtext", "email", "phone", "url", "number", "date", "location",
         "yesno", "choice", "multichoice", "file"}
# what a question is about when the system marks it (its own system field ids, or a title match)
KEYS = {"name", "first_name", "last_name", "email", "phone", "location", "resume",
        "linkedin", "github", "website", None}
# questions that are the user's to answer, never guessed (job-apply hard limits)
ASK = "ask the user"
FILE = "application.json"


def question(id: str, title: str, kind: str, required: bool, options=(), key=None, native=None) -> dict:
    """One form question in the shared shape. `native` = the system's own type name, for its filler."""
    assert kind in KINDS, kind
    assert key in KEYS, key
    return {"id": id, "title": title, "kind": kind, "key": key, "native": native,
            "required": required, "options": list(options)}


def key_from_title(title: str, kind: str) -> str | None:
    """Link boxes are the employer's own questions on most systems: recognise them by title."""
    t = title.casefold()
    if kind in ("text", "url"):
        for key in ("linkedin", "github"):
            if key in t:
                return key
        if "website" in t or "portfolio" in t:
            return "website"
    return None


def link(contact: dict, host: str) -> str:
    for url in contact.get("links") or []:
        if host in url.casefold():
            return url if url.startswith("http") else "https://www." + url.removeprefix("www.")
    return ""


def from_resume(q: dict, contact: dict) -> str:
    """Answer only what the resume states outright. Location stays the user's: a resume says
    "City Area", forms want the town they live in."""
    name = (contact.get("name") or "").split()
    by_key = {
        "name": contact.get("name", ""),
        "first_name": name[0] if name else "",
        "last_name": " ".join(name[1:]),
        "email": contact.get("email", ""),
        "phone": contact.get("phone", ""),
        "linkedin": link(contact, "linkedin."),
        "github": link(contact, "github."),
    }
    if q["key"] in by_key:
        return by_key[q["key"]]
    if q["kind"] == "email":
        return contact.get("email", "")
    if q["kind"] == "phone":
        return contact.get("phone", "")
    return ""


def work_permit(q: dict, config: dict):
    """Setup's two work-permit answers, only for the same US question asked the same way."""
    wa, title = config.get("work_authorization") or {}, q["title"].casefold()
    if q["kind"] != "yesno":
        return None
    if "authorized to work in the u" in title and "without restriction" in title:
        return wa.get("authorized_us")
    if "sponsorship" in title and "future" in title and ("u.s." in title or "us" in title.split()):
        return wa.get("needs_sponsorship")
    return None


def blank(answer) -> bool:
    return answer in (None, "", [])


def draft(qs: list[dict], contact: dict, old: list[dict] | None = None, config: dict | None = None) -> list[dict]:
    """Questions + answers. Answers already written (an earlier prepare, or the AI) are kept."""
    kept = {a["id"]: a for a in old or [] if not blank(a.get("answer"))}
    out = []
    for q in qs:
        if q["id"] in kept:
            out.append({**q, "answer": kept[q["id"]]["answer"], "source": kept[q["id"]].get("source", "")})
            continue
        permit = work_permit(q, config or {})
        if permit is not None:
            out.append({**q, "answer": "Yes" if permit else "No", "source": "search settings - name it to the user"})
            continue
        answer = from_resume(q, contact)
        out.append({**q, "answer": answer or None, "source": "resume" if answer else ASK})
    return out


def missing(answers: list[dict]) -> list[dict]:
    return [a for a in answers if a["required"] and blank(a.get("answer"))]


def load(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
