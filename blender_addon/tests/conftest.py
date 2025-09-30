# Ensure the 'addon' package (located in blender_addon/addon) is importable when tests
# are executed from the repository root or from within the blender_addon directory.
import sys
from pathlib import Path

here = Path(__file__).resolve()
root = here.parents[2]  # repo root
addon_parent = root / 'blender_addon'
if str(addon_parent) not in sys.path:
    sys.path.insert(0, str(addon_parent))
