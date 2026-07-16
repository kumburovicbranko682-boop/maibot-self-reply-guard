"""MaiBot 0.10–0.12 旧体系：发送前拦截机器人自回复。

安装：把本目录（legacy_maibot_0x）整体复制到 MaiBot 的 plugins 目录，
并确保目录名合法（建议 self_reply_guard_legacy）。不要与 1.0+ 版混装同一目录。
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Type

from src.chat.utils.utils import is_bot_self
from src.common.database.database_model import Messages
from src.common.logger import get_logger
from src.plugin_system.apis import database_api
from src.plugin_system.apis.plugin_register_api import register_plugin
from src.plugin_system.base.base_command import BaseCommand
from src.plugin_system.base.base_events_handler import BaseEventHandler
from src.plugin_system.base.base_plugin import BasePlugin
from src.plugin_system.base.component_types import ComponentInfo, EventType, MaiMessages
from src.plugin_system.base.config_types import ConfigField

from .helpers import account_matches, as_str_list, extract_reply_message_id, normalize_token

logger = get_logger("self_reply_guard_legacy")


class SelfReplyAbortHandler(BaseEventHandler):
    """在真正发送前取消“回复自己历史消息”的出站消息。"""

    event_type = EventType.POST_SEND_PRE_PROCESS
    handler_name = "self_reply_abort_before_send"
    handler_description = "发送前拦截机器人自回复"
    weight = 1000
    intercept_message = True

    async def execute(
        self, message: MaiMessages | None
    ) -> Tuple[bool, bool, Optional[str], None, Optional[MaiMessages]]:
        if not bool(self.get_config("plugin.enabled", True)):
            return True, True, None, None, message

        reply_message_id = extract_reply_message_id(message)
        if not reply_message_id:
            return True, True, None, None, message

        try:
            record = await database_api.db_get(
                Messages,
                filters={"message_id": reply_message_id},
                limit=1,
                single_result=True,
            )
        except Exception as error:
            logger.warning(f"{self.log_prefix} 查询引用消息失败，已放行: {error}")
            return True, True, None, None, message

        if not isinstance(record, dict):
            return True, True, None, None, message

        platform = (
            record.get("user_platform")
            or record.get("platform")
            or record.get("chat_info_user_platform")
            or ""
        )
        user_id = record.get("user_id") or record.get("chat_info_user_id") or ""
        configured = as_str_list(self.get_config("identity.bot_accounts", []))

        is_self = False
        try:
            is_self = bool(is_bot_self(str(platform), str(user_id)))
        except Exception as error:
            logger.debug(f"{self.log_prefix} is_bot_self 调用失败: {error}")

        if not is_self and configured:
            is_self = account_matches(user_id, platform, configured)

        if not is_self:
            return True, True, None, None, message

        logger.warning(
            f"{self.log_prefix} 已拦截自回复发送: reply_message_id={reply_message_id} "
            f"platform={platform} user_id={user_id}"
        )
        return True, False, "blocked self-reply", None, message


class SelfReplyStatusCommand(BaseCommand):
    """简单状态指令。"""

    command_name = "self_reply_guard_legacy_status"
    command_description = "查看 0.x 自回复拦截状态"
    command_pattern = r"^(?:/自回复修复|/自回复拦截|/selfreply)(?:\s+(?P<args>[\s\S]*))?\s*$"

    async def execute(self) -> Tuple[bool, Optional[str], int]:
        args = ""
        if isinstance(self.matched_groups, dict):
            args = str(self.matched_groups.get("args") or "").strip()
        action = normalize_token(args.split(maxsplit=1)[0] if args else "状态")

        enabled = bool(self.get_config("plugin.enabled", True))
        accounts = as_str_list(self.get_config("identity.bot_accounts", []))
        allow_public = bool(self.get_config("security.allow_public_status", True))

        user_id = ""
        try:
            user_id = str(self.message.message_info.user_info.user_id)  # type: ignore[union-attr]
        except Exception:
            user_id = ""

        administrators = {
            normalize_token(item)
            for item in as_str_list(self.get_config("security.administrators", []))
        }
        is_admin = (not administrators) or (normalize_token(user_id) in administrators) or any(
            normalize_token(user_id) and f"qq:{normalize_token(user_id)}" == item
            for item in administrators
        )

        if action in {"", "状态", "status", "帮助", "help"}:
            if not allow_public and not is_admin:
                text = "你没有权限查看拦截状态。"
                await self.send_text(text)
                return False, text, 2
            text = "\n".join(
                [
                    "自回复硬拦截（0.x 兼容版）",
                    f"状态：{'开启' if enabled else '关闭'}",
                    f"额外账号：{len(accounts)} 个",
                    "拦截点：POST_SEND_PRE_PROCESS",
                    "说明：此版本仅覆盖 MaiBot 0.10–0.12；1.0+ 请使用主插件目录。",
                ]
            )
            await self.send_text(text)
            return True, text, 2

        if action in {"开启", "on", "enable", "关闭", "off", "disable"}:
            text = "0.x 兼容版请在 config.toml 的 [plugin].enabled 修改开关后重载插件。"
            await self.send_text(text)
            return True, text, 2

        text = "未知子命令。发送 /自回复修复 状态 查看。"
        await self.send_text(text)
        return False, text, 2


@register_plugin
class SelfReplyGuardLegacyPlugin(BasePlugin):
    """MaiBot 0.10–0.12 自回复发送前拦截插件。"""

    plugin_name: str = "self_reply_guard_legacy"
    enable_plugin: bool = True
    dependencies: List[str] = []
    python_dependencies: List[str] = []
    config_file_name: str = "config.toml"

    config_section_descriptions = {
        "plugin": "插件开关",
        "identity": "额外机器人账号",
        "security": "指令权限",
    }

    config_schema: dict = {
        "plugin": {
            "enabled": ConfigField(type=bool, default=True, description="是否启用发送前自回复拦截"),
            "config_version": ConfigField(type=str, default="1.0.0", description="配置版本"),
        },
        "identity": {
            "bot_accounts": ConfigField(
                type=list,
                default=[],
                description="额外机器人账号，支持 123456 或 qq:123456",
            ),
        },
        "security": {
            "administrators": ConfigField(
                type=list,
                default=[],
                description="可查看状态的管理员 QQ；为空表示不额外限制",
            ),
            "allow_public_status": ConfigField(
                type=bool,
                default=True,
                description="是否允许普通成员查看状态",
            ),
        },
    }

    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        return [
            (SelfReplyAbortHandler.get_handler_info(), SelfReplyAbortHandler),
            (SelfReplyStatusCommand.get_command_info(), SelfReplyStatusCommand),
        ]
