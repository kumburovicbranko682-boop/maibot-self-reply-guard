from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

_bootstrap_path = Path(__file__).resolve().parent / "_bootstrap.py"
_spec = importlib.util.spec_from_file_location("self_reply_guard_test_bootstrap", _bootstrap_path)
assert _spec and _spec.loader
_bootstrap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bootstrap)
_bootstrap.ensure_package()

from self_reply_guard.identity import (
    extract_sender,
    same_sender,
    sender_matches_accounts,
)


def build_message(user_id: str, platform: str = "qq") -> dict:
    return {
        "platform": platform,
        "message_info": {"user_info": {"user_id": user_id}},
    }


def test_extract_sender_reads_maibot_message_shape() -> None:
    assert extract_sender(build_message("123456")) == ("qq", "123456")


def test_extract_sender_reads_flat_user_id() -> None:
    assert extract_sender({"platform": "qq", "user_id": "4242"}) == ("qq", "4242")


def test_extract_sender_normalizes_onebot_alias() -> None:
    assert extract_sender(
        {
            "platform": "onebot",
            "message_info": {"user_info": {"user_id": "123"}},
        }
    ) == ("qq", "123")


def test_account_match_supports_plain_and_platform_specs() -> None:
    message = build_message("123456")

    assert sender_matches_accounts(message, ["123456"])
    assert sender_matches_accounts(message, ["qq:123456"])
    assert not sender_matches_accounts(message, ["telegram:123456"])


def test_webui_and_qq_are_the_same_bot_identity() -> None:
    assert same_sender(build_message("123456", "qq"), build_message("123456", "webui"))


def test_different_accounts_never_match() -> None:
    assert not same_sender(build_message("123456"), build_message("999999"))
