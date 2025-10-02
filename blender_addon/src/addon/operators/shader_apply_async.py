"""Asynchronous shader / visualization application."""

from __future__ import annotations

try:  # pragma: no cover  # noqa: I001 (dynamic bpy import grouping)
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore

from typing import Optional

from ..node_groups import ensure_strategy_node_groups

if bpy:

    def _node_strategy_enum_items(self, context):  # pragma: no cover
        """Enum items for node-based strategies."""
        return [  # type: ignore
            (
                "CharacterRainbow",
                "Character Rainbow",
                "Color from first character, brightness from child count",
            ),
            ("PatternCategories", "Pattern Categories", "Distinct colors per naming pattern"),
            (
                "PositionEncoding",
                "Position Encoding",
                "RGB from first 3 characters, blackhole boost",
            ),
        ]

    class EVE_OT_apply_shader_modal(bpy.types.Operator):  # type: ignore
        bl_idname = "eve.apply_shader_modal"
        bl_label = "Apply Visualization (Instant)"
        bl_description = (
            "Apply property-driven material (reads custom properties via Attribute nodes)"
        )

        _objects = None
        _total = 0

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

        # --- Node Group Strategy Material Infrastructure ---
        def _ensure_node_group_material(
            self, strategy_name: str = "CharacterRainbow"
        ) -> Optional["bpy.types.Material"]:  # type: ignore[name-defined]
            """Create or update material using node group strategies with switcher.

            Args:
                strategy_name: Name of the strategy to use (without EVE_Strategy_ prefix)

            Returns:
                The material instance or None
            """
            if not hasattr(bpy, "data"):
                return None
            try:
                # Ensure all strategy node groups exist
                ensure_strategy_node_groups()

                mat_name = "EVE_NodeGroupStrategies"
                mat = bpy.data.materials.get(mat_name)  # type: ignore[attr-defined]

                # Create material if it doesn't exist
                if not mat:
                    mat = bpy.data.materials.new(mat_name)  # type: ignore[attr-defined]
                    mat.use_nodes = True
                    nt = mat.node_tree
                    nodes = nt.nodes
                    links = nt.links

                    # Clear default nodes except output
                    for n in list(nodes):
                        if n.type != "OUTPUT_MATERIAL":
                            nodes.remove(n)
                    out = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
                    out.location = (800, 0)

                    # Create node group references for each strategy
                    ng_char_rainbow = nodes.new("ShaderNodeGroup")
                    ng_char_rainbow.node_tree = bpy.data.node_groups.get(
                        "EVE_Strategy_CharacterRainbow"
                    )  # type: ignore[attr-defined]
                    ng_char_rainbow.location = (-400, 300)
                    ng_char_rainbow.name = "CharacterRainbow"

                    ng_pattern = nodes.new("ShaderNodeGroup")
                    ng_pattern.node_tree = bpy.data.node_groups.get(
                        "EVE_Strategy_PatternCategories"
                    )  # type: ignore[attr-defined]
                    ng_pattern.location = (-400, 0)
                    ng_pattern.name = "PatternCategories"

                    ng_position = nodes.new("ShaderNodeGroup")
                    ng_position.node_tree = bpy.data.node_groups.get(
                        "EVE_Strategy_PositionEncoding"
                    )  # type: ignore[attr-defined]
                    ng_position.location = (-400, -300)
                    ng_position.name = "PositionEncoding"

                    # Create shader switchers for Color and Strength
                    # We'll use Mix nodes in "Mix" mode to switch between strategies

                    # Value node to control which strategy (0, 1, or 2)
                    value_strategy = nodes.new("ShaderNodeValue")
                    value_strategy.location = (-800, -500)
                    value_strategy.name = "StrategySelector"
                    value_strategy.label = "Strategy (0=Rainbow, 1=Pattern, 2=Position)"
                    value_strategy.outputs[0].default_value = 0.0  # Default to CharacterRainbow

                    # First mix: Choose between CharacterRainbow (0) and PatternCategories (1)
                    mix_color_1 = nodes.new("ShaderNodeMix")
                    mix_color_1.data_type = "RGBA"
                    mix_color_1.location = (0, 200)
                    mix_color_1.name = "MixColor1"
                    links.new(ng_char_rainbow.outputs["Color"], mix_color_1.inputs[6])  # A
                    links.new(ng_pattern.outputs["Color"], mix_color_1.inputs[7])  # B

                    # Clamp strategy value to 0-1 for first mix
                    math_clamp_1 = nodes.new("ShaderNodeMath")
                    math_clamp_1.operation = "MAXIMUM"
                    math_clamp_1.location = (-200, -400)
                    math_clamp_1.inputs[1].default_value = 0.0
                    links.new(value_strategy.outputs[0], math_clamp_1.inputs[0])

                    math_min_1 = nodes.new("ShaderNodeMath")
                    math_min_1.operation = "MINIMUM"
                    math_min_1.location = (-100, -400)
                    math_min_1.inputs[1].default_value = 1.0
                    links.new(math_clamp_1.outputs[0], math_min_1.inputs[0])
                    links.new(math_min_1.outputs[0], mix_color_1.inputs[0])  # Factor

                    # Second mix: Choose between result of first mix and PositionEncoding (2)
                    mix_color_2 = nodes.new("ShaderNodeMix")
                    mix_color_2.data_type = "RGBA"
                    mix_color_2.location = (200, 200)
                    mix_color_2.name = "MixColor2"
                    links.new(
                        mix_color_1.outputs[2], mix_color_2.inputs[6]
                    )  # A (result from first mix)
                    links.new(ng_position.outputs["Color"], mix_color_2.inputs[7])  # B

                    # Factor for second mix: clamp (strategy - 1) to 0-1
                    math_sub = nodes.new("ShaderNodeMath")
                    math_sub.operation = "SUBTRACT"
                    math_sub.location = (-200, -500)
                    math_sub.inputs[1].default_value = 1.0
                    links.new(value_strategy.outputs[0], math_sub.inputs[0])

                    math_clamp_2 = nodes.new("ShaderNodeMath")
                    math_clamp_2.operation = "MAXIMUM"
                    math_clamp_2.location = (-100, -500)
                    math_clamp_2.inputs[1].default_value = 0.0
                    links.new(math_sub.outputs[0], math_clamp_2.inputs[0])

                    math_min_2 = nodes.new("ShaderNodeMath")
                    math_min_2.operation = "MINIMUM"
                    math_min_2.location = (0, -500)
                    math_min_2.inputs[1].default_value = 1.0
                    links.new(math_clamp_2.outputs[0], math_min_2.inputs[0])
                    links.new(math_min_2.outputs[0], mix_color_2.inputs[0])  # Factor

                    # Similar mix setup for Strength
                    mix_strength_1 = nodes.new("ShaderNodeMix")
                    mix_strength_1.data_type = "FLOAT"
                    mix_strength_1.location = (0, -100)
                    mix_strength_1.name = "MixStrength1"
                    links.new(ng_char_rainbow.outputs["Strength"], mix_strength_1.inputs[2])  # A
                    links.new(ng_pattern.outputs["Strength"], mix_strength_1.inputs[3])  # B
                    links.new(
                        math_min_1.outputs[0], mix_strength_1.inputs[0]
                    )  # Same factor as color mix 1

                    mix_strength_2 = nodes.new("ShaderNodeMix")
                    mix_strength_2.data_type = "FLOAT"
                    mix_strength_2.location = (200, -100)
                    mix_strength_2.name = "MixStrength2"
                    links.new(mix_strength_1.outputs[1], mix_strength_2.inputs[2])  # A
                    links.new(ng_position.outputs["Strength"], mix_strength_2.inputs[3])  # B
                    links.new(
                        math_min_2.outputs[0], mix_strength_2.inputs[0]
                    )  # Same factor as color mix 2

                    # Emission shader
                    emission = nodes.new("ShaderNodeEmission")
                    emission.location = (500, 0)
                    links.new(mix_color_2.outputs[2], emission.inputs["Color"])
                    links.new(mix_strength_2.outputs[1], emission.inputs["Strength"])

                    # Connect to output
                    links.new(emission.outputs[0], out.inputs[0])

                # Update strategy selector value
                nt = mat.node_tree
                selector = nt.nodes.get("StrategySelector")
                if selector:
                    strategy_map = {
                        "CharacterRainbow": 0.0,
                        "PatternCategories": 1.0,
                        "PositionEncoding": 2.0,
                    }
                    selector.outputs[0].default_value = strategy_map.get(strategy_name, 0.0)

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

        def _apply_node_group_material(self, objs, strategy_name: str):
            """Apply node group material to objects with specified strategy active."""
            mat = self._ensure_node_group_material(strategy_name)
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

        def execute(self, context):  # noqa: D401
            # Get selected strategy from scene property (with fallback)
            strategy_name = getattr(context.scene, "eve_active_strategy", "CharacterRainbow")

            # Gather system objects
            self._gather()
            if self._total == 0:
                self.report({"WARNING"}, "No system objects to shade")
                return {"CANCELLED"}

            # Apply node-group-based material with switcher to all objects
            self._apply_node_group_material(self._objects, strategy_name)

            self.report({"INFO"}, f"Applied {strategy_name} strategy to {self._total} objects")
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

    print("[EVEVisualizer][shader_apply_async] Starting registration...")

    try:
        bpy.utils.register_class(EVE_OT_apply_shader_modal)
        print("[EVEVisualizer][shader_apply_async] Registered EVE_OT_apply_shader_modal")
    except Exception as e:
        print(
            f"[EVEVisualizer][shader_apply_async] ERROR registering EVE_OT_apply_shader_modal: {e}"
        )

    try:
        bpy.utils.register_class(EVE_OT_cancel_shader)
        print("[EVEVisualizer][shader_apply_async] Registered EVE_OT_cancel_shader")
    except Exception as e:
        print(f"[EVEVisualizer][shader_apply_async] ERROR registering EVE_OT_cancel_shader: {e}")

    # Scene property for node-based strategy selection
    # Always set it - Blender will not duplicate if it already exists
    try:
        bpy.types.Scene.eve_active_strategy = bpy.props.EnumProperty(  # type: ignore[attr-defined]
            name="Active Strategy",
            description="Select visualization strategy",
            items=_node_strategy_enum_items,
            default="CharacterRainbow",
            update=_on_strategy_change,
        )
        print("[EVEVisualizer][shader_apply_async] Registered eve_active_strategy property")
    except Exception as e:
        print(f"[EVEVisualizer][shader_apply_async] ERROR registering eve_active_strategy: {e}")
        import traceback

        traceback.print_exc()


