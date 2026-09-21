import os
from pathlib import Path

import yaml

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
# q= matches description prose => off-lane titles for any occupation (docs/freehire.md)
FORBIDDEN_PARAMS = {"q"}
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
            f"{path} missing. Ask your AI to set up Job Finder (job-setup skill), "
            "or copy app/profiles/example.yml there and edit it."
        )
    config = merge(defaults(), yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    for p in config["passes"]:
        bad = FORBIDDEN_PARAMS & p["params"].keys()
        if bad:
            raise ValueError(f"pass {p['tier']}: forbidden params {sorted(bad)} (docs/freehire.md)")
        geo = GEOGRAPHY_PARAMS & p["params"].keys()
        if len(geo) > 1:
            raise ValueError(f"pass {p['tier']}: {sorted(geo)} OR together, keep one (docs/freehire.md)")
    return config


def db_path(config: dict) -> Path:
    path = ROOT / config["db"]
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def resume_path(config: dict, key: str) -> Path:
    return ROOT / config["resume"][key]


def tier_order(config: dict) -> list[str]:
    return [p["tier"] for p in config["passes"]]
