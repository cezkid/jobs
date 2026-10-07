"""measure.py raw's pure parts (plan-k8n.1): the ready test, the scrub, the tenants.txt lines.
Importable (measure.py reads its argv at import): app/tests/test_measure_raw.py checks them on
local pages + every system's EXAMPLES links.

  ready   a system's READY is a Playwright selector: ':visible' (Oracle, iCIMS, ADP) throws in
          document.querySelector, and SmartRecruiters' boxes sit in open shadow roots it can't see.
          count_js() splits it at top-level commas, turns ':visible' into Playwright's own test
          (non-empty box, not visibility:hidden) and walks every open shadow root
  scrub   per link, not per system shape: parse_url's parts (any length - Paylocity's is 1), the
          tenant's own host + its labels (Oracle pods, iCIMS careers-<tenant>), path parts + query
          values of the posting + form links. Shared hosts (apply.workable.com ...) stay readable
  tenants org / host / tenant names for .data/measure/tenants.txt, as lab.py's measure appends
"""
import json
import re
from urllib.parse import parse_qsl, unquote, urlsplit

from apply import lab

# one host for every employer: kept in the saved JSON, never a tenant line
SHARED_HOST = re.compile(r"(?:apply\.workable\.com|jobs\.smartrecruiters\.com|workforcenow\.adp\.com|recruiting\.paylocity\.com"
                         r"|recruiting\d*\.ultipro\.com|(?:www\.)?paycomonline\.net|jobs\.ashbyhq\.com|jobs(?:\.eu)?\.lever\.co"
                         r"|(?:job-)?boards(?:\.eu)?\.greenhouse\.io|careers-page\.com|ats\.rippling\.com)", re.I)
# path parts + query keys every tenant of a system shares: never scrubbed
PATH_WORDS = {"apply", "application", "jobs", "job", "j", "careers", "embed", "job_app", "jobboard", "opportunitydetail",
              "opportunityapply", "hcmui", "candidateexperience", "sites", "email", "login", "recruiting", "details",
              "v4", "ats", "web.php", "portal", "viewjobdetails", "mascsr", "default", "mdf", "recruitment",
              "recruitment.html", "oneclick-ui", "company", "publication", "en", "es", "en_us", "en-us", "true"}
# parse_url parts that name the tenant where lab.tenants (host labels, the path's first part) misses
# it: ADP's cid, Oracle's site, Paycom's portal key. Ids + job slugs never: no name, and a slug
# ("manager") would hit every grep
TENANT_PART = {"ADP Workforce Now": (0,), "Oracle Recruiting Cloud": (1,), "Paycom": (0,)}
VISIBLE = re.compile(r":visible(?![\w-])")


def ready_parts(selector: str) -> list[tuple[str, bool]]:
    """Playwright selector -> [(plain CSS, must be visible)], one per top-level comma part.
    ':visible' must close its part: on an ancestor it would test the wrong element."""
    parts, depth, quote, start = [], 0, "", 0
    for i, ch in enumerate(selector):
        if quote:
            quote = "" if ch == quote and selector[i - 1] != "\\" else quote
        elif ch in "'\"":
            quote = ch
        elif ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == "," and not depth:
            parts.append(selector[start:i])
            start = i + 1
    parts.append(selector[start:])
    out = []
    for part in (p.strip() for p in parts):
        css = part.removesuffix(":visible")
        if VISIBLE.search(re.sub(r"'[^']*'|\"[^\"]*\"", "", css)):  # quoted text aside
            raise ValueError(f"':visible' only at the end of a part: {part!r}")
        out.append((css, css != part))
    return out


