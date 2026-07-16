from __future__ import annotations

import importlib.util
from pathlib import Path

_helpers_path = Path(__file__).resolve().parents[1] / "legacy_maibot_0x" / "helpers.py"
_spec = importlib.util.spec_from_file_location("legacy_helpers", _helpers_path)
assert _spec and _spec.loader
_helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_helpers)


class _Seg:
    def __init__(self, type: str, data):
        self.type = type
        self.data = data


class _Msg:
    def __init__(self, segments, additional=None):
        self.message_segments = segments
        self.additional_data = additional or {}


def test_extract_reply_id_from_seg_objects() -> None:
    msg = _Msg([_Seg("text", "hi"), _Seg("reply", "mid-1")])
    assert _helpers.extract_reply_message_id(msg) == "mid-1"


def test_extract_reply_id_from_dict_segments() -> None:
    msg = _Msg([{"type": "reply", "data": "mid-2"}])
    assert _helpers.extract_reply_message_id(msg) == "mid-2"


def test_extract_reply_id_from_additional_data() -> None:
    msg = _Msg([], {"reply_message_id": "mid-3"})
    assert _helpers.extract_reply_message_id(msg) == "mid-3"


def test_account_match_plain_and_platform() -> None:
    assert _helpers.account_matches("123", "qq", ["123"])
    assert _helpers.account_matches("123", "qq", ["qq:123"])
    assert _helpers.account_matches("123", "webui", ["qq:123"])
    assert not _helpers.account_matches("123", "telegram", ["qq:123"])
