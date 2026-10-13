"""Which employer job links freehire lacks, and which board to send it so it reads that employer.

freehire answers no lookup by link (`q` misses a posting id, no url filter - 2026-10-11), so each
link goes company first: its rows by `company_slug`, then the posting id matched inside their urls.
Board = the employer's site on one hiring system; freehire adds a whole board from one link
(freehire.me/contribute), so a missing board is worth more than a missing posting.
"""
import argparse
import re
from pathlib import Path
from urllib.parse import urlsplit

import httpx

import cfg

PAGE = 100
# rows read per company; Cisco has ~2,000 (2026-10-11), Workday giants more - a miss past it says so
COMPANY_ROW_CAP = 5000
SLUGS_PER_COMPANY = 3
UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
# posting id: a uuid, a Workday req (R0120279, JR104545 - after the last "_"), or 4+ digits
ID_TOKEN = re.compile(rf"{UUID}|(?<=_)[a-z]*\d[\w-]*$|\d{{4,}}", re.I)

# host pattern -> system, how many path segments name the board (None: the host alone)
SYSTEMS = [
    (re.compile(r"^jobs\.ashbyhq\.com$"), "ashby", 1),
    (re.compile(r"^(?:job-)?boards\.greenhouse\.io$"), "greenhouse", 1),
    (re.compile(r"^jobs\.(?:eu\.)?lever\.co$"), "lever", 1),
    (re.compile(r"^jobs\.smartrecruiters\.com$"), "smartrecruiters", 1),
    (re.compile(r"^apply\.workable\.com$"), "workable", 1),
    (re.compile(r"\.myworkdayjobs\.com$"), "workday", 1),
    (re.compile(r"\.icims\.com$"), "icims", None),
    (re.compile(r"\.eightfold\.ai$"), "eightfold", None),
    (re.compile(r"\.oraclecloud\.com$"), "oracle", None),
    (re.compile(r"\.bamboohr\.com$"), "bamboohr", None),
    (re.compile(r"\.recruitee\.com$"), "recruitee", None),
    (re.compile(r"\.teamtailor\.com$"), "teamtailor", None),
    (re.compile(r"\.breezy\.hr$"), "breezy", None),
    (re.compile(r"\.applytojob\.com$"), "jazzhr", None),
]
# SuccessFactors career sites run on the employer's own host: /job/<City-Title>/<digits>/
SUCCESSFACTORS_PATH = re.compile(r"^/job/[^/]+/\d{6,}/?$")
ORACLE_SITE = re.compile(r"^(/hcmUI/CandidateExperience/[^/]+/sites/[^/]+)", re.I)


def board(link: str) -> dict:
    """{system, key, link}: key compares two links' boards; link is what freehire takes."""
    parts = urlsplit(link.strip())
    host = parts.netloc.lower().removeprefix("www.")
    segs = [s for s in parts.path.split("/") if s]
    for pattern, system, depth in SYSTEMS:
        if pattern.search(host):
            if system == "oracle" and (site := ORACLE_SITE.match(parts.path)):
                path = site.group(1)
            elif depth and system == "workday":
                # /<lang>/<site>/job/...: the site is the segment before "job"
                head = segs[:segs.index("job")] if "job" in segs else segs[:1]
                path = "/" + "/".join(s for s in head if not re.fullmatch(r"[a-z]{2}-[A-Z]{2}", s))
            elif depth:
                path = "/" + "/".join(segs[:depth])
            else:
                path = ""
            # boards.greenhouse.io and job-boards.greenhouse.io serve one board
            key_host = "greenhouse.io" if system == "greenhouse" else host
            return {"system": system, "key": f"{key_host}{path}".lower().rstrip("/"),
                    "link": f"https://{parts.netloc}{path}"}
    system = "successfactors (likely)" if SUCCESSFACTORS_PATH.match(parts.path) else "unknown"
    return {"system": system, "key": host, "link": f"https://{parts.netloc}/"}


def posting_id(link: str) -> str | None:
    path = urlsplit(link.strip()).path.rstrip("/")
    for seg in reversed(path.split("/")):
        if found := ID_TOKEN.findall(seg):
            return found[-1].lower()
    return None


def company_guess(link: str) -> str | None:
    """The board's own name for the employer, when the link carries one."""
    parts = urlsplit(link.strip())
    host = parts.netloc.lower().removeprefix("www.")
    segs = [s for s in parts.path.split("/") if s]
    if re.search(r"ashbyhq|greenhouse|lever\.co|smartrecruiters|workable", host) and segs:
        return segs[0]
    if m := re.match(r"^(?:careers-)?([a-z0-9]+)\.(?:wd\d+\.myworkdayjobs|icims|eightfold)\.", host):
        return m.group(1)
    return None


