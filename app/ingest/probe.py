import argparse
from collections import Counter

import httpx

import cfg
from ingest import freehire

SAMPLE_SIZE = 100
SAMPLE_TITLES = 10
FACET_PREVIEW = 12
TALLY_FIELDS = ("category", "seniority", "employment_type")


def probe(client: httpx.Client, base: str, params: dict) -> dict:
    resp = client.get(f"{base}/jobs/search", params={**freehire.query_params(params), "limit": SAMPLE_SIZE})
    resp.raise_for_status()
    body = resp.json()
    rows = body["data"]
    tallies = {f: Counter((r.get("enrichment") or {}).get(f) for r in rows) for f in TALLY_FIELDS}
    tallies["work_mode"] = Counter(r.get("work_mode") for r in rows)
    return {"total": body["meta"]["total"], "sampled": len(rows), "tallies": tallies,
            "titles": [f"{r['title'].strip()} | {r.get('company') or '?'}" for r in rows[:SAMPLE_TITLES]]}


def facet_values(client: httpx.Client, base: str, params: dict, facet: str = "") -> dict[str, list[tuple[str, int]]]:
    """Every valid value + live count in one call. Beats guessing slugs: unknown slug answers 0, not error."""
    resp = client.get(f"{base}/jobs/facets", params=freehire.query_params(params))
    resp.raise_for_status()
    facets = resp.json()["data"]["facets"]
    if facet and facet not in facets:
        raise SystemExit(f"{facet!r}: no such facet. available: {', '.join(sorted(facets))}")
    names = [facet] if facet else sorted(facets)
    return {n: sorted(facets[n].items(), key=lambda kv: (-kv[1], kv[0])) for n in names}


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
    bad = cfg.FORBIDDEN_PARAMS & params.keys()
    if bad:
        raise SystemExit(f"forbidden params {sorted(bad)} (docs/jobs/freehire.md)")
    # defaults only => runs before config.yml exists
    api = cfg.defaults()["api"]
    with httpx.Client(timeout=api["timeout_s"]) as client:
        if args.city:
            print("\n".join(city_values(client, api["base"], args.city)) or "no match")
            return
        if args.facets is not None:
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
