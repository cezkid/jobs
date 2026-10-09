"""Minimum asks a resume visibly doesn't meet: years of experience, a degree, a licence or
certification. Report only.

Knock-out questions are real but narrow (docs/resume/bullets.md Tier 3): work authorisation,
licences, location, minimum qualifications. Before tailoring, the user hears which minimum asks
their resume details fall short of, quoted from the posting, and decides. Never a score, never a
block, never said when either side has no data.

Read off a required line only. Years: the lower bound of what's asked ("3-5 years" -> 3) vs whole
years the dated jobs add up to, overlaps merged - short in total means short in any specialty, so
the statement is always true; "18 years of age", "within 1 year of hire" are not experience.
Credential: a licence or certification a line asks to hold (CPA, CAMS, Series 7) that no part of their
resume details names - `credentials_asked`, measured below it.
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
MONTH_NUM = {m.casefold(): i for i, m in enumerate(schema.MONTH_NAMES, 1)}
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
        return f"{schema.MONTH_NAMES[i % 12]} {i // 12}"
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


# Licences + certifications a required line asks to hold: "Active CAMS certification", "FINRA Series 7
# and 24 licenses", "Certified Internal Auditor (CIA)", "CISSP, CISM, or CISA". Measured 2026-10-09 on
# 6,990 unique required lines of 2,112 compliance-titled US postings (compliance, AML, KYC, BSA,
# regulatory, GRC, internal audit, privacy, financial crimes) + 7,069 from healthcare, finance, legal,
# software, education, security, management: 31 + 46 reads, every one hand-checked; the misreads a
# first try made are tests now (a firm "Registered Investment Adviser (RIA)", "IAR registrations" as a
# duty, "CLI credential", Level II, "license applications", TLS/SSL certificates, a state code, wishes
# worded "an asset" / "advantageous" / "highly valued", DoD 8570 levels any of dozens of certs meet).
CRED_WORD = r"(?:certifications?|certificates?|certified|licen[cs]es?|licensure|licensed|designations?)"
# a credential word naming a topic, not something held: "license applications", "certification programs"
CRED_TOPIC = (r"(?!\s+(?:applications?|requirements?|renewals?|programs?|process\w*|management|compliance|audits?|"
              r"regulations?|reviews?|filings?|tracking|status|fundamentals|infrastructure)\b)")
_ACR = r"(?!(?:I{1,3}|IV|VI{0,3}|IX|X)\b)[A-Z][A-Z0-9&]{1,7}(?:-[A-Z0-9]{1,4})?"
_SEP = r"\s*(?:,\s*(?:or|and)?|/|\bor\b|\band\b|&)\s*"
_LIST = rf"{_ACR}(?:{_SEP}{_ACR})*"
CRED_BEFORE = re.compile(rf"(?<![\w-])({_LIST})\)?\s+{CRED_WORD}\b{CRED_TOPIC}")
CRED_AFTER = re.compile(rf"\b{CRED_WORD}\s*(?:\(|:|,?\s*(?:such as|e\.g\.,?|eg;?|like|including)\s+)\s*(?:an?\s+|the\s+)?"
                        rf"({_LIST})(?![\w-])")
CRED_SPELLED = re.compile(rf"\b(?:Certified|Chartered)\s+[A-Z][\w&-]*(?:\s+[\w&-]+){{0,6}}?\s*\(({_ACR})\)")
# FINRA / NASAA exams, numbered: "Series 7, 24 and 63", "Series 66(63/65)", "Series 9/10"
SERIES = re.compile(r"\bSeries\s+\d{1,2}(?:\s*(?:\(|\)|,|/|&|\band\b|\bor\b)\s*(?:Series\s+)?\d{1,2}\b)*")
ANY_ACR = re.compile(rf"(?<![\w-]){_ACR}(?![\w-])")
# says nothing about holding it now: a wish, something to earn after hire, an alternative to a degree,
# a category many certs meet, a line about knowing or handling licences rather than holding one
CRED_SAYS_NOTHING = re.compile(
    r"\bplus\b|prefer|nice to have|desir|bonus|ideal|asset|advantag|helpful|not required|a benefit|valued|"
    r"in (?:place|lieu) of|equivalent|or similar|\bobtain|\bacquir|\battain|\bearn|\bpursu|\bcomplet|"
    r"\bwithin (?:\d+|one|two|three|six|twelve|the first)\b|progress|working toward|\bwilling|considered|"
    r"\b8570\b|\b8140\b|^\W*(?:\w+\s+)?(?:experience|knowledge|familiarity|understanding)\b", re.I)
# "or", "one of", "such as": any one held answers the line; else each named one is asked
CRED_ANY = re.compile(r"\bor\b|/|one of|such as|e\.g|\blike\b|\betc\b|one or more|at least one|any of", re.I)
# rules, regulators, programs: never a credential however framed
NOT_CRED = set("US USA UK EU IT ISO PCI DSS SOC SOX HIPAA GDPR NIST AML BSA KYC OFAC SEC FINRA NFA CFTC OCC FDIC "
               "GED ID HR QA QC FAA DOT DOD CDL TLS SSL PKI".split())
# a state before a licence ("TN active RN license") is never named as the ask; still accepted on an
# either/or line, where MD is the doctor's ("NYSED MD/DO license")
STATES = set("AL AK AZ AR CA CO CT DE DC FL GA HI IA IL IN KS KY LA MA MD ME MI MN MO MS MT NC ND NE NH NJ NM NV "
             "NY OH OK OR PA RI SC SD TN TX UT VA VT WA WI WV WY".split())


def _named(group: str) -> list[str]:
    return [a for a in re.split(_SEP, group) if a and a not in NOT_CRED | STATES]


def credentials_asked(text: str) -> tuple[list[str], list[str], bool] | None:
    """A licence or certification a required line asks to hold: (named, accepted, any_one), or None.
    named = what the line frames as the credential (said to the user); accepted = named plus every
    other short form on an either/or line ("AWS Certified Solutions Architect, CISSP, or CISA"), so
    any one held answers it; any_one False = each named one asked ("Series 7 and 24")."""
    if CRED_SAYS_NOTHING.search(text):
        return None
    named = [f"Series {n}" for m in SERIES.finditer(text) for n in re.findall(r"\d{1,2}", m.group(0))]
    named += ["SIE"] if re.search(r"\bSIE\b", text) else []
    named += [a for pattern in (CRED_BEFORE, CRED_AFTER, CRED_SPELLED) for m in pattern.finditer(text)
              for a in _named(m.group(1))]
    named = list(dict.fromkeys(named))
    if not named:
        return None
    any_one = bool(CRED_ANY.search(text))
    accepted = list(dict.fromkeys(named + ([a for a in ANY_ACR.findall(text) if a not in NOT_CRED] if any_one else [])))
    return named, accepted, any_one


def _strings(value) -> list[str]:
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return [value] if isinstance(value, str) else []


def credential_text(master: dict) -> str:
    """Their resume details as text, for finding a credential's short form anywhere - a
    Certifications line, the skills list, a summary - plus the initials of each certification
    written out in full ("Certified Internal Auditor" -> CIA). Contact details stay out, all but
    the letters after a name ("Jane Doe, CPA" -> CPA): ranking reads no name (fair-screening.md)."""
    name = (master.get("contact") or {}).get("name") or ""
    initials = [name.split(",", 1)[1]] if "," in name else []
    for cert in master.get("certifications") or []:
        full = re.sub(r"\s*\([^)]*\)", "", cert.get("name") or "")
        for words in (re.split(r"[\s/]+", full), re.split(r"[\s/-]+", full)):
            initials.append("".join(w[0] for w in words if w[:1].isupper()))
    return "\n".join(_strings({k: v for k, v in master.items() if k != "contact"}) + initials)


def holds(credential: str, text: str) -> bool:
    if credential.startswith("Series "):
        number = credential.split()[1]
        return any(number in re.findall(r"\d{1,2}", m.group(0)) for m in SERIES.finditer(text))
    return bool(re.search(rf"(?<![\w-]){re.escape(credential)}(?![\w-])", text))


def credentials_missing(text: str, have: str) -> list[str] | None:
    """None = the line asks no credential; [] = theirs answers it; else the ones it asks they don't list."""
    if not (asked := credentials_asked(text)):
        return None
    named, accepted, any_one = asked
    if any_one:
        return [] if any(holds(c, have) for c in accepted) else named
    return [c for c in named if not holds(c, have)]


def credential_words(missing: list[str], text: str) -> str:
    """"Series 24", "one of CISSP, CISA", "Series 7 and Series 24" - the ask in the posting's terms."""
    if len(missing) == 1:
        return missing[0]
    if credentials_asked(text)[2]:
        return "one of " + ", ".join(missing)
    return ", ".join(missing[:-1]) + " and " + missing[-1]


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
    have = credential_text(master)
    out = []
    for req in job.get("requirements") or []:
        if req.get("priority") != "required":
            continue
        text = req["text"]
        if master and (missing := credentials_missing(text, have)):
            them, they = ("it", "it") if len(missing) == 1 else ("them", "they")
            out.append(f"Asks {credential_words(missing, text)} (\"{text}\"). Not in your resume details - "
                       f"if you hold {them}, {they} can go in there.")
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
