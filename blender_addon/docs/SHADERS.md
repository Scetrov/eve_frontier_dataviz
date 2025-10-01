# Shader / Visualization Strategies

This document catalogs available visualization ("shader") strategies and the data attributes they map into material or node parameters.

## Built-in Strategies

### NameFirstCharHue

- ID: `NameFirstCharHue`
- Mapping: First letter (A–Z) -> hue across color wheel (HSV). Saturation fixed at 0.8, value 1.0.
- Objects: Systems (only systems instantiated currently; planets/moons available as counts on system objects).
- Notes: Creates a shared base material then per-initial copies to set emission color.

### ChildCountEmission

- ID: `ChildCountEmission`
- Mapping: Number of mesh children under a system object -> emission strength (0.1–10.0 bounded).
- Objects: Systems.
- Notes: Creates a base emission material and clones per distinct child count.

### NamePatternCategory

- ID: `NamePatternCategory`
- Mapping: System name matched against relaxed regex categories:
  - `DASH` (AAA-BBB style)
  - `COLON` (A:1234 style)
  - `DOTSEQ` (A.AAAA.BBBB with 3–4 length segments)
  - `OTHER` fallback gray
- Each category maps to a fixed emission color; materials reused per category.
- Notes: Regexes intentionally broad to capture alphanumeric hybrids.

### CharIndexHue

- ID: `CharIndexHue`
- Mapping: Aggregated per-character hue contributions (first 12 chars). Each character contributes a hue derived from (ordinal + index * offset). Final RGB is the averaged (clamped) accumulation.
- Digits compressed into a partial hue range; punctuation bucketed.
- Notes: Produces one variant material per system (hash-suffixed) — acceptable for current scale; future optimization could parameterize via node groups.

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
- Prefix: Material names start with `EVE_` + strategy id.
- Reuse: Avoid creating one-off materials where a shared node group & per-object attribute could work (optimize later).
- Failure Safety: Wrap object iteration to skip missing data gracefully.

## Adding a New Strategy

1. Subclass `BaseShaderStrategy` in a module (e.g. `my_strategies.py`).
2. Decorate with `@register_strategy`.
3. Implement `build(context, objects_by_type)`.
4. Reference objects via keys: `systems` (future keys like `planets`, `moons` will appear once instancing is implemented). Use custom props `planet_count`, `moon_count` on each system if you need child metrics now.
5. Test in a small scene slice before running on full dataset.
6. Document here.

## Optimization Considerations

- Prefer node group parameterization instead of copying full materials once scale grows > 100s of variants (e.g., refactor `CharIndexHue` later if growth accelerates).
- Consider encoding numeric attributes into custom vertex colors or geometry node attributes for more advanced shading.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Materials all identical | Strategy not setting per-object parameters | Validate material copy logic |
| Excess materials count | Strategy creates new material every run | Add lookup + reuse for existing names |
| Performance drop | Too many unique materials | Consolidate using node groups + drivers |
