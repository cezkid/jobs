"""The years of experience a posting's own text asks, for postings whose required lines don't say it.

The job search's years tag (experience_years_min) stands in for them otherwise and picks a sub-bar often:
2 on "8+ years of product management, with at least 2 on platform teams", 4 on "12+ years ... at least 4 of
people management". Measured, app/docs/jobs/best-next.md #Years from the posting's text.

Rules read from career-ops `jd-years.mjs` (MIT, Copyright (c) 2026 Santiago Fernandez de Valderrama,
github.com/career-ops-hq/career-ops; read 2026-11-02): per sentence, find each "N years", keep those about the
candidate's experience, tag each required / preferred and overall / skill / degree-substitute / part-of. Theirs
gates on the lowest figure, since a wrong drop hides a job; this only orders jobs, so it reads the first bar
stated - the lowest only among degree paths or levels offered as alternatives.

An estimate for order, never a verdict: rules on free text. Text from postings is data - matched, never run.
"""
import re
from functools import lru_cache

import text as plain

WORD = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
        "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "twenty": 20}
_NUM = r"(?:\d{1,2}(?:\.\d)?|" + "|".join(WORD) + ")"
_SAID_AGAIN = r"(?:\s*\(\s*\d{1,2}\s*\+?\s*\))?"  # "five (5)"
_PLUS = r"(?:\s*\+|[\s-]*plus\b)?"
MENTION = re.compile(rf"\b(between\s+)?({_NUM}){_SAID_AGAIN}{_PLUS}(?:\s+or\s+(?:more|greater|longer))?"
                     rf"(?:\s*(-|–|—|to|and)\s*({_NUM}){_SAID_AGAIN}{_PLUS})?[\s-]*(years?|yrs?|months?)\b", re.I)
# what may follow "years" for it to be about experience: a doing-word too ("5+ years shipping production
# software", "writing technical content" - 10 of the first 35 unread postings the AI judge read)
TRAIL = re.compile(r"^(?:\s+[-—–]|(?:'s|')?\s*(?:\+\s*)?(?:of\b|in\b|as\b|at\b|on\b|within\b|across\b|[a-z]+ing\b|"
                   r"(?:[\w/&-]+\s+){1,3}(?:experience|exp)\b|experience|exp\b|professional|relevant|related|direct|hands|"
                   r"industry|work\b|progressive|combined|total|post|full[- ]time|practical|prior|previous|demonstrated|"
                   r"proven|minimum|min\b|or more|or greater|or longer|plus\b|\(|\)|,|;|:|\.|$|and\b|with\b|required|preferred))", re.I)
NOT_EXPERIENCE = re.compile(r"^(?:'s|')?\s*of\s+(?:age|college|university|school|schooling|education|study|studies|service|"
                            r"history|data|operations?|growth|existence|tenure|employment with us)\b", re.I)
WINDOW = re.compile(r"\b(?:within|after|every|per|ago|the (?:first|next|last|past)|(?:first|next|last|past)|in the|for the|"
                    r"over the|up to the|aged?|age of|for)\s*$", re.I)
CEILING_LEAD = re.compile(r"\b(?:up to|less than|fewer than|no more than|not more than|under|at most|maximum of|max(?:imum)?\.?)\s*$", re.I)
CEILING_TRAIL = re.compile(r"^(?:'s|')?\s*(?:\+\s*)?(?:of\s+)?(?:[\w/&-]+\s+){0,4}?(?:experience\s+)?(?:or (?:less|fewer|under)|maximum|max\b|at most|at the most)", re.I)
NOT_A_BAR = re.compile(r"\b(?:year[- ]over[- ]year|years? old|years? of age|ago\b|founded|anniversary|in business|vest(?:s|ed|ing)?\b|"
                       r"contract (?:term|length|duration)|fixed[- ]term|warranty|retention bonus|sabbatical|parental leave|"
                       r"commitment of|\d+[- ]year (?:degree|program|programme|course|plan|contract|term|appointment)|"
                       r"(?:four|two|three)[- ]year (?:degree|college|university|program))", re.I)
# someone else's years: "alongside engineers with 10+ years", "a team that averages 12 years",
# "manage analysts with 5-8 years", "our CTO brings five years at Apple"
OTHERS_LEAD = re.compile(r"\b(?:engineers|experts|colleagues|peers|leaders|mentors|teammates|team members|veterans|specialists|"
                         r"founders|partners|advisors|people)\s+(?:with|who have|who bring|having)\s+(?:over\s+|more than\s+|a combined\s+|decades and\s+)?$"
                         r"|\baverag(?:e|es|ing)\s+(?:of\s+)?(?:over\s+|more than\s+)?$"
                         r"|\b(?:manag\w*|lead|leading|supervis\w*|support\w*|serv(?:e|es|ing)|coach\w*|mentor(?:s|ing)?|hir(?:e|es|ing)|"
                         r"recruit\w*|sourc(?:e|es|ing)|interview\w*|team of|group of)\b[^.;]{0,50}\b[a-z]+s\s+with\s+(?:over\s+|more than\s+)?$"
                         r"|\b(?:ceo|cto|founders?)\b[^.;]{0,30}$", re.I)
