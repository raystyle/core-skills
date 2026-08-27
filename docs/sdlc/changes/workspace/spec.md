# Spec: workspace

From: `intent.md`. Status: accepted.

## Requirements

- `workspace detect`：Windows 用 `WT_SESSION`/`WT_PROFILE_ID`；Linux/macOS 用 `HERDR_*`。`--json`。不在复用器里退出码 1。
- `workspace split right|down` / `pane split`：同一窗口拆格。默认 cwd 为当前目录。wt → `split-pane -w 0 -V|-H --startingDirectory`，命令走 pwsh EncodedCommand；herdr → `pane split --direction right|down --cwd`。可选 `--agent/--cmd/--cwd/--title/--size`（`--agent` 与 `--cmd` 互斥）。
- `workspace pane swap|resize`：swap 走 wt `swap-pane` / herdr `pane swap`。wt 无 resize-pane，发 Alt+Shift+方向；herdr `pane resize --amount`。
- `workspace pane list|focus|close`：focus 接受方向或 wt 创建序号；`read`/`keys`/`close` 用 UIA TermControl 序号。wt close 不能关最后一格/自己；`close others` 多窗口时标题须含当前目录名否则拒绝。herdr close 用窗格 id（`close current` 关自己：Linux 再测）。
- `workspace pane text|keys`：向指定格打字或发按键。方向键 `up/down/left/right` 用于 TUI 菜单选择，不是换格。wt 无 send-keys CLI，对目标 TermControl `SetFocus` 且 `HasKeyboardFocus` 为真再 SendInput。不能向当前格发键。字和 Enter 分开发。
- 新格 `--inheritEnvironment` 同时清掉 `NO_COLOR`/`FORCE_COLOR=0`，设 `TERM=xterm-256color`。`wt -w 0` 是最近使用窗口：split/swap/focus 前钉本窗口；不要对已最大化窗口 `ShowWindow(SW_RESTORE)`。
- `workspace pipe send` / `listen`：`.workspace/inbox/` 一文件一条消息；listen 打印后移到 `.workspace/seen/`。
- `workspace init`：拷到 `.agents/skills/workspace/` 与 `.claude/skills/workspace/`。

## Design

新 uv 包 `packages/workspace`（`coreskills-workspace`），入口 `workspace`。窗格命令把 wt/herdr 差异收在 `panes.py`，测试注入 runner，不真调终端。

## Areas of concern

wt CLI 没有窗格 id 列表、没有 close-pane/send-keys/resize-pane。UIA 序号与 `focus-pane -t` 创建序号可能错位。`pane read` 无 ANSI。herdr 关自己 / Linux import 冒烟留到 Linux。
