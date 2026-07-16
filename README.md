# 机器人自回复硬拦截插件

[![MaiBot](https://img.shields.io/badge/MaiBot-0.0.0%2B%20(hooks%201.0.0--pre%2B)-blue)](https://github.com/Mai-with-u/MaiBot)
[![SDK](https://img.shields.io/badge/maibot--plugin--sdk-2.3%2B-green)](https://github.com/Mai-with-u/MaiBot)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

面向 MaiBot 的独立修复插件。它不依赖提示词劝阻模型，而是在程序执行链上直接阻断「机器人回复自己的历史消息」。

插件 ID：`github.kumburovicbranko682-boop.self-reply-guard`

仓库：https://github.com/kumburovicbranko682-boop/maibot-self-reply-guard

## 兼容性（已读官方源码）

| 项目 | 声明范围 | 实际硬拦截能力 |
|------|----------|----------------|
| MaiBot Host | `0.0.0` ~ `1.99.99` | **需要** `1.0.0-pre.1` 及之后（含 rc / 正式版） |
| maibot-plugin-sdk | `2.3.0` ~ `2.99.99` | 与 `1.0.0-pre.1` 对齐 |

说明：

- 官方仓库**没有** `0.0.x` 标签；公开最早标签约 `0.5.8-alpha`。
- `0.5`～`0.12` 使用旧版 `BasePlugin` 插件体系，**没有**本插件依赖的四层命名 Hook，无法做同等硬拦截。
- 从 [`1.0.0-pre.1`](https://github.com/Mai-with-u/MaiBot) 起，源码中已存在：
  - `maisaka.planner.after_response`
  - `maisaka.replyer.before_request`
  - `maisaka.replyer.after_response`
  - `send_service.before_send`
- Host 版本比较会把 `1.0.0-pre.*` / `1.0.0-rc.*` 归一为 `1.0.0`。
- Manifest 声明 `0.0.0` 是为了避免异常/自定义版本号被误拒；真正拦截仍依赖上述 Hook。

已核验标签：`1.0.0-pre.1`、`1.0.0-rc.1`、`1.0.0`、`1.0.1`、`1.0.6`、`1.0.9`、`1.0.12`。

## 配置容错

旧 `config.toml` 缺节、缺字段、缺少 `plugin.config_version`、类型写错时：

- 自动按默认骨架补齐
- 校验失败回退完整默认配置
- **不会因为少字段而拒绝加载插件**

最小可用配置示例：

```toml
[plugin]
enabled = true
```

## 为什么能真正阻断

1. `maisaka.planner.after_response`：删除指向机器人自身消息的 `reply` 工具调用
2. `maisaka.replyer.before_request`：识别并缓存自回复目标
3. `maisaka.replyer.after_response`：强制 `response=""`、`retry=false`
4. `send_service.before_send`：发送前 `abort`

## 安装

1. 复制到 MaiBot `plugins` 目录（建议目录名 `self_reply_guard`）
2. 保证根目录有 `_manifest.json`、`plugin.py`、`config.toml`
3. 重启 MaiBot

## 账号设置

自动读取（按顺序）：`bot.qq_account` / `bot.account` / `bot.user_id` / `bot.qq`

也可手动：

```toml
[identity]
bot_accounts = ["123456789", "qq:987654321"]
```

## QQ 群指令

| 指令 | 说明 |
|------|------|
| `/自回复修复 状态` | 查看开关与累计拦截 |
| `/自回复修复 统计` | 查看统计与近期记录 |
| `/自回复修复 开启` / `关闭` | 持久开关 |
| `/自回复修复 跟随配置` | 取消 QQ 覆盖 |
| `/自回复修复 账号` | 查看账号 |
| `/自回复修复 清零` | 清空统计 |

## 开发验证

```powershell
$env:PYTHONPATH = (Resolve-Path ..).Path
# 或把本目录 junction/symlink 为 self_reply_guard 后：
python -m pytest tests -v
```

## 许可证

MIT License
