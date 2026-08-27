# 检测

`workspace detect` 看**当前进程**在哪个复用器里，不是看机器上装了什么。

| OS | 期望 | 判定 |
|----|------|------|
| Windows | wt | `WT_SESSION` 或 `WT_PROFILE_ID` |
| Linux / macOS | herdr | `HERDR_ENV=1`、`HERDR_PANE_ID` 或 `HERDR_SOCKET_PATH` |

两边环境变量都有时，先跟 OS 期望走。Windows 上若没有 wt 标记但有 Herdr 变量，仍报 `mux=herdr`。

`--json` 给出 `os / expected / mux / inside / session / pane / bin / evidence`。不在复用器里时退出码 1。
