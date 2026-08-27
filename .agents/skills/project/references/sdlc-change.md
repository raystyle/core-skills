# 一次变更：intent → spec → plan

Anthropic AI-native SDLC 的阶段产物。不是仓根常驻一份，而是每次变更一套。

```
docs/sdlc/changes/<短名>/
  intent.md   ← Plan：问题 / 结果 / 约束 / 开放问题
  spec.md     ← Design：对着 intent + skills
  plan.md     ← Build：改哪些文件、顺序、风险、Proof
```

从 `docs/sdlc/templates/` 拷过去再填。

链规则（`project check` 强制）：

- 有 `spec.md` 必须已有 `intent.md`
- 有 `plan.md` 必须已有 `spec.md` 和 `intent.md`
- 实现若偏离 plan，同一 commit 改 `plan.md`

下一阶段只读上一阶段已提交的产物。
