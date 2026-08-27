from __future__ import annotations

from pathlib import Path

from coreskills_workspace.cli import main
from coreskills_workspace.pipe import listen, pending, send


def test_send_and_listen_once(tmp_path: Path) -> None:
    path = send(tmp_path, "hello")
    assert path.parent.name == "inbox"
    assert path.read_text(encoding="utf-8") == "hello\n"
    got: list[str] = []
    n = listen(tmp_path, once=True, emit=got.append)
    assert n == 1
    assert got == ["hello\n"]
    assert pending(tmp_path) == []
    seen = tmp_path / ".workspace" / "seen"
    assert any(p.read_text(encoding="utf-8") == "hello\n" for p in seen.iterdir())


def test_listen_timeout_zero_drains(tmp_path: Path) -> None:
    send(tmp_path, "a")
    send(tmp_path, "b")
    got: list[str] = []
    n = listen(tmp_path, timeout=0, emit=got.append)
    assert n == 2
    assert "".join(got) == "a\nb\n"
    assert pending(tmp_path) == []


def test_cli_send_and_listen(tmp_path: Path, capsys) -> None:
    assert main(["pipe", "send", "ping", "--root", str(tmp_path)]) == 0
    rel = capsys.readouterr().out.strip()
    assert rel.startswith(".workspace/inbox/")
    assert main(["pipe", "listen", "--root", str(tmp_path), "--timeout", "0"]) == 0
    assert capsys.readouterr().out == "ping\n"
