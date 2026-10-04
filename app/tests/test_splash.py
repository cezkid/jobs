import json
import os
import shutil
import subprocess
import sys
import time

import pytest

import cfg
from window import brand

INSTALL = cfg.APP / "install"
SPLASH = INSTALL / "splash-mac.js"
START = INSTALL / "start-mac.sh"
# runs osascript: --dry builds the window and never shows it
mac = pytest.mark.skipif(sys.platform != "darwin" or not shutil.which("osascript"), reason="Mac splash runs under osascript")
bash = pytest.mark.skipif(not shutil.which("bash") or os.name == "nt", reason="mac launcher runs in bash")


def root(tmp_path, look=None):
    # tmp root w/ a space, like "/Users/Your Name/jobs"
    home = tmp_path / "Your Name" / "jobs"
    (home / ".data").mkdir(parents=True)
    (home / "app" / "install").mkdir(parents=True)
    shutil.copy(INSTALL / "icon.icns", home / "app" / "install")
    (home / ".data" / "splash-start").write_text("")
    if look:
        (home / ".data" / "look").write_text(look + "\n")
    return home


def dry(home) -> dict:
    out = subprocess.run(["osascript", "-l", "JavaScript", str(SPLASH), str(home), "--dry"],
                         capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


@mac
def test_splash_compiles(tmp_path):
    out = subprocess.run(["osacompile", "-l", "JavaScript", "-o", str(tmp_path / "splash.scpt"), str(SPLASH)],
                         capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    assert (tmp_path / "splash.scpt").stat().st_size


@mac
@pytest.mark.parametrize("look, appearance", [("light", "NSAppearanceNameAqua"), ("dark", "NSAppearanceNameDarkAqua")])
def test_splash_dry_floats_without_a_dock_icon_in_the_chosen_look(tmp_path, look, appearance):
    made = dry(root(tmp_path, look))
    assert made["shown"] is False
    assert made["level"] == 3  # NSFloatingWindowLevel: a normal window sits under VS Code's
    assert made["policy"] == 1  # accessory: no Dock icon
    # labelWithString's own colour is white on paper in dark mode => colours + appearance both set
    assert (made["look"], made["appearance"]) == (look, appearance)
    assert made["used"] == made["colours"][look]
    assert made["icon"] is True
    assert made["text"] == ["CEZ Job Finder", "Opening...", "The first start can take a minute."]
    assert made["cap"] == 45


@mac
def test_splash_colours_are_brand_tokens_and_readable(tmp_path):
    colours = dry(root(tmp_path, "light"))["colours"]
    assert colours == {
        "light": {"background": brand.PAPER, "title": brand.INK, "text": brand.INK, "hint": brand.INK_2},
        "dark": {"background": brand.DESK, "title": brand.TEXT_DARK, "text": brand.TEXT_DARK, "hint": brand.TEXT_DARK_2},
    }
    for look, parts in colours.items():
        for part in ("title", "text", "hint"):
            assert brand.contrast(parts[part], parts["background"]) >= 4.5, (look, part)
        # yellow = clickable (owner 2026-10-03); nothing on the splash is
        assert not {brand.MARK, brand.MARK_2} & set(parts.values()), look


def test_splash_source_keeps_the_bridge_rules():
    body = SPLASH.read_text(encoding="utf-8")
    code = "\n".join(line.split("//")[0] for line in body.splitlines())
    # bridge constants come back as strings / too big => numeric literals only
    for name in ("$.NSFloatingWindowLevel", "$.NSEventMaskAny", "$.NSApplicationActivationPolicyAccessory"):
        assert name not in code, name
    # runUntilDate never delivers clicks; sendEvent / activate would take focus from the app in use
    assert "nextEventMatchingMaskUntilDateInModeDequeue" in code
    for banned in ("runUntilDate", "sendEvent", "activateIgnoringOtherApps", "makeKeyAndOrderFront", "screencapture"):
        assert banned not in code, banned
    assert "if (!dry) win.orderFrontRegardless" in code  # the only line that shows it
    # no pid file / single instance: a reused pid would hide the splash for good
    assert "pid" not in code.lower()
    for token in (brand.MARK, brand.MARK_2):
        assert token not in body.lower()


@mac
def test_splash_missing_icon_and_look_still_build(tmp_path):
    home = root(tmp_path)
    (home / "app" / "install" / "icon.icns").unlink()
    made = dry(home)
    assert made["icon"] is False and made["look"] in ("light", "dark")
    assert made["used"] == made["colours"][made["look"]]


@mac
def test_splash_dry_closes_on_a_ready_file_as_new_as_its_start(tmp_path):
    home = root(tmp_path, "light")
    start = home / ".data" / "splash-start"
    (home / ".data" / "window-ready").write_text("now\n")
    made = dry(home)
    assert made["closed"] == "ready" and made["waited"] < 0.9
    # >=: same time counts (whole-second filesystems)
    same = start.stat().st_mtime_ns
    os.utime(home / ".data" / "window-ready", ns=(same, same))
    assert dry(home)["closed"] == "ready"


@mac
def test_splash_dry_ignores_last_starts_ready_file_until_the_cap(tmp_path):
    home = root(tmp_path, "dark")
    ready = home / ".data" / "window-ready"
    ready.write_text("last start\n")
    old = time.time() - 60
    os.utime(ready, (old, old))
    began = time.monotonic()
    made = dry(home)
    assert made["closed"] == "cap" and 1 <= made["waited"] < 3
    assert time.monotonic() - began < 10  # 1 s cap in --dry, never the real 45 s


def test_splash_start_script_shows_it_before_update():
    lines = START.read_text(encoding="utf-8").splitlines()
    at = {word: next(i for i, line in enumerate(lines) if line.startswith(word)) for word in
          ("mkdir -p .data", ": > .data/splash-start", "osascript -l JavaScript", "uv run app/jobs.py update", "uv run app/jobs.py launch")}
    assert sorted(at.values()) == list(at.values()), at
    # in the background w/ nothing to wait on: the launcher goes on to update at once
    assert lines[at["osascript -l JavaScript"]] == 'osascript -l JavaScript app/install/splash-mac.js "$PWD" >/dev/null 2>&1 &'
    # ready signal before the alert: the splash floats over it
    assert "launch || { : > .data/window-ready; osascript -e 'display alert" in lines[at["uv run app/jobs.py launch"]]


def stub(folder, name, body):
    path = folder / name
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(0o755)


def run_start(tmp_path, launch_exit: int):
    """start-mac.sh in a tmp copy w/ stub uv + osascript first on its PATH: nothing real runs."""
    home = tmp_path / "Your Name"
    jobs = home / "jobs"
    (jobs / "app" / "install").mkdir(parents=True)
    shutil.copy(START, jobs / "app" / "install")
    bin_dir = home / ".local" / "bin"  # start-mac.sh puts $HOME/.local/bin first
    bin_dir.mkdir(parents=True)
    log = tmp_path / "calls.log"
    seen = '$([ -e .data/splash-start ] && echo splash-start) $([ -e .data/window-ready ] && echo window-ready)'
    stub(bin_dir, "uv", f'echo "uv $3 | {seen}" >> "{log}"\n[ "$3" = launch ] && exit {launch_exit}\nexit 0\n')
    stub(bin_dir, "osascript", f'echo "osascript $* | {seen}" >> "{log}"\n')
    env = {**os.environ, "HOME": str(home)}
    out = subprocess.run(["bash", str(jobs / "app" / "install" / "start-mac.sh")], env=env, cwd=tmp_path,
                         capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr

    def calls():
        return log.read_text().splitlines() if log.exists() else []

    # splash runs in the background => its line may land after the script ends
    end = time.monotonic() + 5
    while time.monotonic() < end and not any(c.startswith("osascript -l") for c in calls()):
        time.sleep(0.05)
    return jobs, calls()


@bash
def test_splash_start_script_starts_it_with_the_folder_then_updates_and_launches(tmp_path):
    jobs, calls = run_start(tmp_path, launch_exit=0)
    splash = [c for c in calls if c.startswith("osascript")]
    assert len(splash) == 1 and splash[0].startswith("osascript -l JavaScript app/install/splash-mac.js ")
    assert splash[0].split(" | ")[0].endswith("Your Name/jobs")  # whole folder, space kept
    assert [c for c in calls if c.startswith("uv")] == ["uv update | splash-start ", "uv launch | splash-start "]
    # launch worked => ready signal is the window's to write, never the script's
    assert not (jobs / ".data" / "window-ready").exists()


@bash
def test_splash_start_script_closes_it_before_the_alert_when_launch_fails(tmp_path):
    jobs, calls = run_start(tmp_path, launch_exit=1)
    assert (jobs / ".data" / "window-ready").exists()
    alert = [c for c in calls if c.startswith("osascript -e")]
    assert len(alert) == 1 and "could not start" in alert[0]
    assert alert[0].endswith("| splash-start window-ready")
    assert calls.index(alert[0]) > calls.index("uv launch | splash-start ")
