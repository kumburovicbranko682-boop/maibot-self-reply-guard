"""MaiBot 机器人自回复硬拦截插件。"""

from __future__ import annotations

from pathlib import Path
from time import monotonic
from typing import Any

import asyncio
import re

from maibot_sdk import Command, HookHandler, MaiBotPlugin, ON_BOT_CONFIG_RELOAD
from maibot_sdk.types import ErrorPolicy, HookMode, HookOrder

from .config import CONFIG_VERSION, SelfReplyGuardConfig
from .identity import (
    normalize_platform,
    normalize_token,
    same_sender,
    sender_matches_accounts,
)
from .storage import atomic_write_json, default_state, load_state, now_text


class SelfReplyGuardPlugin(MaiBotPlugin):
    """阻断 MaiBot 对自身历史消息生成并发送回复。"""

    config_model = SelfReplyGuardConfig
    config_reload_subscriptions = {ON_BOT_CONFIG_RELOAD}

    def __init__(self) -> None:
        super().__init__()
        self._state_path: Path | None = None
        self._state: dict[str, Any] = default_state()
        self._state_lock = asyncio.Lock()
        self._cache_lock = asyncio.Lock()
        self._target_cache: dict[tuple[str, str], tuple[bool, float]] = {}
        self._runtime_accounts: tuple[str, ...] = ()

    def get_components(self) -> list[dict[str, Any]]:
        """收集组件并兼容 SDK 扩展元数据结构。"""

        components = super().get_components()
        for component in components:
            metadata = component.get("metadata")
            if not isinstance(metadata, dict):
                continue
            extension_metadata = metadata.pop("metadata", None)
            if isinstance(extension_metadata, dict):
                metadata.update(extension_metadata)
        return components

    async def on_load(self) -> None:
        """加载统计状态和机器人运行账号。"""

        data_dir = self._resolve_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        self._state_path = data_dir / "state.json"
        try:
            self._state = load_state(self._state_path)
        except (OSError, ValueError) as error:
            self.ctx.logger.error("读取自回复拦截状态失败，已使用空白状态：%s", error)
            self._state = default_state()
        await self._refresh_runtime_accounts()
        if self.config.plugin.config_version != CONFIG_VERSION:
            self.ctx.logger.warning(
                "插件配置版本为 %s，当前代码版本为 %s",
                self.config.plugin.config_version,
                CONFIG_VERSION,
            )
        self.ctx.logger.info(
            "机器人自回复硬拦截插件已加载，当前状态：%s",
            "开启" if self._is_enabled() else "关闭",
        )

    async def on_unload(self) -> None:
        """完成插件卸载。"""

        self.ctx.logger.info("机器人自回复硬拦截插件已卸载")

    async def on_config_update(
        self, scope: str, config_data: dict[str, Any], version: str
    ) -> None:
        """在插件或主配置更新后刷新机器人账号。"""

        del config_data, version
        if scope in {"self", "bot"}:
            await self._refresh_runtime_accounts()
            async with self._cache_lock:
                self._target_cache.clear()

    @Command(
        "self_reply_guard",
        description="在 QQ 群查看和控制机器人自回复硬拦截",
        pattern=r"^(?:/自回复修复|/自回复拦截|/selfreply)(?:\s+(?P<args>[\s\S]*))?\s*$",
        timeout_ms=15000,
    )
    async def handle_guard_command(
        self,
        stream_id: str = "",
        group_id: str = "",
        platform: str = "",
        user_id: str = "",
        matched_groups: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> tuple[bool, str, bool]:
        """处理 QQ 群管理指令。"""

        if normalize_platform(platform) != "qq" or not str(group_id or "").strip():
            return await self._command_reply(
                stream_id, False, "该指令仅支持在 QQ 群内使用。"
            )
        arguments = self._extract_arguments(matched_groups, kwargs)
        action = normalize_token(arguments.split(maxsplit=1)[0] if arguments else "")
        administrator = await self._is_administrator(platform, user_id)

        if action in {"", "状态", "status", "统计", "stats"}:
            if not administrator and not self.config.security.allow_public_status:
                return await self._command_reply(
                    stream_id, False, "你没有权限查看拦截状态。"
                )
            text = self._status_text(include_history=action in {"统计", "stats"})
            return await self._command_reply(stream_id, True, text)
        if action in {"帮助", "help", "?"}:
            return await self._command_reply(stream_id, True, self._help_text())
        if not administrator:
            return await self._command_reply(
                stream_id, False, "该操作仅限插件管理员。"
            )
        if action in {"开启", "启用", "on", "enable"}:
            await self._set_enabled_override(True)
            return await self._command_reply(
                stream_id, True, "自回复硬拦截已开启，并已持久保存。"
            )
        if action in {"关闭", "停用", "off", "disable"}:
            await self._set_enabled_override(False)
            return await self._command_reply(
                stream_id, True, "自回复硬拦截已关闭，并已持久保存。"
            )
        if action in {"跟随配置", "重置开关", "配置", "default"}:
            await self._set_enabled_override(None)
            return await self._command_reply(
                stream_id,
                True,
                "已取消 QQ 开关覆盖，当前跟随 config.toml。",
            )
        if action in {"清零", "清空统计", "reset"}:
            await self._reset_statistics()
            return await self._command_reply(stream_id, True, "拦截统计已清零。")
        if action in {"账号", "accounts", "account"}:
            return await self._command_reply(
                stream_id, True, self._accounts_text()
            )
        return await self._command_reply(
            stream_id, False, "未知子命令。发送 /自回复修复 帮助 查看用法。"
        )

    @HookHandler(
        "maisaka.planner.after_response",
        name="filter_self_reply_tool_calls",
        description="在 Planner 工具调用执行前删除指向机器人自身消息的 reply 调用",
        mode=HookMode.BLOCKING,
        order=HookOrder.LATE,
        timeout_ms=5000,
        error_policy=ErrorPolicy.SKIP,
    )
    async def filter_self_reply_tool_calls(self, **kwargs: Any) -> dict[str, Any]:
        """在 Replyer 启动前移除 Planner 产生的自回复工具调用。"""

        if not self._is_enabled():
            return {"action": "continue"}
        session_id = str(kwargs.get("session_id") or "").strip()
        tool_calls = kwargs.get("tool_calls")
        if not session_id or not isinstance(tool_calls, list) or not tool_calls:
            return {"action": "continue"}

        filtered_tool_calls: list[Any] = []
        blocked_message_ids: list[str] = []
        for tool_call in tool_calls:
            reply_message_id = self._reply_target_from_tool_call(tool_call)
            if not reply_message_id:
                filtered_tool_calls.append(tool_call)
                continue
            if not await self._target_is_configured_bot(
                session_id, reply_message_id
            ):
                filtered_tool_calls.append(tool_call)
                continue
            blocked_message_ids.append(reply_message_id)

        if not blocked_message_ids:
            return {"action": "continue"}
        modified = dict(kwargs)
        modified["tool_calls"] = filtered_tool_calls
        for reply_message_id in blocked_message_ids:
            await self._record_block(
                layer="planner",
                session_id=session_id,
                reply_message_id=reply_message_id,
            )
        self.ctx.logger.warning(
            "Planner 自回复工具调用已删除：session=%s targets=%s",
            session_id,
            ",".join(blocked_message_ids),
        )
        return {"action": "continue", "modified_kwargs": modified}

    @HookHandler(
        "maisaka.replyer.before_request",
        name="identify_self_reply_target",
        description="在 Replyer 请求前识别目标是否为机器人自己的消息",
        mode=HookMode.BLOCKING,
        order=HookOrder.EARLY,
        timeout_ms=5000,
        error_policy=ErrorPolicy.SKIP,
    )
    async def identify_reply_target(self, **kwargs: Any) -> dict[str, Any]:
        """提前识别并缓存自回复目标。"""

        if not self._is_enabled():
            return {"action": "continue"}
        session_id = str(kwargs.get("session_id") or "").strip()
        reply_message_id = str(kwargs.get("reply_message_id") or "").strip()
        if not session_id or not reply_message_id:
            return {"action": "continue"}
        if await self._target_is_configured_bot(session_id, reply_message_id):
            self.ctx.logger.warning(
                "检测到 Replyer 选择机器人自身消息，将在模型返回后硬截断：session=%s target=%s",
                session_id,
                reply_message_id,
            )
        return {"action": "continue"}

    @HookHandler(
        "maisaka.replyer.after_response",
        name="erase_self_reply_response",
        description="把针对机器人自身消息生成的 Replyer 响应强制清空",
        mode=HookMode.BLOCKING,
        order=HookOrder.LATE,
        timeout_ms=5000,
        error_policy=ErrorPolicy.SKIP,
    )
    async def erase_self_reply_response(self, **kwargs: Any) -> dict[str, Any]:
        """硬清空自回复文本，让 Reply 工具判定生成失败且不发送。"""

        if not self._is_enabled():
            return {"action": "continue"}
        session_id = str(kwargs.get("session_id") or "").strip()
        reply_message_id = str(kwargs.get("reply_message_id") or "").strip()
        if not session_id or not reply_message_id:
            return {"action": "continue"}
        if not await self._target_is_configured_bot(session_id, reply_message_id):
            return {"action": "continue"}
        modified = dict(kwargs)
        modified["response"] = ""
        modified["retry"] = False
        await self._record_block(
            layer="replyer",
            session_id=session_id,
            reply_message_id=reply_message_id,
        )
        self.ctx.logger.warning(
            "已硬截断机器人自回复：session=%s target=%s",
            session_id,
            reply_message_id,
        )
        return {"action": "continue", "modified_kwargs": modified}

    @HookHandler(
        "send_service.before_send",
        name="abort_self_reply_before_send",
        description="发送前再次核验引用目标并取消机器人自回复",
        mode=HookMode.BLOCKING,
        order=HookOrder.LATE,
        timeout_ms=5000,
        error_policy=ErrorPolicy.SKIP,
    )
    async def abort_self_reply_before_send(self, **kwargs: Any) -> dict[str, Any]:
        """使用配置账号和出站消息身份进行最后一道精确拦截。"""

        if not self._is_enabled():
            return {"action": "continue"}
        reply_message_id = str(kwargs.get("reply_message_id") or "").strip()
        if not reply_message_id:
            return {"action": "continue"}
        outbound_message = kwargs.get("message")
        session_id = self._message_session_id(outbound_message) or str(
            kwargs.get("stream_id") or ""
        ).strip()
        target_message = await self._get_target_message(session_id, reply_message_id)
        if target_message is None:
            return {"action": "continue"}
        configured_match = self._message_is_configured_bot(target_message)
        outbound_identity_match = same_sender(target_message, outbound_message)
        if not configured_match and not outbound_identity_match:
            await self._remember_target(session_id, reply_message_id, False)
            return {"action": "continue"}
        await self._remember_target(session_id, reply_message_id, True)
        await self._record_block(
            layer="send",
            session_id=session_id,
            reply_message_id=reply_message_id,
        )
        self.ctx.logger.warning(
            "发送前已取消机器人自回复：session=%s target=%s",
            session_id,
            reply_message_id,
        )
        return {"action": "abort"}

    def _is_enabled(self) -> bool:
        override = self._state.get("enabled_override")
        if isinstance(override, bool):
            return override
        return bool(self.config.plugin.enabled)

    async def _target_is_configured_bot(
        self, session_id: str, reply_message_id: str
    ) -> bool:
        cached = await self._cached_target(session_id, reply_message_id)
        if cached is not None:
            return cached
        message = await self._get_target_message(session_id, reply_message_id)
        if message is None:
            return False
        matched = self._message_is_configured_bot(message)
        await self._remember_target(session_id, reply_message_id, matched)
        return matched

    async def _get_target_message(
        self, session_id: str, reply_message_id: str
    ) -> dict[str, Any] | None:
        try:
            message = await self.ctx.message.get_by_id(
                reply_message_id,
                stream_id=session_id,
                include_binary_data=False,
            )
        except Exception as error:
            self.ctx.logger.warning(
                "查询自回复目标消息失败，已安全放行：session=%s target=%s error=%s",
                session_id,
                reply_message_id,
                error,
            )
            return None
        return message if isinstance(message, dict) else None

    def _message_is_configured_bot(self, message: dict[str, Any]) -> bool:
        accounts = (*self.config.identity.bot_accounts, *self._runtime_accounts)
        return sender_matches_accounts(message, accounts)

    async def _cached_target(
        self, session_id: str, reply_message_id: str
    ) -> bool | None:
        key = (session_id, reply_message_id)
        current = monotonic()
        async with self._cache_lock:
            self._purge_cache(current)
            cached = self._target_cache.get(key)
            return None if cached is None else cached[0]

    async def _remember_target(
        self, session_id: str, reply_message_id: str, is_self: bool
    ) -> None:
        if not reply_message_id:
            return
        expires_at = monotonic() + int(self.config.plugin.cache_seconds)
        async with self._cache_lock:
            self._purge_cache(monotonic())
            self._target_cache[(session_id, reply_message_id)] = (is_self, expires_at)

    def _purge_cache(self, current: float) -> None:
        expired = [
            key for key, (_, expires_at) in self._target_cache.items()
            if expires_at <= current
        ]
        for key in expired:
            self._target_cache.pop(key, None)

    async def _refresh_runtime_accounts(self) -> None:
        accounts: list[str] = []
        if self.config.plugin.auto_read_bot_account:
            try:
                qq_account = normalize_token(
                    await self.ctx.config.get("bot.qq_account", "")
                )
            except Exception as error:
                self.ctx.logger.warning("读取 bot.qq_account 失败：%s", error)
                qq_account = ""
            if qq_account and qq_account != "0":
                accounts.append(f"qq:{qq_account}")
        self._runtime_accounts = tuple(accounts)

    async def _record_block(
        self, *, layer: str, session_id: str, reply_message_id: str
    ) -> None:
        event = {
            "time": now_text(),
            "layer": layer,
            "session_id": session_id,
            "reply_message_id": reply_message_id,
        }
        async with self._state_lock:
            self._state["total_blocked"] = int(self._state.get("total_blocked", 0)) + 1
            counter_key = {
                "planner": "planner_blocked",
                "replyer": "replyer_blocked",
                "send": "send_blocked",
            }[layer]
            self._state[counter_key] = int(self._state.get(counter_key, 0)) + 1
            self._state["last_blocked_at"] = event["time"]
            self._state["last_event"] = event
            history = self._state.get("history")
            history = list(history) if isinstance(history, list) else []
            history_limit = int(self.config.storage.history_limit)
            self._state["history"] = (
                (history + [event])[-history_limit:] if history_limit > 0 else []
            )
            self._persist_state()

    async def _set_enabled_override(self, value: bool | None) -> None:
        async with self._state_lock:
            self._state["enabled_override"] = value
            self._persist_state()

    async def _reset_statistics(self) -> None:
        async with self._state_lock:
            for key in (
                "total_blocked",
                "planner_blocked",
                "replyer_blocked",
                "send_blocked",
            ):
                self._state[key] = 0
            self._state["last_blocked_at"] = ""
            self._state["last_event"] = {}
            self._state["history"] = []
            self._persist_state()

    def _persist_state(self) -> None:
        if self._state_path is not None:
            atomic_write_json(self._state_path, self._state)

    @staticmethod
    def _resolve_data_dir() -> Path:
        return Path(__file__).resolve().parent / "data"

    async def _is_administrator(self, platform: str, user_id: str) -> bool:
        normalized_user = normalize_token(user_id)
        normalized_platform = normalize_platform(platform)
        if not normalized_user:
            return False
        candidates = {normalized_user, f"{normalized_platform}:{normalized_user}"}
        administrators = {
            normalize_token(item)
            for item in self.config.security.administrators
            if normalize_token(item)
        }
        if candidates & administrators:
            return True
        if not self.config.security.inherit_plugin_management_permissions:
            return False
        try:
            inherited = await self.ctx.config.get("plugin.permission", [])
        except Exception:
            return False
        inherited = inherited if isinstance(inherited, list) else []
        return bool(
            candidates
            & {normalize_token(item) for item in inherited if normalize_token(item)}
        )

    def _status_text(self, *, include_history: bool) -> str:
        override = self._state.get("enabled_override")
        source = "QQ群持久开关" if isinstance(override, bool) else "config.toml"
        lines = [
            "机器人自回复硬拦截",
            f"状态：{'开启' if self._is_enabled() else '关闭'}（来源：{source}）",
            f"已识别机器人账号：{self._configured_account_count()} 个",
            f"累计拦截：{int(self._state.get('total_blocked', 0))} 次",
            f"Planner 前置过滤：{int(self._state.get('planner_blocked', 0))} 次",
            f"Replyer 硬截断：{int(self._state.get('replyer_blocked', 0))} 次",
            f"发送前兜底：{int(self._state.get('send_blocked', 0))} 次",
            f"最近拦截：{self._state.get('last_blocked_at') or '暂无'}",
        ]
        if include_history:
            history = self._state.get("history")
            history = history if isinstance(history, list) else []
            lines.append("近期记录：")
            if not history:
                lines.append("暂无")
            else:
                for event in history[-5:]:
                    if not isinstance(event, dict):
                        continue
                    lines.append(
                        f"- {event.get('time', '')} [{event.get('layer', '')}] "
                        f"{event.get('reply_message_id', '')}"
                    )
        return "\n".join(lines)

    def _accounts_text(self) -> str:
        accounts = [
            str(item).strip()
            for item in (*self.config.identity.bot_accounts, *self._runtime_accounts)
            if str(item).strip()
        ]
        if not accounts:
            return "当前未识别到机器人账号，请检查 bot.qq_account 或 identity.bot_accounts。"
        return "当前机器人账号：\n" + "\n".join(f"- {item}" for item in accounts)

    def _configured_account_count(self) -> int:
        accounts = {
            normalize_token(item)
            for item in (*self.config.identity.bot_accounts, *self._runtime_accounts)
            if normalize_token(item)
        }
        return len(accounts)

    async def _command_reply(
        self, stream_id: str, success: bool, text: str
    ) -> tuple[bool, str, bool]:
        if stream_id:
            await self.ctx.send.text(text, stream_id)
        return success, text, True

    @staticmethod
    def _message_session_id(message: Any) -> str:
        return (
            str(message.get("session_id") or "").strip()
            if isinstance(message, dict)
            else ""
        )

    @staticmethod
    def _reply_target_from_tool_call(tool_call: Any) -> str:
        if not isinstance(tool_call, dict):
            return ""
        function_info = tool_call.get("function")
        if isinstance(function_info, dict):
            function_name = function_info.get("name")
            arguments = function_info.get("arguments")
        else:
            function_name = tool_call.get("name")
            arguments = tool_call.get("arguments")
        if normalize_token(function_name) != "reply" or not isinstance(arguments, dict):
            return ""
        return str(arguments.get("msg_id") or "").strip()

    @staticmethod
    def _extract_arguments(
        matched_groups: dict[str, Any] | None, kwargs: dict[str, Any]
    ) -> str:
        if isinstance(matched_groups, dict) and isinstance(
            matched_groups.get("args"), str
        ):
            return str(matched_groups["args"]).strip()
        raw_text = str(kwargs.get("text") or "").strip()
        return re.sub(
            r"^(?:/自回复修复|/自回复拦截|/selfreply)\s*",
            "",
            raw_text,
            flags=re.IGNORECASE,
        ).strip()

    @staticmethod
    def _help_text() -> str:
        return "\n".join(
            [
                "自回复修复指令",
                "/自回复修复 状态",
                "/自回复修复 统计",
                "/自回复修复 开启",
                "/自回复修复 关闭",
                "/自回复修复 跟随配置",
                "/自回复修复 账号",
                "/自回复修复 清零",
            ]
        )


def create_plugin() -> SelfReplyGuardPlugin:
    """创建插件实例。"""

    return SelfReplyGuardPlugin()
