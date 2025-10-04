# Node-Based Visualization Strategies

## Overview

The EVE Frontier Data Visualizer uses a **node-based shader system** where all visualization strategies are implemented as Blender shader node groups. This enables real-time tweaking, innovation, and instant strategy switching without Python iteration.

## Architecture

### Core Principles

1. **All Strategies Are Node Groups**: Each visualization strategy is a reusable shader node group
2. **Shared Material**: All star systems share a single material instance
3. **Property-Driven**: Shaders read pre-calculated custom properties from objects
4. **Instant Switching**: Change strategy by updating a single material property

### Data Flow

```text
Scene Build (Python, once)
  ↓
Calculate Properties → Store on Objects
  ↓
[Custom Properties: eve_name_char_index_0_ord, eve_planet_count, etc.]
  ↓
Shader Nodes (GPU, every frame)
  ↓
[Attribute Nodes] → [Strategy Node Group] → [Emission Shader]
  ↓
Visual Output
```

## Custom Properties Reference

All properties are calculated during scene build and stored as custom properties on each system object.

### Character Index Properties

**Purpose**: Enable complex string-based visualizations without shader string parsing

| Property | Type | Range | Description |
|----------|------|-------|-------------|
| `eve_name_char_index_0_ord` | `float` | -1.0 to 1.0 | First character normalized ordinal |
| `eve_name_char_index_1_ord` | `float` | -1.0 to 1.0 | Second character normalized ordinal |
| `eve_name_char_index_2_ord` | `float` | -1.0 to 1.0 | Third character normalized ordinal |
| ... | ... | ... | ... |
| `eve_name_char_index_9_ord` | `float` | -1.0 to 1.0 | Tenth character normalized ordinal |

**Value Mapping:**

- **-1.0**: Non-alphanumeric character or position beyond string length
- **0.0 to 0.71**: Letter (A-Z)
  - `A` = 0.0 / 35.0 = 0.000
  - `B` = 1.0 / 35.0 = 0.029
  - `Z` = 25.0 / 35.0 = 0.714
- **0.74 to 1.0**: Digit (0-9)
  - `0` = 26.0 / 35.0 = 0.743
  - `1` = 27.0 / 35.0 = 0.771
  - `9` = 35.0 / 35.0 = 1.000

**Example**: System name "ABC-123"

```python
eve_name_char_index_0_ord = 0.000  # A
eve_name_char_index_1_ord = 0.029  # B
eve_name_char_index_2_ord = 0.057  # C
eve_name_char_index_3_ord = -1.0   # dash (non-alphanumeric)
eve_name_char_index_4_ord = 0.771  # 1
eve_name_char_index_5_ord = 0.800  # 2
eve_name_char_index_6_ord = 0.829  # 3
eve_name_char_index_7_ord = -1.0   # (beyond string)
eve_name_char_index_8_ord = -1.0   # (beyond string)
eve_name_char_index_9_ord = -1.0   # (beyond string)
```

### Semantic Properties

| Property | Type | Range | Description |
|----------|------|-------|-------------|
| `eve_name_pattern` | `int` | 0-4 | Name pattern category (DASH/COLON/DOTSEQ/PIPE/OTHER) |
| `eve_name_char_bucket` | `int` | -1 to 8 | First character bucket (9 groups + fallback) |
| `eve_planet_count` | `int` | 0+ | Number of planets in system |
| `eve_moon_count` | `int` | 0+ | Total number of moons across all planets |
| `eve_is_blackhole` | `int` | 0 or 1 | 1 if known blackhole system, 0 otherwise |

### Legacy Properties

| Property | Type | Description |
|----------|------|-------------|
| `planet_count` | `int` | Same as `eve_planet_count` (kept for compatibility) |
| `moon_count` | `int` | Same as `eve_moon_count` (kept for compatibility) |

## Creating Node-Based Strategies

### Strategy Node Group Template

Each strategy should be implemented as a **Shader Node Group** with this structure:

**Inputs:**

- Character index attributes (read via Attribute nodes)
- Semantic properties (read via Attribute nodes)

**Processing:**

- Math nodes, ColorRamps, Mix nodes, etc.
- Pure GPU operations, no Python

**Outputs:**

- `Color` socket → Emission color
- `Strength` socket → Emission strength

### Example Strategy 1: Character Rainbow

**Concept**: Color based on first character, brightness based on child count

