"""Directory mailbox: one file per message under .workspace/inbox."""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


INBOX = "inbox"
SEEN = "seen"


class PipeError(RuntimeError):
    pass


def workspace_dir(root: Path) -> Path:
    return root / ".workspace"


def inbox_dir(root: Path) -> Path:
    return workspace_dir(root) / INBOX


def seen_dir(root: Path) -> Path:
    return workspace_dir(root) / SEEN


def send(root: Path, text: str) -> Path:
    inbox = inbox_dir(root)
    inbox.mkdir(parents=True, exist_ok=True)
    body = text if text.endswith("\n") else text + "\n"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    name = f"{stamp}-{os.getpid()}-{uuid.uuid4().hex[:8]}.txt"
    tmp = inbox / f".{name}.tmp"
    dest = inbox / name
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(dest)
    return dest


def pending(root: Path) -> list[Path]:
    inbox = inbox_dir(root)
    if not inbox.is_dir():
        return []
    return sorted(
        p for p in inbox.iterdir() if p.is_file() and not p.name.startswith(".")
    )


def consume_one(path: Path, root: Path) -> str:
    seen = seen_dir(root)
    seen.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8")
    dest = seen / path.name
    if dest.exists():
        dest = seen / f"{path.stem}-{os.getpid()}{path.suffix}"
    path.replace(dest)
    return text


def listen(
    root: Path,
    *,
    timeout: float | None = None,
    once: bool = False,
    poll: float = 0.2,
    emit=None,
) -> int:
    """Print new inbox files to stdout and move them to seen/. Return count."""
    write = emit if emit is not None else _emit
    deadline = None if timeout is None else time.monotonic() + timeout
    count = 0
    while True:
        files = pending(root)
        for path in files:
            text = consume_one(path, root)
            write(text if text.endswith("\n") else text + "\n")
            count += 1
            if once:
                return count
        if timeout == 0:
            return count
        if deadline is not None and time.monotonic() >= deadline:
            return count
        time.sleep(poll)


def _emit(text: str) -> None:
    print(text, end="", flush=True)
