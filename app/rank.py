import argparse
from collections import defaultdict

import cfg
import store

PERIODS_PER_YEAR = {"year": 1, "month": 12, "week": 52, "day": 260, "hour": 2080}


def blocked(job: dict, blocklist: dict) -> bool:
    fields = {"companies": "company_slug", "sources": "source", "categories": "category"}
    for key, field in fields.items():
        blocked_values = {v.lower() for v in blocklist.get(key) or []}
        if (job.get(field) or "").lower() in blocked_values:
            return True
    title = (job.get("title") or "").lower()
    return any(phrase.lower() in title for phrase in blocklist.get("title_phrases") or [])


def annual_usd_min(job: dict) -> int | None:
    if job.get("salary_min") is None or job.get("salary_currency") != "USD":
        return None
    # unstated period -> annual
    return job["salary_min"] * PERIODS_PER_YEAR.get(job.get("salary_period") or "year", 1)


def has_salary(job: dict) -> bool:
    return job.get("salary_min") is not None or job.get("salary_max") is not None


def collections_hit(job: dict, boost: list[str]) -> bool:
    return bool(set(job.get("collections") or []) & set(boost))


def rank(jobs: list[dict], config: dict) -> list[dict]:
    rc = config["rank"]
    tiers = {t: i for i, t in enumerate(cfg.tier_order(config))}
    kept = [j for j in jobs if not blocked(j, config["blocklist"])]
    kept.sort(key=lambda j: j.get("posted_at") or "", reverse=True)
    kept.sort(key=lambda j: (
        tiers.get(j["tier"], len(tiers)),
        not collections_hit(j, rc["boost_collections"]),
        not (annual_usd_min(j) or 0) >= rc["salary_floor_usd"],
        not has_salary(j),
    ))
    return kept


def suspects(jobs: list[dict], min_categories: int) -> list[tuple[str, set[str]]]:
    cats = defaultdict(set)
    for j in jobs:
        if j.get("category"):
            cats[j["company_slug"]].add(j["category"])
    return sorted(((c, s) for c, s in cats.items() if len(s) >= min_categories), key=lambda cs: -len(cs[1]))


def main() -> None:
    ap = argparse.ArgumentParser(description="Print ranked open jobs")
    ap.add_argument("--db", help="override config db path")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--suspects", action="store_true", help="list companies spanning unrelated categories")
    args = ap.parse_args()
    config = cfg.load()
    conn = store.connect(args.db or cfg.db_path(config))
    jobs = store.all_jobs(conn)
    if args.suspects:
        for company, categories in suspects(jobs, config["rank"]["suspect_min_categories"]):
            print(f"{company}: {', '.join(sorted(categories))}")
        return
    for j in rank(jobs, config)[: args.limit]:
        salary = f"${annual_usd_min(j) // 1000}k" if annual_usd_min(j) else "-"
        print(f"{j['tier']:6} {salary:6} {','.join(j['collections']) or '-':20.20} {j['posted_at'][:10]} {j['title'][:60]} | {j['company']}  {j['public_slug']}")


if __name__ == "__main__":
    main()
