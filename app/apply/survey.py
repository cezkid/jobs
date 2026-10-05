"""Which question kinds real forms carry, for developers: `apply-form survey <links file>`.

One plain request per link (each system's own form-definition read, no browser), paced, stops at the
first 403 / 429, never retries. Every employer's slug goes in `.data/measure/tenants.txt` before the
first request. Output = counts only (`.data/measure/survey-<date>.json`): field type x required, survey
forms, file boxes other than the resume, closed. A type the system's KIND map lacks is kept raw beside
it for an anonymised fixture. Results: ashby.md + lever.md "Kinds on real forms".
"""
import json
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import httpx

from apply import lab
from apply.systems import ashby, lever

PACE_S = 2.0
STOP = (403, 429)


class Stopped(Exception):
    """The host refused a read: stop, never retry."""


def ashby_fields(url: str) -> list[dict] | None:
    """[{type, required, survey, resume, file, known, raw}] off the form definition; None = closed."""
    org, posting = ashby.parse_url(url)
    r = httpx.post(ashby.GRAPHQL, timeout=30, json={
        "operationName": "ApiJobPosting", "query": ashby.QUERY,
        "variables": {"organizationHostedJobsPageName": org, "jobPostingId": posting}})
    if r.status_code in STOP:
        raise Stopped(f"{r.status_code} from {ashby.NAME}")
    r.raise_for_status()
    job = (r.json().get("data") or {}).get("jobPosting")
    if not job:
        return None
    out = []
    for survey, form in [(False, job["applicationForm"]), *((True, f) for f in job.get("surveyForms") or [])]:
        for entry in (e for sec in form["sections"] for e in sec["fieldEntries"]):
            f = entry.get("field")
            if f and not f.get("isDeactivated"):
                out.append({"type": f["type"], "required": bool(entry.get("isRequired")), "survey": survey,
                            "resume": f.get("path") == "_systemfield_resume", "file": f["type"] == "File", "known": f["type"] in ashby.KIND,
                            "raw": f})
    return out


def lever_fields(url: str) -> list[dict] | None:
    """Card + survey fields by their JSON type, every other named box by its HTML type; None = closed."""
    r = httpx.get(lever.application_url(url), timeout=30, follow_redirects=False)
    if r.status_code in STOP:
        raise Stopped(f"{r.status_code} from {lever.NAME}")
    if r.status_code in (301, 302, 404):
        return None
    r.raise_for_status()
    form = lever.Form()
    form.feed(r.text)
    out = []
    for name, box in form.boxes.items():
        if m := lever.FIELD.match(name):
            fields = (form.templates.get((m.group(1), m.group(2))) or {}).get("fields") or []
            if int(m.group(3)) < len(fields):
                f = fields[int(m.group(3))]
                part = "card" if m.group(1) == "cards" else "survey"
                out.append({"type": f"{part}:{f.get('type')}", "required": bool(f.get("required")),
                            "survey": part == "survey", "resume": False, "file": f.get("type") == "file-upload", "known": f.get("type") in lever.KIND,
                            "raw": f})
                continue
        kind = name.split("[")[0] + "[]" if "[" in name and name not in lever.STANDARD else name
        part = "standard" if name in lever.STANDARD else "box"
        out.append({"type": f"{part}:{kind}:{box['type']}", "required": box["required"] or "✱" in box["label"],
                    "survey": False, "resume": name == "resume", "file": box["type"] == "file", "known": True, "raw": None})
    return out


SYSTEMS = ((ashby, ashby_fields), (lever, lever_fields))


def tally(results: list[tuple[str, list[dict] | None]]) -> dict:
    """Per system: employers, closed, type -> {fields, required, employers}, survey forms, other file boxes."""
    out = {}
    for name in dict.fromkeys(n for n, _ in results):
        rows = [f for n, f in results if n == name]
        types = defaultdict(lambda: Counter())
        for fields in (f for f in rows if f is not None):
            for t in {f["type"] for f in fields}:
                types[t]["employers"] += 1
            for f in fields:
                types[f["type"]]["fields"] += 1
                types[f["type"]]["required"] += f["required"]
        open_ = [f for f in rows if f is not None]
        out[name] = {
            "employers": len(rows), "closed": rows.count(None),
            "survey_forms": sum(any(f["survey"] for f in fields) for fields in open_),
            "other_file_boxes": sum(sum(f["file"] and not f["resume"] for f in fields) for fields in open_),
            "employers_with_other_file": sum(any(f["file"] and not f["resume"] for f in fields) for fields in open_),
            "types": {t: dict(c) for t, c in sorted(types.items(), key=lambda kv: -kv[1]["fields"])},
            "unknown": sorted({f["type"] for fields in open_ for f in fields if not f["known"]}),
        }
    return out


def survey(links: Path) -> Path:
    urls = [u.strip() for u in links.read_text(encoding="utf-8").splitlines() if u.strip()]
    todo = []
    for u in urls:
        system = next(((s, read) for s, read in SYSTEMS if s.matches(u)), None)
        if system is None:
            print(f"skipped (not Ashby or Lever): line {urls.index(u) + 1}")
            continue
        todo.append((u, *system))
    added = lab.record_tenants(lab.OUT / "tenants.txt",
                               [t for u, _, _ in todo for t in lab.tenants(u, [], {"controls": []})])
    print(f"tenants.txt: {added} new line(s)")
    results, unknown, loads = [], [], Counter()
    for i, (u, system, read) in enumerate(todo):
        if i:
            time.sleep(PACE_S)
        loads[system.NAME] += 1
        try:
            fields = read(u)
        except Stopped as e:
            print(f"stopped at link {i + 1} of {len(todo)}: {e}")
            break
        except (httpx.HTTPError, ValueError) as e:
            print(f"link {i + 1}: not read ({type(e).__name__}) - left out")
            continue
        results.append((system.NAME, fields))
        unknown += [{"system": system.NAME, "link": i + 1, "field": f["raw"]} for f in fields or [] if not f["known"]]
    stamp = date.today().isoformat()
    out = lab.OUT / f"survey-{stamp}.json"
    out.write_text(json.dumps({"date": stamp, "requests": dict(loads), "systems": tally(results)}, indent=1))
    if unknown:  # raw, may name the employer: local only, for an anonymised fixture
        (lab.OUT / f"survey-{stamp}-unknown.json").write_text(json.dumps(unknown, indent=1))
    print(f"requests: {dict(loads)}\n{out}")
    return out
