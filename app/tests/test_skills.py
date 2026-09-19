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
