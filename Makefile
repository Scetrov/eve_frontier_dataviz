PYTHON=python
ADDON_VERSION:=$(shell $(PYTHON) -c "import tomllib,sys;import pathlib;d=tomllib.load(open('blender_addon/pyproject.toml','rb'));print(d['project']['version'])")
DIST_DIR=dist
ZIP=dist/eve_frontier_visualizer-$(ADDON_VERSION).zip

.PHONY: help build clean test lint lint-fix format release

help:
	@echo "Targets:"
	@echo "  build   - build addon zip to dist/"
	@echo "  clean   - remove dist/ directory"
	@echo "  test    - run pytest with coverage"
	@echo "  lint    - run ruff check"
	@echo "  lint-fix- run ruff check --fix & ruff format"
	@echo "  format  - run ruff format (code style only)"
	@echo "  release - tag current version (git tag v<version>)"

build: $(ZIP)
	@echo "Built $(ZIP)"

$(ZIP):
	$(PYTHON) blender_addon/scripts/build_addon.py

clean:
	rm -rf $(DIST_DIR)

test:
	pytest

lint:
	ruff check .

lint-fix:
	ruff check --fix . && ruff format .

format:
	ruff format .

release:
	@git tag v$(ADDON_VERSION)
	@git push origin v$(ADDON_VERSION)
	@echo "Pushed tag v$(ADDON_VERSION). CI will draft release."
