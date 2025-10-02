"""Asynchronous shader / visualization application."""

from __future__ import annotations

try:  # pragma: no cover  # noqa: I001 (dynamic bpy import grouping)
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore

from ..shader_registry import get_strategies, get_strategy

if bpy:

    def _strategy_enum_items(self, context):  # pragma: no cover
        try:
            items = [(s.id, s.label, s.id) for s in get_strategies()]
            if not items:
                return [("__none__", "(no strategies)", "")]  # type: ignore
            return items  # type: ignore
        except Exception:  # noqa: BLE001
            return [("__error__", "(error)", "")]  # type: ignore

    class EVE_OT_apply_shader_modal(bpy.types.Operator):  # type: ignore
        bl_idname = "eve.apply_shader_modal"
        bl_label = "Apply Visualization (Async)"
        bl_description = "Apply selected visualization strategy asynchronously"

        batch_size: bpy.props.IntProperty(  # type: ignore[valid-type]
            name="Batch Size", default=5000, min=100, max=200000
        )
        strategy_id: bpy.props.StringProperty(  # type: ignore[valid-type]
            name="Strategy Id", default=""
        )

        _objects = None
        _index = 0
        _total = 0
        _strategy = None
        _timer = None

        def _gather(self):
            systems = []
            coll = bpy.data.collections.get("EVE_Systems")  # type: ignore[union-attr]
            if coll:
                systems.extend(coll.objects)
            self._objects = systems
            self._total = len(systems)

        def _resolve_strategy(self, context):
            sid = self.strategy_id.strip()
            wm = context.window_manager
            if not sid and hasattr(wm, "eve_strategy_id"):
                sid = wm.eve_strategy_id  # type: ignore[attr-defined]
            if not sid:
                strategies = get_strategies()
                if not strategies:
                    self.report({"ERROR"}, "No strategies registered")
                    return False
                sid = strategies[0].id
            strat = get_strategy(sid)
            if not strat:
                self.report({"ERROR"}, f"Strategy not found: {sid}")
                return False
            self._strategy = strat
            if hasattr(wm, "eve_shader_strategy"):
                wm.eve_shader_strategy = sid  # type: ignore[attr-defined]
            return True

        def execute(self, context):  # noqa: D401
            if not self._resolve_strategy(context):
                return {"CANCELLED"}
            self._gather()
            if self._total == 0:
                self.report({"WARNING"}, "No system objects to shade")
                return {"CANCELLED"}
            wm = context.window_manager
            wm.eve_shader_in_progress = True
            wm.eve_shader_progress = 0.0
            wm.eve_shader_total = self._total
            wm.eve_shader_processed = 0
            self._timer = context.window_manager.event_timer_add(0.01, window=context.window)
            context.window_manager.modal_handler_add(self)
            return {"RUNNING_MODAL"}

        def modal(self, context, event):  # noqa: D401
            if event.type == "TIMER":
                end = min(self._index + self.batch_size, self._total)
                strat = self._strategy
                objs = self._objects
                if not strat or not objs:
                    return {"CANCELLED"}
                for i in range(self._index, end):
                    obj = objs[i]
                    try:
                        # Support both build(context, dict) and apply(context, obj)
                        if hasattr(strat, "apply"):
                            strat.apply(context, obj)  # type: ignore[attr-defined]
                    except Exception:  # noqa: BLE001
                        pass
                self._index = end
                wm = context.window_manager
                wm.eve_shader_processed = self._index
                wm.eve_shader_progress = self._index / self._total if self._total else 1.0
                if self._index >= self._total:
                    context.window_manager.event_timer_remove(self._timer)
                    wm.eve_shader_in_progress = False
                    self.report({"INFO"}, f"Applied {strat.id}")
                    return {"FINISHED"}
            return {"RUNNING_MODAL"}

    class EVE_OT_cancel_shader(bpy.types.Operator):  # type: ignore
        bl_idname = "eve.cancel_shader"
        bl_label = "Cancel Visualization"
        bl_description = "Cancel the asynchronous visualization application"

        def execute(self, context):  # noqa: D401
            wm = context.window_manager
            if getattr(wm, "eve_shader_in_progress", False):
                wm.eve_shader_in_progress = False
                self.report({"INFO"}, "Cancellation requested")
            else:
                self.report({"INFO"}, "No visualization in progress")
            return {"FINISHED"}


def register():  # pragma: no cover
    if not bpy:
        return
    bpy.utils.register_class(EVE_OT_apply_shader_modal)
    bpy.utils.register_class(EVE_OT_cancel_shader)
    wm = bpy.types.WindowManager
    # Progress properties (shader)
    if not hasattr(wm, "eve_shader_in_progress"):
        wm.eve_shader_in_progress = bpy.props.BoolProperty(default=False)  # type: ignore
    if not hasattr(wm, "eve_shader_progress"):
        wm.eve_shader_progress = bpy.props.FloatProperty(default=0.0)  # type: ignore
    if not hasattr(wm, "eve_shader_total"):
        wm.eve_shader_total = bpy.props.IntProperty(default=0)  # type: ignore
    if not hasattr(wm, "eve_shader_processed"):
        wm.eve_shader_processed = bpy.props.IntProperty(default=0)  # type: ignore
    if not hasattr(wm, "eve_shader_strategy"):
        wm.eve_shader_strategy = bpy.props.StringProperty(default="")  # type: ignore
    if not hasattr(wm, "eve_strategy_id"):
        wm.eve_strategy_id = bpy.props.EnumProperty(  # type: ignore[attr-defined]
            name="Strategy", items=_strategy_enum_items
        )


def unregister():  # pragma: no cover
    if not bpy:
        return
    bpy.utils.unregister_class(EVE_OT_cancel_shader)
    bpy.utils.unregister_class(EVE_OT_apply_shader_modal)
