from __future__ import annotations

from self_reply_guard.storage import atomic_write_json, default_state, load_state


def test_state_round_trip(tmp_path) -> None:
    path = tmp_path / "state.json"
    state = default_state()
    state["total_blocked"] = 3

    atomic_write_json(path, state)

    assert load_state(path)["total_blocked"] == 3


def test_invalid_fields_are_normalized(tmp_path) -> None:
    path = tmp_path / "state.json"
    path.write_text(
        '{"enabled_override":"yes","total_blocked":"bad","history":{}}',
        encoding="utf-8",
    )

    state = load_state(path)

    assert state["enabled_override"] is None
    assert state["total_blocked"] == 0
    assert state["history"] == []
