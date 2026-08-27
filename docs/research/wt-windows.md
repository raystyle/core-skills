# WT 窗口 vs 窗格（1.24）

来源：本机 `WindowsTerminal 1.24.11911.0` + [ConptyConnection.cpp](https://github.com/microsoft/terminal/blob/main/src/cascadia/TerminalConnection/ConptyConnection.cpp) + [WindowEmperor / #18215](https://github.com/microsoft/terminal/pull/18215)。

## 结论

| 层 | 是什么 | 怎么探测 |
|----|--------|----------|
| 进程 | 多个窗口共用 **一个** `WindowsTerminal.exe` | 进程树 **不能** 区分窗口 |
| 窗口（工作台） | HWND，类名 `CASCADIA_HOSTING_WINDOW_CLASS` | `EnumWindows` + pid |
| 标签 | UIA `TabItem` | 每个 HWND 下 `FindAll` |
| 窗格 | UIA `TermControl` | 每个 HWND 下 `ControlType.Text` + class `TermControl` |
| `WT_SESSION` | **每个 ConPTY 连接一条 GUID**（一格一个） | 不能用来把多格归到同一窗口 |

实测（2026-08-27）：同一 pid 下 2 个可见 Cascadia HWND。独立 grok 窗口 1 个 `TermControl`；当前 core-skills 窗口 2 个 `TermControl`。进程树却把 3 个 `pwsh` 全算进「当前窗口」——那是错的。

`wt -w 0` 的「当前窗口」靠前台/`WT_SESSION` 查宿主窗口，不是靠父进程。

## 当前窗格对应哪扇 HWND

壳进程没有自己的 HWND（ConPTY）。可靠近似：前台窗口若是 Cascadia 且 pid 相同，即当前工作台（agent 在前台格时成立）。UIA 里 `TermControl.Name` 只有配置名（如 PowerShell），对不上 grok/claude 进程。

因此：**可以数清某一窗口有几格，还不能把某个 `pwsh` pid 钉到某一格。** 不能按进程树 `close others`，会误杀独立窗口里的 grok。
