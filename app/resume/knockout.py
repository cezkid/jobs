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
# software, education, security, management: 38 + 64 reads (risk below: 41), every one hand-checked; the misreads a
# first try made are tests now (a firm "Registered Investment Adviser (RIA)", "IAR registrations" as a
# duty, "CLI credential", Level II, "license applications", TLS/SSL certificates, a state code, wishes
# worded "an asset" / "advantageous" / "highly valued", DoD 8570 levels any of dozens of certs meet - read
# off DoD's chart since, `dod_asked`).
# Risk management added (2026-10-09, 5,003 required lines of 1,768 postings titled risk, risk
# management, SOX, internal controls, ERM): "CPA required" / "Active CPA." name no credential word ->
# KNOWN_CRED; "Professional Certification, such as CIA or CPA required" was missed on its capital C.
# Project + program management added (2026-10-09, 15,562 required lines of 3,700 postings titled
# program / project manager): 465 name PMP, PgMP, CAPM, Scrum, SAFe, ITIL or Lean - mostly as a method
# or a wish; 38 now read as asked. Missed before: "PMP" alone, "PMP (Project Management Professional)
# certification", PgMP / SAFe / ITILv4 (mixed case), two spelled-out names before one "certification",
# "Certifications - PMP, ITILF". Re-read over 34,284 lines (+ compliance, risk, finance, healthcare,
# software, security): 16 reads changed, each checked - BLS / ACLS / PALS now named, not "ARC" in brackets.
# lower case or Capitalised, never a SHOUTED heading ("MINIMUM LICENSURE/CERTIFICATION REQUIRED")
CRED_WORD = (r"(?:[Cc]ertifications?|[Cc]ertificates?|[Cc]ertified|[Ll]icen[cs]es?|[Ll]icensure|[Ll]icensed|"
             r"[Dd]esignations?|[Cc]harter(?:holder)?s?)")
# a credential word naming a topic, not something held: "license applications", "certification programs"
CRED_TOPIC = (r"(?!\s+(?:applications?|requirements?|renewals?|programs?|process\w*|management|compliance|audits?|"
              r"regulations?|reviews?|filings?|tracking|status|fundamentals|infrastructure)\b)")
# PgMP, SAFe, ITILv4: project management credentials written in mixed case (2026-10-09). CompTIA's end
# in "+" and are words, not initials: Security+ was the 2nd cyber cert asked (203 of 23,420 security
# required lines, 2026-10-09) and was never read; "Security +" spaced, SecurityX = CASP+ since 2024-12-17
_COMPTIA = r"(?:Security|Sec|Network|Cloud|Linux|PenTest|Pentest|CySA|CASP|Server|Data|Project|A)\s?\+|Security\s?X\b|CySA\b"
# a hyphen tail up to 5: ISC2's concentrations "CISSP-ISSAP", "CISSP-ISSEP", "CISSP-ISSMP"
_ACR = rf"(?:{_COMPTIA}|PgMP|SAFe|ITILv\d|(?!(?:I{{1,3}}|IV|VI{{0,3}}|IX|X)\b)[A-Z][A-Z0-9&]{{1,7}}(?:-[A-Z0-9]{{1,5}})?)"
# one way to read each gap: ", " split between two \s* made a long list of short forms ("states of
# operation (AL, AR, AZ ... WI)", 33 codes) take hours to fail - every rank stalled on it (2026-10-09)
_SEP = r"\s*(?:,(?:\s*(?:or|and)\b)?|/|\bor\b|\band\b|&)\s*"
_LIST = rf"{_ACR}(?:{_SEP}{_ACR})*"
# its name spelled out between may sit in brackets: "PMP (Project Management Professional) certification"
CRED_BEFORE = re.compile(rf"(?<![\w-])({_LIST})\)?(?:\s*\([A-Z][^()]{{2,60}}\))?\s+{CRED_WORD}\b{CRED_TOPIC}")
# "certification required: OSCP, OSCE, ..." (2026-10-09, security lines)
CRED_AFTER = re.compile(rf"\b{CRED_WORD}(?:\s+(?i:required|needed))?\s*(?:\(|:|,?\s*(?i:such as:?|e\.g\.,?|eg;?|like|including|as)\s+)\s*(?i:an?\s+|the\s+)?"
                        rf"({_LIST})(?![\w-])")
