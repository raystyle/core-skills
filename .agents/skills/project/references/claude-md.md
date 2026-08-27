# CLAUDE.md 与 AGENTS.md

两文件并存，不能互相替代。

## CLAUDE.md

仓库根或 `.claude/CLAUDE.md`。每个 session 都读，建议少于 200 行。必须有这些 `##` 标题：

- Commands（含健康输出长什么样）
- Conventions
- Architecture
- Things Claude gets wrong
- Verifying your work

第一行（或文中）`@AGENTS.md`，下面写 Claude 自己的命令与常错，不要只剩桥接一行。

## AGENTS.md

团队硬规则唯一权威源。CLAUDE.md 不重复维护规则正文。

## 个人

`CLAUDE.local.md` 不入库（gitignore）。
