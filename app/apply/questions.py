"""The answers file every application system shares: questions in one common shape, answered from
the resume and setup where they state it outright, the rest left for the AI to ask the user.

A system (`apply/systems/<name>.py`) turns its own form into these questions; everything below
works the same for every system. How to add one: app/docs/apply/apply-systems.md.
"""
import json
import re
import unicodedata
from pathlib import Path

# what a question asks for, whatever the system calls it; a system maps each of its types to one
KINDS = {"text", "longtext", "email", "phone", "url", "number", "date", "location",
         "yesno", "choice", "multichoice", "file"}
# what a question is about when the system marks it (its own system field ids, or a title match)
KEYS = {"name", "first_name", "middle_name", "last_name", "legal_name", "legal_first", "legal_middle",
        "legal_last", "preferred_name", "preferred_first", "other_names", "email", "phone", "location",
        "resume", "linkedin", "github", "website", "street", "city", "state", "zip", None}
# home address boxes, answered from `home_address` in search settings (never on the resume)
ADDRESS = {"street", "city", "state", "zip"}
# questions that are the user's to answer, never guessed (job-apply hard limits)
ASK = "ask the user"
# a plain Name box when the page name is not the legal one: the user picks once, contact.form_name keeps it
ASK_FORM_NAME = "ask the user once - legal name or the name on your resume"
# a name box about someone else (a referrer, a manager, the school) is never theirs to fill from contact
OTHER_PERSON = re.compile(r"\brefer|manager|supervisor|emergency|reference|recruiter|employer|company|school|"
                          r"universit|college|spouse|relative|user ?name|business|organi[sz]ation")
PLAIN_NAME = {"name", "first_name", "middle_name", "last_name"}
# questions only the user answers, however well a saved answer seems to fit: the AI names the kind and
# asks (fair-screening.md). "Are you 18 or older?" is not one - a plain yes/no, answered truthfully.
SENSITIVE = [
    ("date of birth", re.compile(r"\bdate of birth\b|\bbirth ?date\b|\bbirthday\b|\bd\.?o\.?b\b")),
    ("graduation date", re.compile(r"\bgraduation (date|year)|\b(date|year)s? (of |you )?graduat|"
                                   r"\b(when|year) did you graduate|\bgrad(uation)? (yr|year)")),
    ("criminal history", re.compile(r"\bcriminal\b(?! (justice|law|defen[cs]e|investigat))|\bconvict(ed|ions?)\b|"
                                    r"\bfelon(y|ies)\b|\bmisdemeanou?rs?\b|(?<!cardiac )\barrest(ed|s)?\b|"
                                    r"\bpleaded guilty|\bpled guilty|\bno contest\b")),
    ("work break", re.compile(r"\b(gaps?|breaks?) (in|between) (your )?(employment|work|career|jobs)|"
                              r"\b(employment|career|work history) (gaps?|breaks?)\b|\bunemploy|"
                              r"\bexplain any gaps\b")),
    ("disability or health", re.compile(r"\bdisabilit|\bdisabled\b|\bimpairment|reasonable accommodation|"
                                        r"\b(medical|health|mental health) (condition|history|issue|problem)s?\b")),
]
# answers the program wrote itself; the user's own (via the AI) survive a second prepare
AUTO = ("resume", "search settings")
NAME_PART = {"first": ("first", "given", "forename"), "middle": ("middle",), "last": ("last", "family", "surname")}
FILE = "application.json"


def question(id: str, title: str, kind: str, required: bool, options=(), key=None, native=None) -> dict:
    """One form question in the shared shape. `native` = the system's own type name, for its filler."""
    assert kind in KINDS, kind
    assert key in KEYS, key
    return {"id": id, "title": title, "kind": kind, "key": key, "native": native,
            "required": required, "options": list(options)}


def name_key(title: str) -> str | None:
    """Which of the user's names a box asks for. Labelled legal or for a background check -> legal
    name; preferred -> the name on the page; other / previous / maiden -> other names used."""
    t = title.casefold()
    words = re.findall(r"[a-z]+", t)
    if not ({"name", "names", "surname"} & set(words)) or OTHER_PERSON.search(t):
        return None
    if {"other", "previous", "former", "prior", "maiden", "alias", "aliases"} & set(words):
        return "other_names"
    parts = [p for p, said in NAME_PART.items() if set(said) & set(words)]
    part = parts[0] if len(parts) == 1 else None  # "Name (first and last)" is the whole name
    if "legal" in words or "background" in words:
        return f"legal_{part}" if part else "legal_name"
    if "preferred" in words or "nickname" in words or "go by" in t:
        return "preferred_first" if part == "first" else "preferred_name" if part is None else None
    if part:
        return f"{part}_name"
    return "name" if parts or set(words) <= {"name", "full", "your"} else None


def key_from_title(title: str, kind: str) -> str | None:
    """Link + name boxes are the employer's own questions on most systems: recognise them by title."""
    t = title.casefold()
    if kind == "text" and (key := name_key(title)):
        return key
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


def same_name(a: str, b: str) -> bool:
    """José / JOSE / jose are one name: accents, case and spacing never make a mismatch."""
    def fold(s: str) -> str:
        return " ".join("".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
                        .casefold().split())
    return fold(a) == fold(b)


