import argparse
import json

import httpx

import cfg
from resume import handoff, import_pdf
from text import html_to_text

PRIORITIES = ("required", "preferred")
# requirements past this crowd tailor task + coverage table w/o adding signal
MAX_REQUIREMENTS = 14

EXTRACT_SCHEMA = handoff.obj(
    title=handoff.STRING,
    company=handoff.STRING,
    requirements=handoff.array(handoff.obj(text=handoff.STRING, priority=handoff.STRING)),
)

EXTRACT_SYSTEM = f"""Read one pasted job posting. Emit its title, hiring company and requirement list.

- `title`: posting's own title, verbatim. Never add location or seniority.
- `company`: hiring employer only, never job board or agency.
- `requirements`: ONE entry per posting bullet or requirement sentence, that bullet's whole ask in `text`, posting's own terms. Never split one bullet across entries, never merge two. Skip perks, mission prose, benefits, equity, interview process.
- Name stacks, products and scale the posting names: bullet saying Ruby/Rails and React at large scale stays one entry naming all three.
- `priority`: {" or ".join(PRIORITIES)}. What posting asks candidate to HAVE - years, skills, past ownership -> required. Day-to-day duties, collaboration, bonus and nice-to-have -> preferred.
- At most {MAX_REQUIREMENTS} entries. Over that, keep ones naming concrete skills or scale and drop vaguest.
"""


def fetch(client: httpx.Client, base: str, slug: str) -> dict:
    # jobs.description truncated at 999 chars => detail endpoint only full-JD source
    resp = client.get(f"{base}/jobs/{slug}")
    resp.raise_for_status()
    return parse(resp.json()["data"])


def checked(slug: str, requirements: list[dict], where: str) -> list[dict]:
    # coverage gate scores against requirements => row w/o them cannot be tailored
    if not requirements:
        raise ValueError(f"{slug}: {where} empty")
    bad = sorted({r["priority"] for r in requirements} - set(PRIORITIES))
    if bad:
        raise ValueError(f"{slug}: unknown requirement priorities {bad}")
    return requirements


def from_text(text: str, url: str, got: dict) -> dict:
    """Pasted posting + AI's EXTRACT_SCHEMA answer -> same job dict shape fetch() returns."""
    title, company = got["title"].strip(), got["company"].strip()
    slug = import_pdf.slug(f"{company} {title}") or "pasted"
    return {
        "public_slug": slug,
        "title": title,
        "company": company,
        "url": url,
        "source": "pasted",
        "text": text.strip(),
        "requirements": checked(slug, got["requirements"], "extracted requirements"),
        "enrichment": {},
        "reality": {},
    }


def parse(raw: dict) -> dict:
    slug = raw["public_slug"]
    enrichment = raw.get("enrichment") or {}
    requirements = [
        {"text": html_to_text(r["text"]), "priority": r["priority"]} for r in enrichment.get("requirements") or []
    ]
    checked(slug, requirements, "enrichment.requirements")
    return {
        "public_slug": slug,
        "title": raw["title"].strip(),
        "company": (raw.get("company") or "").strip(),
        "url": raw["url"],
        "source": raw.get("source"),
        "text": html_to_text(raw.get("description")),
        "requirements": requirements,
        "enrichment": enrichment,
        "reality": raw.get("reality") or {},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch full JD + requirements for one job")
    ap.add_argument("slug")
    args = ap.parse_args()
    api = cfg.load()["api"]
    with httpx.Client(timeout=api["timeout_s"]) as client:
        jd = fetch(client, api["base"], args.slug)
    print(json.dumps(jd, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
