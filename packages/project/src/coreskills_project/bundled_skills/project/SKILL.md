---
name: project
description: >
  维护项目文档结构与健康度：CLAUDE.md / AGENTS.md / REVIEW.md / SDLC 变更链，
  以及 git pre-push 关键文档同步。Use when 初始化仓库文档、project check 报缺文件、
  或开一次 intent/spec/plan 变更时。
---

# project

先 SDLC，再本仓约定。结构见 `docs/sdlc/README.md`。

## 常驻

- `CLAUDE.md`：Commands / Conventions / Architecture / Things Claude gets wrong / Verifying your work；并用 `@AGENTS.md`
- `AGENTS.md`：硬规则
- `REVIEW.md`：PR 对照 intent / spec / plan
- `docs/sdlc/templates/{intent,spec,plan}.md` 与 `docs/sdlc/changes/`

## 一次变更

复制模板到 `docs/sdlc/changes/<短名>/`，按 intent → spec → plan 写。

## 命令

```
uv run project init      # 把本 skill 装到 .agents/skills 与 .claude/skills
uv run project check
uv run project hooks install
```
