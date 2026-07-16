"""0.x 兼容版纯函数（无 MaiBot 源码依赖，便于单测）。"""

from __future__ import annotations

from typing import Any, List


def normalize_token(value: Any) -> str:
    return str(value or "").strip().lower()


def as_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if "," in text:
            return [item.strip() for item in text.split(",") if item.strip()]
        return [text]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def extract_reply_message_id(message: Any) -> str:
    if message is None:
        return ""
    segments = getattr(message, "message_segments", None) or []
    for segment in segments:
        seg_type = getattr(segment, "type", None)
        seg_data = getattr(segment, "data", None)
        if seg_type is None and isinstance(segment, dict):
            seg_type = segment.get("type")
            seg_data = segment.get("data")
        if normalize_token(seg_type) != "reply":
            continue
        reply_id = str(seg_data or "").strip()
        if reply_id:
            return reply_id
    additional = getattr(message, "additional_data", None)
    additional = additional if isinstance(additional, dict) else {}
    for key in ("reply_message_id", "reply_to_message_id", "msg_id"):
        reply_id = str(additional.get(key) or "").strip()
        if reply_id:
            return reply_id
    return ""


def account_matches(user_id: Any, platform: Any, configured: List[str]) -> bool:
    uid = normalize_token(user_id)
    plat = normalize_token(platform)
    if not uid:
        return False
    for item in configured:
        raw = str(item or "").strip()
        if not raw:
            continue
        if ":" in raw:
            cfg_platform, cfg_account = raw.split(":", 1)
            cfg_platform = normalize_token(cfg_platform)
            cfg_account = normalize_token(cfg_account)
            if cfg_account != uid:
                continue
            if cfg_platform in {"", "*", plat}:
                return True
            if {cfg_platform, plat} <= {"qq", "webui"}:
                return True
        elif normalize_token(raw) == uid:
            return True
    return False
