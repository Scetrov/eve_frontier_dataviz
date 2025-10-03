"""Operator package aggregator.

Each submodule defines one or more Blender operators (EVE_OT_*) plus
`register()` / `unregister()` functions. We import them lazily in the
top-level add-on registration. All Blender specific code is guarded so
that importing this package in a pure Python (non-Blender) environment
for tests will not fail (``bpy`` will be ``None`` and registration is a no-op).
"""

from __future__ import annotations

from importlib import import_module
from typing import List, Protocol, runtime_checkable

try:  # pragma: no cover - only present in Blender runtime
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore

_SUBMODULES = [
    "._shared",
    ".data_ops",
    ".build_scene_modal",
    ".build_jumps",
    ".shader_apply_async",
    ".viewport",
    ".volumetric",
    ".camera",
    ".lighting",
    ".reference_points",
    ".jump_analysis",
]

_loaded: List[object] = []


@runtime_checkable
class _HasReg(Protocol):  # pragma: no cover - typing helper
    def register(self) -> None: ...  # noqa: D401,E701
    def unregister(self) -> None: ...  # noqa: D401,E701


def _load():  # pragma: no cover - trivial
    global _loaded
    if _loaded:
        return _loaded
    mods: List[object] = []
    for rel in _SUBMODULES:
        try:
            mods.append(import_module(rel, __name__))
        except Exception as e:  # noqa: BLE001
            print(f"[EVEVisualizer][operators][error] failed importing {rel}: {e}")
    _loaded = mods
    return _loaded


def register():  # pragma: no cover - Blender side effect
    if bpy is None:
        return
    for m in _load():  # type: ignore[assignment]
        reg: _HasReg | None = m if isinstance(m, _HasReg) else None  # type: ignore[arg-type]
        if reg and hasattr(reg, "register"):
            try:  # noqa: SIM105
                reg.register()  # type: ignore[attr-defined]
            except Exception as e:  # noqa: BLE001
                print(f"[EVEVisualizer][operators][error] register() failed in {m}: {e}")


def unregister():  # pragma: no cover - Blender side effect
    if bpy is None:
        return
    for m in reversed(_load()):  # type: ignore[assignment]
        reg: _HasReg | None = m if isinstance(m, _HasReg) else None  # type: ignore[arg-type]
        if reg and hasattr(reg, "unregister"):
            try:  # noqa: SIM105
                reg.unregister()  # type: ignore[attr-defined]
            except Exception as e:  # noqa: BLE001
                print(f"[EVEVisualizer][operators][error] unregister() failed in {m}: {e}")