```text
[Attribute "eve_name_char_index_0_ord"]
  → [Math: Max with 0.0] (clamp -1 to 0)
  → [Math: Multiply by 0.9] (normalize to hue range 0-0.9)
  → [Combine HSV] (Hue input, Sat=1.0, Val=1.0)
  → [Output: Color]

[Attribute "eve_planet_count"]
  → [Math: Add]
  ← [Attribute "eve_moon_count"]
  → [Map Range: 0-20 → 0.5-3.0]
  → [Output: Strength]
```

### Example Strategy 2: Pattern Categories

**Concept**: Distinct colors per naming pattern

```text
[Attribute "eve_name_pattern"]
  → [Map Range: 0-4 → 0-1]
  → [ColorRamp with 5 stops]
      Stop 0.0: Blue (DASH)
      Stop 0.25: Orange (COLON)
      Stop 0.5: Purple (DOTSEQ)
      Stop 0.75: Green (PIPE)
      Stop 1.0: Gray (OTHER)
  → [Output: Color]

[Constant: 1.5]
  → [Output: Strength]
```

### Example Strategy 3: Position-Based Encoding

**Concept**: Use multiple character positions for complex patterns

```text
[Attribute "eve_name_char_index_0_ord"] → [ColorRamp] → R channel
[Attribute "eve_name_char_index_1_ord"] → [ColorRamp] → G channel
[Attribute "eve_name_char_index_2_ord"] → [ColorRamp] → B channel
  → [Combine RGB]
  → [Output: Color]

[Attribute "eve_is_blackhole"]
  → [Math: Multiply by 10.0]
  → [Math: Add 1.0] (base strength)
  → [Output: Strength]

### Example Strategy 4: Proper Noun Highlight

**Concept**: Highlight systems whose names are proper nouns (first letter uppercase, remaining characters letters or spaces). This strategy reads `eve_is_proper_noun` (0 or 1) and mixes a bright highlight color when true.

``text
[Attribute "eve_is_proper_noun"]
  → [Mix: Neutral Gray ↔ Highlight Color]
  → [Output: Color]

[Attribute "eve_is_proper_noun"]
  → [Math: Multiply by 2.0]
  → [Math: Add 0.5]
  → [Output: Strength]
``
```

## Material Strategy Switching

### Current Implementation (Phase 2)

The add-on creates a single material `EVE_NodeGroupStrategies` with all strategy node groups (CharacterRainbow, PatternCategories, PositionEncoding, and ProperNounHighlight):

**Structure:**
**Structure:**

- **Character Rainbow** node group (outputs Color + Strength)
- **Pattern Categories** node group (outputs Color + Strength)
- **Position Encoding** node group (outputs Color + Strength)
- **Proper Noun Highlight** node group (outputs Color + Strength)
- **StrategySelector** value node (0.0, 1.0, 2.0 or 3.0)
- **Mix nodes** to switch between strategies based on selector value
- **Emission shader** receives final Color and Strength
- **Material Output**

**Switching mechanism:**

**Switching mechanism:**

- Two cascading Mix (RGBA) nodes for color
- Two cascading Mix (FLOAT) nodes for strength
- First mix: CharacterRainbow (0) vs PatternCategories (1)
- Second mix: Result vs PositionEncoding (2)
- Third mix: Result vs ProperNounHighlight (3)
- Factor values computed from StrategySelector

**To change strategy manually:**

1. Open Shading workspace
2. Select material `EVE_NodeGroupStrategies`
3. Find `StrategySelector` value node
4. Set value: 0.0 (Rainbow), 1.0 (Pattern), 2.0 (Position) or 3.0 (ProperNoun)

**Benefits:**

- All strategies pre-loaded and ready
- Instant switching (no material reassignment)
- Can manually tweak node groups in Blender
- GPU evaluates everything in parallel

### Future: UI-Based Switching (Phase 3)

**IMPLEMENTED!** The add-on now includes a scene property dropdown for strategy switching.

**Current UI Workflow:**

1. Open EVE Frontier panel in 3D Viewport sidebar
2. Build scene (if not already built)
3. Click "Apply (Async)" to create material with all strategies
4. Use "Strategy" dropdown to switch between Character Rainbow, Pattern Categories, Position Encoding, and Proper Noun Highlight.
5. Viewport updates instantly when dropdown changes

**Technical Implementation:**

- Scene property: `bpy.context.scene.eve_active_strategy` (EnumProperty)
- Update callback: `_on_strategy_change()` modifies StrategySelector value node
- Update callback: `_on_strategy_change()` modifies StrategySelector value node and performs automatic relinking/rebuild of material nodes when broken references or legacy materials are detected
- Panel: `panels.py` displays dropdown with `scene.eve_active_strategy`
- Persistence: Strategy choice saved with .blend file

**Benefits:**

- No manual node editing required
- Instant visual feedback
- Property persists across sessions
- Foundation for adding more strategies via UI