CRED_SPELLED = re.compile(rf"\b(?:Certified|Chartered)\s+(?:in\s+)?[A-Z][\w&-]*(?:\s+[\w&-]+){{0,6}}?\s*\(({_ACR})\)")
# a heading run into its list: "Licensures and Certifications - PMP, ITILF." (plural only: "Certificate -
# NIH Stroke Scale Training" names a course)
CRED_HEADING = re.compile(rf"\b(?:[Cc]ertifications|[Ll]icen[cs]es|[Ll]icensures)\s+[-–]\s+({_LIST})(?![\w-])")
# a name spelled out w/ its short form, then the credential word, maybe after another such name: "Project
# Management Professional (PMP) or Program Management Professional (PgMP) certification"
_SPELLED_OUT = r"[A-Z][\w&-]*(?:\s+[A-Z][\w&-]*){1,6}\s*\("
CRED_NAMED = re.compile(rf"\b{_SPELLED_OUT}({_ACR})\)(?=(?:{_SEP}{_SPELLED_OUT}{_ACR}\))*\s+{CRED_WORD}\b{CRED_TOPIC})")
# credentials whose short form means nothing else, named on a line that requires them w/o a credential
# word ("CPA required", "Active CPA.", "CPA or CIA is required"), or alone on a required line ("PMP").
# Not CSM / PSM: also Customer Success Manager, Process Safety Management. Not CRM / ARM: also a sales
# system and a cloud tool ("CRM experience required" - 9 such lines in the risk sample)
# ... and never years of the work ("7 years of RN or clinical professional experience")
# Security (2026-10-09, 557 of 23,420 required lines of 5,248 US security postings name a cyber cert):
# OffSec, EC-Council, GIAC, ISC2 + CompTIA short forms. Not CAP / CND / CFR: also a cap, a
# "Cyber Network Defense" team, a code of federal regulations. CISA is also the federal agency
# ("CISA KEV", "CISA Zero Trust Maturity Model", "CISA HVA assessment"): never that
_CISA_AGENCY = r"(?!\s+(?:KEV|ZTMM|HVA|AES|BOD|Zero Trust|guidance|directives?|alerts?|advisor(?:y|ies)|binding))"
KNOWN_CRED = re.compile(r"(?<![\w-])(CPA|CIA|CISA" + _CISA_AGENCY + r"|CISM|CISSP(?:-IS[A-Z]{2}P)?|CRISC|CGEIT|CAMS|CFE|CFA|FRM|PRM|"
                        r"CPCU|CRCM|CCEP|CHC|CIPP|CIPM|CIPT|CRMA|CPHRM|CTPRP|CBCP|CERA|RN|PMP|PgMP|CAPM|"
                        r"SSCP|CCSP|CSSLP|CGRC|CCISO|OSCP|OSCE3?|OSWE|OSEP|OSED|CEH|GSEC|GCIH|GCIA|GPEN|GWAPT|GXPN|GCFA|GCFE|"
                        r"GREM|GNFA|GICSP|GCED|GSLC|GCSA|GCLD|Security\+|CySA\+|CASP\+|PenTest\+|SecurityX)"
                        r"(?![\w-])(?!(?:\s+\S+){0,4}\s+experience)")
# the line is nothing but the credential(s): "PMP", "PMP / CAPM.", "ISC2 CISSP", "CompTIA Security+"
_BODY = r"(?:(?:CompTIA|ISC2|\(ISC\)\s?(?:2|²)|GIAC|EC-Council|OffSec|SANS)\s+)?"
KNOWN_ALONE = re.compile(rf"^\W*{_BODY}{KNOWN_CRED.pattern}(?:{_SEP}{_BODY}{KNOWN_CRED.pattern})*\W*$")
MUST = re.compile(r"\brequired\b|\bmust\b|\bactive\b|\bcurrent\b|\bvalid\b|\bhold\b|\bpossess|\bmandatory\b|"
                  r"in good standing", re.I)
# FINRA / NASAA exams, numbered: "Series 7, 24 and 63", "Series 66(63/65)", "Series 9/10"
SERIES = re.compile(r"\bSeries\s+\d{1,2}(?:\s*(?:\(|\)|,|/|&|\band\b|\bor\b)\s*(?:Series\s+)?\d{1,2}\b)*")
ANY_ACR = re.compile(rf"(?<![\w-]){_ACR}(?![\w-])")
# says nothing about holding it now: a wish, something to earn after hire, an alternative to a degree,
# a category many certs meet, a line about knowing or handling licences rather than holding one
CRED_SAYS_NOTHING = re.compile(
    r"\bplus\b|prefer|recommend|nice to have|desir|bonus|ideal|asset|advantag|helpful|not required|benefi|valued|optional|"
    r"in (?:place|lieu) of|equivalent|or similar|\bobtain|\bacquir|\battain|\bearn|\bpursu|\bcomplet|"
    r"\bwithin (?:\d+|one|two|three|six|twelve|the first)\b|progress|working toward|\bwilling|considered|"
    r"\b8570\b|\b8140\b|^\W*(?:\w+\s+)?(?:experience|knowledge|familiarity|understanding)\b", re.I)
