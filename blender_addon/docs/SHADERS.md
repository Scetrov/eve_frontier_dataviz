# Visualization Strategies

This document describes the node-based visualization system and the available strategies for visualizing EVE Frontier data.

## System Overview

The EVE Frontier Data Visualizer uses a **GPU-driven, node-based shader system**:

- **All strategies are node groups**: Implemented as Blender shader node groups, not Python code
- **Single shared material**: All systems share `EVE_NodeGroupStrategies` material
- **Pre-calculated properties**: Object custom properties computed once during scene build
- **Instant switching**: Change visualization by updating a dropdown (no Python iteration)
- **GPU performance**: All color/strength calculations happen on GPU via shader nodes

## Built-in Strategies

### Character Rainbow

**ID**: `CharacterRainbow`  
**Node Group**: `EVE_Strategy_CharacterRainbow`

**Concept**: Rainbow color based on first character, brightness based on child count

**Mapping**:

- **Color**: First character ordinal → Hue (0-0.9 range for rainbow)
  - `A` = Red
  - `E` = Orange
  - `I` = Yellow
  - `M` = Green
  - `Q` = Cyan
  - `U` = Blue
  - `Y` = Purple
  - Non-alphanumeric = Clamped to `A` (red)
- **Strength**: `(planet_count + moon_count)` mapped to 0.5-3.0 range

**Use case**: Quick identification of systems by name prefix, with brighter stars indicating more orbital bodies.

### Pattern Categories

**ID**: `PatternCategories`  
**Node Group**: `EVE_Strategy_PatternCategories`

**Concept**: Distinct colors for different naming patterns

**Mapping**:

- **DASH** (`ABC-DEF`) → Blue (0.20, 0.50, 1.00)
- **COLON** (`A:1234`) → Orange (1.00, 0.55, 0.00)
- **DOTSEQ** (`A.BBB.CCC`) → Purple (0.60, 0.20, 0.85)
- **PIPE** (`ABC|1DE`) → Green (0.00, 0.90, 0.30)
- **OTHER** (fallback) → Gray (0.50, 0.50, 0.50)
- **Strength**: Constant 1.5

**Use case**: Visualize naming convention distribution across the galaxy, identify regions with similar naming schemes.

### Position Encoding

**ID**: `PositionEncoding`  
**Node Group**: `EVE_Strategy_PositionEncoding`

**Concept**: Multi-character encoding into RGB color space

**Mapping**:

- **Red channel**: First character ordinal (clamped 0-1)
- **Green channel**: Second character ordinal (clamped 0-1)
- **Blue channel**: Third character ordinal (clamped 0-1)
- **Strength**: Base 1.0, with 10x boost for black hole systems

**Use case**: Complex visual clustering by multi-character patterns, dramatic highlighting of special systems.

## Custom Properties Used

All strategies read from pre-calculated custom properties on system objects:

| Property | Range | Description |
|----------|-------|-------------|
| `eve_name_char_index_0_ord` | -1.0 to 1.0 | First character normalized ordinal |
| `eve_name_char_index_1_ord` | -1.0 to 1.0 | Second character normalized ordinal |
| `eve_name_char_index_2_ord` | -1.0 to 1.0 | Third character normalized ordinal |
| `eve_name_pattern` | 0-4 | Name pattern category (DASH/COLON/DOTSEQ/PIPE/OTHER) |
| `eve_planet_count` | 0+ | Number of planets in system |
| `eve_moon_count` | 0+ | Total number of moons |
| `eve_is_blackhole` | 0 or 1 | Black hole flag |

See `SHADER_PROPERTIES.md` for complete property reference.

## Switching Strategies

### Via UI Panel

1. Open 3D Viewport sidebar (`N` key)
2. Navigate to **EVE Frontier** tab
3. Build scene (if not already built)
4. Select strategy from **Strategy** dropdown:
   - Character Rainbow
   - Pattern Categories
   - Position Encoding
5. Click **Apply Visualization**
6. Viewport updates instantly

### Manual Node Editing (Advanced)

1. Switch to **Shading** workspace
2. Select any system object
3. Open material `EVE_NodeGroupStrategies`
4. Find `StrategySelector` value node
5. Set value:
   - `0.0` = Character Rainbow
   - `1.0` = Pattern Categories
   - `2.0` = Position Encoding
6. Viewport updates immediately

## Creating Custom Strategies

### Node Group Template

Create a new shader node group with this structure:

**Group Inputs**: (None - read from Attribute nodes)

**Processing**:

```text
[Attribute Nodes] → [Math/ColorRamp/Mix Nodes] → [Group Outputs]
```

**Group Outputs**:

- `Color` (RGBA socket) → Emission color
- `Strength` (Value socket) → Emission strength

### Example: Simple Bucket Strategy

```text
[Attribute "eve_name_char_bucket"]
  → [Math: Max(value, 0)] (clamp -1 to 0)
  → [Math: Divide by 8] (normalize 0-8 to 0-1)
  → [Combine HSV] (Hue input, S=1.0, V=1.0)
  → [Output: Color]

[Attribute "eve_planet_count"]
  → [Map Range: 0-10 → 0.5-2.0]
  → [Output: Strength]
```

### Integration Steps

1. Create node group in Blender (`EVE_Strategy_YourName`)
2. Add to `node_groups/__init__.py`:

   ```python
   def create_your_strategy():
       # Node group creation code
       pass
   ```

3. Add to switcher in `_ensure_node_group_material()`
4. Add enum item to `_node_strategy_enum_items()`
5. Test with small dataset first

## Future Strategy Ideas

| Proposed Strategy | Concept | Key Properties |
|------------------|---------|----------------|
| **Hierarchy Depth Glow** | Brightness by collection depth | Parent collection count |
| **Security Gradient** | Color ramp based on security status | `eve_security` (future) |
| **Moon Count Saturation** | Saturation by moon count | `eve_moon_count` |
| **Temporal Pulse** | Animated emission based on discovery date | `eve_discovery_date` (future) |
| **Distance Fade** | Opacity based on distance from center | Position coordinates |

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| All systems same color | Properties not calculated | Rebuild scene |
| Attribute not found error | Property name mismatch | Check exact property name (case-sensitive) |
| -1.0 values causing black | Negative clamp issue | Add `Math: Max(attr, 0)` node |
| Material not switching | Update callback failed | Manually edit StrategySelector value node |
| Performance drop | Complex node tree | Simplify shader, reduce math nodes |

## Implementation Notes

- **Idempotent**: Re-applying visualization is safe and doesn't duplicate materials
- **Deterministic**: Same input always produces same output
- **GPU-driven**: No Python loops over objects during visualization
- **Extensible**: Add strategies by creating node groups, not Python classes

## See Also

- `NODE_BASED_STRATEGIES.md` - Comprehensive node system guide
- `SHADER_PROPERTIES.md` - Complete property reference
- `operators/property_calculators.py` - Property calculation source
- `node_groups/__init__.py` - Node group creation code
