import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import cfg  # noqa: E402

CEILING_S = 300

SERVICE = """[Unit]
Description=jobs: {desc}
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User={user}
WorkingDirectory={root}
EnvironmentFile=-{root}/.data/email.env
ExecStart={uv} run --frozen python {cmd}
TimeoutStartSec={ceiling}
"""

TIMER = """[Unit]
Description=jobs: {desc} schedule

[Timer]
OnCalendar={calendar}
Persistent=true

[Install]
WantedBy=timers.target
"""

UNITS = {
    "jobs-poll": ("poll freehire", "app/jobs.py poll", "poll"),
    "jobs-digest": ("email digest", "app/jobs.py email", "digest"),
}


def main() -> None:
    ap = argparse.ArgumentParser(description="Write systemd units from search settings schedule")
    ap.add_argument("--out", required=True, help="e.g. /etc/systemd/system")
    ap.add_argument("--root", default="/opt/jobs")
    ap.add_argument("--user", default="jobs")
    ap.add_argument("--uv", default="/usr/local/bin/uv")
    args = ap.parse_args()
    schedule = cfg.load()["schedule"]
    out = Path(args.out)
    for name, (desc, cmd, key) in UNITS.items():
        fields = dict(desc=desc, user=args.user, root=args.root, uv=args.uv, cmd=cmd, ceiling=CEILING_S, calendar=schedule[key])
        (out / f"{name}.service").write_text(SERVICE.format(**fields), encoding="utf-8", newline="\n")
        (out / f"{name}.timer").write_text(TIMER.format(**fields), encoding="utf-8", newline="\n")
        print(f"wrote {name}.service + {name}.timer ({schedule[key]})")


if __name__ == "__main__":
    main()
