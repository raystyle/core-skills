# Claude / Anthropic 原生 AI-SDLC：项目文档与 hook

## 需求

- 研究：Anthropic 官方「AI-native SDLC」与 Claude Code 文档规定了哪些**项目级 markdown**；各自职责与存放位置。
- 研究：官方对文档**健康度**有哪些可检查的期望（长度、何时更新、advisory vs 强制）。
- 研究：官方说的 **hook** 是 git hook 还是 Claude Code 生命周期 hook；和文档更新的关系；git commit/PR 在流程里扮演什么。
- 研究：Anthropic 公开仓库实际落了哪些 md。
- 核查：（无独立可真可假主张；下列结论均对照官方正文。）

## 结论

### 1. 官方项目 md：一条「常驻记忆」+ 一套阶段产物 + `.claude/` 扩展

官方不是 CoreSkills 那套 AGENTS/七段式 README/CHANGELOG/ROADMAP。原生分层是：

**A. 常驻、每个 session 都读（项目结构检查的核心对象）**

| 文件 | 位置 | 官方职责 | 是否进 git |
|------|------|----------|------------|
| `CLAUDE.md` | 仓库根或 `.claude/CLAUDE.md` | 新成员第一天需要的：Commands / Conventions / Architecture / 「Claude 常错的事」 | 是 |
| `CLAUDE.local.md` | 仓库根 | 个人偏好（沙箱 URL、本机测试数据） | **否**（加入 `.gitignore`） |
| `.claude/rules/*.md` | 项目 | 按主题拆的指令；可带 `paths:` 只在碰到匹配文件时加载 | 是 |
| `.claude/skills/<name>/SKILL.md` | 项目 | 可复用流程/政策；frontmatter 写何时触发 | 是 |
| `.claude/agents/*.md` | 项目 | 子 agent 定义 | 是 |
| `.claude/settings.json` | 项目 | 权限与 **Claude Code hooks**（不是 markdown，但是官方强制层） | 是 |

Claude Code **不原生读 `AGENTS.md`**。多 agent 仓库官方建议：`CLAUDE.md` 第一行 `@AGENTS.md`，或 Windows 上不要用 symlink。[实证: code.claude.com/docs/en/memory.md「AGENTS.md」节]

`README` 在官方例子里是 `@README` 导入对象，不是独立结构门禁。`CHANGELOG.md` / `ROADMAP.md` **没有**出现在官方 SDLC 文件清单里。

**B. 阶段产物（一次变更一条链，下一阶段读上一阶段）** — 来自 2026-08-21 官方 playbook，不是 Claude Code 运行时自动加载的文件名。

| 阶段 | 提交的产物 | 谁签 |
|------|------------|------|
| Plan | `intent.md`（问题/结果/约束/开放问题） | 产品负责人 merge |
| Design | `spec.md`（对着 intent + skills） | 产品负责人；高风险再找技术负责人 |
| Build | `plan.md`（改哪些文件、顺序、风险、证明） | 工程师在 plan mode 接受后再写代码 |
| Deploy | PR + 评审发现；建议根目录 `REVIEW.md` 写评审策略 | 人类 code owner 才能合 |

Playbook 原话：每阶段以提交一份产物结束，下一阶段从读它开始；早期阶段以 `.md` 为主，因为人和 agent 都能读同一份文件。[实证: claude.com/blog/the-ai-native-sdlc-playbook]

**C. 官方明确不要求、或只顺带提到**

- `CHANGELOG.md`：只在 CI 里作为「判断步骤」示例（用 `claude -p` 起草 changelog），不是必检元文件。
- `ROADMAP.md`：playbook 与 memory 文档均未列为项目文件。
- `docs/README.md` 地图、六态标记：非 Anthropic 规范。

### 2. 文档健康度：官方可检查的是「短、不过时、advisory vs 强制」

从 memory + playbook + features-overview 抽出、能做成检查器的点：

