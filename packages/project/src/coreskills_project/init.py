"""Install the bundled `project` skill into a repo (generic + Claude dirs)."""

from __future__ import annotations

import shutil
from pathlib import Path

from .skills_layout import agents_skills_dir, ensure_claude_skills_alias

SKILL_NAME = "project"


def bundled_skill_dir() -> Path:
    return Path(__file__).resolve().parent / "bundled_skills" / SKILL_NAME


def init_project(root: Path, *, force: bool = False) -> list[str]:
    src = bundled_skill_dir()
    if not (src / "SKILL.md").is_file():
        raise FileNotFoundError(f"bundled skill missing: {src / 'SKILL.md'}")
    dest = agents_skills_dir(root) / SKILL_NAME
    actions = _copy_tree(src, dest, root, force=force)
    actions.extend(ensure_claude_skills_alias(root))
    return actions


def _copy_tree(src: Path, dest: Path, root: Path, *, force: bool) -> list[str]:
    dest.mkdir(parents=True, exist_ok=True)
    actions: list[str] = []
    for item in sorted(src.iterdir()):
        if item.name.startswith("."):
            continue
        out = dest / item.name
        if item.is_dir():
            actions.extend(_copy_tree(item, out, root, force=force))
            continue
        rel = _rel(root, out)
        if out.exists() and not force:
            actions.append(f"skip {rel}（已存在，--force 覆盖）")
            continue
        shutil.copy2(item, out)
        actions.append(f"wrote {rel}")
    return actions


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)
