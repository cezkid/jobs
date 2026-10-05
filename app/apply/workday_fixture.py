"""A Workday step's `window.__jf.snapshot()` -> an anonymised test fixture: `apply-form workday-fixture <json>`.

The snapshot holds the step's labels, widget kinds, hooks, required marks and option lists - never an
answer (workday.js). Here: the employer's names (site name, "at X" in the page title, the tenant part of the host)
go to `.data/measure/tenants.txt` and become "Acme" in the fixture; the page block is dropped; an
email address or phone number left anywhere refuses the whole file. Never reads the user's resume.
Writes `app/tests/fixtures/workday/<step>.json`. Rules + why: app/docs/apply/workday.md (Fixtures).
"""
import json
import re
import sys
from pathlib import Path

from apply import lab

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "workday"
# what an applicant's contact looks like: none belongs in a fixture, whoever typed it
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"\+?\d[\d ().-]{8,}\d")


def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)


def swap(x, names: re.Pattern):
    if isinstance(x, str):
        return names.sub("Acme", x)
    if isinstance(x, dict):
        return {k: swap(v, names) for k, v in x.items()}
    if isinstance(x, list):
        return [swap(v, names) for v in x]
    return x


def fixture(src: Path) -> Path:
    snap = json.loads(src.read_text(encoding="utf-8"))
    if isinstance(snap, str):  # the extension hands back snapshot()'s JSON string as is
        snap = json.loads(snap)
    page = snap.pop("page", {})
    found = [s for s in strings(snap) if EMAIL.search(s) or PHONE.search(s)]
    if found:
        sys.exit(f"refused: {len(found)} text(s) look like an email or phone number - an applicant's answer "
                 "has no place in a fixture; nothing written")
    # a step's title can be the step itself ("My Experience" in the model): only its "at <employer>" part
    names = [page.get("site", "").strip()] + [m.group(1).strip() for m in [re.search(r"\bat (.+)$", page.get("title", ""))] if m]
    found = [n for n in lab.tenants(f"https://{page.get('host', '')}/", [n for n in names if n], {"controls": []}) if n]
    added = lab.record_tenants(lab.OUT / "tenants.txt", found)
    if found:  # longest first: "Acme Corp" before "Acme"
        snap = swap(snap, re.compile(r"(?<!\w)(?:" + "|".join(re.escape(n) for n in sorted(found, key=len, reverse=True)) + r")(?!\w)", re.I))
    step = re.sub(r"[^a-z0-9]+", "-", (snap.get("step") or "step").lower()).strip("-") or "step"
    out = FIXTURES / f"{step}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snap, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"fixture: {out}\ntenants.txt: {added} new line(s)")
    return out