1. **存在性**：仓库有 `CLAUDE.md` 或 `.claude/CLAUDE.md`。
2. **长度**：目标 **< 200 行**；超过 4 MiB 会被跳过。`/doctor` 会建议删掉能从代码推出来的目录树/依赖列表。[实证: memory.md Size + /doctor]
3. **内容块**：Commands（含「健康输出长什么样」）、Conventions、Architecture、Things Claude gets wrong；验证命令写在 CLAUDE.md 的 Verifying 段。[实证: playbook CLAUDE.md 样例 + Test 阶段]
4. **更新时机**：同一错误第二次 → 写进 CLAUDE.md；PR 评审发现 CLAUDE.md 过时要标出来。[实证: playbook「mistake twice」+ Deploy 节]
5. **分层健康**：CLAUDE.md 膨胀应拆到 `.claude/rules/` 或 skill，不要继续塞根文件。[实证: features-overview 200 行经验法则]
6. **产物链健康（阶段文档）**：`intent.md` → `spec.md` → `plan.md` 应对同一变更；实现若偏离 plan，**同一 commit 更新 `plan.md`**；可考虑 hook 强制同步。[实证: playbook Build 节 step 7]
7. **强制 vs 提示**：CLAUDE.md / skill 是 **advisory**（模型尽量遵守）。必须成立的规则用 **Claude Code hook**（PreToolUse 拦截）或 PR 检查，不要写进 md 假装能拦。[实证: memory.md「context, not enforced」；features-overview Hook vs Skill]

**不能从官方推出的健康度**：六态、README 七段式、gitignore 三类、CHANGELOG [Unreleased]、ROADMAP 四态、docs 地图登记。那些是 CoreSkills/ProjectEvo 的规范，不是 Claude 原生 SDLC。

### 3. Hook：官方是 Claude Code 生命周期，不是 git pre-commit

官方 hooks 写在 `.claude/settings.json`（可提交）或 `~/.claude/settings.json`（本机）。事件是 **Claude 会话**，例如：

| 事件 | 官方典型用途 | 对文档的含义 |
|------|----------------|--------------|
| `PreToolUse` | 拦受保护路径、生产部署、改测试文件 | **拦截**（exit 2）；适合「不许动 CLAUDE.md / 不许改测试」 |
| `PostToolUse`（Edit\|Write） | 格式化、markdown formatter | 改完文件立刻跑，不是 git 时机 |
| `Stop` | 任务结束做确定性检查 | 重检查可放这里；全量测试官方说放 **commit 或 PR** |
| `FileChanged` | 监视 `.env` / 某 md | 磁盘变化即触发，不论谁写的 |
| `InstructionsLoaded` | 记录加载了哪份 CLAUDE.md/rules | 调试文档是否进上下文 |
| `SessionStart` / compact | 压缩后回灌关键约定 | 文档太长会被挤掉，所以要短 |

Playbook 原话：build 期 hook 要快、只盯改动的文件；**更重的检查（全量测试）属于 commit 或 PR**。需要人点头的 hook 属于 Deploy 门，不要插在每次编辑上。[实证: playbook「Hooks as build-time guardrails」+「Hooks as approval gates」]

git pre-commit / pre-push / post-merge **不是** Claude Code 文档里的 hook 模型。官方仓库 `anthropics/claude-cookbooks` 的 CLAUDE.md 写的是 `uv run pre-commit install`，那是 **Python 生态 pre-commit 框架**（format/lint/notebook），不是「按 git 事件提示更新某份产品文档」。

若 `project hooks` 要对齐官方：应部署 **`.claude/settings.json` 的 Claude Code hooks**，而不是 `.githooks/{pre-commit,pre-push}`。git 侧最多对应 playbook 说的「commit / PR 跑重检查」。

### 4. 公开仓库落地

