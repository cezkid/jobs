"""The answers file every application system shares: questions in one common shape, answered from
the resume and setup where they state it outright, the rest left for the AI to ask the user.

A system (`apply/systems/<name>.py`) turns its own form into these questions; everything below
works the same for every system. How to add one: app/docs/apply/apply-systems.md.
"""
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

from resume import render, schema

# what a question asks for, whatever the system calls it; a system maps each of its types to one
KINDS = {"text", "longtext", "email", "phone", "url", "number", "date", "location",
         "yesno", "choice", "multichoice", "file"}
# what a question is about when the system marks it (its own system field ids, or a title match)
KEYS = {"name", "first_name", "middle_name", "last_name", "legal_name", "legal_first", "legal_middle",
        "legal_last", "preferred_name", "preferred_first", "other_names", "email", "phone", "location",
        "resume", "cover_letter", "linkedin", "github", "website", "street", "city", "state", "zip", None}
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
# the time a work-break question asks about: "in the last 5 years", "past ten years", "since 2019"
WORD_NUMBER = {w: n for n, w in enumerate("one two three four five six seven eight nine ten".split(), 1)}
LAST_YEARS = re.compile(r"\b(?:last|past) (\d{1,2}|" + "|".join(WORD_NUMBER) + r") years?\b")
SINCE_YEAR = re.compile(r"\bsince ((?:19|20)\d\d)\b")
# a work-break question answered from the user's saved words: named, so the AI shows it before Submit
READ_FIRST = "read it before Submit"
# a form asking for every job: leaving the oldest off there is a false answer, so all of them go.
# Not "all employment decisions" (equal-opportunity text) nor "view all jobs" (site menus).
COMPLETE_HISTORY = re.compile(r"\b(complete|full|entire|whole) (\w+ )?(employment|work|job|career) history\b|"
                              r"\b(complete|full|entire) history of (your )?(employment|work)\b|"
                              r"\ball (of )?(your )?(previous|prior|past|former) (employers|employment|jobs|positions)\b|"
                              r"\b(all|every) (of )?(your )?employers?\b")
ASK_JOBS = ("ASK no jobs added yet - ask the user once: same {page} jobs as your resume, or all {all} jobs "
            "(the {left} left off ended {years}+ years ago; a form adds each with its dates). Save the answer as "
            "contact.form_jobs (page or all) in resume details, then run this again")
# pay, where they live, voluntary questions about them: the user's own answer only, never drafted
YOURS = "yours to answer"
# the AI marks an answer the user gave in the chat this way; a never-drafted or sensitive question
# answered under any other source is refused before anything is typed or pasted
USER_SAID = "you said"
# answers the program wrote itself; the user's own (via the AI) survive a second prepare
SAVED = "saved answer"
AUTO = ("resume", "search settings", SAVED)
NAME_PART = {"first": ("first", "given", "forename"), "middle": ("middle",), "last": ("last", "family", "surname")}
FILE = "application.json"


# terms, privacy, texts, e-signatures: accepting or signing is the applicant's own act, ticked or
# typed by them on the page - never drafted, kept or filled (2026-10-03: a start-page SMS consent
# Yes/No, a terms box + e-signature in one system's apply flow, consent checkboxes on another).
# Not "informed consent" (clinical work), "signed off", a certification held.
SIGNING_PATTERN = (r"terms (?:and|&) conditions|terms of (?:use|service)|privacy (?:policy|notice|statement)|"
                   r"(?<!informed )\bconsent|\bopt[- ]?in\b|\bi (?:hereby )?(?:agree|certify|attest|acknowledge|"
                   r"authori[sz]e|understand)\b|\bcertify\b|\battest\b|\backnowledg(?:e|ement)\b|"
                   r"\b(?:sms|text messag\w*|texts|automated (?:calls|messages))\b.{0,40}\b(?:receive|agree|consent)|"
                   r"\breceive (?:\w+ ){0,3}(?:sms|texts|text messages|automated calls)\b|"
                   r"\b(?:may|can) we (?:text|sms) you\b|(?<!digital )\bsignature\b|\be-?sign|"
                   r"\bsign (?:here|below|electronically)\b|\btype (?:your )?(?:full |legal )?name to sign\b")
SIGN_ON_PAGE = "yours to do on the page"


