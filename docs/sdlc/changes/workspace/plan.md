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

wt 没有关闭窗格的 CLI。禁止调用 `close-pane`（未知子命令会弹出帮助表）。

## Proof

- `uv run pytest`（含 test_workspace_*）
- `uv run workspace detect --json`
- `uv run workspace init` 后两目录都有 `SKILL.md`