def count_js(selector: str) -> str:
    """JS expression: how many elements match, in the document + every open shadow root."""
    return f"""(() => {{ const roots = [];
  const walk = (r) => {{ roots.push(r); for (const e of r.querySelectorAll('*')) if (e.shadowRoot) walk(e.shadowRoot); }};
  walk(document);
  const shown = (e) => {{ const b = e.getBoundingClientRect(); return b.width > 0 && b.height > 0 && getComputedStyle(e).visibility !== 'hidden'; }};
  const out = new Set();
  for (const [css, vis] of {json.dumps(ready_parts(selector))})
    for (const r of roots) for (const e of r.querySelectorAll(css)) if (!vis || shown(e)) out.add(e);
  return out.size; }})()"""


def ready_js(selector: str) -> str:
    return f"document.readyState === 'complete' && {count_js(selector)} > 0"


def _tenant_host(url: str) -> str | None:
    host = (urlsplit(url).hostname or "").casefold()
    return host if host and not SHARED_HOST.fullmatch(host) else None


def _parts(system, url: str) -> list[str]:
    """parse_url's parts, the tenant's host + its labels, path parts, query values."""
    try:
        got = [str(p) for p in system.parse_url(url)]
    except ValueError:
        got = []
    u = urlsplit(url.strip())
    if host := _tenant_host(url):
        labels = host.split(".")
        got += [host, *labels, *(p for lab_ in labels for p in lab_.split("-"))]
    got += [unquote(p) for p in u.path.split("/")] + [p for p in u.path.split("/") if "%" in p]
    got += [v for _, v in parse_qsl(u.query)]
    return got


def kind(part: str) -> str:
    return "<host>" if "." in part else "<id>" if re.search(r"\d", part) else "<org>"


def scrub_pairs(system, *urls: str) -> list[tuple[str, str]]:
    """(tenant text, placeholder) for every part of these links that names the employer or posting,
    longest first - a part inside a longer one (acme in careers-acme) goes after it. Short letter
    parts (us2, ocs) left: they'd cut into every word holding them."""
    seen = {}
    for url in urls:
        for p in _parts(system, url):
            p = p.strip()
            if len(p) < (3 if p.isdigit() else 4) or p.casefold() in lab.GENERIC | PATH_WORDS | {"freehire.me"} or SHARED_HOST.fullmatch(p):
                continue
            seen.setdefault(p.casefold(), p)
    return sorted(((p, kind(p)) for p in seen.values()), key=lambda t: -len(t[0]))


def scrub(text: str, pairs: list[tuple[str, str]]) -> str:
    """One pass, any case: a placeholder is never scrubbed again. Digits-only parts match whole
    numbers only (id 101 leaves readyMs 1012 alone)."""
    if not pairs:
        return text
    rx = "|".join(rf"(?<!\d){re.escape(p)}(?!\d)" if p.isdigit() else re.escape(p) for p, _ in pairs)
    place = {p.casefold(): b for p, b in pairs}
    return re.sub(rx, lambda m: place[m.group(0).casefold()], text, flags=re.I)


def scrub_values(value, pairs: list[tuple[str, str]]):
    """scrub() on every string value, keys left whole: a tenant named like a key can't break the JSON."""
    if isinstance(value, dict):
        return {k: scrub_values(v, pairs) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [scrub_values(v, pairs) for v in value]
    return scrub(value, pairs) if isinstance(value, str) else value


def tenant_lines(system, urls: list[str], names: list[str] = ()) -> list[str]:
    """What names this employer, for tenants.txt: lab.tenants per link (names, host labels, the
    path's tenant part), the tenant's own host, TENANT_PART."""
    out = [n for n in names if n.casefold() not in lab.GENERIC]  # og:site_name can be the platform's own
    for url in urls:
        out += lab.tenants(url, [], {"controls": []})
        if host := _tenant_host(url):
            out.append(host)
        try:
            got = system.parse_url(url)
        except ValueError:
            got = ()
        out += [got[i] for i in TENANT_PART.get(system.NAME, ()) if i < len(got)]
    return list(dict.fromkeys(s for s in out if s and s.casefold() not in lab.CHROME))
