from __future__ import annotations

from dataclasses import dataclass

ERR = "error"
WARN = "warning"


@dataclass(frozen=True)
class Problem:
    level: str
    check: str
    msg: str


def error(check: str, msg: str) -> Problem:
    return Problem(ERR, check, msg)


def warning(check: str, msg: str) -> Problem:
    return Problem(WARN, check, msg)
