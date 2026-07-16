"""机器人账号与消息发送者识别工具。"""

from __future__ import annotations

from typing import Any, Iterable


PLATFORM_ALIASES = {
    "onebot": "qq",
    "napcat": "qq",
}


def normalize_token(value: Any) -> str:
    """把平台、账号等标识转换为可比较文本。"""

    return str(value or "").strip().lower()


def normalize_platform(value: Any) -> str:
    """归一化常见平台别名。"""

    platform = normalize_token(value)
    return PLATFORM_ALIASES.get(platform, platform)


def parse_account_spec(value: Any) -> tuple[str, str] | None:
    """解析 ``账号`` 或 ``平台:账号`` 配置。"""

    raw = str(value or "").strip()
    if not raw:
        return None
    if ":" not in raw:
        return "*", normalize_token(raw)
    platform, account = raw.split(":", 1)
    normalized_account = normalize_token(account)
    if not normalized_account:
        return None
    return normalize_platform(platform) or "*", normalized_account


def extract_sender(message: Any) -> tuple[str, str]:
    """从 MaiBot 序列化消息中提取平台和发送者账号。"""

    if not isinstance(message, dict):
        return "", ""
    message_info = message.get("message_info")
    message_info = message_info if isinstance(message_info, dict) else {}
    user_info = message_info.get("user_info")
    user_info = user_info if isinstance(user_info, dict) else {}
    user_id = user_info.get("user_id", message.get("user_id", ""))
    return normalize_platform(message.get("platform")), normalize_token(user_id)


def sender_matches_accounts(message: Any, account_specs: Iterable[Any]) -> bool:
    """判断消息发送者是否命中机器人账号配置。"""

    platform, user_id = extract_sender(message)
    if not user_id:
        return False
    for value in account_specs:
        parsed = parse_account_spec(value)
        if parsed is None:
            continue
        configured_platform, configured_account = parsed
        if configured_account != user_id:
            continue
        if configured_platform in {"*", platform}:
            return True
        if {configured_platform, platform} <= {"qq", "webui"}:
            return True
    return False


def same_sender(first_message: Any, second_message: Any) -> bool:
    """判断两条消息是否来自同一平台账号。"""

    first_platform, first_user = extract_sender(first_message)
    second_platform, second_user = extract_sender(second_message)
    if not first_user or not second_user or first_user != second_user:
        return False
    if first_platform == second_platform:
        return True
    return {first_platform, second_platform} <= {"qq", "webui"}
