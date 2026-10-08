import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

# before any app module is imported: paths built from the home folder at import time land in a
# throwaway one, never the owner's ~/.claude.json, VS Code settings or Desktop icon
REAL_HOME = os.environ.get("HOME", "")
FAKE_HOME = Path(tempfile.mkdtemp(prefix="jobs-test-home-"))
for _name in ("HOME", "USERPROFILE"):
    os.environ[_name] = str(FAKE_HOME)
os.environ["APPDATA"] = str(FAKE_HOME / "AppData" / "Roaming")
os.environ.pop("JOBS_VSCODE_DIR", None)

import pytest  # noqa: E402

import store  # noqa: E402

CODE_NAMES = {"code", "code.cmd", "code.exe"}
# Chrome under a made-up home hangs on its first page load (measured: 2 lab tests time out);
# the tests start it on its own throwaway profile, so the real home is safe to give it
BROWSER_NAMES = {"google chrome", "chromium", "google-chrome", "google-chrome-stable", "msedge", "chrome.exe", "msedge.exe"}
_real_which = shutil.which
_real_popen_init = subprocess.Popen.__init__


def is_code(word) -> bool:
    return Path(str(word)).name.lower() in CODE_NAMES


def reaches_real_vscode(args) -> str | None:
    """Why this command would drive the owner's VS Code; None when it can't."""
    argv = shlex.split(args) if isinstance(args, str) else [str(a) for a in args]
    if any(a.startswith("vscode://") for a in argv):
        return "opens a vscode:// link (macOS hands it to the owner's VS Code)"
    if argv and is_code(argv[0]) and "--user-data-dir" not in argv:
        return "runs VS Code's code command without --user-data-dir (set JOBS_VSCODE_DIR)"
    return None


@pytest.fixture(autouse=True)
def no_real_vscode(request, monkeypatch, tmp_path_factory):
    # a test that reached the real code command drove the owner's open VS Code window, and one
    # writing via the home folder rewrote their Claude trust, VS Code settings or Desktop icon
    home = tmp_path_factory.mktemp("home")
    for name in ("HOME", "USERPROFILE"):
        monkeypatch.setenv(name, str(home))
    monkeypatch.setenv("APPDATA", str(home / "AppData" / "Roaming"))
    monkeypatch.delenv("JOBS_VSCODE_DIR", raising=False)
    opted_in = request.node.get_closest_marker("real_vscode") is not None

    def which(cmd, *args, **kw):
        return _real_which(cmd, *args, **kw) if opted_in or not is_code(cmd) else None

    def popen_init(self, args, *rest, **kw):
        why = reaches_real_vscode(args)
        if why:
            pytest.fail(f"test guard: {why}: {args!r}", pytrace=False)
        argv0 = args if isinstance(args, str) else (args[0] if args else "")
        if Path(str(argv0)).name.lower() in BROWSER_NAMES and kw.get("env") is None and REAL_HOME:
            kw["env"] = {**os.environ, "HOME": REAL_HOME}
        _real_popen_init(self, args, *rest, **kw)

    monkeypatch.setattr(shutil, "which", which)
    monkeypatch.setattr(subprocess.Popen, "__init__", popen_init)


def pytest_configure(config):
    config.addinivalue_line("markers", "real_vscode: test may find the real code command (still only w/ --user-data-dir)")


def pytest_addoption(parser):
    parser.addoption("--changed", nargs="?", const="HEAD", default=None, metavar="REF",
                     help="only test files a change since REF (default HEAD: uncommitted work) can reach; "
                          "affected.py says how. Full run before sending a fix")
    parser.addoption("--changed-depth", type=int, default=None, metavar="N",
                     help="import steps followed back from a change (default 2: its tests + its users' tests)")


def pytest_collection_modifyitems(config, items):
    ref = config.getoption("--changed")
    if ref is None:
        return
    import affected
    changed = affected.changed_files(ref)
    keep, why = affected.select(changed, config.getoption("--changed-depth") or affected.DEPTH)
    reporter = config.pluginmanager.get_plugin("terminalreporter")
    if keep is None:
        reporter and reporter.write_line(f"--changed: {why[0]}: all {len(items)} tests")
        return
    picked = [i for i in items if i.path.name in keep]
    dropped = [i for i in items if i.path.name not in keep]
    if dropped:
        config.hook.pytest_deselected(items=dropped)
        items[:] = picked
    if reporter:
        reporter.write_line(f"--changed {ref}: {len(changed)} files changed -> {len(keep)} test files, "
                            f"{len(picked)} of {len(picked) + len(dropped)} tests: {', '.join(sorted(keep)) or 'none'}")


def make_job(slug: str, **over) -> dict:
    job = {c: None for c in store.COLS}
    job.update(
        public_slug=slug,
        tier="remote",
        title=f"Senior Vue Engineer {slug}",
        company="Acme",
        company_slug="acme",
        url=f"https://boards.greenhouse.io/acme/jobs/{slug}",
        source="greenhouse",
        work_mode="remote",
        countries=["us"],
        cities=[],
        skills=["vue"],
        collections=[],
        employment_type="full_time",
        seniority="senior",
        category="frontend",
        posted_at="2026-09-15T10:00:00Z",
        enrichment={},
        reality={},
    )
    job.update(over)
    return job


@pytest.fixture
def conn():
    c = store.connect(":memory:")
    yield c
    c.close()
