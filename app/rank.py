import argparse
import re
from collections import defaultdict
from datetime import datetime, timezone

import cfg
import software
import store

PERIODS_PER_YEAR = {"year": 1, "month": 12, "week": 52, "day": 260, "hour": 2080}
# period missing: a figure this small cannot be yearly pay
HOURLY_BELOW, MONTHLY_BELOW = 1000, 10000
COMPANY_SUFFIXES = {"inc", "llc", "ltd", "corp", "corporation", "co", "company", "plc", "lp", "llp"}
COLLECTION_NAMES = {"fortune500": "Fortune 500", "bigtech": "big tech", "mag7": "Magnificent 7",
                    "unicorn": "unicorn startup", "yc": "Y Combinator"}
# posting this much older than its day on the user's list => its own age shown too (a repost or
# long-open job reaching the list now); closer than that the two read the same
POSTING_AGE_GAP = 7
# title words that clearly contradict a stated career level; a title without any is never demoted
_JUNIOR = r"interns?|internships?|co-?op|junior|jr|entry[ -]level|trainee|apprentice"
_TOP = r"director|vp|vice president|chief|head of"
# individual-contributor + support titles: below "Manager, director or executive" (leader) unless the
# title also names a role that leads (LEADS). 2026-10-09, 3,341 US HR-titled rows: 1,301 carry one of
# these and no leading word - generalist 430, specialist 227, coordinator 181, analyst 97, assistant 85,
# associate 46, recruiter 37 ... For a head of HR they filled half the list
_SUPPORT = (r"coordinators?|assistants?|specialists?|generalists?|associates?|clerks?|representatives?|reps?|"
            r"analysts?|recruiters?|sourcers?|technicians?|aides?|schedulers?|processors?|receptionists?")
LEADS = r"manager|director|head|chief|vp|svp|evp|vice[- ]president|officer|president|lead|leader|principal|partner|" \
        r"supervisor|superintendent|dean|executive director"
# support roles even beside a leader's title: "Executive Assistant to the Chief People Officer"
SUPPORT_ALWAYS = r"executive assistants?|assistants? to|administrative (?:assistant|coordinator)s?|admin coordinators?"
# a first-rung title, numbered: "Information Security Analyst I", "Tier 1 SOC Analyst", "Help Desk Level 1",
# "L1". 2026-10-09, 5,248 US security rows: 85 (76 end in "I"). Below senior + leader unless the title also
# says senior or leads ("Sr. Cybersecurity Engineer I"); a DoD cert level in a title ("IAT Level I") is no rung
FIRST_RUNG = re.compile(r"(?<![\w&-])I(?=\s*(?:$|[-,(|/–:]))|(?i:\btier[\s-]*(?:1|i)\b|\blevel[\s-]*(?:1|i)\b|\bL1\b)")
DOD_LEVEL_IN_TITLE = re.compile(r"(?i)\b(?:IAT|IAM|IASAE)[\s-]*(?:Level[\s-]*)?(?:III|II|I|[123])\b")
# level -> (words above it, words below it)
LEVEL_MISMATCH = {
    "entry": (rf"senior|sr|principal|lead|{_TOP}", None),
    "mid": (_TOP, r"interns?|internships?|co-?op|trainee|apprentice"),
    "senior": (None, _JUNIOR),
    "leader": (None, _JUNIOR),
}


# a title naming an early-career job: where the job search's experience_years_min tag misreads
# most (10 on "Software Engineer - New Grad", 20 on "Entry Level Sales Representative", 2026-10-07)
EARLY_CAREER = rf"{_JUNIOR}|new (?:college )?grad(?:uate)?s?|early career|graduate program|university grad(?:uate)?"
# a shop's shift lead is an hourly floor role, not a level above entry
ENTRY_TITLE_KEEP = re.compile(r"\bshift (?:lead|leader|supervisor)\b", re.I)
# the job search tags 87 of 300 real internships full time (summer hours) and 17 part time
# (2026-10-07, newest intern-titled US rows): the title says what the job is. One way only - a
# title can keep a job its tag would hide or sort lower, never hide one ("Intern Program Manager")
# Freelance / temporary titles (2026-10-09, 63 on 3,000 newest video, creative, finance, software,
# healthcare, marketing US rows): tagged contract 38, part time 15, full time 5, internship 4 => contract
TITLE_TYPES = (("internship", re.compile(r"(?<!\w)(?:interns?|internships?|co-?op|co op)(?!\w)", re.I)),
               ("part_time", re.compile(r"(?<!\w)part[- ]time(?!\w)", re.I)),
               ("contract", re.compile(r"(?<!\w)(?:freelancer?|temporary|temp)(?!\w)", re.I)))
# a student programme titled without an intern word ("2027 Summer Analyst Program", "Rotational
# Program", "Fellowship", "University New Hire"): 16 of 133 such titles on 442 intern-tagged
# business rows, 2026-10-08; the other 117 were ordinary jobs (Account Executive, a VP)
STUDENT_PROGRAM = (r"fellows?|fellowships?|students?|scholars?|rotational|rotation|campus|career fair"
                   r"|university (?:new )?(?:hire|grad|graduate|recruit)s?|new hires?|summer (?:analyst|associate)s?"
                   r"|(?:summer|analyst|associate|development|leadership|graduate|trainee|early talent|emerging talent)"
                   r" program(?:me)?s?|20\d\d grads?|class of 20\d\d")