# "or", "one of", "such as": any one held answers the line; else each named one is asked
CRED_ANY = re.compile(r"\bor\b|/|one of|such as|e\.g|\blike\b|\betc\b|one or more|at least one|any of", re.I)
# rules, regulators, programs, the bodies that issue credentials ("Regulatory Affairs Certification
# (RAPS)"): never a credential however framed
NOT_CRED = set("US USA UK EU IT ISO PCI DSS SOC SOX HIPAA GDPR NIST AML BSA KYC OFAC SEC FINRA NFA CFTC OCC FDIC "
               "GED ID HR QA QC FAA DOT DOD CDL TLS SSL PKI RAPS ISACA IIA ACAMS ACFE GARP PRMIA IAPP AHA ASQ "
               "ISC2 AICPA RIMS PMI SANS HTB IAT IAM IASAE DCWF DOW DISA RMF STIG".split())
# a state before a licence ("TN active RN license") is never named as the ask; still accepted on an
# either/or line, where MD is the doctor's ("NYSED MD/DO license")
STATES = set("AL AK AZ AR CA CO CT DE DC FL GA HI IA IL IN KS KY LA MA MD ME MI MN MO MS MT NC ND NE NH NJ NM NV "
             "NY OH OK OR PA RI SC SD TN TX UT VA VT WA WI WV WY".split())


def _named(group: str) -> list[str]:
    return [canon(a) for a in re.split(_SEP, group) if a and a not in NOT_CRED | STATES]


def canon(name: str) -> str:
    """"Security +" -> "Security+", "Security X" -> "SecurityX": one spelling to say and look for."""
    return re.sub(r"\s+(?=[+X]$)", "", name)


# DoD 8570.01-M baseline certifications by category + level (DoD Cyber Exchange chart, as reprinted by
# training vendors; the DoD page now needs a sign-in, 2026-10-09). A higher IAT or IAM level's certs meet a
# lower one; IASAE levels don't carry over. 8140 (DoDM 8140.03) replaced it with work roles that also take
# a degree or training, so a line naming only a work role ("DCWF 511") says nothing; one naming the old
# level ("Current DoD IAT Level II certification prior to start date; no exceptions", "MUST have IAM level 2
# Certification on Day 1") asks one of these. 2026-10-09: 150 of 626 DoD lines name the certs too
DOD_BASELINE = {
    ("IAT", 1): ("A+", "CCNA Security", "CND", "Network+", "SSCP"),
    ("IAT", 2): ("CCNA Security", "CySA+", "GICSP", "GSEC", "Security+", "CND", "SSCP"),
    ("IAT", 3): ("CASP+", "CCNP Security", "CISA", "CISSP", "GCED", "GCIH", "CCSP"),
    ("IAM", 1): ("CGRC", "CND", "Cloud+", "GSLC", "Security+", "HCISPP"),
    ("IAM", 2): ("CGRC", "CASP+", "CISM", "CISSP", "GSLC", "CCISO", "HCISPP"),
    ("IAM", 3): ("CISM", "CISSP", "GSLC", "CCISO"),
    ("IASAE", 1): ("CASP+", "CISSP", "CSSLP"),
    ("IASAE", 2): ("CASP+", "CISSP", "CSSLP"),
    ("IASAE", 3): ("CISSP-ISSAP", "CISSP-ISSEP", "CCSP"),
}
_DOD_N = r"(?:III|II|I|[123])"
DOD_LEVEL = re.compile(rf"\b((?:IAT|IAM|IASAE)(?:\s*/\s*(?:IAT|IAM|IASAE))*)\s*[-/]?\s*(?:Level\s*|L)?({_DOD_N}(?:\s*/\s*{_DOD_N})*)\b", re.I)
# "IAM" alone is identity and access management: the level is what makes it DoD's
_ROMAN = {"i": 1, "ii": 2, "iii": 3, "1": 1, "2": 2, "3": 3}
# what "or equivalent", "8570", "or higher" mean on such a line: the chart's own list - only these say nothing
DOD_SAYS_NOTHING = re.compile(
    r"\bplus\b|prefer|nice to have|desir|bonus|ideal|asset|advantag|helpful|not required|optional|\bobtain|\bacquir|"
    r"\battain|\bearn|\bpursu|\bwithin (?:\d+|one|two|three|six|twelve|the first)\b|progress|working toward|\bwilling", re.I)


