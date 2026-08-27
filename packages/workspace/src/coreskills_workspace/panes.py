"""Unified pane primitives over wt and herdr."""

from __future__ import annotations

import json
import shlex
import shutil
from collections.abc import Sequence
from pathlib import Path

from .detect import DetectResult, detect
from .run import RunResult, Runner, run as default_run

SPLIT_RIGHT = {"right", "v", "vertical"}
SPLIT_DOWN = {"down", "h", "horizontal"}
FOCUS_DIRS = {"left", "right", "up", "down"}


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


def list_panes(*, info: DetectResult | None = None, runner: Runner | None = None) -> dict:
    info = require_mux(info)
    if info.mux == "wt":
        return {
            "mux": "wt",
            "session": info.session,
            "panes": [{"id": "current", "note": "wt CLI 不能列出窗格 id"}],
            "focus": "left/right/up/down",
            "close": "current",
        }
    result = _check(_exec(runner, [_bin(info), "pane", "list"]), what="herdr pane list")
    panes = _parse_herdr_list(result.stdout)
    return {"mux": "herdr", "session": info.session, "panes": panes}


def focus_pane(
    target: str, *, info: DetectResult | None = None, runner: Runner | None = None
) -> dict:
    info = require_mux(info)
    d = target.lower().strip()
    if d not in FOCUS_DIRS:
        raise MuxError("pane focus 只接受方向：left/right/up/down")
    if info.mux == "wt":
        _check(
            _exec(runner, [_bin(info), "-w", "0", "move-focus", d]),
            what="wt move-focus",
        )
        return {"mux": "wt", "focused": d}
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
) -> dict:
    info = require_mux(info)
    t = target.strip() or "current"
    if info.mux == "wt":
        if t.lower() != "current":
            raise MuxError("wt 只能关闭当前聚焦窗格：workspace pane close current")
        _check(_exec(runner, [_bin(info), "-w", "0", "close-pane"]), what="wt close-pane")
        return {"mux": "wt", "closed": "current"}
    if t.lower() == "current":
        t = info.pane or ""
        if not t:
            raise MuxError("herdr 关闭需要窗格 id（HERDR_PANE_ID 为空）")
    _check(_exec(runner, [_bin(info), "pane", "close", t]), what="herdr pane close")
    return {"mux": "herdr", "closed": t}


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
        argv.extend(_cmd_tokens(cmd, posix=False))
    _check(_exec(runner, argv), what="wt split-pane")
    return {"mux": "wt", "direction": side, "cwd": cwd, "title": title, "cmd": cmd}


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
