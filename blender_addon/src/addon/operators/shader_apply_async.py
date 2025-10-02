"""Asynchronous shader / visualization application."""

from __future__ import annotations

try:  # pragma: no cover  # noqa: I001 (dynamic bpy import grouping)
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore

from typing import Optional

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
        bl_label = "Apply Visualization (Instant)"
        bl_description = (
            "Apply property-driven material (reads custom properties via Attribute nodes)"
        )

        strategy_id: bpy.props.StringProperty(  # type: ignore[valid-type]
            name="Strategy Id", default=""
        )

        _objects = None
        _total = 0
        _strategy = None

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
                out.location = (300, 0)

                # Read custom property: eve_name_char_bucket (-1 to 8)
                attr_bucket = nodes.new("ShaderNodeAttribute")
                attr_bucket.attribute_name = "eve_name_char_bucket"
                attr_bucket.attribute_type = "OBJECT"
                attr_bucket.location = (-900, 200)

                # Clamp -1 to 0 (so fallback becomes first bucket)
                math_max = nodes.new("ShaderNodeMath")
                math_max.operation = "MAXIMUM"
                math_max.inputs[1].default_value = 0.0
                math_max.location = (-700, 200)
                links.new(attr_bucket.outputs["Fac"], math_max.inputs[0])

                # Normalize 0-8 to 0-1 for ColorRamp/HSV
                math_div = nodes.new("ShaderNodeMath")
                math_div.operation = "DIVIDE"
                math_div.inputs[1].default_value = 8.0
                math_div.location = (-500, 200)
                links.new(math_max.outputs[0], math_div.inputs[0])

                # Convert to HSV color (rainbow gradient)
                hsv = nodes.new("ShaderNodeCombineHSV")
                hsv.location = (-300, 200)
                hsv.inputs["S"].default_value = 1.0  # Full saturation
                hsv.inputs["V"].default_value = 1.0  # Full brightness
                links.new(math_div.outputs[0], hsv.inputs["H"])  # Hue from bucket

                # Read custom property: eve_planet_count + eve_moon_count for emission strength
                attr_planets = nodes.new("ShaderNodeAttribute")
                attr_planets.attribute_name = "eve_planet_count"
                attr_planets.attribute_type = "OBJECT"
                attr_planets.location = (-900, -100)

                attr_moons = nodes.new("ShaderNodeAttribute")
                attr_moons.attribute_name = "eve_moon_count"
                attr_moons.attribute_type = "OBJECT"
                attr_moons.location = (-900, -250)

                # Add planet + moon counts
                math_add = nodes.new("ShaderNodeMath")
                math_add.operation = "ADD"
                math_add.location = (-700, -150)
                links.new(attr_planets.outputs["Fac"], math_add.inputs[0])
                links.new(attr_moons.outputs["Fac"], math_add.inputs[1])

                # Map child count to emission strength (0-20 → 0.5-3.0)
                map_range = nodes.new("ShaderNodeMapRange")
                map_range.location = (-500, -150)
                map_range.inputs["From Min"].default_value = 0.0
                map_range.inputs["From Max"].default_value = 20.0
                map_range.inputs["To Min"].default_value = 0.5
                map_range.inputs["To Max"].default_value = 3.0
                map_range.clamp = True
                links.new(math_add.outputs[0], map_range.inputs["Value"])

                # Emission shader
                emission = nodes.new("ShaderNodeEmission")
                emission.location = (100, 0)
                links.new(hsv.outputs["Color"], emission.inputs["Color"])
                links.new(map_range.outputs["Result"], emission.inputs["Strength"])

                # Connect to output
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

            # Since properties are pre-calculated on objects, we just need to apply the material!
            # No iteration needed - shader reads properties directly via Attribute nodes
            self._gather()
            if self._total == 0:
                self.report({"WARNING"}, "No system objects to shade")
                return {"CANCELLED"}

            # Apply attribute-driven material to all objects
            self._apply_attribute_material(self._objects)

            self.report({"INFO"}, f"Applied property-driven material to {self._total} objects")
            return {"FINISHED"}

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
