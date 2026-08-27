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
    skill_md = src / "SKILL.md"
    if not skill_md.is_file():
        raise FileNotFoundError(f"bundled skill missing: {skill_md}")
    dest = agents_skills_dir(root) / SKILL_NAME
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / "SKILL.md"
    actions: list[str] = []
    if target.exists() and not force:
        actions.append(f"skip {target.relative_to(root).as_posix()}（已存在，--force 覆盖）")
    else:
        shutil.copy2(skill_md, target)
        actions.append(f"wrote {target.relative_to(root).as_posix()}")
        for extra in src.iterdir():
            if extra.name == "SKILL.md" or extra.name.startswith("."):
                continue
            out = dest / extra.name
            if extra.is_file():
                shutil.copy2(extra, out)
            elif extra.is_dir():
                if out.exists() and force:
                    shutil.rmtree(out)
                if not out.exists():
                    shutil.copytree(extra, out)
    actions.extend(ensure_claude_skills_alias(root))
    return actions
