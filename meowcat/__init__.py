# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat — An agent framework built on the biological blueprint of a cat. Depends on pydantic>=2.0 + anyio>=4.0, zero meowagent imports."""

from __future__ import annotations

import importlib
import pathlib
import re

from meowcat._exports import __all__, _LAZY_MAP, _SUBMODULES

# -- Version -----------------------------------------------------------
# Use importlib.metadata for pip-installed packages;
# fall back to pyproject.toml for editable/dev installs.
try:
    from importlib.metadata import version as _pkg_version
    __version__ = _pkg_version("meowcat")
except Exception:
    _pyproject = pathlib.Path(
        __file__).resolve().parent.parent / "pyproject.toml"
    _match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']',
                       _pyproject.read_text(encoding="utf-8"), re.MULTILINE)
    __version__ = _match.group(1) if _match else "0.0.0"


def __getattr__(name: str):
    """PEP 562 lazy import — only loads a module on first access.

    ``import meowcat`` costs ~2 ms instead of ~80 ms because nothing
    beyond ``_exports.py`` + ``__init__.py`` is imported eagerly.
    """
    # Submodule access: meowcat.anatomy, meowcat.biology, meowcat.organ_roles
    if name in _SUBMODULES:
        module = importlib.import_module(f"meowcat.{name}")
        globals()[name] = module
        return module

    # Named symbol access: meowcat.CatBase, meowcat.Nervous, etc.
    entry = _LAZY_MAP.get(name)
    if entry is not None:
        mod_path, attr = entry
        module = importlib.import_module(mod_path)
        value = getattr(module, attr)
        globals()[name] = value
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

