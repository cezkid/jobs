import os
import sys
from datetime import datetime

import httpx
from dotenv import load_dotenv

import alert
import cfg
import notify
import store
from ingest import freehire

def main() -> None:
    # scheduled run has no console => everything lands in daily log
    cfg.DATA.mkdir(exist_ok=True)
    sys.stdout = sys.stderr = cfg.DAILY_LOG.open("a", encoding="utf-8")
    print(f"== {datetime.now().isoformat(timespec='seconds')}")
    load_dotenv(cfg.EMAIL_ENV)
    config = cfg.load()
    conn = store.connect(cfg.db_path(config))
    with httpx.Client(timeout=config["api"]["timeout_s"]) as client:
        for tier, s in freehire.run(config, conn, client).items():
            print(f"{tier}: fetched {s['fetched']}, closed {s['closed']}")
    user, password = os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASSWORD")
    if user and password:
        to = os.environ.get("ALERT_TO") or user
        send, done = alert.smtp_sender(config, user, password, to), f"emailed to {to}"
    else:
        send, done = notify.sender(), "notified"
    new = alert.run(conn, config, send)
    print(f"{new} new, {done}" if new else "0 new, nothing sent")


if __name__ == "__main__":
    main()
