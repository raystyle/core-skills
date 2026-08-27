from __future__ import annotations

from coreskills_workspace.cli import main
from coreskills_workspace.detect import detect


def test_windows_inside_wt(monkeypatch) -> None:
    monkeypatch.setenv("WT_SESSION", "guid-1")
    monkeypatch.delenv("WT_PROFILE_ID", raising=False)
    monkeypatch.delenv("HERDR_ENV", raising=False)
    monkeypatch.delenv("HERDR_PANE_ID", raising=False)
    monkeypatch.delenv("HERDR_SOCKET_PATH", raising=False)
    info = detect(plat="win32")
    assert info.os == "windows"
    assert info.expected == "wt"
    assert info.mux == "wt"
    assert info.inside
    assert "WT_SESSION" in info.evidence


def _clear_mux_env(monkeypatch) -> None:
    for key in (
        "WT_SESSION",
        "WT_PROFILE_ID",
        "HERDR_ENV",
        "HERDR_PANE_ID",
        "HERDR_SOCKET_PATH",
    ):
        monkeypatch.delenv(key, raising=False)


def test_windows_not_in_wt(monkeypatch) -> None:
    _clear_mux_env(monkeypatch)
    info = detect(plat="win32")
    assert info.mux is None
    assert not info.inside


def test_linux_inside_herdr(monkeypatch) -> None:
    _clear_mux_env(monkeypatch)
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setenv("HERDR_PANE_ID", "w1:p1")
    info = detect(plat="linux")
    assert info.os == "linux"
    assert info.expected == "herdr"
    assert info.mux == "herdr"
    assert info.pane == "w1:p1"


def test_linux_not_in_herdr(monkeypatch) -> None:
    monkeypatch.delenv("HERDR_ENV", raising=False)
    monkeypatch.delenv("HERDR_PANE_ID", raising=False)
    monkeypatch.delenv("HERDR_SOCKET_PATH", raising=False)
    monkeypatch.delenv("WT_SESSION", raising=False)
    monkeypatch.delenv("WT_PROFILE_ID", raising=False)
    info = detect(plat="linux")
    assert info.mux is None


def test_windows_herdr_preview(monkeypatch) -> None:
    monkeypatch.delenv("WT_SESSION", raising=False)
    monkeypatch.delenv("WT_PROFILE_ID", raising=False)
    monkeypatch.setenv("HERDR_ENV", "1")
    info = detect(plat="win32")
    assert info.mux == "herdr"


def test_cli_detect_json_exit(monkeypatch, capsys) -> None:
    _clear_mux_env(monkeypatch)
    code = main(["detect", "--json"])
    assert code == 1
    out = capsys.readouterr().out
    assert '"inside": false' in out
