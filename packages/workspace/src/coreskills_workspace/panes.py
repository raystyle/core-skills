"""Unified pane primitives over wt and herdr."""

from __future__ import annotations

import base64
import json
import os
import shutil
import time
import uuid
from collections.abc import Callable, Sequence
from pathlib import Path

from .detect import DetectResult, detect
from .run import RunResult, Runner, run as default_run
from .wt_terms import (
    close_term,
    inspect_panes,
    read_pane as uia_read_pane,
    resize_term,
    send_term,
)
from .wt_window import (
    Killer,
    Proc,
    force_foreground,
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
# PATH 名；claude-code 只是别名。未知名字也走 shutil.which（其它智能体）。
AGENT_ALIASES = {
    "claude": "claude",
    "claude-code": "claude",
    "codex": "codex",
    "kimi": "kimi",
    "grok": "grok",
    "pi": "pi",
    "opencode": "opencode",
    "gemini": "gemini",
    "cursor": "cursor",
}
KEY_ALIASES = {
    "return": "enter",
    "escape": "esc",
    "bs": "backspace",
    "del": "delete",
    "pgup": "pageup",
    "pgdn": "pagedown",
    "spacebar": "space",
    "上": "up",
    "下": "down",
    "左": "left",
    "右": "right",
}
VK = {
    "enter": 0x0D,
    "tab": 0x09,
    "esc": 0x1B,
    "space": 0x20,
    "backspace": 0x08,
    "delete": 0x2E,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "minus": 0xBD,
    "plus": 0xBB,
}
VK.update({f"f{i}": 0x6F + i for i in range(1, 13)})
MOD_VK = {"ctrl": 0x11, "alt": 0x12, "shift": 0x10}
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


def _exec(
    runner: Runner | None,
    argv: Sequence[str],
    *,
    env: dict[str, str] | None = None,
) -> RunResult:
    if runner is not None:
        return runner(argv)
    if env is not None:
        return default_run(argv, env=env)
    return default_run(argv)


def _check(result: RunResult, *, what: str) -> RunResult:
    if result.code != 0:
        err = (result.stderr or result.stdout or "").strip() or f"exit {result.code}"
        raise MuxError(f"{what} 失败: {err}")
    return result


def _ps_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def normalize_key(token: str) -> str:
    raw = token.strip()
    if not raw:
        raise MuxError("空按键")
    low = raw.lower().replace("c-", "ctrl+").replace("control+", "ctrl+")
    if "+" in low:
        parts = [p for p in low.split("+") if p]
        mods: list[str] = []
        key = None
        order = ("ctrl", "alt", "shift")
        for part in parts:
            part = KEY_ALIASES.get(part, part)
            if part in MOD_VK:
                if part not in mods:
                    mods.append(part)
            else:
                key = KEY_ALIASES.get(part, part)
        if key is None:
            raise MuxError(f"无法解析按键 {token!r}")
        mods.sort(key=lambda m: order.index(m) if m in order else 9)
        return "+".join([*mods, key])
    return KEY_ALIASES.get(low, low)


def key_chords(names: Sequence[str]) -> tuple[list[str], list[list[int]]]:
    canon = [normalize_key(n) for n in names]
    chords: list[list[int]] = []
    for item in canon:
        parts = item.split("+")
        vks: list[int] = []
        for mod in parts[:-1]:
            if mod not in MOD_VK:
                raise MuxError(f"未知修饰键 {mod!r}")
            vks.append(MOD_VK[mod])
        last = parts[-1]
        if last in VK:
            vks.append(VK[last])
        elif len(last) == 1 and last.isascii():
            if last.isalpha():
                vks.append(ord(last.upper()))
            elif last.isdigit():
                vks.append(ord(last))
            else:
                raise MuxError(f"未知按键 {item!r}；可打印字符请用 pane text")
        else:
            raise MuxError(f"未知按键 {item!r}")
        chords.append(vks)
    return canon, chords


def resolve_agent(
    name: str, *, which: Callable[[str], str | None] | None = None
) -> tuple[str, str]:
    raw = name.lower().strip()
    if not raw:
        raise MuxError("空的 --agent")
    kind = AGENT_ALIASES.get(raw, raw)
    find = which or shutil.which
    exe = find(kind)
    if not exe:
        raise MuxError(f"找不到智能体 {kind!r}（不在 PATH）")
    return kind, exe


def split_pane(
    direction: str,
    *,
    cwd: Path | None = None,
    title: str | None = None,
    cmd: str | None = None,
    agent: str | None = None,
    size: float | None = None,
    info: DetectResult | None = None,
    runner: Runner | None = None,
    which: Callable[[str], str | None] | None = None,
) -> dict:
    info = require_mux(info)
    side = normalize_split(direction)
    cwd_s = str(cwd.resolve()) if cwd is not None else str(Path.cwd())
    extra_env: dict[str, str] = {}
    kind: str | None = None
    if size is not None and not (0.01 <= float(size) <= 0.99):
        raise MuxError("--size 范围 0.01–0.99")
    if agent and cmd:
        raise MuxError("--agent 和 --cmd 不能一起用")
    if agent:
        kind, exe = resolve_agent(agent, which=which)
        extra_env["WORKSPACE_AGENT"] = kind
        title = title or kind
        cmd = f"& {_ps_quote(exe)}" if info.mux == "wt" else kind
    if info.mux == "wt":
        return _split_wt(
            side,
            cwd=cwd_s,
            title=title,
            cmd=cmd,
            size=size,
            extra_env=extra_env,
            agent=kind,
            info=info,
            runner=runner,
        )
    return _split_herdr(
        side,
        cwd=cwd_s,
        title=title,
        cmd=cmd,
        size=size,
        extra_env=extra_env,
        agent=kind,
        info=info,
        runner=runner,
    )


def swap_pane(
    direction: str, *, info: DetectResult | None = None, runner: Runner | None = None
) -> dict:
    info = require_mux(info)
    d = direction.lower().strip()
    if info.mux == "wt":
        if d not in WT_MOVE_FOCUS:
            raise MuxError(
                "wt pane swap 接受 left/right/up/down/previous/first/nextInOrder/previousInOrder"
            )
        if runner is None:
            _focus_our_window()
        _check(
            _exec(runner, [_bin(info), "-w", "0", "swap-pane", d]),
            what="wt swap-pane",
        )
        return {"mux": "wt", "swapped": d, "via": "swap-pane"}
    if d not in FOCUS_DIRS:
        raise MuxError("herdr pane swap 只接受方向：left/right/up/down")
    _check(
        _exec(
            runner,
            [_bin(info), "pane", "swap", "--direction", d, "--current"],
        ),
        what="herdr pane swap",
    )
    return {"mux": "herdr", "swapped": d}


def resize_pane(
    direction: str,
    *,
    amount: float | None = None,
    info: DetectResult | None = None,
    runner: Runner | None = None,
    send_keys: Callable[[str, int], dict] | None = None,
) -> dict:
    info = require_mux(info)
    d = direction.lower().strip()
    if d not in FOCUS_DIRS:
        raise MuxError("resize 只用 left/right/up/down")
    if info.mux == "wt":
        # AppCommandlineArgs.cpp 没有 resize-pane。默认键位 Alt+Shift+方向。
        steps = 5 if amount is None else max(1, int(amount))
        if send_keys is not None:
            data = send_keys(d, steps)
        else:
            listed = count_panes(info=info)
            self_id = next(
                (int(p["id"]) for p in (listed.get("panes") or []) if p.get("current")),
                None,
            )
            if self_id is None:
                raise MuxError("无法确定当前格，拒绝 resize")
            data = resize_term(d, steps, pane_id=self_id)
        data["mux"] = "wt"
        data["resized"] = d
        data["steps"] = steps
        data["via"] = "alt+shift+arrow"
        return data
    amt = 0.1 if amount is None else amount
    _check(
        _exec(
            runner,
            [
                _bin(info),
                "pane",
                "resize",
                "--direction",
                d,
                "--amount",
                str(amt),
                "--current",
            ],
        ),
        what="herdr pane resize",
    )
    return {"mux": "herdr", "resized": d, "amount": amt}


def resolve_pane(target: str, records: list[dict]) -> int:
    t = str(target).strip()
    if t.isdigit():
        idx = int(t)
        if 0 <= idx < len(records):
            return idx
        raise MuxError(f"本窗口没有窗格 {t}（共 {len(records)} 格）")
    key = t.lower()
    hits = [
        r
        for r in records
        if str(r.get("pane_id") or "").lower().startswith(key)
        or str(r.get("wt_session") or "").lower().startswith(key)
        or str(r.get("id") or "").lower().startswith(key)
    ]
    if len(hits) == 1:
        return int(hits[0]["id"])
    raise MuxError(f"无法解析窗格 '{t}'")


def _tag_records(uia: dict, tree: list[dict]) -> list[dict]:
    """Tag UIA terms. Only the caller pane gets pane_id; do not zip foreign shells."""
    terms = uia.get("panes") or []
    mine = next((p for p in tree if p.get("current")), None)
    hint = "workspace pane"
    hits = [
        i
        for i, term in enumerate(terms)
        if hint in str(term.get("preview") or "") or hint in str(term.get("text") or "")
    ]
    self_idx: int | None
    if len(hits) == 1:
        self_idx = hits[0]
    elif mine is not None and len(terms) == 1:
        self_idx = 0
    else:
        self_idx = None
    records = []
    for i, term in enumerate(terms):
        is_self = self_idx is not None and i == self_idx
        shell = mine if is_self and mine else {}
        records.append(
            {
                "id": i,
                "pane_id": (shell.get("pane_id") or shell.get("wt_session"))
                if is_self
                else None,
                "wt_session": shell.get("wt_session") if is_self else None,
                "current": is_self,
                "running": (shell.get("running") or []) if is_self else [],
                "exited": term.get("exited"),
                "focus": term.get("focus"),
                "preview": term.get("preview"),
            }
        )
    return records


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
    rows = snapshot_processes()
    me = os.getpid()
    tid = terminal_pid(rows, me)
    tree = window_panes(rows, term_pid=tid, self_pid=me) if tid else []
    records = _tag_records(data, tree)
    return {
        "mux": "wt",
        "count": int(data.get("count") or 0),
        "hwnd": data.get("hwnd"),
        "title": data.get("title"),
        "current": os.environ.get("WT_SESSION"),
        "current_session": os.environ.get("WT_SESSION"),
        "panes": records,
    }


def read_pane_content(
    target: str | int,
    *,
    info: DetectResult | None = None,
    snapshot: dict | None = None,
) -> dict:
    info = require_mux(info)
    if snapshot is not None:
        panes = snapshot.get("panes") or []
        idx = resolve_pane(str(target), panes)
        p = panes[idx]
        return {
            "mux": info.mux,
            "id": idx,
            "pane_id": p.get("pane_id"),
            "text": p.get("text") or p.get("preview") or "",
        }
    if info.mux != "wt":
        raise MuxError("herdr pane read 尚未接到这条原语")
    listed = count_panes(info=info)
    idx = resolve_pane(str(target), listed.get("panes") or [])
    try:
        data = uia_read_pane(idx)
    except RuntimeError as exc:
        raise MuxError(str(exc)) from exc
    rec = (listed.get("panes") or [])[idx]
    data["mux"] = "wt"
    data["pane_id"] = rec.get("pane_id")
    data["wt_session"] = rec.get("wt_session")
    return data


def send_text_to_pane(
    target: str,
    text: str,
    *,
    info: DetectResult | None = None,
    runner: Runner | None = None,
    snapshot: dict | None = None,
    sender: Callable[..., dict] | None = None,
) -> dict:
    if text == "":
        raise MuxError("空文本")
    return _interact_pane(
        target,
        text=text,
        keys=[],
        info=info,
        runner=runner,
        snapshot=snapshot,
        sender=sender,
    )


def send_keys_to_pane(
    target: str,
    keys: Sequence[str],
    *,
    info: DetectResult | None = None,
    runner: Runner | None = None,
    snapshot: dict | None = None,
    sender: Callable[..., dict] | None = None,
) -> dict:
    if not keys:
        raise MuxError("给出至少一个按键，如 enter / ctrl+c / down")
    return _interact_pane(
        target,
        text=None,
        keys=list(keys),
        info=info,
        runner=runner,
        snapshot=snapshot,
        sender=sender,
    )


def _interact_pane(
    target: str,
    *,
    text: str | None,
    keys: list[str],
    info: DetectResult | None,
    runner: Runner | None,
    snapshot: dict | None,
    sender: Callable[..., dict] | None,
) -> dict:
    info = require_mux(info)
    canon, chords = key_chords(keys) if keys else ([], [])
    if info.mux != "wt":
        t = str(target).strip()
        if t.lower() in {"", "current"}:
            t = info.pane or ""
            if not t:
                raise MuxError("herdr 发键需要窗格 id（HERDR_PANE_ID 为空）")
        if info.pane and t == info.pane:
            raise MuxError("不能向当前窗格发键（会打进正在跑的命令）")
        if text is not None:
            _check(
                _exec(runner, [_bin(info), "pane", "send-text", t, text]),
                what="herdr pane send-text",
            )
        if canon:
            _check(
                _exec(runner, [_bin(info), "pane", "send-keys", t, *canon]),
                what="herdr pane send-keys",
            )
        return {
            "mux": "herdr",
            "target": t,
            "text": text,
            "keys": canon,
        }
    listed = count_panes(info=info, snapshot=snapshot)
    panes = listed.get("panes") or []
    idx = resolve_pane(str(target), panes)
    rec = panes[idx]
    if rec.get("current"):
        raise MuxError("不能向当前窗格发键（会打进正在跑的命令）")
    restore = next((int(p["id"]) for p in panes if p.get("current")), None)
    if sender is not None:
        data = sender(idx, text, chords, restore)
    else:
        try:
            data = send_term(idx, text=text, chords=chords, restore=restore)
        except RuntimeError as exc:
            raise MuxError(str(exc)) from exc
    data["mux"] = "wt"
    data["id"] = idx
    data["pane_id"] = rec.get("pane_id")
    data["text"] = text
    data["keys"] = canon
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
        if runner is None:
            _focus_our_window()
        if t.isdigit():
            _check(
                _exec(runner, [_bin(info), "-w", "0", "focus-pane", "-t", t]),
                what="wt focus-pane",
            )
            return {"mux": "wt", "focused": t, "via": "focus-pane"}
        d = t.lower()
        if d not in WT_MOVE_FOCUS:
            raise MuxError(
                "wt pane focus 接受方向（left/right/up/down/previous/first/"
                "nextInOrder/previousInOrder）或创建序号整数"
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
        if t.lower() == "current":
            raise MuxError("不能关当前窗格")
        if t.lower() in {"others", "other"}:
            return _close_wt(
                t,
                info=info,
                procs=procs,
                self_pid=self_pid,
                killer=killer,
                host_windows=host_windows,
            )
        listed = count_panes(info=info)
        panes = listed.get("panes") or []
        idx = resolve_pane(t, panes)
        rec = panes[idx]
        self_id = next((int(p["id"]) for p in panes if p.get("current")), None)
        if rec.get("current") or (self_id is not None and idx == self_id):
            raise MuxError("不能关当前窗格")
        try:
            data = close_term(idx, self_id=self_id)
        except RuntimeError as exc:
            raise MuxError(str(exc)) from exc
        data["mux"] = "wt"
        data["pane_id"] = rec.get("pane_id")
        return data
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
    extra_env: dict[str, str],
    agent: str | None,
    info: DetectResult,
    runner: Runner | None,
) -> dict:
    flag = "-V" if side == "right" else "-H"
    argv = [_bin(info), "-w", "0", "split-pane", flag, "--startingDirectory", cwd]
    if title:
        argv.extend(["--title", title, "--suppressApplicationTitle"])
    if size is not None:
        argv.extend(["--size", str(size)])
    pane_id = None
    if cmd:
        # commandline 存在时源码默认 inherit；显式写出，让 PATH / API key 跟过来。
        argv.append("--inheritEnvironment")
        spawn, pane_id = _wt_spawn_argv(cmd, extra_env=extra_env)
        argv.extend(spawn)
    if runner is None:
        _focus_our_window()
    _check(
        _exec(runner, argv, env=None if runner else _wt_client_env()),
        what="wt split-pane",
    )
    return {
        "mux": "wt",
        "direction": side,
        "cwd": cwd,
        "title": title,
        "cmd": cmd,
        "agent": agent,
        "pane": pane_id,
        "via": "pwsh EncodedCommand" if cmd else "profile",
    }


def _wt_client_env() -> dict[str, str]:
    """Env for the `wt` client so inheritEnvironment is not NO_COLOR/FORCE_COLOR=0."""
    env = {k: v for k, v in os.environ.items() if k.upper() not in {"NO_COLOR", "FORCE_COLOR"}}
    env["TERM"] = "xterm-256color"
    env["COLORTERM"] = "truecolor"
    env["FORCE_COLOR"] = "1"
    return env


def _focus_our_window() -> None:
    """`wt -w 0` is last-used window, not 'this pane's window'."""
    rows = snapshot_processes()
    tid = terminal_pid(rows, os.getpid())
    if not tid:
        return
    chosen = pick_current_window(list_host_windows(tid), cwd=str(Path.cwd()))
    hwnd = (chosen or {}).get("hwnd")
    if hwnd and force_foreground(int(hwnd)):
        time.sleep(0.15)


def _wt_spawn_argv(
    cmd: str, *, extra_env: dict[str, str] | None = None
) -> tuple[list[str], str]:
    """pwsh EncodedCommand：注入 WORKSPACE_*，避免 wt 把 `;` 切成下一条命令。"""
    pane_id = "p-" + uuid.uuid4().hex[:8]
    # inheritEnvironment 会把宿主的 NO_COLOR=1 / TERM=dumb 带进新格（Codex/Grok
    # 沙箱注入）。win-rmux 实测：必须 Remove-Item，置空无效。见 docs/research/pane-color.md
    assigns = [
        "Remove-Item Env:NO_COLOR,Env:FORCE_COLOR -ErrorAction SilentlyContinue",
        "$env:TERM='xterm-256color'",
        "$env:COLORTERM='truecolor'",
        "$env:FORCE_COLOR='1'",
        "$env:WORKSPACE_ENV='1'",
        f"$env:WORKSPACE_PANE_ID={_ps_quote(pane_id)}",
    ]
    for key, value in (extra_env or {}).items():
        assigns.append(f"$env:{key}={_ps_quote(value)}")
    wrapper = "; ".join(assigns) + "; " + cmd
    shell = shutil.which("pwsh") or shutil.which("powershell") or "pwsh"
    blob = base64.b64encode(wrapper.encode("utf-16-le")).decode("ascii")
    return [shell, "-NoProfile", "-EncodedCommand", blob], pane_id


def _split_herdr(
    side: str,
    *,
    cwd: str,
    title: str | None,
    cmd: str | None,
    size: float | None,
    extra_env: dict[str, str],
    agent: str | None,
    info: DetectResult,
    runner: Runner | None,
) -> dict:
    workspace_pane = "p-" + uuid.uuid4().hex[:8]
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
        "--env",
        "WORKSPACE_ENV=1",
        "--env",
        f"WORKSPACE_PANE_ID={workspace_pane}",
    ]
    for key, value in extra_env.items():
        argv.extend(["--env", f"{key}={value}"])
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
        "agent": agent,
        "pane": pane_id,
    }


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