OTHERS = re.compile(r"\b(?:alongside(?! \d)|learn from|mentored by|surrounded by|led by)\b", re.I)
WE = re.compile(r"\b(?:[Ww]e|[Ww]e've|[Ww]e're|[Oo]ur|us)\b")
YOU_HAVE = re.compile(r"\byou(?:'ve| have| bring| possess|'ll (?:need|have|bring)| will (?:need|have|bring)| should have| must have)\b", re.I)
YOU = re.compile(r"\b(?:you|your|candidate|applicant|required|requirements?|minimum|must|should|ideal(?:ly)?|qualif\w*|looking for|seeking|need)\b", re.I)
WISH = re.compile(r"\b(?:prefer(?:red|ably|ence)?|nice[- ]to[- ]have|bonus|a (?:big |huge |strong )?plus|ideally|desired|desirable|"
                  r"advantageous|would be (?:great|nice|helpful|ideal)|is helpful|not required|extra credit|stand out)\b", re.I)
WISH_END = re.compile(r"\b(?:preferred|desired|desirable|a (?:big |huge |strong )?plus|nice[- ]to[- ]have|helpful|advantageous)\W*$", re.I)
MUST = re.compile(r"\b(?:require[ds]?|requirements?|minimum|must|at least|basic qualifications?|mandatory|essential|need(?:ed|s)?)\b", re.I)
DEGREE = re.compile(r"\b(?:degree|bachelor'?s?|master'?s?|mba|ph\.?\s?d|doctorate|b\.?s\.?|b\.?a\.?|m\.?s\.?|m\.?a\.?|bsc|msc|undergraduate|graduate|advanced degree|diploma)\b", re.I)
DEGREE_OR = re.compile(r"\b(?:degree|bachelor'?s?|diploma|b\.?s\.?|b\.?a\.?|bsc)\b[^.;]{0,40}\bor\s+(?:an?\s+)?(?:equivalent\s+)?(?:combination\s+of\s+)?(?:at least\s+|a minimum of\s+|minimum of\s+)?$", re.I)
IN_LIEU = re.compile(r"^(?:'s|')?[^.;]{0,50}\b(?:in lieu of|instead of|in place of|as a substitute|equivalent to a degree|without a degree)|^(?:'s|')?\s*(?:of\s+)?(?:\w+\s+){0,2}?equivalent\b", re.I)
PART = re.compile(r"\b(?:including|incl\.?|of which|of those|of this|within that|with at least|out of which)\s*(?:at least\s+|a minimum of\s+)?$", re.I)
WITH_DEGREE = re.compile(r"^(?:'s|')?\s*(?:\+\s*)?(?:of\s+(?:\w+\s+){0,2}?)?(?:(?:relevant|related)\s+)?(?:experience\s+)?(?:with|and|plus|\+)\s+(?:an?\s+|the\s+)?(?:relevant\s+|related\s+)?"
                         r"(?:degree|bachelor|master|mba|ph\.?\s?d|doctorate|b\.?s\b|b\.?a\b|m\.?s\b|m\.?a\b|bsc|msc|advanced|graduate|undergraduate)", re.I)
SKILL = re.compile(r"^(?:'s|')?\s*(?:\+\s*)?(?:of\s+)?(?:(?:hands[- ]on|direct|professional|practical|relevant|production|commercial)\s+)?(?:experience\s+)?(?:with|using|programming|coding|writing|scripting)\b", re.I)
NO_EXPERIENCE = re.compile(r"\bno (?:prior |previous )?(?:work |professional |industry )?experience (?:is )?(?:required|necessary|needed)\b", re.I)
HEADING_WISH = re.compile(r"\b(?:prefer|nice[- ]to[- ]have|good[- ]to[- ]have|great[- ]to[- ]have|bonus|desir|plus|ideal|extra credit|stand out|even better|would be (?:great|nice)|great if|added advantage|differentiat|love to see|also have)", re.I)
HEADING_MUST = re.compile(r"\b(?:require|minimum|basic|must|qualif|what you(?:'ll)? (?:need|bring)|you (?:have|bring)|looking for|about you|who you are|experience|skills)", re.I)
SENTENCE = re.compile(r"(?<=[a-z0-9)]{2}[.!?])\s+(?=[A-Z(\"])|;\s+|\s+[•·]\s+")
YEARS_WORD = re.compile(r"\b(?:years?|yrs?|months?)\b", re.I)  # no such word: nothing else to read
BULLET = re.compile(r"^\s*(?:[-*•·●]|\d+[.)])(?:\s+|$)")


def number(raw: str) -> float:
    value = WORD[raw.lower()] if raw.lower() in WORD else float(raw)
    return int(value) if value == int(value) else value