def dod_asked(text: str) -> tuple[list[str], list[str], bool] | None:
    """A DoD 8570 category + level a required line asks to hold: named "a DoD IAT Level II certification", accepted =
    any cert on the chart for it (or a higher IAT / IAM level), plus any the line names itself."""
    found = list(DOD_LEVEL.finditer(text))
    if not found or DOD_SAYS_NOTHING.search(text):
        return None
    # each level a line offers ("IAT II or IAM II", "IAT III/IAM II") answers it; said as the first one
    accepted, said = [], None
    for m in found:
        kinds = [k.upper() for k in re.split(r"\s*/\s*", m[1])]
        # "IAT/IAM Level III": either category; "Level II/III": the lower one meets the line
        level = min(_ROMAN[n.lower()] for n in re.split(r"\s*/\s*", m[2]))
        said = said or (kinds, level)
        accepted += [c for kind in kinds for n in ([level] if kind == "IASAE" else range(level, 4))
                     for c in DOD_BASELINE[(kind, n)]]
    accepted += [canon(a) for a in ANY_ACR.findall(text) if a not in NOT_CRED]
    kinds, level = said
    return [f"a DoD {'/'.join(kinds)} Level {'I' * level} certification"], list(dict.fromkeys(accepted)), True


def credentials_asked(text: str) -> tuple[list[str], list[str], bool] | None:
    """A licence or certification a required line asks to hold: (named, accepted, any_one), or None.
    named = what the line frames as the credential (said to the user); accepted = named plus every
    other short form on an either/or line ("AWS Certified Solutions Architect, CISSP, or CISA"), so
    any one held answers it; any_one False = each named one asked ("Series 7 and 24")."""
    if dod := dod_asked(text):
        return dod
    if CRED_SAYS_NOTHING.search(text):
        return None
    named = [f"Series {n}" for m in SERIES.finditer(text) for n in re.findall(r"\d{1,2}", m.group(0))]
    named += ["SIE"] if re.search(r"\bSIE\b", text) else []
    named += [a for pattern in (CRED_NAMED, CRED_BEFORE, CRED_AFTER, CRED_HEADING, CRED_SPELLED) for m in pattern.finditer(text)
              for a in _named(m.group(1))]
    named += KNOWN_CRED.findall(text) if MUST.search(text) or KNOWN_ALONE.match(text) else []
    named = list(dict.fromkeys(named))
    if not named:
        return None
    # a long plain list ("CRISC, CISM, CIA, CISSP,") is a menu; "BLS, ACLS, and PALS" asks all three
    plain = [c for c in named if not c.startswith("Series ")]
    any_one = bool(CRED_ANY.search(text)) or (len(plain) >= 3 and not re.search(r"(?:\band|&)\s+[A-Z]{2,}", text))
    accepted = list(dict.fromkeys(named + ([canon(a) for a in ANY_ACR.findall(text) if a not in NOT_CRED] if any_one else [])))
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
        written = cert.get("name") or ""
        # its own short form in brackets says it: "Program Management Professional (PgMP)" is no PMP
        if re.search(rf"\((?:{_ACR})\)", written):
            continue
        full = re.sub(r"\s*\([^)]*\)", "", written)
        for words in (re.split(r"[\s/]+", full), re.split(r"[\s/-]+", full)):
            initials.append("".join(w[0] for w in words if w[:1].isupper()))
    return "\n".join(_strings({k: v for k, v in master.items() if k != "contact"}) + initials)


# an exam part passed or a candidacy is not the credential: "FRM Part I", "CFA Level II Candidate"
ON_THE_WAY = re.compile(r"\s*(?:\(|-|,)?\s*(?i:part|level|candidate|exam|in progress|expected|pending)\b")


