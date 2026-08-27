from __future__ import annotations

import subprocess
from pathlib import Path

from coreskills_project.cli import main
from coreskills_project.hooks import install_hooks
from coreskills_project.skills_layout import claude_alias_ok
from coreskills_project.sync import check_code_doc_sync


def git(root: Path, *args: str) -> None:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr


def test_code_without_key_docs_fails() -> None:
    problems = check_code_doc_sync(["packages/project/src/x.py"])
    assert problems and "关键文档未同步" in problems[0].msg


def test_code_with_changelog_ok() -> None:
    assert check_code_doc_sync(["src/cli.py", "CHANGELOG.md"]) == []


def test_code_with_sdlc_plan_ok() -> None:
    assert check_code_doc_sync(
        ["packages/foo.py", "docs/sdlc/changes/demo/plan.md"]
    ) == []


def test_docs_only_ok() -> None:
    assert check_code_doc_sync(["CHANGELOG.md", "CLAUDE.md"]) == []


def test_install_writes_pre_push(tmp_path: Path) -> None:
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "t")
    leftover = tmp_path / ".claude"
    leftover.mkdir()
    (leftover / "settings.json").write_text(
        '{"hooks":{"PostToolUse":[{"hooks":[{"command":"project hooks run file-change"}]}]}}',
        encoding="utf-8",
    )
    (tmp_path / ".githooks").mkdir()
    (tmp_path / ".githooks" / "pre-commit").write_text("old\n", encoding="utf-8")
    actions = install_hooks(tmp_path)
    assert (tmp_path / ".githooks" / "pre-push").exists()
    assert not (tmp_path / ".githooks" / "pre-commit").exists()
    assert not (tmp_path / ".claude" / "settings.json").exists()
    assert claude_alias_ok(tmp_path)
    assert any("pre-push" in a for a in actions)


def test_cli_pre_push_reminds_code_only(capsys) -> None:
    code = main(["hooks", "run", "pre-push", "--file", "pkg.py"])
    assert code == 0
    err = capsys.readouterr().err
    assert "关键文档未同步" in err
    assert "[提醒]" in err


def test_cli_pre_push_ok_with_doc() -> None:
    assert main(["hooks", "run", "pre-push", "--file", "pkg.py", "--file", "CHANGELOG.md"]) == 0
