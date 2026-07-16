"""机器人自回复硬拦截插件配置。"""

from __future__ import annotations

from typing import ClassVar

from maibot_sdk import Field, PluginConfigBase


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
        ge=30,
        le=900,
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
        ge=0,
        le=1000,
        description="最多保存的近期拦截记录数；0 表示不保存明细。",
    )


class SelfReplyGuardConfig(PluginConfigBase):
    """插件完整配置。"""

    plugin: PluginSection = Field(default_factory=PluginSection)
    identity: IdentitySection = Field(default_factory=IdentitySection)
    security: SecuritySection = Field(default_factory=SecuritySection)
    storage: StorageSection = Field(default_factory=StorageSection)
