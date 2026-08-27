"""Classify paths: source code vs key docs."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path


def _norm(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def matches(rel: str, globs: tuple[str, ...]) -> bool:
    path = _norm(rel)
    name = Path(path).name
    for g in globs:
        g = g.replace("\\", "/")
        if fnmatch(path, g) or fnmatch(name, g):
            return True
        if g.endswith("/**") and (path.startswith(g[:-3]) or path.startswith(g[:-2])):
            return True
    return False


SOURCE = (
    "src/**",
    "packages/**",
    "lib/**",
    "app/**",
    "tests/**",
    "*.py",
    "*.ts",
    "*.tsx",
    "*.js",
    "*.go",
    "*.rs",
    "*.java",
)

KEY_DOC_ROOT = ("CHANGELOG.md", "CLAUDE.md", "AGENTS.md", "REVIEW.md")
KEY_SDLC_NAMES = ("intent.md", "spec.md", "plan.md")


def is_key_doc(rel: str) -> bool:
    path = _norm(rel)
    name = Path(path).name
    if name in KEY_DOC_ROOT and "/" not in path:
        return True
    if name in KEY_SDLC_NAMES and "docs/sdlc/changes/" in path:
        return True
    return False


def is_source(rel: str) -> bool:
    if is_key_doc(rel):
        return False
    return matches(rel, SOURCE)
