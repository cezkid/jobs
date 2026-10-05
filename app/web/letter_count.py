"""Cover-letter count: which forms in the knockout-question sample have a cover letter box, and is it required.

The measurement behind /research/cover-letters-after-ai/ "Do employers still ask for cover letters?".
Same forms as knockout_count.py (its raw file, same form numbers + employer letters as its CSV):

  uv run app/web/letter_count.py raw.json > app/web/research/cover-letter-boxes-2026-10.csv

letter_box: the form as freehire read it lists a cover letter (a basics entry or a question labelled
"cover letter"). letter_required: read from the hiring system's own public form, one request per form with a
box (Greenhouse job board, Workable form, Recruitee offers list; Ashby forms carry the flag in freehire's
read): 1 required, 0 optional, blank = could not read (posting closed since the sample). Postings are found
by freehire's listing id; nothing about anyone is sent. Answers are cached in the raw file, so a rerun asks
nothing. Lever forms list no cover letter box; their open "additional information" box is not counted.
"""

import collections
import csv
import json
import re
import sys
import time

import httpx

from knockout_count import API, FIELDS, HEADERS, letters

COLUMNS = ["form", "employer", "job_field", "form_system", "letter_box", "letter_required"]
LETTER = re.compile(r"^\s*cover letter\b", re.I)


def box(data: dict) -> dict | None:
    """The form's cover letter entry as freehire read it: {'required': bool | None}, or None for no box."""
    for question in data.get("questions") or []:
        if LETTER.match(question["text"]):
            return {"required": question.get("required")}
    if any(LETTER.match(b) for b in data.get("basics") or []):
        return {"required": None}
    return None


def required(client: httpx.Client, system: str, external_id: str) -> bool | None:
    """The hiring system's own flag for its cover letter box; None when the posting no longer answers."""
    account, _, job = external_id.partition(":")
    if system == "greenhouse":
        r = client.get(f"https://boards-api.greenhouse.io/v1/boards/{account}/jobs/{job}", params={"questions": "true"})
        if r.status_code != 200:
            return None
        flags = [q["required"] for q in r.json().get("questions", []) if LETTER.match(q.get("label", ""))]
        return flags[0] if flags else None
    if system == "workable":
        r = client.get(f"https://apply.workable.com/api/v1/jobs/{job}/form")
        if r.status_code != 200:
            return None
        found = []

        def walk(x):
            if isinstance(x, dict):
                if x.get("id") == "cover_letter":
                    found.append(bool(x.get("required")))
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(r.json())
        return found[0] if found else None
    if system == "recruitee":
        r = client.get(f"https://{account}.recruitee.com/api/offers/")
        offers = [o for o in r.json().get("offers", []) if str(o["id"]) == job] if r.status_code == 200 else []
        return offers[0]["options_cover_letter"] == "required" if offers else None
    return None


def count(path: str, out=sys.stdout) -> None:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    forms = [(field, job) for field in FIELDS for job in raw.get(field, {}).get("jobs", []) if job["form"]]
    asked = False
    with httpx.Client(timeout=30, headers=HEADERS) as client:
        for _, job in forms:
            data = job["form"]["data"]
            entry = box(data)
            if entry and entry["required"] is None and "letter_required" not in job:
                external_id = client.get(f"{API}/jobs/{job['slug']}").json()["data"]["external_id"]
                job["letter_required"] = required(client, data.get("provider", ""), external_id)
                asked = True
                time.sleep(0.15)
    if asked:
        with open(path, "w", encoding="utf-8") as f:  # kept: the next run asks nothing
            json.dump(raw, f, indent=1)
    employers: dict[str, str] = {}
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(COLUMNS)
    counts = collections.Counter()
    for n, (field, job) in enumerate(forms, 1):
        data = job["form"]["data"]
        system = data.get("provider", "").capitalize()
        employer = employers.setdefault(job["company"], letters(len(employers)))
        entry = box(data)
        flag = None if not entry else entry["required"] if entry["required"] is not None else job.get("letter_required")
        writer.writerow([n, employer, FIELDS[field], system, int(bool(entry)), "" if flag is None else int(flag)])
        counts[(system, "box")] += bool(entry)
        counts[(system, "forms")] += 1
        counts[(system, {True: "required", False: "optional", None: "unknown"}[flag])] += bool(entry)
    systems = sorted({s for s, _ in counts})
    print(f"forms {len(forms)}; box {sum(counts[(s, 'box')] for s in systems)}; required "
          f"{sum(counts[(s, 'required')] for s in systems)}; optional {sum(counts[(s, 'optional')] for s in systems)}; "
          f"unknown {sum(counts[(s, 'unknown')] for s in systems)}", file=sys.stderr)
    for s in systems:
        print(f"{s}: forms {counts[(s, 'forms')]} box {counts[(s, 'box')]} required {counts[(s, 'required')]} "
              f"optional {counts[(s, 'optional')]} unknown {counts[(s, 'unknown')]}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    count(sys.argv[1])
