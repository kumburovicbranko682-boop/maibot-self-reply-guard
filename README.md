# 机器人自回复硬拦截插件

[![MaiBot](https://img.shields.io/badge/MaiBot-1.0.6%2B-blue)](https://github.com/Mai-with-u/MaiBot)
[![SDK](https://img.shields.io/badge/maibot--plugin--sdk-2.5.4%2B-green)](https://github.com/Mai-with-u/MaiBot)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

面向 MaiBot `v1.0.6+` 的独立修复插件。它不依赖提示词劝阻模型，而是在程序执行链上直接阻断「机器人回复自己的历史消息」。

插件 ID：`github.kumburovicbranko682-boop.self-reply-guard`

仓库：https://github.com/kumburovicbranko682-boop/maibot-self-reply-guard

## 兼容性

| 项目 | 要求 |
|------|------|
| MaiBot | `1.0.6` ~ `1.99.99` |
| maibot-plugin-sdk | `2.5.4` ~ `2.99.99` |

## 为什么能真正阻断

插件完全通过 MaiBot 官方 Hook 工作，使用四层防线：

1. `maisaka.planner.after_response`：发现 `reply` 的 `msg_id` 指向机器人自身消息时，直接从 `tool_calls` 删除该调用
2. `maisaka.replyer.before_request`：查询漏过前置过滤的 Replyer 目标并缓存发送者身份
3. `maisaka.replyer.after_response`：对命中目标强制写回 `response = ""`、`retry = false`，让 MaiBot 判定生成失败
4. `send_service.before_send`：真正发送前再次核验；命中配置账号或同发送者自回复时直接 `abort`

普通聊天消息没有 `reply_message_id`，QQ 群指令回复也不会携带目标消息，因此不会被粗糙策略误伤。

## 安装

1. 将本仓库复制到 MaiBot 的 `plugins` 目录
2. 保证目录中直接包含 `_manifest.json`、`plugin.py` 和 `config.toml`
3. 重启 MaiBot，确认日志出现「机器人自回复硬拦截插件已加载」

## 账号设置

默认自动读取 MaiBot 主配置：

```toml
[bot]
qq_account = "123456789"
```

多账号、旧账号消息或自动读取失败时，在本插件 `config.toml` 补充：

```toml
[identity]
bot_accounts = ["123456789", "qq:987654321"]
```

发送前兜底还会直接比较「目标消息发送者」和「本次出站消息发送者」，即使漏填账号也能拦住进入发送阶段的同账号自回复。

## QQ 群指令

以下指令只在 QQ 群内生效：

| 指令 | 说明 |
|------|------|
| `/自回复修复 状态` | 查看开关、账号数量和累计拦截 |
| `/自回复修复 统计` | 查看统计与最近五条记录 |
| `/自回复修复 开启` | 持久开启插件 |
| `/自回复修复 关闭` | 持久关闭插件 |
| `/自回复修复 跟随配置` | 取消 QQ 开关覆盖，重新使用 `config.toml` |
| `/自回复修复 账号` | 查看已识别账号 |
| `/自回复修复 清零` | 清空统计 |
| `/自回复修复 帮助` | 查看命令列表 |

状态和统计默认可公开查看；开关、账号和清零仅限管理员。管理员来自：

1. 本插件 `[security].administrators`
2. MaiBot 主配置 `plugin.permission`（默认继承）

## 状态文件

运行状态写入插件自身的 `data/state.json`，包括：

- QQ 指令设置的持久开关覆盖
- Planner 前置过滤次数
- Replyer 硬截断次数
- 发送前兜底次数
- 最近拦截时间与有限条历史记录

## 与官方补丁的区别

官方后续补丁主要修正 Replyer 提示文字：当回复目标是机器人自己时，把「回复麦麦」改成「补充说明你自己的发言」。它能降低模型误解，但不会禁止 Planner 选择自身消息，也不会取消已经生成的发送。

本插件不修改 MaiBot 源码，直接在 Host 已公开的 Hook 上删除危险 `reply` 工具调用，并再通过清空生成结果和发送前 `abort` 兜底。

## 故障排查

- 状态中「已识别机器人账号」为 0：检查主配置 `bot.qq_account`，或填写 `identity.bot_accounts`
- 日志持续出现「查询目标消息失败」：确认 Manifest 已授权 `message.get_by_id`，并检查消息数据库
- 多机器人共用一个群：把所有机器人 QQ 都加入 `identity.bot_accounts`
- 需要临时排查：使用 `/自回复修复 关闭`，恢复后再 `/自回复修复 开启`

## 许可证

MIT License
