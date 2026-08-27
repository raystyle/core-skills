# Changelog

## [Unreleased]

### 新增

- `workspace` CLI：`detect`（Windows=wt / Linux=herdr）、`split` + `pane list/focus/close`、`.workspace/inbox` 文件信箱（`pipe send` / `pipe listen`）
- wt 的 `pane close` 直接拒绝：源码无 close-pane；`pane focus <n>` 走 `focus-pane -t`（见 docs/research/wt-cli.md）
- `split --cmd` 含 `;` 时改 `pwsh -EncodedCommand`，避免 wt 把分号切成下一条命令（`0x80070002`）
- wt `pane list` 按 Cascadia HWND + UIA TermControl 区分窗口
- 同一窗口三原语：`pane count` / `pane read` / `pane close`；`pane_id` 用 `WT_SESSION`（对齐 Herdr 的 `HERDR_PANE_ID`）
- 同一窗口建格 / 布局：`pane split`（`split` 别名）默认 `--startingDirectory`/`--cwd` 为当前目录；`--agent claude|codex|kimi|…` 经 pwsh EncodedCommand 启动；`pane swap`；`pane resize`（wt 无 CLI，发 Alt+Shift+方向）
- 同一窗口交互：`pane text` / `pane keys`（wt 无 send-keys CLI，对目标 TermControl SetFocus 再 SendInput）。菜单选择用 `up/down/left/right`
- `pane close` 不再走 `wt -w 0 focus-pane`（会关错当前格）；改为目标 TermControl SetFocus，确认焦点后再 Ctrl+Shift+W / Ctrl+D
- 新格启动清掉继承来的 `NO_COLOR=1` / `TERM=dumb` / `FORCE_COLOR=0`，设 `xterm-256color` 与 `FORCE_COLOR=1`（win-rmux 同款；否则 claude 单色）。split 前把本窗口拉到前台，避免 `wt -w 0` 拆到另一扇
- 按 claude 评审修 Windows 侧：`swap`/`focus` 同样钉本窗口；`close others` 多窗口必须标题含目录名否则拒绝；send/resize SetFocus 后复核焦点；`_tag_records` 不再把外来壳的 pane_id 贴到本窗口；stdin `pane text` 去掉尾随换行。herdr 关自己 / Linux import 冒烟留到 Linux 上测
- `workspace init`：自带 skill 整树拷到 `.agents/skills/workspace/` 与 `.claude/skills/workspace/` 各一份
- `project init`：把自带 `project` skill 整树拷到 `.agents/skills/project/` 与 `.claude/skills/project/` 各一份；已存在则跳过，`--force` 整目录覆盖
- 自带 skill 补 `references/`（layout / claude-md / sdlc-change / review / skills / hooks / six-states）；索引在 `SKILL.md`，`references/` 不放 README.md

### 变更

- `project check` 不再建议「去建 skill」；只扫描已有项目级 SKILL.md 是否符合 agentskills 规范

- 项目 skill 同时装到 `.agents/skills/` 与 `.claude/skills/`（两份独立拷贝，不用 junction / symlink）
- SDLC 文档结构：`REVIEW.md`、`docs/sdlc/templates/{intent,spec,plan}.md`、`docs/sdlc/changes/`；`CLAUDE.md` 补 Architecture / Verifying
- `project check` 先检 SDLC 层再检本仓层（AGENTS 并存、禁止 rules、skill）
- 文档健康度：两文件互相引用、SKILL.md 须有 name/description
- Hook：用 git `pre-commit` 代替 `.claude/rules`——暂存文件同时提示**请先看**和**请更新**哪些文档

### 变更

- git `pre-push`：代码改了但关键文档没动只打印提醒，不拦截推送

- 不再把 README 七段式 / CHANGELOG / ROADMAP / 六态 / git 四事件当作默认必检项（见 `docs/research/claude-ai-native-sdlc.md`）
- 不再写入 Claude Code `PostToolUse`；`hooks install` 会清掉先前装上的 file-change 段
