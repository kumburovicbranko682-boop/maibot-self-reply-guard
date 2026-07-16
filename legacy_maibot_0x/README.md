# 自回复硬拦截 · MaiBot 0.10–0.12 兼容版

本目录是给 **MaiBot 0.10.1～0.12.x** 用的旧插件体系实现。

1.0+（含 `1.0.0-pre`）请使用仓库**根目录**主插件，不要装这个目录。

## 原理（已对照 0.12.3 源码）

`UniversalMessageSender.send_message` 在真正发送前会触发：

- `EventType.POST_SEND_PRE_PROCESS`

若事件处理器返回 `continue_processing=False`，发送会直接取消。

本插件订阅该事件（`intercept_message=True`），从出站消息的 `reply` 段取出被引用消息 ID，查库后用 `is_bot_self` / 配置账号判断是否在回复自己；命中则拦截。

## 安装

1. 复制本目录到 MaiBot `plugins/`（建议改名为 `self_reply_guard_legacy`）
2. 确认目录内有 `_manifest.json`、`plugin.py`、`config.toml`
3. 重启或热重载插件

## 配置

```toml
[plugin]
enabled = true

[identity]
bot_accounts = []  # 可选，额外账号

[security]
allow_public_status = true
```

## 指令

```text
/自回复修复 状态
```

## 限制

- 0.x **没有** 1.0+ 的 Planner/Replyer Hook，只能做发送前拦截
- 若发送路径不带 `reply` 段，或查库失败，会安全放行
- 与主插件（manifest v2）**不要**放在同一目录
