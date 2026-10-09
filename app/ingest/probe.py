import argparse
from collections import Counter

import httpx

import cfg
from ingest import freehire

SAMPLE_SIZE = 100
SAMPLE_TITLES = 10
FACET_PREVIEW = 12
TALLY_FIELDS = ("category", "seniority", "employment_type")
# --title: how recent "posted lately" is - a month, the setup's thin-search yardstick
RECENT_DAYS = 30


def probe(client: httpx.Client, base: str, params: dict) -> dict:
    resp = client.get(f"{base}/jobs/search", params={**freehire.query_params(params), "limit": SAMPLE_SIZE})
    resp.raise_for_status()
    body = freehire.understood(resp.json())
    rows = body["data"]
    tallies = {f: Counter((r.get("enrichment") or {}).get(f) for r in rows) for f in TALLY_FIELDS}
    tallies["work_mode"] = Counter(r.get("work_mode") for r in rows)
    return {"total": body["meta"]["total"], "sampled": len(rows), "tallies": tallies,
            "titles": [f"{r['title'].strip()} | {r.get('company') or '?'}" for r in rows[:SAMPLE_TITLES]]}


# A title search's facets, read off the rows themselves: /jobs/facets ignores q_fields (2026-10-09,
# meta.ignored_params), so its counts match the words anywhere in a posting - "compliance" in titles
# 3,562 US jobs, its facet counts summed to 61,000+ (management alone 13,666). Newest rows, so a
# sample: enough to see where a title's jobs sit and which filters drop most of them.
TITLE_TALLY_ROWS = 500
ROW_FACETS = {
    "category": lambda r: (r.get("enrichment") or {}).get("category"),
    "seniority": lambda r: (r.get("enrichment") or {}).get("seniority"),
    "employment_type": lambda r: (r.get("enrichment") or {}).get("employment_type"),
    "visa_sponsorship": lambda r: (r.get("enrichment") or {}).get("visa_sponsorship"),
    "work_mode": lambda r: r.get("work_mode"),
    "requires_clearance": lambda r: r.get("requires_clearance"),
    "cities": lambda r: r.get("cities") or [],
    "collections": lambda r: r.get("collections") or [],
}


def title_facets(client: httpx.Client, base: str, params: dict) -> dict[str, Counter]:
    """Tally per facet over the newest TITLE_TALLY_ROWS a title search returns."""
    rows = []
    while len(rows) < TITLE_TALLY_ROWS:
        resp = client.get(f"{base}/jobs/search", params={**freehire.query_params(params), "sort": "posted_at",
                                                          "order": "desc", "limit": SAMPLE_SIZE, "offset": len(rows)})
        resp.raise_for_status()
        body = freehire.understood(resp.json())
        rows += body["data"]
        if not body["data"] or len(rows) >= body["meta"]["total"]:
            break
    tallies = {}
    for name, read in ROW_FACETS.items():
        values = [v for r in rows for v in (read(r) if isinstance(read(r), list) else [read(r)])]
        tallies[name] = Counter(str(v).lower() if isinstance(v, bool) else v for v in values)
    return tallies


def facet_values(client: httpx.Client, base: str, params: dict, facet: str = "") -> dict[str, list[tuple[str, int]]]:
    """Every valid value + live count in one call. Beats guessing slugs: unknown slug answers 0, not error.
    A title search (q) is tallied off its rows instead (title_facets); None = no value on the row."""
    if params.get("q"):
        tallies = title_facets(client, base, params)
        if facet and facet not in tallies:
            raise SystemExit(f"{facet!r}: not tallied for a title search. available: {', '.join(sorted(tallies))}")
        names = [facet] if facet else sorted(tallies)
        return {n: sorted((("-" if v is None else v, c) for v, c in tallies[n].items()), key=lambda kv: (-kv[1], kv[0]))
                for n in names}
    resp = client.get(f"{base}/jobs/facets", params=freehire.query_params(params))
    resp.raise_for_status()
    facets = freehire.understood(resp.json())["data"]["facets"]
    if facet and facet not in facets:
        raise SystemExit(f"{facet!r}: no such facet. available: {', '.join(sorted(facets))}")
    names = [facet] if facet else sorted(facets)
    return {n: sorted(facets[n].items(), key=lambda kv: (-kv[1], kv[0])) for n in names}