### Alternative: Scene Attribute with Switch Node (Future Enhancement)

Use drivers to blend between strategies based on scene properties:

```text
[Strategy A Node Group] → [Mix Shader Factor: driver]
[Strategy B Node Group] → [Mix Shader]
  → [Material Output]
```

**Driver Expression**: `bpy.context.scene.get("eve_strategy") == 0`

### Scene Property Setup

Add a custom property to the scene for strategy selection:

```python
bpy.context.scene["eve_active_strategy"] = 0  # Integer strategy index
```

Update UI panel to show dropdown that modifies this property.

## Implementation Checklist

### ✅ Phase 1: Properties (Complete)

- [x] Calculate character indices during scene build
- [x] Store `eve_name_char_index_0_ord` through `eve_name_char_index_9_ord` on objects
- [x] Maintain semantic properties (pattern, bucket, counts, blackhole)
- [x] Test property calculations

### ✅ Phase 2: Node Groups (Complete)

- [x] Create node group module structure (`node_groups/`)
- [x] Implement Character Rainbow strategy as node group
- [x] Implement Pattern Categories strategy as node group
- [x] Implement Position Encoding strategy as node group
- [x] Create material with Mix node switcher
- [x] Update operator to use node group material
- [x] Test node groups with Attribute nodes

### ✅ Phase 3: Material Switching (Complete)

- [x] Create master material with Mix node switcher
- [x] Add scene property `eve_active_strategy` for strategy selection
- [x] Update UI panel with strategy dropdown
- [x] Implement update callback for instant switching
- [x] Sync scene property when operator runs

### ✅ Phase 4: Legacy Cleanup (Complete)

- [x] Deprecate old Python strategy system (`shader_registry.py`, `shaders_builtin.py`)
- [x] Remove legacy strategy dropdown from panel
- [x] Clean up unused strategy modules (`shaders/` directory)
- [x] Update all documentation to reference node-based system only
- [x] Simplify operator to use scene property directly
- [x] Remove all WindowManager legacy properties

### 📋 Phase 5: Documentation & Examples (Planned)

- [ ] Record video tutorial of creating custom strategies
- [ ] Provide .blend file with example strategies
- [ ] Document node group input/output contracts
- [ ] Create gallery of community strategies
- [ ] Add troubleshooting guide for common issues

## Best Practices

### Property Usage

1. **Always check for -1.0**: Use Math Max node to clamp before normalization
2. **Normalize ranges**: Use Map Range nodes to convert property ranges to 0-1
3. **Handle edge cases**: Empty strings, missing properties, etc.

### Node Organization

1. **Use Frames**: Group related nodes in labeled frames
2. **Name sockets clearly**: "Character 0 Hue", "Child Count Strength", etc.
3. **Add Reroute nodes**: Keep noodles clean and readable
4. **Document assumptions**: Use note nodes to explain logic

### Performance

1. **Minimize shader complexity**: Fewer nodes = faster rendering
2. **Avoid conditionals**: Use Math Mix instead of branching where possible
3. **Reuse calculations**: Store intermediate values in Value nodes
4. **Test with full dataset**: Ensure shaders work with 10K+ objects

## Advanced Techniques

### Multi-Character Patterns

Combine multiple `char_index_N_ord` properties for complex patterns:

```text
# Detect "ABC-" pattern (A at pos 0, dash at pos 3)
[Attribute "eve_name_char_index_0_ord"]
  → [Math: Less Than 0.1] (is it A-C?)
  → [Math: Multiply]
  ← [Attribute "eve_name_char_index_3_ord"]
      → [Math: Equal -1.0] (is it non-alphanumeric?)
  → [Boolean output: 1.0 if matches, 0.0 otherwise]
```

### Gradient Transitions

Smooth transitions between strategy visualizations:

```text
[Scene Attribute "eve_strategy_blend"]
  → [Mix Shader Factor]
      A: [Strategy 1 Node Group]
      B: [Strategy 2 Node Group]
  → [Emission]
```

### Animated Strategies

Keyframe scene properties for animated visualizations:

```python
scene["eve_strategy_blend"] = 0.0  # Frame 1
scene.keyframe_insert(data_path='["eve_strategy_blend"]', frame=1)

scene["eve_strategy_blend"] = 1.0  # Frame 120
scene.keyframe_insert(data_path='["eve_strategy_blend"]', frame=120)
```

## Troubleshooting

### "Missing Data-Block" Errors After Parameter Changes

**Symptom**: Node groups show red "Missing Data-Block" error after changing strategy parameters (e.g., Character Index) or after adding new strategies