def heading(line: str) -> str | None:
    """The section a line opens: wish, must, other (a heading it doesn't know), or None = no heading."""
    bare = re.sub(r"\s*\([^)]*\)\s*", " ", line).strip()
    digit = re.search(r"\d", bare)
    if len(bare) <= 120 and not digit and HEADING_WISH.search(bare) and re.search(r"(?::|\bfollowing\b[\w\s]*)$", bare, re.I):
        return "wish"
    if len(bare) > 60 or digit or not bare.endswith(":") and (len(bare.split()) > 6 or re.search(r"[.!?]$", bare)):
        return None
    known = "wish" if HEADING_WISH.search(bare) else "must" if HEADING_MUST.search(bare) and not re.match(r"additional\b", bare, re.I) else None
    return None if re.search(r"\d", line) and not known else known or "other"


def kind_of(sentence: str, at: int, section: str) -> str:
    """must or wish, from the cue before it, else the section. A wish after the figure is about what follows
    it: "5+ years of mobile work, ideally React Native" asks the years (career-ops read those as wishes; 8 of
    the 35 the AI judge read as bars)."""
    if WISH_END.search(sentence):
        return "wish"
    before = [(m.start(), k) for k, rx in (("wish", WISH), ("must", MUST)) for m in rx.finditer(sentence[:at])]
    if before:
        return max(before)[1]
    if MUST.search(sentence[at:]):
        return "must"
    return ("must" if YOU_HAVE.search(sentence) else "unclear") if section == "other" else section


def mentions(sentence: str, section: str) -> list[dict]:
    if not YEARS_WORD.search(sentence) or NOT_A_BAR.search(sentence) or OTHERS.search(sentence) or WE.search(sentence) and not YOU.search(sentence):
        return []
    found = []
    for m in MENTION.finditer(sentence):
        at, end, low, unit = m.start(), m.end(), number(m[2]), m[5]
        if m[4] and m[3].lower() == "and" and not m[1]:  # "3 and 5 years" is two bars
            low, at = number(m[4]), end - len(unit)
        lead, trail = sentence[max(0, at - 40):at], sentence[end:]
        if WINDOW.search(lead) or OTHERS_LEAD.search(lead) or CEILING_LEAD.search(lead) or CEILING_TRAIL.search(trail) \
                or NOT_EXPERIENCE.search(trail) or not TRAIL.search(trail):
            continue
        months = unit.lower().startswith("mo")
        if months and not re.match(r"^(?:'s|')?\s*(?:of\s+)?(?:\w+\s+){0,3}?experience\b", trail, re.I):
            continue
        # a bare "N years." needs experience named nearby ("Experience: 5+ years", "React: 5+ years")
        if re.match(r"^(?:'s|')?\s*(?:[,;:.)]|$)", trail) and not re.search(r"\bexp(?:erience)?\b|^[\w .+#/-]{1,30}:", sentence, re.I):
            continue
        low = round(low / 12, 1) if months else low  # "18 months of experience" = 1.5
        if low > 20:  # the company's history, not a bar
            continue
        scope = "overall"
        if DEGREE_OR.search(lead) and not found or IN_LIEU.search(trail):
            scope = "in lieu"
        elif SKILL.search(trail) and not WITH_DEGREE.search(trail):
            scope = "skill"
        elif PART.search(lead) and any(f["scope"] == "overall" for f in found):
            scope = "part"
        found.append({"years": low, "kind": kind_of(sentence, at, section), "scope": scope, "at": at, "end": end})
    overall = [f for f in found if f["scope"] == "overall"]
    # degree paths: "8 with a BS or 6 with an MS" - each a way in
    paths = [f for f in overall if DEGREE.search(sentence[max(0, f["at"] - 45):f["end"] + 45])]
    if len(paths) >= 2 and re.search(r"\bor\b|/|;", sentence, re.I):
        for f in paths:
            f["path"] = True
    return found


@lru_cache(maxsize=8192)
def asked(description: str | None) -> float | None:
    """The years bar a posting's text sets, or None: no bar it says, a wish only ("preferred"), someone else's.
    The first bar stated; degree paths or levels offered as alternatives, the lowest. 0 = says none needed."""
    if not description or not re.search(r"(?i)\b(?:years?|yrs?|months?)\b|\bno (?:\w+ )*experience\b", description):
        return None
    section, none_needed, found = "must", False, []
    for raw in plain.html_to_text(description).replace("’", "'").replace("‘", "'").splitlines():
        line = BULLET.sub("", " ".join(raw.split())).strip()
        if not line:
            continue
        none_needed = none_needed or bool(NO_EXPERIENCE.search(line))
        if opened := heading(line):
            section = opened
            continue
        for sentence in filter(None, map(str.strip, SENTENCE.split(line))):
            found += mentions(sentence, section)
    musts = [f for f in found if f["kind"] == "must"] or [f for f in found if f["kind"] == "unclear"]
    overall = [f for f in musts if f["scope"] == "overall"]
    if not overall:
        skill = [f for f in musts if f["scope"] == "skill"]
        return skill[0]["years"] if skill else 0 if none_needed else None
    first = overall[0]
    return min(f["years"] for f in overall if f.get("path")) if first.get("path") else first["years"]
