# Features Guide

This document describes the user-facing features of the EVE Frontier Data Visualizer add-on.

## Core Visualization Features

### System Visualization

**Overview**: Visualize 24,000+ star systems from EVE Frontier's database as 3D objects in Blender.

**Key Capabilities**:

- Load and parse SQLite database (`static.db`)
- Create system objects with accurate 3D positions
- Store pre-calculated visualization properties on objects
- Apply GPU-driven shader strategies for instant visual switching

**Usage**:

1. Set database path in Preferences
2. Click `Load / Refresh Data`
3. Click `Build Scene`
4. Systems appear in `Frontier` collection (hierarchical: `Frontier/Region/Constellation/Systems`) and a new top-level `SystemsByName` grouping is created. By default the flat `Frontier` collection (and its region/constellation parents) are hidden on import so users can control visibility via `SystemsByName` subcollections. Each `SystemsByName` child corresponds to a naming-pattern bucket (DASH, COLON, DOTSEQ, PIPE, OTHER).

### SystemsByName & Filters

To make large-scale visibility control easy, the build now creates a top-level `SystemsByName` collection
containing five child collections (DASH, COLON, DOTSEQ, PIPE, OTHER). By default the `Frontier` hierarchy
(Region/Constellation) is hidden so these buckets control what's visible in the viewport and render.

Use the Filters panel (3D View → Sidebar → EVE Frontier → Filters) to:

- Toggle individual buckets via checkboxes (session-only toggles affect the current blend file).
- Use Show All / Hide All to persist a default across Blender sessions — these bulk actions update
  the add-on preferences so your chosen default persists across restarts.

Note: Manual checkbox toggles do not automatically update saved preferences. Use Show All / Hide All
to change the persistent defaults.

**Properties Stored** (per system):

- Position (X, Y, Z coordinates scaled to 1e-18 for Blender units)
- Name character indices (first 10 characters as normalized ordinals)
- Pattern category (DASH/COLON/DOTSEQ/PIPE/OTHER)
- Child counts (planets, moons)
- Black hole flag (IDs 30000001-30000003)

### Node-Based Visualization Strategies

**Overview**: Three built-in GPU-driven shader strategies with instant switching.

#### Character Rainbow

**Purpose**: Quick identification by name prefix with brightness indicating complexity

**Visual Encoding**:

- **Color**: Selected character determines hue (A=red, M=green, Y=purple)
- **Brightness**: Planet + moon count (0.5-3.0 range)

**Customization**:

- **Character Index** (0-9): Choose which character to use for coloring
  - 0 = First character (default)
  - 1 = Second character
  - 2 = Third character, etc.
- **Use Case**: Change index to find patterns in different name positions

**Example**: Index 0 → "**A**BC-123" uses 'A' for color, Index 1 → "A**B**C-123" uses 'B' for color

#### Pattern Categories

**Purpose**: Visualize naming convention distribution

**Visual Encoding**:

- **DASH** (`ABC-DEF`) → Blue
- **COLON** (`A:1234`) → Orange
- **DOTSEQ** (`A.BBB.CCC`) → Purple
- **PIPE** (`ABC|1DE`) → Green
- **OTHER** → Gray

**Use Case**: "Which regions use dash-separated names?" → Find blue clusters

#### Position Encoding

**Purpose**: Complex multi-character pattern visualization with RGB encoding

**Visual Encoding**:

- **R channel**: 1st character ordinal (normalized 0-1)
- **G channel**: 2nd character ordinal (normalized 0-1)
- **B channel**: 3rd character ordinal (normalized 0-1)
- **Intensity**: 10x boost for black hole systems

**Key Difference from Character Rainbow**:

- Uses **three characters simultaneously** to create RGB combinations
- Produces unique colors for unique 3-character prefixes
- Character Rainbow uses **one character** for hue only

**Use Case**: "Show me maximum visual variety across name prefixes" → Each ABC, ABD, ABE gets distinct color

**Switching Strategies**:

- Select from dropdown in **Visualization** section
- Adjust strategy-specific parameters (e.g., Character Index for Character Rainbow)
- Viewport updates instantly on GPU when parameters change

## Navigation & Analysis Features

### Reference Points (Navigation Landmarks)

**Overview**: Add labeled markers at significant locations to aid spatial orientation.

**Features**:

- **Black Hole Labels**: Red text objects at 3 black hole systems (A 2560, M 974, U 3183)
- **Constellation Centers**: Cyan text labels at up to 10 constellation centers
- **Billboard Constraints**: Labels always face camera
- **Configurable Size**: Default 50 Blender units

**Usage**:

1. Build scene first
2. Click `Add Reference Points` in Visualization section
3. Navigate viewport - labels remain readable
4. Click remove button (X) to clear

