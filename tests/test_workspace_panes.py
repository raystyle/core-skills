from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from coreskills_workspace.detect import DetectResult
from coreskills_workspace.panes import (
    MuxError,
    _tag_records,
    close_pane,
    count_panes,
    focus_pane,
    key_chords,
    list_panes,
    normalize_key,
    read_pane_content,
    resize_pane,
    resolve_agent,
    send_keys_to_pane,
    send_text_to_pane,
    split_pane,
    swap_pane,
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


def test_split_wt_default_cwd(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    calls: list[list[str]] = []

    def runner(argv):
        calls.append(list(argv))
        return RunResult(list(argv), 0, "", "")

    split_pane("right", info=WT, runner=runner)
    argv = calls[0]
    assert argv[:5] == ["wt", "-w", "0", "split-pane", "-V"]
    i = argv.index("--startingDirectory")
    assert Path(argv[i + 1]).resolve() == tmp_path.resolve()
    assert "-EncodedCommand" not in argv


def test_split_wt_agent_uses_pwsh_encoded(tmp_path: Path) -> None:
    calls: list[list[str]] = []
    claude = r"C:\Users\ray\.local\bin\claude.exe"

    def runner(argv):
        calls.append(list(argv))
        return RunResult(list(argv), 0, "", "")

    data = split_pane(
        "right",
        cwd=tmp_path,
        agent="claude",
        info=WT,
        runner=runner,
        which=lambda n: claude if n == "claude" else None,
    )
    argv = calls[0]
    assert "--startingDirectory" in argv
    assert argv[argv.index("--startingDirectory") + 1] == str(tmp_path.resolve())
    assert "--inheritEnvironment" in argv
    assert "claude" in argv  # --title claude
    assert "-EncodedCommand" in argv
    assert ";" not in "".join(argv)
    blob = argv[argv.index("-EncodedCommand") + 1]
    decoded = base64.b64decode(blob).decode("utf-16-le")
    assert "WORKSPACE_ENV=" in decoded
    assert "WORKSPACE_PANE_ID=" in decoded
    assert "WORKSPACE_AGENT=" in decoded
    assert "Remove-Item Env:NO_COLOR" in decoded
    assert "FORCE_COLOR" in decoded
    assert "xterm-256color" in decoded
    assert "truecolor" in decoded
    assert claude in decoded
    assert decoded.strip().endswith(f"& '{claude}'") or f"& '{claude}'" in decoded
    assert data["agent"] == "claude"
    assert data["cwd"] == str(tmp_path.resolve())
    assert data["via"] == "pwsh EncodedCommand"


def test_split_agent_and_cmd_exclusive() -> None:
    with pytest.raises(MuxError, match="不能一起用"):
        split_pane("right", agent="claude", cmd="echo hi", info=WT, runner=lambda a: RunResult(list(a), 0, "", ""))


def test_resolve_agent_missing() -> None:
    with pytest.raises(MuxError, match="不在 PATH"):
        resolve_agent("no-such-agent-xyz", which=lambda n: None)


def test_split_herdr_agent() -> None:
    payload = json.dumps({"result": {"pane": {"pane_id": "w1:p3"}}})
    calls: list[list[str]] = []

    def runner(argv):
        calls.append(list(argv))
        if "split" in argv:
            return RunResult(list(argv), 0, payload, "")
        return RunResult(list(argv), 0, "", "")

    data = split_pane(
        "down",
        cwd=Path("/tmp/p"),
        agent="kimi",
        info=HERDR,
        runner=runner,
        which=lambda n: "/usr/bin/kimi" if n == "kimi" else None,
    )
    split_argv = calls[0]
    assert "--cwd" in split_argv
    assert "WORKSPACE_AGENT=kimi" in split_argv
    run_argv = next(c for c in calls if "run" in c)
    assert run_argv[-1] == "kimi"
    assert data["agent"] == "kimi"
    assert data["pane"] == "w1:p3"


def test_swap_wt() -> None:
    calls: list[list[str]] = []

    def runner(argv):
        calls.append(list(argv))
        return RunResult(list(argv), 0, "", "")

    data = swap_pane("right", info=WT, runner=runner)
    assert calls[0] == ["wt", "-w", "0", "swap-pane", "right"]
    assert data["via"] == "swap-pane"


def test_swap_herdr() -> None:
    calls: list[list[str]] = []

    def runner(argv):
        calls.append(list(argv))
        return RunResult(list(argv), 0, "", "")

    swap_pane("left", info=HERDR, runner=runner)
    assert calls[0] == ["herdr", "pane", "swap", "--direction", "left", "--current"]


def test_resize_herdr() -> None:
    calls: list[list[str]] = []

    def runner(argv):
        calls.append(list(argv))
        return RunResult(list(argv), 0, "", "")

    data = resize_pane("right", amount=0.2, info=HERDR, runner=runner)
    assert calls[0] == [
        "herdr",
        "pane",
        "resize",
        "--direction",
        "right",
        "--amount",
        "0.2",
        "--current",
    ]
    assert data["amount"] == 0.2


def test_resize_wt_sends_keys() -> None:
    sent: list[tuple[str, int]] = []

    def send(direction: str, steps: int) -> dict:
        sent.append((direction, steps))
        return {"keys": f"alt+shift+{direction}", "steps": steps}

    data = resize_pane("left", info=WT, send_keys=send)
    assert sent == [("left", 5)]
    assert data["via"] == "alt+shift+arrow"


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
    here = Path.cwd().name
    wins = [
        {"hwnd": 1, "title": "independent", "tabs": 1, "panes": 1, "current": False},
        {"hwnd": 2, "title": f"{here} CLI", "tabs": 1, "panes": 2, "current": True},
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


def test_close_others_refuses_ambiguous_window() -> None:
    procs = [
        Proc(10, 1, "WindowsTerminal.exe"),
        Proc(21, 10, "pwsh.exe", created="1"),
        Proc(31, 10, "pwsh.exe", created="2"),
        Proc(99, 21, "python.exe"),
    ]
    wins = [
        {"hwnd": 1, "title": "other grok", "tabs": 1, "panes": 2, "current": True},
        {"hwnd": 2, "title": "unrelated", "tabs": 1, "panes": 1, "current": False},
    ]
    with pytest.raises(MuxError, match="无法确定当前窗口"):
        close_pane(
            "others",
            info=WT,
            procs=procs,
            self_pid=99,
            host_windows=wins,
            killer=lambda p: None,
        )


def test_tag_records_does_not_zip_foreign_shells() -> None:
    uia = {
        "panes": [
            {"id": 0, "preview": "workspace pane close", "exited": False, "focus": True},
            {"id": 1, "preview": "Claude Code", "exited": False, "focus": False},
        ]
    }
    tree = [
        {
            "current": True,
            "pane_id": "mine-session",
            "wt_session": "mine-session",
            "running": ["grok.exe"],
            "created": "2",
        },
        {
            "current": False,
            "pane_id": "foreign-session",
            "wt_session": "foreign-session",
            "running": ["grok.exe"],
            "created": "1",
            "shell_pid": 31,
        },
    ]
    rec = _tag_records(uia, tree)
    assert rec[0]["current"] is True
    assert rec[0]["pane_id"] == "mine-session"
    assert rec[1]["pane_id"] is None
    assert rec[1]["current"] is False


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


def test_close_refuses_current_even_by_pane_id(monkeypatch) -> None:
    snap = {
        "panes": [
            {"id": 0, "current": True, "pane_id": "64f0a21d-aaaa"},
            {"id": 1, "current": False, "pane_id": "p-c86fc8da"},
        ]
    }
    monkeypatch.setattr(
        "coreskills_workspace.panes.count_panes",
        lambda **k: {"mux": "wt", "count": 2, "panes": snap["panes"]},
    )
    with pytest.raises(MuxError, match="当前窗格"):
        close_pane("0", info=WT)
    with pytest.raises(MuxError, match="当前窗格"):
        close_pane("64f0a21d", info=WT)


def test_arrow_keys_for_menu_select() -> None:
    assert normalize_key("下") == "down"
    assert normalize_key("上") == "up"
    assert normalize_key("左") == "left"
    assert normalize_key("右") == "right"
    canon, chords = key_chords(["down", "up", "left", "right", "enter"])
    assert canon == ["down", "up", "left", "right", "enter"]
    assert chords == [[0x28], [0x26], [0x25], [0x27], [0x0D]]


def test_send_keys_wt_arrows_not_self() -> None:
    snap = {
        "panes": [
            {"id": 0, "current": True, "pane_id": "aaa"},
            {"id": 1, "current": False, "pane_id": "bbb"},
        ]
    }
    sent: list[tuple] = []

    def sender(idx, text, chords, restore):
        sent.append((idx, text, chords, restore))
        return {"ok": True}

    with pytest.raises(MuxError, match="当前窗格"):
        send_keys_to_pane("0", ["down"], info=WT, snapshot=snap, sender=sender)
    data = send_keys_to_pane("1", ["down", "enter"], info=WT, snapshot=snap, sender=sender)
    assert sent[0][0] == 1
    assert sent[0][2] == [[0x28], [0x0D]]
    assert sent[0][3] == 0
    assert data["keys"] == ["down", "enter"]
    assert data["pane_id"] == "bbb"


def test_send_text_and_keys_herdr() -> None:
    calls: list[list[str]] = []

    def runner(argv):
        calls.append(list(argv))
        return RunResult(list(argv), 0, "", "")

    send_text_to_pane("w1:p2", "hello", info=HERDR, runner=runner)
    send_keys_to_pane("w1:p2", ["down", "enter"], info=HERDR, runner=runner)
    assert calls[0] == ["herdr", "pane", "send-text", "w1:p2", "hello"]
    assert calls[1] == ["herdr", "pane", "send-keys", "w1:p2", "down", "enter"]
    with pytest.raises(MuxError, match="当前窗格"):
        send_keys_to_pane("w1:p1", ["enter"], info=HERDR, runner=runner)
