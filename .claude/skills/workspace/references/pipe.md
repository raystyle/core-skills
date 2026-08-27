# 文件信箱

目录（相对项目根）：

```
.workspace/inbox/   待收
.workspace/seen/    listen 消费后移到这里
```

每条消息一个 `.txt`。`send` 先写临时文件再 rename，避免 listen 读到半截。

```
# 其它进程 / 脚本
uv run workspace pipe send "hello from script"
echo more | uv run workspace pipe send

# agent 后台监听（一直跑，打印到 stdout）
uv run workspace pipe listen

# 清掉当前积压然后退出
uv run workspace pipe listen --timeout 0

# 等到一条就退出
uv run workspace pipe listen --once
```

Claude Code 或其它 agent 把 `workspace pipe listen` 放到后台，就能接到别的进程送来的文本。`--root` 指定项目根，默认当前目录。
