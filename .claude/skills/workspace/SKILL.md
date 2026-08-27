---
name: workspace
description: >
  检测当前智能体在 wt（Windows）还是 herdr（Linux）里，
  同一窗口拆/换/调格、读指定格、关指定格，以及文件信箱。
  Use when 要拆窗格、起 claude/codex/kimi、查同一窗口有几格、读/关某一格、或让 agent 监听消息。
---

# workspace

细节在 `references/`，不要一次读完。

## 同一窗口建格 / 布局

默认 `--cwd` 是当前目录。wt 走 `split-pane -w 0 --startingDirectory`，命令经 pwsh EncodedCommand 启动（避免 `;` 被 wt 切开）。

```
uv run workspace pane split right --agent claude
uv run workspace pane split down --agent kimi
uv run workspace pane split right --cmd "pwsh -NoProfile"
uv run workspace pane swap left
uv run workspace pane resize right
```

`--agent` 查 PATH（claude / codex / kimi / grok，或其它名字）。不要加 yolo 参数。`--agent` 与 `--cmd` 互斥。`workspace split` 是同一条命令的别名。新格会清掉宿主的 `NO_COLOR=1` / `TERM=dumb`，设 `xterm-256color`（否则 TUI 单色）。

wt 没有 `resize-pane` CLI，resize 发默认键位 Alt+Shift+方向。swap 走 `wt swap-pane`。

## 同一窗口：count / read / 交互 / close

格子有两套标记：序号 `0..n-1`（给 `wt focus-pane -t`），以及 `pane_id`（`WT_SESSION`，类似 Herdr 的 `HERDR_PANE_ID`）。`read` / `text` / `keys` / `close` 都能用。

```
uv run workspace pane count
uv run workspace pane read 1
uv run workspace pane keys 1 down
uv run workspace pane keys 1 enter
uv run workspace pane text 1 "hello"
uv run workspace pane keys 1 enter
uv run workspace pane close 1
```

菜单选择用 **方向键**（`up`/`down`/`left`/`right`，也可用 上/下/左/右），再 `enter` 确认。这是发给目标格 TUI 的键，不是 `pane focus` 换格。

打字和 Enter **分开发**：TUI 智能体常会吞「字+回车」同一次发送。wt 没有 send-keys CLI，对目标格 TermControl `SetFocus` 再 SendInput。不能向当前正在跑本命令的那一格发键。

关格：对目标 TermControl `SetFocus`，确认键盘焦点在那一格后才发 Ctrl+D（已退出）或 Ctrl+Shift+W。不要用 `wt -w 0 focus-pane`（多窗口会关错格）。不能关最后一格，也不能关正在跑本命令的那一格。

## 其它

```
uv run workspace init
uv run workspace detect
uv run workspace pane list
uv run workspace pipe send "文本"
uv run workspace pipe listen
```

[references/panes.md](references/panes.md) · [references/detect.md](references/detect.md) · [references/pipe.md](references/pipe.md)
