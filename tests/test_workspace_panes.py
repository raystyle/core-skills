from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from coreskills_workspace.detect import DetectResult
from coreskills_workspace.panes import (
    MuxError,
    close_pane,
    count_panes,
    focus_pane,
    list_panes,
    read_pane_content,
    split_pane,
)
from coreskills_workspace.run import RunResult
from coreskills_workspace.wt_window import Proc, pick_current_window


WT = DetectResult(os="windows", expected="wt", mux="wt", inside=True, bin="wt")
HERDR = DetectResult(
    os="linux",
    expected="herdr",
    mux="herdr",
    inside=True,
    bin="herdr",
    pane="w1:p1",
)
NONE = DetectResult(os="windows", expected="wt", mux=None, inside=False)


def test_split_refuses_outside_mux() -> None:
    with pytest.raises(MuxError, match="不在 wt/herdr"):
        split_pane("right", info=NONE, runner=lambda a: RunResult(list(a), 0, "", ""))


def test_split_wt_vertical() -> None:
    calls: list[list[str]] = []

    def runner(argv):
        calls.append(list(argv))
        return RunResult(list(argv), 0, "", "")

    data = split_pane("v", cwd=Path("D:/repo"), title="logs", cmd="pwsh -NoProfile", info=WT, runner=runner)
    assert data["mux"] == "wt"
    assert data["direction"] == "right"
    argv = calls[0]
    assert argv[:5] == ["wt", "-w", "0", "split-pane", "-V"]
    assert "--startingDirectory" in argv
    assert "logs" in argv
    assert "-EncodedCommand" in argv


def test_split_wt_semicolon_uses_encoded_command() -> None:
    cmd = (
        'pwsh -NoProfile -Command "Write-Output \'workspace-live pane\'; '
        'Start-Sleep -Seconds 8"'
    )
    calls: list[list[str]] = []

    def runner(argv):
        calls.append(list(argv))
        return RunResult(list(argv), 0, "", "")

    split_pane("right", cwd=Path("D:/repo"), cmd=cmd, info=WT, runner=runner)
    argv = calls[0]
    assert ";" not in "".join(argv)
    assert "-EncodedCommand" in argv
    blob = argv[argv.index("-EncodedCommand") + 1]
    decoded = base64.b64decode(blob).decode("utf-16-le")
    assert "WORKSPACE_PANE_ID=" in decoded
    assert cmd in decoded


def test_split_herdr_down_parses_pane() -> None:
    payload = json.dumps({"result": {"pane": {"pane_id": "w1:p2"}}})

    def runner(argv):
        if "split" in argv:
            return RunResult(list(argv), 0, payload, "")
        return RunResult(list(argv), 0, "", "")

    data = split_pane("down", cwd=Path("/tmp/p"), info=HERDR, runner=runner)
    assert data["direction"] == "down"
    assert data["pane"] == "w1:p2"


def test_list_wt_windows_not_process_tree() -> None:
    procs = [
        Proc(10, 1, "WindowsTerminal.exe"),
        Proc(21, 10, "pwsh.exe", created="1"),
        Proc(22, 21, "grok.exe"),
        Proc(31, 10, "pwsh.exe", created="2"),
        Proc(99, 21, "python.exe"),
    ]
    wins = [
        {"hwnd": 1, "title": "independent grok", "tabs": 1, "panes": 1, "current": False},
        {"hwnd": 2, "title": "core-skills", "tabs": 1, "panes": 2, "current": True},
    ]
    data = list_panes(info=WT, procs=procs, self_pid=99, host_windows=wins)
    assert data["process_pid"] == 10
    assert data["current_window_panes"] == 2
    # even if UIA current flags are false, unique multi-pane window is used
    data2 = list_panes(
        info=WT,
        procs=procs,
        self_pid=99,
        host_windows=[
            {"hwnd": 1, "title": "independent grok", "tabs": 1, "panes": 1, "current": False},
            {"hwnd": 2, "title": "core-skills", "tabs": 1, "panes": 2, "current": False},
        ],
    )
    assert data2["current_window_panes"] == 2
    assert len(data["windows"]) == 2
    assert sum(w["panes"] for w in data["windows"]) == 3


