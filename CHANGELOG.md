# 更新日志

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