**Cause**: When node groups are deleted and recreated with new parameters, existing material node group references become invalid

**Technical Explanation**:

- Blender stores node group references by pointer
- When a node group is deleted, the pointer becomes invalid
- Even though a new node group with the same name is created, the old pointer doesn't automatically update

**Solution** (Automatic):

- The add-on automatically relinks node groups in `_on_strategy_param_change()`
- If you see this error, it means the relinking failed or was bypassed

Automatic repair and material recreation:

- When the strategy dropdown changes, `_on_strategy_change()` will attempt to relink any broken node group references (including `EVE_Strategy_ProperNounHighlight`).
- If the existing material is missing the newer mix stages or node groups (legacy material), the add-on will recreate the `EVE_NodeGroupStrategies` material and reapply it to all system objects so the new strategy is available.
- For an explicit manual repair, the add-on provides an operator `eve.repair_strategy_materials` which re-attaches node group data-blocks by name and updates the StrategySelector node label.

To run the explicit repair operator from Blender's Python console:

```python
import bpy
bpy.ops.eve.repair_strategy_materials()
```

**Manual Fix** (if needed):

1. Open Shader Editor
2. Find the node group nodes showing "Missing Data-Block"
3. Click the node group selector (browse icon)
4. Re-select the correct node group:
   - `EVE_Strategy_CharacterRainbow`
   - `EVE_Strategy_PatternCategories`
   - `EVE_Strategy_PositionEncoding`

**Prevention**:

- This is handled automatically by the add-on
- If you manually edit materials in Shader Editor, be aware that parameter changes will recreate node groups
- Always use the UI controls in the Visualization panel

**Note**: This issue has occurred before and will occur again when node groups must be recreated. The automatic relinking in `_on_strategy_param_change()` prevents it for normal usage, but manual shader edits may still encounter it.

### Nodes Become Unlinked After Strategy Changes

**Symptom**: Node connections are broken after switching strategies or changing parameters. Mix nodes lose their links to node group outputs.

**Cause**: When node groups are recreated (due to parameter changes), Blender's internal pointer system can invalidate not only the node group references themselves, but also the connections between nodes.

**Technical Explanation**:

- Node group recreation can break socket connections
- Even after relinking node groups (fixing "Missing Data-Block"), the links between nodes may be gone
- This affects the Mix nodes that switch between different strategy outputs

**Solution** (Automatic):

- The add-on automatically rebuilds connections in `_on_strategy_change()` when broken references are detected
- After relinking node groups, it reconstructs the entire connection graph:
  - CharacterRainbow Color → MixColor1 Input A
  - PatternCategories Color → MixColor1 Input B
  - MixColor1 Result → MixColor2 Input A
  - PositionEncoding Color → MixColor2 Input B
  - Similar path for Strength outputs
  - MixColor2/MixStrength2 results → Emission shader

**Manual Fix** (if needed):

1. Open Shader Editor
2. Manually reconnect each node group's outputs:
   - Drag Color output to corresponding Mix node input
   - Drag Strength output to corresponding Mix node input
3. Verify Emission shader receives final mixed outputs
4. Check viewport to confirm visualization works

**Prevention**:

- This is handled automatically when using UI controls
- The `_on_strategy_change()` callback detects broken references and rebuilds all connections
- Avoid manually editing the `EVE_NodeGroupStrategies` material structure

**Note**: This issue has occurred before and will occur again when node groups are recreated. The automatic detection and reconnection in `_on_strategy_change()` prevents it for normal usage, but deeply customized materials may require manual intervention.

### Attribute Node Shows "Attribute Not Found"

**Cause**: Property name mismatch or property not on object

**Solution**:

1. Check exact property name in outliner (case-sensitive!)
2. Verify property exists: Select object → Properties → Custom Properties
3. Rebuild scene if properties missing

### All Objects Same Color

**Cause**: Attribute node not reading per-object property

**Solution**:

1. Ensure Attribute Type = "OBJECT" (not "GEOMETRY")
2. Check that property varies across objects
3. Try different Attribute output socket (Fac vs Color vs Vector)

### -1.0 Values Causing Issues

**Cause**: Negative values in nodes expecting 0-1 range

**Solution**:

1. Add Math Max node after Attribute: `Max(attribute, 0.0)`
2. Use Map Range with clamping enabled
3. Handle -1 explicitly with Mix node

## See Also

- `SHADER_PROPERTIES.md` - Complete property reference
- `operators/property_calculators.py` - Property calculation source code
- `operators/build_scene_modal.py` - Where properties are assigned
- `tests/test_property_calculators.py` - Property calculation tests
