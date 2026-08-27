"""Current Windows Terminal window only: infer panes from the process tree."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass

SHELL_NAMES = {
    "pwsh.exe",
    "powershell.exe",
    "cmd.exe",
    "bash.exe",
    "wsl.exe",
}
SKIP_RUNNING = {"conhost.exe", "openconsole.exe"}


@dataclass(frozen=True)
class Proc:
    pid: int
    ppid: int
    name: str
    cmdline: str = ""
    created: str = ""


def snapshot_processes() -> list[Proc]:
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "Get-CimInstance Win32_Process | "
                "Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate | "
                "ConvertTo-Json -Compress"
            ),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return []
    data = json.loads(proc.stdout)
    if isinstance(data, dict):
        data = [data]
    out: list[Proc] = []
    for row in data:
        try:
            pid = int(row.get("ProcessId") or 0)
            ppid = int(row.get("ParentProcessId") or 0)
        except (TypeError, ValueError):
            continue
        name = str(row.get("Name") or "")
        if not pid or not name:
            continue
        out.append(
            Proc(
                pid=pid,
                ppid=ppid,
                name=name,
                cmdline=str(row.get("CommandLine") or ""),
                created=str(row.get("CreationDate") or ""),
            )
        )
    return out


def terminal_pid(procs: Sequence[Proc], self_pid: int) -> int | None:
    by_pid = {p.pid: p for p in procs}
    pid = self_pid
    seen: set[int] = set()
    while pid and pid not in seen:
        seen.add(pid)
        p = by_pid.get(pid)
        if p is None:
            return None
        if p.name.lower() == "windowsterminal.exe":
            return p.pid
        pid = p.ppid
    return None


def window_panes(
    procs: Sequence[Proc], *, term_pid: int, self_pid: int
) -> list[dict]:
    kids = [p for p in procs if p.ppid == term_pid]
    cons = sorted(
        (p for p in kids if p.name.lower() == "openconsole.exe"),
        key=lambda p: (p.created, p.pid),
    )
    shells = sorted(
        (p for p in kids if p.name.lower() in SHELL_NAMES),
        key=lambda p: (p.created, p.pid),
    )
    children: dict[int, list[Proc]] = {}
    for p in procs:
        children.setdefault(p.ppid, []).append(p)

    current_shell = _shell_containing(self_pid, shells, procs)
    n = max(len(cons), len(shells))
    panes: list[dict] = []
    for i in range(n):
        shell = shells[i] if i < len(shells) else None
        con = cons[i] if i < len(cons) else None
        running = []
        if shell is not None:
            for d in _descendants(shell.pid, children):
                if d.name.lower() in SKIP_RUNNING:
                    continue
                running.append(d.name)
        panes.append(
            {
                "id": str(i),
                "current": bool(shell and shell.pid == current_shell),
                "shell_pid": shell.pid if shell else None,
                "shell": shell.name if shell else None,
                "openconsole_pid": con.pid if con else None,
                "running": running,
            }
        )
    return panes


def _shell_containing(
    self_pid: int, shells: Sequence[Proc], procs: Sequence[Proc]
) -> int | None:
    by_pid = {p.pid: p for p in procs}
    shell_ids = {s.pid for s in shells}
    pid = self_pid
    seen: set[int] = set()
    while pid and pid not in seen:
        seen.add(pid)
        if pid in shell_ids:
            return pid
        p = by_pid.get(pid)
        if p is None:
            return None
        pid = p.ppid
    return None


def _descendants(root: int, children: dict[int, list[Proc]]) -> list[Proc]:
    found: list[Proc] = []
    stack = [root]
    seen = {root}
    while stack:
        pid = stack.pop()
        for c in children.get(pid, []):
            if c.pid in seen:
                continue
            seen.add(c.pid)
            found.append(c)
            stack.append(c.pid)
    return found


def kill_pid(pid: int) -> None:
    subprocess.run(
        ["taskkill", "/PID", str(pid)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
    )


Killer = Callable[[int], None]