# what a question is about, in the user's words - the never-drafted ones first
TOPICS = (
    ("agreeing, consenting or signing", SIGNING_PATTERN),
    ("the pay you expect", r"salary|compensation|pay (?:expectation|range|requirement)|desired (?:pay|rate)"),
    ("permission to work", r"authori[sz]ed to work|right to work|work authori[sz]ation|legally (?:able|eligible|permitted)"),
    ("visa sponsorship", r"sponsor|\bvisa\b"),
    ("where you live", r"where (?:are you|do you) (?:live|located|based)|(?:state|country|city) of residence|"
                       r"currently (?:reside|located|live)"),
    ("voluntary questions about you", r"\bgender\b|\brace\b|ethnic|veteran|sexual orientation|pronoun"),
    ("working on site", r"on[- ]?site|in[- ]office|in the office|days (?:a|per) week|hybrid"),
    ("moving for the job", r"relocat"),
    ("your start date", r"start date|when can you start|available to start|notice period"),
    ("how you heard", r"how did you (?:hear|find|learn)|where did you (?:hear|find)"),
    ("being 18 or older", r"\b18 (?:years|or older)|over the age of 18|at least 18"),
)
# asked only of the user, never drafted - not even from a setting that seems to fit
VOLUNTARY = "voluntary questions about you"
NEVER_DRAFT = ("agreeing, consenting or signing", "the pay you expect", "where you live", VOLUNTARY)
SIGNING = "agreeing, consenting or signing"
# a voluntary question filled from the user's saved self-identification, after their yes to it
VOLUNTARY_SAVED = "your saved voluntary answer"



def topics(text: str) -> list[str]:
    return [name for name, pattern in TOPICS if re.search(pattern, text, re.I)]


def never_draft(text: str) -> str | None:
    return next((t for t in topics(text) if t in NEVER_DRAFT), None)


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
    # "Signature (type your full name)": their act on the page, never the name box
    if not ({"name", "names", "surname"} & set(words)) or OTHER_PERSON.search(t) or re.search(SIGNING_PATTERN, t):
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
    if kind == "file" and "cover letter" in t:
        return "cover_letter"
    if kind == "file" and re.search(r"\b(resume|résumé|cv)\b", t):
        return "resume"
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


def asks_complete_history(text: str) -> bool:
    return bool(COMPLETE_HISTORY.search(" ".join(text.casefold().split())))


def form_roles(master: dict, tailored: dict | None = None, complete: bool = False) -> tuple[list[dict], str | None]:
    """The jobs a form's work history gets, + a note for the AI. Tailoring may leave the oldest off
    the page (tailor.OLD_ROLE_YEARS); a form adding them with dates puts that age cue back. Same
    jobs as the page when the user chose it (contact.form_jobs: page); all when they chose all or
    the form asks for complete history. Unset -> none, and the note starting ASK asks, counts
    and all - never guessed."""
    roles = master.get("roles") or []
    shown = {e["id"] for e in (tailored or {}).get("entries") or []}
    page = [r for r in roles if r["id"] in shown] if shown else roles
    choice = (master.get("contact") or {}).get("form_jobs")
    if len(page) == len(roles) or choice == "all":
        return roles, None
    if complete:
        return roles, f"all {len(roles)} jobs: the form asks for complete work history - tell the user"
    if choice == "page":
        return page, None
    from resume import tailor
    return [], ASK_JOBS.format(page=len(page), all=len(roles), left=len(roles) - len(page), years=tailor.OLD_ROLE_YEARS)


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


def window_start(title: str, today: date) -> int | None:
    """First month a work-break question asks about, or None when it names no window (every break)."""
    t = " ".join(title.casefold().split())
    if m := LAST_YEARS.search(t):
        years = WORD_NUMBER.get(m[1]) or int(m[1])
        return schema.month_index(f"{today.year - years}-{today.month:02d}", today)
    if m := SINCE_YEAR.search(t):
        return schema.month_index(m[1], today)
    return None


def break_answer(q: dict, breaks: list[dict], today: date | None = None) -> str | None:
    """A work-break question in the user's own saved words (career_break explain), text boxes only.
    Breaks = those the question's window reaches ("last 5 years"), else all. Any of them without
    saved words, or none at all -> None, the user answers: part of the story reads as the whole of
    it. Several -> each after its dates, newest first."""
    if q["kind"] not in ("text", "longtext"):
        return None
    today = today or date.today()
    start = window_start(q["title"], today)
    asked = [b for b in schema.newest_first(breaks)
             if start is None or schema.month_index(b["end"], today, end=True) >= start]
    if not asked or any(not (b.get("explain") or "").strip() for b in asked):
        return None
    if len(asked) == 1:
        return asked[0]["explain"].strip()
    sep = "\n" if q["kind"] == "longtext" else " "
    return sep.join(f"{render.span_label(b)}: {b['explain'].strip()}" for b in asked)


def blank(answer) -> bool:
    return answer in (None, "", [])


def signs(text: str) -> bool:
    return never_draft(text) == SIGNING


