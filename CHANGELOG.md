# Changelog

## [Unreleased]

### 新增

- `project init`：把自带 `project` skill 同时写入 `.agents/skills/project/` 与 `.claude/skills/project/`（独立拷贝）
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
