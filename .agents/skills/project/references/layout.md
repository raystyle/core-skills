# 新项目文档清单

`project check` 按两层检：**先 SDLC，再本仓**。

## 常驻（缺了报错）

| 文件 | 职责 |
|------|------|
| `CLAUDE.md` | 五段标题，见 [claude-md.md](claude-md.md) |
| `AGENTS.md` | 硬规则；CLAUDE.md 须 `@AGENTS.md` |
| `REVIEW.md` | PR 对照 intent / spec / plan |
| `docs/sdlc/templates/intent.md` | Plan 模板 |
| `docs/sdlc/templates/spec.md` | Design 模板 |
| `docs/sdlc/templates/plan.md` | Build 模板 |
| `docs/sdlc/changes/` | 单次变更落点（目录必须在） |

## 按次变更（有则检链）

`docs/sdlc/changes/<短名>/{intent,spec,plan}.md`，见 [sdlc-change.md](sdlc-change.md)。

## check 不管必建

`README.md`、`ROADMAP.md`、`docs/README.md`。`CHANGELOG.md` 不作为结构必建，但 **pre-push 会扫**是否随代码更新。

项目级 skill 用 `project init` 安装，check **不建议去建 skill**，只校验已有 SKILL.md，见 [skills.md](skills.md)。
