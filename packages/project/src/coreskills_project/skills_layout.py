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


def is_link_dir(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        if path.is_junction():
            return True
    except OSError:
        return False
    return False


def dissolve_link(path: Path, root: Path) -> list[str]:
    """Drop a symlink/junction so a real directory can be created in its place."""
    if not is_link_dir(path):
        return []
    path.unlink()
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        rel = str(path)
    return [f"removed {rel}（原为别名，改为独立目录）"]
