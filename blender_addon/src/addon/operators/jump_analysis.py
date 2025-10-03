"""Jump network analysis operators for finding patterns and structures."""

from __future__ import annotations

try:  # pragma: no cover
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore

from .. import data_state

if bpy:  # Only define classes when Blender API is present

    class EVE_OT_highlight_triangle_islands(bpy.types.Operator):  # type: ignore[misc,name-defined]
        """Find and highlight isolated triangle loops in the jump network."""

        bl_idname = "eve.highlight_triangle_islands"
        bl_label = "Highlight Triangle Islands"
        bl_description = "Show only jump links that form isolated 3-system loops (A->B->C->A)"
        bl_options = {"REGISTER", "UNDO"}

        def execute(self, context):  # noqa: D401
            """Find triangle islands and hide all other jumps."""
            if not bpy or not hasattr(bpy, "data"):
                self.report({"ERROR"}, "Blender context not available")
                return {"CANCELLED"}

            # Get jump data
            jumps = data_state.get_loaded_jumps()
            if not jumps:
                self.report({"ERROR"}, "No jump data loaded. Load data and build jumps first.")
                return {"CANCELLED"}

            # Get system objects to map IDs to names
            systems = data_state.get_loaded_systems()
            if not systems:
                self.report({"ERROR"}, "No system data loaded")
                return {"CANCELLED"}

            # Build system ID to name mapping
            system_names = {sys.id: sys.name for sys in systems}

            # Build adjacency graph: system_id -> set of connected system_ids
            graph = {}
            for jump in jumps:
                from_id = jump.from_system_id
                to_id = jump.to_system_id

                # Add bidirectional edges
                if from_id not in graph:
                    graph[from_id] = set()
                if to_id not in graph:
                    graph[to_id] = set()

                graph[from_id].add(to_id)
                graph[to_id].add(from_id)

            # Find all triangles (3-cycles)
            triangles = set()
            for sys_a in graph:
                for sys_b in graph[sys_a]:
                    if sys_b <= sys_a:  # Avoid duplicates
                        continue
                    # Check if any neighbor of B connects back to A
                    for sys_c in graph[sys_b]:
                        if sys_c <= sys_a:  # Avoid duplicates
                            continue
                        if sys_c in graph[sys_a]:
                            # Found a triangle: A-B-C-A
                            triangle = tuple(sorted([sys_a, sys_b, sys_c]))
                            triangles.add(triangle)

            if not triangles:
                self.report({"WARNING"}, "No triangles found in jump network")
                return {"CANCELLED"}

            # Filter for ISOLATED triangles (each system has exactly 2 connections)
            isolated_triangles = []
            for triangle in triangles:
                sys_a, sys_b, sys_c = triangle
                # Check if each system has exactly 2 connections (only to the other 2 in triangle)
                if len(graph[sys_a]) == 2 and len(graph[sys_b]) == 2 and len(graph[sys_c]) == 2:
                    # Verify connections are only within the triangle
                    if (
                        graph[sys_a] == {sys_b, sys_c}
                        and graph[sys_b] == {sys_a, sys_c}
                        and graph[sys_c] == {sys_a, sys_b}
                    ):
                        isolated_triangles.append(triangle)

            if not isolated_triangles:
                self.report(
                    {"WARNING"},
                    f"Found {len(triangles)} triangles, but none are isolated (all have extra connections)",
                )
                return {"CANCELLED"}

            # Build set of system IDs that are part of isolated triangles
            triangle_systems = set()
            for triangle in isolated_triangles:
                triangle_systems.update(triangle)

            # Log the isolated triangles
            print(f"\n=== Found {len(isolated_triangles)} Isolated Triangle Islands ===")
            for i, triangle in enumerate(isolated_triangles, 1):
                sys_a, sys_b, sys_c = triangle
                name_a = system_names.get(sys_a, f"Unknown-{sys_a}")
                name_b = system_names.get(sys_b, f"Unknown-{sys_b}")
                name_c = system_names.get(sys_c, f"Unknown-{sys_c}")
                print(f"Triangle {i}: {name_a} <-> {name_b} <-> {name_c}")

            # Find jump line collection
            jumps_coll = bpy.data.collections.get("EVE_Jumps")  # type: ignore[union-attr]
            if not jumps_coll:
                self.report({"ERROR"}, "EVE_Jumps collection not found. Build jumps first.")
                return {"CANCELLED"}

            # Process all jump line objects
            hidden_count = 0
            shown_count = 0

            for obj in jumps_coll.objects:
                # Check if this jump connects two systems in our triangle set
                # Jump line names should contain system IDs or we can check custom properties
                # We'll need to check the actual line endpoints

                # Try to get system IDs from custom properties if they exist
                from_id = obj.get("from_system_id")
                to_id = obj.get("to_system_id")

                # If properties don't exist, try parsing from name
                if from_id is None or to_id is None:
                    # Jump lines are named like "JumpLine_FromID_ToID" or similar
                    # We may need to check the actual geometry instead
                    # For now, hide by default if we can't determine
                    obj.hide_set(True)
                    obj.hide_render = True
                    hidden_count += 1
                    continue

                # Check if both systems are in triangle set
                if from_id in triangle_systems and to_id in triangle_systems:
                    # Show this jump
                    obj.hide_set(False)
                    obj.hide_render = False
                    shown_count += 1
                else:
                    # Hide this jump
                    obj.hide_set(True)
                    obj.hide_render = True
                    hidden_count += 1

            self.report(
                {"INFO"},
                f"Found {len(isolated_triangles)} triangle islands "
                f"({len(triangle_systems)} systems, {shown_count} jumps shown, {hidden_count} hidden)",
            )
            return {"FINISHED"}

    class EVE_OT_show_all_jumps(bpy.types.Operator):  # type: ignore[misc,name-defined]
        """Show all jump lines (undo filtering)."""

        bl_idname = "eve.show_all_jumps"
        bl_label = "Show All Jumps"
        bl_description = "Unhide all jump lines"
        bl_options = {"REGISTER", "UNDO"}

        def execute(self, context):  # noqa: D401
            """Show all jump line objects."""
            if not bpy or not hasattr(bpy, "data"):
                self.report({"ERROR"}, "Blender context not available")
                return {"CANCELLED"}

            jumps_coll = bpy.data.collections.get("EVE_Jumps")  # type: ignore[union-attr]
            if not jumps_coll:
                self.report({"WARNING"}, "EVE_Jumps collection not found")
                return {"CANCELLED"}

            shown_count = 0
            for obj in jumps_coll.objects:
                obj.hide_set(False)
                obj.hide_render = False
                shown_count += 1

            self.report({"INFO"}, f"Showing all {shown_count} jump lines")
            return {"FINISHED"}


def register():  # pragma: no cover - Blender runtime usage
    """Register jump analysis operators."""
    if bpy:
        bpy.utils.register_class(EVE_OT_highlight_triangle_islands)
        bpy.utils.register_class(EVE_OT_show_all_jumps)


def unregister():  # pragma: no cover - Blender runtime usage
    """Unregister jump analysis operators."""
    if bpy:
        bpy.utils.unregister_class(EVE_OT_show_all_jumps)
        bpy.utils.unregister_class(EVE_OT_highlight_triangle_islands)
