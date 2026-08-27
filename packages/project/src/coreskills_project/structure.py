"""Structure: SDLC layer first, then this-repo extras."""

from __future__ import annotations

from pathlib import Path

from .problems import Problem, error, warning

CLAUDE_LINE_SOFT_LIMIT = 200

# Anthropic playbook CLAUDE.md sections
SDLC_CLAUDE_HEADINGS = (
    "Commands",
    "Conventions",
    "Architecture",
    "Things Claude gets wrong",
    "Verifying your work",
)

SDLC_TEMPLATES = (
    "docs/sdlc/templates/intent.md",
    "docs/sdlc/templates/spec.md",
    "docs/sdlc/templates/plan.md",
)

GITIGNORE_CLASSES = {
    "智能体配置": [".codex/", "settings.local.json"],
    "密钥凭据": [".env", "*.pem", "*.key"],
    "衍生垃圾": [".venv/", "__pycache__/", "node_modules/"],
}


def check_structure(root: Path) -> list[Problem]:
    problems: list[Problem] = []
    problems.extend(_check_sdlc(root))
    problems.extend(_check_ours(root))
    return problems


def _check_sdlc(root: Path) -> list[Problem]:
    problems: list[Problem] = []
    claude = _claude_md(root)
    if claude is None:
        problems.append(
            error("structure", "缺 CLAUDE.md（SDLC 常驻记忆：仓库根或 .claude/CLAUDE.md）")
        )
    else:
        text = claude.read_text(encoding="utf-8", errors="replace")
        stripped = text.strip()
        if not stripped:
            problems.append(error("structure", f"{_rel(root, claude)} 是空文件"))
        else:
            headings = {
                line[3:].strip()
                for line in stripped.splitlines()
                if line.startswith("## ")
            }
            missing = [h for h in SDLC_CLAUDE_HEADINGS if h not in headings]
            if missing:
                problems.append(
                    error(
                        "structure",
                        f"{_rel(root, claude)} 缺 SDLC 标题: {', '.join(missing)}",
                    )
                )
            if stripped.count("\n") + 1 > CLAUDE_LINE_SOFT_LIMIT:
                problems.append(
                    warning(
                        "structure",
                        f"{_rel(root, claude)} 超过 {CLAUDE_LINE_SOFT_LIMIT} 行；"
                        "通用说明应拆到 skill",
                    )
                )

    if not (root / "REVIEW.md").is_file():
        problems.append(error("structure", "缺 REVIEW.md（SDLC Deploy：PR 对照 intent/spec/plan）"))

    for rel in SDLC_TEMPLATES:
        if not (root / rel).is_file():
            problems.append(error("structure", f"缺 {rel}（SDLC 阶段产物模板）"))

    if not (root / "docs" / "sdlc" / "changes").is_dir():
        problems.append(
            error("structure", "缺 docs/sdlc/changes/（单次变更 intent/spec/plan 落点）")
        )
    return problems


def _check_ours(root: Path) -> list[Problem]:
    problems: list[Problem] = []
    agents = root / "AGENTS.md"
    if not agents.exists():
        problems.append(error("structure", "缺 AGENTS.md（本仓层：与 CLAUDE.md 并存）"))
    elif not agents.read_text(encoding="utf-8", errors="replace").strip():
        problems.append(error("structure", "AGENTS.md 是空文件"))

    claude = _claude_md(root)
    if claude is not None:
        text = claude.read_text(encoding="utf-8", errors="replace").strip()
        body = "\n".join(
            line
            for line in text.splitlines()
            if line.strip() and line.strip() != "@AGENTS.md"
        )
        if text and not body:
            problems.append(
                error(
                    "structure",
                    f"{_rel(root, claude)} 只有 @AGENTS.md 桥接，没有 Claude 自己的约定",
                )
            )

    problems.extend(_check_gitignore(root))
    return problems


def _check_gitignore(root: Path) -> list[Problem]:
    gi = root / ".gitignore"
    if not gi.exists():
        return [warning("structure", ".gitignore 不存在")]
    text = gi.read_text(encoding="utf-8", errors="replace")
    problems: list[Problem] = []
    for cls, patterns in GITIGNORE_CLASSES.items():
        missing = [p for p in patterns if p not in text]
        if missing:
            problems.append(
                error(
                    "structure",
                    f".gitignore 缺「{cls}」条目: {', '.join(missing)}",
                )
            )
    if "CLAUDE.local.md" not in text:
        problems.append(
            warning("structure", ".gitignore 建议忽略 CLAUDE.local.md（SDLC 个人偏好，不入库）")
        )
    return problems


def _claude_md(root: Path) -> Path | None:
    for rel in ("CLAUDE.md", ".claude/CLAUDE.md"):
        path = root / rel
        if path.is_file():
            return path
    return None


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)
