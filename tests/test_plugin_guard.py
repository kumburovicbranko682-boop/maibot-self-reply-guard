from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace

from self_reply_guard.plugin import SelfReplyGuardPlugin, create_plugin
from self_reply_guard.storage import default_state


def build_message(user_id: str, *, message_id: str = "target", platform: str = "qq") -> dict:
    return {
        "message_id": message_id,
        "session_id": "stream-1",
        "platform": platform,
        "message_info": {"user_info": {"user_id": user_id}},
    }


def build_tool_call(name: str, arguments: dict, call_id: str) -> dict:
    return {
        "id": call_id,
        "function": {"name": name, "arguments": arguments},
    }


class FakeMessages:
    def __init__(self, messages: dict[str, dict], error: Exception | None = None) -> None:
        self.messages = messages
        self.error = error

    async def get_by_id(self, message_id: str, **kwargs):
        del kwargs
        if self.error is not None:
            raise self.error
        return self.messages.get(message_id)


class FakeConfig:
    def __init__(self, values: dict | None = None) -> None:
        self.values = values or {}

    async def get(self, key: str, default=None):
        return self.values.get(key, default)


class FakeSend:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    async def text(self, text: str, stream_id: str):
        self.messages.append((text, stream_id))
        return {"text": text, "stream_id": stream_id}


def build_plugin(messages: FakeMessages) -> SelfReplyGuardPlugin:
    plugin = SelfReplyGuardPlugin()
    plugin.set_plugin_config(plugin.get_default_config())
    plugin._state = default_state()
    plugin._ctx = SimpleNamespace(
        message=messages,
        config=FakeConfig(),
        send=FakeSend(),
        logger=logging.getLogger("self_reply_guard_test"),
    )
    plugin._runtime_accounts = ("qq:10001",)
    return plugin


def test_planner_hook_removes_self_reply_and_preserves_other_tools() -> None:
    plugin = build_plugin(
        FakeMessages(
            {
                "bot-target": build_message("10001", message_id="bot-target"),
                "user-target": build_message("20002", message_id="user-target"),
            }
        )
    )
    keep_tool = build_tool_call("no_action", {}, "call-2")
    user_reply = build_tool_call("reply", {"msg_id": "user-target"}, "call-3")

    result = asyncio.run(
        plugin.filter_self_reply_tool_calls(
            session_id="stream-1",
            response="",
            tool_calls=[
                build_tool_call("reply", {"msg_id": "bot-target"}, "call-1"),
                keep_tool,
                user_reply,
            ],
        )
    )

    assert result["modified_kwargs"]["tool_calls"] == [keep_tool, user_reply]
    assert plugin._state["planner_blocked"] == 1
    assert plugin._state["total_blocked"] == 1


def test_planner_hook_leaves_normal_user_reply_unchanged() -> None:
    plugin = build_plugin(
        FakeMessages({"target": build_message("20002", message_id="target")})
    )

    result = asyncio.run(
        plugin.filter_self_reply_tool_calls(
            session_id="stream-1",
            tool_calls=[build_tool_call("reply", {"msg_id": "target"}, "call-1")],
        )
    )

    assert result == {"action": "continue"}
    assert plugin._state["planner_blocked"] == 0


def test_reply_target_parser_supports_legacy_flat_tool_call() -> None:
    assert (
        SelfReplyGuardPlugin._reply_target_from_tool_call(
            {"name": "reply", "arguments": {"msg_id": "target"}}
        )
        == "target"
    )


def test_after_response_is_emptied_for_bot_target() -> None:
    plugin = build_plugin(FakeMessages({"target": build_message("10001")}))

    result = asyncio.run(
        plugin.erase_self_reply_response(
            response="继续回复自己",
            session_id="stream-1",
            reply_message_id="target",
            attempt=1,
        )
    )

    assert result["modified_kwargs"]["response"] == ""
    assert result["modified_kwargs"]["retry"] is False
    assert plugin._state["replyer_blocked"] == 1


def test_normal_user_target_is_not_modified() -> None:
    plugin = build_plugin(FakeMessages({"target": build_message("20002")}))

    result = asyncio.run(
        plugin.erase_self_reply_response(
            response="正常回复",
            session_id="stream-1",
            reply_message_id="target",
        )
    )

    assert result == {"action": "continue"}
    assert plugin._state["total_blocked"] == 0


def test_before_send_aborts_when_outbound_identity_matches() -> None:
    plugin = build_plugin(FakeMessages({"target": build_message("10001")}))
    plugin._runtime_accounts = ()

    result = asyncio.run(
        plugin.abort_self_reply_before_send(
            message=build_message("10001", message_id="outbound"),
            reply_message_id="target",
            set_reply=False,
        )
    )

    assert result == {"action": "abort"}
    assert plugin._state["send_blocked"] == 1


def test_message_query_failure_does_not_block_unrelated_send() -> None:
    plugin = build_plugin(FakeMessages({}, RuntimeError("database unavailable")))

    result = asyncio.run(
        plugin.abort_self_reply_before_send(
            message=build_message("10001", message_id="outbound"),
            reply_message_id="missing",
        )
    )

    assert result == {"action": "continue"}


def test_extra_bot_account_is_honored() -> None:
    plugin = build_plugin(FakeMessages({"target": build_message("30003")}))
    config = plugin.get_default_config()
    config["identity"]["bot_accounts"] = ["30003"]
    plugin.set_plugin_config(config)

    result = asyncio.run(
        plugin.erase_self_reply_response(
            response="不应发送",
            session_id="stream-1",
            reply_message_id="target",
        )
    )

    assert result["modified_kwargs"]["response"] == ""


def test_runtime_qq_account_is_loaded_from_bot_config() -> None:
    plugin = build_plugin(FakeMessages({}))
    plugin._ctx.config = FakeConfig({"bot.qq_account": "424242"})

    asyncio.run(plugin._refresh_runtime_accounts())

    assert plugin._runtime_accounts == ("qq:424242",)


def test_qq_admin_can_persistently_disable_guard() -> None:
    plugin = build_plugin(FakeMessages({}))
    config = plugin.get_default_config()
    config["security"]["administrators"] = ["10001"]
    plugin.set_plugin_config(config)

    result = asyncio.run(
        plugin.handle_guard_command(
            stream_id="stream-1",
            group_id="group-1",
            platform="qq",
            user_id="10001",
            matched_groups={"args": "关闭"},
        )
    )

    assert result[0] is True
    assert plugin._state["enabled_override"] is False
    assert plugin._is_enabled() is False


def test_plugin_declares_command_and_all_guard_hooks() -> None:
    components = SelfReplyGuardPlugin().get_components()
    names = {component["name"] for component in components}

    assert {
        "self_reply_guard",
        "filter_self_reply_tool_calls",
        "identify_self_reply_target",
        "erase_self_reply_response",
        "abort_self_reply_before_send",
    } <= names


def test_create_plugin_factory_returns_plugin_instance() -> None:
    assert isinstance(create_plugin(), SelfReplyGuardPlugin)
