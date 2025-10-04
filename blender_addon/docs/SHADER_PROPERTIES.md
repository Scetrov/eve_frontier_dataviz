# Shader-Driven Visualization Properties

## Overview

To enable **instant strategy switching** without Python iteration, the scene builder pre-calculates visualization properties and stores them as custom properties on each system object. Shaders can then read these properties via **Attribute** nodes and use **ColorRamp** or **Switch** nodes to select visualization strategies instantly on the GPU.

## Property Reference

All properties are stored on system objects during scene construction (see `operators/build_scene_modal.py`).

### Legacy Properties (Backward Compatibility)

| Property | Type | Description |
|----------|------|-------------|
| `planet_count` | `int` | Number of planets in system |
| `moon_count` | `int` | Total moons across all planets |

### New Semantic Properties

| Property | Type | Range | Description |
|----------|------|-------|-------------|
| `eve_name_pattern` | `int` | 0-4 | Name pattern category (see below) |
| `eve_name_char_bucket` | `int` | -1 to 8 | First character bucket (see below) |
| `eve_planet_count` | `int` | 0+ | Number of planets (same as legacy) |
| `eve_moon_count` | `int` | 0+ | Number of moons (same as legacy) |
| `eve_is_blackhole` | `int` | 0 or 1 | 1 if blackhole system, 0 otherwise |
| `eve_is_proper_noun` | `int` | 0 or 1 | 1 if system name is a proper noun (Uppercase first letter + letters/spaces), 0 otherwise |

## Name Pattern Categories (`eve_name_pattern`)

Systems are classified into 5 pattern categories based on their naming convention:

| Value | Pattern | Example | Shader Color Suggestion |
|-------|---------|---------|------------------------|
| 0 | **DASH** | `ABC-123` (7 chars, dash at pos 3) | Blue |
| 1 | **COLON** | `AB:123` (6 chars with colon) | Orange |
| 2 | **DOTSEQ** | `1.2.3` (exactly 2 dots) | Purple |
| 3 | **PIPE** | `ABC\|123` (7 chars, pipe at pos 3) | Green |
| 4 | **OTHER** | Any other pattern | Gray |

### Usage in Shaders

```text
[Attribute "eve_name_pattern"] → [ColorRamp with 5 stops] → [Emission Color]
```

Configure ColorRamp stops:

- Position 0.0 → Blue (DASH)
- Position 0.25 → Orange (COLON)
- Position 0.5 → Purple (DOTSEQ)
- Position 0.75 → Green (PIPE)
- Position 1.0 → Gray (OTHER)

## Character Buckets (`eve_name_char_bucket`)

The first character of the system name is mapped to one of **9 alphabetic buckets** plus a fallback:

| Value | Characters | Example Systems | Suggested Hue |
|-------|------------|-----------------|---------------|
| -1 | **Empty/Invalid** | `""`, `"-ABC"` | Gray (neutral) |
| 0 | **A-C** | `Alpha`, `Bravo`, `Charlie` | Red |
| 1 | **D-F** | `Delta`, `Echo`, `Foxtrot` | Orange |
| 2 | **G-I** | `Golf`, `Hotel`, `India` | Yellow |
| 3 | **J-L** | `Juliet`, `Kilo`, `Lima` | Yellow-Green |
| 4 | **M-O** | `Mike`, `November`, `Oscar` | Green |
| 5 | **P-R** | `Papa`, `Quebec`, `Romeo` | Cyan |
| 6 | **S-U** | `Sierra`, `Tango`, `Uniform` | Blue |
| 7 | **V-X** | `Victor`, `Whiskey`, `Xray` | Purple |
| 8 | **Y-Z, 0-9** | `Yankee`, `Zulu`, `5-Test` | Magenta |

### Node Setup Example — Character Buckets

```text
[Attribute "eve_name_char_bucket"] → [Map Range -1..8 → 0..1] → [ColorRamp] → [Emission Color]
```

**ColorRamp Setup:**

1. Add 10 color stops (positions 0.0, 0.111, 0.222, ..., 1.0)
2. First stop (position 0.0) = neutral gray for fallback (-1)
3. Remaining 9 stops = rainbow gradient for buckets 0-8

