"""Unified pane primitives over wt and herdr."""

from __future__ import annotations

import base64
import json
import os
import shlex
import shutil
from collections.abc import Sequence
from pathlib import Path

from .detect import DetectResult, detect
from .run import RunResult, Runner, run as default_run
from .wt_terms import close_term, inspect_panes, read_pane as uia_read_pane
from .wt_window import (
    Killer,
    Proc,
    kill_pid,
    list_host_windows,
    pick_current_window,
    siblings_in_current_window,
    snapshot_processes,
    terminal_pid,
    window_panes,
)

SPLIT_RIGHT = {"right", "v", "vertical"}
SPLIT_DOWN = {"down", "h", "horizontal"}
FOCUS_DIRS = {"left", "right", "up", "down"}
# microsoft/terminal AppCommandlineArgs.cpp focusDirectionMap
WT_MOVE_FOCUS = FOCUS_DIRS | {"previous", "first", "nextInOrder", "previousInOrder"}
# Same file: _buildParser subcommands. There is no close-pane.
WT_SUBCOMMANDS = (
    "new-tab",
    "nt",
    "split-pane",
    "sp",
    "focus-tab",
    "ft",
    "move-focus",
    "mf",
    "move-pane",
    "mp",
    "swap-pane",
    "focus-pane",
    "fp",
    "x-save",
)


class MuxError(RuntimeError):
    pass


def normalize_split(direction: str) -> str:
    d = direction.lower().strip()
    if d in SPLIT_RIGHT:
        return "right"
    if d in SPLIT_DOWN:
        return "down"
    raise MuxError("split 只用 right/down（或 v/h）；left/up 用于 pane focus")


def require_mux(info: DetectResult | None = None) -> DetectResult:
    info = info if info is not None else detect()
    if not info.inside or info.mux not in {"wt", "herdr"}:
        raise MuxError(
            f"当前不在 wt/herdr 里（os={info.os} expected={info.expected} mux={info.mux!r}）"
        )
    return info


def _bin(info: DetectResult) -> str:
    if info.mux == "wt":
        return info.bin or shutil.which("wt") or shutil.which("wt.exe") or "wt"
    return info.bin or shutil.which("herdr") or "herdr"


def _exec(runner: Runner | None, argv: Sequence[str]) -> RunResult:
    fn = runner or default_run
    return fn(argv)


def _check(result: RunResult, *, what: str) -> RunResult:
    if result.code != 0:
        err = (result.stderr or result.stdout or "").strip() or f"exit {result.code}"
        raise MuxError(f"{what} 失败: {err}")
    return result


def split_pane(
    direction: str,
    *,
    cwd: Path | None = None,
    title: str | None = None,
    cmd: str | None = None,
    size: float | None = None,
    info: DetectResult | None = None,
    runner: Runner | None = None,
) -> dict:
    info = require_mux(info)
    side = normalize_split(direction)
    cwd_s = str(cwd.resolve()) if cwd is not None else str(Path.cwd())
    if info.mux == "wt":
        return _split_wt(side, cwd=cwd_s, title=title, cmd=cmd, size=size, info=info, runner=runner)
    return _split_herdr(side, cwd=cwd_s, title=title, cmd=cmd, size=size, info=info, runner=runner)


def count_panes(*, info: DetectResult | None = None, snapshot: dict | None = None) -> dict:
    info = require_mux(info)
    if snapshot is not None:
        return {
            "mux": info.mux,
            "count": snapshot.get("count", len(snapshot.get("panes") or [])),
            "hwnd": snapshot.get("hwnd"),
            "title": snapshot.get("title"),
            "panes": snapshot.get("panes") or [],
        }
    if info.mux != "wt":
        listed = list_panes(info=info)
        panes = listed.get("panes") or []
        return {"mux": "herdr", "count": len(panes), "panes": panes}
    try:
        data = inspect_panes()
    except RuntimeError as exc:
        raise MuxError(str(exc)) from exc
    if data.get("error"):
        raise MuxError(str(data["error"]))
    return {
        "mux": "wt",
        "count": int(data.get("count") or 0),
        "hwnd": data.get("hwnd"),
        "title": data.get("title"),
        "panes": [
            {
                "id": p.get("id"),
                "exited": p.get("exited"),
                "focus": p.get("focus"),
                "preview": p.get("preview"),
            }
            for p in (data.get("panes") or [])
        ],
    }


