# core-skills

> 一句话定位：一组用 uv 维护的项目级 CLI；当前可用的是 `project`（AGENTS.md+CLAUDE.md 结构检查、skill 健康度、改文件看文档 / 提交更新文档）。

## 快速开始

```powershell
cd D:\core-skills
uv sync
uv run project init
uv run project check .
uv run project hooks install
```

## 目录结构

```
core-skills/
  packages/project/   # project 命令
  tests/              # 回归测试
  docs/               # 文档地图
```

## 核心概念

| 术语 | 定义 |
|------|------|
| 结构检查 | 五类元文件、七段式 README、gitignore 三类、CHANGELOG/ROADMAP 存在 |
| 文档状态 | 地图登记、六态标记、CHANGELOG [Unreleased]、ROADMAP 四态、与 git 提交同步 |
| hook 提示 | 不同 git 事件提示更新不同文档，默认不阻断提交 |

## 常用命令

```powershell
uv run project check                 # 结构 + 文档状态
uv run project check --structure
uv run project check --docs --strict
uv run project hooks install         # git pre-push：代码改了文档没动则提醒
uv run project check --sync          # 手动跑同一扫描（相对上游）
uv run project hooks status
uv run pytest
```

## 文档导航

| 文档 | 讲什么 | 何时看 |
|------|--------|--------|
| [AGENTS.md](AGENTS.md) | 开发规则 | 改代码前 |
| [docs/README.md](docs/README.md) | 文档地图 | 找文档时 |
| [CHANGELOG.md](CHANGELOG.md) | 变更记录 | 改完同步 |
| [ROADMAP.md](ROADMAP.md) | 里程碑 | 推进阶段时 |

## 环境前提

- uv 0.12.x
- Python 3.12（`uv python pin` 已写入 `.python-version`）
- git（hook 部署需要）