def initial(word: str) -> bool:
    return len(word.rstrip(".")) == 1


def split(name: str, initials_ok: bool) -> tuple[str, str] | None:
    """First + last only when the name says it outright: two words. "Mary Ann Smith" could be
    Mary Ann / Smith or Mary / Ann Smith, and an initial on the page is rarely what a form wants."""
    words = name.split()
    if len(words) == 2 and (initials_ok or not any(initial(w) for w in words)):
        return words[0], words[1]
    return None


def names(contact: dict) -> tuple[dict, str]:
    """The answer for every name box, and where a blank plain Name / First / Last box goes. Legal
    name only from the user's own legal fields; a plain box gets it only when it is the page name
    or they chose it (contact.form_name)."""
    page = (contact.get("name") or "").strip()
    first, middle, last = (contact.get(f"legal_{p}") or "" for p in ("first", "middle", "last"))
    one = len(page.split()) == 1  # a mononym: first name only, no last name to give
    pair = (page, "") if one else split(page, initials_ok=False) or ("", "")
    out = {"name": page, "preferred_name": page, "preferred_first": pair[0],
           "other_names": ", ".join(contact.get("other_names") or [])}
    if not (first and last):
        return out | {"first_name": pair[0], "last_name": pair[1]}, ASK
    legal = " ".join(w for w in (first, middle, last) if w)
    out |= {"legal_name": legal, "legal_first": first, "legal_middle": middle, "legal_last": last}
    choice = contact.get("form_name")
    if choice == "legal" or same_name(page, legal) or same_name(page, f"{first} {last}"):
        return out | {"name": legal if choice == "legal" else page, "first_name": first, "middle_name": middle,
                      "last_name": last}, ASK
    if choice == "page":
        chosen = (page, "") if one else split(page, initials_ok=True) or ("", "")
        return out | {"first_name": chosen[0], "last_name": chosen[1]}, ASK
    return out | {"name": ""}, ASK_FORM_NAME


def from_resume(q: dict, contact: dict) -> str:
    """Answer only what the resume states outright. Location stays the user's: a resume says
    "City Area", forms want the town they live in."""
    by_key = {
        **names(contact)[0],
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
    """Setup's work-permit answers, only for the same US question asked the same way."""
    wa, title = config.get("work_authorization") or {}, q["title"].casefold()
    us = "u.s." in title or "us" in title.split() or "united states" in title
    if q["kind"] != "yesno":
        return None
    if "authorized to work in the u" in title and "without restriction" in title:
        return wa.get("authorized_us")
    if "sponsorship" in title and "future" in title and us:
        return wa.get("needs_sponsorship")
    # another country's "citizen or permanent resident" is a different question
    if "citizen" in title and ("green card" in title or ("permanent resident" in title and us)):
        return wa.get("citizen_or_permanent_resident")
    return None


def sensitive(q: dict, contact: dict) -> str | None:
    """What a sensitive question is about, or None. Other names count only when the user saved none:
    saved ones are theirs to give (resume details)."""
    title = " ".join(q["title"].casefold().split())
    if "other_names" in (q["key"], name_key(q["title"])) and not contact.get("other_names"):
        return "other names"
    # a yes/no on the birth date ("does it make you 18 or older?") is an age check, not the date itself
    return next((kind for kind, pattern in SENSITIVE if pattern.search(title)
                 and not (kind == "date of birth" and q["kind"] == "yesno")), None)


def blank(answer) -> bool:
    return answer in (None, "", [])


def draft(qs: list[dict], contact: dict, old: list[dict] | None = None, config: dict | None = None) -> list[dict]:
    """Questions + answers. Answers already written (an earlier prepare, or the AI) are kept -
    on a sensitive question only the user's own, never one the program filled."""
    kept = {a["id"]: a for a in old or [] if not blank(a.get("answer"))}
    out = []
    for q in qs:
        tag = sensitive(q, contact)
        if q["id"] in kept and not (tag and kept[q["id"]].get("source", "").startswith(AUTO)):
            out.append({**q, "answer": kept[q["id"]]["answer"], "source": kept[q["id"]].get("source", "")})
            continue
        if tag:
            # plan-1fw.6 hook: a break explanation the user saved (career_break explain) fills "work break" here
            out.append({**q, "answer": None, "source": f"{ASK} - sensitive: {tag}"})
            continue
        home = (config or {}).get("home_address") or {}
        if q["key"] in ADDRESS and home.get(q["key"]):
            out.append({**q, "answer": str(home[q["key"]]), "source": "search settings - name it to the user"})
            continue
        permit = work_permit(q, config or {})
        if permit is not None:
            out.append({**q, "answer": "Yes" if permit else "No", "source": "search settings - name it to the user"})
            continue
        answer = from_resume(q, contact)
        source = names(contact)[1] if q["key"] in PLAIN_NAME else ASK
        out.append({**q, "answer": answer or None, "source": "resume" if answer else source})
    return out


def missing(answers: list[dict]) -> list[dict]:
    return [a for a in answers if a["required"] and blank(a.get("answer"))]


def load(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
