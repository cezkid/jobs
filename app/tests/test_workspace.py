import json
import re
import subprocess
from pathlib import Path

import pytest

import cfg
import look
import workspace

HOME = Path("/Users/someone")


@pytest.fixture(autouse=True)
def no_real_look(tmp_path, monkeypatch):
    # a developer's own .data/look would change what every write here produces
    monkeypatch.setattr(look, "CHOICE_FILE", tmp_path / ".data" / "look")


def load(text: str) -> dict:
    return json.loads(re.sub(r"^\s*//.*$", "", text, flags=re.M))


def test_claude_and_chatgpt_hide_builtin_vscode_chat():
    # without this the built-in Copilot chat owns the right-hand panel on first open
    for ai in ("claude", "chatgpt", None):
        settings = workspace.settings(ai)
        assert settings["chat.disableAIFeatures"] is True
        # default puts the chat in a tab and leaves Claude's right-hand sidebar empty, doing nothing
        assert settings["claudeCode.preferredLocation"] == "sidebar"
        assert settings["claudeCode.hideOnboarding"] is True and settings["claudeCode.focusView"] is True
        assert not any(key.startswith("github.copilot") for key in settings)


def test_copilot_shows_its_chat_and_carries_every_key():
    settings = workspace.settings("copilot", HOME)
    assert settings["chat.disableAIFeatures"] is False
    assert settings["chat.newSession.defaultMode"] == "agent"
    assert settings["chat.useClaudeMdFile"] is False
    assert settings["github.copilot.chat.additionalReadAccessPaths"] == [
        str(HOME / "Downloads"), str(HOME / "Desktop"), str(HOME / "Documents")]
    assert settings["github.copilot.enable"] == {"*": False}
    assert settings["github.copilot.nextEditSuggestions.enabled"] is False
    assert settings["chat.sessionSync.enabled"] is False
    # experiment-controlled defaults pinned: which harness, when the agent pauses
    assert settings["chat.defaultToCopilotHarness"] is False
    assert settings["chat.agent.maxRequests"] == 150
    assert settings["github.copilot.chat.workspace.codeSearchExternalIngest.enabled"] is False
    assert all(v is True for v in settings["chat.tools.terminal.autoApprove"].values())
    assert not any(key.startswith("claudeCode.") for key in settings)


def test_every_ai_gets_the_same_window():
    for ai in ("claude", "chatgpt", "copilot", None):
        settings = workspace.settings(ai, HOME)
        # "modified" reshuffled 1 To apply ... 4 Closed whenever a job moved; compact folders
        # squeezed a stage holding one job onto its job's row
        assert settings["explorer.sortOrder"] == "default" and settings["explorer.compactFolders"] is False
        # sidebar shown on open => START HERE in the middle, chat beside it
        assert settings["workbench.secondarySideBar.defaultVisibility"] == "visible"
        # users saw a developer tool: search box, layout buttons, breadcrumbs
        assert settings["window.title"] == cfg.NAME
        assert not settings["window.commandCenter"]
        assert settings["workbench.activityBar.location"] != "hidden"  # ChatGPT's icon is there
        # hiding tab buttons / status bar hid Claude's new-chat and open-chat buttons with them
        assert settings.get("workbench.editor.editorActionsLocation", "default") != "hidden"
        assert settings.get("workbench.statusBar.visible", True)
        assert settings["yaml.schemas"] == {"./app/resume/details.schema.json": "My Resume/Resume details.yml"}


def test_window_browser_keeps_its_sign_ins_to_this_folder():
    # default (global) shares cookies + sign-ins w/ every VS Code window and profile, kept after
    # uninstall; the globe button is experiment-controlled => pinned off
    for ai in ("claude", "chatgpt", "copilot", None):
        settings = workspace.settings(ai, HOME)
        assert settings["workbench.browser.dataStorage"] == "workspace"
        assert settings["workbench.browser.showInTitleBar"] is False
        # chat tools left at VS Code's default: decided in app/docs/app-window.md, not here
        assert "workbench.browser.enableChatTools" not in settings


