"""Knockout-question count: sample US job postings, read their application forms, one CSV row per form.

The measurement behind /research/ats-rejection-myth/ "How common are knockout questions?" and its data
page /research/knockout-questions-2026-10/ (source app/web/research/knockout-questions-2026-10.md + .csv).

  uv run app/web/knockout_count.py sample raw.json      # network: freehire job search, ~900 requests, a few minutes
  uv run app/web/knockout_count.py table raw.json > app/web/research/knockout-questions-2026-10.csv

sample: per job field, US postings of the last 14 days, one page of 60 at a random point in the first 9,900
results (fixed seed), each
posting's application form as freehire reads it (questions only, never answers; nothing about anyone is sent).
table: forms we could read -> CSV. Employers as letters (same employer = same letter), no titles or links;
counts summary on stderr. A raw file without employers (the 2026-10-03 run) gets them from each posting's
record, one request per readable form, saved back into it.

Categories are matched on the question text (RULES, lower-cased). A form counts once per category however
many of its questions match. Location: a form whose only location hits are address / zip / "where are you
located" boxes is not a location screen. Questions beyond basics: every question but name, contact,
address, profile-link, phone, email, pronoun, resume and cover-letter boxes (BASIC). The form's questions =
its question list + the employer questions some forms (Workable) list among the basics (asks()).
"""

import collections
import csv
import json
import random
import re
import sys
import time

import httpx

API = "https://freehire.me/api/v1"
HEADERS = {"User-Agent": "cez-job-finder-research"}
SEED = 20261003
FIELDS = {"healthcare": "Healthcare", "finance": "Finance", "sales": "Sales", "hospitality": "Hospitality",
          "education": "Education", "hr": "HR", "administration": "Administration",
          "customer_success": "Customer success", "design": "Design", "data_analytics": "Data analytics",
          "backend": "Backend software", "legal": "Law", "marketing": "Marketing", "devops": "DevOps"}
RULES = {
    "work_permit": r"authori[sz]ed to (lawfully )?work|legally (authori[sz]ed|eligible|able|permitted)|right to work|eligib\w* to work|able to work in the (us|u\.s|united states)|work permit|lawfully work",
    "sponsorship": r"sponsor|visa\b",
    "location_screen": r"relocat|on-?site|in[- ]office|office \d|\d\s*(x|days?)\s*(a|per)?\s*week|willing to work (from|in|at)|commut|reside|residence|based in|located in|currently located|live within|zip code",
    "years_experience": r"\byears?\b[^?]*experience|experience[^?]*\byears?\b|\d\+?\s*years",
    "license_certificate": r"licen[cs]e|certification|certified (?!that)|registered nurse|\bcpa\b|\bbar (status|admission|membership)",
    "security_clearance": r"clearance(?!/resignation)|polygraph|poly type|ts/sci|export control|\bitar\b",
    "age_18": r"18 years|age of 18|over 18|at least 18|over the age",
    "degree": r"degree|bachelor|level of education|education you have",
    "background_or_drug": r"background check|drug (test|screen)",
}
KNOCKOUT = ["work_permit", "sponsorship", "location_screen", "years_experience", "license_certificate",
            "security_clearance"]
NOT_YEARS = re.compile(r"18 years|years of age|years old")
NOT_LOCATION = re.compile(RULES["work_permit"] + "|" + RULES["sponsorship"] + "|permanent resident|onsite management|export control")
ADDRESS = re.compile(r"^\s*(address|city|state|zip|postal|country|location|current location)\b|zip code|where are you (currently )?(located|based)", re.I)
BASIC = re.compile(r"^\s*(preferred (first )?name|legal (first |last )?name|(first|last|full) name|name|pronouns?|address( line \d)?|street|city|state( / province)?|province|zip( code)?|postal code|country|location|current location|linkedin( profile| url)?|website|portfolio|github|twitter|personal website|phone|email|resume|cv|cover letter)\b[^?]{0,25}$", re.I)
COLUMNS = ["form", "employer", "job_field", "form_system", "questions_beyond_basics", *KNOCKOUT, "any_knockout",
           "age_18", "degree", "background_or_drug"]


