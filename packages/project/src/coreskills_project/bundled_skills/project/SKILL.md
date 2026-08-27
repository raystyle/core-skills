---
name: project
description: >
  维护项目文档结构与健康度：CLAUDE.md / AGENTS.md / REVIEW.md / SDLC 变更链，
  以及 git pre-push 关键文档同步。Use when 初始化仓库文档、project check 报缺文件、
  或开一次 intent/spec/plan 变更时。
---

# project

先 SDLC，再本仓。细节在 `references/`，不要一次读完。

## 命令

```
uv run project init           # 本 skill → .agents/skills + .claude/skills 别名
uv run project check
uv run project hooks install  # pre-push：代码改了文档没动则提醒
```

## 常驻（check 缺了报错）

`CLAUDE.md`（五段标题 + `@AGENTS.md`）、`AGENTS.md`、`REVIEW.md`、
`docs/sdlc/templates/{intent,spec,plan}.md`、`docs/sdlc/changes/`。

清单与写法：[references/layout.md](references/layout.md)、[references/claude-md.md](references/claude-md.md)。

## 一次变更

拷模板到 `docs/sdlc/changes/<短名>/`：intent → spec → plan。
[references/sdlc-change.md](references/sdlc-change.md)

## 其它

- 评审：[references/review.md](references/review.md)
- 项目级 skill：[references/skills.md](references/skills.md)
- 推送同步：[references/hooks.md](references/hooks.md)
- 六态（可选）：[references/six-states.md](references/six-states.md)
