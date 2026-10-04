"""Best to apply next: one score per open job the user hasn't acted on, from how well their resume
backs the posting's asks, how much it asks, pay, where, and how fresh it is. Orders the Today
page's "Best to apply next", the chat brief and the morning email - one order everywhere.

Weights: settings `rank.best_next`. Why each factor + its basis: app/docs/jobs/best-next.md.
An estimate for ordering, never a verdict: match is word overlap w/ the resume, not a reading of
it. Tailoring (job-tailor) judges each ask properly, with the user.
"""
import re
from bisect import bisect_left
from datetime import date, datetime, timezone

import cfg
import rank
import store
from resume import knockout, schema, tailor

# seniority facet (row `seniority`, from enrichment) -> rung; career_level (setup answer) -> rung.
# "above yours" = 2+ rungs up: a mid-level applying to a senior post is ordinary, to a lead isn't
SENIORITY = {"intern": 0, "junior": 1, "middle": 2, "senior": 3, "lead": 4, "staff": 4, "principal": 5,
             "director": 5, "c_level": 6}
CAREER = {"entry": 1, "mid": 2, "senior": 3, "leader": 5}
# a required ask that hands over a team or a whole area: weighs as two asks
LEAD = re.compile(r"\b(?:lead|leads|leading|own|owns|ownership|manage|manages|managing|direct|directs|oversee|"
                  r"oversees|oversight|supervis\w*|head)\b", re.I)
# words every requirement uses: never what makes it this job's ask
FILLER = set("""a an and or the of in on for to with within at by from as is are be being been this that these those
your you our we their its it any all other such related relevant similar equivalent including include includes
experience experienced years year yrs plus minimum least ability able strong excellent good solid proven demonstrated
knowledge understanding familiarity familiar working work proficiency proficient skills skill required requirement
preferred must have has having must should will can using use used new etc e.g ie well highly advanced basic
environment fast paced team teams across multiple various""".split())
STEM = 6


def stems(text: str) -> set[str]:
    """Content words cut to their first 6 letters: "reconciliation" = "reconcile", "accountant" =
    "accounting". Crude on purpose - an order, not a verdict."""
    return {w[:STEM] for w in re.findall(r"[a-z][a-z0-9+#]*", text.lower()) if len(w) > 1 and w not in FILLER}


def named(text: str) -> set[str]:
    """Tools + products a requirement names (capitalised mid-sentence: Excel, SAP, SQL)."""
    return {stems(t).pop() for t in tailor.NAMED_TERM.findall(text) if stems(t)}


def resume_facts(config: dict, today: date) -> dict | None:
    """What the match reads off their resume details; none yet (or unreadable) => None."""
    path = cfg.resume_path(config, "master")
    try:
        master = schema.load(path)
    except (OSError, ValueError):
        return None
    parts = [master.get("summary") or "", master.get("headline") or ""]
    for group in ("roles", "projects"):
        for e in master.get(group) or []:
            parts += [e.get("title") or "", e.get("name") or "", e.get("blurb") or ""]
            parts += [b["claim"] if isinstance(b, dict) else str(b) for b in e.get("bullets") or []]
            parts += [s for b in e.get("bullets") or [] if isinstance(b, dict) for s in b.get("stack") or []]
    parts += [i for g in master.get("skills") or [] for i in g.get("items") or []]
    for e in master.get("education") or []:
        parts += [e.get("degree") or "", e.get("field") or "", e.get("details") or ""]
    parts += [c if isinstance(c, str) else " ".join(map(str, c.values())) for c in master.get("certifications") or []]
    levels = [knockout.degree_held(e) for e in master.get("education") or []]
    held = max((knockout.LADDER.index(lv) for lv in levels if lv), default=None)
    return {"stems": stems(" ".join(parts)), "years": knockout.dated_years(master, today),
            "degree": held if None not in levels else "unknown"}