# a licence or registration their resume says is no longer current: "Series 7 (passed 2019; not currently
# registered)" (job-tailor's wording), "CPA (inactive)", "CAMS - expired 2022". Read in its own bracket, or
# up to the next ; or . on its line - "Series 7 and 63; Series 24 lapsed" lapses 24 only. Shown as held
# = Hold (AGENTS.md); a FINRA exam counts again only once a firm re-registers them (Rule 1210.08)
LAPSED = re.compile(r"(?i)\b(?:not currently|no longer|lapsed|expired|inactive)\b")


def _lapsed_after(text: str, end: int) -> bool:
    rest = text[end:].split("\n", 1)[0]
    bracket = re.match(r"[^()\n;.]{0,40}?\(([^)]*)\)", rest)
    return bool(LAPSED.search(bracket.group(1) if bracket else re.split(r"[;.]", rest, maxsplit=1)[0][:40]))


# one credential, several names: CompTIA's short forms, CASP+ renamed SecurityX (CompTIA, 2024-12-17), CAP
# renamed CGRC (ISC2, 2023-02-15) - a resume from before says the old name
SAME_AS = (("Security+", "Sec+"), ("CASP+", "CASP", "SecurityX"), ("CySA+", "CySA", "CSA+"), ("PenTest+", "Pentest+"),
           ("CGRC", "CAP"))
# passed the CISSP exam w/o the years of work it needs: "Associate of ISC2" until then - not the CISSP
# (ISC2). "CISSP (or Associate)" on a DoD line is the posting's own allowance, read there
ASSOCIATE = re.compile(r"(?i)associate of \(?isc\)?\s?(?:2|²)|\(?isc\)?\s?(?:2|²) associate")


def _names(credential: str) -> tuple[str, ...]:
    return next((g for g in SAME_AS if credential in g), (credential,))


def _found(credential: str, text: str) -> list[re.Match]:
    if credential.startswith("Series "):
        number = credential.split()[1]
        return [m for m in SERIES.finditer(text) if number in re.findall(r"\d{1,2}", m.group(0))]
    return [m for name in _names(credential) for m in re.finditer(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text)
            if not ON_THE_WAY.match(text, m.end())
            and not ASSOCIATE.search(text[text.rfind("\n", 0, m.start()) + 1:m.start()])]


# a senior credential answers an ask for its junior one from the same body, and a body's name answers
# any of its credentials: "SHRM-CP required" <- SHRM-SCP, "PHR" <- SPHR, "SHRM and/or HRCI" <- SPHR.
# Postings also write "SHRM-CP/SCP" and "SHRMSCP". 2026-10-09, 182 HR certification lines on 9,768
# unique required lines of US HR-titled jobs: 16 ask one outright, 4 name a junior one a senior holder
# was marked missing on
# ISC2's concentrations are held only on top of the CISSP: "CISSP-ISSMP" answers "CISSP required" (12 + 11
# + 4 security lines ask ISSAP / ISSEP / ISSMP; the hyphen hid the CISSP before, 2026-10-09)
_GIAC = ("GSEC", "GCIH", "GCIA", "GPEN", "GWAPT", "GXPN", "GCFA", "GCFE", "GREM", "GNFA", "GICSP", "GCED", "GSLC",
         "GCSA", "GCLD", "GSTRT", "GMON", "GDSA", "GRID", "GPYC", "GCPN", "GSE")
ANSWERED_BY = {"SHRM-CP": ("SHRM-SCP",), "SCP": ("SHRM-SCP",), "SHRMSCP": ("SHRM-SCP",), "PHR": ("SPHR",),
               "aPHR": ("PHR", "SPHR"), "SHRM": ("SHRM-CP", "SHRM-SCP"), "HRCI": ("aPHR", "PHR", "SPHR", "GPHR", "PHRi", "SPHRi"),
               "CISSP": ("CISSP-ISSAP", "CISSP-ISSEP", "CISSP-ISSMP"), "ISSAP": ("CISSP-ISSAP",), "ISSEP": ("CISSP-ISSEP",),
               "ISSMP": ("CISSP-ISSMP",), "GIAC": _GIAC}


def holds(credential: str, text: str) -> bool:
    return any(not _lapsed_after(text, m.end()) for m in _found(credential, text)) \
        or any(holds(other, text) for other in ANSWERED_BY.get(credential, ()))


def lapsed(credential: str, text: str) -> bool:
    """On their resume, but only as no longer current - said "not current", never "not in your resume"."""
    return not holds(credential, text) and bool(_found(credential, text))


def missing_words(missing: list[str], have: str) -> str:
    """How the ones a line asks stand on their resume: absent, or there but not current."""
    return "not current on your resume" if all(lapsed(c, have) for c in missing) else "not in your resume"


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



