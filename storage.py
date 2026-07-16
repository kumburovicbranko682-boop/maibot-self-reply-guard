"""插件状态持久化。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import json
import os
import tempfile


STATE_VERSION = 2


def now_text() -> str:
    """返回带时区的本地时间。"""

    return datetime.now().astimezone().isoformat(timespec="seconds")


def default_state() -> dict[str, Any]:
    """构造空白运行状态。"""

    return {
        "version": STATE_VERSION,
        "enabled_override": None,
        "total_blocked": 0,
        "planner_blocked": 0,
        "replyer_blocked": 0,
        "send_blocked": 0,
        "last_blocked_at": "",
        "last_event": {},
        "history": [],
    }


def load_state(path: Path) -> dict[str, Any]:
    """读取并补齐插件状态。"""

    if not path.exists():
        return default_state()
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("状态文件顶层必须是对象")
    state = default_state()
    state.update(raw)
    if state.get("enabled_override") not in {True, False, None}:
        state["enabled_override"] = None
    for key in (
        "total_blocked",
        "planner_blocked",
        "replyer_blocked",
        "send_blocked",
    ):
        try:
            state[key] = max(0, int(state.get(key, 0)))
        except (TypeError, ValueError):
            state[key] = 0
    state["last_event"] = (
        dict(state["last_event"]) if isinstance(state.get("last_event"), dict) else {}
    )
    state["history"] = (
        [dict(item) for item in state["history"] if isinstance(item, dict)]
        if isinstance(state.get("history"), list)
        else []
    )
    state["version"] = STATE_VERSION
    return state


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """在同目录原子写入 JSON，避免异常退出破坏状态。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