def backed(text: str, facts: dict) -> bool | None:
    """Does the resume back one required ask? None = can't tell from words (a trait everyone
    claims: tailoring shows it w/ a line, bullets.md) => not counted either way."""
    years = knockout.years_asked(text)
    if years is not None:
        return None if facts["years"] is None else facts["years"] >= years
    degree = knockout.degree_asked(text)
    if degree:
        held = facts["degree"]
        return None if held == "unknown" else held is not None and held >= knockout.LADDER.index(degree)
    if tailor.is_trait(text):
        return None
    tools = named(text)
    if tools & facts["stems"]:
        # "SQL, Python, R, or other tools": one named tool they have answers the ask
        return True
    words = stems(text)
    return bool(words) and len(words & facts["stems"]) * 2 >= len(words)


def required(job: dict) -> list[str]:
    return [r["text"] for r in (job.get("enrichment") or {}).get("requirements") or [] if r.get("priority") == "required"]


def match(job: dict, facts: dict | None) -> tuple[float, tuple[int, int] | None]:
    """Share of required asks the resume backs; years asked (experience_years_min) one more ask
    when no line said it. No resume or no asks => neutral 0.5."""
    if facts is None:
        return 0.5, None
    asks = required(job)
    verdicts = [backed(t, facts) for t in asks]
    years = (job.get("enrichment") or {}).get("experience_years_min")
    if years and facts["years"] is not None and not any(knockout.years_asked(t) is not None for t in asks):
        verdicts.append(facts["years"] >= years)
    counted = [v for v in verdicts if v is not None]
    if not counted:
        return 0.5, None
    return sum(counted) / len(counted), (sum(counted), len(counted))


def above_level(job: dict, config: dict) -> bool:
    level = CAREER.get(config["rank"].get("career_level") or "")
    rung = SENIORITY.get(job.get("seniority") or "")
    return level is not None and rung is not None and rung >= level + 2


def asks(job: dict, config: dict, bn: dict) -> tuple[float, int, int]:
    """1 = light, 0 = heavy: required asks + lead/manage duties (each counts twice) between
    asks_light and asks_heavy; a level 2+ rungs above theirs halves it. No asks listed => 0.5."""
    texts = required(job)
    lead = sum(bool(LEAD.search(t)) for t in texts)
    if not texts:
        score = 0.5
    else:
        load = len(texts) + lead
        score = min(1.0, max(0.0, (bn["asks_heavy"] - load) / (bn["asks_heavy"] - bn["asks_light"])))
    return (score / 2 if above_level(job, config) else score), len(texts), lead


def pay(job: dict, ladder: list[float], floor: float) -> float:
    """Place among the listed pay of the jobs scored (`ladder`, sorted; 0 lowest, 1 highest); under their floor
    halves it. Not listed => 0.25: unknown, below a listed middle."""
    annual = rank.annual_usd(job)
    if annual is None:
        return 0.25
    place = 1.0 if len(ladder) < 2 else bisect_left(ladder, annual) / (len(ladder) - 1)
    return place / 2 if floor and not rank.meets_floor(job, floor) else place


def where(job: dict, tiers: list[str]) -> float:
    """Their own where-first order (search settings passes): first tier 1, last 0."""
    if job.get("tier") not in tiers:
        return 0.0
    return 1.0 if len(tiers) < 2 else 1 - tiers.index(job["tier"]) / (len(tiers) - 1)


def posted_days(job: dict, now: datetime) -> int | None:
    """Days since the posting went up (freehire's first sighting, rank.age), else since it
    reached their list."""
    days = rank.age(job, now)
    if days is None and job.get("first_fetched_at"):
        days = (now - datetime.strptime(job["first_fetched_at"], store.ISO).replace(tzinfo=timezone.utc)).days
    return None if days is None else max(0, days)


def fresh(job: dict, now: datetime, fresh_days: int) -> float:
    """Newer is better, linear to 0 at fresh_days. Unknown => 0.5."""
    days = posted_days(job, now)
    return 0.5 if days is None else max(0.0, 1 - days / fresh_days)


