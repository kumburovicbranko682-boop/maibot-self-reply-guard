"""测试用包引导：把当前插件目录注册为 self_reply_guard。"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_PACKAGE = "self_reply_guard"


def ensure_package() -> None:
    if _PACKAGE in sys.modules and hasattr(sys.modules[_PACKAGE], "plugin"):
        return

    package = types.ModuleType(_PACKAGE)
    package.__path__ = [str(_ROOT)]  # type: ignore[attr-defined]
    package.__file__ = str(_ROOT / "__init__.py")
    package.__package__ = _PACKAGE
    sys.modules[_PACKAGE] = package

    for module_name in ("identity", "storage", "config", "plugin"):
        full_name = f"{_PACKAGE}.{module_name}"
        if full_name in sys.modules:
            setattr(package, module_name, sys.modules[full_name])
            continue
        file_path = _ROOT / f"{module_name}.py"
        spec = importlib.util.spec_from_file_location(
            full_name,
            file_path,
            submodule_search_locations=[str(_ROOT)],
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载模块: {full_name}")
        module = importlib.util.module_from_spec(spec)
        module.__package__ = _PACKAGE
        sys.modules[full_name] = module
        spec.loader.exec_module(module)
        setattr(package, module_name, module)

    package.SelfReplyGuardPlugin = package.plugin.SelfReplyGuardPlugin
    package.create_plugin = package.plugin.create_plugin
