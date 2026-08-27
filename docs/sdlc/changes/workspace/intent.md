# Intent: workspace

Author: ray. Status: accepted.

## Problem

智能体不知道自己跑在 Windows Terminal 还是 Herdr 里，拆窗格要各写一套命令；进程之间也没有简单的文本通道，Claude Code 等没法后台收其它脚本的消息。

## Proposed outcome

`workspace` CLI + 项目级 skill（两份拷贝）：检测当前复用器、统一 split/list/focus/close、`.workspace/inbox` 消费式信箱。

## Affected users and systems

在 wt / herdr 里跑的 agent；需要给 agent 投递文本的脚本。

## Constraints

- Windows 检测 wt，Linux 检测 herdr。
- 窗格做到分割 + 列表/聚焦/关闭，不包含独立的 send/run 子命令。
- 信箱是目录文件，不是 OS named pipe / junction。
- `init` 与 `project` 一样装两份 skill。

## Open questions

无（已确认）。
