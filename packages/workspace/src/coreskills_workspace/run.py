"""Subprocess runner (injectable in tests)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from collections.abc import Callable, Sequence


@dataclass
class RunResult:
    argv: list[str]
    code: int
    stdout: str
    stderr: str


def run(argv: Sequence[str], *, timeout: float = 30) -> RunResult:
    proc = subprocess.run(
        list(argv),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return RunResult(list(argv), proc.returncode, proc.stdout, proc.stderr)


Runner = Callable[[Sequence[str]], RunResult]
