"""Project skills live in .agents/skills (cross-tool). Claude gets an alias."""

from __future__ import annotations

import os
from pathlib import Path


def agents_skills_dir(root: Path) -> Path:
    return root / ".agents" / "skills"


def claude_skills_dir(root: Path) -> Path:
    return root / ".claude" / "skills"


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


def claude_alias_ok(root: Path) -> bool:
    src = agents_skills_dir(root)
    dst = claude_skills_dir(root)
    if not src.is_dir() or not dst.exists():
        return False
    try:
        return src.resolve() == dst.resolve()
    except OSError:
        return False


def ensure_claude_skills_alias(root: Path) -> list[str]:
    """Point .claude/skills at .agents/skills (relative symlink, else junction)."""
    src = agents_skills_dir(root)
    dst = claude_skills_dir(root)
    src.mkdir(parents=True, exist_ok=True)
    dst.parent.mkdir(parents=True, exist_ok=True)

    if claude_alias_ok(root):
        return [".claude/skills 已指向 .agents/skills"]

    if dst.exists() and not dst.is_symlink():
        leftover = [p for p in dst.rglob("*") if p.is_file()]
        if leftover:
            return [
                "跳过 Claude 别名：.claude/skills 仍是独立目录，"
                "请把 skill 迁到 .agents/skills 后再跑 hooks install"
            ]
        _rmtree(dst)

    if dst.is_symlink() or dst.is_junction():
        dst.unlink()

    rel = os.path.relpath(src, dst.parent)
    try:
        os.symlink(rel, dst, target_is_directory=True)
        return [f"linked .claude/skills -> {rel}（Claude 发现路径）"]
    except OSError:
        pass

    # Windows: junction needs an absolute target
    import subprocess

    if dst.exists():
        try:
            dst.unlink()
        except OSError:
            _rmtree(dst)
    proc = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(dst), str(src.resolve())],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode == 0:
        return ["junction .claude/skills -> .agents/skills（Claude 发现路径）"]
    return [f"未能创建 Claude 别名: {(proc.stderr or proc.stdout).strip()}"]


def _rmtree(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    for child in path.iterdir():
        _rmtree(child)
    path.rmdir()