def sample(path: str) -> None:
    rng, out = random.Random(SEED), {}
    with httpx.Client(timeout=30, headers=HEADERS) as client:
        for field in FIELDS:
            query = {"countries": "us", "category": field, "posted_within_days": 14}
            total = client.get(f"{API}/jobs/search", params={**query, "limit": 1, "offset": 0}).json()["meta"]["total"]
            offset = rng.randrange(0, max(1, min(total, 9900) - 60))
            rows = client.get(f"{API}/jobs/search", params={**query, "limit": 60, "offset": offset}).json()["data"]
            jobs = []
            for row in rows:
                form = client.get(f"{API}/jobs/{row['public_slug']}/apply-form")
                jobs.append({"slug": row["public_slug"], "title": row["title"], "source": row.get("source"),
                             "company": row.get("company_slug"), "status": form.status_code,
                             "form": form.json() if form.status_code == 200 else None})
                time.sleep(0.15)
            out[field] = {"total": total, "offset": offset, "jobs": jobs}
            print(field, total, offset, sum(j["form"] is not None for j in jobs), file=sys.stderr)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)


def categories(questions: list[dict]) -> set[str]:
    found, places = set(), []
    for question in questions:
        text = question["text"].lower()
        for name, rule in RULES.items():
            if name == "years_experience" and NOT_YEARS.search(text):
                continue
            if name == "location_screen" and NOT_LOCATION.search(text):
                continue
            if re.search(rule, text):
                found.add(name)
                if name == "location_screen":
                    places.append(text)
    if places and all(ADDRESS.search(t) for t in places):
        found.discard("location_screen")
    return found


def asks(basic: str) -> bool:
    """A basics entry that is the employer's own question: some Workable forms list them there (F1, review
    2026-10-04). Question = not a name / contact / profile box, and ends in ? or runs 4+ words."""
    return not BASIC.match(basic) and (basic.rstrip().endswith("?") or len(basic.split()) >= 4)


def letters(n: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA."""
    out = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        out = chr(65 + r) + out
    return out


def table(path: str, out=sys.stdout) -> None:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    forms = [(field, job) for field in FIELDS for job in raw.get(field, {}).get("jobs", []) if job["form"]]
    missing = [job for _, job in forms if not job.get("company")]
    if missing:
        with httpx.Client(timeout=30, headers=HEADERS) as client:
            for job in missing:
                job["company"] = client.get(f"{API}/jobs/{job['slug']}").json()["data"]["company_slug"]
                time.sleep(0.15)
        with open(path, "w", encoding="utf-8") as f:  # kept: the next run asks nothing
            json.dump(raw, f, indent=1)
    employers: dict[str, str] = {}
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(COLUMNS)
    counts, extra = collections.Counter(), []
    for n, (field, job) in enumerate(forms, 1):
        data = job["form"]["data"]
        questions = (data.get("questions") or []) + [{"text": b} for b in data.get("basics") or [] if asks(b)]
        found = categories(questions)
        found |= {"any_knockout"} if found & set(KNOCKOUT) else set()
        beyond = sum(not BASIC.match(q["text"]) for q in questions)
        employer = employers.setdefault(job["company"], letters(len(employers)))
        writer.writerow([n, employer, FIELDS[field], data.get("provider", "").capitalize(), beyond,
                         *(int(c in found) for c in COLUMNS[5:])])
        counts.update(found)
        extra.append(beyond)
    extra.sort()
    print(f"forms {len(forms)} of {sum(len(v['jobs']) for v in raw.values())} postings; employers {len(employers)}; "
          f"middle form {extra[len(extra) // 2]} beyond basics, {extra.count(0)} none", file=sys.stderr)
    print(" ".join(f"{c} {counts[c]}" for c in COLUMNS[5:]), file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("sample", "table"):
        sys.exit(__doc__)
    (sample if sys.argv[1] == "sample" else table)(sys.argv[2])
