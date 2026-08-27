# git pre-push 文档同步

只在 **推送** 时跑，不拦提交。改了代码、关键文档都没动 → stderr 打 `[提醒]`，**不拦截** `git push`。

```
uv run project hooks install
uv run project check --sync    # 相对上游手动扫一遍
```

关键文档（改了代码则应在同一批提交里出现至少一份）：

- `CHANGELOG.md`
- `CLAUDE.md`
- `AGENTS.md`
- `REVIEW.md`
- 或本次 `docs/sdlc/changes/<名>/{intent,spec,plan}.md`

跳过：`git push --no-verify`。