def squash(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def company_slugs(client: httpx.Client, base: str, company: str) -> list[str]:
    resp = client.get(f"{base}/jobs/search", params={"q": company, "limit": PAGE})
    resp.raise_for_status()
    want = squash(company)
    counts: dict[str, int] = {}
    for row in resp.json()["data"]:
        name = squash(row.get("company"))
        if row.get("company_slug") and want and (want in name or (name and name in want)):
            counts[row["company_slug"]] = counts.get(row["company_slug"], 0) + 1
    return sorted(counts, key=counts.get, reverse=True)[:SLUGS_PER_COMPANY]


def company_rows(client: httpx.Client, base: str, slug: str) -> tuple[list[dict], bool]:
    """Every open row for one company slug; True when the cap cut it short."""
    rows: list[dict] = []
    while len(rows) < COMPANY_ROW_CAP:
        resp = client.get(f"{base}/jobs/search", params={"company_slug": slug, "limit": PAGE, "offset": len(rows)})
        resp.raise_for_status()
        page = resp.json()["data"]
        rows += page
        if len(page) < PAGE:
            return rows, False
    return rows, True


def check(client: httpx.Client, base: str, link: str, company: str | None = None) -> dict:
    """verdict: found | posting_missing (board read) | board_missing | company_missing | no_company."""
    site = board(link)
    out = {"link": link, "system": site["system"], "board": site["link"], "company": company or company_guess(link)}
    if not out["company"]:
        return {**out, "verdict": "no_company"}
    slugs = company_slugs(client, base, out["company"])
    if not slugs:
        return {**out, "verdict": "company_missing"}
    pid = posting_id(link)
    rows, capped = [], False
    for slug in slugs:
        got, cut = company_rows(client, base, slug)
        rows += got
        capped = capped or cut
    out["rows"], out["capped"] = len(rows), capped
    for row in rows:
        if pid and pid in (row.get("url") or "").lower():
            return {**out, "verdict": "found", "title": row["title"].strip(), "source": row.get("source")}
    same_board = any(board(row.get("url") or "")["key"] == site["key"] for row in rows)
    return {**out, "verdict": "posting_missing" if same_board else "board_missing"}


SAY = {
    "found": "in freehire",
    "posting_missing": "employer site already read, this posting not in - report to freehire",
    "board_missing": "employer site not read - submit board",
    "company_missing": "company not in freehire - submit board",
    "no_company": "can't tell the company from the link - add it: LINK | Company",
}


def read_lines(path: str) -> list[tuple[str, str | None]]:
    """LINK or `LINK | Company` per line; # comments and blanks skipped."""
    pairs = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        link, _, company = line.partition("|")
        pairs.append((link.strip(), company.strip() or None))
    return pairs


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Which employer job links freehire lacks + the board link to submit for each "
                    "(freehire.me/contribute). Developers: finding gaps against another job site.",
        epilog="file: one LINK or 'LINK | Company' per line - the employer's own posting link, "
               "not another job site's copy",
    )
    ap.add_argument("file", nargs="?", help="file of links")
    ap.add_argument("--link", action="append", default=[], help="one link (repeatable); 'LINK | Company' ok")
    args = ap.parse_args()
    pairs = read_lines(args.file) if args.file else []
    pairs += [(link.partition("|")[0].strip(), link.partition("|")[2].strip() or None) for link in args.link]
    if not pairs:
        ap.error("give a file or --link")
    api = cfg.defaults()["api"]
    tally: dict[str, int] = {}
    to_submit: dict[str, str] = {}
    with httpx.Client(timeout=api["timeout_s"]) as client:
        for link, company in pairs:
            got = check(client, api["base"], link, company)
            tally[got["verdict"]] = tally.get(got["verdict"], 0) + 1
            what = SAY[got["verdict"]]
            if got["verdict"] == "found":
                what += f" ({got['source']}: {got['title']})"
            elif got.get("capped"):
                what += f" (read first {got['rows']} rows only)"
            print(f"{got['company'] or '?'} | {got['system']} | {what}\n  {link}")
            if got["verdict"] in ("board_missing", "company_missing"):
                to_submit[got["board"]] = got["system"]
    print("\n" + ", ".join(f"{SAY[v].split(' - ')[0]}: {n}" for v, n in tally.items()))
    if to_submit:
        print("boards to submit at https://freehire.me/contribute (unknown = request a platform):")
        for link, system in to_submit.items():
            print(f"  {link}  ({system})")


if __name__ == "__main__":
    main()
