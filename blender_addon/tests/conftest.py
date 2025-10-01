# Ensure the 'addon' package (located in blender_addon/addon) is importable when tests
# are executed from the repository root or from within the blender_addon directory.
import sys
from pathlib import Path

here = Path(__file__).resolve()
root = here.parents[2]  # repo root
src_path = root / 'blender_addon' / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
