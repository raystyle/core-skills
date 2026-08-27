# Herdr 如何标记窗格

来源：[herdr SKILL](https://raw.githubusercontent.com/herdrdev/herdr/master/skills/herdr/SKILL.md)、[CLI](https://herdr.dev/docs/cli-reference/)、本仓 `pane.rs` 启动环境。

## 身份在进程里，不在 UI 顺序里

每个 Herdr 管理的窗格进程被注入：

| 变量 | 含义 |
|------|------|
| `HERDR_ENV=1` | 我在 Herdr 窗格里 |
| `HERDR_PANE_ID` | 本格公共 id，如 `w1:p1` |
| `HERDR_TAB_ID` | 如 `w1:t1` |
| `HERDR_WORKSPACE_ID` | 如 `w1` |
| `HERDR_SOCKET_PATH` | 控制面 |

`--current` 读的是**调用进程**的 `HERDR_PANE_ID`，不是前台焦点。关/读都带这个 id，不靠「左边那格」。

公共 id 不复用。`pane list` / `pane get` 返回结构化记录：`pane_id`、`label`、`cwd`、`focused`、agent 状态。`pane rename` 写人读标签；`report-metadata` 写侧栏展示，不抢生命周期。

## 对 WT 的对应

WT **没有** workspace/tab id，但每个 ConPTY 连接已经注入 **`WT_SESSION`（每格一条 GUID）**，语义接近 `HERDR_PANE_ID`。`WT_PROFILE_ID` 是配置文件。

本机实测（同一 `WindowsTerminal.exe`、两扇窗口）：

- 独立 grok 壳 `29076` → `WT_SESSION=975c447b-...`
- 当前 grok 壳 `39988` → `WT_SESSION=64f0a21d-...`（与本进程环境一致）

所以：同一窗口几格仍用 UIA `TermControl` 数；**指定格**用 `WT_SESSION`（及我们 split 时写入的 `WORKSPACE_PANE_ID`），不要只用 0/1 顺序，也不要用前台窗口。
