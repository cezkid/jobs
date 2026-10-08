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
# an Education section's boxes, answered from one school in Resume details (question entry = which one)
EDUCATION = {"school", "degree", "discipline", "school_start_month", "school_start_year", "school_end_month",
             "school_end_year"}
KEYS |= EDUCATION
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
# home address boxes, answered from `home_address` in search settings (never on the resume)
ADDRESS = {"street", "city", "state", "zip"}
# questions that are the user's to answer, never guessed (job-apply hard limits)
ASK = "ask the user"
# a plain Name box when the page name is not the legal one: the user picks once, contact.form_name keeps it
ASK_FORM_NAME = "ask the user once - legal name or the name on your resume"
# a name box about someone else (a referrer, a manager, the school) is never theirs to fill from contact;
# pronouns ask how to address them ("... just my first name", Manatal tenant 2026-10-06), not a name
OTHER_PERSON = re.compile(r"\brefer|manager|supervisor|emergency|reference|recruiter|employer|company|school|"
                          r"universit|college|spouse|relative|user ?name|business|organi[sz]ation|pronoun")
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
# a student's questions, answered from the school in progress on their resume. The expected date
# is on the page ("Expected May 2027") and career centres keep it early in career
# (fair-screening.md); a finished degree's date stays sensitive (age), and so does a bare "graduation
# date" - it may mean high school or an older degree
EXPECTED_GRADUATION = re.compile(r"\b(?:expected|anticipated|projected|estimated|planned) (?:\w+ ){0,2}?graduat|"
                                 r"\bexpect(?:ing)? to graduate\b|\bgraduat\w* (?:date|year)? ?\(?(?:expected|anticipated)")
GPA_QUESTION = re.compile(r"\bgpa\b|\bgrade point average\b")
# a GPA the resume doesn't hold: the major's, high school's, a weighted or one term's
GPA_OTHER = re.compile(r"\bmajor\b|high school|weighted|\bsemester\b|\bterm\b|\bquarter\b|\bgraduate school\b|\bscale\b")
ENROLLED = re.compile(r"\b(?:currently|presently) (?:enrolled|attending|a student|pursuing)\b|"
                      r"\bare you (?:a |currently a |currently )?(?:current )?(?:college |university )?student\b|\bstill (?:a )?student\b")
# enrolled how, or later: full or half time, returning after the internship - theirs to say
ENROLLED_OTHER = re.compile(r"full[- ]time|part[- ]time|half[- ]time|\breturn|next (?:semester|term|fall|year)|after the|\bduring\b")
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
# a multi-page system's fill result for a box on another page of the form: not a failure, filled
# once the user clicks Next / Continue and fill runs again (single-page systems: "FAIL ... not on page")
LATER = "LATER"


# terms, privacy, texts, e-signatures: accepting or signing is the applicant's own act, ticked or
# typed by them on the page - never drafted, kept or filled (2026-10-03: a start-page SMS consent
# Yes/No, a terms box + e-signature in one system's apply flow, consent checkboxes on another, a
# yes/no "Do you affirm that the information you've provided ... is true and complete?").
# Not "informed consent" (clinical work), "signed off", a certification held.
SIGNING_PATTERN = (r"terms (?:and|&) conditions|terms of (?:use|service)|privacy (?:policy|notice|statement)|"
                   r"(?<!informed )\bconsent|\bopt[- ]?in\b|\bi (?:hereby )?(?:agree|certify|attest|acknowledge|"
                   r"authori[sz]e|understand)\b|\bcertify\b|\battest\b|\baffirm\b|\backnowledg(?:e|e?ment)\b|"
                   r"\b(?:sms|text messag\w*|texts|automated (?:calls|messages))\b.{0,40}\b(?:receive|agree|consent)|"
                   r"\breceive (?:\w+ ){0,3}(?:sms|texts|text messages|automated calls)\b|"
                   r"\b(?:may|can) we (?:text|sms) you\b|\bpermission to (?:text|sms|message) you\b|(?<!digital )\bsignature\b|\be-?sign|"
                   r"\bsign (?:here|below|electronically)\b|\btype (?:your )?(?:full |legal )?name to sign\b")
