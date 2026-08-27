# 项目级 skill

SKILL.md 格式跟 [Agent Skills](https://agentskills.io/specification)。**发现路径各端不同**：

| 路径 | 谁原生扫 |
|------|----------|
| `.agents/skills/<name>/SKILL.md` | Codex 等（跨端真源） |
| `.claude/skills/` | Claude Code（本 CLI 做成指向 `.agents/skills` 的别名） |

```
uv run project init          # 安装自带 project skill
uv run project init --force  # 覆盖
```

`project check` 只校验**已经存在**的项目级 SKILL.md：

- YAML frontmatter：`name`、`description`（做什么 + 何时用）
- `name` 小写字母/数字/连字符，与目录名一致
- 正文建议 &lt; 500 行，细节放 `references/`

没有 skill 不报错、不建议去建。
