# Windows Terminal CLI（源码）

来源：[microsoft/terminal `AppCommandlineArgs.cpp`](https://github.com/microsoft/terminal/blob/main/src/cascadia/TerminalApp/AppCommandlineArgs.cpp)（本机包 1.24.11911.0 与此一致）。

`wt --help` **不会写 stdout**。解析错误/帮助进 `_exitMessage`，由进程弹 Win32 Help 对话框。因此 `wt --help > help.txt` 是 0 字节。不要为了查命令去跑 `--help`。

## 子命令（`_buildParser`）

| 命令 | 别名 | 作用 |
|------|------|------|
| `new-tab` | `nt` | 新标签 |
| `split-pane` | `sp` | 拆窗格：`-H`=Down，`-V`=Right，`-s/--size` 0.01–0.99；`-d/--startingDirectory`；`--inheritEnvironment` |
| `focus-tab` | `ft` | `-t` 标签序号 |
| `move-focus` | `mf` | 必填方向：`left/right/up/down/previous/nextInOrder/previousInOrder/first` |
| `move-pane` | `mp` | 焦点窗格移到另一标签 |
| `swap-pane` | | 与相邻窗格对调（方向同 move-focus） |
| `focus-pane` | `fp` | **必填** `-t/--target` 非负整数（按创建顺序的窗格 id） |
| `x-save` | | 内部保存命令行 |

**没有 `close-pane`，也没有 `resize-pane`、`send-keys`。** 调用未注册子命令会 `CLI::ParseError` → Help 对话框。调大小只能走默认键位 Alt+Shift+方向。往窗格打字/方向键：先 `focus-pane -t n`，再 SendInput（`workspace pane keys`）。

有 commandline 时源码把 `inheritEnv` 设为 true（PATH / 进程环境跟过去）；空 split 用配置文件则 reload。`--inheritEnvironment` / `--reloadEnvironment` 可显式覆盖。

`-w 0` / `--window 0`：**最近使用的窗口**，不是「本进程所在窗口」。另一扇 WT 在前台时 split/focus 会打到那边。本 CLI 在 split 前把本窗口拉到前台。

## `;` 分隔符

`BuildCommands` 用正则 `^;|[^\\];` 切开**每一条 argv**。未转义的 `;` 会变成下一条 `wt` 子命令（隐式 `new-tab`），于是去启动 `;` 后面的词当可执行文件 → `0x80070002 系统找不到指定的文件`（例如 `Start-Sleep`）。

`workspace split --cmd` 若含 `;`，改为 `pwsh -EncodedCommand`，wt 命令行里不再出现分号。
