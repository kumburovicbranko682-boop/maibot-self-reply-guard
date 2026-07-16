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

from self_reply_guard.storage import atomic_write_json, default_state, load_state


class StorageTests(unittest.TestCase):
    def test_state_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            state = default_state()
            state["total_blocked"] = 3
            atomic_write_json(path, state)
            self.assertEqual(load_state(path)["total_blocked"], 3)

    def test_invalid_fields_are_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text(
                '{"enabled_override":"yes","total_blocked":"bad","history":{}}',
                encoding="utf-8",
            )
            state = load_state(path)
            self.assertIsNone(state["enabled_override"])
            self.assertEqual(state["total_blocked"], 0)
            self.assertEqual(state["history"], [])


if __name__ == "__main__":
    unittest.main()