# A US security clearance a required line asks to HOLD now, and what their resume details show.
# 2026-10-09, 5,248 US security postings (category + "cyber" / "information security" titles): 707 carry a
# required clearance line, 503 ask one held ("Active TS/SCI clearance with polygraph") - Secret 189, Top
# Secret 140, TS/SCI 174, a polygraph 59; the rest only the ability to get one. 590 lines read by hand. The job search's flag is
# yes / no, so a Secret holder's list read the same as for a TS/SCI one. Public Trust is a suitability
# check, not a clearance: never read. Level order: DOE L sits with Secret, Q with Top Secret
CLEARANCE_LEVELS = ("a Secret clearance", "a Top Secret clearance", "a TS/SCI clearance")
_LEVEL = (
    (2, r"\bTS\s*/\s*SCI\b|\bTS[- ]SCI\b|\btop secret\s*/\s*SCI\b|\bTS/SCI\b"),
    (1, r"\btop[- ]secret\b|\bTS\b(?=\s*(?:\(|clearance|level|security|/|with|$))|\bDOE Q\b|\bQ (?:clearance|access)\b"),
    # Secret beside the clearance words only: never "secrets management", a "Secret Server", the one in "Top Secret"
    (0, r"(?<!top )(?<!top-)\bsecret\b(?!\s*(?:s\b|management|manager|server|scanning|exposure|stores?|detection|"
        r"rotation|sprawl|sauce|weapon|ingredient|santa))|\bDOE L\b|\bL clearance\b"),
)
# a clearance said without a level ("Active DoD security clearance") asks for any one: Secret meets it
# never "current medical clearance", "customs clearance", a "final clearance" sale
SECURITY_CLEARANCE = re.compile(r"(?i)\b(?:security|government|dod|dow|doe|federal|u\.?s\.?|secret|ts/sci|top secret|"
                                r"personnel|poly(?:graph)?)\s+(?:[\w./-]+\s+){0,2}?clearances?\b|"
                                r"(?<!medical )(?<!customs )(?<!dental )(?<!credit )(?<!financial )(?<!export )"
                                r"\bclearance (?:level|required|is required)\b|\bTS/SCI\b")
# a level-less mention asks one only when it says held: never "pay is based on ... security clearance"
CLEARANCE_HELD_CUE = re.compile(r"(?i)\b(?:active|current\w*|must (?:have|hold|possess)|possess\w*|hold\w*|held|in place|"
                                r"required|requires)\b")
# "CI poly eligible": eligible for one, not holding one
POLYGRAPH = re.compile(r"(?i)(?:polygraph|\bpoly\b|\bFSP\b|full[- ]scope|\bCI[- ]?poly)(?!\w*\s+(?:\w+\s+)?eligib)")
# from here to the clause's end the line asks only to be able to get one ("Ability to obtain ... post start");
# "able to maintain an Active Top Secret" still asks one held
CLEARANCE_OBTAIN = re.compile(r"(?i)\b(?:obtain\w*|eligib\w*|willing\w*|be granted|receive|sponsor\w*|post[- ]start|"
                              r"after (?:start|hire)|submit to|undergo|pass(?:ing)? a|within \d+ (?:days|months)|permitting|to issue)\b")
# held now or able to get one: either answers the line ("Active clearance or ability to obtain one")
CLEARANCE_EITHER = re.compile(r"(?i)\bor\s+(?:be\s+|the\s+|ha(?:ve|s)\s+the\s+)?(?:ability|able|eligib\w*|obtain|willing)")
# a clause wishing for more ("SCI preferred", "polygraph desired") asks nothing beyond the rest
# ... or one asked only of some ("some assignments may require Secret", "if required by the contract"),
# a note on who can hold one ("US Citizenship is required to obtain"), a Public Trust / suitability check
CLEARANCE_WISH = re.compile(r"(?i)\b(?:preferred|a plus|desired|nice to have|bonus|ideal(?:ly)?|may (?:be )?requir\w*|"
                            r"(?:if|where|when) (?:required|requested|applicable|needed)|applicable|not required|"
                            r"citizen\w*\s*\(?\s*(?:is\s+)?(?:required|needed)\s+(?:to|for)|requires? (?:US )?citizenship|"
                            r"public trust|suitability)\b")
