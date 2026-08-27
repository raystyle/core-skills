from __future__ import annotations

from pathlib import Path

from coreskills_project.cli import main
from coreskills_project.docs import check_docs
from coreskills_project.structure import check_structure

GITIGNORE = """\
.codex/
settings.local.json
CLAUDE.local.md
.env
*.pem
*.key
.venv/
__pycache__/
node_modules/
"""

CLAUDE = """\
@AGENTS.md

# Claude Code

## Commands
x

## Conventions
x

## Architecture
x

## Things Claude gets wrong
x

## Verifying your work
x
"""


def skeleton(root: Path, *, skill: bool = False) -> None:
    (root / "AGENTS.md").write_text("# demo\n\n硬规则。\n", encoding="utf-8")
    (root / "CLAUDE.md").write_text(CLAUDE, encoding="utf-8")
    (root / "REVIEW.md").write_text("# Review\n\n## Passes\n- Bugs\n", encoding="utf-8")
    (root / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    templates = root / "docs" / "sdlc" / "templates"
    templates.mkdir(parents=True)
    for name in ("intent.md", "spec.md", "plan.md"):
        (templates / name).write_text(f"# {name}\n", encoding="utf-8")
    (root / "docs" / "sdlc" / "changes").mkdir(parents=True, exist_ok=True)
    if skill:
        skill_dir = root / ".agents" / "skills" / "review"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: review\ndescription: Review changes before merge.\n---\n\n# review\n",
            encoding="utf-8",
        )


def test_empty_dir_requires_sdlc_and_agents(tmp_path: Path) -> None:
    problems = check_structure(tmp_path)
    assert any("CLAUDE.md" in p.msg for p in problems)
    assert any("REVIEW.md" in p.msg for p in problems)
    assert any("AGENTS.md" in p.msg for p in problems)


def test_claude_missing_sdlc_headings(tmp_path: Path) -> None:
    skeleton(tmp_path)
    (tmp_path / "CLAUDE.md").write_text(
        "@AGENTS.md\n\n# Claude Code\n\n## Commands\n\nx\n",
        encoding="utf-8",
    )
    problems = check_structure(tmp_path)
    assert any("缺 SDLC 标题" in p.msg for p in problems)


def test_claude_bridge_only_is_error(tmp_path: Path) -> None:
    skeleton(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
    problems = check_structure(tmp_path)
    assert any("只有 @AGENTS.md" in p.msg or "缺 SDLC 标题" in p.msg for p in problems)


def test_full_skeleton_structure_ok(tmp_path: Path) -> None:
    skeleton(tmp_path)
    assert check_structure(tmp_path) == []


def test_spec_without_intent_breaks_chain(tmp_path: Path) -> None:
    skeleton(tmp_path)
    change = tmp_path / "docs" / "sdlc" / "changes" / "demo"
    change.mkdir(parents=True)
    (change / "spec.md").write_text("# spec\n", encoding="utf-8")
    problems = check_docs(tmp_path)
    assert any("缺 intent.md" in p.msg for p in problems)


def test_claude_must_point_at_agents(tmp_path: Path) -> None:
    skeleton(tmp_path)
    (tmp_path / "CLAUDE.md").write_text(
        "# Claude\n\n## Commands\n\n## Conventions\n\n## Architecture\n\n"
        "## Things Claude gets wrong\n\n## Verifying your work\n",
        encoding="utf-8",
    )
    problems = check_docs(tmp_path)
    assert any("未引用 AGENTS.md" in p.msg for p in problems)


def test_no_skill_is_not_a_finding(tmp_path: Path) -> None:
    skeleton(tmp_path)
    assert not any("skill" in p.check or "SKILL" in p.msg for p in check_docs(tmp_path))


def test_skill_needs_description(tmp_path: Path) -> None:
    skeleton(tmp_path, skill=True)
    skill = tmp_path / ".agents" / "skills" / "review" / "SKILL.md"
    skill.write_text("---\nname: review\n---\n\n# x\n", encoding="utf-8")
    problems = check_docs(tmp_path)
    assert any("description" in p.msg for p in problems)


def test_skill_name_must_match_dir(tmp_path: Path) -> None:
    skeleton(tmp_path, skill=True)
    skill = tmp_path / ".agents" / "skills" / "review" / "SKILL.md"
    skill.write_text(
        "---\nname: other\ndescription: do review when asked.\n---\n\n# x\n",
        encoding="utf-8",
    )
    problems = check_docs(tmp_path)
    assert any("目录名" in p.msg for p in problems)


def test_skill_ok(tmp_path: Path) -> None:
    skeleton(tmp_path, skill=True)
    assert [p for p in check_docs(tmp_path) if p.level == "error"] == []


def test_cli_ok(tmp_path: Path) -> None:
    skeleton(tmp_path)
    assert main(["check", str(tmp_path)]) == 0


def test_init_installs_agents_and_claude_alias(tmp_path: Path) -> None:
    assert main(["init", str(tmp_path)]) == 0
    skill = tmp_path / ".agents" / "skills" / "project" / "SKILL.md"
    assert skill.is_file()
    text = skill.read_text(encoding="utf-8")
    assert "name: project" in text
    from coreskills_project.skills_layout import claude_alias_ok

    assert claude_alias_ok(tmp_path)
    problems = check_docs(tmp_path)
    assert not any(p.check == "skill" and p.level == "error" for p in problems)