SIGN_ON_PAGE = "yours to do on the page"
# "I confirm that my application materials ... were not generated, edited, or supplemented by AI
# tools" (2026-10-05, one Greenhouse tenant): a resume tailored here is AI help, so a drafted Yes is a
# false statement - left on the page like a signature, and prepare tells the AI to say how the resume
# was made. Needs AI words + making words + their own application: "experience with AI tools", "used
# AI to draft replies to customers" are skill questions.
AI_USE_PATTERN = (r"(?=[\s\S]*\b(?:AI|artificial intelligence|ChatGPT|GPT|LLMs?|large language models?|Gemini|Claude|"
                  r"Copilot)\b)"
                  r"(?=[\s\S]*\b(?:generat|writ|wrote|edit|supplement|assist|help|creat|produc|draft|us(?:e|ed|ing)\b))"
                  r"(?=[\s\S]*\b(?:my|your|this|these) (?:\w+ ){0,2}?(?:application|resume|résumé|cv|cover letter|"
                  r"responses|answers|materials|submission)s?\b)")


# what a question is about, in the user's words - the never-drafted ones first
TOPICS = (
    ("saying whether AI helped", AI_USE_PATTERN),
    ("agreeing, consenting or signing", SIGNING_PATTERN),
    ("the pay you expect", r"salary|compensation|pay (?:expectation|range|requirement)|desired (?:pay|rate)"),
    ("permission to work", r"authori[sz]ed to work|right to work|work authori[sz]ation|legally (?:able|eligible|permitted)"),
    ("visa sponsorship", r"sponsor|\bvisa\b"),
    ("where you live", r"where (?:are you|do you) (?:live|located|based)|(?:state|country|city) of residence|"
                       r"currently (?:reside|located|live)"),
    ("voluntary questions about you", r"\bgender\b|\brace\b|ethnic|veteran|sexual orientation|pronoun|transgender|"
                                      r"\blgbt|armed forces|military (?:status|service)|served in the military"),
    ("working on site", r"on[- ]?site|in[- ]office|in the office|days (?:a|per) week|hybrid"),
    ("moving for the job", r"relocat"),
    ("your start date", r"start date|when can you start|available to start|notice period"),
    ("how you heard", r"how did you (?:hear|find|learn)|where did you (?:hear|find)"),
    ("being 18 or older", r"\b18 (?:years|or older)|over the age of 18|at least 18"),
)
# asked only of the user, never drafted - not even from a setting that seems to fit
VOLUNTARY = "voluntary questions about you"
NEVER_DRAFT = ("saying whether AI helped", "agreeing, consenting or signing", "the pay you expect", "where you live",
               VOLUNTARY)
SIGNING = "agreeing, consenting or signing"
AI_USE = "saying whether AI helped"
# the applicant's own act on the page: never drafted, kept or filled, not even from "you said"
ON_PAGE = (AI_USE, SIGNING)
# a box whose question has no words (2026-10-05, one Ashby tenant: an untitled "I agree" tick whose
# consent words sat elsewhere): what it agrees to is unknown, so it is the applicant's on the page too
UNTITLED = "a box with no question words"
# a voluntary question filled from the user's saved self-identification, after their yes to it
VOLUNTARY_SAVED = "your saved voluntary answer"



def topics(text: str) -> list[str]:
    return [name for name, pattern in TOPICS if re.search(pattern, text, re.I)]


def never_draft(text: str) -> str | None:
    return next((t for t in topics(text) if t in NEVER_DRAFT), None)


def question(id: str, title: str, kind: str, required: bool, options=(), key=None, native=None,
             page: str | None = None, entry: int | None = None) -> dict:
    """One form question in the shared shape. `native` = the system's own type name, for its filler.
    `page` = which page of a multi-page form shows it: a section name the form's definition gives, or
    what identifies the page a system read it off (its step heading). `entry` = which school on the
    resume an Education box is for (0 = the first)."""
    assert kind in KINDS, kind
    assert key in KEYS, key
    out = {"id": id, "title": title, "kind": kind, "key": key, "native": native,
           "required": required, "options": list(options)}
    out |= {"page": page} if page else {}
    return out | {"entry": entry} if entry is not None else out


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
    """A profile link from the page's links, else one kept for forms only (contact.form_links)."""
    for url in (contact.get("links") or []) + (contact.get("form_links") or []):
        if host in url.casefold():
            return url if url.startswith("http") else "https://www." + url.removeprefix("www.")
    return ""


