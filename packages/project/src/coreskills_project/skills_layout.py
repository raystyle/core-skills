"""Project skills live in both .agents/skills and .claude/skills (independent copies)."""

from __future__ import annotations

from pathlib import Path


def agents_skills_dir(root: Path) -> Path:
    return root / ".agents" / "skills"


def claude_skills_dir(root: Path) -> Path:
    return root / ".claude" / "skills"


def skill_install_dirs(root: Path) -> tuple[Path, Path]:
    """Generic discovery path, then Claude Code discovery path."""
    return agents_skills_dir(root), claude_skills_dir(root)


def iter_skill_mds(root: Path, *, project_level: bool = False) -> list[Path]:
    """Unique SKILL.md files. project_level: only .agents/skills and .claude/skills."""
    found: list[Path] = []
    seen: set[Path] = set()
    bases = [agents_skills_dir(root), claude_skills_dir(root)]
    if not project_level:
        bases.append(root / "skills")
    for base in bases:
        if not base.is_dir():
            continue
        for md in sorted(base.rglob("SKILL.md")):
            try:
                key = md.resolve()
            except OSError:
                key = md
            if key in seen:
                continue
            seen.add(key)
            found.append(md)
    return found
