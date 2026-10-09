import os
from pathlib import Path

import yaml

import software

# what the user sees: Desktop icon, notifications, guides; installers + docs spell it out
NAME = "CEZ Job Finder"
APP = Path(__file__).resolve().parent
ROOT = APP.parent
DEFAULTS = APP / "defaults.yml"
PROFILES = APP / "profiles"
SETTINGS = ROOT / "My Settings" / "Search settings.yml"
# user's own folders: created empty at launch so VS Code's file list matches START HERE.md
# before anything is saved - user sees what is private on day one
PRIVATE_DIRS = ("My Resume", "My Jobs", "My Settings")
# hidden from user in VS Code: db, log, email password, AI task files
DATA = ROOT / ".data"
EMAIL_ENV = DATA / "email.env"
DAILY_LOG = DATA / "daily.log"
# q= alone matches description prose => off-lane titles for any occupation; w/ q_fields=title it
# matches titles only (docs/jobs/freehire.md #Title search)
TITLE_ONLY = "title"
# shortest wait before a follow-up is suggested: always holds two working days
MIN_FOLLOW_UP_DAYS = 5
# API ORs these together => two in one pass widen, never narrow
GEOGRAPHY_PARAMS = {"regions", "countries", "cities"}


def config_path() -> Path:
    return Path(os.environ.get("JOBS_CONFIG") or SETTINGS)


def ensure_private_dirs(root: Path | None = None) -> None:
    for name in PRIVATE_DIRS:
        ((root or ROOT) / name).mkdir(parents=True, exist_ok=True)


def merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for key, value in over.items():
        out[key] = merge(out[key], value) if isinstance(value, dict) and isinstance(out.get(key), dict) else value
    return out


def defaults() -> dict:
    return yaml.safe_load(DEFAULTS.read_text(encoding="utf-8"))


def load(path: Path | None = None) -> dict:
    path = path or config_path()
    if not path.exists():
        raise SystemExit(
            f"{path} missing. Ask your AI to set up {NAME} (job-setup skill), "
            "or copy app/profiles/example.yml there and edit it."
        )
    config = merge(defaults(), yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    for p in config["passes"]:
        if problem := q_problem(p["params"]):
            raise ValueError(f"pass {p['tier']}: {problem}")
        geo = GEOGRAPHY_PARAMS & p["params"].keys()
        if len(geo) > 1:
            raise ValueError(f"pass {p['tier']}: {sorted(geo)} OR together, keep one (docs/jobs/freehire.md)")
        # read here only (rank.far), never sent: two-letter US state codes
        if bad := [s for s in p.get("states") or [] if not (isinstance(s, str) and len(s) == 2 and s.isalpha())]:
            raise ValueError(f"pass {p['tier']}: states {bad} - two-letter US state codes, e.g. [DC, MD, VA]")
    for where in (config["rank"], config.get("blocklist") or {}):
        if bad := software.unknown(where.get("software_kinds")):
            raise ValueError(f"software_kinds {bad} - any of {', '.join(software.KINDS)} (app/software.py)")
    for stage, days in (config.get("follow_up") or {}).items():
        if not isinstance(days, int) or days < MIN_FOLLOW_UP_DAYS:
            raise ValueError(f"follow_up.{stage}: {days!r} - at least {MIN_FOLLOW_UP_DAYS} days (a weekend can take 3)")
    return config


def q_problem(params: dict) -> str | None:
    """q only as one title phrase: alone it matches description prose (q=react returned a
    Lifecycle Marketing Manager), and the job search has no OR, so a list can't mean either form."""
    if "q" not in params:
        return None
    if params.get("q_fields") not in (TITLE_ONLY, [TITLE_ONLY]):
        return "q matches posting text unless q_fields: title (docs/jobs/freehire.md #Title search)"
    if isinstance(params["q"], list):
        return "q: one title phrase per pass - the job search has no OR (docs/jobs/freehire.md #Title search)"
    return None


def db_path(config: dict) -> Path:
    path = ROOT / config["db"]
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def resume_path(config: dict, key: str) -> Path:
    return ROOT / config["resume"][key]


def resume_font(config: dict) -> str:
    """Typeface the resume renders in. A user who asks for another gets it here; every page
    measurement follows from the file, so nothing else needs changing (resume/typeface.py)."""
    return config["resume"]["font"]


def title_mirror_always(config: dict) -> bool:
    """User pre-approved the posting's title in brackets after their own: not asked per job."""
    return config["resume"].get("title_mirror") == "always"


def load_or_defaults() -> dict:
    """Merged settings when the user has them, the shipped defaults when they do not - for the
    commands that can run off an explicit path before setup (resume-render --master)."""
    return load() if config_path().exists() else defaults()


def tier_order(config: dict) -> list[str]:
    """Each tier once, in pass order: two passes may fill one tier (an internship search reads
    two of the job search's tags, each its own pass)."""
    return list(dict.fromkeys(p["tier"] for p in config["passes"]))
