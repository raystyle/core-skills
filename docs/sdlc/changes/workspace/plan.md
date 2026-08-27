# Plan: workspace

From: `intent.md` / `spec.md`. Status: done.

## Files that change

- `packages/workspace/`（CLI、skill、init）
- `tests/test_workspace_*.py`
- 根 `pyproject.toml`、`.gitignore`、`AGENTS.md`、`CLAUDE.md`、`CHANGELOG.md`、`ROADMAP.md`、`README.md`

## Order of work

1. 包骨架与 uv workspace 接入
2. detect / panes / pipe / init / CLI
3. bundled skill + 测试
4. 本仓 `workspace init` 装两份

## Risks

wt `close-pane` 视本机 Windows Terminal 版本；不支持时命令失败并打印 stderr。

## Proof

- `uv run pytest`（含 test_workspace_*）
- `uv run workspace detect --json`
- `uv run workspace init` 后两目录都有 `SKILL.md`
