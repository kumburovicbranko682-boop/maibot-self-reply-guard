"""机器人自回复硬拦截插件配置。"""

from __future__ import annotations

from typing import Any, ClassVar, Mapping

from maibot_sdk import Field, PluginConfigBase
from maibot_sdk.config import (
    build_plugin_default_config,
    merge_plugin_config_data,
    validate_plugin_config,
)


CONFIG_VERSION = "1.0.0"


class PluginSection(PluginConfigBase):
    """插件基础设置。"""

    __ui_label__: ClassVar[str] = "插件"
    __ui_icon__: ClassVar[str] = "shield-ban"
    __ui_order__: ClassVar[int] = 0

    enabled: bool = Field(default=True, description="是否启用自回复硬拦截。")
    auto_read_bot_account: bool = Field(
        default=True,
        description="自动读取 bot.qq_account 作为机器人 QQ。",
    )
    cache_seconds: int = Field(
        default=120,
        description="目标消息身份识别缓存秒数。",
    )
    config_version: str = Field(
        default=CONFIG_VERSION,
        description="配置结构版本。",
        json_schema_extra={"hidden": True, "disabled": True},
    )


class IdentitySection(PluginConfigBase):
    """机器人账号设置。"""

    __ui_label__: ClassVar[str] = "机器人账号"
    __ui_icon__: ClassVar[str] = "bot"
    __ui_order__: ClassVar[int] = 1

    bot_accounts: list[str] = Field(
        default_factory=list,
        description="额外机器人账号，支持 123456 或 qq:123456 格式。",
    )


class SecuritySection(PluginConfigBase):
    """QQ群指令权限。"""

    __ui_label__: ClassVar[str] = "权限"
    __ui_icon__: ClassVar[str] = "shield-check"
    __ui_order__: ClassVar[int] = 2

    administrators: list[str] = Field(
        default_factory=list,
        description="插件管理员，支持 QQ号 或 qq:QQ号。",
    )
    inherit_plugin_management_permissions: bool = Field(
        default=True,
        description="同时继承 bot_config.toml 中 plugin.permission 的管理员。",
    )
    allow_public_status: bool = Field(
        default=True,
        description="是否允许普通群成员查看运行状态和统计。",
    )


class StorageSection(PluginConfigBase):
    """状态记录设置。"""

    __ui_label__: ClassVar[str] = "记录"
    __ui_icon__: ClassVar[str] = "database"
    __ui_order__: ClassVar[int] = 3

    history_limit: int = Field(
        default=50,
        description="最多保存的近期拦截记录数；0 表示不保存明细。",
    )


class SelfReplyGuardConfig(PluginConfigBase):
    """插件完整配置。"""

    plugin: PluginSection = Field(default_factory=PluginSection)
    identity: IdentitySection = Field(default_factory=IdentitySection)
    security: SecuritySection = Field(default_factory=SecuritySection)
    storage: StorageSection = Field(default_factory=StorageSection)


def default_config_dict() -> dict[str, Any]:
    """导出完整默认配置字典。"""

    return build_plugin_default_config(SelfReplyGuardConfig)


def coerce_config_data(config_data: Mapping[str, Any] | None) -> tuple[dict[str, Any], bool]:
    """容错规范化配置：缺节、缺字段、缺 config_version、类型错误都不致命。

    SDK 的 ``normalize_plugin_config`` 会在缺少 ``plugin.config_version`` 时直接抛错；
    本函数先补齐默认骨架，再校验；校验失败则回退到完整默认配置。
    """

    default_config = default_config_dict()
    raw_config: dict[str, Any] = (
        dict(config_data) if isinstance(config_data, Mapping) else {}
    )
    if not raw_config:
        return default_config, True

    # 先按默认结构补齐缺失字段，避免旧 config.toml 少节少键。
    merged_config, changed = merge_plugin_config_data(default_config, raw_config)

    plugin_section = merged_config.get("plugin")
    if not isinstance(plugin_section, dict):
        merged_config["plugin"] = dict(default_config["plugin"])
        plugin_section = merged_config["plugin"]
        changed = True
    if not str(plugin_section.get("config_version") or "").strip():
        plugin_section["config_version"] = CONFIG_VERSION
        changed = True

    # 纠正常见坏值，避免 pydantic 因类型/约束直接失败。
    plugin_section["enabled"] = _as_bool(
        plugin_section.get("enabled"), default=True
    )
    plugin_section["auto_read_bot_account"] = _as_bool(
        plugin_section.get("auto_read_bot_account"), default=True
    )
    plugin_section["cache_seconds"] = _as_int(
        plugin_section.get("cache_seconds"), default=120, minimum=1, maximum=86400
    )

    identity_section = merged_config.get("identity")
    if not isinstance(identity_section, dict):
        merged_config["identity"] = dict(default_config["identity"])
        changed = True
    else:
        identity_section["bot_accounts"] = _as_str_list(
            identity_section.get("bot_accounts")
        )

    security_section = merged_config.get("security")
    if not isinstance(security_section, dict):
        merged_config["security"] = dict(default_config["security"])
        changed = True
    else:
        security_section["administrators"] = _as_str_list(
            security_section.get("administrators")
        )
        security_section["inherit_plugin_management_permissions"] = _as_bool(
            security_section.get("inherit_plugin_management_permissions"),
            default=True,
        )
        security_section["allow_public_status"] = _as_bool(
            security_section.get("allow_public_status"), default=True
        )

    storage_section = merged_config.get("storage")
    if not isinstance(storage_section, dict):
        merged_config["storage"] = dict(default_config["storage"])
        changed = True
    else:
        storage_section["history_limit"] = _as_int(
            storage_section.get("history_limit"), default=50, minimum=0, maximum=10000
        )

    try:
        validated = validate_plugin_config(SelfReplyGuardConfig, merged_config)
        return validated.model_dump(mode="python"), changed
    except Exception:
        return default_config, True


def _as_bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "on", "开启", "启用"}:
        return True
    if text in {"0", "false", "no", "off", "关闭", "停用"}:
        return False
    return default


def _as_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def _as_str_list(value: Any) -> list[str]:
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
