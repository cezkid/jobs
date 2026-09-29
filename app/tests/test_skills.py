import re

import cfg
import jobs

SKILL_DIRS = [cfg.ROOT / ".claude" / "skills", cfg.ROOT / ".agents" / "skills"]
BODIES = cfg.APP / "skills"
COMMAND = re.compile(r"uv run app/jobs\.py ([\w-]+)")


def names() -> list[str]:
    return sorted(p.stem for p in BODIES.glob("*.md"))


def test_every_body_has_one_identical_stub_per_ai():
    for name in names():
        stubs = [(d / name / "SKILL.md").read_text(encoding="utf-8") for d in SKILL_DIRS]
        assert stubs[0] == stubs[1], name
        assert f"name: {name}\n" in stubs[0]
        assert f"`app/skills/{name}.md`" in stubs[0]


def test_no_stub_without_body():
    for d in SKILL_DIRS:
        assert sorted(p.name for p in d.iterdir()) == names()


def test_commands_named_in_instructions_exist():
    docs = [*BODIES.glob("*.md"), cfg.ROOT / "AGENTS.md", cfg.ROOT / "START HERE.md"]
    used = {m for p in docs for m in COMMAND.findall(p.read_text(encoding="utf-8"))}
    assert used <= jobs.COMMANDS.keys()


def test_questions_asked_one_at_a_time():
    # several questions at once show as tabs with Submit greyed until all are answered; users stalled
    docs = [cfg.ROOT / "AGENTS.md", BODIES / "job-setup.md"]
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        assert "ONE question" in text and "batch of 4" not in text.lower()


def test_status_is_asked_not_remembered():
    # users never type 'I applied to Ramp' unasked: apply ends w/ the question, chat start asks one job
    apply = (BODIES / "job-apply.md").read_text(encoding="utf-8")
    assert apply.count("Did you send it?") >= 3 and "status set 12 applied" in apply
    agents = (cfg.ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "uv run app/jobs.py status ask" in agents and "ONE clickable question" in agents


def test_report_defect_finds_git_and_gh_right_after_winget_install():
    # AI shell calls inherit VS Code's launch PATH: registry change after launch invisible to every call
    # (measured 2026-09-28: user env var set via registry absent from next PowerShell call)
    text = (BODIES / "report-defect.md").read_text(encoding="utf-8")
    installs = re.findall(r"winget install [^`]+", text)
    assert installs and all("--scope user" in i for i in installs)
    assert "$env:Path = [Environment]::GetEnvironmentVariable('Path', 'User')" in text


def test_every_allowed_command_runs_without_asking_in_powershell_too():
    # Windows w/o Git => Claude runs commands in PowerShell; Bash(...) rules never match there
    # (measured 2026-09-28: `uv run app/jobs.py check-settings` denied until PowerShell twin added)
    import json
    allow = json.loads((cfg.ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))["permissions"]["allow"]
    bash = {r.removeprefix("Bash(") for r in allow if r.startswith("Bash(")}
    powershell = {r.removeprefix("PowerShell(") for r in allow if r.startswith("PowerShell(")}
    assert bash == powershell