- `anthropics/claude-cookbooks` 根 `CLAUDE.md`：Quick Start、Development Commands、Code Style、Git Workflow、Key Rules、Slash Commands、Project Structure。并写明安装 **pre-commit** 做 format/lint。无 AGENTS.md / CHANGELOG 门禁 / ROADMAP / 六态。[实证: gh api contents CLAUDE.md, blob 35f2eec]
- `anthropics/skills`：`skills/*/SKILL.md` + `template/SKILL.md`，符合「政策写成 skill」而非根 CLAUDE.md 膨胀。
- 对 `owner:anthropics filename:plan.md` / `REVIEW.md` 的 code search 为 `[]`：playbook 里的 `intent.md`/`spec.md`/`plan.md`/`REVIEW.md` 是 **流程产物模板**，不是 Anthropic 每个公开仓都检入的固定根文件。

## 事实源

| 类型 | 定位 | 日期 | 对应需求 | 提供了什么 |
|------|------|------|----------|------------|
| web | https://claude.com/blog/the-ai-native-sdlc-playbook | 2026-08-21 | 1,2,3 | 六阶段产物：intent/spec/plan/CLAUDE.md/skills/REVIEW.md；hook 分 build 护栏 vs deploy 批准门；commit/PR 放重检查 |
| web | https://code.claude.com/docs/en/memory.md | 拉正文当日文档 | 1,2 | CLAUDE.md 层级、200 行、@import、不读 AGENTS.md、CLAUDE.local.md gitignore、/doctor |
| web | https://code.claude.com/docs/en/features-overview | 拉正文当日文档 | 1,2,3 | CLAUDE.md vs rules vs skill vs hook；hook 才是确定性 |
| web | https://code.claude.com/docs/en/claude-directory | 拉正文当日文档 | 1 | 项目树：CLAUDE.md、.claude/rules、skills、agents、settings.json |
| web | https://code.claude.com/docs/en/hooks-guide | 拉正文当日文档 | 3 | PreToolUse/PostToolUse/Stop/FileChanged 等；exit 2 拦截 |
| github | anthropics/claude-cookbooks CLAUDE.md @ 35f2eec | 检索日 | 4 | 官方仓 CLAUDE.md 实样 + pre-commit install |
| github | anthropics/skills `skills/*/SKILL.md` | 检索日 | 1,4 | skill 作为可分发政策单元 |
| x | 无 @AnthropicAI 命中本次关键词 | — | — | 见缺口 |

## 缺口

- **X**：`from:AnthropicAI (CLAUDE.md OR intent.md OR AI-native SDLC)` 无结果。语义搜索只命中社区转述官方 skill 指南，不当成规范源。
- **intent.md / plan.md / REVIEW.md**：playbook 有完整模板，Anthropic 公开 code search 未找到同名根文件；不能声称「官方仓家家都有」。
- **git hook 提示更新文档**：官方未给出「pre-commit → CHANGELOG」这类映射。
- 未拉 https://claude.com/blog/how-anthropic-secures-its-ai-native-software-development-lifecycle 全文（playbook 仅链接）；安全向 hook 细节不在本报告展开。

## 对 `project` CLI 的含义（供你拍板，本轮不改代码）

对照当前实现（CoreSkills 五类元文件 + 六态 + git pre-commit 提示 CHANGELOG）：

| 当前实现 | 与官方 SDLC |
|----------|-------------|
| 强制 AGENTS.md + CLAUDE.md 一行桥接 | 官方核心是 **CLAUDE.md 正文**；AGENTS.md 仅多工具时 `@import` |
| README 七段式、docs 地图、CHANGELOG、ROADMAP | 官方不把这些当 agent 元文件 |
| 六态 | 非 Anthropic |
| git `pre-commit`/`pre-push`/`post-merge` 提示文档 | 官方 hook 是 **Claude Code 事件**；重检查在 commit/PR |

若要对齐官方，结构检查对象大致是：`CLAUDE.md`（或 `.claude/CLAUDE.md`）+ 可选 `REVIEW.md` + `.claude/rules`/`skills`/`agents`；健康度是行数、Commands 段、过时（错误重复仍未写入）；hook 部署 `.claude/settings.json` 的 PreToolUse/PostToolUse/Stop，而不是 `.githooks`。阶段产物 `intent.md`/`spec.md`/`plan.md` 是**变更工件**，适合「有变更时检查链是否断」，不适合「每个仓根必须有一份」。