**Alternative (simpler):** Use Math node to clamp negative values to 0, then divide by 8 to normalize 0-8 → 0-1, feed into HSV node's Hue input.

## Blackhole Detection (`eve_is_blackhole`)

Binary flag for known blackhole systems (currently 5 systems):

- `J055520`, `J110909`, `J164710`, `J174618`, `J175552`

### Node Setup Example — Blackhole

```text
[Attribute "eve_is_blackhole"] → [Mix Shader Factor] 
  → [Regular Emission] (factor=0)
  → [Bright Orange/Red Emission] (factor=1)
```

Or use as emission strength multiplier for dramatic effect.

## Strategy Switching Architecture

### Current Approach (Python Iteration)

```text
User clicks Apply → Python loops through 5000+ objects → Sets color attributes → Slow
```

### Future Approach (Shader Switching)

```text
User changes dropdown → Scene property updates → GPU instantly re-evaluates all shaders → Fast
```

### Implementation Plan

1. **Scene Property**: Add `scene["eve_active_strategy"]` (0-N for each strategy)

2. **Master Material**: Create single material with multiple branches:

   ```text
   [Scene Attribute "eve_active_strategy"] → [Switch Node]
     → Branch 0: Pattern-based coloring (uses eve_name_pattern)
     → Branch 1: Character-based coloring (uses eve_name_char_bucket)  
     → Branch 2: Child-count emission (uses eve_planet_count + eve_moon_count)
     → Branch N: Additional strategies...
   ```

3. **UI**: Simple dropdown in panel → updates scene property → instant visual update

### Automatic repair / legacy material upgrade

When the strategy dropdown changes the add-on will attempt to relink any broken `ShaderNodeGroup` references. If an older material lacks the new strategy branches (for example, the Proper Noun mix stage), the add-on will recreate the `EVE_NodeGroupStrategies` material and reapply it to all system objects so the newly added strategy is available immediately.

### Benefits

- ✅ **Instant switching**: No Python iteration, pure GPU
- ✅ **Real-time preview**: Animate strategy changes
- ✅ **Scalable**: Add strategies as new node branches
- ✅ **Maintainable**: Visual node editor vs complex Python
- ✅ **Performant**: Works with 10K+ objects smoothly

## Migration Path

### Phase 1: ✅ Pre-calculate Properties (Current)

- Scene builder stores semantic properties
- Legacy async operator still works

### Phase 2: Create Master Shader (Next)

- Build node-based material with strategy branches
- Add scene property for strategy selection
- Update UI panel with instant-switch dropdown

### Phase 3: Deprecate Async Operator (Future)

- Keep for backward compatibility
- Document new approach as preferred method

## Example Node Setups

### Pattern-Based Strategy

```text
[Attribute "eve_name_pattern"] 
  → [Map Range: 0..4 → 0..1] 
  → [ColorRamp] 
  → [Emission Color]
```

### Character Bucket Rainbow

```text
[Attribute "eve_name_char_bucket"]
  → [Math: Max with 0] (clamp -1 to 0)
  → [Math: Divide by 8] (normalize 0-8 to 0-1)
  → [Combine HSV] (Hue=input, Sat=1, Val=1)
  → [Emission Color]
```

### Child Count Emission Strength

```text
[Attribute "eve_planet_count"]
  → [Math: Add]
  ← [Attribute "eve_moon_count"]
  → [Map Range: 0..20 → 0.5..5.0]
  → [Emission Strength]
```

### Blackhole Override

```text
[Attribute "eve_is_blackhole"]
  → [Mix Shader Factor]
    → [Base Strategy Emission] (A)
    → [High-Intensity Orange Emission] (B)
```

## Technical Notes

- Properties are **calculated once** during scene build
- No runtime Python overhead after build completes
- Shaders can read properties via **Attribute** nodes (use property name exactly)
- Use **Map Range** nodes to normalize values for ColorRamps/HSV
- **Switch** or **Mix** nodes select between strategy branches based on scene property

## See Also

- `operators/property_calculators.py` - Property calculation functions
- `operators/build_scene_modal.py` - Where properties are assigned
- `tests/test_property_calculators.py` - Property calculation tests