def read_pane_content(
    pane_id: int, *, info: DetectResult | None = None, snapshot: dict | None = None
) -> dict:
    info = require_mux(info)
    if snapshot is not None:
        panes = snapshot.get("panes") or []
        if pane_id < 0 or pane_id >= len(panes):
            raise MuxError(f"本窗口没有窗格 {pane_id}")
        p = panes[pane_id]
        return {"mux": info.mux, "id": pane_id, "text": p.get("text") or p.get("preview") or ""}
    if info.mux != "wt":
        raise MuxError("herdr pane read 尚未接到这条原语")
    try:
        data = uia_read_pane(pane_id)
    except RuntimeError as exc:
        raise MuxError(str(exc)) from exc
    data["mux"] = "wt"
    return data


def list_panes(
    *,
    info: DetectResult | None = None,
    runner: Runner | None = None,
    procs: list[Proc] | None = None,
    self_pid: int | None = None,
    host_windows: list[dict] | None = None,
) -> dict:
    info = require_mux(info)
    if info.mux == "wt":
        return _list_wt(
            info, procs=procs, self_pid=self_pid, host_windows=host_windows
        )
    result = _check(_exec(runner, [_bin(info), "pane", "list"]), what="herdr pane list")
    panes = _parse_herdr_list(result.stdout)
    return {"mux": "herdr", "session": info.session, "panes": panes}


def focus_pane(
    target: str, *, info: DetectResult | None = None, runner: Runner | None = None
) -> dict:
    info = require_mux(info)
    t = target.strip()
    if info.mux == "wt":
        if t.isdigit():
            _check(
                _exec(runner, [_bin(info), "-w", "0", "focus-pane", "-t", t]),
                what="wt focus-pane",
            )
            return {"mux": "wt", "focused": t, "via": "focus-pane"}
        d = t.lower()
        if d not in WT_MOVE_FOCUS:
            raise MuxError(
                "wt pane focus 接受方向（left/right/up/down/previous/first）或创建序号整数"
            )
        _check(
            _exec(runner, [_bin(info), "-w", "0", "move-focus", d]),
            what="wt move-focus",
        )
        return {"mux": "wt", "focused": d, "via": "move-focus"}
    d = t.lower()
    if d not in FOCUS_DIRS:
        raise MuxError("herdr pane focus 只接受方向：left/right/up/down")
    _check(
        _exec(runner, [_bin(info), "pane", "focus", "--direction", d, "--current"]),
        what="herdr pane focus",
    )
    return {"mux": "herdr", "focused": d}


def close_pane(
    target: str = "current",
    *,
    info: DetectResult | None = None,
    runner: Runner | None = None,
    procs: list[Proc] | None = None,
    self_pid: int | None = None,
    killer: Killer | None = None,
    host_windows: list[dict] | None = None,
) -> dict:
    info = require_mux(info)
    t = target.strip() or "current"
    if info.mux == "wt":
        if t.isdigit():
            try:
                data = close_term(int(t))
            except RuntimeError as exc:
                raise MuxError(str(exc)) from exc
            data["mux"] = "wt"
            return data
        return _close_wt(
            t,
            info=info,
            procs=procs,
            self_pid=self_pid,
            killer=killer,
            host_windows=host_windows,
        )
    if t.lower() == "current":
        t = info.pane or ""
        if not t:
            raise MuxError("herdr 关闭需要窗格 id（HERDR_PANE_ID 为空）")
    _check(_exec(runner, [_bin(info), "pane", "close", t]), what="herdr pane close")
    return {"mux": "herdr", "closed": t}


def _list_wt(
    info: DetectResult,
    *,
    procs: list[Proc] | None,
    self_pid: int | None,
    host_windows: list[dict] | None,
) -> dict:
    rows = procs if procs is not None else snapshot_processes()
    me = os.getpid() if self_pid is None else self_pid
    tid = terminal_pid(rows, me)
    wins = host_windows if host_windows is not None else (
        list_host_windows(tid) if tid else []
    )
    current = pick_current_window(wins, cwd=str(Path.cwd()))
    return {
        "mux": "wt",
        "session": info.session,
        "note": "WT_SESSION 是每格一条；多窗口共用一个 WindowsTerminal.exe。见 docs/research/wt-windows.md",
        "process_pid": tid,
        "windows": wins,
        "current_window_panes": (current or {}).get("panes"),
        "process_tree_all_windows": (
            window_panes(rows, term_pid=tid, self_pid=me) if tid else []
        ),
        "focus": "left/right/up/down|previous|first|<n>（相对当前窗口）",
        "close": "others：关掉当前窗口里其它格（UIA 格数 + 创建时间最近的壳）",
    }