**Use Case**: "Where am I in this 190-unit diameter galaxy?" → Look for nearest cyan label

**Technical Details**:

- Creates `EVE_ReferencePoints` collection
- Text objects with emission materials (no external light needed)
- Black holes: Spectral class O0, infinite mass, zero luminosity
- Constellation centers: Geometric center of member systems

### Jump Network Visualization

**Overview**: Visualize stargate connections between systems as 3D curves.

**Features**:

- **Jump Lines**: Cyan curves connecting systems with stargates
- **Custom Properties**: Each jump stores from/to system IDs
- **Thickness Control**: Bevel depth 0.005 (scaled for 1e-18 coordinates)
- **Toggle Visibility**: Show/hide all jumps via collection

**Usage**:

1. Build scene (loads jump data automatically)
2. Click `Build Jumps` in Visualization section
3. Click eye icon to toggle visibility

**Use Case**: "What does the gate network topology look like?" → See connection patterns

**Technical Details**:

- Creates `EVE_Jumps` collection
- NURBS curve objects with circular bevel profile
- Emission shader (cyan, strength 0.5)
- Properties: `from_system_id`, `to_system_id` for filtering

### Triangle Island Detection

**Overview**: Find isolated 3-system loops in the jump network (graph analysis feature).

**Purpose**: Identify disconnected triangular regions (systems with exactly 2 connections forming a closed loop).

**Algorithm**:

1. Build adjacency graph from jump data
2. Find all 3-cycles (triangles: A↔B↔C↔A)
3. Filter for **isolated** triangles (each system has exactly 2 connections)
4. Hide all other jump lines
5. Log system names to console

**Usage**:

1. Build jumps first
2. Click `Triangle Islands` in Visualization section
3. Console shows: `Found N triangle islands`
4. Viewport shows only isolated triangle jumps
5. Click eye icon to restore all jumps

**Use Case**: "Are there any small disconnected regions?" → Find orphaned triangle networks

**Example Output**:

```text
=== Found 2 Isolated Triangle Islands ===
Triangle 1: SystemA <-> SystemB <-> SystemC
Triangle 2: SystemX <-> SystemY <-> SystemZ
Info: Found 2 triangle islands (6 systems, 6 jumps shown, 14578 hidden)
```

**Technical Notes**:

- Strict isolation requirement (no connections outside triangle)
- Uses custom properties for efficient filtering
- Graph algorithm runs in Python (not GPU)

## Camera & View Features

### Camera Setup

**Automatic Camera**: Click `Add Camera` creates camera with proper clipping for massive scale.

**Key Settings**:

- **Clip Start**: 0.01 (can get very close to stars)
- **Clip End**: 300 (covers full 190-unit diagonal + margin)
- **Position**: Strategic placement for overview

**Use Case**: Avoid clipping issues when navigating vast distances

### Viewport Helpers

**Frame All Stars**: Click to zoom viewport to fit all systems (View → Frame Selected equivalent)

**Set Background to Black**: Solid black for star visibility

**Apply Space HDRI**: Load space environment texture (requires HDRI file)

**Toggle Grid/Axis**: Hide Blender's overlay grid for clean renders

## Data Management Features

### Database Loading

**Path Configuration**:

- Set in Add-on Preferences (`Edit > Preferences > Add-ons > EVE Frontier`)
- Click `Locate` button to browse
- Environment variable `EVE_STATIC_DB` overrides preference
- Default: `~/Documents/static.db`

**Load / Refresh Data**:

- Parses SQLite database
- Loads 24,426 systems with spatial data
- Loads jump network data
- Caches in memory for fast rebuilds
- Shows summary in info panel

**Clear Scene**:

- Removes all `EVE_*` collections
- Preserves user objects
- Safe to re-run

### Scene Building

**Modal Progress Operator**:

