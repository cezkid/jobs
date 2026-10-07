"""Minimum asks a resume visibly doesn't meet: years of experience, a degree. Report only.

Knock-out questions are real but narrow (docs/resume/bullets.md Tier 3): work authorisation,
licences, location, minimum qualifications. Before tailoring, the user hears which minimum asks
their resume details fall short of, quoted from the posting, and decides. Never a score, never a
block, never said when either side has no data.

Read off a required line only. Years: the lower bound of what's asked ("3-5 years" -> 3) vs whole
years the dated jobs add up to, overlaps merged - short in total means short in any specialty, so
the statement is always true; "18 years of age", "within 1 year of hire" are not experience.
Degree: the lowest level a line names vs the highest listed; "or equivalent", professional
doctorates (JD, MD...), students ("currently pursuing") and wishes ("MBA a plus") say nothing.
Measured 2026-10-01 on 104 live postings (healthcare, finance, education, software): 668 required
lines, 51 years + 24 degree reads, 0 misread by hand check (4 misreads fixed before: "master your
craft", "MBA a plus", "currently pursuing", "experience within an e-commerce environment").
"""
import re
from datetime import date

from resume import render, schema

WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
         "ten": 10, "twelve": 12, "fifteen": 15}
NUM = r"(\d{1,2}|" + "|".join(WORDS) + r")"
YEARS = re.compile(rf"\b{NUM}\s*(?:\+|plus)?\s*(?:(?:-|–|to|or)\s*{NUM}\s*\+?\s*)?(?:full[- ]time\s+)?(?:years?|yrs?)\b"
                   r"(?!\s+(?:of\s+age|old|ago))", re.I)
NOT_WORK = re.compile(rf"\bwithin\s+(?:\(?{NUM}\)?\s*)+(?:years?|months?)|\bevery\b|\bper\b|of age\b|\byears? old\b|"
                      r"\bago\b|\bcommit", re.I)
# school, not work: "2 years of undergraduate study", "two years of college", "coursework" ("work" in it)
STUDY = re.compile(r"\bcoursework\b|\bdegree program\b|\b(?:undergraduate|college|university|graduate|academic)\s+"
                   r"(?:study|studies|education|program)\b|\byears?\s+of\s+(?:college|university|school|study|"
                   r"undergraduate|graduate school)\b", re.I)
WORK = re.compile(r"experience|working|\bwork\b|professional|industry|background|practice|clinical", re.I)
AFTER = re.compile(r"\s*(?:of|in|as|with|working|doing|building|developing|leading|managing|designing|teaching|"
                   r"supporting|selling|providing)\b", re.I)
LADDER = ("high school", "associate's", "bachelor's", "master's", "doctorate")
ASKED = (
    ("doctorate", r"\bph\.?\s?d\b|\bdoctorate\b|\bdoctoral\b"),
    ("master's", r"\bmaster'?s\b|\bmasters? (?:degree|of)\b|\bmba\b|\bm\.s\.|\bms degree\b|\bmsn\b|\bm\.?ed\b"),
    ("bachelor's", r"\bbachelor'?s?\b|\bb\.s\.|\bb\.a\.|\bbs\b(?= (?:degree|in))|\bba\b(?= (?:degree|in))|\bbsn\b|"
                   r"\b(?:4|four)[- ]year (?:college )?degree\b|\bundergraduate degree\b|\bcollege degree\b"),
    ("associate's", r"\bassociate'?s? degree\b|\badn\b|\b(?:2|two)[- ]year degree\b"),
    ("high school", r"\bhigh school\b|\bged\b"),
)
EQUIVALENT = re.compile(r"or equivalent|equivalent (?:\w+ )?(?:experience|combination)|or (?:related |relevant )?"
                        r"(?:work )?experience|in lieu|or comparable", re.I)
STUDENT = re.compile(r"pursuing|enrolled|working toward|candidate for|currently studying|expected graduation", re.I)
WISH = re.compile(r"\bplus\b|preferred|nice to have|desired|bonus|ideal", re.I)
PROFESSIONAL = re.compile(r"\b(?:j\.?d|m\.?d|d\.?d\.?s|pharm\.?\s?d|psy\.?\s?d|d\.?n\.?p|d\.?v\.?m)\b", re.I)
# spelled-out degree's first word -> level; Juris Doctor, Doctor of Medicine... answer "can't tell"
HELD = {"associate": "associate's", "bachelor": "bachelor's", "master": "master's"}


def years_asked(text: str) -> int | None:
    if NOT_WORK.search(text) or STUDY.search(text):
        return None
    m = YEARS.search(text)
    if not m or not (WORK.search(text) or AFTER.match(text[m.end():])):
        return None
    return int(m[1]) if m[1].isdigit() else WORDS[m[1].lower()]


def degree_asked(text: str) -> str | None:
    if EQUIVALENT.search(text) or STUDENT.search(text) or PROFESSIONAL.search(text):
        return None
    asked = " ".join(c for c in re.split(r"[;,()]|\s-\s", text) if not WISH.search(c))
    found = [level for level, pattern in ASKED if re.search(pattern, asked, re.I)]
    return found[-1] if found else None


def degree_held(entry: dict) -> str | None:
    """Level of one education entry, or None (a certificate program, a professional doctorate)."""
    written = (entry.get("degree") or "").strip()
    # "BS", "B.S. in Computer Science", "Bachelor of Science": the first word names the level
    spelled = render.DEGREES.get(re.sub(r"[\s.]", "", written).upper()) or render.degree_name(written)
    first = spelled.split()[0].casefold() if spelled.split() else ""
    if first in HELD:
        return HELD[first]
    if re.match(r"doctor of (philosophy|education)\b|ph\.?\s?d", spelled, re.I):
        return "doctorate"
    if re.search(r"high school|\bged\b", spelled, re.I):
        return "high school"
    return None


def dated_years(master: dict, today: date) -> int | None:
    """Whole years the dated jobs add up to, overlaps counted once; None w/o dates."""
    spans = sorted((schema.month_index(r["start"], today), schema.month_index(r["end"], today, end=True))
                   for r in master.get("roles") or [] if r.get("start") and r.get("end"))
    if not spans:
        return None
    months, (low, high) = 0, spans[0]
    for start, end in spans[1:]:
        if start > high + 1:
            months, low, high = months + high - low + 1, start, end
        else:
            high = max(high, end)
    return (months + high - low + 1) // 12


def shortfalls(master: dict, job: dict, today: date) -> list[str]:
    """Plain lines: each minimum ask the resume details visibly miss, quoting the posting."""
    have_years = dated_years(master, today)
    levels = [degree_held(e) for e in master.get("education") or []]
    # an entry read as no level (a diploma program, a JD) may be the higher one: can't tell
    known = None not in levels
    held = max((LADDER.index(lv) for lv in levels if lv), default=None)
    out = []
    for req in job.get("requirements") or []:
        if req.get("priority") != "required":
            continue
        text = req["text"]
        asked = years_asked(text)
        if asked is not None and have_years is not None and have_years < asked:
            out.append(f'Asks {asked}+ years ("{text}"). Your dated jobs add up to {have_years}.')
        level = degree_asked(text)
        if level and known and (held is None or held < LADDER.index(level)):
            mine = LADDER[held] if held is not None else "none listed"
            what = "a high school diploma" if level == "high school" else f"{'an' if level[0] in 'aeiou' else 'a'} {level} degree"
            out.append(f'Asks {what} ("{text}"). Your highest in your resume details: {mine}.')
    return out
