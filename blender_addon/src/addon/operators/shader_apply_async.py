"""Asynchronous shader / visualization application."""

from __future__ import annotations

try:  # pragma: no cover  # noqa: I001 (dynamic bpy import grouping)
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore

from typing import Optional

from ..preferences import get_prefs  # type: ignore
from ..shader_registry import get_strategies, get_strategy
from ..shaders_builtin import _BLACKHOLE_NAMES

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
        _strength_scale = 1.0
        _pending_init = True  # defer heavy gather to first timer for responsiveness

        def _gather(self):
            systems = []
            coll = bpy.data.collections.get("Frontier")  # type: ignore[union-attr]
            if coll:
                # Recursively gather objects from Frontier and all subcollections (Region/Constellation hierarchy)
                def _collect_recursive(collection):
                    systems.extend(collection.objects)
                    for child in collection.children:
                        _collect_recursive(child)

                _collect_recursive(coll)
            self._objects = systems
            self._total = len(systems)

        # --- Attribute Driven Material Infrastructure ---
        def _ensure_attribute_material(self) -> Optional["bpy.types.Material"]:  # type: ignore[name-defined]
            if not hasattr(bpy, "data"):
                return None
            try:
                mat_name = "EVE_AttrDriven"
                mat = bpy.data.materials.get(mat_name)  # type: ignore[attr-defined]
                if mat:
                    return mat
                mat = bpy.data.materials.new(mat_name)  # type: ignore[attr-defined]
                mat.use_nodes = True
                nt = mat.node_tree
                nodes = nt.nodes
                links = nt.links
                for n in list(nodes):
                    if n.type != "OUTPUT_MATERIAL":
                        nodes.remove(n)
                out = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
                obj_info = nodes.new("ShaderNodeObjectInfo")
                obj_info.location = (-600, 0)
                emission = nodes.new("ShaderNodeEmission")
                emission.location = (-150, 0)
                # Map per-object color to emission color (use Color output, not Location)
                # Object Info outputs order: Location, Color, Alpha, Object Index, Material Index, Random
                links.new(obj_info.outputs[1], emission.inputs[0])  # Color -> Emission Color
                # Use Alpha channel (per-object) for emission strength via a multiply (allows global scaling if updated later)
                math_mult = nodes.new("ShaderNodeMath")
                math_mult.operation = "MULTIPLY"
                math_mult.location = (-350, -80)
                math_mult.inputs[0].default_value = 1.0  # will be overridden by Alpha link
                math_mult.inputs[1].default_value = 1.0  # global scale placeholder
                links.new(obj_info.outputs[2], math_mult.inputs[0])  # Alpha -> Math input
                links.new(math_mult.outputs[0], emission.inputs[1])  # Math -> Emission Strength
                links.new(emission.outputs[0], out.inputs[0])
                return mat
            except Exception:  # noqa: BLE001
                return None

        def _apply_attribute_material(self, objs):
            mat = self._ensure_attribute_material()
            if mat is None:
                return
            for o in objs:
                try:
                    if getattr(o, "data", None) and hasattr(o.data, "materials"):
                        if o.data.materials:
                            o.data.materials[0] = mat
                        else:
                            o.data.materials.append(mat)
                except Exception:  # noqa: BLE001
                    continue

        def _color_from_strategy(self, strat, obj):
            name = obj.name or "?"
            if obj.name in _BLACKHOLE_NAMES:
                return (1.0, 0.45, 0.0, 1.0), 5.0
            if "NamePatternCategory" in strat.id:
                up = name.upper()
                if len(up) == 7 and up[3] == "-":
                    return (0.20, 0.50, 1.00, 1.0), 1.0  # DASH (blue)
                if ":" in up and len(up) == 6:
                    return (1.00, 0.55, 0.00, 1.0), 1.0  # COLON (orange)
                if up.count(".") == 2:
                    return (0.60, 0.20, 0.85, 1.0), 1.0  # DOTSEQ (purple)
                if len(up) == 7 and up[3] == "|" and up.count("|") == 1:
                    return (0.00, 0.90, 0.30, 1.0), 1.0  # PIPE (green)
                return (0.5, 0.5, 0.5, 1.0), 1.0
            if "NameChar" in strat.id or "FirstChar" in strat.id:
                up = name.upper()
                ch = up[0] if up else "A"
                if ch.isalpha():
                    idx = ord(ch) - ord("A")
                    hue = (idx / 26.0) % 1.0
                elif ch.isdigit():
                    hue = (ord(ch) - ord("0")) / 10.0 * 0.15
                else:
                    hue = 0.9
                import colorsys

                r, g, b = colorsys.hsv_to_rgb(hue, 0.8, 1.0)
                return (r, g, b, 1.0), 1.0
            return (0.8, 0.8, 0.8, 1.0), 1.0

        def _resolve_strategy(self, context):
            sid = self.strategy_id.strip()
            wm = context.window_manager
            if not sid and hasattr(wm, "eve_strategy_id"):
                sid = wm.eve_strategy_id  # type: ignore[attr-defined]
            if not sid:
                # Prefer NamePatternCategory as default if available
                npc = get_strategy("NamePatternCategory")
                if npc:
                    sid = npc.id
                else:
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
            if hasattr(wm, "eve_strategy_id"):
                # Persist selection so subsequent runs use same strategy unless changed
                try:
                    wm.eve_strategy_id = sid  # type: ignore[attr-defined]
                except Exception:  # noqa: BLE001
                    pass
            return True

        def execute(self, context):  # noqa: D401
            if not self._resolve_strategy(context):
                return {"CANCELLED"}
            # Defer heavy work (gather + material creation) to first TIMER tick to avoid UI pause.
            self._pending_init = True
            wm = context.window_manager
            wm.eve_shader_in_progress = True
            wm.eve_shader_progress = 0.0
            wm.eve_shader_total = 0
            wm.eve_shader_processed = 0
            try:
                context.workspace.status_text_set("EVE: Preparing visualization…")  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass
            self.report({"INFO"}, "Starting visualization (initializing)…")
            self._timer = context.window_manager.event_timer_add(0.01, window=context.window)
            context.window_manager.modal_handler_add(self)
            return {"RUNNING_MODAL"}

        def modal(self, context, event):  # noqa: D401
            if event.type == "TIMER":
                # Perform deferred initialization
                if self._pending_init:
                    self._gather()
                    if self._total == 0:
                        self.report({"WARNING"}, "No system objects to shade")
                        context.window_manager.event_timer_remove(self._timer)
                        wm = context.window_manager
                        wm.eve_shader_in_progress = False
                        try:
                            context.workspace.status_text_set(None)  # type: ignore[attr-defined]
                        except Exception:  # noqa: BLE001
                            pass
                        return {"CANCELLED"}
                    try:
                        prefs = get_prefs(context)
                        self._strength_scale = float(getattr(prefs, "emission_strength_scale", 1.0))
                    except Exception:  # noqa: BLE001
                        self._strength_scale = 1.0
                    self._apply_attribute_material(self._objects)
                    wm = context.window_manager
                    wm.eve_shader_total = self._total
                    self._pending_init = False
                    # fall through to process first batch same tick
                end = min(self._index + self.batch_size, self._total)
                strat = self._strategy
                objs = self._objects
                if not strat or not objs:
                    return {"CANCELLED"}
                for i in range(self._index, end):
                    obj = objs[i]
                    try:
                        color_rgba, strength = self._color_from_strategy(strat, obj)
                        # Pack strength (after global scale) into alpha channel for emission strength
                        scaled = float(strength) * self._strength_scale
                        r, g, b, _ = color_rgba
                        obj.color = (r, g, b, max(0.0, min(1.0, scaled)))
                        obj["eve_attr_strength"] = scaled  # retain for inspection
                    except Exception:  # noqa: BLE001
                        pass
                self._index = end
                wm = context.window_manager
                wm.eve_shader_processed = self._index
                wm.eve_shader_progress = self._index / self._total if self._total else 1.0
                if self._index and self._index % (self.batch_size * 10) == 0:
                    # Periodic lightweight feedback without spamming
                    self.report({"INFO"}, f"Viz progress: {self._index}/{self._total}")
                if self._index >= self._total:
                    context.window_manager.event_timer_remove(self._timer)
                    wm.eve_shader_in_progress = False
                    self.report({"INFO"}, f"Applied {strat.id}")
                    try:
                        context.workspace.status_text_set(None)  # type: ignore[attr-defined]
                    except Exception:  # noqa: BLE001
                        pass
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
