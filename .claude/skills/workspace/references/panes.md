# 窗格原语

必须已经在 wt 或 herdr 里，否则命令失败。

## split

| 统一 | wt | herdr |
|------|----|-------|
| `right`（`v` / `vertical`） | `wt -w 0 split-pane -V` | `herdr pane split --current --direction right` |
| `down`（`h` / `horizontal`） | `wt -w 0 split-pane -H` | `herdr pane split --current --direction down` |

`--cmd` 在 wt 里作为新 pane 的 commandline；在 herdr 里 split 之后 `pane run`。`--size` 对应 wt `--size` / herdr `--ratio`。

wt 把未转义的 `;` 当成下一条 wt 命令。`--cmd` 里带分号时走 `pwsh -EncodedCommand`，否则会去启动 `Start-Sleep` 这类词并报 `0x80070002`。

## 同一窗口：count / read / close

当前工作台用窗口标题里的目录名认定（不要用前台窗口）。格子 = 该 HWND 下 UIA `TermControl`，编号 0..n-1。

| 命令 | 做什么 |
|------|--------|
| `pane count` | 同一窗口几格 |
| `pane read n` | 读第 n 格屏幕文本 |
| `pane close n` | 关掉第 n 格：已退出 → Ctrl+D；仍在跑 → Ctrl+Shift+W |

`close` 拒绝最后一格，以及 preview 里带 `workspace pane` 的自身格。

`pane list` 仍列出所有 Cascadia 窗口。`docs/research/wt-windows.md`。
