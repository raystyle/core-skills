# Review instructions

对照本变更的 `docs/sdlc/changes/<短名>/` 下 intent / spec / plan。

## Passes

Run three passes and tag each finding:

- Bugs: logic errors, broken edge cases, regressions
- Security: injection, auth gaps, secrets in logs
- Compliance: the change matches spec.md, plan.md, and AGENTS.md hard rules

## What Important means

Reserve Important for findings that would break behavior, leak data, or breach a hard rule. Style and naming are nits.

## Cap the nits

Report at most five nits per review; summarize the rest as a count.

## Do not report

Generated files, lockfile-only noise, and anything `uv run pytest` / CI already enforces.
