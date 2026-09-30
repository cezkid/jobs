import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ISO = "%Y-%m-%dT%H:%M:%SZ"

JSON_COLS = {"cities", "countries", "regions", "skills", "collections", "enrichment", "reality"}

# Normalized row shape; every ingest path emits exactly these keys.
COLS = (
    "public_slug", "tier", "title", "company", "company_slug", "url", "source", "location",
    "cities", "countries", "regions", "work_mode", "skills", "collections",
    "employment_type", "seniority", "category",
    "salary_min", "salary_max", "salary_currency", "salary_period",
    "posted_at", "created_at", "last_seen_at", "closed_at",
    "description", "enrichment", "reality",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    public_slug TEXT PRIMARY KEY,
    tier TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    company_slug TEXT,
    url TEXT NOT NULL,
    source TEXT,
    location TEXT,
    cities TEXT,
    countries TEXT,
    regions TEXT,
    work_mode TEXT,
    skills TEXT,
    collections TEXT,
    employment_type TEXT,
    seniority TEXT,
    category TEXT,
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency TEXT,
    salary_period TEXT,
    posted_at TEXT,
    created_at TEXT,
    last_seen_at TEXT,
    closed_at TEXT,
    description TEXT,
    enrichment TEXT,
    reality TEXT,
    first_fetched_at TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_tier_posted ON jobs (tier, posted_at);
CREATE TABLE IF NOT EXISTS seen (
    public_slug TEXT PRIMARY KEY,
    alerted_at TEXT NOT NULL
);
-- where each job the user acts on stands (status.py). Keyed by posting link, not slug: pasted
-- postings + jobs applied outside Job Finder have no jobs row
CREATE TABLE IF NOT EXISTS applications (
    key TEXT PRIMARY KEY,
    url TEXT,
    company TEXT,
    title TEXT,
    public_slug TEXT,
    state TEXT NOT NULL,
    state_at TEXT NOT NULL,
    added_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS application_log (
    key TEXT NOT NULL,
    state TEXT NOT NULL,
    at TEXT NOT NULL
);
-- last time the chat asked "did you send it?" about a job (status.to_ask): never twice in 3 days
CREATE TABLE IF NOT EXISTS asked (
    key TEXT PRIMARY KEY,
    at TEXT NOT NULL
);
-- job number the user sees in chat, email, Today page: given the first time a job is shown,
-- never changed or reused (AUTOINCREMENT). key = slug, or the applications key of a job w/o one
CREATE TABLE IF NOT EXISTS numbers (
    num INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    at TEXT NOT NULL
);
"""
# "12", "#12", "job 12" -> 12
NUMBER = re.compile(r"(?:job\s*)?#?\s*(\d+)", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime(ISO)


def connect(path: Path | str) -> sqlite3.Connection:
    # another chat or the morning check may be writing: wait for it instead of "database is locked"
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _encode(row: dict, col: str):
    value = row.get(col)
    return json.dumps(value) if col in JSON_COLS and value is not None else value


def _decode(row: sqlite3.Row) -> dict:
    job = dict(row)
    for col in JSON_COLS:
        if job.get(col) is not None:
            job[col] = json.loads(job[col])
    return job


def upsert(conn: sqlite3.Connection, rows: list[dict], now: str) -> None:
    cols = COLS + ("first_fetched_at", "fetched_at")
    updates = ", ".join(f"{c} = excluded.{c}" for c in COLS[1:] + ("fetched_at",))
    sql = (
        f"INSERT INTO jobs ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))}) "
        f"ON CONFLICT (public_slug) DO UPDATE SET {updates}"
    )
    conn.executemany(sql, [[_encode(r, c) for c in COLS] + [now, now] for r in rows])


def close_missing(
    conn: sqlite3.Connection, tier: str, fetched_slugs: set[str], posted_since: str | None, now: str
) -> int:
    # Rows posted before fetch window never return => only in-window absence means closed.
    conn.execute("CREATE TEMP TABLE IF NOT EXISTS fetched (slug TEXT PRIMARY KEY)")
    conn.execute("DELETE FROM fetched")
    conn.executemany("INSERT OR IGNORE INTO fetched VALUES (?)", [(s,) for s in fetched_slugs])
    cur = conn.execute(
        "UPDATE jobs SET closed_at = ? WHERE tier = ? AND closed_at IS NULL"
        " AND (? IS NULL OR posted_at >= ?)"
        " AND public_slug NOT IN (SELECT slug FROM fetched)",
        (now, tier, posted_since, posted_since),
    )
    return cur.rowcount


def all_jobs(conn: sqlite3.Connection, include_closed: bool = False) -> list[dict]:
    sql = "SELECT jobs.*, seen.alerted_at FROM jobs LEFT JOIN seen USING (public_slug)"
    if not include_closed:
        sql += " WHERE closed_at IS NULL"
    return [_decode(r) for r in conn.execute(sql)]


def unseen_open(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM jobs WHERE closed_at IS NULL"
        " AND public_slug NOT IN (SELECT public_slug FROM seen)"
    )
    return [_decode(r) for r in rows]


def mark_seen(conn: sqlite3.Connection, slugs: list[str], now: str) -> None:
    conn.executemany("INSERT OR IGNORE INTO seen VALUES (?, ?)", [(s, now) for s in slugs])


def number(conn: sqlite3.Connection, key: str, *copies: str) -> int:
    """Job's number, given on first sight. Stored => every chat, the email + Today page read the
    same one. copies = other postings of the same job (rank.collapse duplicates): if one was
    shown before, its number stays the job's number."""
    keys = [key, *copies]
    known = conn.execute(f"SELECT MIN(num) FROM numbers WHERE key IN ({', '.join('?' * len(keys))})", keys).fetchone()[0]
    if known is not None:
        return known
    conn.execute("INSERT OR IGNORE INTO numbers (key, at) VALUES (?, ?)", (key, utc_now()))
    return conn.execute("SELECT num FROM numbers WHERE key = ?", (key,)).fetchone()[0]


def numbered(conn: sqlite3.Connection, jobs: list[dict]) -> list[dict]:
    """Sets `num` on each row about to be shown, in shown order => a first list reads 1, 2, 3."""
    with conn:
        for j in jobs:
            j["num"] = number(conn, j["public_slug"], *j.get("duplicates") or [])
    return jobs


def key_for(conn: sqlite3.Connection, ref: str) -> str:
    """Job number ("12", "#12", "job 12") -> its slug (or applications key); anything else as is."""
    m = NUMBER.fullmatch(ref.strip())
    if not m:
        return ref
    row = conn.execute("SELECT key FROM numbers WHERE num = ?", (int(m[1]),)).fetchone()
    if row is None:
        raise LookupError(f"job {m[1]}: no job has that number")
    return row["key"]
