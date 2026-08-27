# Spec: workspace

From: `intent.md`. Status: accepted.

## Requirements

- `workspace detect`：Windows 用 `WT_SESSION`/`WT_PROFILE_ID`；Linux/macOS 用 `HERDR_*`。`--json`。不在复用器里退出码 1。
- `workspace split right|down`：wt → `split-pane -V|-H`；herdr → `pane split --direction right|down`。可选 `--cmd/--cwd/--title/--size`。
- `workspace pane list|focus|close`：focus 只接受方向；wt close 只关 current；herdr close 用窗格 id。
- `workspace pipe send` / `listen`：`.workspace/inbox/` 一文件一条消息；listen 打印后移到 `.workspace/seen/`。
- `workspace init`：拷到 `.agents/skills/workspace/` 与 `.claude/skills/workspace/`。

## Design

新 uv 包 `packages/workspace`（`coreskills-workspace`），入口 `workspace`。窗格命令把 wt/herdr 差异收在 `panes.py`，测试注入 runner，不真调终端。

## Areas of concern

wt CLI 没有窗格 id 列表；list/close 能力弱于 herdr，skill 里写明。