- Asynchronous build (doesn't freeze UI)
- Progress bar and cancel button
- Batch size: 2,500 systems per update
- Creates only system objects (planets/moons as counts)

**Sampling**:

- **Build Percentage**: 0.0-1.0 (default 1.0 = all systems)
- Useful for testing with subset
- Random sampling for representative distribution

**Scale Factor**:

- Default: 1e-18 (converts real-space meters to Blender units)
- Database coordinates: ~7.7e+16 to 7.7e+16 meters
- Blender coordinates: -77 to +77 units (154 unit range)
- **Do not change unless you understand coordinate system**

## Lighting & Atmosphere Features

### Black Hole Lights

**Overview**: Add point lights at three black hole systems.

**Features**:

- Light radius: 500 units
- Light power: 1,000,000 (very bright)
- Positioned at black hole coordinates

**Usage**:

- Click `Add Black Hole Lights`
- Click X to remove

**Use Case**: Illuminate nearby systems, create dramatic lighting

### Volumetric Atmosphere (Experimental)

**Overview**: Add world volume shader for atmospheric effect.

**Note**: Performance-intensive, use with caution on large scenes.

**Usage**:

- Click `Add Atmosphere`
- Adjust World shader nodes for desired effect
- Click X to remove

## Scaling & Performance

### Scale Context

**Object Count**: 25,000+ objects minimum (24,426 systems + jump lines + future planets/moons)

**Critical Performance Rule**: At this scale, O(n²) operations are **impossible**—they will hang Blender for minutes or crash. All addon operations are designed for O(n) or better complexity.

### Coordinate System

**Database Scale**: EVE Frontier uses real-world astronomical units (meters)

**Blender Scale**: 1e-18 multiplier converts to manageable Blender units

**Map Dimensions** (with 1e-18 scale):

- Radius from center: 77.37 units
- Full diagonal: 190.41 units
- System spacing: ~0.01 to 10 units typical

**Visual Parameters** (proportional to scale):

- Star radius: 0.02 units
- Jump line thickness: 0.005 units
- Light radius: 500 units
- Label size: 50 units

### Performance Considerations

**System Count**: 24,426 base objects + jump lines = 25,000+ total

**Recommendations**:

- Use `Build Percentage` < 1.0 for testing
- Hide jumps collection when not needed
- Disable volumetric effects for editing
- Use node-based strategies (GPU-accelerated)

**Fast Operations** (GPU/cached, O(1) or O(n)):

- Strategy switching (instant, GPU shader swap)
- Jump visibility toggle (instant, collection hide)
- Viewport navigation (GPU accelerated)
- Clear scene (<1 second, batch removal)

**Moderate Operations** (CPU/Python, O(n)):

- Scene build (30-60 seconds, modal with progress)
- Jump network creation (15-30 seconds, modal)
- Shader application (5-10 seconds, modal)

**Slow Operations** (CPU/Python, complex algorithms):

- Triangle detection (5-10 seconds, graph analysis)

**Memory Requirements**:

- 16GB+ RAM recommended for full dataset
- Expected high memory usage with 25k+ objects
- Consider reducing build percentage on lower-spec systems

## Export & Automation Features

### Headless Rendering

**Script**: `scripts/export_batch.py`

**Usage**:

```bash
blender -b scene.blend -P scripts/export_batch.py -- --modes CharacterRainbow PatternCategories --output renders/
```

**Capabilities**:

- Apply strategies without UI
- Render multiple visualizations
- Batch export stills
- Automation-friendly

### Add-on Reload

**Script**: `scripts/dev_reload.py`

**Usage** (inside Blender Python console or external):

```python
import sys
sys.path.append("/path/to/blender_addon/scripts")
import dev_reload
dev_reload.reload_addon()
```

**Use Case**: Development workflow - reload without restarting Blender

## Troubleshooting & Diagnostics

### Common Issues

**"No data loaded"**:

- Check database path in Preferences
- Verify `static.db` exists and is readable
- Check file size (~700MB expected)

**"No systems to shade"**:

- Build scene first
- Check `Frontier` collection exists and has objects (hierarchical structure)

**"Attribute not found" in shader**:

- Rebuild scene (properties not calculated)
- Check exact property name (case-sensitive)

**Triangle detection finds nothing**:

- Very strict isolation requirement
- Most triangles have external connections
- Use `Show All Jumps` to reset filter

### Performance Issues

**Viewport slow**:

- Reduce build percentage
- Hide jumps collection
- Simplify shaders
- Disable volumetric effects

**Memory usage high**:

- Expected with 25k+ objects
- Close other applications
- Consider RAM upgrade (16GB+ recommended)

**Blender hangs/freezes**:

- Long operations (scene build, jump creation) are normal
- Modal operators show progress in status bar
- Can cancel with ESC key during modal operations
- If truly frozen, may be a bug—report with reproduction steps

**Performance degradation over time**:

- Blender accumulates undo history—restart periodically
- Check system resources (Task Manager/Activity Monitor)
- Clear unused data blocks (File → Clean Up → Purge)

## See Also

**Documentation**:

- `ARCHITECTURE.md` - Technical architecture
- `SHADERS.md` - Visualization strategy details
- `DATA_MODEL.md` - Database schema
- `NODE_BASED_STRATEGIES.md` - Node system guide

**Code**:

- `operators/reference_points.py` - Navigation landmarks
- `operators/jump_analysis.py` - Graph analysis
- `operators/build_jumps.py` - Jump network creation
- `node_groups/` - Shader strategy implementations
