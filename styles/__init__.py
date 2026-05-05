# -*- coding: utf-8 -*-
"""Styles package - dynamically load report CSS themes."""
import os, importlib.util

_STYLES_DIR = os.path.dirname(os.path.abspath(__file__))


def load_style(name: str = "ios_liquid") -> str:
    """Load CSS string by style name (without .py extension)."""
    path = os.path.join(_STYLES_DIR, f"{name}.py")
    if not os.path.exists(path):
        available = [f[:-3] for f in os.listdir(_STYLES_DIR)
                     if f.endswith(".py") and f != "__init__.py"]
        raise ValueError(f"Style not found: {name}. Available: {available}")
    spec = importlib.util.spec_from_file_location(f"_style_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "CSS"):
        raise ValueError(f"Style '{name}' must export a CSS string")
    return mod.CSS


def list_styles() -> list:
    """Return sorted list of available style names."""
    return sorted(f[:-3] for f in os.listdir(_STYLES_DIR)
                  if f.endswith(".py") and f != "__init__.py")