# on their resume: once held, no longer current ("TS/SCI (inactive since 2024)") / never held yet
CLEARANCE_GONE = re.compile(r"(?i)\b(?:not currently|no longer|lapsed|expired|inactive|previously|formerly|former|held until)\b")
CLEARANCE_NOT_YET = re.compile(r"(?i)\b(?:eligible|eligibility|clearable|able to obtain|in process|pending|applied)\b")


def _clearance_level(text: str) -> tuple[int, bool] | None:
    """(level, named): a line naming no level reads as Secret, the lowest, said as "a security clearance".
    Two levels as alternatives ("Secret or Top Secret") ask the lower; otherwise the higher."""
    found = []
    for level, pattern in _LEVEL:
        # a level read is taken out first: "TS/SCI" is no Top Secret, "Top Secret" no Secret
        text, n = re.subn(pattern, " ", text, flags=re.I)
        found += [level] if n else []
    if found:
        return (min(found) if re.search(r"(?i)\bor\b", text) else max(found)), True
    return (0, False) if SECURITY_CLEARANCE.search(text) else None


def clearance_asked(text: str) -> tuple[int, bool, bool] | None:
    """(level, polygraph, level named) a required line asks them to already hold, or None: no clearance named, only
    the ability to get one ("Ability to obtain a DoD Secret Clearance post start"), or "or able to obtain"."""
    if not SECURITY_CLEARANCE.search(text) or CLEARANCE_EITHER.search(text):
        return None
    # "U.S." ends no clause; a bracket wishing for more goes, one that asks stays in its clause ("Top Secret (TS)")
    text = re.sub(r"\bU\.\s?S\.(?:\s?A\.)?", "US", text)
    text = re.sub(r"\([^()]*\)", lambda b: " " if CLEARANCE_WISH.search(b.group(0)) else b.group(0), text)
    # a heading ("Security Clearance:", "CLEARANCE REQUIREMENTS:") names the topic, not the ask
    text = re.sub(r"(?i)^\W*(?:security\s+)?clearances?(?:\s+(?:requirements?|required|level))?\s*:", " ", text)
    # "... is obtainable after hire", "must be obtained": the whole clause is about getting one
    clauses = [c for c in re.split(r"[;.](?:\s|$)|\s[-–]\s", text)
               if not CLEARANCE_WISH.search(c) and not re.search(r"(?i)\bobtainable\b|\bbe obtained\b", c)]
    kept = " ".join(c[:m.start()] if (m := CLEARANCE_OBTAIN.search(c)) else c for c in clauses)
    if not SECURITY_CLEARANCE.search(kept) and not re.search(r"(?i)\bsecret\b|\bTS\b", kept):
        return None
    found = _clearance_level(kept)
    if found is None or not found[1] and not CLEARANCE_HELD_CUE.search(kept):
        return None
    return found[0], bool(POLYGRAPH.search(kept)) and not re.search(r"(?i)\bpoly\w*\s+(?:\w+\s+)?eligib", text), found[1]


def clearance_held(have: str) -> tuple[int | None, bool, int | None]:
    """(level held now, polygraph held, level shown as no longer current) off their resume details' lines:
    "Active TS/SCI with CI polygraph", "Secret (inactive since 2024)". A line saying eligible / clearable /
    pending holds nothing."""
    level, poly, gone = None, False, None
    for line in have.splitlines():
        # "Clearance: Secret", or a line under their "Security Clearance" heading: "Active Secret"
        if not SECURITY_CLEARANCE.search(line) and not re.search(r"(?i)\bclearance\b|\bTS/SCI\b|\btop secret\b|"
                                                                 r"^\W*(?:active|current|interim|final)?\s*(?:dod\s+|doe\s+)?secret\b", line):
            continue
        if (found := _clearance_level(line)) is None:
            continue
        found = found[0]
        if CLEARANCE_NOT_YET.search(line) and not re.search(r"(?i)\bactive\b", line):
            continue
        if CLEARANCE_GONE.search(line):
            gone = max(found, gone if gone is not None else -1)
            continue
        level = max(found, level if level is not None else -1)
        poly |= bool(POLYGRAPH.search(line))
    return level, poly, gone


