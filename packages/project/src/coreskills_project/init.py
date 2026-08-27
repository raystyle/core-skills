"""Install the bundled `project` skill into a repo (generic + Claude dirs)."""

from __future__ import annotations

import shutil
from pathlib import Path

from .skills_layout import skill_install_dirs

SKILL_NAME = "project"


def bundled_skill_dir() -> Path:
    return Path(__file__).resolve().parent / "bundled_skills" / SKILL_NAME


def init_project(root: Path, *, force: bool = False) -> list[str]:
    src = bundled_skill_dir()
    if not (src / "SKILL.md").is_file():
        raise FileNotFoundError(f"bundled skill missing: {src / 'SKILL.md'}")
    actions: list[str] = []
    for base in skill_install_dirs(root):
        dest = base / SKILL_NAME
        rel = _rel(root, dest)
        if dest.exists() and not force:
            actions.append(f"skip {rel}（已存在，--force 覆盖）")
            continue
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        actions.append(f"wrote {rel}")
    return actions


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)
