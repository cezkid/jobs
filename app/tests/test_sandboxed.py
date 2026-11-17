"""--sandboxed: what an agent in a sandbox (no internet, no local port, no Chrome, no desktop) runs."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def pytest_run(*args: str) -> str:
    out = subprocess.run([sys.executable, "-m", "pytest", "-n", "0", "-p", "no:cacheprovider", *args],
                         cwd=ROOT, capture_output=True, text=True, timeout=300)
    return out.stdout + out.stderr


def test_sandboxed_leaves_out_live_loopback_and_desktop_tests():
    got = pytest_run("--sandboxed", "--collect-only", "-q", "app/tests/test_gates_live.py",
                     "app/tests/test_companies.py", "app/tests/test_word.py", "app/tests/test_apply_in_window.py")
    assert "--sandboxed:" in got
    assert "test_gates_live.py::" not in got
    assert "test_live_companies_endpoint_has_a_website" not in got
    assert "test_older_word_file_read_on_a_mac" not in got
    assert "Restricted Mode" not in got
    # the rest of those files still runs: the offline companies tests, the window-not-open case
    assert "test_link_none_without_a_website" in got
    assert "Job Finder window isn't open" in got


def test_sandboxed_browser_test_skips_instead_of_starting_chrome():
    got = pytest_run("--sandboxed", "-rs", "app/tests/test_dom.py::test_captcha_frame_listed_not_read")
    assert "1 skipped" in got and "Chrome cannot start in a sandbox" in got, got


def test_without_sandboxed_nothing_is_left_out():
    got = pytest_run("--collect-only", "-q", "app/tests/test_companies.py")
    assert "test_live_companies_endpoint_has_a_website" in got
