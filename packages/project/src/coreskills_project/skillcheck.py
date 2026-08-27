"""Validate project-level SKILL.md against the Agent Skills spec."""

from __future__ import annotations

import re
from pathlib import Path

from .problems import Problem, error, warning
from .skills_layout import iter_skill_mds

MAX_NAME = 64
MAX_DESC = 1024
MAX_COMPAT = 500
MAX_BODY_LINES = 500
ALLOWED = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
}
NAME_OK = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def check_skills(root: Path) -> list[Problem]:
    """Only scan existing project-level skills. No 'please add a skill' hints."""
    problems: list[Problem] = []
    for md in iter_skill_mds(root, project_level=True):
        problems.extend(_check_one(root, md))
    return problems


def _check_one(root: Path, path: Path) -> list[Problem]:
    rel = path.relative_to(root).as_posix()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [error("skill", f"{rel} 无法读取: {exc}")]
    if not text.startswith("---"):
        return [error("skill", f"{rel} 缺 YAML frontmatter（agentskills 规范）")]
    parts = text.split("---", 2)
    if len(parts) < 3:
        return [error("skill", f"{rel} frontmatter 未闭合")]
    fm = parse_frontmatter(parts[1])
    body = parts[2]
    problems: list[Problem] = []
    problems.extend(_check_name(rel, path.parent.name, fm.get("name")))
    problems.extend(_check_description(rel, fm.get("description")))
    compat = fm.get("compatibility")
    if compat is not None and len(compat) > MAX_COMPAT:
        problems.append(
            error("skill", f"{rel} compatibility 超过 {MAX_COMPAT} 字符")
        )
    extra = [k for k in fm if k not in ALLOWED and k != "metadata"]
    # metadata nested keys are flattened as metadata.x — skip
    extra = [k for k in extra if not k.startswith("metadata.")]
    if extra:
        problems.append(
            warning("skill", f"{rel} 非规范字段: {', '.join(extra)}")
        )
    if body.count("\n") + 1 > MAX_BODY_LINES:
        problems.append(
            warning("skill", f"{rel} 正文超过 {MAX_BODY_LINES} 行（规范建议拆 references/）")
        )
    return problems


def parse_frontmatter(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
        if m and not line.startswith((" ", "\t")):
            if current is not None:
                fields[current] = _fold(buf)
            current = m.group(1)
            rest = m.group(2).strip()
            buf = [] if rest in {">", ">-", "|", "|-", "|+", ">+"} else [rest]
            continue
        if current is not None:
            buf.append(line.strip() if line.startswith((" ", "\t")) else line)
    if current is not None:
        fields[current] = _fold(buf)
    return fields


def _fold(buf: list[str]) -> str:
    return " ".join(p.strip("\"'") for p in buf if p.strip()).strip()


def _check_name(rel: str, dirname: str, name: str | None) -> list[Problem]:
    if not name:
        return [error("skill", f"{rel} frontmatter 缺 name")]
    problems: list[Problem] = []
    if len(name) > MAX_NAME:
        problems.append(error("skill", f"{rel} name 超过 {MAX_NAME} 字符"))
    if not NAME_OK.fullmatch(name):
        problems.append(
            error(
                "skill",
                f"{rel} name '{name}' 须为小写字母/数字/连字符，且不头尾连字符、无 --",
            )
        )
    if dirname != name:
        problems.append(
            error("skill", f"{rel} 目录名 '{dirname}' 必须与 name '{name}' 一致")
        )
    return problems


def _check_description(rel: str, desc: str | None) -> list[Problem]:
    if not desc:
        return [error("skill", f"{rel} frontmatter 缺 description（做什么 + 何时用）")]
    if len(desc) > MAX_DESC:
        return [error("skill", f"{rel} description 超过 {MAX_DESC} 字符")]
    return []
