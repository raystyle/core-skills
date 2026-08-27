# SDLC 文档结构

两层。先满足 Anthropic AI-native SDLC，再叠本仓约定。

## 第一层：SDLC（标准）

常驻（每个 session / 每次评审）：

| 文件 | 职责 |
|------|------|
| `CLAUDE.md` | Commands、Conventions、Architecture、Things Claude gets wrong、Verifying your work |
| `REVIEW.md` | PR 怎么审：对照 intent/spec/plan |
| `.agents/skills/*/SKILL.md` | 可复用流程（跨端发现路径）；Claude 用 `.claude/skills` 别名。不用 `.claude/rules/` |

一次变更一条链（拷模板到 `changes/<短名>/`，下一阶段读上一阶段）：

```
docs/sdlc/changes/<短名>/
  intent.md   ← Plan
  spec.md     ← Design
  plan.md     ← Build
```

模板在 `templates/`。有 `plan.md` 必须已有 `spec.md`；有 `spec.md` 必须已有 `intent.md`。

## 第二层：本仓

| 文件 | 职责 |
|------|------|
| `AGENTS.md` | 团队硬规则，与 CLAUDE.md 并存（CLAUDE.md 用 `@AGENTS.md`） |
| `README.md` | 人读入口 |
| `CHANGELOG.md` / `ROADMAP.md` | 变更与里程碑 |
| `docs/README.md` | 地图 |
| git `pre-push` | 推送时扫描：改了代码但关键文档没动则输出提醒，不拦截 |

`uv run project hooks install` 部署该 hook。
