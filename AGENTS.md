# core-skills — 项目规范

> 项目名 core-skills；对外命令目前是 `project` 与 `workspace`。本文件是开发协作规则唯一权威源。

## 项目概览

用 uv workspace 维护若干 Python CLI（`project` / `workspace` / `harness`）和对应 skill。本阶段已落地 `project` 与 `workspace`。

## 硬规则

1. 新功能写在 `D:\core-skills`，参考仓只读。
2. 根目录不切进 `packages/` 再跑 uv；一律在仓库根 `uv run`。
3. 文档先 SDLC 再本仓：常驻 `CLAUDE.md`（五段标题）+ `REVIEW.md` + `docs/sdlc/`；本仓再叠 `AGENTS.md` 并存。
4. 一次变更走 `docs/sdlc/changes/<短名>/`：intent → spec → plan；实现偏离 plan 则同一 commit 改 plan。
5. 项目 skill 同时写入 `.agents/skills/` 与 `.claude/skills/`（两份独立拷贝）。
6. 推送时 `pre-push` 会扫关键文档是否随代码更新。
7. 改代码同步 `CHANGELOG.md` `[Unreleased]`；里程碑翻 `ROADMAP.md`。

## 验收门禁

```powershell
uv run project check .
uv run workspace detect --json
uv run pytest
```

## 目录与分类规范

- `packages/project/`：`project` 命令
- `packages/workspace/`：`workspace` 命令
- `tests/`：根测试

## 环境事实

- uv 0.12.x，Python 3.12，Windows / pwsh

## 待办

见 `ROADMAP.md`。
