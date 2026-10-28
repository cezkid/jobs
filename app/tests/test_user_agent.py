"""Plain HTTP reads of employers' and hiring systems' pages say who they are (cfg.USER_AGENT)."""
import re

import cfg

BROWSER = re.compile(r"Chrome/|Safari/|Firefox/|Macintosh|Windows NT|AppleWebKit")


def test_app_never_sends_a_browsers_name():
    assert "CEZ-Job-Finder" in cfg.USER_AGENT and not BROWSER.search(cfg.USER_AGENT)
    for path in (cfg.APP / "apply").rglob("*.py"):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "User-Agent" in line:
                assert "cfg.USER_AGENT" in line and not BROWSER.search(line), f"{path.name}:{n}: {line.strip()}"
