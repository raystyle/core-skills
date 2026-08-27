# 窗格原语

必须已经在 wt 或 herdr 里，否则命令失败。

## split

| 统一 | wt | herdr |
|------|----|-------|
| `right`（`v` / `vertical`） | `wt -w 0 split-pane -V` | `herdr pane split --current --direction right` |
| `down`（`h` / `horizontal`） | `wt -w 0 split-pane -H` | `herdr pane split --current --direction down` |

`--cmd` 在 wt 里作为新 pane 的 commandline；在 herdr 里 split 之后 `pane run`。`--size` 对应 wt `--size` / herdr `--ratio`。

## list / focus / close

| 命令 | wt | herdr |
|------|----|-------|
| `pane list` | 无原生 id，只报 `current` + session | `herdr pane list` |
| `pane focus left\|right\|up\|down` | `wt -w 0 move-focus DIR` | `herdr pane focus --direction DIR --current` |
| `pane close current` | `wt -w 0 close-pane`（关当前格） | 用 `HERDR_PANE_ID` |
| `pane close <id>` | 不支持 | `herdr pane close <id>` |

focus 不接受窗格 id，只接受方向。
