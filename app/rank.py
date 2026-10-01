import argparse
import re
from collections import defaultdict
from datetime import datetime, timezone

import cfg
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
_JUNIOR = r"intern|internship|junior|jr|entry[ -]level|trainee|apprentice"
_TOP = r"director|vp|vice president|chief|head of"
# level -> (words above it, words below it)
LEVEL_MISMATCH = {
    "entry": (rf"senior|sr|principal|lead|{_TOP}", None),
    "mid": (_TOP, r"intern|internship|trainee|apprentice"),
    "senior": (None, _JUNIOR),
    "leader": (None, _JUNIOR),
}


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
    # the job search's own tags: a job w/o one is never hidden by them
    if job.get("employment_type") and job["employment_type"] in (blocklist.get("employment_types") or []):
        return True
    if blocklist.get("clearance") and job.get("requires_clearance"):
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


def mismatches(job: dict, rc: dict) -> list[str]:
    out = []
    above, below = LEVEL_MISMATCH.get(rc.get("career_level") or "", (None, None))
    title = job.get("title") or ""
    if above and words(above).search(title):
        out.append("title above your level")
    if below and words(below).search(title):
        out.append("title below your level")
    wanted = rc.get("employment_types") or []
    if wanted and job.get("employment_type") and job["employment_type"] not in wanted:
        human = lambda t: t.replace("_", " ")
        out.append(f"{human(job['employment_type'])}, you asked {' or '.join(map(human, wanted))}")
    return out


def sponsorship(job: dict, config: dict) -> list[str]:
    """User needs a visa sponsor and freehire marks this job as never sponsoring. A weak label
    (docs/jobs/freehire.md #Visa sponsorship): demoted like a mismatch, never hidden."""
    needs = (config.get("work_authorization") or {}).get("needs_sponsorship")
    return ["says no visa sponsorship"] if needs and (job.get("enrichment") or {}).get("visa_sponsorship") is False else []


def clearance(job: dict) -> list[str]:
    """Job asks for a US security clearance (the job search's own flag: Secret, TS/SCI,
    polygraph...; 45,763 US jobs 2026-10-01). Named on every such job, so a user can see it."""
    return ["needs a security clearance"] if job.get("requires_clearance") else []


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
    kept = collapse([dict(j, stale=stale_for(j, rc, now)) for j in jobs if not blocked(j, config["blocklist"])])
    # Order, most decisive first:
    # tier - user's own where-first choice;
    # stale - no fetch returned it in rank.stale_days: probably filled, so below every live row,
    #   yet shown - hiding an open job costs a chance, showing a closed one costs a click;
    # demerits - likely ghost / wrong level / wrong hours / no sponsor for a user who needs one /
    #   a clearance the user can't hold:
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
        bool(doubts(j, rc)) + len(mismatches(j, rc)) + len(sponsorship(j, config))
        + (bool(clearance(j)) and can_hold_clearance(config) is False),
        not meets_floor(j, rc["salary_floor_usd"]),
        -(annual_usd(j) or 0),
        not collections_hit(j, rc["boost_collections"]),
    ))
    return kept


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
    label = pay_label(job)
    if label and rc["salary_floor_usd"]:
        label += " (meets your pay)" if meets_floor(job, rc["salary_floor_usd"]) else " (below your pay)"
    hits = [COLLECTION_NAMES.get(c, c) for c in job.get("collections") or [] if c in rc["boost_collections"]]
    parts = [place, label or "pay not listed", *hits,
             age_label(job, now or datetime.now(timezone.utc)) if when is None else when]
    if 1 < reposts(job) < rc["repost_demote"]:
        parts.append(f"reposted {reposts(job)}x")
    parts += doubts(job, rc) + mismatches(job, rc) + sponsorship(job, config) + clearance(job)
    if job.get("stale"):
        parts.append(f"may be closed - not seen in {job['stale']}d")
    return " · ".join(p for p in parts if p)


def would_hide(jobs: list[dict], phrase: str, blocklist: dict) -> list[dict]:
    """Rows a new title phrase would hide that nothing hides today."""
    probe = {"title_phrases": [phrase], "title_keep": blocklist.get("title_keep")}
    return [j for j in jobs if not blocked(j, blocklist) and blocked(j, probe)]


def suspects(jobs: list[dict], min_categories: int) -> list[tuple[str, set[str]]]:
    cats = defaultdict(set)
    for j in jobs:
        if j.get("category"):
            cats[j["company_slug"]].add(j["category"])
    return sorted(((c, s) for c, s in cats.items() if len(s) >= min_categories), key=lambda cs: -len(cs[1]))


def row(job: dict, config: dict, now: datetime) -> str:
    """One printed line: job number first (same in every chat, email, Today page), link = the
    posting's real address, slug last."""
    new = "-" if job["seen"] else "NEW"
    return (f"#{job['num']:<4} {new:3} {job['tier']:6} {job['title'][:60]} | {job['company']}  "
            f"[{reasons(job, config, now)}]  {job['url']}  {job['public_slug']}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Print ranked open jobs")
    ap.add_argument("--db", help="override config db path")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--suspects", action="store_true", help="list companies spanning unrelated categories")
    ap.add_argument("--would-hide", metavar="PHRASE", help="count + sample titles a title phrase would hide")
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
    now = datetime.now(timezone.utc)
    for j in store.numbered(conn, rank(jobs, config, now)[: args.limit]):
        print(row(j, config, now))


if __name__ == "__main__":
    main()
