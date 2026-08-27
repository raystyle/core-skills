# 新窗格无色彩

## 现象

`workspace pane split --agent claude` 起的右侧格是单色 TUI。`pane read` 也没有 ANSI。

## 根因（win-rmux 已踩过）

来源：`win-rmux/references/rmux-usage.md`（2026-08-19 实测）。

本机 grok/codex 沙箱给 **每个 exec 子进程** 注入：

| 变量 | 值 | 效果 |
|------|----|------|
| `NO_COLOR` | `1` | 智能体关掉颜色。**置空无效，必须删掉变量** |
| `FORCE_COLOR` | `0` | chalk/ink 显式关色；只设 TERM 不够 |
| `TERM` | `dumb` | 当 dumb 终端，无 256 色 |
| `COLORTERM` | （空） | 没有 truecolor |

本会话实测：`TERM=dumb`、`NO_COLOR=1`。

`wt split-pane --inheritEnvironment` 把这套环境原样带进新格。claude inheriting 后就是灰阶。

另外：`wt -w 0` 是**最近使用的窗口**，不是「本格所在窗口」。另一扇 grok 在前台时，split 会拆到那边。本窗口已在前台则不动；最小化才 `SW_RESTORE`。不要对已最大化窗口 `ShowWindow(9)`，否则会先缩一下再拆格。

win-rmux 的处理（launcher / 独立 wt 窗口同一套）：

```powershell
Remove-Item Env:NO_COLOR -ErrorAction SilentlyContinue
$env:TERM = 'xterm-256color'
$env:COLORTERM = 'truecolor'
```

「无色彩的真正根因是 NO_COLOR=1，不是客户端 TERM。」旧 daemon 若带着 NO_COLOR 启动，新 pane 仍会单色。

## 和 `pane read` 的区别

| 层 | 有没有颜色 |
|----|------------|
| 窗格里人眼看到的 TUI | 取决于进程 env（上面那套） |
| `workspace pane read` | **永远没有。** UIA `TextPattern.GetText()` 只给纯文本，不给 ANSI / 前景色 |
| herdr `pane read --ansi` | herdr 从 PTY 读，可保留 ANSI |
| rmux `capture-pane -p` | 默认定稿；claude/kimi **备屏**时常为空，与颜色无关 |

所以：修好启动 env，右侧 claude **看起来**会有色彩；`pane read` 仍然是无色纯文本。TUI 备屏（claude/kimi）长回复要以写文件为准，不要指望 capture/UIA。

## 本 CLI

两处一起清：

1. 调用 `wt` 时用去掉 `NO_COLOR`/`FORCE_COLOR` 的 env，并设 `FORCE_COLOR=1`（`--inheritEnvironment` 拷的是 wt 客户端环境）。
2. EncodedCommand 里再 `Remove-Item Env:NO_COLOR,Env:FORCE_COLOR`，设 `TERM`/`COLORTERM`/`FORCE_COLOR=1`。

本机已开的 claude 格：包装 pwsh 已是 `TERM=xterm-256color` 且无 `NO_COLOR`，但仍是 `FORCE_COLOR=0`，所以 TUI 还是灰的。要重新 split 才生效。
