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

from resume import schema

WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
         "ten": 10, "twelve": 12, "fifteen": 15}
NUM = r"(\d{1,2}|" + "|".join(WORDS) + r")"
YEARS = re.compile(rf"\b{NUM}\s*(?:\+|plus)?\s*(?:(?:-|–|to|or)\s*{NUM}\s*\+?\s*)?(?:full[- ]time\s+)?(?:years?|yrs?)\b"
                   r"(?!\s+(?:of\s+age|old|ago))", re.I)
NOT_WORK = re.compile(rf"\bwithin\s+(?:\(?{NUM}\)?\s*)+(?:years?|months?)|\bevery\b|\bper\b|of age\b|\byears? old\b|"
                      r"\bago\b|\bcommit", re.I)
# school, not work, right after the years: "2 years of undergraduate study", "two years of college",
# "one year of a Master's degree", "of coursework" ("work" inside it). Only the words that follow the
# number, and never a line that goes on to say experience: "5+ years of high school coaching
# experience", "a degree program and 3 years of experience" still ask years. A lower-case doing-word
# on the way ("of full-time teaching in a school") is work; a field's name ("Aerospace Engineering
# program") is not
STUDY = re.compile(r"^\W*(?:of|in)\s+(?:(?:a|an|the|your)\s+)?(?:(?-i:(?![a-z][\w'’/.-]*ing\b))[\w'’/.-]+\s+){0,6}?"
                   r"(?:coursework|degree|program|college|university|school|study|studies|undergraduate|education)\b", re.I)
# "up to 2 years" caps the experience; it asks no minimum
UP_TO = re.compile(r"\bup to\s*$", re.I)
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
    if NOT_WORK.search(text):
        return None
    m = YEARS.search(text)
    rest = re.split(r"[;.](?:\s|$)", text[m.end():], maxsplit=1)[0] if m else ""
    school = STUDY.match(rest) and not re.search(r"\bexperience\b", rest, re.I)
    if not m or school or UP_TO.search(text[:m.start()]) \
            or not (WORK.search(text) or AFTER.match(text[m.end():])):
        return None
    return int(m[1]) if m[1].isdigit() else WORDS[m[1].lower()]


def degree_asked(text: str) -> str | None:
    if EQUIVALENT.search(text) or STUDENT.search(text) or PROFESSIONAL.search(text):
        return None
    asked = " ".join(c for c in re.split(r"[;,()]|\s-\s", text) if not WISH.search(c))
    found = [level for level, pattern in ASKED if re.search(pattern, asked, re.I)]
    return found[-1] if found else None


# Graduation window an internship or new-grad posting asks ("graduating between December 2027 and
# June 2028", "Class of 2027", "by Summer 2028", "December 2026 or later"). 2026-10-07, 2,268 live US
# intern / new grad / entry level / co-op / early career rows: 116 carried one on a required line.
# Read wide on purpose - a season spans its months, "A or B" its whole stretch - so only a date
# clearly outside is ever said. "if graduating before ..." is a condition, not a window.
MONTH_ABBR = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
MONTH_NUM = {m.casefold(): i for i, m in enumerate(MONTH_ABBR, 1)}
# a season's widest reading: spring commencements run March-June, fall's September-December;
# "winter" is December at some schools, a January-March term at others, so it spans both
SEASONS = {"spring": (3, 6), "summer": (6, 8), "fall": (9, 12), "autumn": (9, 12), "winter": (1, 15)}
_WHEN = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?|spring|summer|fall|autumn|winter"
POINT = re.compile(rf"\b(?P<when>(?:{_WHEN})(?:\s*(?:/|&|,|and|or)\s*(?:{_WHEN}))*)?\s*(?:of\s+)?"
                   r"(?:the\s+)?(?P<years>20\d\d(?:\s*/\s*20\d\d)?)\b", re.I)
GRADUATING = re.compile(r"\bgraduat\w*|\bclass of\b|\bcompletion of\b", re.I)
CONDITIONAL = re.compile(r"\bif (?:you are |you're )?graduat", re.I)
# a clause ends where the graduation ask does: "graduate by Dec 2026 and be able to start by Feb 2027"
CLAUSE = re.compile(r";|\.(?:\s|$)|\band (?:be able to |can |will )?(?:start|begin)\b|\b(?:start|begin)\w*\b|"
                    r"\bavailab\w*|\bwork period\b|\bduring\b", re.I)
OPEN_LOW = re.compile(r"\b(?:by|before|no later than|prior to)\b|\bor (?:sooner|earlier|before)\b|\brecent(?:ly)? grad", re.I)
BEFORE = re.compile(r"\b(?:before|prior to)\b", re.I)
OPEN_HIGH = re.compile(r"\bor (?:later|after|beyond)\b|\bin or after\b|\band (?:later|after)\b|\bonward", re.I)
# the text cut off mid-date ("... Fall 2027 or Spring/Summ"): its last end is unknown, so left open
CUT_OFF = re.compile(r"(?:/|,|\bor\b|\band\b)\s*(?:spr|sum|fal|aut|win|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*$", re.I)
WITHIN = re.compile(rf"\bwithin the (?:past|last) (?:\d+\s*-\s*)?{NUM} years?\b", re.I)