# profile sites a form asks for by name; any other link on the resume is the user's own website
PROFILE_HOSTS = ("linkedin.", "github.", "gitlab.", "twitter.", "x.com", "behance.", "dribbble.", "medium.")


def website(contact: dict) -> str:
    """The resume's own site (example.com -> https://www.example.com), never a profile link."""
    for url in contact.get("links") or []:
        if not any(h in url.casefold() for h in PROFILE_HOSTS):
            return link(contact, url.casefold())
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
        "website": website(contact),
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
        # a visa holder's permit has limits - CPT/OPT their field and dates, H-1B one employer - and
        # international offices (CMU, UCI) say "No" here: asked every time, even over a Yes saved
        # before this rule (setup's old "allowed now, sponsorship later" option saved one)
        if wa.get("needs_sponsorship") or wa.get("student_visa"):
            return None
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


def degree_option(written: str, options: list[str]) -> str | None:
    """The resume's degree as the form's list words it: its own wording or spelled out ("BA" ->
    "Bachelor of Arts"), the one option naming it with its letters ("PhD" -> "Doctor of Philosophy
    (Ph.D.)"), the longest option it starts with ("High School Diploma" -> "High School"), else its
    family ("BA" -> "Bachelor's Degree"); none -> None, the user picks."""
    from apply import profile  # it imports this module: imported at call time
    full = render.degree_name(written)
    folded = {o.casefold(): o for o in options}
    if hit := folded.get(written.casefold()) or folded.get(full.casefold()):
        return hit
    lettered = [o for o in options if o.casefold().startswith(full.casefold() + " (")]
    if len(lettered) == 1:
        return lettered[0]
    if hit := major_option(full, options):
        return hit
    return next((folded[f.casefold()] for f in profile.DEGREE_FAMILY.get(full.split()[0] if full else "", [])
                 if f.casefold() in folded), None)


def major_option(field: str, options: list[str]) -> str | None:
    """Exact major, or the longest option the field starts with ('Art Education in School and
    Community' -> 'Art Education'); none -> None, never a partial word or a catch-all."""
    f = field.casefold().strip()
    fits = [o for o in options if f == o.casefold() or f.startswith(o.casefold() + " ")]
    return max(fits, key=len) if fits else None


def school_answer(q: dict, schools: list[dict]) -> tuple[str | None, str]:
    """One Education box from school q["entry"] on the resume -> (answer, source). Degree and
    discipline as the form's list words them (a free-text box: as written); the graduation date only as the page shows it (hidden
    by the user's choice -> left blank, or asked as sensitive when required); a start date from the
    school's start when on file (never with its years hidden), else asked."""
    entry = q.get("entry") or 0
    school = schools[entry] if entry < len(schools) else {}
    unsaid = (None, f"{ASK} - not on your resume") if q["required"] else (None, "not on your resume - left blank")
    key = q["key"]
    if key == "school":
        return (school["institution"], "resume") if school.get("institution") else unsaid
    if key in ("degree", "discipline"):
        written = (school.get("degree" if key == "degree" else "field") or "").strip()
        if not written:
            return unsaid
        if q["kind"] == "text":  # a free-text box (Ashby): the resume's words, its degree spelled out
            return (render.degree_name(written) if key == "degree" else written), "resume"
        pick =(degree_option if key == "degree" else major_option)(written, q["options"])
        if pick is None:
            return None, f"{ASK} - '{written}' isn't on the form's list: the nearest option is theirs to pick"
        return pick, "resume" if pick.casefold() == written.casefold() else \
            f"resume - '{written}' as the form's nearest option - name it to the user"
    if key in ("school_start_month", "school_start_year") and schema.shown_start(school):
        year, _, month = schema.shown_start(school).partition("-")
        value = year if key == "school_start_year" else MONTHS[int(month) - 1] if month.isdigit() else None
        return (value, "resume") if value else unsaid
    if key in ("school_end_month", "school_end_year"):
        if school.get("hide_year") and school.get("end"):
            return (None, f"{ASK} - sensitive: graduation date") if q["required"] else \
                (None, "left off your resume (your choice) - left blank")
        year, _, month = schema.shown_end(school).partition("-")
        value = year if key == "school_end_year" else MONTHS[int(month) - 1] if month.isdigit() else None
        return (value, "resume") if year.isdigit() and value else unsaid
    return unsaid


