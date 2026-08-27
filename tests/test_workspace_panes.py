from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from coreskills_workspace.detect import DetectResult
from coreskills_workspace.panes import MuxError, close_pane, focus_pane, list_panes, split_pane
from coreskills_workspace.run import RunResult


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
    assert "pwsh" in argv
    assert "-EncodedCommand" not in argv


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
    assert base64.b64decode(blob).decode("utf-16-le") == cmd


def test_split_herdr_down_parses_pane() -> None:
    payload = json.dumps({"result": {"pane": {"pane_id": "w1:p2"}}})

    def runner(argv):
        if "split" in argv:
            return RunResult(list(argv), 0, payload, "")
        return RunResult(list(argv), 0, "", "")

    data = split_pane("down", cwd=Path("/tmp/p"), info=HERDR, runner=runner)
    assert data["direction"] == "down"
    assert data["pane"] == "w1:p2"


def test_list_wt_has_no_native_ids() -> None:
    data = list_panes(info=WT, runner=lambda a: RunResult(list(a), 0, "", ""))
    assert data["mux"] == "wt"
    assert data["panes"][0]["id"] == "current"


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


def test_close_wt_does_not_invoke_wt() -> None:
    calls: list[list[str]] = []

    def runner(argv):
        calls.append(list(argv))
        return RunResult(list(argv), 0, "", "")

    with pytest.raises(MuxError, match="没有 close-pane"):
        close_pane("current", info=WT, runner=runner)
    assert calls == []


def test_close_herdr_id() -> None:
    calls: list[list[str]] = []

    def runner(argv):
        calls.append(list(argv))
        return RunResult(list(argv), 0, "", "")

    close_pane("w1:p2", info=HERDR, runner=runner)
    assert calls[0] == ["herdr", "pane", "close", "w1:p2"]