def test_debug_toolbar_hidden_while_a_form_fills_in_the_window():
    # an attached fill showed VS Code's floating debug bar over the tabs; hidden measured gone, fill
    # the same (vscode-browser.md "Built (c)", 2026-10-07)
    for ai in ("claude", "chatgpt", "copilot", None):
        assert workspace.settings(ai, HOME)["debug.toolBarLocation"] == "hidden"


def codex_commands() -> set[str]:
    rules = (cfg.ROOT / ".codex" / "rules" / "default.rules").read_text(encoding="utf-8")
    found = set()
    for pattern in re.findall(r"pattern\s*=\s*(\[.*?\])\s*,\s*\n", rules, flags=re.S):
        words = [[w] if isinstance(w, str) else w for w in json.loads(pattern)]
        prefixes = [""]
        for options in words:
            prefixes = [f"{p} {o}".strip() for p in prefixes for o in options]
        found.update(prefixes)
    return found


def test_copilot_runs_exactly_what_claude_and_codex_run_without_asking():
    # one AI asking before a step another runs silently => the user stalls on a prompt they can't judge
    copilot = set(workspace.settings("copilot", HOME)["chat.tools.terminal.autoApprove"])
    claude = set(workspace.claude_commands())
    assert copilot == claude == codex_commands()
    assert "uv run app/jobs.py" in copilot and "git pull" in copilot
    assert not any(c.startswith(("git p" + "ush", "rm")) for c in copilot)


def test_claude_rules_read_as_commands_once_each():
    allow = ["Bash(uv run app/jobs.py *)", "PowerShell(uv run app/jobs.py *)", "Bash(git status*)", "WebFetch", "Read(~/Downloads/**)"]
    assert workspace.terminal_commands(allow) == ["uv run app/jobs.py", "git status"]


def test_written_only_when_changed(tmp_path):
    # every write reloads the open window's settings
    path = tmp_path / ".vscode" / "settings.json"
    assert workspace.write("claude", path, set_up=False) is True
    text = path.read_text(encoding="utf-8")
    assert text.startswith("//") and "app/workspace.py" in text.splitlines()[0]
    assert load(text) == workspace.settings("claude")
    stamp = path.stat().st_mtime_ns
    assert workspace.write("claude", path, set_up=False) is False and path.stat().st_mtime_ns == stamp
    assert workspace.write("copilot", path, HOME, set_up=False) is True
    assert load(path.read_text(encoding="utf-8"))["chat.disableAIFeatures"] is False


def test_settings_file_generated_not_tracked():
    # tracked + edited per user => dirty checkout, `git pull --ff-only` in update fails
    if not (cfg.ROOT / ".git").exists():
        return
    git = ["git", "-C", str(cfg.ROOT)]
    tracked = subprocess.run([*git, "ls-files", ".vscode"], capture_output=True, text=True).stdout
    assert tracked.strip() == ""
    assert subprocess.run([*git, "check-ignore", "-q", ".vscode/settings.json"]).returncode == 0


def test_start_here_leaves_the_file_list_once_set_up(tmp_path, monkeypatch):
    # "type set me up" stayed in the file list for good, weeks after setup
    path, search = tmp_path / ".vscode" / "settings.json", tmp_path / "Search settings.yml"
    monkeypatch.setenv("JOBS_CONFIG", str(search))
    workspace.write("claude", path)
    assert "START HERE.md" not in load(path.read_text(encoding="utf-8"))["files.exclude"]
    search.write_text("{}\n", encoding="utf-8")
    assert workspace.write("claude", path) is True
    assert load(path.read_text(encoding="utf-8"))["files.exclude"]["START HERE.md"] is True