# entry level: a required line asking this many years or more is a job for someone further on
# (knockout.years_asked reads the posting's own line; the job search's experience_years_min tag read
# 10 on "Software Engineer - New Grad" and 7 on "18+ years old", 2026-10-07)
ENTRY_MAX_YEARS = 3
# graduation compared only while studying or this soon after: a year further back says nothing
# about an internship's window, and a year they hid stays hidden
GRADUATION_RECENT_MONTHS = 24


def words(phrase: str) -> re.Pattern:
    """Whole-word, case-insensitive: "intern" hides "Tax Intern", never "Internal Auditor"."""
    return re.compile(rf"(?<!\w)(?:{phrase})(?!\w)", re.I)


def norm(text: str | None) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", (text or "").lower()).split())


def norm_company(name: str | None) -> str:
    parts = norm(name).split()
    while len(parts) > 1 and parts[-1] in COMPANY_SUFFIXES:
        parts.pop()
    return " ".join(parts)


def blocked(job: dict, blocklist: dict) -> bool:
    fields = {"companies": "company_slug", "sources": "source", "categories": "category"}
    for key, field in fields.items():
        blocked_values = {v.lower() for v in blocklist.get(key) or []}
        if (job.get(field) or "").lower() in blocked_values:
            return True
    if norm_company(job.get("company")) in {norm_company(c) for c in blocklist.get("companies") or []}:
        return True
    # the job search's own tags: a job w/o one is never hidden by them, nor one whose title names
    # a type they kept (an internship tagged full time)
    hidden_types = blocklist.get("employment_types") or []
    if job.get("employment_type") in hidden_types and job.get("employment_type") \
            and not ((t := title_type(job)) and t not in hidden_types):
        return True
    if blocklist.get("clearance") and job.get("requires_clearance"):
        return True
    # kinds of software work they chose to hide, by title only: "Java Full Stack" stays when only back-end is
    if software.hidden(job, blocklist.get("software_kinds")):
        return True
    return title_blocked(job.get("title") or "", blocklist)


def slashes(text: str) -> str:
    """"Senior / Staff" and "Senior/Staff" read alike."""
    return re.sub(r"\s*/\s*", "/", text)


def title_blocked(title: str, blocklist: dict) -> bool:
    """title_phrases match whole words, never inside a title_keep phrase: keep "member of
    technical staff" + phrase "staff" hides "Staff Engineer", not "Member of Technical Staff"."""
    title = slashes(title)
    for keep in blocklist.get("title_keep") or []:
        title = words(re.escape(slashes(keep))).sub(" ", title)
    return any(words(re.escape(p)).search(title) for p in blocklist.get("title_phrases") or [])


def pay(job: dict) -> tuple[float, float, str] | None:
    """(low, high, period) in USD; period inferred from size when the posting omits it."""
    lo, hi = job.get("salary_min"), job.get("salary_max")
    if job.get("salary_currency") != "USD" or (lo is None and hi is None):
        return None
    lo, hi = lo if lo is not None else hi, hi if hi is not None else lo
    period = job.get("salary_period")
    if period not in PERIODS_PER_YEAR:
        period = "hour" if hi < HOURLY_BELOW else "month" if hi < MONTHLY_BELOW else "year"
    return lo, hi, period


def annual_usd(job: dict) -> float | None:
    """Midpoint of the range, per year - the one number rows are ordered by."""
    p = pay(job)
    return (p[0] + p[1]) / 2 * PERIODS_PER_YEAR[p[2]] if p else None


def meets_floor(job: dict, floor: float) -> bool:
    # top of the range: a $55k-$90k job is open to someone asking $60k
    p = pay(job)
    return bool(p) and p[1] * PERIODS_PER_YEAR[p[2]] >= floor


def money(x: float) -> str:
    return f"{x:,.2f}".removesuffix(".00")


def pay_label(job: dict) -> str:
    p = pay(job)
    if not p:
        return ""
    lo, hi, period = p
    if period == "hour":
        return f"${money(lo)}/hr" if lo == hi else f"${money(lo)}-{money(hi)}/hr"
    lo, hi = lo * PERIODS_PER_YEAR[period] // 1000, hi * PERIODS_PER_YEAR[period] // 1000
    return f"${lo:.0f}k" if lo == hi else f"${lo:.0f}k-{hi:.0f}k"


def hourly_floor(rc: dict) -> bool:
    return rc.get("salary_floor_unit") == "hour"


def floor_words(rc: dict, floor: float | None = None) -> str:
    """Their lowest pay in the unit they gave it: "$22/hr" (stored yearly, x 2080) or "$60,000"."""
    floor = rc.get("salary_floor_usd") if floor is None else floor
    if hourly_floor(rc):
        return f"${money(round(floor / PERIODS_PER_YEAR['hour'], 2))}/hr"
    return f"${floor:,.0f}"


