import os
import sqlite3
import sys
import traceback
from collections.abc import Callable
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

import httpx
from dotenv import load_dotenv

import alert
import cfg
import companies
import notify
import store
import today
from ingest import freehire

FAILED = f"{cfg.NAME} couldn't check for jobs today"
FAILED_HINT = f'Open {cfg.NAME} and ask: "why didn\'t today\'s job check work?"'
Sender = tuple[Callable[[EmailMessage], None], str]


def senders(config: dict) -> list[Sender]:
    """Email when set up, desktop always - failure report falls through to the next one."""
    out = []
    user, password = os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASSWORD")
    if user and password:
        to = os.environ.get("ALERT_TO") or user
        out.append((alert.smtp_sender(config, user, password, to), f"emailed to {to}"))
    return out + [(notify.sender(), "notified")]


def check(config: dict, send: Sender | None) -> None:
    """send None = a later check of the day: the job list + Today catch up, nothing is sent - the
    next day's first check tells them about these jobs too (still unseen)."""
    conn = store.connect(cfg.db_path(config))
    with httpx.Client(timeout=config["api"]["timeout_s"]) as client:
        started = store.utc_now()
        for tier, s in freehire.run(config, conn, client).items():
            print(f"{tier}: fetched {s['fetched']} ({s['days']} days), closed {s['closed']}" + (" (cut at ceiling)" if s["truncated"] else ""))
        freehire.recheck_quietly(conn, client, config["api"]["base"], started)
        companies.refresh_quietly(conn, client, config["api"]["base"])
    if send is None:
        print("later check, nothing sent")
        return
    with alert.lock(cfg.db_path(config)):
        new = alert.run(conn, config, send[0])
    print(f"{new} new, {send[1]}" if new else "0 new, nothing sent")


def refresh_today(config: dict) -> None:
    """Today page rebuilt after each check => a VS Code window left open for days shows this
    morning's jobs (the formatted view reloads when the file changes). Jobs were found either
    way: a page that fails to write is logged, never reported as a failed check."""
    try:
        today.write(config)
        print("Today page updated")
    except (Exception, SystemExit):
        traceback.print_exc()


def failure_message(exc: BaseException) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = FAILED
    msg.set_content(f"{FAILED}.\n\nWhat went wrong: {exc}\n\n{FAILED_HINT}\n")
    msg.preview = FAILED_HINT
    return msg


def report_failure(exc: BaseException, ways: list[Sender]) -> bool:
    """Never silent: try each way to reach the user until one works."""
    for send, _ in ways:
        try:
            send(failure_message(exc))
            return True
        except Exception:
            traceback.print_exc()
    return False


def guarded(work: Callable[[], None], ways: Callable[[], list[Sender]]) -> bool:
    try:
        work()
        return True
    except (Exception, SystemExit) as exc:
        traceback.print_exc()
        reason = " ".join(str(exc).split()) or type(exc).__name__
        print(f"failed {stamp()} {reason}")
        report_failure(exc, ways())
        return False


def stamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _utc(t: datetime) -> datetime:
    """One kind of time: timezone-aware UTC. A naive time is this computer's local time."""
    return t.astimezone(timezone.utc)


def last_ok(data_dir: Path) -> datetime | None:
    """When the morning check last worked (timezone-aware UTC): newest "ok" line in the log,
    else newest job fetch. The log writes local time, the store writes UTC with a Z."""
    best = None
    try:
        lines = (data_dir / "daily.log").read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        lines = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "ok":
            try:
                t = _utc(datetime.fromisoformat(parts[1]))
            except ValueError:
                continue
            if best is None or t > best:
                best = t
    if best:
        return best
    db = data_dir / "jobs.db"
    if not db.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            row = conn.execute("SELECT MAX(fetched_at) FROM jobs").fetchone()
        finally:
            conn.close()
        if not (row and row[0]):
            return None
        t = datetime.fromisoformat(row[0])  # the store is UTC, with or without the Z
        return t.replace(tzinfo=timezone.utc) if t.tzinfo is None else _utc(t)
    except (sqlite3.Error, ValueError):
        return None


def ran_today(data_dir: Path, word: str, now: datetime | None = None) -> bool:
    """A log line "<word> <local time>" from today: "ok" = a check worked, "failed" = one didn't."""
    day = (now or datetime.now()).date()
    try:
        lines = (data_dir / "daily.log").read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False
    for line in lines:
        parts = line.split()
        if len(parts) >= 2 and parts[0] == word:
            try:
                if datetime.fromisoformat(parts[1]).date() == day:
                    return True
            except ValueError:
                continue
    return False


def work() -> None:
    config = cfg.load()
    # several checks a day (autorun.times), one message: the day's first that works sends it
    check(config, None if ran_today(cfg.DATA, "ok") else senders(config)[0])
    refresh_today(config)
    # the count is decoration: it must never fail a finished check
    try:
        conn = store.connect(cfg.db_path(config))
        n = conn.execute("SELECT COUNT(*) FROM jobs WHERE closed_at IS NULL").fetchone()[0]
        tail = f" {n} jobs"
    except Exception:
        tail = ""
    print(f"ok {stamp()}{tail}")


def main() -> None:
    # scheduled run has no console => everything lands in daily log
    cfg.DATA.mkdir(exist_ok=True)
    sys.stdout = sys.stderr = cfg.DAILY_LOG.open("a", encoding="utf-8")
    print(f"== {datetime.now().isoformat(timespec='seconds')}")
    load_dotenv(cfg.EMAIL_ENV)

    # one failure report a day at most, none once a check worked: offline all day = 1, not 8
    told = ran_today(cfg.DATA, "ok") or ran_today(cfg.DATA, "failed")

    def ways() -> list[Sender]:
        if told:
            return []
        # broken settings must not stop the failure report
        try:
            return senders(cfg.load())
        except (Exception, SystemExit):
            return senders(cfg.defaults())

    if not guarded(work, ways):
        sys.exit(1)


if __name__ == "__main__":
    main()