def draft(qs: list[dict], contact: dict, old: list[dict] | None = None, config: dict | None = None,
          breaks: list[dict] | None = None, saved: list[dict] | None = None) -> list[dict]:
    """Questions + answers. Answers already written (an earlier prepare, or the AI) are kept -
    same id and same question only; on a sensitive question only the user's own, never one the
    program filled. The one sensitive kind the program fills: a work break, from words the user
    saved for it (`breaks`). Agreeing, consenting, signing: always left for the user on the page."""
    from apply import answers  # it reads this module's lists: imported at call time
    # generated page ids (rc_select_4, :r3:) can name another question on the next load: id + title
    kept = {(a["id"], answers.fold(a.get("title") or "")): a for a in old or [] if not blank(a.get("answer"))}
    out = []
    for q in qs:
        if signs(q["title"]):
            out.append({**q, "answer": None, "source": f"{ASK} - {SIGN_ON_PAGE}: {SIGNING}"})
            continue
        tag = sensitive(q, contact)
        was = kept.get((q["id"], answers.fold(q["title"])))
        if was and not (tag and was.get("source", "").startswith(AUTO)):
            out.append({**q, "answer": was["answer"], "source": was.get("source", "")})
            continue
        if tag == "work break" and (saved := break_answer(q, breaks or [])):
            out.append({**q, "answer": saved, "source": f"resume - sensitive: {tag} - {READ_FIRST}"})
            continue
        if tag:
            out.append({**q, "answer": None, "source": f"{ASK} - sensitive: {tag}"})
            continue
        home = (config or {}).get("home_address") or {}
        if q["key"] in ADDRESS and home.get(q["key"]):
            out.append({**q, "answer": str(home[q["key"]]), "source": "search settings - name it to the user"})
            continue
        hit = answers.recall(saved or [], q)
        if (topic := never_draft(q["title"])) == VOLUNTARY and (pick := voluntary_answer(q, config or {})):
            out.append({**q, "answer": pick, "source": f"search settings - {VOLUNTARY_SAVED} - name it to the user"})
            continue
        if topic:
            offer = f" - offer saved answer {hit[1]['answer']!r} ({answers.named(hit[1])})" if hit else ""
            out.append({**q, "answer": None, "source": f"{ASK} - {YOURS}: {topic}{offer}"})
            continue
        permit = work_permit(q, config or {})
        if permit is not None:
            out.append({**q, "answer": "Yes" if permit else "No", "source": "search settings - name it to the user"})
            continue
        answer = from_resume(q, contact)
        if not answer and hit:
            mode, entry = hit
            out.append({**q, "answer": entry["answer"], "source": f"{SAVED} - {answers.named(entry)} - name it to the user"}
                       if mode == "fill" else
                       {**q, "answer": None, "source": f"{ASK} - offer saved answer {entry['answer']!r} ({answers.named(entry)})"})
            continue
        source = names(contact)[1] if q["key"] in PLAIN_NAME else ASK
        out.append({**q, "answer": answer or None, "source": "resume" if answer else source})
    return out


SAME_GENDER = {"male": ("man",), "man": ("male",), "female": ("woman",), "woman": ("female",)}


def voluntary_answer(q: dict, config: dict) -> str | list[str] | None:
    """The user's saved self-identification (`self_identification` in search settings) as this
    question's option - only after they said yes to filling it on forms (`fill_on_forms: true`).
    Exactly one option must match, else None and the user is asked as before."""
    saved = config.get("self_identification") or {}
    if saved.get("fill_on_forms") is not True or not q["options"]:
        return None
    title, want = q["title"].casefold(), None
    if "veteran" in title and saved.get("protected_veteran") is not None:
        want = (lambda o: "not a protected veteran" in o) if saved["protected_veteran"] is False \
            else (lambda o: o.startswith("i identify as"))
    elif re.search(r"\bgender\b", title) and saved.get("gender"):
        said = str(saved["gender"]).casefold()
        same = {said, *SAME_GENDER.get(said, ())}  # "Male" saved, another list says "Man" (2026-10)
        want = lambda o: o in same
    elif re.search(r"\brace\b|ethnic|hispanic", title) and saved.get("hispanic_latino") is True:
        # "Hispanic or Latino" (EEOC), "Hispanic, Latinx, or Spanish Origin" (2026-10)
        want = lambda o: o.startswith("hispanic")
    hits = [o for o in q["options"] if want and want(o.casefold().strip())]
    if len(hits) != 1:
        return None
    return [hits[0]] if q["kind"] == "multichoice" else hits[0]


def asks_voluntary(answers: list[dict]) -> bool:
    return any(never_draft(a["title"]) == VOLUNTARY for a in answers)


def unvouched(answers: list[dict]) -> list[dict]:
    """Never-drafted or sensitive questions answered by anyone but the user (their source still
    says "ask the user"): the AI wrote them - refused, never typed or pasted."""
    return [a for a in answers if not blank(a.get("answer")) and (a.get("source") or "").startswith(ASK)
            and (f" - {YOURS}: " in a["source"] or " - sensitive: " in a["source"])]


def on_page(answers: list[dict]) -> list[dict]:
    """Agreeing, consenting or signing questions carrying an answer: never typed or ticked by the
    program, whoever wrote it - the user does it on the page."""
    return [a for a in answers if not blank(a.get("answer")) and signs(a["title"])]


def missing(answers: list[dict]) -> list[dict]:
    """Required and blank - not counting the ones the user ticks or signs on the page."""
    return [a for a in answers if a["required"] and blank(a.get("answer")) and not signs(a["title"])]


def load(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
