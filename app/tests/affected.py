"""Which test files a change can reach: `uv run pytest --changed` runs only those.

The full suite takes ~14 minutes (2,220 tests, 2026-10-08): 75% browser form-filler tests. They
can't run side by side - 9 timing comparisons failed under 8 workers (pytest-xdist) - so speed comes
from running fewer. A test file is picked when it changed, or a file it imports (at the top or inside
a function) changed, or a file one of those imports changed (DEPTH). Reaches past imports, each erring wide:
- a command a test runs through jobs.py (argv "jobs.py", "today" or `jobs.py today`) -> that command's module;
  a test naming `app/launch.py` or another top-level file run as a process -> that module;
- a data file (`defaults.yml`, `setup-form.json`, `today.js`): every module or test whose source names
  it counts as changed;
- any `.md`: test_docs (every link checked); `docs/` or `app/web/`: the site tests;
- conftest, pyproject.toml, uv.lock, this file: everything.
An estimate to work fast: the full `uv run pytest` still runs before a fix is sent (CONTRIBUTING).
"""
import ast
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"
TESTS = APP / "tests"
SKIP = {"tests", "docs", "__pycache__"}
EVERYTHING = {"app/tests/conftest.py", "app/tests/affected.py", "pyproject.toml", "uv.lock"}
SITE_TESTS = ("test_site.py", "test_web.py", "test_claims.py")
# import steps followed back from a change: 2 = the changed file's own tests + the tests of every
# file that uses it. Measured on the 2026-10-08 suite (841s): a rank.py change picks 13 test files,
# 31s, at 2; 31 files, 335s, at 3; 64, 716s, unlimited - the browser form fillers reach rank only
# 4 steps away (filler -> questions -> tailor -> report -> rank), never through what they test.
# --changed-depth N widens it
DEPTH = 2


def changed_files(ref: str = "HEAD") -> list[str]:
    """Paths (repo-relative) changed against `ref`, staged or not, plus new untracked files."""
    git = lambda *a: subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True,
                                    check=True).stdout.splitlines()
    return sorted(set(git("diff", "--name-only", ref)) | set(git("ls-files", "--others", "--exclude-standard")))


def nodes() -> dict[str, Path]:
    """Program modules by import name (ingest.freehire, resume.knockout) + test-dir modules by stem."""
    out = {}
    for p in APP.rglob("*.py"):
        rel = p.relative_to(APP)
        if rel.parts[0] in SKIP or "__pycache__" in rel.parts:
            continue
        name = ".".join(rel.with_suffix("").parts)
        out[name.removesuffix(".__init__")] = p
    out.update({p.stem: p for p in TESTS.glob("*.py")})
    return out


def commands() -> dict[str, str]:
    """jobs.py COMMANDS: command name -> module it runs (read off the file, never imported)."""
    tree = ast.parse((APP / "jobs.py").read_text(encoding="utf-8"))
    table = next(n.value for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "COMMANDS")
    return {k.value: v.elts[0].value for k, v in zip(table.keys, table.values)
            if isinstance(v, ast.Tuple) and isinstance(v.elts[0], ast.Constant) and v.elts[0].value}


def imports(path: Path, known: dict[str, Path]) -> set[str]:
    """Known modules a file imports anywhere in it, + every module it names as a string or by path
    (jobs.py runs commands by module name; tests run `app/jobs.py` as a process)."""
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    pkg = ".".join(path.relative_to(APP).parent.parts) if path.is_relative_to(APP) else ""
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            base = n.module or ""
            if n.level:
                parent = pkg.split(".")[:len(pkg.split(".")) - n.level + 1] if pkg else []
                base = ".".join([*parent, base] if base else parent)
            out |= {base} | {f"{base}.{a.name}" if base else a.name for a in n.names}
    # a test running a command (argv ["jobs.py", "today"], `app/jobs.py rank` as a process) reaches that
    # command's module - not every module jobs.py names: many files import it for one helper (open),
    # and following its whole list picked 67 of 80 test files for any change (2026-10-08). The run
    # form only: a bare "email" is also a form field
    if path.parent == TESTS:
        out |= {m for cmd, m in commands().items() if f'jobs.py", "{cmd}"' in text or f"jobs.py {cmd}" in text}
    # dotted names reach their packages too: `import resume.render` runs resume/__init__
    out |= {".".join(m.split(".")[:i]) for m in list(out) for i in range(1, m.count(".") + 1)}
    for name, p in known.items():
        rel = p.relative_to(APP).as_posix()
        if p.parent == APP and (f"app/{rel}" in text or f"/{rel}" in text or f'"{rel}"' in text):
            out.add(name)
    return out & known.keys()


def select(changed: list[str], depth: int = DEPTH) -> tuple[set[str] | None, list[str]]:
    """Test file names to run (None = all) and why, for a list of repo-relative changed paths."""
    if EVERYTHING & set(changed):
        return None, ["test setup changed - everything"]
    known = nodes()
    by_path = {p.resolve(): n for n, p in known.items()}
    sources = {n: p.read_text(encoding="utf-8") for n, p in known.items()}
    hit, why, tests = set(), [], set()
    for f in changed:
        path = (ROOT / f).resolve()
        if path in by_path:
            hit.add(by_path[path])
            continue
        if not path.exists() and f.endswith(".py"):
            # deleted module: whoever named it
            hit |= {n for n, s in sources.items() if Path(f).stem in s}
            continue
        name = Path(f).name
        named = {n for n, s in sources.items() if name in s}
        if named:
            why.append(f"{f} named in {len(named)} files")
        hit |= named
        if f.endswith(".md"):
            tests.add("test_docs.py")
        if f.startswith(("docs/", "app/web/")):
            tests |= {t for t in SITE_TESTS if (TESTS / t).exists()}
    users = defaultdict(set)
    for n, p in known.items():
        for m in imports(p, known):
            users[m].add(n)
    # conftest is every test's helper, not a user of what it imports: through it all would reach all
    users = {m: u - {"conftest"} for m, u in users.items()}
    reached = front = set(hit)
    for _ in range(depth):
        front = {u for m in front for u in users.get(m, ())} - reached
        reached |= front
    tests |= {known[n].name for n in reached if known[n].parent == TESTS and known[n].name.startswith("test_")}
    return tests, why
