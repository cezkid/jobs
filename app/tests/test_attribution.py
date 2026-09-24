import json
import os
import subprocess

import pytest

import attribution

MESSAGE = """rank: demote stale jobs

Body line about Claude Chrome extension stays.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_abc
"""


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))
    return tmp_path


def test_strip_removes_every_credit_line_and_keeps_the_rest():
    assert attribution.strip(MESSAGE) == (
        "rank: demote stale jobs\n\nBody line about Claude Chrome extension stays.\n")


@pytest.mark.parametrize("settings, commit, pr", [
    ({}, None, None),
    ({"includeCoAuthoredBy": False}, "off", "off"),
    ({"includeCoAuthoredBy": True}, "on", "on"),
    ({"attribution": False}, "off", "off"),
    ({"attribution": {"commit": "", "pr": ""}}, "off", "off"),
    ({"attribution": {"commit": ""}, "includeCoAuthoredBy": True}, "off", "on"),
    ({"attribution": {"commit": "Assisted-by: me"}}, "on", None),
])
def test_state_follows_claude_code_settings(settings, commit, pr):
    assert (attribution.state("commit", settings), attribution.state("pr", settings)) == (commit, pr)


def test_choose_off_keeps_other_settings_and_on_undoes_it(home):
    path = attribution.user_settings()
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"theme": "dark", "includeCoAuthoredBy": True}))
    attribution.choose(on=False)
    saved = json.loads(path.read_text())
    assert saved == {"theme": "dark", "attribution": attribution.OFF}
    attribution.choose(on=True)
    assert json.loads(path.read_text()) == {"theme": "dark"}


def test_project_local_settings_override_user(home, tmp_path):
    attribution.choose(on=False)
    local = tmp_path / "proj" / ".claude" / "settings.local.json"
    local.parent.mkdir(parents=True)
    local.write_text(json.dumps({"attribution": {"commit": "x", "pr": "y"}}))
    assert attribution.state("commit", attribution.merged(tmp_path / "proj")) == "on"


def test_hook_strips_commits_only_when_setting_is_off(home, tmp_path):
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    assert attribution.install_hook(repo).startswith("installed")
    git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com"]

    def commit_body(name):
        (repo / name).write_text(name)
        subprocess.run(git + ["add", name], check=True)
        subprocess.run(git + ["commit", "-q", "-m", MESSAGE], check=True,
                       env={**os.environ, "CLAUDE_CONFIG_DIR": str(home / "claude")})
        return subprocess.run(git + ["log", "-1", "--format=%B"], capture_output=True, text=True).stdout

    assert "Co-Authored-By: Claude" in commit_body("a")  # never chosen: left as Claude Code wrote it
    attribution.choose(on=False)
    assert "Claude <noreply" not in commit_body("b") and "Generated with" not in commit_body("c")


def test_hook_never_overwrites_someone_elses(tmp_path):
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    hook = repo / ".git" / "hooks" / "commit-msg"
    hook.write_text("#!/bin/sh\necho mine\n")
    assert attribution.install_hook(repo).startswith("kept")
    assert hook.read_text() == "#!/bin/sh\necho mine\n"
