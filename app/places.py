"""How far a job's office is from where they live, in miles - straight line, an estimate of the commute.

Home = their saved home address (city + state), else their resume's location. A job's place = the first
town its location names that the town list knows (`us-places.tsv`: GeoNames cities1000, US towns of
1,000+ people, CC BY 4.0), else the job search's own city tags; several offices => the nearest. A town
named w/o a state is read in the tier's `states` (else their home state) - "Newark, United States" in a
New York City area search is Newark NJ, not Newark CA - else the biggest town of that name. Why + basis:
app/docs/jobs/best-next.md #Distance.
"""
import math
import re
from functools import cache
from pathlib import Path

import rank

PLACES = Path(__file__).with_name("us-places.tsv")
# names job boards write that the town list spells otherwise
ALIASES = {"new york": "new york city", "nyc": "new york city", "bronx": "the bronx", "washington dc": "washington",
           "washington d.c.": "washington", "st. louis": "saint louis", "st louis": "saint louis", "st. paul": "saint paul",
           "st paul": "saint paul", "st. petersburg": "saint petersburg", "ft. lauderdale": "fort lauderdale",
           "ft lauderdale": "fort lauderdale", "ft. worth": "fort worth", "ft worth": "fort worth"}
# one office per piece: "Boca Raton; Boston; New York City", "Raleigh, NC / New York City, NY", "Plano, TX or Jersey
# City", "Madhive HQ (New York, NY)"
OFFICES = re.compile(r"\s*(?:;|\||/|\(|\)|\bor\b|\band\b|\n)\s*", re.I)
# words around a town name that are no part of it: "Madhive HQ (New York, NY)", "Greater Boston Area", "Hybrid - Denver"
NOISE = re.compile(r"(?i)\b(?:greater|metro(?:politan)?|area|hq|headquarters|office|downtown|hybrid|on-?site|in-?office|"
                   r"remote|city of|county)\b|\d{5}(?:-\d{4})?|[()\[\]]")


@cache
def towns() -> dict[str, list[tuple[str, float, float, int, str]]]:
    """lower-case name -> [(state, lat, lon, population, name)], biggest first."""
    out: dict[str, list] = {}
    for line in PLACES.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        name, state, lat, lon, pop = line.split("\t")
        out.setdefault(name.lower(), []).append((state, float(lat), float(lon), int(pop), name))
    for v in out.values():
        v.sort(key=lambda t: -t[3])
    return out


def town(name: str, states: set[str] = frozenset(), prefer: set[str] = frozenset()) -> tuple[float, float, str] | None:
    """A town's (lat, lon, its own name - "New York City" for "NEW YORK"): in one of `states` when the place names one, else in `prefer` (their
    search's own states), else the biggest of that name. Unknown name => None."""
    written = re.sub(r"\s+", " ", NOISE.sub(" ", name)).strip(" ,.-")
    found = towns().get(ALIASES.get(written.lower(), written.lower()))
    if not found:
        return None
    for pick in (states, prefer):
        if pick:
            if inside := [t for t in found if t[0] in pick]:
                return inside[0][1], inside[0][2], inside[0][4]
            if pick is states:
                return None
    return found[0][1], found[0][2], found[0][4]


def miles(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Great-circle distance (haversine), miles."""
    (la1, lo1), (la2, lo2) = (map(math.radians, p[:2]) for p in (a, b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def located(text: str | None, prefer: set[str] = frozenset()) -> tuple[float, float, str] | None:
    """One place written "Town, ST" / "Town, State, United States" / "Area, Town": the first piece the town
    list knows, read in the state it names."""
    text = text or ""
    states = rank.states_named(text)
    for piece in text.split(","):
        if piece.strip() and (at := town(piece, states, prefer)):
            return at
    return None


def home(config: dict, facts: dict | None) -> tuple[float, float, str] | None:
    """Where they live: their saved home address's town, else their resume's location."""
    addr = config.get("home_address") or {}
    if addr.get("city"):
        if at := located(f"{addr['city']}, {addr.get('state') or ''}"):
            return at
    return located((facts or {}).get("location"))


def distance(job: dict, here: tuple | None, prefer: set[str] = frozenset()) -> tuple[float, str] | None:
    """(miles, town) from home to the job's nearest office its location names, else to the nearest of its
    city tags. Home or every office unknown => None."""
    if here is None:
        return None
    offices = [at for part in OFFICES.split(job.get("location") or "") if (at := located(part, prefer))]
    if not offices:
        offices = [at for c in job.get("cities") or [] if (at := town(c, prefer=prefer))]
    return min(((miles(here, at), at[2]) for at in offices), default=None)
