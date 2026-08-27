@AGENTS.md

# Claude Code

## Commands

- Init: `uv run project init`；`uv run workspace init`
- Check: `uv run project check .`
- Detect: `uv run workspace detect --json`
- Panes: `uv run workspace pane split right --agent claude`；`pane keys 1 enter`；`pane read 1`
- Tests: `uv run pytest`
- Hooks: `uv run project hooks install`（pre-push 扫描关键文档是否随代码更新）

Healthy check output starts with `OK:` or `Summary: 0 error`. Tests: `passed`.

## Conventions

- SDLC 文档在 `docs/sdlc/`（intent → spec → plan）和根目录 `REVIEW.md`。
- AGENTS.md 与本文件并存：硬规则只写 AGENTS.md。
- 通用说明写 `.agents/skills/<name>/SKILL.md`（跨端）；不要 `.claude/rules/`。
- 根目录 `uv run`，不要 `cd packages/`。

## Architecture

- `packages/project/`：`project` CLI（结构检查 + 文档健康度 + git hook）
- `packages/workspace/`：`workspace` CLI（wt/herdr 检测；同一窗口 split/`--agent`/swap/resize/count/read/text/keys/close；`.workspace/inbox`）
- `docs/research/`：wt-cli、wt-windows、pane-color、herdr-pane-identity（窗格行为的依据）
- `docs/sdlc/`：SDLC 标准结构；`changes/<短名>/` 是单次变更产物
- `.agents/skills/` 与 `.claude/skills/`：`project init` / `workspace init` 各写一份独立拷贝

## Things Claude gets wrong

- 不要把 CLAUDE.md 收成只剩一行 `@AGENTS.md`。
- 不要建 `.claude/rules/`；路径提示走 git hook。
- 实现若偏离 `plan.md`，同一 commit 改 plan，不要只改代码。
- `wt -w 0` 是最近使用窗口，不是本格所在窗口；关格/发键必须 SetFocus 到目标 TermControl，禁止裸 `focus-pane` 再 Ctrl+Shift+W。
- 不要调用不存在的 wt 子命令（`close-pane` / `resize-pane` / `send-keys`），会弹 Help 框。

## Verifying your work

- `uv run project check .`（0 error）
- `uv run pytest`（all passed）
- 有进行中的 `docs/sdlc/changes/<短名>/` 时，对照 plan.md 的 Proof
