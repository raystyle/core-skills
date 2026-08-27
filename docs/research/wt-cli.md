# Windows Terminal CLI（源码）

来源：[microsoft/terminal `AppCommandlineArgs.cpp`](https://github.com/microsoft/terminal/blob/main/src/cascadia/TerminalApp/AppCommandlineArgs.cpp)（本机包 1.24.11911.0 与此一致）。

`wt --help` **不会写 stdout**。解析错误/帮助进 `_exitMessage`，由进程弹 Win32 Help 对话框。因此 `wt --help > help.txt` 是 0 字节。不要为了查命令去跑 `--help`。

## 子命令（`_buildParser`）

| 命令 | 别名 | 作用 |
|------|------|------|
| `new-tab` | `nt` | 新标签 |
| `split-pane` | `sp` | 拆窗格：`-H`=Down，`-V`=Right，`-s/--size` 0.01–0.99 |
| `focus-tab` | `ft` | `-t` 标签序号 |
| `move-focus` | `mf` | 必填方向：`left/right/up/down/previous/nextInOrder/previousInOrder/first` |
| `move-pane` | `mp` | 焦点窗格移到另一标签 |
| `swap-pane` | | 与相邻窗格对调（方向同 move-focus） |
| `focus-pane` | `fp` | **必填** `-t/--target` 非负整数（按创建顺序的窗格 id） |
| `x-save` | | 内部保存命令行 |

**没有 `close-pane`。** 调用未注册子命令会 `CLI::ParseError` → Help 对话框。

`-w 0` / `--window 0`：当前窗口。