def count(client: httpx.Client, base: str, params: dict) -> int:
    resp = client.get(f"{base}/jobs/search", params={**freehire.query_params(params), "limit": 1})
    resp.raise_for_status()
    return freehire.understood(resp.json())["meta"]["total"]


def title_counts(client: httpx.Client, base: str, params: dict, forms: list[str]) -> list[tuple[str, int, int]]:
    """Each way a job title is written (registered nurse, RN) -> open now, posted in the last
    RECENT_DAYS. A field's category count says nothing about one role: Healthcare held 31,964 US
    jobs, 17,849 of them titled RN and 50 "registered nurse" (2026-10-01)."""
    out = []
    for form in forms:
        titled = {**params, "q": form, "q_fields": cfg.TITLE_ONLY}
        out.append((form, count(client, base, titled), count(client, base, {**titled, "posted_within_days": RECENT_DAYS})))
    return out


def city_values(client: httpx.Client, base: str, text: str) -> list[str]:
    resp = client.get(f"{base}/geo/cities", params={"q": text})
    resp.raise_for_status()
    return [f"{c['value']} ({c['country']})" for c in resp.json()["data"]]


def parse_params(pairs: list[str]) -> dict:
    params = {}
    for pair in pairs:
        key, _, value = pair.partition("=")
        if not value:
            raise SystemExit(f"{pair!r}: expected key=value, lists comma-separated")
        params[key] = value.split(",") if "," in value else value
    return params


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Count freehire matches for candidate filter params; sample first page",
        epilog="examples:\n"
        "  python -m ingest.probe category=finance work_mode=remote countries=us\n"
        "  python -m ingest.probe --city springfield\n"
        "  python -m ingest.probe --facets category countries=us",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("params", nargs="*", help="key=value; same keys as a profile's passes[].params")
    ap.add_argument("--city", help="list exact cities= values matching this text, then exit")
    ap.add_argument("--title", action="append", metavar="WORDS",
                    help="count jobs titled WORDS (exact phrase), open + last 30 days; repeat for each "
                         "way the title is written (--title 'registered nurse' --title RN), then exit")
    ap.add_argument(
        "--facets", nargs="?", const="", metavar="FACET",
        help="list valid values + counts for every facet (or just FACET), then exit; "
             "use instead of guessing slugs one probe at a time",
    )
    args = ap.parse_args()
    raw = list(args.params)
    # `--facets countries=us`: argparse hands the filter to --facets, so put it back as a param
    if args.facets and "=" in args.facets:
        raw.append(args.facets)
        args.facets = ""
    params = parse_params(raw)
    if problem := cfg.q_problem(params):
        raise SystemExit(problem)
    # defaults only => runs before config.yml exists
    api = cfg.defaults()["api"]
    with httpx.Client(timeout=api["timeout_s"]) as client:
        if args.city:
            print("\n".join(city_values(client, api["base"], args.city)) or "no match")
            return
        if args.title:
            for form, open_now, recent in title_counts(client, api["base"], params, args.title):
                print(f'"{form}": {open_now} open, {recent} posted in the last {RECENT_DAYS} days')
            return
        if args.facets is not None:
            if params.get("q"):
                print(f"titles only: tallied over the newest {TITLE_TALLY_ROWS} (the job search's own facet counts "
                      f"read the words anywhere in a posting); - = not tagged")
            for name, values in facet_values(client, api["base"], params, args.facets).items():
                shown = values if args.facets else values[:FACET_PREVIEW]
                line = ", ".join(f"{v} {n}" for v, n in shown)
                more = "" if len(shown) == len(values) else f", (+{len(values) - len(shown)} more)"
                print(f"{name}: {line}{more}")
            return
        result = probe(client, api["base"], params)
    print(f"total {result['total']} (tallies over first {result['sampled']})")
    for field, counts in result["tallies"].items():
        print(f"  {field}: " + ", ".join(f"{k or '-'} {n}" for k, n in counts.most_common()))
    for title in result["titles"]:
        print(f"  {title}")


if __name__ == "__main__":
    main()