def student_answer(q: dict, schools: list[dict], today: date) -> tuple | None:
    """(answer, source) for an expected graduation date, a GPA or "currently enrolled?", from the
    school in progress (else, for a GPA, the latest one carrying it); None = not one of these, or
    nothing to answer from - the question goes on as any other (asked)."""
    title = " ".join(q["title"].casefold().split())
    studying = [s for s in schools if schema.in_progress(s, today)]
    if EXPECTED_GRADUATION.search(title):
        if len(studying) != 1 or not schema.shown_end(studying[0]):
            return None if len(studying) == 1 else (None, f"{ASK} - expected graduation: "
                                                         f"{'none in progress' if not studying else 'two degrees in progress'} on your resume")
        end = schema.shown_end(studying[0])
        words = [render.month_label(end), end[:4]]
        if q["kind"] in ("choice", "multichoice"):
            pick = next((o for w in words for o in q["options"] if o.casefold() == w.casefold()), None)
            return (pick, f"resume - {READ_FIRST}") if pick else (None, f"{ASK} - expected graduation: "
                                                                         f"{words[0]} isn't on the form's list")
        if q["kind"] not in ("text", "longtext"):
            return None, f"{ASK} - expected graduation {words[0]} (a date box: theirs to enter)"
        return words[0], f"resume - {READ_FIRST}"
    if GPA_QUESTION.search(title) and not GPA_OTHER.search(title):
        school = next((s for s in [*studying, *schools] if s.get("gpa")), None)
        if school is None:
            return None
        gpa, four = school["gpa"].strip(), schema.FOUR_POINT.match(school["gpa"].strip())
        # the transcript's own figure, never converted from another scale or rounded
        if q["kind"] == "number":
            return (four["gpa"], "resume - name it to the user") if four else \
                (None, f"{ASK} - GPA {gpa!r} is on another scale: never converted")
        if q["kind"] in ("choice", "multichoice"):
            pick = gpa_option(float(four["gpa"]), q["options"]) if four else None
            return (pick, "resume - name it to the user") if pick else (None, f"{ASK} - GPA {gpa!r}: no option holds it")
        return gpa, "resume - name it to the user"
    if q["kind"] == "yesno" and ENROLLED.search(title) and not ENROLLED_OTHER.search(title):
        return ("Yes", "resume - degree in progress - name it to the user") if studying else None
    return None


def gpa_option(gpa: float, options: list[str]) -> str | None:
    """The one option whose range holds the GPA: "3.5 - 3.74", "3.0-3.49", "3.5+", "Below 3.0"."""
    fits = []
    for o in options:
        nums = [float(n) for n in re.findall(r"\d(?:\.\d+)?", o)]
        low = o.casefold()
        if len(nums) == 2 and nums[0] <= gpa <= nums[1]:
            fits.append(o)
        elif len(nums) == 1 and (("+" in o or "above" in low or "higher" in low or "or more" in low) and gpa >= nums[0]
                                 or ("below" in low or "under" in low or "less" in low) and gpa < nums[0]
                                 or abs(gpa - nums[0]) < 1e-9):
            fits.append(o)
    return fits[0] if len(fits) == 1 else None


def blank(answer) -> bool:
    return answer in (None, "", [])


def signs(text: str) -> bool:
    """The applicant's own act on the page: agreeing, signing, saying whether AI helped - or a box
    with no words on it, which nobody but the person reading the page can answer."""
    return not text.strip() or never_draft(text) in ON_PAGE


def why_on_page(text: str) -> str:
    """What a box `signs` is, in the user's words."""
    return never_draft(text) or (SIGNING if text.strip() else UNTITLED)


def left_on_page(q: dict) -> str:
    """A filler's result for a question the user ticks or signs on the page themselves."""
    return f"ASK {SIGN_ON_PAGE} - {why_on_page(q['title'])}"


