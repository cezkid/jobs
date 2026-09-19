import re
from datetime import date
from pathlib import Path

import yaml

PRESENT = "present"
MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
# Greenhouse parse rules: titles unabbreviated (error); company legal identifier = lint warn only,
# hospitals, schools, agencies carry none
ABBREVIATED_TITLE = re.compile(r"\b(Sr|Jr)\b\.?", re.I)
LEGAL_IDENTIFIER = re.compile(
    r"\b(Inc|LLC|L\.L\.C|Ltd|Corp|Corporation|Co|Company|GmbH|PBC|LP|LLP|PLC|S\.A|B\.V|AG|Pty)\.?$"
)
# HBS/Accenture 2021: gap past this = automatic screen-out at ~half of employers
MAX_GAP_MONTHS = 6


def load(path: Path) -> dict:
    master = yaml.safe_load(path.read_text(encoding="utf-8"))
    errors = validate(master)
    if errors:
        raise ValueError(f"{path}:\n  " + "\n  ".join(errors))
    return master


def month_index(value: str, today: date) -> int:
    if value == PRESENT:
        return today.year * 12 + today.month - 1
    year, month = value.split("-")
    return int(year) * 12 + int(month) - 1


def month_label(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def employment_gaps(master: dict, today: date) -> list[dict]:
    spans = sorted((month_index(r["start"], today), month_index(r["end"], today)) for r in master["roles"])
    now = month_index(PRESENT, today)
    gaps = []
    covered_through = spans[0][1]
    # today as zero-length span => unemployment since last role counts as gap too
    for start, end in [*spans[1:], (now, now)]:
        months = start - covered_through - 1
        if months > MAX_GAP_MONTHS:
            gaps.append({"after": month_label(covered_through), "before": month_label(start), "months": months})
        covered_through = max(covered_through, end)
    return gaps


def validate(master) -> list[str]:
    errors: list[str] = []
    if not isinstance(master, dict):
        return ["master: expected mapping"]
    contact = field(master, "contact", dict, "master", errors)
    if contact is not None:
        for key in ("name", "email", "location"):
            text(contact, key, "contact", errors)
        optional(contact, "phone", str, "contact", errors)
        strings(contact, "links", "contact", errors)
    optional(master, "summary", str, "master", errors)

    bullet_ids: set[str] = set()
    roles = field(master, "roles", list, "master", errors)
    if roles is not None:
        if not roles:
            errors.append("master.roles: empty")
        for i, role in enumerate(roles):
            validate_entry(role, f"roles[{i}]", ("company", "title"), bullet_ids, errors)
            if isinstance(role, dict):
                check_role_title(role, f"roles[{i}]", errors)
        check_reverse_chronological(roles, "roles", errors)
    projects = optional(master, "projects", list, "master", errors) or []
    for i, project in enumerate(projects):
        validate_entry(project, f"projects[{i}]", ("name",), bullet_ids, errors)
    check_reverse_chronological(projects, "projects", errors)

    for i, group in enumerate(optional(master, "skills", list, "master", errors) or []):
        where = f"skills[{i}]"
        if isinstance(group, dict):
            text(group, "group", where, errors)
            strings(group, "items", where, errors, required=True)
        else:
            errors.append(f"{where}: expected mapping")
    for i, school in enumerate(optional(master, "education", list, "master", errors) or []):
        where = f"education[{i}]"
        if isinstance(school, dict):
            text(school, "institution", where, errors)
            text(school, "degree", where, errors)
            optional(school, "field", str, where, errors)
            optional(school, "details", str, where, errors)
            month(school, "end", where, errors, required=False)
        else:
            errors.append(f"{where}: expected mapping")
    for i, cert in enumerate(optional(master, "certifications", list, "master", errors) or []):
        where = f"certifications[{i}]"
        if isinstance(cert, dict):
            text(cert, "name", where, errors)
            optional(cert, "issuer", str, where, errors)
            month(cert, "date", where, errors, required=False)
        else:
            errors.append(f"{where}: expected mapping")
    strings(master, "languages", "master", errors)
    return errors


def validate_entry(entry, where: str, named: tuple[str, ...], bullet_ids: set[str], errors: list[str]) -> None:
    if not isinstance(entry, dict):
        errors.append(f"{where}: expected mapping")
        return
    entry_id = text(entry, "id", where, errors)
    if entry_id and not ID.match(entry_id):
        errors.append(f"{where}.id: {entry_id!r} not lowercase-kebab")
    for key in named:
        text(entry, key, where, errors)
    optional(entry, "location", str, where, errors)
    optional(entry, "blurb", str, where, errors)
    start = month(entry, "start", where, errors, required=True)
    end = month(entry, "end", where, errors, required=True, allow_present=True)
    if start and end and end != PRESENT and end < start:
        errors.append(f"{where}: end {end} before start {start}")
    ai_era = optional(entry, "ai_era", bool, where, errors) or False
    bullets = field(entry, "bullets", list, where, errors) or []
    for j, bullet in enumerate(bullets):
        validate_bullet(bullet, f"{where}.bullets[{j}]", ai_era, bullet_ids, errors)


def validate_bullet(bullet, where: str, entry_ai_era: bool, bullet_ids: set[str], errors: list[str]) -> None:
    if not isinstance(bullet, dict):
        errors.append(f"{where}: expected mapping")
        return
    bullet_id = text(bullet, "id", where, errors)
    if bullet_id:
        if not ID.match(bullet_id):
            errors.append(f"{where}.id: {bullet_id!r} not lowercase-kebab")
        if bullet_id in bullet_ids:
            errors.append(f"{where}.id: {bullet_id!r} duplicate")
        bullet_ids.add(bullet_id)
    text(bullet, "claim", where, errors)
    strings(bullet, "metrics", where, errors)
    strings(bullet, "stack", where, errors)
    # role predating AI work never carries AI bullet - backdated AI claim falsifiable on dates alone
    if optional(bullet, "ai_work", bool, where, errors) and not entry_ai_era:
        errors.append(f"{where}: ai_work bullet inside entry with ai_era false")


def check_role_title(role: dict, where: str, errors: list[str]) -> None:
    title = role.get("title")
    if isinstance(title, str) and ABBREVIATED_TITLE.search(title):
        errors.append(f"{where}.title: {title!r} abbreviated - spell out Senior/Junior")


def check_reverse_chronological(entries: list, where: str, errors: list[str]) -> None:
    starts = [e.get("start") for e in entries if isinstance(e, dict)]
    if all(isinstance(s, str) and MONTH.match(s) for s in starts) and starts != sorted(starts, reverse=True):
        errors.append(f"{where}: not newest-first by start")


def field(obj: dict, key: str, kind: type, where: str, errors: list[str]):
    if key not in obj:
        errors.append(f"{where}.{key}: missing")
        return None
    return optional(obj, key, kind, where, errors)


def optional(obj: dict, key: str, kind: type, where: str, errors: list[str]):
    value = obj.get(key)
    if value is not None and not isinstance(value, kind):
        errors.append(f"{where}.{key}: expected {kind.__name__}, got {type(value).__name__}")
        return None
    return value


def text(obj: dict, key: str, where: str, errors: list[str]) -> str | None:
    value = field(obj, key, str, where, errors)
    if value is not None and not value.strip():
        errors.append(f"{where}.{key}: empty")
        return None
    return value


def strings(obj: dict, key: str, where: str, errors: list[str], required: bool = False) -> list[str]:
    values = (field if required else optional)(obj, key, list, where, errors) or []
    if any(not isinstance(v, str) or not v.strip() for v in values):
        errors.append(f"{where}.{key}: expected non-empty strings")
    return values


def month(obj: dict, key: str, where: str, errors: list[str], required: bool, allow_present: bool = False) -> str | None:
    value = obj.get(key)
    if value is None:
        if required:
            errors.append(f"{where}.{key}: missing")
        return None
    if allow_present and value == PRESENT:
        return value
    # unquoted YYYY-MM-DD loads as date => rejected, YYYY-MM loads as str
    if not isinstance(value, str) or not MONTH.match(value):
        errors.append(f"{where}.{key}: {value!r} not YYYY-MM" + (" or present" if allow_present else ""))
        return None
    return value