def test_count_and_read_from_snapshot() -> None:
    snap = {
        "hwnd": 2,
        "title": "core-skills",
        "count": 2,
        "panes": [
            {"id": 0, "preview": "Claude Code", "text": "Claude Code\nexited", "exited": True},
            {"id": 1, "preview": "grok", "text": "hello grok", "exited": False},
        ],
    }
    counted = count_panes(info=WT, snapshot=snap)
    assert counted["count"] == 2
    read = read_pane_content(1, info=WT, snapshot=snap)
    assert "hello grok" in read["text"]
    with pytest.raises(MuxError, match="没有窗格 9"):
        read_pane_content(9, info=WT, snapshot=snap)
    snap["panes"][0]["id"] = 0
    snap["panes"][0]["pane_id"] = "64f0a21d-aaaa"
    snap["panes"][1]["id"] = 1
    snap["panes"][1]["pane_id"] = "975c447b-bbbb"
    by_id = read_pane_content("64f0a21d", info=WT, snapshot=snap)
    assert by_id["id"] == 0


def test_list_herdr() -> None:
    payload = json.dumps({"result": {"panes": [{"pane_id": "w1:p1", "focused": True}]}})

    def runner(argv):
        return RunResult(list(argv), 0, payload, "")

    data = list_panes(info=HERDR, runner=runner)
    assert data["panes"][0]["id"] == "w1:p1"


def test_focus_direction_wt() -> None:
    calls: list[list[str]] = []

    def runner(argv):
        calls.append(list(argv))
        return RunResult(list(argv), 0, "", "")

    data = focus_pane("left", info=WT, runner=runner)
    assert calls[0] == ["wt", "-w", "0", "move-focus", "left"]
    assert data["via"] == "move-focus"


def test_focus_wt_index() -> None:
    calls: list[list[str]] = []

    def runner(argv):
        calls.append(list(argv))
        return RunResult(list(argv), 0, "", "")

    data = focus_pane("1", info=WT, runner=runner)
    assert calls[0] == ["wt", "-w", "0", "focus-pane", "-t", "1"]
    assert data["via"] == "focus-pane"


def test_focus_rejects_herdr_pane_id() -> None:
    with pytest.raises(MuxError, match="方向"):
        focus_pane("w1:p2", info=HERDR, runner=lambda a: RunResult(list(a), 0, "", ""))


def test_close_wt_others_nearest_in_time_not_other_window() -> None:
    killed: list[int] = []
    procs = [
        Proc(10, 1, "WindowsTerminal.exe"),
        Proc(20, 10, "OpenConsole.exe", created="20260827095203000"),
        Proc(21, 10, "pwsh.exe", created="20260827095203000"),
        Proc(22, 21, "grok.exe"),
        Proc(30, 10, "OpenConsole.exe", created="20260827172456000"),
        Proc(31, 10, "pwsh.exe", created="20260827172456000"),
        Proc(32, 31, "claude.exe"),
        Proc(40, 10, "OpenConsole.exe", created="20260827172542000"),
        Proc(41, 10, "pwsh.exe", created="20260827172542000"),
        Proc(99, 41, "python.exe"),
    ]
    wins = [
        {"hwnd": 1, "title": "independent", "tabs": 1, "panes": 1, "current": False},
        {"hwnd": 2, "title": "here", "tabs": 1, "panes": 2, "current": True},
    ]
    data = close_pane(
        "others",
        info=WT,
        procs=procs,
        self_pid=99,
        killer=killed.append,
        host_windows=wins,
    )
    assert killed == [31]
    assert data["closed"][0]["running"] == ["claude.exe"]


def test_pick_window_by_cwd_not_foreground() -> None:
    wins = [
        {"hwnd": 1, "title": "qihoo-01 sing-box - grok", "tabs": 1, "panes": 1, "current": True},
        {"hwnd": 2, "title": "core-skills CLI - grok", "tabs": 1, "panes": 2, "current": False},
    ]
    w = pick_current_window(wins, cwd=r"D:\core-skills")
    assert w is not None
    assert w["hwnd"] == 2


def test_close_wt_others_none() -> None:
    procs = [
        Proc(10, 1, "WindowsTerminal.exe"),
        Proc(41, 10, "pwsh.exe", created="20260827172542000"),
        Proc(99, 41, "python.exe"),
    ]
    wins = [{"hwnd": 2, "title": "here", "tabs": 1, "panes": 1, "current": True}]
    with pytest.raises(MuxError, match="没有其它窗格"):
        close_pane(
            "others", info=WT, procs=procs, self_pid=99, host_windows=wins, killer=lambda p: None
        )


def test_close_herdr_id() -> None:
    calls: list[list[str]] = []

    def runner(argv):
        calls.append(list(argv))
        return RunResult(list(argv), 0, "", "")

    close_pane("w1:p2", info=HERDR, runner=runner)
    assert calls[0] == ["herdr", "pane", "close", "w1:p2"]
