from __future__ import annotations

import importlib.util
from pathlib import Path

_bootstrap_path = Path(__file__).resolve().parent / "_bootstrap.py"
_spec = importlib.util.spec_from_file_location("self_reply_guard_test_bootstrap", _bootstrap_path)
assert _spec and _spec.loader
_bootstrap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bootstrap)
_bootstrap.ensure_package()

from self_reply_guard.config import coerce_config_data, default_config_dict
from self_reply_guard.plugin import SelfReplyGuardPlugin


def test_missing_sections_are_filled_with_defaults() -> None:
    normalized, changed = coerce_config_data({"plugin": {"enabled": False}})
    assert changed is True
    assert normalized["plugin"]["enabled"] is False
    assert normalized["plugin"]["config_version"]
    assert normalized["identity"]["bot_accounts"] == []
    assert normalized["security"]["allow_public_status"] is True
    assert normalized["storage"]["history_limit"] == 50


def test_missing_config_version_does_not_fail() -> None:
    normalized, _ = coerce_config_data({"plugin": {"enabled": True}})
    assert normalized["plugin"]["config_version"] == default_config_dict()["plugin"]["config_version"]


def test_bad_types_are_coerced_or_fallback() -> None:
    normalized, _ = coerce_config_data(
        {
            "plugin": {
                "enabled": "yes",
                "cache_seconds": "180",
                "config_version": "1.0.0",
            },
            "identity": {"bot_accounts": "123,456"},
            "storage": {"history_limit": "bad"},
        }
    )
    assert normalized["plugin"]["enabled"] is True
    assert normalized["plugin"]["cache_seconds"] == 180
    assert normalized["identity"]["bot_accounts"] == ["123", "456"]
    assert normalized["storage"]["history_limit"] == 50


def test_plugin_set_plugin_config_survives_empty_and_broken_input() -> None:
    plugin = SelfReplyGuardPlugin()
    plugin.set_plugin_config({})
    assert plugin._safe_config().plugin.enabled is True

    plugin.set_plugin_config({"plugin": {"enabled": "off", "config_version": "1.0.0"}})
    assert plugin._safe_config().plugin.enabled is False

    plugin.set_plugin_config({"totally": "wrong"})
    assert plugin._safe_config().plugin.config_version
    assert isinstance(plugin._safe_config().identity.bot_accounts, list)
