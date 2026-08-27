# 窗格原语

必须已经在 wt 或 herdr 里，否则命令失败。

## split

| 统一 | wt | herdr |
|------|----|-------|
| `right`（`v` / `vertical`） | `wt -w 0 split-pane -V` | `herdr pane split --current --direction right` |
| `down`（`h` / `horizontal`） | `wt -w 0 split-pane -H` | `herdr pane split --current --direction down` |

`--cmd` 在 wt 里作为新 pane 的 commandline；在 herdr 里 split 之后 `pane run`。`--size` 对应 wt `--size` / herdr `--ratio`。

wt 把未转义的 `;` 当成下一条 wt 命令。`--cmd` 里带分号时走 `pwsh -EncodedCommand`，否则会去启动 `Start-Sleep` 这类词并报 `0x80070002`。

## list / focus / close

依据 [microsoft/terminal AppCommandlineArgs.cpp](https://github.com/microsoft/terminal/blob/main/src/cascadia/TerminalApp/AppCommandlineArgs.cpp)。完整对照见 `docs/research/wt-cli.md`。

| 命令 | wt | herdr |
|------|----|-------|
| `pane list` | 无 list API；id 是创建序号 0,1,2… | `herdr pane list` |
| `pane focus left\|right\|up\|down` | `wt -w 0 move-focus DIR` | `herdr pane focus --direction DIR --current` |
| `pane focus <n>` | `wt -w 0 focus-pane -t n` | 不支持（不是方向） |
| `pane close` | **没有这个子命令** | `herdr pane close <id>` |

不要对 wt 调用未列出的子命令，`--help` / 未知命令会弹 Help 对话框，stdout 是空的。