def demerits(job: dict, config: dict) -> int:
    """Same count rank.rank demotes by: likely ghost (once), level/hours mismatch, no sponsor,
    clearance they can't hold."""
    rc = config["rank"]
    return (bool(rank.doubts(job, rc)) + len(rank.mismatches(job, rc)) + len(rank.sponsorship(job, config))
            + (bool(rank.clearance(job)) and rank.can_hold_clearance(config) is False))


def score(jobs: list[dict], config: dict, now: datetime, facts: dict | None) -> list[dict]:
    """Each job + `best` (0-1 weighted mean less demerits) + `best_parts`, best first. Ties:
    slug order, so the same list always reads the same."""
    bn = config["rank"]["best_next"]
    weights = {k: bn[k] for k in ("match", "asks", "pay", "where", "fresh")}
    tiers, floor = cfg.tier_order(config), config["rank"]["salary_floor_usd"]
    ladder = sorted(a for j in jobs if (a := rank.annual_usd(j)) is not None)
    out = []
    for j in jobs:
        m, counted = match(j, facts)
        a, n_asks, lead = asks(j, config, bn)
        parts = {"match": m, "asks": a, "pay": pay(j, ladder, floor), "where": where(j, tiers),
                 "fresh": fresh(j, now, bn["fresh_days"])}
        total = sum(weights[k] * parts[k] for k in weights) / (sum(weights.values()) or 1)
        total -= bn["demerit"] * demerits(j, config)
        out.append(dict(j, best=round(total, 6), best_parts=parts,
                        best_facts={"matched": counted, "asks": n_asks, "lead": lead, "above": above_level(j, config)}))
    return sorted(out, key=lambda j: (-j["best"], j["public_slug"]))


def candidates(conn, config: dict, now: datetime, ranked: list[dict] | None = None) -> list[dict]:
    """Open jobs on their list they haven't acted on: no job folder, not applied, not closed,
    not blocked (rank hides those), not stale (likely filled). ranked = rank.rank of every row,
    when the caller already made it."""
    acting = {v for r in conn.execute("SELECT public_slug, link_key(url) FROM applications") for v in r if v}
    return [j for j in (rank.rank(store.all_jobs(conn), config, now) if ranked is None else ranked)
            if not j["stale"] and not ({j["public_slug"], *j["duplicates"], store.link_key(j["url"])} & acting)]


def ordered(conn, config: dict, now: datetime) -> list[dict]:
    return score(candidates(conn, config, now), config, now, resume_facts(config, now.date()))


def ago(days: int | None) -> str:
    if days is None:
        return ""
    return "posted today" if days < 1 else "posted 1 day ago" if days == 1 else f"posted {days} days ago"


def reasons(job: dict, config: dict, now: datetime) -> str:
    """The score in plain words, the order it weighs: match, a heavy ask, pay, where, age, then
    anything that pulled it down."""
    rc, f = config["rank"], job["best_facts"]
    parts = [f"Matches {f['matched'][0]} of {f['matched'][1]} asks" if f["matched"] else ""]
    if job["best_parts"]["asks"] < 0.5 and f["asks"]:
        heavy = f"Asks a lot: {f['asks']} requirements"
        parts.append(heavy + (f", {f['lead']} to lead or manage" if f["lead"] >= 2 else ""))
    if f["above"]:
        parts.append(f"{job['seniority'].replace('_', '-')} level, above yours")
    label = rank.pay_label(job)
    if label and rc["salary_floor_usd"]:
        label += " (meets your pay)" if rank.meets_floor(job, rc["salary_floor_usd"]) else " (below your pay)"
    place = "remote" if job.get("work_mode") == "remote" else next(iter(job.get("cities") or []), job.get("location") or "")
    parts += [label or "pay not listed", place, ago(posted_days(job, now))]
    parts += rank.doubts(job, rc) + rank.mismatches(job, rc) + rank.sponsorship(job, config) + rank.clearance(job)
    return " · ".join(p for p in parts if p)