def _on_strategy_change(self, context):  # pragma: no cover
    """Update material when strategy changes - creates material if needed."""
    if not bpy or not hasattr(bpy, "data"):
        return

    strategy_name = context.scene.eve_active_strategy

    # Ensure node groups exist
    ensure_strategy_node_groups()

    # Get or create the material
    mat_name = "EVE_NodeGroupStrategies"
    mat = bpy.data.materials.get(mat_name)  # type: ignore[attr-defined]

    if not mat:
        # Material doesn't exist yet - need to create it
        # Create temporary operator instance to use its method
        op = EVE_OT_apply_shader_modal()
        mat = op._ensure_node_group_material(strategy_name)

        if mat:
            # Apply to all system objects
            systems = []
            frontier = bpy.data.collections.get("Frontier")  # type: ignore[union-attr]
            if frontier:

                def _collect_recursive(collection):
                    systems.extend(collection.objects)
                    for child in collection.children:
                        _collect_recursive(child)

                _collect_recursive(frontier)

            # Assign material to all systems
            for obj in systems:
                try:
                    if getattr(obj, "data", None) and hasattr(obj.data, "materials"):
                        if obj.data.materials:
                            obj.data.materials[0] = mat
                        else:
                            obj.data.materials.append(mat)
                except Exception:  # noqa: BLE001
                    pass

    # Update the StrategySelector value
    if mat and mat.node_tree:
        selector = mat.node_tree.nodes.get("StrategySelector")
        if selector:
            strategy_map = {
                "CharacterRainbow": 0.0,
                "PatternCategories": 1.0,
                "PositionEncoding": 2.0,
            }
            selector.outputs[0].default_value = strategy_map.get(strategy_name, 0.0)


def unregister():  # pragma: no cover
    if not bpy:
        return
    # Remove scene property
    if hasattr(bpy.types.Scene, "eve_active_strategy"):
        del bpy.types.Scene.eve_active_strategy

    bpy.utils.unregister_class(EVE_OT_cancel_shader)
    bpy.utils.unregister_class(EVE_OT_apply_shader_modal)
