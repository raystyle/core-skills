"""Current Windows Terminal window only: infer panes from the process tree."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable, Sequence
from ctypes import (
    POINTER,
    Structure,
    byref,
    c_size_t,
    c_ubyte,
    c_ulong,
    c_void_p,
    sizeof,
    windll,
)
from ctypes import wintypes as w
from dataclasses import dataclass
from pathlib import Path

SHELL_NAMES = {
    "pwsh.exe",
    "powershell.exe",
    "cmd.exe",
    "bash.exe",
    "wsl.exe",
}
SKIP_RUNNING = {"conhost.exe", "openconsole.exe"}
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
OpenProcess = windll.kernel32.OpenProcess
OpenProcess.restype = w.HANDLE
ReadProcessMemory = windll.kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [
    w.HANDLE,
    w.LPCVOID,
    w.LPVOID,
    c_size_t,
    POINTER(c_size_t),
]
NtQueryInformationProcess = windll.ntdll.NtQueryInformationProcess
CloseHandle = windll.kernel32.CloseHandle


class _PBI(Structure):
    _fields_ = [
        ("ExitStatus", c_void_p),
        ("PebBaseAddress", c_void_p),
        ("AffinityMask", c_void_p),
        ("BasePriority", c_void_p),
        ("UniqueProcessId", c_void_p),
        ("InheritedFromUniqueProcessId", c_void_p),
    ]


def process_env(pid: int, keys: Sequence[str] | None = None) -> dict[str, str]:
    """Read selected env vars from another process (WT_SESSION ≈ HERDR_PANE_ID)."""
    wanted = set(
        keys
        or (
            "WT_SESSION",
            "WT_PROFILE_ID",
            "WORKSPACE_PANE_ID",
            "WORKSPACE_ENV",
            "HERDR_PANE_ID",
            "HERDR_ENV",
        )
    )
    handle = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not handle:
        return {}
    try:
        pbi = _PBI()
        ret = c_ulong()
        status = NtQueryInformationProcess(
            handle, 0, byref(pbi), sizeof(pbi), byref(ret)
        )
        if status != 0 or not pbi.PebBaseAddress:
            return {}
        peb = _read_mem(handle, pbi.PebBaseAddress, 0x40)
        if not peb:
            return {}
        params_addr = int.from_bytes(peb[0x20:0x28], "little")
        params = _read_mem(handle, params_addr, 0x200)
        if not params:
            return {}
        env_ptr = int.from_bytes(params[0x80:0x88], "little")
        raw = _read_mem(handle, env_ptr, 64 * 1024)
        if not raw:
            return {}
        text = raw.decode("utf-16le", "replace")
        found: dict[str, str] = {}
        for part in text.split("\x00"):
            if "=" not in part:
                continue
            key, val = part.split("=", 1)
            if key in wanted:
                found[key] = val
        return found
    finally:
        CloseHandle(handle)


def _read_mem(handle, addr: int, n: int) -> bytes | None:
    buf = (c_ubyte * n)()
    got = c_size_t()
    if not ReadProcessMemory(handle, c_void_p(addr), buf, n, byref(got)):
        return None
    return bytes(buf[: got.value])


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
                "Select-Object ProcessId,ParentProcessId,Name,CommandLine,"
                "@{n='CreationDate';e={ if ($_.CreationDate) { $_.CreationDate.ToString('yyyyMMddHHmmss') } else { '' } }} | "
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
        env: dict[str, str] = {}
        if shell is not None:
            for d in _descendants(shell.pid, children):
                if d.name.lower() in SKIP_RUNNING:
                    continue
                running.append(d.name)
            env = process_env(shell.pid)
        panes.append(
            {
                "id": str(i),
                "current": bool(shell and shell.pid == current_shell),
                "shell_pid": shell.pid if shell else None,
                "shell": shell.name if shell else None,
                "openconsole_pid": con.pid if con else None,
                "created": shell.created if shell else (con.created if con else ""),
                "running": running,
                "pane_id": env.get("WORKSPACE_PANE_ID") or env.get("WT_SESSION"),
                "wt_session": env.get("WT_SESSION"),
            }
        )
    return panes


def pick_current_window(
    host_windows: Sequence[dict], *, cwd: str | None = None
) -> dict | None:
    """Window this agent is in: title∋cwd name, else unique split window, else foreground."""
    wins = list(host_windows)
    if cwd:
        name = Path(cwd).name.lower()
        if name:
            hits = [w for w in wins if name in (w.get("title") or "").lower()]
            if len(hits) == 1:
                return hits[0]
    multi = [w for w in wins if int(w.get("panes") or 0) > 1]
    if len(multi) == 1:
        return multi[0]
    fg = [w for w in wins if w.get("current")]
    if fg:
        return fg[0]
    return None


def siblings_in_current_window(
    panes: Sequence[dict], host_windows: Sequence[dict]
) -> list[dict]:
    """Other shells in the current Cascadia window.

    Pane count comes from UIA. Sibling shells are the nearest-in-creation-time
    neighbors of the current shell (same WT process, not the current pane).
    """
    current_win = pick_current_window(host_windows, cwd=str(Path.cwd()))
    if not current_win:
        raise RuntimeError("无法确定当前 Cascadia 窗口")
    n_other = int(current_win.get("panes") or 0) - 1
    if n_other <= 0:
        raise RuntimeError("当前窗口没有其它窗格")
    mine = next((p for p in panes if p.get("current")), None)
    if not mine or not mine.get("shell_pid"):
        raise RuntimeError("找不到当前格的壳进程")
    others = [p for p in panes if not p.get("current") and p.get("shell_pid")]
    others.sort(key=lambda p: _created_dist(mine.get("created") or "", p.get("created") or ""))
    picked = others[:n_other]
    if len(picked) < n_other:
        raise RuntimeError("当前窗口其它格数量对不上进程树")
    return picked


def _created_dist(a: str, b: str) -> int:
    try:
        return abs(int(a[:14]) - int(b[:14]))
    except ValueError:
        return 10**18


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
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
    )


Killer = Callable[[int], None]

_UIA_WINDOWS_PS = r"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$src = @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class WtWins {
  public delegate bool Cb(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(Cb lp, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
}
'@
Add-Type -TypeDefinition $src
$wtPid = [uint32]$env:WT_PROBE_PID
$fg = [int64][WtWins]::GetForegroundWindow()
$wins = [System.Collections.Generic.List[object]]::new()
$cb = [WtWins+Cb]{
  param($h, $l)
  $p = 0
  [void][WtWins]::GetWindowThreadProcessId($h, [ref]$p)
  if ($p -ne $wtPid -or -not [WtWins]::IsWindowVisible($h)) { return $true }
  $c = New-Object System.Text.StringBuilder 256
  [void][WtWins]::GetClassName($h, $c, 256)
  if ($c.ToString() -ne 'CASCADIA_HOSTING_WINDOW_CLASS') { return $true }
  $t = New-Object System.Text.StringBuilder 512
  [void][WtWins]::GetWindowText($h, $t, 512)
  $el = [System.Windows.Automation.AutomationElement]::FromHandle($h)
  $tabs = 0; $panes = 0
  if ($el) {
    $all = $el.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
    foreach ($x in $all) {
      if ($x.Current.ControlType.ProgrammaticName -eq 'ControlType.TabItem') { $tabs++ }
      if ($x.Current.ClassName -eq 'TermControl') { $panes++ }
    }
  }
  $hwnd = [int64]$h
  $wins.Add([pscustomobject]@{
    hwnd = $hwnd
    title = $t.ToString()
    tabs = $tabs
    panes = $panes
    current = ($hwnd -eq $fg)
  })
  return $true
}
[void][WtWins]::EnumWindows($cb, [IntPtr]::Zero)
$wins | ConvertTo-Json -Compress
"""


def list_host_windows(term_pid: int) -> list[dict]:
    """Visible Cascadia windows of this WindowsTerminal.exe (one process, many windows)."""
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", _UIA_WINDOWS_PS],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        env={**os.environ, "WT_PROBE_PID": str(term_pid)},
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return []
    data = json.loads(proc.stdout)
    if isinstance(data, dict):
        data = [data]
    out = []
    for row in data:
        out.append(
            {
                "hwnd": int(row.get("hwnd") or 0),
                "title": str(row.get("title") or ""),
                "tabs": int(row.get("tabs") or 0),
                "panes": int(row.get("panes") or 0),
                "current": bool(row.get("current")),
            }
        )
    return out