def draft(qs: list[dict], contact: dict, old: list[dict] | None = None, config: dict | None = None,
          breaks: list[dict] | None = None, saved: list[dict] | None = None,
          schools: list[dict] | None = None) -> list[dict]:
    """Questions + answers. Answers already written (an earlier prepare, or the AI) are kept -
    same id and same question only; on a sensitive question only the user's own, never one the
    program filled. The one sensitive kind the program fills: a work break, from words the user
    saved for it (`breaks`). Agreeing, consenting, signing, saying whether AI helped: always left
    for the user on the page. Education boxes: from `schools` (Resume details education)."""
    from apply import answers  # it reads this module's lists: imported at call time
    # generated page ids (rc_select_4, :r3:) can name another question on the next load: id + title
    kept = {(a["id"], answers.fold(a.get("title") or "")): a for a in old or [] if not blank(a.get("answer"))}
    out = []
    for q in qs:
        if signs(q["title"]):
            out.append({**q, "answer": None, "source": f"{ASK} - {SIGN_ON_PAGE}: {why_on_page(q['title'])}"})
            continue
        tag = sensitive(q, contact)
        was = kept.get((q["id"], answers.fold(q["title"])))
        if was and not (tag and was.get("source", "").startswith(AUTO)):
            out.append({**q, "answer": was["answer"], "source": was.get("source", "")})
            continue
        if q["key"] in EDUCATION:
            answer, source = school_answer(q, schools or [])
            out.append({**q, "answer": answer, "source": source})
            continue
        if (said := student_answer(q, schools or [], date.today())) is not None:
            out.append({**q, "answer": said[0], "source": said[1]})
            continue
        if tag == "work break" and (saved := break_answer(q, breaks or [])):
            out.append({**q, "answer": saved, "source": f"resume - sensitive: {tag} - {READ_FIRST}"})
            continue
        # the user's saved disability answer, after their yes to filling it: still a sensitive kind, read back
        if tag == "disability or health" and voluntary_kind(q) == "disability" and \
                (pick := voluntary_answer(q, config or {})):
            out.append({**q, "answer": pick, "source": f"search settings - {VOLUNTARY_SAVED} - sensitive: {tag} - "
                                                       f"{READ_FIRST}"})
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
SAME_ORIENTATION = {"heterosexual": ("straight",), "straight": ("heterosexual",)}
# serving in the armed forces at all - not the EEOC protected-veteran list ("Veteran Status"), though
# both titles can say "veteran": "Are you a veteran or active member of the United States Armed
# Forces?", "What is your military status?" (Greenhouse surveys, 2026-10-05)
ARMED_FORCES = re.compile(r"armed forces|\bmilitary\b|active (?:duty|member)")
# a disability self-identification, not "will you need a reasonable accommodation?" nor the
# "disabled veteran" in a protected-veteran list's text
DISABILITY = re.compile(r"\bdisabilit|\bdisabled\b(?! veteran)")
# the EEOC protected-veteran options, whatever the title says (its text can name "active duty ...
# Armed Forces service medal veteran")
EEOC_VETERAN = re.compile(r"not a protected veteran|classifications of (?:a )?protected veteran")


def says(option: str, yes: bool) -> bool:
    """A Yes or No option, bare or worded: "No, I do not have a disability ...", "No military service"."""
    return re.match(r"yes\b" if yes else r"no\b", option) is not None


def parts(option: str) -> set[str]:
    """An option and the words it joins: "Straight/Heterosexual", "Bisexual and/or pansexual"."""
    return {option, *filter(None, re.split(r"\s*(?:[/,()]|\band\b|\bor\b)\s*", option))}


def voluntary_kind(q: dict) -> str | None:
    """The `self_identification` key a question asks about - exactly one, else None (asked)."""
    t = q["title"].casefold()
    eeoc = any(EEOC_VETERAN.search(o.casefold()) for o in q.get("options") or [])
    found = [key for key, asks in (
        ("armed_forces", ARMED_FORCES.search(t) and not eeoc),
        ("protected_veteran", "veteran" in t and (eeoc or not ARMED_FORCES.search(t))),
        ("transgender", "transgender" in t),
        ("gender", re.search(r"\bgender\b", t)),
        ("sexual_orientation", re.search(r"\borientation\b", t)),
        ("hispanic_latino", re.search(r"\brace\b|ethnic|hispanic", t)),
        ("disability", DISABILITY.search(t) and "accommodat" not in t)) if asks]
    return found[0] if len(found) == 1 else None