def clearance_short(text: str, have: str) -> tuple[str, str] | None:
    """A required line asks to hold a clearance their resume details don't show held: (the ask, where
    they stand) - ("an active TS/SCI clearance with a polygraph", "your resume shows a Secret clearance"),
    else None. Never said when the line asks only the ability to get one."""
    if not (asked := clearance_asked(text)):
        return None
    want, poly, named = asked
    level, has_poly, gone = clearance_held(have)
    if level is not None and level >= want and (has_poly or not poly):
        return None
    ask = f"an active {CLEARANCE_LEVELS[want][2:] if named else 'security clearance'}{' with a polygraph' if poly else ''}"
    if level is not None and level >= want:
        return ask, "no polygraph on your resume"
    if level is not None:
        return ask, f"your resume shows {CLEARANCE_LEVELS[level]}"
    if gone is not None and gone >= want:
        return ask, "not current on your resume"
    return ask, "not in your resume"


CLEARANCE_SAYS = {
    "not in your resume": "Not in your resume details - if you hold one, it goes there as a form asks it: level, "
                          "active or current, polygraph if any.",
    "not current on your resume": "Your resume details show it as no longer current - said that way, never as active.",
    "no polygraph on your resume": "No polygraph in your resume details - if you've had one, it goes there as it "
                                   "was (CI or full scope).",
}


# A required line asking to see their work: a portfolio, a reel, work samples. 2026-10-09, US: 217 of 551
# video / editor / motion postings w/ required lines ask one (210 of 3,828 unique lines), creative 123 of
# 2,490, marketing 24 of 1,985 (copywriters, social), finance + software 2 each ("prior projects, portfolio
# of work"), healthcare 0. Singular only: "portfolios" is money ("cash portfolios", "managing
# portfolios"); "Reels" is Instagram's; "reel spins" a slot machine. Every hit + cut read by hand.
PORTFOLIO = re.compile(r"(?<![\w-])(?:portfolio|porfolio|show ?reel|demo reel|reel|work samples|"
                       r"samples? of (?:your |relevant |past |previous |recent )?work|"
                       r"examples of (?:your |relevant |past |previous |recent )?work)(?![\w-])", re.I)
NOT_PORTFOLIO = re.compile(
    r"\b(?:manag\w*|investment|loan|credit|asset|cash|client|customer|product|project|program|patent|property|"
    r"media|brand|account|deal|insurance|fund|equity|mortgage|vendor|application|enterprise|business|solutions?)\s+portfolio\b|"
    r"\bportfolio\s+(?:manag\w*|analy\w*|marketing|consolidation|narratives?|work and live deals)\b|"
    r"\bportfolio of [\w/ -]{0,30}?\b(?:investments|loans|assets|clients|accounts|products|properties|brands|"
    r"patents|companies|funds)\b|\bthe [A-Z]\w+ portfolio\b|\breel (?:spins?|strips?)\b|"
    r"\b(?:instagram|ig|facebook|fb|youtube) reel\b", re.I)
# not their own site: a link here is a profile, not work to look at
PROFILE_ONLY = ("linkedin.",)


def portfolio_asked(text: str) -> bool:
    return bool(PORTFOLIO.search(text)) and not NOT_PORTFOLIO.search(text)


def portfolio_link(master: dict) -> str:
    """A link their work can be seen at: any on the page or kept for forms that isn't LinkedIn
    (Vimeo, YouTube, Behance, their own site; GitHub for code)."""
    contact = master.get("contact") or {}
    return next((u for u in (contact.get("links") or []) + (contact.get("form_links") or [])
                 if not any(h in u.casefold() for h in PROFILE_ONLY)), "")


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
    no_link = bool(master) and not portfolio_link(master)
    out = []
    for req in job.get("requirements") or []:
        if req.get("priority") != "required":
            continue
        text = req["text"]
        # once per posting: one link answers every line asking to see their work
        if no_link and portfolio_asked(text):
            no_link = False
            out.append(f"Asks to see your work - a portfolio or reel (\"{text}\"). No link to one in your resume "
                       "details - if you have one (Vimeo, YouTube, your own site), it can go there.")
        if master and (missing := credentials_missing(text, have)):
            them, they = ("it", "it") if len(missing) == 1 else ("them", "they")
            if all(lapsed(c, have) for c in missing):
                out.append(f"Asks {credential_words(missing, text)} (\"{text}\"). Your resume details show {them} "
                           "as no longer current - said that way on the page, never as held now.")
            else:
                out.append(f"Asks {credential_words(missing, text)} (\"{text}\"). Not in your resume details - "
                           f"if you hold {them}, {they} can go in there.")
        if master and (short := clearance_short(text, have)):
            ask, standing = short
            out.append(f'Asks {ask} ("{text}"). ' + CLEARANCE_SAYS.get(
                standing, f"Your resume details show {standing.removeprefix('your resume shows ')} - said as held, never higher."))
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
