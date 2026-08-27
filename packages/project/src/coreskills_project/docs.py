"""Document health: SDLC chain, AGENTS/CLAUDE coexist, spec-check existing skills."""

from __future__ import annotations

from pathlib import Path

from .problems import Problem, error, warning
from .skillcheck import check_skills


def check_docs(root: Path) -> list[Problem]:
    problems: list[Problem] = []
    problems.extend(_check_sdlc_chain(root))
    problems.extend(_check_coexist(root))
    problems.extend(check_skills(root))
    return problems


def _check_sdlc_chain(root: Path) -> list[Problem]:
    changes = root / "docs" / "sdlc" / "changes"
    if not changes.is_dir():
        return []
    problems: list[Problem] = []
    for folder in sorted(p for p in changes.iterdir() if p.is_dir()):
        names = {p.name for p in folder.iterdir() if p.is_file()}
        rel = folder.relative_to(root).as_posix()
        if "spec.md" in names and "intent.md" not in names:
            problems.append(error("docs", f"{rel} 有 spec.md 但缺 intent.md（SDLC 链）"))
        if "plan.md" in names and "spec.md" not in names:
            problems.append(error("docs", f"{rel} 有 plan.md 但缺 spec.md（SDLC 链）"))
        if "plan.md" in names and "intent.md" not in names:
            problems.append(error("docs", f"{rel} 有 plan.md 但缺 intent.md（SDLC 链）"))
    return problems


def _check_coexist(root: Path) -> list[Problem]:
    agents = root / "AGENTS.md"
    claude = None
    for rel in ("CLAUDE.md", ".claude/CLAUDE.md"):
        if (root / rel).is_file():
            claude = root / rel
            break
    if not agents.exists() or claude is None:
        return []
    ctext = claude.read_text(encoding="utf-8", errors="replace")
    if "@AGENTS.md" not in ctext and "AGENTS.md" not in ctext:
        return [
            warning(
                "docs",
                f"{claude.relative_to(root).as_posix()} 未引用 AGENTS.md；"
                "两文件并存时应 @AGENTS.md，避免双份漂移",
            )
        ]
    return []