def _close_wt(
    target: str,
    *,
    info: DetectResult,
    procs: list[Proc] | None,
    self_pid: int | None,
    killer: Killer | None,
    host_windows: list[dict] | None = None,
) -> dict:
    if target.lower() not in {"others", "other"}:
        raise MuxError("wt 请用 pane close others（只关当前窗口其它格）")
    rows = procs if procs is not None else snapshot_processes()
    me = os.getpid() if self_pid is None else self_pid
    tid = terminal_pid(rows, me)
    if tid is None:
        raise MuxError("找不到当前 Windows Terminal 进程")
    wins = host_windows if host_windows is not None else list_host_windows(tid)
    panes = window_panes(rows, term_pid=tid, self_pid=me)
    try:
        chosen = siblings_in_current_window(panes, wins)
    except RuntimeError as exc:
        raise MuxError(str(exc)) from exc
    kill = killer or kill_pid
    closed: list[dict] = []
    for p in chosen:
        kill(int(p["shell_pid"]))
        closed.append(
            {
                "shell_pid": p["shell_pid"],
                "running": p.get("running") or [],
            }
        )
    return {
        "mux": "wt",
        "scope": "current-window",
        "closed": closed,
        "session": info.session,
    }


def _split_wt(
    side: str,
    *,
    cwd: str,
    title: str | None,
    cmd: str | None,
    size: float | None,
    info: DetectResult,
    runner: Runner | None,
) -> dict:
    flag = "-V" if side == "right" else "-H"
    argv = [_bin(info), "-w", "0", "split-pane", flag, "--startingDirectory", cwd]
    if title:
        argv.extend(["--title", title, "--suppressApplicationTitle"])
    if size is not None:
        argv.extend(["--size", str(size)])
    if cmd:
        argv.extend(_wt_spawn_argv(cmd))
    _check(_exec(runner, argv), what="wt split-pane")
    return {"mux": "wt", "direction": side, "cwd": cwd, "title": title, "cmd": cmd}


def _wt_spawn_argv(cmd: str) -> list[str]:
    """Argv for the new pane. WT splits on unescaped ';' (BuildCommands)."""
    if ";" not in cmd:
        return _cmd_tokens(cmd, posix=False)
    shell = shutil.which("pwsh") or shutil.which("powershell") or "pwsh"
    blob = base64.b64encode(cmd.encode("utf-16-le")).decode("ascii")
    return [shell, "-NoProfile", "-EncodedCommand", blob]


def _split_herdr(
    side: str,
    *,
    cwd: str,
    title: str | None,
    cmd: str | None,
    size: float | None,
    info: DetectResult,
    runner: Runner | None,
) -> dict:
    argv = [
        _bin(info),
        "pane",
        "split",
        "--current",
        "--direction",
        side,
        "--cwd",
        cwd,
        "--no-focus",
    ]
    if size is not None:
        argv.extend(["--ratio", str(size)])
    result = _check(_exec(runner, argv), what="herdr pane split")
    pane_id = _parse_herdr_new_pane(result.stdout)
    if title and pane_id:
        _exec(runner, [_bin(info), "pane", "rename", pane_id, title])
    if cmd and pane_id:
        _check(
            _exec(runner, [_bin(info), "pane", "run", pane_id, cmd]),
            what="herdr pane run",
        )
    return {
        "mux": "herdr",
        "direction": side,
        "cwd": cwd,
        "title": title,
        "cmd": cmd,
        "pane": pane_id,
    }


def _cmd_tokens(cmd: str, *, posix: bool) -> list[str]:
    return shlex.split(cmd, posix=posix)


def _parse_herdr_new_pane(stdout: str) -> str | None:
    text = stdout.strip()
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    result = data.get("result") if "result" in data else data
    if not isinstance(result, dict):
        return None
    pane = result.get("pane")
    if isinstance(pane, dict) and pane.get("pane_id"):
        return str(pane["pane_id"])
    if result.get("pane_id"):
        return str(result["pane_id"])
    return None


def _parse_herdr_list(stdout: str) -> list[dict]:
    text = stdout.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return [{"raw": text}]
    if isinstance(data, list):
        return [_pane_item(x) for x in data]
    if isinstance(data, dict):
        result = data.get("result", data)
        if isinstance(result, dict):
            panes = result.get("panes")
            if isinstance(panes, list):
                return [_pane_item(x) for x in panes]
        if isinstance(result, list):
            return [_pane_item(x) for x in result]
    return [{"raw": text}]


def _pane_item(item: object) -> dict:
    if isinstance(item, dict):
        pid = item.get("pane_id") or item.get("id")
        out = {"id": str(pid) if pid else None}
        for key in ("label", "cwd", "focused", "agent_status"):
            if key in item:
                out[key] = item[key]
        if out["id"] is None:
            return dict(item)
        return out
    return {"id": str(item)}
