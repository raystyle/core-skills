---
name: workspace
description: >
  检测当前智能体在 wt（Windows）还是 herdr（Linux）里，
  同一窗口数窗格、读指定格内容、关指定格，以及文件信箱。
  Use when 要拆窗格、查同一窗口有几格、读/关某一格、或让 agent 监听消息。
---

# workspace

细节在 `references/`，不要一次读完。

## 同一窗口三原语

编号是当前 Cascadia 窗口里 `TermControl` 的顺序，和 `wt focus-pane -t` 一致。

```
uv run workspace pane count
uv run workspace pane read <n>
uv run workspace pane close <n>
```

关格：先 `focus-pane -t n`，已退出的发 Ctrl+D，还活着的发 Ctrl+Shift+W。不能关最后一格，也不能关正在跑本命令的那一格。

## 其它

```
uv run workspace init
uv run workspace detect
uv run workspace split right|down [--cmd ...]
uv run workspace pane list
uv run workspace pipe send "文本"
uv run workspace pipe listen
```

[references/panes.md](references/panes.md) · [references/detect.md](references/detect.md) · [references/pipe.md](references/pipe.md)