def voluntary_answer(q: dict, config: dict) -> str | list[str] | None:
    """The user's saved self-identification (`self_identification` in search settings) as this
    question's option - only after they said yes to filling it on forms (`fill_on_forms: true`).
    Exactly one option must match, else None and the user is asked as before. Option wordings:
    `app/docs/apply/answers.md` #Saved voluntary answers."""
    saved = config.get("self_identification") or {}
    if saved.get("fill_on_forms") is not True or not q["options"]:
        return None
    key = voluntary_kind(q)
    said, want = saved.get(key) if key else None, None
    if key == "protected_veteran" and isinstance(said, bool):
        want = (lambda o: "not a protected veteran" in o) if said is False else (lambda o: o.startswith("i identify as"))
    elif key == "armed_forces" and isinstance(said, bool):
        # "Yes, I am a veteran or active member" / "I am a veteran or active member"; "No, I am not a
        # veteran or active member", "I have never served in the military", "No military service"
        want = (lambda o: says(o, True) or o.startswith("i am a veteran")) if said else \
            (lambda o: says(o, False) or re.search(r"\bnot a veteran\b|\bnever served\b", o) is not None)
    elif key in ("transgender", "disability") and isinstance(said, bool):
        # "Yes" / "No"; "No, I do not have a disability and have not had one in the past" (EEOC)
        want = lambda o: says(o, said)
    elif key == "gender" and said:
        said = str(said).casefold()
        same = {said, *SAME_GENDER.get(said, ())}  # "Male" saved, another list says "Man" (2026-10)
        want = lambda o: o in same
    elif key == "sexual_orientation" and said:
        said = str(said).casefold()
        same = {said, *SAME_ORIENTATION.get(said, ())}
        want = lambda o: bool(parts(o) & same)
    elif key == "hispanic_latino" and said is True:
        # "Hispanic or Latino" (EEOC), "Hispanic, Latinx, or Spanish Origin" (2026-10)
        want = lambda o: o.startswith("hispanic")
    hits = [o for o in q["options"] if want and want(o.casefold().strip())]
    if len(hits) != 1:
        return None
    return [hits[0]] if q["kind"] == "multichoice" else hits[0]


def asks_voluntary(answers: list[dict]) -> bool:
    """A question the saved self-identification could answer: a voluntary one, or disability."""
    return any(never_draft(a["title"]) == VOLUNTARY or voluntary_kind(a) == "disability" for a in answers)


def unvouched(answers: list[dict]) -> list[dict]:
    """Never-drafted or sensitive questions answered by anyone but the user (their source still
    says "ask the user"): the AI wrote them - refused, never typed or pasted."""
    return [a for a in answers if not blank(a.get("answer")) and (a.get("source") or "").startswith(ASK)
            and (f" - {YOURS}: " in a["source"] or " - sensitive: " in a["source"])]


def on_page(answers: list[dict]) -> list[dict]:
    """Agreeing, consenting, signing or AI-use questions carrying an answer: never typed or ticked
    by the program, whoever wrote it - the user does it on the page."""
    return [a for a in answers if not blank(a.get("answer")) and signs(a["title"])]


def merge(old: list[dict], read: list[dict]) -> list[dict]:
    """Questions read off the page the user is on, merged into the answers file of the same form:
    other pages' entries kept as they are, this page's replaced in place, a page not seen before
    appended. Questions without a page (a whole form read at once) replace everything."""
    pages, ids = {q.get("page") for q in read}, {q["id"] for q in read}
    if None in pages:
        return read
    out, placed = [], False
    for a in old:
        if a.get("page") in pages or a["id"] in ids:
            out += [] if placed else read
            placed = True
        else:
            out.append(a)
    return out if placed else out + read


def missing(answers: list[dict]) -> list[dict]:
    """Required and blank - not counting the ones the user ticks, signs or chose to type on the page
    (source marked SIGN_ON_PAGE: 2026-10-08, a user writing their own "why join us" on the page)."""
    return [a for a in answers if a["required"] and blank(a.get("answer")) and not signs(a["title"])
            and SIGN_ON_PAGE not in (a.get("source") or "")]


def load(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
