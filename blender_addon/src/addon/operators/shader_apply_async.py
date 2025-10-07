"""Asynchronous shader / visualization application."""

from __future__ import annotations

try:  # pragma: no cover  # noqa: I001 (dynamic bpy import grouping)
    import bpy  # type: ignore
except (ImportError, ModuleNotFoundError):  # pragma: no cover  # noqa: BLE001
    # Running in test/CI environment without Blender available
    bpy = None  # type: ignore

from typing import Optional

from ..node_groups import ensure_strategy_node_groups

if bpy:

    def _node_strategy_enum_items(self, context):  # pragma: no cover
        """Enum items for node-based strategies."""
        return [  # type: ignore
            (
                "UniformOrange",
                "Uniform Orange",
                "All stars with uniform orange-red color",
            ),
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
            (
                "ProperNounHighlight",
                "Proper Noun Highlight",
                "Highlight systems whose names are proper nouns",
            ),
        ]

    class EVE_OT_apply_shader_modal(bpy.types.Operator):  # type: ignore
        bl_idname = "eve.apply_shader_modal"
        bl_label = "Apply Visualization (Instant)"
        bl_description = "Apply GPU-driven node-based material to all system objects. Reads pre-calculated custom properties via Attribute nodes for instant visualization."
        bl_options = {"REGISTER"}

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
            except (AttributeError, RuntimeError, TypeError):  # noqa: BLE001
                # Best-effort: if Blender API access fails while building nodes, return None
                return None

        # --- Node Group Strategy Material Infrastructure ---
        def _ensure_node_group_material(
            self, strategy_name: str = "UniformOrange"
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
                    out.location = (1000, 0)

                    # Create node group references for each strategy
                    ng_uniform = nodes.new("ShaderNodeGroup")
                    ng_uniform.node_tree = bpy.data.node_groups.get("EVE_Strategy_UniformOrange")  # type: ignore[attr-defined]
                    ng_uniform.location = (-600, 400)
                    ng_uniform.name = "UniformOrange"

                    ng_char_rainbow = nodes.new("ShaderNodeGroup")
                    ng_char_rainbow.node_tree = bpy.data.node_groups.get(
                        "EVE_Strategy_CharacterRainbow"
                    )  # type: ignore[attr-defined]
                    ng_char_rainbow.location = (-600, 200)
                    ng_char_rainbow.name = "CharacterRainbow"

                    ng_pattern = nodes.new("ShaderNodeGroup")
                    ng_pattern.node_tree = bpy.data.node_groups.get(
                        "EVE_Strategy_PatternCategories"
                    )  # type: ignore[attr-defined]
                    ng_pattern.location = (-600, 0)
                    ng_pattern.name = "PatternCategories"

                    ng_position = nodes.new("ShaderNodeGroup")
                    ng_position.node_tree = bpy.data.node_groups.get(
                        "EVE_Strategy_PositionEncoding"
                    )  # type: ignore[attr-defined]
                    ng_position.location = (-600, -200)
                    ng_position.name = "PositionEncoding"

                    ng_proper = nodes.new("ShaderNodeGroup")
                    ng_proper.node_tree = bpy.data.node_groups.get(
                        "EVE_Strategy_ProperNounHighlight"
                    )  # type: ignore[attr-defined]
                    ng_proper.location = (-600, -400)
                    ng_proper.name = "ProperNounHighlight"

                    # Value node to control which strategy (0=Uniform, 1=Rainbow, 2=Pattern, 3=Position, 4=ProperNoun)
                    value_strategy = nodes.new("ShaderNodeValue")
                    value_strategy.location = (-1000, -500)
                    value_strategy.name = "StrategySelector"
                    value_strategy.label = (
                        "Strategy (0=Uniform, 1=Rainbow, 2=Pattern, 3=Position, 4=ProperNoun)"
                    )
                    value_strategy.outputs[0].default_value = 0.0  # Default to UniformOrange

                    # Mix 1: UniformOrange (0) vs CharacterRainbow (1)
                    mix_color_1 = nodes.new("ShaderNodeMix")
                    mix_color_1.data_type = "RGBA"
                    mix_color_1.location = (-200, 200)
                    mix_color_1.name = "MixColor1"
                    links.new(ng_uniform.outputs["Color"], mix_color_1.inputs[6])  # A
                    links.new(ng_char_rainbow.outputs["Color"], mix_color_1.inputs[7])  # B

                    # Factor for mix 1: clamp strategy to 0-1
                    clamp_1 = nodes.new("ShaderNodeClamp")
                    clamp_1.name = "Clamp_Strategy0to1"
                    clamp_1.location = (-350, -400)
                    clamp_1.inputs["Min"].default_value = 0.0
                    clamp_1.inputs["Max"].default_value = 1.0
                    links.new(value_strategy.outputs[0], clamp_1.inputs["Value"])
                    links.new(clamp_1.outputs["Result"], mix_color_1.inputs[0])  # Factor

                    # Mix 2: Result vs PatternCategories (2)
                    mix_color_2 = nodes.new("ShaderNodeMix")
                    mix_color_2.data_type = "RGBA"
                    mix_color_2.location = (0, 200)
                    mix_color_2.name = "MixColor2"
                    links.new(mix_color_1.outputs[2], mix_color_2.inputs[6])  # A
                    links.new(ng_pattern.outputs["Color"], mix_color_2.inputs[7])  # B

                    # Factor for mix 2: clamp (strategy - 1) to 0-1
                    math_sub_2 = nodes.new("ShaderNodeMath")
                    math_sub_2.name = "Math_SubStrategyMinus1"
                    math_sub_2.operation = "SUBTRACT"
                    math_sub_2.location = (-450, -500)
                    math_sub_2.inputs[1].default_value = 1.0
                    links.new(value_strategy.outputs[0], math_sub_2.inputs[0])

                    clamp_2 = nodes.new("ShaderNodeClamp")
                    clamp_2.name = "Clamp_Sub1to0_1"
                    clamp_2.location = (-250, -500)
                    clamp_2.inputs["Min"].default_value = 0.0
                    clamp_2.inputs["Max"].default_value = 1.0
                    links.new(math_sub_2.outputs[0], clamp_2.inputs["Value"])
                    links.new(clamp_2.outputs["Result"], mix_color_2.inputs[0])  # Factor

                    # Mix 3: Result vs PositionEncoding (3)
                    mix_color_3 = nodes.new("ShaderNodeMix")
                    mix_color_3.data_type = "RGBA"
                    mix_color_3.location = (200, 200)
                    mix_color_3.name = "MixColor3"
                    links.new(mix_color_2.outputs[2], mix_color_3.inputs[6])  # A
                    links.new(ng_position.outputs["Color"], mix_color_3.inputs[7])  # B

                    # Factor for mix 3: clamp (strategy - 2) to 0-1
                    math_sub_3 = nodes.new("ShaderNodeMath")
                    math_sub_3.name = "Math_SubStrategyMinus2"
                    math_sub_3.operation = "SUBTRACT"
                    math_sub_3.location = (-450, -600)
                    math_sub_3.inputs[1].default_value = 2.0
                    links.new(value_strategy.outputs[0], math_sub_3.inputs[0])

                    clamp_3 = nodes.new("ShaderNodeClamp")
                    clamp_3.name = "Clamp_Sub2to0_1"
                    clamp_3.location = (-250, -600)
                    clamp_3.inputs["Min"].default_value = 0.0
                    clamp_3.inputs["Max"].default_value = 1.0
                    links.new(math_sub_3.outputs[0], clamp_3.inputs["Value"])
                    links.new(clamp_3.outputs["Result"], mix_color_3.inputs[0])  # Factor

                    # Mix 4: Result vs ProperNounHighlight (4)
                    mix_color_4 = nodes.new("ShaderNodeMix")
                    mix_color_4.data_type = "RGBA"
                    mix_color_4.location = (400, 200)
                    mix_color_4.name = "MixColor4"
                    links.new(mix_color_3.outputs[2], mix_color_4.inputs[6])  # A
                    if bpy.data.node_groups.get("EVE_Strategy_ProperNounHighlight"):
                        links.new(ng_proper.outputs["Color"], mix_color_4.inputs[7])  # B

                    # Factor for mix 4: clamp (strategy - 3) to 0-1
                    math_sub_4 = nodes.new("ShaderNodeMath")
                    math_sub_4.name = "Math_SubStrategyMinus3"
                    math_sub_4.operation = "SUBTRACT"
                    math_sub_4.location = (-450, -700)
                    math_sub_4.inputs[1].default_value = 3.0
                    links.new(value_strategy.outputs[0], math_sub_4.inputs[0])

                    clamp_4 = nodes.new("ShaderNodeClamp")
                    clamp_4.name = "Clamp_Sub3to0_1"
                    clamp_4.location = (-250, -700)
                    clamp_4.inputs["Min"].default_value = 0.0
                    clamp_4.inputs["Max"].default_value = 1.0
                    links.new(math_sub_4.outputs[0], clamp_4.inputs["Value"])
                    links.new(clamp_4.outputs["Result"], mix_color_4.inputs[0])  # Factor

                    # Emission shader with constant strength
                    emission = nodes.new("ShaderNodeEmission")
                    emission.name = "EVE_Emission"
                    emission.location = (800, 0)
                    emission.inputs["Strength"].default_value = 2.0  # Constant emission strength
                    links.new(mix_color_4.outputs[2], emission.inputs["Color"])

                    # Connect to output
                    links.new(emission.outputs[0], out.inputs[0])

                # Repair/attach node group references for existing materials
                try:
                    if hasattr(bpy, "data") and mat and getattr(mat, "node_tree", None):
                        nt = mat.node_tree
                        for node in nt.nodes:
                            # Only update ShaderNodeGroup nodes we know about
                            try:
                                if getattr(node, "type", None) != "GROUP":
                                    continue
                                if node.name == "UniformOrange":
                                    node.node_tree = bpy.data.node_groups.get(
                                        "EVE_Strategy_UniformOrange"
                                    )  # type: ignore[attr-defined]
                                elif node.name == "CharacterRainbow":
                                    node.node_tree = bpy.data.node_groups.get(
                                        "EVE_Strategy_CharacterRainbow"
                                    )  # type: ignore[attr-defined]
                                elif node.name == "PatternCategories":
                                    node.node_tree = bpy.data.node_groups.get(
                                        "EVE_Strategy_PatternCategories"
                                    )  # type: ignore[attr-defined]
                                elif node.name == "PositionEncoding":
                                    node.node_tree = bpy.data.node_groups.get(
                                        "EVE_Strategy_PositionEncoding"
                                    )  # type: ignore[attr-defined]
                                elif node.name == "ProperNounHighlight":
                                    node.node_tree = bpy.data.node_groups.get(
                                        "EVE_Strategy_ProperNounHighlight"
                                    )  # type: ignore[attr-defined]
                            except (AttributeError, TypeError, RuntimeError) as e:
                                # best-effort: skip broken nodes but log minimal info
                                print(
                                    f"[EVEVisualizer][repair] Skipping node {getattr(node,'name',repr(node))}: {e}"
                                )
                                continue

                        # Update strategy selector value (if present)
                        selector = nt.nodes.get("StrategySelector")
                        if selector:
                            strategy_map = {
                                "UniformOrange": 0.0,
                                "CharacterRainbow": 1.0,
                                "PatternCategories": 2.0,
                                "PositionEncoding": 3.0,
                                "ProperNounHighlight": 4.0,
                            }
                            selector.outputs[0].default_value = strategy_map.get(strategy_name, 0.0)
                except (AttributeError, RuntimeError, TypeError) as e:
                    # Non-fatal: if anything goes wrong here, leave existing material as-is
                    print(
                        f"[EVEVisualizer][node_material] Warning while repairing material {getattr(mat,'name',repr(mat))}: {e}"
                    )
                    pass

                return mat
            except (AttributeError, RuntimeError, TypeError):  # noqa: BLE001
                # Best-effort: likely Blender API/attribute issues - surface as None
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
                except (AttributeError, RuntimeError, TypeError) as e:  # noqa: BLE001
                    print(
                        f"[EVEVisualizer][apply_attr_mat] Failed on object {getattr(o,'name',repr(o))}: {e}"
                    )
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
                except (AttributeError, RuntimeError, TypeError) as e:  # noqa: BLE001
                    print(
                        f"[EVEVisualizer][apply_node_mat] Failed on object {getattr(o,'name',repr(o))}: {e}"
                    )
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
        bl_description = "Cancel the asynchronous visualization application (if running)"
        bl_options = {"INTERNAL"}

        def execute(self, context):  # noqa: D401
            wm = context.window_manager
            if getattr(wm, "eve_shader_in_progress", False):
                wm.eve_shader_in_progress = False
                self.report({"INFO"}, "Cancellation requested")
            else:
                self.report({"INFO"}, "No visualization in progress")
            return {"FINISHED"}

    class EVE_OT_repair_strategy_materials(bpy.types.Operator):  # type: ignore
        """Repair ShaderNodeGroup references in existing materials.

        This operator looks for ShaderNodeGroup nodes named after known strategies
        and re-attaches their `node_tree` to the corresponding `EVE_Strategy_*`
        node groups when available. It also updates the StrategySelector value
        node label to include the ProperNoun mapping (0..3).
        """

        bl_idname = "eve.repair_strategy_materials"
        bl_label = "Repair Strategy NodeGroups"
        bl_description = "Reconnect ShaderNodeGroup references to strategy node groups after blend file reload or node group updates"
        bl_options = {"REGISTER"}

        def execute(self, context):  # noqa: D401
            repaired = 0
            try:
                if not hasattr(bpy, "data"):
                    self.report({"WARNING"}, "bpy not available")
                    return {"CANCELLED"}

                for mat in bpy.data.materials:  # type: ignore[attr-defined]
                    nt = getattr(mat, "node_tree", None)
                    if not nt:
                        continue
                    for node in nt.nodes:
                        try:
                            if getattr(node, "type", None) != "GROUP":
                                continue
                            # Map friendly node names to strategy node group names
                            if node.name == "CharacterRainbow":
                                node.node_tree = bpy.data.node_groups.get(
                                    "EVE_Strategy_CharacterRainbow"
                                )
                            elif node.name == "PatternCategories":
                                node.node_tree = bpy.data.node_groups.get(
                                    "EVE_Strategy_PatternCategories"
                                )
                            elif node.name == "PositionEncoding":
                                node.node_tree = bpy.data.node_groups.get(
                                    "EVE_Strategy_PositionEncoding"
                                )
                            elif node.name == "ProperNounHighlight":
                                node.node_tree = bpy.data.node_groups.get(
                                    "EVE_Strategy_ProperNounHighlight"
                                )
                            # Count repaired nodes
                            if node.node_tree:
                                repaired += 1
                        except (AttributeError, TypeError, RuntimeError) as e:
                            # Skip problematic nodes but continue processing others
                            print(
                                f"[EVEVisualizer][repair] Skipping node {getattr(node,'name',repr(node))}: {e}"
                            )
                            continue

                    # Update StrategySelector node label/value if present
                    selector = nt.nodes.get("StrategySelector")
                    if selector:
                        selector.label = "Strategy (0=Rainbow, 1=Pattern, 2=Position, 3=ProperNoun)"

                self.report({"INFO"}, f"Repaired {repaired} strategy node references")
                return {"FINISHED"}
            except (AttributeError, RuntimeError, TypeError) as e:  # noqa: BLE001
                # Non-fatal: if anything unexpected happens with Blender API, report and cancel
                self.report({"ERROR"}, f"Error repairing materials: {e}")
                return {"CANCELLED"}


def _repair_strategy_materials_silent():
    """Best-effort repair of ShaderNodeGroup references in all materials.

    Returns the number of successfully attached node groups.
    """
    repaired = 0
    try:
        if not hasattr(bpy, "data"):
            return repaired
        for mat in bpy.data.materials:  # type: ignore[attr-defined]
            nt = getattr(mat, "node_tree", None)
            if not nt:
                continue
            for node in nt.nodes:
                try:
                    if getattr(node, "type", None) != "GROUP":
                        continue
                    if node.name == "CharacterRainbow":
                        node.node_tree = bpy.data.node_groups.get("EVE_Strategy_CharacterRainbow")
                    elif node.name == "PatternCategories":
                        node.node_tree = bpy.data.node_groups.get("EVE_Strategy_PatternCategories")
                    elif node.name == "PositionEncoding":
                        node.node_tree = bpy.data.node_groups.get("EVE_Strategy_PositionEncoding")
                    elif node.name == "ProperNounHighlight":
                        node.node_tree = bpy.data.node_groups.get(
                            "EVE_Strategy_ProperNounHighlight"
                        )
                    if node.node_tree:
                        repaired += 1
                except (AttributeError, TypeError, RuntimeError) as e:
                    print(
                        f"[EVEVisualizer][repair_silent] Skipping node {getattr(node,'name',repr(node))}: {e}"
                    )
                    continue
            selector = nt.nodes.get("StrategySelector")
            if selector:
                selector.label = "Strategy (0=Rainbow, 1=Pattern, 2=Position, 3=ProperNoun)"
    except (AttributeError, RuntimeError, TypeError):
        # If Blender API errors occur, return the count we have so far
        return repaired
    return repaired


def register():  # pragma: no cover
    if not bpy:
        return

    print("[EVEVisualizer][shader_apply_async] Starting registration...")

    try:
        bpy.utils.register_class(EVE_OT_apply_shader_modal)
        print("[EVEVisualizer][shader_apply_async] Registered EVE_OT_apply_shader_modal")
    except (RuntimeError, ValueError) as e:
        print(
            f"[EVEVisualizer][shader_apply_async] ERROR registering EVE_OT_apply_shader_modal: {e}"
        )

    try:
        bpy.utils.register_class(EVE_OT_cancel_shader)
        print("[EVEVisualizer][shader_apply_async] Registered EVE_OT_cancel_shader")
    except (RuntimeError, ValueError) as e:
        print(f"[EVEVisualizer][shader_apply_async] ERROR registering EVE_OT_cancel_shader: {e}")

    try:
        bpy.utils.register_class(EVE_OT_repair_strategy_materials)
        print("[EVEVisualizer][shader_apply_async] Registered EVE_OT_repair_strategy_materials")
    except (RuntimeError, ValueError) as e:
        print(
            f"[EVEVisualizer][shader_apply_async] ERROR registering EVE_OT_repair_strategy_materials: {e}"
        )

    # Scene property for node-based strategy selection
    # Always set it - Blender will not duplicate if it already exists
    try:
        bpy.types.Scene.eve_active_strategy = bpy.props.EnumProperty(  # type: ignore[attr-defined]
            name="Active Strategy",
            description="Select visualization strategy",
            items=_node_strategy_enum_items,
            default=0,  # Index 0 = UniformOrange (first item)
            update=_on_strategy_change,
        )
        print("[EVEVisualizer][shader_apply_async] Registered eve_active_strategy property")
    except (AttributeError, TypeError, RuntimeError) as e:
        print(f"[EVEVisualizer][shader_apply_async] ERROR registering eve_active_strategy: {e}")
    # Attempt a best-effort repair of node group references in existing materials
    try:
        repaired_count = _repair_strategy_materials_silent()
        print(f"[EVEVisualizer] Repaired {repaired_count} node group references in materials")
    except (AttributeError, RuntimeError, TypeError):
        import traceback

        print("[EVEVisualizer] Error during silent repair of strategy materials:")
        traceback.print_exc()

    # Strategy-specific parameters
    try:
        bpy.types.Scene.eve_char_rainbow_index = bpy.props.IntProperty(  # type: ignore[attr-defined]
            name="Character Index",
            description="Which character to use for rainbow coloring (0=first, 1=second, etc.)",
            default=0,
            min=0,
            max=9,
            update=_on_strategy_param_change,
        )
        print("[EVEVisualizer][shader_apply_async] Registered eve_char_rainbow_index property")
    except (AttributeError, TypeError, RuntimeError) as e:
        print(f"[EVEVisualizer][shader_apply_async] ERROR registering strategy params: {e}")
        import traceback

        traceback.print_exc()


def _on_strategy_param_change(self, context):  # pragma: no cover
    """Update node group when strategy parameters change."""
    if not bpy or not hasattr(bpy, "data"):
        return

    strategy_name = context.scene.eve_active_strategy
    print(f"[EVEVisualizer][param_change] Updating strategy: {strategy_name}")

    # Update node groups with new parameters (updates in place, doesn't recreate)
    ensure_strategy_node_groups(context)

    # Fix material references after node group update
    mat_name = "EVE_NodeGroupStrategies"
    mat = bpy.data.materials.get(mat_name)  # type: ignore[attr-defined]

    if mat and mat.node_tree:
        nodes = mat.node_tree.nodes

        # Re-link all node group references to ensure they're up-to-date
        node_group_map = {
            "UniformOrange": "EVE_Strategy_UniformOrange",
            "CharacterRainbow": "EVE_Strategy_CharacterRainbow",
            "PatternCategories": "EVE_Strategy_PatternCategories",
            "PositionEncoding": "EVE_Strategy_PositionEncoding",
            "ProperNounHighlight": "EVE_Strategy_ProperNounHighlight",
        }

        for node_name, ng_name in node_group_map.items():
            node = nodes.get(node_name)
            if node and node.type == "GROUP":
                # Always refresh the reference to pick up node group changes
                node.node_tree = bpy.data.node_groups.get(ng_name)  # type: ignore[attr-defined]
                if node.node_tree:
                    print(f"[EVEVisualizer][param_change] Refreshed {ng_name}")

    print("[EVEVisualizer][param_change] Node group update complete")


def _on_strategy_change(self, context):  # pragma: no cover
    """Update material when strategy changes - creates material if needed."""
    if not bpy or not hasattr(bpy, "data"):
        return

    strategy_name = context.scene.eve_active_strategy
    print(f"[EVEVisualizer][strategy_change] Strategy changed to: {strategy_name}")

    # Ensure node groups exist
    ensure_strategy_node_groups(context)

    # Get or create the material
    mat_name = "EVE_NodeGroupStrategies"
    mat = bpy.data.materials.get(mat_name)  # type: ignore[attr-defined]

    if not mat:
        print("[EVEVisualizer][strategy_change] Material doesn't exist, creating it...")
        # Material doesn't exist yet - need to create it
        # Create temporary operator instance to use its method
        op = EVE_OT_apply_shader_modal()
        mat = op._ensure_node_group_material(strategy_name)
        print(f"[EVEVisualizer][strategy_change] Material created: {mat.name if mat else 'FAILED'}")

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

            print(
                f"[EVEVisualizer][strategy_change] Found {len(systems)} objects to apply material to"
            )

            # Debug: Check if objects have the required properties
            if systems:
                sample_obj = systems[0]
                print(
                    f"[EVEVisualizer][strategy_change] Sample object '{sample_obj.name}' properties:"
                )
                for key in sample_obj.keys():
                    if key.startswith("eve_"):
                        print(f"  {key}: {sample_obj[key]}")

            # Assign material to all systems
            for obj in systems:
                try:
                    if getattr(obj, "data", None) and hasattr(obj.data, "materials"):
                        if obj.data.materials:
                            obj.data.materials[0] = mat
                        else:
                            obj.data.materials.append(mat)
                except (AttributeError, RuntimeError, TypeError):  # noqa: BLE001
                    # Best-effort assignment failure - skip this object
                    pass
    else:
        print("[EVEVisualizer][strategy_change] Material already exists, updating selector...")

    # If the material exists but is missing newer nodes (MixColor3/ProperNounHighlight),
    # recreate it so the proper noun strategy is available.
    if mat and mat.node_tree:
        nodes = mat.node_tree.nodes
        missing_critical = False
        for name in ("MixColor3", "ProperNounHighlight"):
            if not nodes.get(name):
                missing_critical = True
                break
        if missing_critical:
            print(
                "[EVEVisualizer][strategy_change] Detected legacy material without ProperNoun nodes — recreating material"
            )
            # recreate material and reapply to systems
            op = EVE_OT_apply_shader_modal()
            new_mat = op._ensure_node_group_material(strategy_name)
            if new_mat:
                mat = new_mat
                # Re-apply to all system objects
                systems = []
                frontier = bpy.data.collections.get("Frontier")  # type: ignore[union-attr]
                if frontier:

                    def _collect_recursive(collection):
                        systems.extend(collection.objects)
                        for child in collection.children:
                            _collect_recursive(child)

                    _collect_recursive(frontier)

                for obj in systems:
                    try:
                        if getattr(obj, "data", None) and hasattr(obj.data, "materials"):
                            if obj.data.materials:
                                obj.data.materials[0] = mat
                            else:
                                obj.data.materials.append(mat)
                    except (AttributeError, RuntimeError, TypeError):  # noqa: BLE001
                        # Best-effort assignment failure - skip this object
                        pass

    # Update the StrategySelector value AND fix broken node group references
    if mat and mat.node_tree:
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Fix broken node group references (Missing Data nodes)
        node_group_map = {
            "UniformOrange": "EVE_Strategy_UniformOrange",
            "CharacterRainbow": "EVE_Strategy_CharacterRainbow",
            "PatternCategories": "EVE_Strategy_PatternCategories",
            "PositionEncoding": "EVE_Strategy_PositionEncoding",
            "ProperNounHighlight": "EVE_Strategy_ProperNounHighlight",
        }

        needs_reconnect = False
        for node_name, ng_name in node_group_map.items():
            node = nodes.get(node_name)
            if node and node.type == "GROUP":
                # Check if node_tree reference is broken (None)
                if node.node_tree is None:
                    print(
                        f"[EVEVisualizer][strategy_change] Fixing broken reference for {node_name}"
                    )
                    node.node_tree = bpy.data.node_groups.get(ng_name)  # type: ignore[attr-defined]
                    if node.node_tree:
                        print(f"[EVEVisualizer][strategy_change] Successfully re-linked {ng_name}")
                        needs_reconnect = True
                    else:
                        print(
                            f"[EVEVisualizer][strategy_change] ERROR: Node group {ng_name} not found!"
                        )

        # Rebuild connections if we re-linked any node groups
        if needs_reconnect:
            print("[EVEVisualizer][strategy_change] Rebuilding node connections...")

            # Get all the nodes we need
            ng_uniform = nodes.get("UniformOrange")
            ng_char_rainbow = nodes.get("CharacterRainbow")
            ng_pattern = nodes.get("PatternCategories")
            ng_position = nodes.get("PositionEncoding")
            ng_proper = nodes.get("ProperNounHighlight")
            mix_color_1 = nodes.get("MixColor1")
            mix_color_2 = nodes.get("MixColor2")
            mix_color_3 = nodes.get("MixColor3")
            mix_color_4 = nodes.get("MixColor4")

            # Reconnect color paths (5-strategy chain)
            # Mix1: UniformOrange vs CharacterRainbow
            if ng_uniform and ng_char_rainbow and mix_color_1:
                # Clear existing connections to these inputs
                for input_socket in [mix_color_1.inputs[6], mix_color_1.inputs[7]]:
                    for link in input_socket.links:
                        links.remove(link)
                # Reconnect
                links.new(ng_uniform.outputs["Color"], mix_color_1.inputs[6])  # A
                links.new(ng_char_rainbow.outputs["Color"], mix_color_1.inputs[7])  # B
                print("[EVEVisualizer][strategy_change] Reconnected MixColor1")

            # Mix2: Result vs PatternCategories
            if mix_color_1 and ng_pattern and mix_color_2:
                # Clear existing connections
                for input_socket in [mix_color_2.inputs[6], mix_color_2.inputs[7]]:
                    for link in input_socket.links:
                        links.remove(link)
                # Reconnect
                links.new(mix_color_1.outputs[2], mix_color_2.inputs[6])  # A
                links.new(ng_pattern.outputs["Color"], mix_color_2.inputs[7])  # B
                print("[EVEVisualizer][strategy_change] Reconnected MixColor2")

            # Mix3: Result vs PositionEncoding
            if mix_color_2 and ng_position and mix_color_3:
                # Clear existing connections
                for input_socket in [mix_color_3.inputs[6], mix_color_3.inputs[7]]:
                    for link in list(input_socket.links):
                        links.remove(link)
                # Reconnect
                links.new(mix_color_2.outputs[2], mix_color_3.inputs[6])  # A
                links.new(ng_position.outputs["Color"], mix_color_3.inputs[7])  # B
                print("[EVEVisualizer][strategy_change] Reconnected MixColor3")

            # Mix4: Result vs ProperNounHighlight
            if mix_color_3 and mix_color_4:
                # Clear existing connections for MixColor4 inputs
                for input_socket in [mix_color_4.inputs[6], mix_color_4.inputs[7]]:
                    for link in list(input_socket.links):
                        links.remove(link)
                # Reconnect previous result into MixColor4 A
                links.new(mix_color_3.outputs[2], mix_color_4.inputs[6])
                # If proper noun group present, connect it as B
                if ng_proper and ng_proper.outputs.get("Color"):
                    links.new(ng_proper.outputs["Color"], mix_color_4.inputs[7])
                print("[EVEVisualizer][strategy_change] Reconnected MixColor4")

            # Note: Strength mixing removed - using constant emission strength instead

        selector = mat.node_tree.nodes.get("StrategySelector")
        if selector:
            strategy_map = {
                "UniformOrange": 0.0,
                "CharacterRainbow": 1.0,
                "PatternCategories": 2.0,
                "PositionEncoding": 3.0,
                "ProperNounHighlight": 4.0,
            }
            new_value = strategy_map.get(strategy_name, 0.0)
            selector.outputs[0].default_value = new_value
            print(f"[EVEVisualizer][strategy_change] Updated StrategySelector to {new_value}")
        else:
            print("[EVEVisualizer][strategy_change] ERROR: StrategySelector node not found!")
    else:
        print("[EVEVisualizer][strategy_change] ERROR: Material or node tree not found!")


def unregister():  # pragma: no cover
    if not bpy:
        return
    # Remove scene properties
    if hasattr(bpy.types.Scene, "eve_active_strategy"):
        del bpy.types.Scene.eve_active_strategy
    if hasattr(bpy.types.Scene, "eve_char_rainbow_index"):
        del bpy.types.Scene.eve_char_rainbow_index

    bpy.utils.unregister_class(EVE_OT_cancel_shader)
    bpy.utils.unregister_class(EVE_OT_apply_shader_modal)
