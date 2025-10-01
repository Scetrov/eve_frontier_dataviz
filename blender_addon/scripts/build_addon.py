"""Build a distributable ZIP for the Blender add-on.

Usage (from repo root):
  python blender_addon/scripts/build_addon.py

Creates dist/eve_frontier_visualizer-<version>.zip containing the addon package.
The archive root will contain the `addon` package directory contents (Blender expects
top-level modules with `__init__.py` exposing `bl_info`).
"""
from __future__ import annotations

import argparse
import shutil
import tempfile
import tomllib
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PKG_ROOT = REPO_ROOT / "blender_addon" / "src" / "addon"
DIST_DIR = REPO_ROOT / "dist"


def read_version() -> str:
    pyproject = REPO_ROOT / "blender_addon" / "pyproject.toml"
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def build(zip_name: str | None = None) -> Path:
    if not PKG_ROOT.exists():
        raise SystemExit(f"Package root not found: {PKG_ROOT}")
    version = read_version()
    DIST_DIR.mkdir(exist_ok=True)
    if zip_name is None:
        zip_name = f"eve_frontier_visualizer-{version}.zip"
    out_path = DIST_DIR / zip_name

    # Create a temp staging dir that mirrors the final expected layout:
    # zip root contains addon/*
    with tempfile.TemporaryDirectory() as tmpd:
        staging_root = Path(tmpd)
        addon_target = staging_root / "addon"
        shutil.copytree(PKG_ROOT, addon_target, dirs_exist_ok=True)
        for cache in addon_target.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)
        if out_path.exists():
            out_path.unlink()
        # Manually zip to avoid race on Windows with shutil.make_archive/stat
        with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in addon_target.rglob('*'):
                if p.is_dir():
                    continue
                rel = p.relative_to(staging_root)
                zf.write(p, rel.as_posix())
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Blender add-on zip")
    parser.add_argument("--name", help="Override output zip file name")
    args = parser.parse_args(argv)
    out = build(args.name)
    print(f"Created: {out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
