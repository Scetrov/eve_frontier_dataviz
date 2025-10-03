"""Headless batch export example.

Run with:
    blender -b some_scene.blend -P scripts/export_batch.py -- --modes CharacterRainbow PatternCategories

This script applies node-based visualization strategies and renders stills.
"""

import argparse

import bpy

from addon.shader_registry import get_strategy


def apply_strategy(strategy_id: str):
    strat = get_strategy(strategy_id)
    if not strat:
        print(f"Strategy {strategy_id} not found")
        return
    objs_by_type = {"systems": []}
    systems_coll = bpy.data.collections.get("EVE_Systems")
    if systems_coll:
        objs_by_type["systems"].extend(systems_coll.objects)
    strat.build(bpy.context, objs_by_type)
    print(f"Applied {strategy_id}")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--modes", nargs="+", default=["CharacterRainbow"])
    parser.add_argument("--output", default="renders")
    args = parser.parse_args(argv)
    out_dir = args.output
    import os

    os.makedirs(out_dir, exist_ok=True)

    for mode in args.modes:
        apply_strategy(mode)
        filepath = os.path.join(out_dir, f"frame_{mode}.png")
        bpy.context.scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True)
        print(f"Rendered {filepath}")


if __name__ == "__main__":
    main()
