# 更新日志

## 1.3.1 - 2026-07-16

- 新增 `legacy_maibot_0x/`：面向 MaiBot 0.10–0.12 旧 `BasePlugin` 体系。
- 对照 0.12.3 源码，使用 `POST_SEND_PRE_PROCESS` + `intercept_message` 在发送前取消自回复。
- 主插件（1.0+）与旧版插件分目录安装，避免体系冲突。

## 1.3.0 - 2026-07-16

- 对照官方标签：无 `0.0.x`；`0.5`～`0.12` 为旧 `BasePlugin` 体系且无四层硬拦截 Hook；Hook 从 `1.0.0-pre.1`（SDK>=2.3.0）起可用。
- Manifest：`host_application.min_version` 放宽为 `0.0.0`，`sdk.min_version` 放宽为 `2.3.0`。
- 配置容错：缺节、缺字段、缺 `plugin.config_version`、类型错误时自动补齐或回退默认值，避免加载失败。
- 去掉易因脏配置触发的严格数值上下界校验，改为运行时钳制。
- 配置访问统一走 `_safe_config()`，避免配置未注入时崩溃。

## 1.2.0 - 2026-07-16

- 对照 MaiBot `1.0.0` / `1.0.1` / `1.0.6` / `1.0.9` / `1.0.12` 源码确认四层官方 Hook 稳定，将 Host 兼容下限放宽至 `1.0.0`。
- SDK 兼容下限放宽至 `2.5.3`（覆盖 MaiBot 1.0.0 自带 SDK）。
- 增强消息发送者识别与工具参数解析，兼容多版本消息结构。

## 1.1.1 - 2026-07-10

- 增加 SDK 2.5.4 Runner 要求的模块级 `create_plugin` 工厂函数。
- 状态文件改为保存在插件自身的 `data/state.json`。

## 1.1.0 - 2026-07-10

- 增加 `maisaka.planner.after_response` 前置 Hook。
- 保留 Replyer 空响应截断和发送前 abort 作为兼容兜底。

## 1.0.0 - 2026-07-10

- 首个正式版本：Replyer 截断 + 发送前 abort + QQ 群指令。
