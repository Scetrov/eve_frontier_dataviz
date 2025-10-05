# Manual Testing Checklist

Quick regression tests to run before committing changes to volumetric shaders or strategy switching.

## Prerequisites

- Blender 4.5+ installed
- EVE Frontier addon installed and enabled
- Integration test database loaded (`tests/integration/fixtures/integration_test.db.sql`)

## Critical Test Cases

### 1. Volumetric Shader Nodes

**Test**: Volume atmosphere nodes are properly connected

1. Build scene (or create Frontier collection with a test object)
2. Click "Add Atmosphere"
3. Open Shading workspace
4. Select `EVE_VolumetricAtmosphere` cube
5. Open material `EVE_VolumetricMaterial`

**Expected**:
- ✅ Noise Texture node exists
- ✅ ColorRamp node exists  
- ✅ Mix (FLOAT) node exists
- ✅ Math (MULTIPLY) node exists
- ✅ Principled Volume node exists
- ✅ Material Output node exists
- ✅ Noise → ColorRamp → Math → Mix → Volume → Output (all connected, no orphaned nodes)
- ✅ Volume Density input shows connection (not default value)

**If nodes are disconnected**: Bug in volumetric.py - check Mix vs Math node types and socket indices

---

###  2. Strategy Switching (UniformOrange ↔ Others)

**Test**: Switching strategies preserves all node connections

1. Build scene with some systems
2. Click "Apply Visualization" 
3. Open Shading workspace
4. Select any system object
5. Open material `EVE_NodeGroupStrategies`
6. Note: All stars should be orange-red (UniformOrange is default)

**Initial state check**:
- ✅ 5 strategy node groups exist: UniformOrange, CharacterRainbow, PatternCategories, PositionEncoding, ProperNounHighlight
- ✅ 4 MixColor nodes exist (MixColor1-4)
- ✅ 4 MixStrength nodes exist (MixStrength1-4) 
- ✅ StrategySelector Value node set to 0.0
- ✅ All node groups have `node_tree` set (not "Missing Datablock")

**Switch to CharacterRainbow**:

7. In EVE Frontier panel, change Strategy dropdown to "Character Rainbow"
8. Check Shading workspace

**Expected**:

- ✅ StrategySelector Value node changed to 1.0
- ✅ All nodes still connected (count links before/after - should be same)
- ✅ Stars change color based on first character

**Switch back to UniformOrange**:

9. Change Strategy dropdown to "Uniform Orange"

**Expected**:

- ✅ StrategySelector Value node changed to 0.0
- ✅ All nodes still connected
- ✅ **Stars return to orange-red color** (regression check!)
- ✅ UniformOrange node group still has valid `node_tree` reference

**If UniformOrange doesn't restore**: Bug in shader_apply_async.py - check node_group_map includes UniformOrange, check reconnection logic handles 5-strategy chain

---

### 3. Manual Strategy Selector Test

**Test**: Manually changing StrategySelector value works

1. With material open in Shading workspace
2. Find `StrategySelector` Value node
3. Manually type different values:
   - 0.0 → Uniform Orange
   - 1.0 → Character Rainbow
   - 2.0 → Pattern Categories
   - 3.0 → Position Encoding
   - 4.0 → Proper Noun Highlight

**Expected**:
- ✅ Each value produces different visualization immediately
- ✅ No "Missing Datablock" errors on any strategy node group
- ✅ Viewport updates in real-time

---

## Regression Scenarios

### Scenario A: Broken Volume Nodes

**Symptoms**:
- Volume appears uniform (no noise variation)
- Blender console shows "Density input not connected"

**Root cause**: Mix/Math node confusion, wrong socket indices

**Files to check**: `operators/volumetric.py`

---

### Scenario B: UniformOrange Not Restoring

**Symptoms**:
- Switching to UniformOrange shows wrong colors
- UniformOrange node group shows "Missing Datablock" 

**Root cause**: Missing from `node_group_map` or reconnection logic doesn't handle 5-strategy chain

**Files to check**: `operators/shader_apply_async.py` (`_on_strategy_change` function)

---

### Scenario C: Strategy Node Groups Missing

**Symptoms**:
- Error when applying visualization
- Material exists but strategies don't switch

**Root cause**: Node groups not created or not linked to material

**Files to check**: 
- `node_groups/__init__.py` (ensure_strategy_node_groups)
- `node_groups/uniform_orange.py`

---

## Quick Smoke Test (30 seconds)

1. Load test database
2. Build scene
3. Add atmosphere → Check nodes connected
4. Apply visualization → Should be orange
5. Switch to Character Rainbow → Colors change
6. Switch back to Uniform Orange → **Orange restored!**

If all 6 steps pass: ✅ No regressions!