def parse_floor(text: str) -> tuple[int, str]:
    """"22/hr", "$22 an hour", "45000" -> (yearly USD, unit). An hourly floor is kept yearly
    (x 2080) so every comparison stays one sum; the unit only changes how it is said."""
    m = re.fullmatch(r"\$?\s*([\d,]+(?:\.\d+)?)\s*(/\s*(?:hr|hour|h)|an? hour|per hour|hourly)?", text.strip(), re.I)
    if not m:
        raise ValueError(f"{text!r}: a pay like 22/hr or 45000")
    value = float(m[1].replace(",", ""))
    hourly = bool(m[2]) or value < HOURLY_BELOW
    return round(value * PERIODS_PER_YEAR["hour"]) if hourly else round(value), "hour" if hourly else "year"


def incomparable(job: dict, rc: dict) -> bool:
    """A part-time job listing a yearly or monthly sum against an hourly floor: the hours behind
    the sum are unknown ($25,000 for 20 hours a week is $24/hr), so it is never read as low pay."""
    p = pay(job)
    return hourly_floor(rc) and bool(p) and p[2] in ("year", "month") and job_type(job) == "part_time"


def pay_hidden(job: dict, rc: dict) -> str | None:
    """Why rank.pay_filter hides it: "below" (top of range under the floor), "unlisted" (no USD
    pay to compare - not low pay, just unknown), else None. No floor set => never hidden."""
    pf, floor = rc.get("pay_filter") or {}, rc.get("salary_floor_usd")
    if not floor:
        return None
    if pay(job) is None:
        return "unlisted" if pf.get("hide_unlisted") else None
    if incomparable(job, rc):
        return None
    return "below" if pf.get("hide_below_floor") and not meets_floor(job, floor) else None


