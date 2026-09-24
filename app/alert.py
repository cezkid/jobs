import argparse
import html
import os
import smtplib
import sys
from collections.abc import Callable
from email.message import EmailMessage

from dotenv import load_dotenv

import cfg
import rank
import store


# digest lists the best this many; the rest wait in the chat, still marked seen
DIGEST_CAP = 25


def facts(job: dict, config: dict) -> list[str]:
    return [job["company"] or job["company_slug"] or "?", rank.reasons(job, config)]


def by_tier(ranked: list[dict], config: dict) -> list[tuple[str, list[dict]]]:
    return [
        (p["label"], rows)
        for p in config["passes"]
        if (rows := [j for j in ranked if j["tier"] == p["tier"]])
    ]


def build_message(ranked: list[dict], config: dict) -> EmailMessage:
    counts = ", ".join(f"{len(rows)} {label}" for label, rows in by_tier(ranked, config))
    text, markup = [], []
    for label, rows in by_tier(ranked[:DIGEST_CAP], config):
        text.append(f"== {label} ==")
        markup.append(f"<h3>{html.escape(label)}</h3><ul>")
        for j in rows:
            detail = " | ".join(facts(j, config))
            text += [f"{j['title']} - {detail}", f"  {j['url']}", ""]
            markup.append(
                f'<li><a href="{html.escape(j["url"], quote=True)}">{html.escape(j["title"])}</a>'
                f" - {html.escape(detail)}</li>"
            )
        markup.append("</ul>")
    if len(ranked) > DIGEST_CAP:
        more = f"{len(ranked) - DIGEST_CAP} more - ask the chat to see them"
        text.append(more)
        markup.append(f"<p>{html.escape(more)}</p>")
    msg = EmailMessage()
    msg["Subject"] = f"{len(ranked)} new {config['profile']['name']} ({counts})"
    msg.set_content("\n".join(text))
    msg.add_alternative("".join(markup), subtype="html")
    # desktop pop-up has room for a line, not a digest (notify.sender)
    msg.preview = "; ".join(j["title"] for j in ranked[:3])
    return msg


def unseen_ranked(conn, config: dict) -> list[dict]:
    # rank every open row so a repost of a job already sent collapses into it, not in as new;
    # stale rows (likely filled) are never announced - they stay in the chat list only
    return [j for j in rank.rank(store.all_jobs(conn), config) if not j["seen"] and not j["stale"]]


def run(conn, config: dict, send: Callable[[EmailMessage], None]) -> int:
    ranked = unseen_ranked(conn, config)
    if not ranked:
        return 0
    send(build_message(ranked, config))
    # only after send succeeds => failed send retries tomorrow
    with conn:
        store.mark_seen(conn, [s for j in ranked for s in [j["public_slug"], *j["duplicates"]]], store.utc_now())
    return len(ranked)


def smtp_sender(config: dict, user: str, password: str, to: str) -> Callable[[EmailMessage], None]:
    smtp = config["alert"]

    def send(msg: EmailMessage) -> None:
        msg["From"] = user
        msg["To"] = to
        with smtplib.SMTP_SSL(smtp["smtp_host"], smtp["smtp_port"], timeout=smtp["timeout_s"]) as server:
            server.login(user, password)
            server.send_message(msg)
    return send


def check_login(config: dict, user: str, password: str, connect=smtplib.SMTP_SSL) -> None:
    """Sign in and hang up. Proves credentials before a scheduled run depends on them."""
    smtp = config["alert"]
    with connect(smtp["smtp_host"], smtp["smtp_port"], timeout=smtp["timeout_s"]) as server:
        server.login(user, password)


def main() -> None:
    ap = argparse.ArgumentParser(description="Email unseen ranked jobs, then mark seen")
    ap.add_argument("--db", help="override config db path")
    ap.add_argument("--dry-run", action="store_true", help="print message; no send, no seen insert")
    args = ap.parse_args()
    load_dotenv(cfg.EMAIL_ENV)
    config = cfg.load()
    conn = store.connect(args.db or cfg.db_path(config))
    if args.dry_run:
        ranked = unseen_ranked(conn, config)
        if ranked:
            msg = build_message(ranked, config)
            print(msg["Subject"])
            print(msg.get_body(("plain",)).get_content())
        print(f"{len(ranked)} new (dry run)")
        user, password = os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASSWORD")
        if not (user and password):
            print(f"email not set up ({cfg.EMAIL_ENV} missing SMTP_USER/SMTP_PASSWORD); "
                  "daily run notifies on this computer instead")
            return
        try:
            check_login(config, user, password)
        except Exception as exc:
            sys.exit(f"email sign-in failed: {exc}\nFix SMTP_USER/SMTP_PASSWORD in {cfg.EMAIL_ENV} "
                     "(Gmail needs an app password, not the account password).")
        print(f"email sign-in ok: {user} -> {os.environ.get('ALERT_TO') or user}")
        return
    missing = [k for k in ("SMTP_USER", "SMTP_PASSWORD") if not os.environ.get(k)]
    if missing:
        sys.exit(f"{', '.join(missing)} not set. Put them in {cfg.EMAIL_ENV} (see app/email.env.example).")
    user = os.environ["SMTP_USER"]
    to = os.environ.get("ALERT_TO") or user
    new = run(conn, config, smtp_sender(config, user, os.environ["SMTP_PASSWORD"], to))
    print(f"{new} new, emailed to {to}" if new else "0 new, nothing sent")


if __name__ == "__main__":
    main()
