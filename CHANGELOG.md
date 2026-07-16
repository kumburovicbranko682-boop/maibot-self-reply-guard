# 更新日志

## 1.2.0 - 2026-07-16

- 对照 MaiBot `1.0.0` / `1.0.1` / `1.0.6` / `1.0.9` / `1.0.12` 源码确认四层官方 Hook 稳定，将 Host 兼容下限放宽至 `1.0.0`。
- SDK 兼容下限放宽至 `2.5.3`（覆盖 MaiBot 1.0.0 自带 SDK）。
- 增强消息发送者识别：兼容顶层 `user_id`、嵌套 `user_info`、平台别名（onebot / napcat / llonebot / lagrange）。
- 增强 Planner `reply` 工具参数解析：兼容 JSON 字符串 arguments，以及 `msg_id` / `message_id` / `reply_message_id` 别名。
- Hook 入参兼容 `session_id` / `stream_id` 与多种 reply 目标字段名。
- `message.get_by_id` 调用兼容不同 SDK 签名；查询失败仍安全放行。
- 自动读取机器人账号时额外尝试 `bot.account` / `bot.user_id` / `bot.qq`。

## 1.1.1 - 2026-07-10

- 增加 SDK 2.5.4 Runner 要求的模块级 `create_plugin` 工厂函数。
- 状态文件改为保存在插件自身的 `data/state.json`，避免依赖后续 SDK 才提供的 `ctx.paths`。

## 1.1.0 - 2026-07-10

- 增加 `maisaka.planner.after_response` 前置 Hook。
- 在 `reply` 工具执行前查询 `msg_id`，直接删除指向机器人自身消息的工具调用。
- 保留 Replyer 空响应截断和发送前 abort 作为兼容兜底。
- 增加 Planner 前置过滤统计。

## 1.0.0 - 2026-07-10

- 兼容 MaiBot v1.0.6 与 maibot-plugin-sdk 2.5.4。
- 增加 Replyer 目标消息身份预识别。
- 增加 Replyer 响应强制清空，阻止生成结果进入发送流程。
- 增加发送前同账号与配置账号双重核验兜底。
- 增加 QQ 群开关、状态、统计、账号与清零指令。
- 增加原子状态持久化和近期拦截记录。