def _spans(point: re.Match) -> list[tuple[int, int]]:
    """One date mention -> month spans (months since year 0): "May/June of 2027", "Spring 2028/2029"."""
    years = [int(y) for y in re.findall(r"20\d\d", point["years"])]
    whens = re.split(r"\s*(?:/|&|,|and|or)\s*", point["when"].casefold()) if point["when"] else []
    out = []
    for year in years:
        if not whens:
            out.append((year * 12, year * 12 + 11))
        for w in whens:
            first, last = SEASONS[w] if w in SEASONS else (MONTH_NUM[w[:3]],) * 2
            out.append((year * 12 + first - 1, year * 12 + last - 1))
    return out


def graduation_window(text: str, today: date) -> tuple[int | None, int | None] | None:
    """(earliest, latest) graduation month a required line accepts, either end open (None); None when
    the line names no graduation date. Months since year 0, as schema.month_index."""
    if CONDITIONAL.search(text) or not (m := GRADUATING.search(text)):
        return None
    # the clause holding the ask: from the sentence's start, so "(2027 or 2028 graduates)" counts
    start = max((c.end() for c in CLAUSE.finditer(text, 0, m.start())), default=0)
    stop = next((c.start() for c in CLAUSE.finditer(text, m.end())), len(text))
    clause = text[start:stop]
    points = list(POINT.finditer(clause))
    spans = [s for p in points for s in _spans(p)]
    if not spans:
        return None
    low, high = min(s[0] for s in spans), max(s[1] for s in spans)
    if OPEN_HIGH.search(clause) or CUT_OFF.search(clause[points[-1].end():]):
        high = None
    if OPEN_LOW.search(clause):
        high = min(s[0] for s in spans) - 1 if BEFORE.search(clause) and len(spans) == 1 else high
        low = None
    if within := WITHIN.search(clause):
        # "graduated within the past two years": anyone who finished from then up to today
        years, now = int(within[1]) if within[1].isdigit() else WORDS[within[1].lower()], today.year * 12 + today.month - 1
        low = None if low is None else min(low, now - 12 * years)
        high = None if high is None else max(high, now)
    return None if low is None and high is None else (low, high)


def window_label(window: tuple[int | None, int | None]) -> str:
    """"Dec 2027 - Jun 2028", "2027-2028", "by Jun 2028", "Dec 2027 or later"."""
    def month(i: int) -> str:
        return f"{MONTH_ABBR[i % 12]} {i // 12}"
    low, high = window
    if low is not None and high is not None and low % 12 == 0 and high % 12 == 11:
        return str(low // 12) if low // 12 == high // 12 else f"{low // 12}-{high // 12}"
    if low is None:
        return f"by {month(high)}"
    if high is None:
        return f"{month(low)} or later"
    return month(low) if low == high else f"{month(low)} - {month(high)}"


def outside(window: tuple[int | None, int | None], graduation: str, today: date) -> bool:
    """Their graduation (YYYY-MM or a year, its whole span) clearly misses the window."""
    mine_low, mine_high = schema.month_index(graduation, today), schema.month_index(graduation, today, end=True)
    low, high = window
    return (high is not None and mine_low > high) or (low is not None and mine_high < low)


def graduation_asked(job: dict, graduation: str | None, today: date) -> tuple[str, str] | None:
    """(window label, the posting's line) when a required line's graduation window misses theirs."""
    if not graduation:
        return None
    for req in job.get("requirements") or []:
        if req.get("priority") == "required" and (w := graduation_window(req["text"], today)) \
                and outside(w, graduation, today):
            return window_label(w), req["text"]
    return None


def degree_held(entry: dict) -> str | None:
    """Level of one education entry, or None (a certificate program, a professional doctorate)."""
    from resume import render  # pymupdf + typst: only where a degree name is read
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


def enrollment_asked(text: str) -> str | None:
    """Level a line asks a student to be working toward ("currently pursuing a bachelor's degree"),
    or None. degree_asked skips these lines: they ask what you study, not what you hold."""
    if not STUDENT.search(text) or EQUIVALENT.search(text) or PROFESSIONAL.search(text):
        return None
    asked = " ".join(c for c in re.split(r"[;,()]|\s-\s", text) if not WISH.search(c))
    found = [level for level, pattern in ASKED if re.search(pattern, asked, re.I)]
    return found[-1] if found else None


def shortfalls(master: dict, job: dict, today: date) -> list[str]:
    """Plain lines: each minimum ask the resume details visibly miss, quoting the posting."""
    have_years = dated_years(master, today)
    studying = [degree_held(e) for e in master.get("education") or [] if schema.in_progress(e, today)]
    graduation = schema.graduation(master, today)
    school = next((s for s in master.get("education") or [] if s.get("end") == graduation), {})
    if school.get("hide_year"):
        graduation = None
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
        # a student's eligibility: what they're studying for, and when they finish
        level = enrollment_asked(text)
        if level and studying and None not in studying and max(LADDER.index(lv) for lv in studying) < LADDER.index(level):
            out.append(f'Asks to be studying for {"an" if level[0] in "aeiou" else "a"} {level} degree ("{text}"). '
                       f'Yours in progress: {LADDER[max(LADDER.index(lv) for lv in studying)]}.')
        if graduation and (window := graduation_window(text, today)) and outside(window, graduation, today):
            mine = window_label((schema.month_index(graduation, today), schema.month_index(graduation, today, end=True)))
            out.append(f'Asks graduating {window_label(window)} ("{text}"). Your resume details say {mine}.')
    return out
