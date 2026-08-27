# 项目级 skill

SKILL.md 格式跟 [Agent Skills](https://agentskills.io/specification)。**发现路径各端不同**：

| 路径 | 谁原生扫 |
|------|----------|
| `.agents/skills/<name>/SKILL.md` | Codex 等 |
| `.claude/skills/<name>/SKILL.md` | Claude Code |

`project init` 把自带 skill **同时写入这两个目录**（两份独立拷贝）。

```
uv run project init          # 安装自带 project skill
uv run project init --force  # 覆盖
```

`project check` 只校验**已经存在**的项目级 SKILL.md：

- YAML frontmatter：`name`、`description`（做什么 + 何时用）
- `name` 小写字母/数字/连字符，与目录名一致
- 正文建议 &lt; 500 行，细节放 `references/`

没有 skill 不报错、不建议去建。
