# Spec: workspace

From: `intent.md`. Status: accepted.

## Requirements

- `workspace detect`：Windows 用 `WT_SESSION`/`WT_PROFILE_ID`；Linux/macOS 用 `HERDR_*`。`--json`。不在复用器里退出码 1。
- `workspace split right|down` / `pane split`：同一窗口拆格。默认 cwd 为当前目录。wt → `split-pane -w 0 -V|-H --startingDirectory`，命令走 pwsh EncodedCommand；herdr → `pane split --direction right|down --cwd`。可选 `--agent/--cmd/--cwd/--title/--size`（`--agent` 与 `--cmd` 互斥）。
- `workspace pane swap|resize`：swap 走 wt `swap-pane` / herdr `pane swap`。wt 无 resize-pane，发 Alt+Shift+方向；herdr `pane resize --amount`。
- `workspace pane list|focus|close`：focus 只接受方向或序号；wt close 不能关最后一格/自己；herdr close 用窗格 id。
- `workspace pane text|keys`：向指定格打字或发按键。方向键 `up/down/left/right` 用于 TUI 菜单选择，不是换格。wt 无 send-keys CLI，先 `focus-pane` 再 SendInput。不能向当前格发键。字和 Enter 分开发。
- `workspace pipe send` / `listen`：`.workspace/inbox/` 一文件一条消息；listen 打印后移到 `.workspace/seen/`。
- `workspace init`：拷到 `.agents/skills/workspace/` 与 `.claude/skills/workspace/`。

## Design

新 uv 包 `packages/workspace`（`coreskills-workspace`），入口 `workspace`。窗格命令把 wt/herdr 差异收在 `panes.py`，测试注入 runner，不真调终端。

## Areas of concern

wt CLI 没有窗格 id 列表；list/close 能力弱于 herdr，skill 里写明。