def listed_days(job: dict, now: datetime) -> int | None:
    """Days since it reached their list (first fetch)."""
    since = job.get("first_fetched_at")
    return None if not since else (now - datetime.strptime(since[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)).days


def pay_filter(jobs: list[dict], rc: dict, now: datetime) -> list[dict]:
    """The one pay filter every list goes through (rank => Today, chat brief, email, find):
    drops jobs under the pay floor (and, per setting, w/o pay listed); rows stay in jobs.db.
    Relax: fewer than relax_under_new_per_week live jobs that pass reached the list in the last
    7 days => hidden ones from that week come back up to it, closest first - below-floor
    nearest the floor (pay known, gap small), then pay not listed, newest first (unknown, could
    be either). Each back carries `pay_relaxed` = why it was hidden, named in its reasons."""
    hide = [pay_hidden(j, rc) for j in jobs]
    if not any(hide):
        return jobs
    want = (rc.get("pay_filter") or {}).get("relax_under_new_per_week") or 0
    week = lambda j: not j.get("stale") and (d := listed_days(j, now)) is not None and d < 7
    short = want - sum(1 for j, h in zip(jobs, hide) if not h and week(j))
    pool = sorted((i for i, j in enumerate(jobs) if hide[i] and week(jobs[i])), key=lambda i: (
        hide[i] == "unlisted", -(top_annual(jobs[i]) or 0), listed_days(jobs[i], now)))
    back = set(pool[:max(0, short)])
    return [dict(j, pay_relaxed=hide[i]) if i in back else j
            for i, j in enumerate(jobs) if not hide[i] or i in back]


def pay_probe(jobs: list[dict], config: dict, floor: float, hide_unlisted: bool, now: datetime) -> str:
    """What a floor would hide among the rows shown today (blocklist + max_age_days applied, pay
    filter off) - the narrowing count AGENTS.md wants said before saving."""
    off = cfg.merge(config, {"rank": {"pay_filter": {"hide_below_floor": False, "hide_unlisted": False}}})
    rc = cfg.merge(config["rank"], {"salary_floor_usd": floor,
                                    "pay_filter": {"hide_below_floor": True, "hide_unlisted": hide_unlisted}})
    shown, out = rank(jobs, off, now), []
    week = [j for j in shown if (d := listed_days(j, now)) is not None and d < 7]
    for label, rows in (("open", shown), ("reached your list in the last 7 days", week)):
        why = [pay_hidden(j, rc) for j in rows]
        out.append(f"{label}: {len(rows)} - keeps {why.count(None)}, hides {why.count('below')} below"
                   f" {floor_words(rc, floor)}" + (f" + {why.count('unlisted')} with no pay listed" if hide_unlisted else
                                        f" (no pay listed, kept: {sum(1 for j in rows if pay(j) is None)})"))
    return "\n".join(out)


def top_annual(job: dict) -> float | None:
    p = pay(job)
    return p[1] * PERIODS_PER_YEAR[p[2]] if p else None


def pay_words(job: dict, rc: dict) -> str:
    """Pay in a job's why: shown against their floor; one the pay filter let back says so."""
    label = pay_label(job)
    if job.get("pay_relaxed") == "below":
        return f"below your pay: {label} (few new jobs this week)"
    if job.get("pay_relaxed") == "unlisted":
        return "pay not listed (few new jobs this week)"
    if label and rc["salary_floor_usd"] and not incomparable(job, rc):
        label += " (meets your pay)" if meets_floor(job, rc["salary_floor_usd"]) else " (below your pay)"
    return label or "pay not listed"


def has_salary(job: dict) -> bool:
    return job.get("salary_min") is not None or job.get("salary_max") is not None


def collections_hit(job: dict, boost: list[str]) -> bool:
    return bool(set(job.get("collections") or []) & set(boost))


def reposts(job: dict) -> int:
    """Earlier postings of this role that closed: repost_count less mass_posting_count. Both
    count postings sharing the role's fingerprint, the second only the open ones, the job
    itself included - so a role open in 3 cities at once reads 3/3, reposted 0. Raw
    repost_count called those copies "reposted 3x" on 75 of 111 demoted rows of a real list
    (docs/jobs/freehire.md #reality); freehire's own reality classifier subtracts the same way."""
    r = job.get("reality") or {}
    return max(0, (r.get("repost_count") or 0) - (r.get("mass_posting_count") or 1))


def doubts(job: dict, rc: dict) -> list[str]:
    """Plain reasons the posting may be a ghost: relisted often, open for months, or evergreen."""
    r = job.get("reality") or {}
    out = []
    if reposts(job) >= rc["repost_demote"]:
        out.append(f"reposted {reposts(job)}x")
    if (r.get("age_days") or 0) >= rc["old_days"]:
        out.append("old listing")
    if r.get("class") == "likely-evergreen":
        out.append("always-open listing")
    return out


def title_type(job: dict) -> str | None:
    """Employment type the title itself names, or None."""
    title = job.get("title") or ""
    return next((kind for kind, rx in TITLE_TYPES if rx.search(title)), None)


def early_career(job: dict) -> bool:
    return job.get("seniority") in ("intern", "junior") or bool(words(EARLY_CAREER).search(job.get("title") or ""))


def job_type(job: dict) -> str | None:
    """Type as the title says it, else the job search's tag."""
    return title_type(job) or job.get("employment_type")


def below_leader(title: str) -> bool:
    """An individual-contributor or support title, for someone who leads: "HR Generalist", "People
    Operations Coordinator", "Executive Assistant to the CHRO" - never "Assistant Director of HR",
    "Associate Director", "Lead Generalist"."""
    return bool(words(SUPPORT_ALWAYS).search(title)) or bool(words(_SUPPORT).search(title)) and not words(LEADS).search(title)


def first_rung(title: str) -> bool:
    """"Security Analyst I", "Tier 1 SOC Analyst" - not "Sr. Engineer I", "Analyst II", "IAT Level I"."""
    return bool(FIRST_RUNG.search(DOD_LEVEL_IN_TITLE.sub(" ", title))) and not words(rf"senior|sr|principal|lead|staff|manager|{_TOP}|{LEADS}").search(title)


def mismatches(job: dict, rc: dict) -> list[str]:
    out = []
    level = rc.get("career_level") or ""
    above, below = LEVEL_MISMATCH.get(level, (None, None))
    title = job.get("title") or ""
    if above and words(above).search(ENTRY_TITLE_KEEP.sub(" ", title) if level == "entry" else title):
        out.append("title above your level")
    if below and words(below).search(title) or level == "leader" and below_leader(title) \
            or level in ("senior", "leader") and first_rung(title):
        out.append("title below your level")
    wanted, kind = rc.get("employment_types") or [], job_type(job)
    # an intern title below a mid-level user's level already says it: one doubt, not two
    if wanted and kind and kind not in wanted and "title below your level" not in out:
        human = lambda t: t.replace("_", " ")
        out.append(f"{human(kind)}, you asked {' or '.join(map(human, wanted))}")
    # internships only: the job search tags ordinary jobs intern too - 117 of 442 intern-tagged
    # business rows (2026-10-08), 8 of a student's top 15; none whose posting called it an
    # internship but 2 SkillBridge (service members). Title naming none => sorted lower, never hidden
    elif wanted and set(wanted) <= {"internship", "fellowship"} and kind in (None, *wanted) \
            and not title_type(job) and not words(rf"{EARLY_CAREER}|{STUDENT_PROGRAM}").search(title):
        out.append("title doesn't say internship")
    # another kind of software work than theirs (front-end user, back-end title): one reason, sorted lower
    return out + software.mismatch(job, rc.get("software_kinds"))


def required_lines(job: dict) -> list[str]:
    return [r["text"] for r in (job.get("enrichment") or {}).get("requirements") or [] if r.get("priority") == "required"]


def asks_beyond(job: dict, config: dict, graduation: str | None, today, credentials: str | None = None) -> list[str]:
    """What a posting's own required lines ask that the user clearly lacks: 3+ years (entry level
    only), a graduation window theirs misses, a licence or certification their resume details never
    name ("asks Series 24" - compliance, finance and nursing posts ask these outright; one held from
    an either/or list answers it; one their resume says lapsed is "not current"), an active clearance above
    the one their resume shows ("asks an active TS/SCI clearance, your resume shows a Secret clearance").
    Sorted lower, never hidden."""
    from resume import knockout  # light: the posting's lines only
    out = []
    if credentials is not None:
        out += [f"asks {knockout.credential_words(missing, t)}, {knockout.missing_words(missing, credentials)}"
                for t in required_lines(job) if (missing := knockout.credentials_missing(t, credentials))]
        # an active clearance at a level (or a polygraph) their resume doesn't show - once per job. Not for one
        # who can't hold any: the clearance demerit already says it
        if can_hold_clearance(config) is not False and \
                (short := next(filter(None, (knockout.clearance_short(t, credentials) for t in required_lines(job))), None)):
            out.append(f"asks {short[0]}, {short[1]}")
    if config["rank"].get("career_level") == "entry":
        asked = [y for t in required_lines(job) if (y := knockout.years_asked(t)) is not None]
        if asked and max(asked) >= ENTRY_MAX_YEARS:
            out.append(f"asks {max(asked)}+ years")
    reqs = (job.get("enrichment") or {}).get("requirements") or []
    if hit := knockout.graduation_asked({"requirements": reqs}, graduation, today):
        out.append(f"asks graduating {hit[0]}; yours {knockout.window_label(graduation_span(graduation, today))}")
    return out


def graduation_span(graduation: str, today) -> tuple[int, int]:
    from resume import schema
    return schema.month_index(graduation, today), schema.month_index(graduation, today, end=True)


def resume_credentials(config: dict) -> str | None:
    """Their resume details as text a credential is looked for in; none yet or unreadable => None
    (nothing to compare: no job is told it asks something they lack)."""
    from resume import knockout, schema
    try:
        return knockout.credential_text(schema.load(cfg.resume_path(config, "master")))
    except (OSError, ValueError, KeyError):
        return None


def student_graduation(config: dict, today) -> str | None:
    """Their graduation as internship and new-grad windows are read against: a degree in
    progress, or one finished in the last GRADUATION_RECENT_MONTHS, its year not hidden. Read off
    their resume details; none yet or unreadable => None."""
    from resume import schema
    try:
        master = schema.load(cfg.resume_path(config, "master"))
    except (OSError, ValueError, KeyError):
        return None
    when = schema.graduation(master, today)
    school = next((s for s in master.get("education") or [] if s.get("end") == when), {})
    if not when or school.get("hide_year"):
        return None
    now = schema.month_index(schema.PRESENT, today)
    recent = schema.in_progress(school, today) or now - schema.month_index(when, today, end=True) <= GRADUATION_RECENT_MONTHS
    return when if recent else None


def sponsorship(job: dict, config: dict) -> list[str]:
    """User needs a visa sponsor and freehire marks this job as never sponsoring. A weak label
    (docs/jobs/freehire.md #Visa sponsorship): demoted like a mismatch, never hidden."""
    wa = config.get("work_authorization") or {}
    if not (wa.get("needs_sponsorship") and (job.get("enrichment") or {}).get("visa_sponsorship") is False):
        return []
    # CPT and OPT need no employer sponsorship: an internship saying "no sponsorship" may still take them
    return ["says no visa sponsorship - CPT or OPT may still work, read the posting"] if wa.get("student_visa") \
        else ["says no visa sponsorship"]


def clearance(job: dict) -> list[str]:
    """Job asks for a US security clearance (the job search's own flag: Secret, TS/SCI,
    polygraph...; 45,763 US jobs 2026-10-01), or a required line does where the flag is missing (10 of
    549 senior security postings asking one, 2026-10-09). Named on every such job, so a user can see it."""
    from resume import knockout  # light: the posting's lines only
    if job.get("requires_clearance") or any(knockout.SECURITY_CLEARANCE.search(t) and not knockout.CLEARANCE_WISH.search(t)
                                            for t in required_lines(job)):
        return ["needs a security clearance"]
    return []


# What a posting says about its employer, named on the job when the user asked for that kind
# (`rank.posting_says`, set after a values / workplace note). Never hides, never sorts lower: a
# preference, not a fit. Employer's own words only - never a stance looked up elsewhere.
# 2026-10-06, 1,091 US postings (11 categories, 30 days): faith 7 rows / 7 employers, all religious
# schools, dioceses, a church university; defense 41 rows / 8 employers, 0 false ("national
# security" left out: an energy association's goals; 2 defense employers said only that). Politics measured + declined: "advocacy",
# "progressive" matched patient care and legal aid, no party stance (app/docs/about-me.md).
_NONPROFIT = r"(?:non-?profit|not-for-profit|not for profit|501\s*\(\s*c\s*\)\s*\(?\s*3\s*\)?)"
POSTING_SAYS = {
    "faith": ("religious employer", re.compile(
        r"\b(faith[- ]based|christ[- ]centered|catholic|lutheran|baptist|methodist|presbyterian|episcopal|"
        r"(arch)?diocese|ministr(?:y|ies)|jewish (?:community|federation|day school)|islamic (?:school|center|relief)|"
        r"christian (?:school|academy|university|college|ministry|ministries|values|faith|organization|mission|worldview))\b",
        re.I)),
    "defense": ("defense or military work", re.compile(
        r"\b(defen[cs]e (?:technology|technologies|contractor|industry|industrial base|systems|company|programs?)|"
        r"department of (?:defense|war)|DoD|munitions|missiles?|weapons? systems?|warfighters?|"
        r"military (?:capabilities|customers|programs?|systems|applications|contracts?))\b", re.I)),
    # the employer calling itself one ("X is a nonprofit", "X, a 501(c)(3)", "we are a ... not-for-profit"),
    # never an ask ("nonprofit experience preferred") or a client ("clients run ... a large nonprofit")
    "nonprofit": ("nonprofit employer", re.compile(
        rf"\b(?:is|are|as|become|became)\s+(?:a|an|the|one of the)\s+(?:[\w,'’&-]+\s+){{0,6}}?{_NONPROFIT}|"
        rf"(?-i:[A-Z][\w.&'’-]*)\s*,\s+(?:a|an)\s+(?:[\w'’&-]+\s+){{0,4}}?{_NONPROFIT}|"
        rf"\b(?:we are|we're)\s+(?:a|an)?\s*(?:[\w,'’&-]+\s+){{0,5}}?{_NONPROFIT}", re.I)),
}
TAG = re.compile(r"<[^>]+>")


def posting_says(job: dict, rc: dict) -> list[str]:
    """Named in the posting's own words; a nonprofit also when the job search's company record
    calls it one (companies.nonprofit - 3x the employers the text names, about 1 in 7 a misfile:
    two recruiting firms in 20) - said as the record's word, not the posting's."""
    text, wanted = TAG.sub(" ", job.get("description") or ""), rc.get("posting_says") or []
    out = [f"posting says: {words}" for kind, (words, rx) in POSTING_SAYS.items() if kind in wanted and rx.search(text)]
    if "nonprofit" in wanted and job.get("company_nonprofit") and not any("nonprofit" in o for o in out):
        out.append("listed as a nonprofit employer")
    return out


def can_hold_clearance(config: dict) -> bool | None:
    """Setup's answer; else US clearances go to citizens only, so "neither citizen nor green card"
    settles it. A green card alone doesn't - asked, never guessed."""
    wa = config.get("work_authorization") or {}
    if wa.get("can_hold_clearance") is not None:
        return wa["can_hold_clearance"]
    return False if wa.get("citizen_or_permanent_resident") is False else None


def stale_for(job: dict, rc: dict, now: datetime) -> int | None:
    """Days since any fetch returned it, when past rank.stale_days - likely filled
    (close_missing only sees its fetch window). Demoted, not hidden: may still be open."""
    if not job.get("fetched_at"):
        return None
    days = (now - datetime.strptime(job["fetched_at"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)).days
    return days if days > rc["stale_days"] else None


def dedupe_key(job: dict) -> tuple[str, str, str]:
    where = "remote" if job.get("work_mode") == "remote" else norm(next(iter(job.get("cities") or []), job.get("location")))
    return norm_company(job.get("company") or job.get("company_slug")), norm(job.get("title")), where


def collapse(jobs: list[dict]) -> list[dict]:
    """One row per (company, title, place): a live copy over a stale one, then the copy with
    pay, else the earliest seen.
    Kept row carries `duplicates` (other slugs) and `seen` (any copy already notified)."""
    groups = defaultdict(list)
    for j in jobs:
        groups[dedupe_key(j)].append(j)
    kept = []
    for group in groups.values():
        group.sort(key=lambda j: (bool(j.get("stale")), not has_salary(j), j.get("first_fetched_at") or j.get("posted_at") or ""))
        best = dict(group[0], duplicates=[j["public_slug"] for j in group[1:]],
                    seen=any(j.get("alerted_at") for j in group))
        kept.append(best)
    return kept


def rank(jobs: list[dict], config: dict, now: datetime | None = None) -> list[dict]:
    rc = config["rank"]
    tiers = {t: i for i, t in enumerate(cfg.tier_order(config))}
    now = now or datetime.now(timezone.utc)
    kept = pay_filter(collapse([dict(j, stale=stale_for(j, rc, now)) for j in jobs
                                if not blocked(j, config["blocklist"]) and not too_old(j, rc, now)
                                and not far(j, config)]), rc, now)
    # read once per list, kept on each row: the sort key, its reasons and best's demerits all read it
    graduation, credentials = student_graduation(config, now.date()), resume_credentials(config)
    kept = [dict(j, beyond=asks_beyond(j, config, graduation, now.date(), credentials)) for j in kept]
    # Order, most decisive first:
    # tier - user's own where-first choice;
    # stale - no fetch returned it in rank.stale_days: probably filled, so below every live row,
    #   yet shown - hiding an open job costs a chance, showing a closed one costs a click;
    # demerits - likely ghost / wrong level / wrong hours / no sponsor for a user who needs one /
    #   a clearance the user can't hold / a required licence their resume never names:
    #   a trustworthy fitting job beats any pay;
    # pay floor - user's stated minimum (top of range, so a range spanning it counts);
    # pay - a fact about this job, so it outranks employer lists;
    # collections - employer lists, mostly tech-only, so they only order rows pay can't
    #   (no salary listed - most rows outside tech);
    # recency - days since freehire first saw it (see age), a weak signal, last.
    kept.sort(key=lambda j: age(j, now) if age(j, now) is not None else 1 << 30)
    kept.sort(key=lambda j: (
        tiers.get(j["tier"], len(tiers)),
        bool(j["stale"]),
        # ghost reasons are one verdict told several ways (likely-evergreen = two of old,
        # reposted, many copies open, "always hiring" text), so they count once
        bool(doubts(j, rc)) + len(mismatches(j, rc)) + len(sponsorship(j, config)) + len(j["beyond"])
        + (bool(clearance(j)) and can_hold_clearance(config) is False),
        not meets_floor(j, rc["salary_floor_usd"]),
        -(annual_usd(j) or 0),
        not collections_hit(j, rc["boost_collections"]),
    ))
    return kept


def too_old(job: dict, rc: dict, now: datetime) -> bool:
    """User's own cutoff (rank.max_age_days): first seen longer ago hides. Age unknown stays."""
    limit, days = rc.get("max_age_days"), age(job, now)
    return limit is not None and days is not None and days > limit


US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
    "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia", "PR": "Puerto Rico"}
# "Washington, DC", "Washington D.C.", "District of Columbia" - read before the state named Washington
DC_FORMS = re.compile(r"\bWashington,?\s*(?:D\.?\s?C\b\.?|District of Columbia)|\bD\.C\.|\bDC\b|District of Columbia", re.I)
STATE_CODE = re.compile(r"(?<![A-Za-z])([A-Z]{2})(?![A-Za-z])")
# longest first: "West Virginia" before "Virginia". Washington the state only after a comma
# ("Seattle, Washington", "United States, Washington, Redmond"); "Washington, United States" can't tell
STATE_NAME = re.compile(r"\b(" + "|".join(sorted((n for c, n in US_STATES.items() if c not in ("DC", "WA")),
                                                  key=len, reverse=True)) + r")\b|,\s*(Washington)\b", re.I)
NAME_STATE = {n.lower(): c for c, n in US_STATES.items()}


def states_named(location: str | None) -> set[str]:
    """US states a row's location names, as two-letter codes; none written => empty."""
    text = location or ""
    found = {"DC"} if DC_FORMS.search(text) else set()
    text = DC_FORMS.sub(" ", text)
    found |= {c for c in STATE_CODE.findall(text) if c in US_STATES}
    found |= {NAME_STATE[(a or b).lower()] for a, b in STATE_NAME.findall(text)}
    return found


def far(job: dict, config: dict) -> bool:
    """A city tier's row whose location names only states outside the tier's `states` (or only
    places outside the US): the job search's cities match by name alone - "Washington" brought
    Seattle and Redmond into a DC search, "Newark" more Newark CA than NJ (2026-10-08). Remote
    rows, and rows naming no state, stay: can't tell."""
    wanted = {s.upper() for p in config["passes"] if p["tier"] == job.get("tier") for s in p.get("states") or []}
    if not wanted or job.get("work_mode") == "remote":
        return False
    if named := states_named(job.get("location")):
        return not named & wanted
    countries = job.get("countries") or []
    return bool(countries) and "us" not in countries


def age(job: dict, now: datetime) -> int | None:
    """Days since freehire first saw it: reality.age_days, else posted_at - which is restamped
    on recrawl (reality.fake_freshness), so only a fallback."""
    days = (job.get("reality") or {}).get("age_days")
    if days is None and job.get("posted_at"):
        days = (now - datetime.strptime(job["posted_at"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)).days
    return days


def age_label(job: dict, now: datetime) -> str:
    days = age(job, now)
    return "" if days is None else "first seen today" if days < 1 else f"first seen {days}d ago"


def added(job: dict, now: datetime) -> str:
    """Age that agrees w/ "new" (Today page, email): when the job reached their list (first
    fetch), not freehire's first sighting - that alone read "new" next to "first seen 66d ago"
    (real install). Posting's own age added only when POSTING_AGE_GAP+ days older."""
    since = job.get("first_fetched_at")
    listed = 0 if not since else max(0, (now - datetime.strptime(since, store.ISO).replace(tzinfo=timezone.utc)).days)
    out = "added to your list " + ("today" if listed < 1 else "1 day ago" if listed == 1 else f"{listed} days ago")
    posting = age(job, now)
    if posting is not None and posting - listed >= POSTING_AGE_GAP:
        out += f" · posting first seen {posting} days ago"
    return out


def reasons(job: dict, config: dict, now: datetime | None = None, when: str | None = None) -> str:
    """Why the row sits where it does, in plain words, most decisive first. when = the age words
    in place of age_label (Today page + email: added, when it reached the user's list)."""
    rc = config["rank"]
    place = "remote" if job.get("work_mode") == "remote" else next(iter(job.get("cities") or []), job.get("location") or "")
    hits = [COLLECTION_NAMES.get(c, c) for c in job.get("collections") or [] if c in rc["boost_collections"]]
    parts = [place, pay_words(job, rc), *hits,
             age_label(job, now or datetime.now(timezone.utc)) if when is None else when]
    if 1 < reposts(job) < rc["repost_demote"]:
        parts.append(f"reposted {reposts(job)}x")
    parts += (doubts(job, rc) + mismatches(job, rc) + (job.get("beyond") or []) + sponsorship(job, config)
              + clearance(job) + posting_says(job, rc))
    if job.get("stale"):
        parts.append(f"may be closed - not seen in {job['stale']}d")
    return " · ".join(p for p in parts if p)


def would_hide(jobs: list[dict], phrase: str, blocklist: dict) -> list[dict]:
    """Rows a new title phrase would hide that nothing hides today."""
    probe = {"title_phrases": [phrase], "title_keep": blocklist.get("title_keep")}
    return [j for j in jobs if not blocked(j, blocklist) and blocked(j, probe)]


def would_hide_kind(jobs: list[dict], kind: str, blocklist: dict) -> list[dict]:
    """Rows hiding one more kind of software work would hide that nothing hides today."""
    probe = {"software_kinds": [*(blocklist.get("software_kinds") or []), kind]}
    return [j for j in jobs if not blocked(j, blocklist) and blocked(j, probe)]


def suspects(jobs: list[dict], min_categories: int) -> list[tuple[str, set[str]]]:
    cats = defaultdict(set)
    for j in jobs:
        if j.get("category"):
            cats[j["company_slug"]].add(j["category"])
    return sorted(((c, s) for c, s in cats.items() if len(s) >= min_categories), key=lambda cs: -len(cs[1]))


def row(job: dict, config: dict, now: datetime, why: str | None = None) -> str:
    """One printed line: job number first (same in every chat, email, Today page), link = the
    posting's real address, slug last."""
    new = "-" if job["seen"] else "NEW"
    return (f"#{job['num']:<4} {new:3} {job['tier']:6} {job['title'][:60]} | {job['company']}  "
            f"[{why or reasons(job, config, now)}]  {job['url']}  {job['public_slug']}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Print ranked open jobs")
    ap.add_argument("--db", help="override config db path")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--suspects", action="store_true", help="list companies spanning unrelated categories")
    ap.add_argument("--would-hide", metavar="PHRASE", help="count + sample titles a title phrase would hide")
    ap.add_argument("--would-hide-kind", metavar="KIND", choices=list(software.KINDS),
                    help="count + sample titles hiding one kind of software work would hide (software.KINDS)")
    ap.add_argument("--pay-floor", metavar="PAY", help="count what a pay floor would hide - yearly (45000) or"
                    " hourly (22/hr) - all open + last 7 days, before the thin-week relax, to say before saving it")
    ap.add_argument("--hide-unlisted", action="store_true", help="with --pay-floor: no pay listed hides too")
    ap.add_argument("--best", action="store_true", help="Today page's 'Best to apply next' order: open jobs not"
                    " acted on, resume match, asks, pay, where, freshness (app/best.py)")
    args = ap.parse_args()
    config = cfg.load()
    conn = store.connect(args.db or cfg.db_path(config))
    jobs = store.all_jobs(conn)
    if args.suspects:
        for company, categories in suspects(jobs, config["rank"]["suspect_min_categories"]):
            print(f"{company}: {', '.join(sorted(categories))}")
        return
    if args.would_hide:
        hidden = would_hide(jobs, args.would_hide, config["blocklist"])
        print(f'"{args.would_hide}" would hide {len(hidden)} of {len(jobs)} open jobs')
        for j in hidden[:10]:
            print(f"  {j['title']} | {j['company']}")
        return
    if args.would_hide_kind:
        hidden = would_hide_kind(jobs, args.would_hide_kind, config["blocklist"])
        print(f'{software.label(args.would_hide_kind)} titles would hide {len(hidden)} of {len(jobs)} open jobs')
        for j in hidden[:10]:
            print(f"  {j['title']} | {j['company']}")
        return
    now = datetime.now(timezone.utc)
    if args.pay_floor is not None:
        floor, unit = parse_floor(args.pay_floor)
        config = cfg.merge(config, {"rank": {"salary_floor_unit": unit}})
        print(pay_probe(jobs, config, floor, args.hide_unlisted, now))
        if unit == "hour":
            print(f"to save: rank.salary_floor_usd: {floor}  rank.salary_floor_unit: hour  ({floor_words(config['rank'], floor)})")
        return
    if args.best:
        import best  # imports this module
        for j in store.numbered(conn, best.ordered(conn, config, now)[: args.limit]):
            print(row(j, config, now, best.reasons(j, config, now)))
        return
    for j in store.numbered(conn, rank(jobs, config, now)[: args.limit]):
        print(row(j, config, now))


if __name__ == "__main__":
    main()
