# Shader / Visualization Strategies

This document catalogs available visualization ("shader") strategies and the data attributes they map into material or node parameters.

## Built-in Strategies

### NamePatternCategory

- ID: `NamePatternCategory`
- Mapping: System name matched against relaxed regex categories:
  - `DASH` (AAA-BBB style) → Blue
  - `COLON` (A:1234 style) → Orange
  - `DOTSEQ` (A.AAAA.BBBB with 3–4 length segments) → Purple
  - `PIPE` (AAA|1BB where left = 3 alnum, right = digit + 2 alnum, e.g. MVT|1IT) → Green
  - `OTHER` fallback gray
- Each category maps to a fixed emission color; materials reused per category.
- Notes: Regexes intentionally broad to capture alphanumeric hybrids.

### Unified Nth Character Hue Strategies

Provided by `shaders/name_nth_char_hue.py`:

- IDs: `NameFirstCharHue` (alias), plus `NameChar1HueUnified` .. `NameChar9HueUnified`
- Mapping: Character at index N (0–8) in system name -> hue across wheel. Digits & punctuation mapped to stable sub‑ranges.
- Notes: Consolidates previously separate per-character modules into one deterministic generator. Materials are reused per (index, character) pair.

## Future Strategy Ideas

| Proposed ID | Concept | Mapping Sketch |
|-------------|---------|----------------|
| `HierarchyDepthGlow` | Depth-based glow | deeper = stronger outline/emission |
| `MoonCountSaturation` | Saturation by moon count | clamp moons 0–N to sat 0.2–1.0 |
| `SecondCharMetal` | Second char classification | groups letters into metallic values |
| `SecurityGradient` | Security scalar -> color ramp | 0.0 red -> 1.0 green |
| `OrbitIndexValue` | Orbital index -> value (brightness) | index scaled log or linear |
| `CharSequentialGradient` | Per-character layered gradient | stacked mix by char order |

## Implementation Guidelines

- Idempotent: Re-running should not create unbounded duplicate materials.
- Prefix: Material names start with `EVE_` + strategy id (unchanged by collection rename from `EVE_Systems` to `Frontier_Systems`).
- Reuse: Avoid creating one-off materials where a shared node group & per-object attribute could work (optimize later).
- Failure Safety: Wrap object iteration to skip missing data gracefully.

## Adding a New Strategy

1. Subclass `BaseShaderStrategy` in a module (e.g. `my_strategies.py`).
2. Decorate with `@register_strategy`.
3. Implement `build(context, objects_by_type)`.
4. Reference objects via keys: `systems` (future keys like `planets`, `moons` will appear once instancing is implemented). Objects live in the `Frontier_Systems` collection or hierarchical constellation collections. Use custom props `planet_count`, `moon_count` on each system if you need child metrics now.
5. Test in a small scene slice before running on full dataset.
6. Document here.

## Attribute-Driven Material (Current Implementation Basis)

The modal shader operator now assigns a single shared material `EVE_AttrDriven` to all system objects. Per-object variation is achieved via:

- Object color (from the Object Info node) → Emission color.
- Custom object property `eve_attr_strength` (accessed through an Attribute node) → Multiplied into the emission strength.

This replaces prior per-object material duplication and drastically reduces material count and memory overhead.

Global scaling of the emission intensity can be tuned in Add-on Preferences using the setting `Emission Strength Scale`.

Fallback behavior: if running outside Blender or node creation fails, shading silently degrades without throwing an exception.

## Optimization Considerations

- Prefer node group parameterization instead of copying full materials once scale grows > 100s of variants (e.g., refactor `CharIndexHue` later if growth accelerates).
- Consider encoding numeric attributes into custom vertex colors or geometry node attributes for more advanced shading.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Materials all identical | Attribute material missing or object colors unset | Re-run Apply Visualization; ensure objects have `obj.color` set |
| Excess materials count | Strategy creates new material every run | Add lookup + reuse for existing names |
| Performance drop | Extremely high emission strength scale | Lower `Emission Strength Scale` in preferences |
