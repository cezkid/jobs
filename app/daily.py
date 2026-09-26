import os
import sys
import traceback
from collections.abc import Callable
from datetime import datetime
from email.message import EmailMessage

import httpx
from dotenv import load_dotenv

import alert
import cfg
import notify
import store
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


def check(config: dict, send: Sender) -> None:
    conn = store.connect(cfg.db_path(config))
    with httpx.Client(timeout=config["api"]["timeout_s"]) as client:
        for tier, s in freehire.run(config, conn, client).items():
            print(f"{tier}: fetched {s['fetched']} ({s['days']} days), closed {s['closed']}" + (" (cut at ceiling)" if s["truncated"] else ""))
    new = alert.run(conn, config, send[0])
    print(f"{new} new, {send[1]}" if new else "0 new, nothing sent")


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
        report_failure(exc, ways())
        return False


def main() -> None:
    # scheduled run has no console => everything lands in daily log
    cfg.DATA.mkdir(exist_ok=True)
    sys.stdout = sys.stderr = cfg.DAILY_LOG.open("a", encoding="utf-8")
    print(f"== {datetime.now().isoformat(timespec='seconds')}")
    load_dotenv(cfg.EMAIL_ENV)

    def work() -> None:
        config = cfg.load()
        check(config, senders(config)[0])

    def ways() -> list[Sender]:
        # broken settings must not stop the failure report
        try:
            return senders(cfg.load())
        except (Exception, SystemExit):
            return senders(cfg.defaults())

    if not guarded(work, ways):
        sys.exit(1)


if __name__ == "__main__":
    main()
