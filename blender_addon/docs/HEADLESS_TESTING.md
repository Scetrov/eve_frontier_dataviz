# Headless Blender Testing Opportunities

This add-on already has extensive pure-Python coverage for the data layer and
helper calculators, but none of the tests currently drive Blender itself.
Adding a thin headless harness (``blender --background``) would let CI smoke
critical operator and shader paths without opening the UI.

## Current coverage

* ``blender_addon/tests/test_import_addon.py`` only verifies that the add-on
  package imports and exposes ``register`` / ``unregister`` symbols when
  ``bpy`` is absent, so no Blender APIs are exercised yet.【F:blender_addon/tests/test_import_addon.py†L1-L13】
* ``blender_addon/tests/test_data_loader.py`` and the property calculator test
  suites focus on the SQLite parsing logic and math helpers. They stop before
  the operators that push data into Blender collections or materials, leaving
  the 3D scene workflow untested.【F:blender_addon/tests/test_data_loader.py†L1-L157】

Because the repository already commits a tiny SQL fixture
(``blender_addon/tests/fixtures/mini.db.sql``), a headless Blender session can
re-use the same dataset to build deterministic scenes during automated checks.

## Suggested headless smoke tests

The following areas are prime candidates for a background Blender run that
executes real operators and inspects the resulting scene graph.

### 1. Data load and scene build pipeline

1. Launch Blender with ``--factory-startup`` and register the add-on.
2. Set the preference ``db_path`` to point at a temporary database built from ``mini.db.sql``.
3. Invoke ``EVE_OT_load_data`` so ``load_data`` / ``load_jumps`` fill the cache, then confirm the info report reflects the expected counts.【F:blender_addon/src/addon/operators/data_ops.py†L35-L73】
4. Call ``EVE_OT_build_scene_modal`` in a tight loop (triggering ``modal`` ticks manually) and assert that objects end up under the ``Frontier`` collection with the custom properties that the shaders rely on, such as ``eve_name_char_bucket`` or ``eve_is_proper_noun``.【F:blender_addon/src/addon/operators/build_scene_modal.py†L57-L200】
5. Optionally assert that ``clear_generated`` removes those collections so repeated runs stay idempotent.【F:blender_addon/src/addon/operators/_shared.py†L10-L79】

This exercise would catch regressions where collection wiring, property names,
or axis transforms break even though the pure-Python helpers still pass.

### 2. Node-group material authoring

1. Inside the same session, call ``ensure_strategy_node_groups`` and verify that the expected node groups are present in ``bpy.data.node_groups``.【F:blender_addon/src/addon/node_groups/__init__.py†L1-L65】
2. Trigger ``EVE_OT_apply_shader_modal`` (or directly call its internal ``_ensure_node_group_material`` helper) so the material with the "strategy selector" tree is created. Validate that the strategy nodes are present and linked, and that switching ``context.scene.eve_active_strategy`` updates the selector value.【F:blender_addon/src/addon/operators/shader_apply_async.py†L42-L315】
3. Run ``EVE_OT_repair_strategy_materials`` or the silent repair helper to make sure node references can be restored after intentionally breaking them, which mirrors what users experience when re-opening .blend files.【F:blender_addon/src/addon/operators/shader_apply_async.py†L497-L610】

A headless assertion around these materials would ensure strategy additions or
node name changes cannot silently ship without updating the repair logic.

### 3. End-to-end headless export

The repository already includes ``blender_addon/scripts/export_batch.py`` as an
example of batch rendering without a UI.【F:blender_addon/scripts/export_batch.py†L1-L48】
A simple smoke test could spin up Blender with a minimal scene (e.g., one mesh
linked to the generated material) and run this script via ``-P``. Assertions can
check that the script reports "Rendered" for the requested strategies and that
image files appear in a temporary directory. This would confirm that the shader
strategy registry stays in sync with the exported identifiers.

## Implementation tips

* Wrap the headless tests with ``pytest`` markers so they only run when a
  ``BLENDER_EXECUTABLE`` environment variable is available; fall back to the
  current pure-Python suite otherwise.
* Use ``subprocess.run([blender, "--background", "--factory-startup", ...])``
  to execute small helper scripts that orchestrate the steps above and report
  JSON to stdout for verification.
* Keep the generated .blend data in ``/tmp`` and clean it up to avoid polluting
  CI workspaces.

Adding even one or two of these smoke tests would dramatically increase
confidence in the add-on’s Blender integration without requiring manual UI
interaction.
