from __future__ import annotations

from pathlib import Path

from coreskills_workspace.cli import main


def test_init_writes_two_copies(tmp_path: Path) -> None:
    assert main(["init", str(tmp_path)]) == 0
    agents = tmp_path / ".agents" / "skills" / "workspace"
    claude = tmp_path / ".claude" / "skills" / "workspace"
    assert (agents / "SKILL.md").is_file()
    assert (claude / "SKILL.md").is_file()
    assert (agents / "references" / "pipe.md").is_file()
    assert (claude / "references" / "panes.md").is_file()
    assert not (agents / "references" / "README.md").exists()
    assert agents.resolve() != claude.resolve()
    (agents / "references" / "only-agents.md").write_text("x\n", encoding="utf-8")
    assert not (claude / "references" / "only-agents.md").exists()


def test_init_skips_without_force(tmp_path: Path) -> None:
    dest = tmp_path / ".agents" / "skills" / "workspace"
    dest.mkdir(parents=True)
    (dest / "SKILL.md").write_text("# old\n", encoding="utf-8")
    assert main(["init", str(tmp_path)]) == 0
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == "# old\n"
    assert (tmp_path / ".claude" / "skills" / "workspace" / "SKILL.md").is_file()
