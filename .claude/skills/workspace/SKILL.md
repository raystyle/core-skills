---
name: workspace
description: >
  检测当前智能体在 wt（Windows）还是 herdr（Linux）里，
  统一分割/列表/聚焦/关闭窗格，并用 .workspace/inbox 文件信箱传文本。
  Use when 要拆窗格、查自己在哪个终端、或让 agent 后台监听其它进程的消息。
---

# workspace

细节在 `references/`，不要一次读完。

## 命令

```
uv run workspace init
uv run workspace detect
uv run workspace split right|down [--cmd ...] [--cwd ...] [--title ...] [--size 0.4]
uv run workspace pane list
uv run workspace pane focus left|right|up|down
uv run workspace pane close [id|current]
uv run workspace pipe send "文本"
uv run workspace pipe listen
```

## 检测

Windows 看 `WT_SESSION`（是否在 Windows Terminal）。Linux 看 `HERDR_ENV` / `HERDR_PANE_ID`（是否在 Herdr）。
[references/detect.md](references/detect.md)

## 窗格

`split` / `pane list` / `pane focus` / `pane close` 是统一原语。wt 与 herdr 后端不同：herdr 有窗格 id；wt 只能方向聚焦，不能关窗格（无 CLI，乱调会弹出帮助表）。
[references/panes.md](references/panes.md)

## 信箱

其它进程：`workspace pipe send`。Agent 起后台：`workspace pipe listen`（打印到 stdout，文件移到 `.workspace/seen/`）。
[references/pipe.md](references/pipe.md)
