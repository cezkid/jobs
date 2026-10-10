"""Pay range a posting states in its own words, for rows the job search left without one.

Pay-transparency laws put the range in the text; the job search's own pay field misses most of it
outside tech. 2026-10-09, US HR-titled rows (full descriptions): pay field set on 1-8% per title
search, a "$..." amount in the text on 28-50%. Facts + hand check: app/docs/jobs/pay-filter.md
#Pay read from the posting.

Reads a dollar range (or one amount said as pay) next to pay words, a period or "USD"; never a
budget, revenue, bonus, stipend or an amount in millions. One-way: a row whose field has pay keeps it.
"""
import re

from text import html_to_text

_AMOUNT = r"(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?\s?([kK])?(?![\w,]*\d)"
_DASH = r"\s*(?:(?:per|/|a|an)\s*(?:year|yr|hour|hr)\s*)?(?:-{1,2}|–|—|to|and|through)\s*"
RANGE = re.compile(rf"\$\s?{_AMOUNT}(?:\s*USD)?{_DASH}(?:USD\s*)?\$?\s?{_AMOUNT}")
SINGLE = re.compile(rf"\$\s?{_AMOUNT}")
PERIOD = re.compile(r"^\+?\s*(?:USD\b\s*)?(?:per|an|a|every|/)?\s*(hour|hr|h|hourly|year|yr|annually|annual|annum|month|monthly|mo|"
                    r"week|weekly|wk|bi-?weekly|two weeks|day|daily)\b", re.I)
PERIODS = {"hour": "hour", "hr": "hour", "h": "hour", "hourly": "hour", "year": "year", "yr": "year", "annually": "year",
           "annual": "year", "annum": "year", "month": "month", "monthly": "month", "mo": "month"}
# paid by the week or fortnight (state + county jobs): said per year, the unit rank compares in
PER_YEAR = {"week": 52, "weekly": 52, "wk": 52, "biweekly": 26, "bi-weekly": 26, "two weeks": 26}
# per day: shift and per-diem rates, never comparable to a yearly floor - left unread
UNREAD = {"day", "daily"}
USD_AFTER = re.compile(r"^\s*USD\b")
# words before the amount that say it is pay (a range needs these, a period or "USD" after it)
PAY = re.compile(r"\b(?:salary|salaries|pay|paid|wage|wages|compensation|base|rate|range|band|starting at|"
                 r"starts at|annual|hourly|OTE|earn|earning)\b", re.I)
# not pay when it names the amount: "budget of $5M", "up to $85/month reimbursement", "$5,000 sign-on bonus"
_NOT_PAY = (r"budgets?|revenues?|sales|assets|portfolios?|funding|raised|grants?|donations?|endowment|bonus(?:es)?|"
            r"sign[- ]on|signing|relocation|stipends?|tuition|reimburse\w*|referral|allowance|credits?|"
            r"savings|spend|contracts?|deductibles?|premiums?|match(?:ing)?|fees?|costs?|purchases?|gifts?|"
            r"million|billion|fund(?:s|ed|raising)?")
# a benefit's own cost, said before it ("Medical starts at $8/week"); after a range these start the
# next line of the posting ("$130,000-150,000 Medical, dental ..."), so before only, and never
# "Compensation and Benefits: $23/hr"
_BENEFIT = r"medical|dental|vision|insurance|plans?|benefits?|wellness|lifestyle"
# connectors only - "(excluding equity and bonus): $205k" is pay, the bracket ends the aside
NOT_PAY_BEFORE = re.compile(rf"\b(?:{_NOT_PAY}|(?<!and )(?<!& )(?:{_BENEFIT}))[\s:,-]+(?:(?:of|up to|to|about|over|nearly|approximately|around|a|an|the|"
                            rf"than|exceeding|totaling|totalling|worth|in|at|with|and|or|starts? at|starting at|"
                            rf"under|for|is|are)[\s:,-]+){{0,3}}$", re.I)
# the amount names it: "$5,000 sign-on bonus", "$2,000 attendance bonus" - "+ bonus" after pay is still pay
NOT_PAY_AFTER = re.compile(rf"^\s?(?:USD\s)?(?:[\w-]+\s)?(?:{_NOT_PAY})\b", re.I)
MILLIONS = re.compile(r"^\s?(?:m|mm|b|bn|million|billion)\b", re.I)
# a sum outside these is a misread, never pay (yearly $15k-$1.5M, hourly $7-$500, monthly $1k-$60k)
SANE = {"year": (15000, 1500000), "hour": (7, 300), "month": (1000, 60000)}
RANGE_BEHIND, SINGLE_BEHIND, AHEAD = 250, 60, 30


def _value(whole: str, cents: str | None, k: str | None) -> float:
    v = float(whole.replace(",", "") + (f".{cents}" if cents else ""))
    return v * 1000 if k else v


def _period(after: str, hi: float) -> tuple[str, int, bool]:
    """Period said right after the amount, else read off its size: (period, multiplier to it, said).
    Weekly + biweekly sums come back yearly; a day rate comes back None."""
    m = PERIOD.search(after)
    if m:
        word = m.group(1).lower()
        if word in UNREAD:
            return "", 0, True
        if word in PER_YEAR:
            return "year", PER_YEAR[word], True
        return PERIODS[word], 1, True
    return ("hour" if hi < 1000 else "month" if hi < 10000 else "year"), 1, False


def ranges(text: str) -> list[tuple[float, float, str]]:
    """Every (low, high, period) the text states as pay, in reading order."""
    out, taken = [], []
    for rx, single in ((RANGE, False), (SINGLE, True)):
        for m in rx.finditer(text):
            if any(a <= m.start() < b for a, b in taken):
                continue
            before = text[max(0, m.start() - (SINGLE_BEHIND if single else RANGE_BEHIND)):m.start()]
            after = text[m.end():m.end() + AHEAD]
            if MILLIONS.search(after) or NOT_PAY_BEFORE.search(before) or NOT_PAY_AFTER.search(after):
                continue
            g = m.groups()
            lo = _value(*g[:3])
            hi = lo if single else _value(*g[3:6])
            # "$150 - 180K": the k on the second number covers the first
            if not single and g[5] and not g[2] and lo < 1000 <= hi:
                lo *= 1000
            period, times, said = _period(after, max(lo, hi))
            if not period or not (said or PAY.search(before) or (not single and USD_AFTER.search(after))):
                continue
            # "$107,744 - $71,875": a range written high to low
            lo, hi = sorted((round(lo * times, 2), round(hi * times, 2)))
            low, high = SANE[period]
            if not (low <= lo and hi <= high):
                continue
            taken.append((m.start(), m.end()))
            out.append((m.start(), lo, hi, period))
    return [r[1:] for r in sorted(out)]


def stated(description: str | None) -> tuple[float, float, str] | None:
    """The posting's pay as one range: lowest low to highest high among ranges in the first one's
    period (a range per city or level reads as their span). None = no pay said as pay."""
    found = ranges(html_to_text(description))
    if not found:
        return None
    period = found[0][2]
    same = [r for r in found if r[2] == period]
    return min(r[0] for r in same), max(r[1] for r in same), period
