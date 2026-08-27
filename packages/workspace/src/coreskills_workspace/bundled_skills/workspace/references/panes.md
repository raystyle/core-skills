# 窗格原语

必须已经在 wt 或 herdr 里，否则命令失败。

## split（同一窗口建格）

`workspace pane split` 与 `workspace split` 相同。默认 `--cwd` = 当前工作目录。

| 统一 | wt | herdr |
|------|----|-------|
| `right`（`v` / `vertical`） | `wt -w 0 split-pane -V --startingDirectory <cwd>` | `herdr pane split --current --direction right --cwd <cwd>` |
| `down`（`h` / `horizontal`） | `wt -w 0 split-pane -H --startingDirectory <cwd>` | `herdr pane split --current --direction down --cwd <cwd>` |

`--agent claude|codex|kimi|grok|…`：在 PATH 上找可执行文件。wt 用 **pwsh -NoProfile -EncodedCommand** 跑 `& '绝对路径'`，并写入 `WORKSPACE_ENV` / `WORKSPACE_PANE_ID` / `WORKSPACE_AGENT`；herdr 先 split 再 `pane run <kind>`。不加 yolo 参数。

`--cmd` 是任意命令，与 `--agent` 互斥。`--size` 对应 wt `--size` / herdr `--ratio`。

wt 把未转义的 `;` 当成下一条 wt 命令。pwsh EncodedCommand 让分号不出现在 wt argv 里，否则会去启动 `Start-Sleep` 这类词并报 `0x80070002`。有 commandline 时加上 `--inheritEnvironment`（源码默认如此），PATH 和 API key 跟过去。

宿主（grok/codex 沙箱）常带 `NO_COLOR=1`、`TERM=dumb`。继承过去新格就是单色。EncodedCommand 里先 `Remove-Item Env:NO_COLOR`，再设 `TERM=xterm-256color` / `COLORTERM=truecolor`（win-rmux 实测：置空无效）。`pane read` 走 UIA `GetText`，**读出来仍无 ANSI**，只影响人眼看到的 TUI。见 `docs/research/pane-color.md`。

## 布局

| 统一 | wt | herdr |
|------|----|-------|
| `pane swap left/right/up/down` | 先把本窗口拉到前台，再 `wt -w 0 swap-pane` | `herdr pane swap --direction … --current` |
| `pane resize left/right/up/down` | 对本格 TermControl SetFocus 后发 Alt+Shift+方向（`--amount` 次数，默认 5） | `herdr pane resize --direction … --amount FLOAT --current` |

不要调用不存在的 `wt resize-pane`（会弹 Help 对话框）。`wt -w 0` 是最近使用窗口：swap/focus/split 执行前都先钉本窗口。

`pane keys 1` / `pane close 1` 的序号是 **UIA TermControl 顺序**；`pane focus 1` 的 `-t` 是 **wt 创建顺序**。拆过几次后两套编号可能对不上。`close others` 多窗口时标题必须含当前目录名，否则拒绝（避免 taskkill 另一扇 grok）。

## 交互：read → keys / text

wt **没有** send-keys CLI。对目标 HWND 下第 n 个 UIA `TermControl` 做 `SetFocus` 再 SendInput（不要用 `wt -w 0 focus-pane`，多窗口时 `-w 0` 会打到另一扇）。herdr 走 `pane send-text` / `pane send-keys`。

| 命令 | 做什么 |
|------|--------|
| `pane read n` | 读第 n 格屏幕 |
| `pane keys n down` | 方向键，菜单里往下选一项 |
| `pane keys n up` / `left` / `right` | 上 / 左 / 右 |
| `pane keys n enter` | 确认 |
| `pane keys n down enter` | 先下移再确认（仍是两次按键，中间有间隔） |
| `pane text n "hello"` | 打字，**不**带 Enter |
| `pane keys n ctrl+c` | 和弦 |

`pane focus left` 是换焦点到左边那格；`pane keys 1 left` 是向第 1 格的程序发 ←。别混。

对 TUI 智能体：先 `text` 再单独一次 `keys enter`。字和回车捆在一起常被吞。

## 同一窗口：count / read / close

当前工作台用窗口标题里的目录名认定（不要用前台窗口）。格子 = 该 HWND 下 UIA `TermControl`。

Herdr 往进程注入 `HERDR_PANE_ID`；WT 每格注入 `WT_SESSION`（本 CLI 当作 `pane_id`）。split 时再写入 `WORKSPACE_ENV` / `WORKSPACE_PANE_ID`。见 `docs/research/herdr-pane-identity.md`。

| 命令 | 做什么 |
|------|--------|
| `pane count` | 同一窗口几格 |
| `pane read n` | 读第 n 格屏幕文本 |
| `pane close n` | 关掉第 n 格：已退出 → Ctrl+D；仍在跑 → Ctrl+Shift+W |

`close` 与 `keys` 一样：对目标 TermControl `SetFocus`，**HasKeyboardFocus 为真才发键**。不要用 `wt -w 0 focus-pane`（会把 Ctrl+Shift+W 打进当前 grok 格）。拒绝最后一格、当前格、焦点没切过去的目标。

`pane list` 仍列出所有 Cascadia 窗口。`docs/research/wt-windows.md`。