def test_resume_and_settings_files_read_as_documents():
    # line numbers, folding arrows, lightbulbs made Resume details.yml look like a code file
    for ai in ("claude", "copilot"):
        settings = workspace.settings(ai, HOME)
        for lang in ("[yaml]", "[markdown]"):
            block = settings[lang]
            assert block["editor.lineNumbers"] == "off" and block["editor.folding"] is False
            assert block["editor.glyphMargin"] is False and block["editor.wordWrap"] == "on"
        assert settings["terminal.integrated.hideOnStartup"] == "always"
        # schema's red underline + hover are the point of the YAML checker: never switched off
        flat = {k: v for block in (settings, settings["[yaml]"], settings["[markdown]"]) for k, v in block.items()}
        assert not any(k.startswith(("problems.", "editor.hover", "explorer.decorations", "workbench.editor.decorations"))
                       or k.endswith(".decorations.enabled") for k in flat)
        assert settings["yaml.validate"] is True


def test_setup_saving_search_settings_hides_start_here_in_the_open_window(tmp_path, monkeypatch, capsys):
    # START HERE stayed listed until the next launch after setup saved search settings
    import jobs
    import launch
    search = tmp_path / "My Settings" / "Search settings.yml"
    search.parent.mkdir()
    search.write_text((cfg.PROFILES / "example.yml").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv("JOBS_CONFIG", str(search))
    monkeypatch.setattr(cfg, "ROOT", tmp_path)
    monkeypatch.setattr(launch, "chosen_ai", lambda: "claude")
    jobs.check_settings()
    written = load((tmp_path / ".vscode" / "settings.json").read_text(encoding="utf-8"))
    assert written["files.exclude"]["START HERE.md"] is True
    assert written == workspace.settings("claude", set_up=True)  # the launcher's own file: no other key moves
    assert capsys.readouterr().out.startswith("ok: ")


# light / dark picked => the window stays that way, whatever the computer's look
def test_look_fixes_the_theme_and_auto_follows_the_computer():
    for ai in ("claude", "copilot"):
        dark, light, auto = (workspace.settings(ai, HOME, look=w) for w in ("dark", "light", "auto"))
        assert dark["window.autoDetectColorScheme"] is False and dark["workbench.colorTheme"] == "Dark Modern"
        assert light["window.autoDetectColorScheme"] is False and light["workbench.colorTheme"] == "Light Modern"
        assert auto["window.autoDetectColorScheme"] is True and "workbench.colorTheme" not in auto
        # brand colors for both themes stay; high contrast left to the computer
        for s in (dark, light, auto):
            assert s["workbench.colorCustomizations"] == auto["workbench.colorCustomizations"]
            assert "window.autoDetectHighContrast" not in s


# a missing, empty or garbled choice must not break the window: it just follows the computer
def test_missing_or_garbage_look_is_auto(tmp_path):
    path = tmp_path / "look"
    assert look.current(path) == "auto"
    for text in ("", "purple\n", "\x00\x01"):
        path.write_text(text, encoding="utf-8")
        assert look.current(path) == "auto"
    path.write_bytes(b"\xff\xfe")
    assert look.current(path) == "auto"
    assert workspace.settings("claude", look="purple")["window.autoDetectColorScheme"] is True


# "dark mode" in the chat must switch the open window at once, and survive the next launch
def test_look_command_round_trip(tmp_path, monkeypatch, capsys):
    import launch
    path = tmp_path / ".vscode" / "settings.json"
    monkeypatch.setattr(launch, "chosen_ai", lambda: "claude")
    monkeypatch.setattr(launch, "write_workspace", lambda ai: workspace.write(ai, path, set_up=False))
    for args, said, auto, theme in ((["dark"], "Look: dark. Switched.", False, "Dark Modern"),
                                    ([], "Look: dark.", False, "Dark Modern"),
                                    (["light"], "Look: light. Switched.", False, "Light Modern"),
                                    (["auto"], "Look: match my computer. Switched.", True, None)):
        monkeypatch.setattr("sys.argv", ["look", *args])
        look.main()
        assert capsys.readouterr().out.strip() == said
        written = load(path.read_text(encoding="utf-8"))
        assert written["window.autoDetectColorScheme"] is auto and written.get("workbench.colorTheme") == theme
    monkeypatch.setattr("sys.argv", ["look", "purple"])
    with pytest.raises(SystemExit):
        look.main()
    assert look.current() == "auto"
