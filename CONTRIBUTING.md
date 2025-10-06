# Contributing Guide

Thank you for contributing to the EVE Frontier Data Visualizer! This document distills the key workflow expectations so PRs stay lean, deterministic, and easy to review.

## Branch & Commit Hygiene

- Use feature branches; keep `main` green.
- Conventional Commits prefixes: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`.
- Keep commits focused; avoid mixing unrelated refactors with new features.

## Quality Gates (Must Pass)

1. Ruff lint (imports, errors, style) — `ruff check .`
2. Tests with coverage ≥ 90% (pure Python modules only) — `pytest`
3. Markdown linter — `python blender_addon/scripts/markdown_lint.py`
4. Deterministic add-on build — `python blender_addon/scripts/build_addon.py`

## Recommended Local Workflow

```bash
pip install -e blender_addon[dev]
pre-commit install  # one-time

# During development
make test
make lint

# If lint fails on imports or trivial style
make lint-fix

# Build the zip (optional local verification)
make build
```

## Pre-commit Hooks

Configured in `.pre-commit-config.yaml`:

- `ruff` (with `--fix`)
- `ruff-format`
- custom `markdown-lint`
- `pytest -q` (fast suite)

Run on all files manually:

```bash
pre-commit run --all-files
```

If you see an import ordering (I001) failure in CI, it generally means hooks weren’t run. Use `make lint-fix` (or allow pre-commit to fix) and recommit.

## Adding Shader Strategies

1. Implement subclass in `shaders_builtin.py` (or new module) with `@register_strategy`.
2. Deterministic material naming: prefix `EVE_` + strategy id (+ stable variant token).
3. Re-run apply in Blender to verify idempotency (no material explosion).
4. Document in `docs/SHADERS.md` (brief intent, naming pattern).

## Data Loader Changes

- Add one bulk SELECT per new entity type; never per-row queries.
- Update `docs/DATA_MODEL.md` after stabilizing schema mapping.
- Extend tests with fixture SQL if new tables/columns are used.

## Scene / Visualization Boundaries

- No `bpy` usage in `data_loader.py` or its tests.
- Strategies must NOT create objects; only assign/update materials.
- Future `scene_builder` will centralize object creation.

## Performance Requirements (Scale-Critical)

**Context**: This addon manages 25,000+ objects (24,426 systems minimum + jump lines + future planets/moons).

**Critical Rule**: All operations must be **O(n) or better**. O(n²) operations will hang Blender for minutes or crash.

**Required Patterns**:
- ✅ Batch operations: `bpy.data.batch_remove()`, collect-then-process
- ✅ Disable undo during bulk ops: `bpy.context.preferences.edit.use_global_undo = False`
- ✅ Modal operators for operations > 1 second with progress reporting
- ✅ Bulk SELECT queries, never per-row loops

**Forbidden Patterns**:
- ❌ Nested object iteration (`for obj in objs: for other in objs:`)
- ❌ Per-object material creation (use shared materials with deterministic variants)
- ❌ Synchronous long operations without progress feedback
- ❌ Database queries inside object loops

**Example - Correct Approach**:

```python
# Collect first, then batch process
objects_to_remove = set()
for coll in collections:
    objects_to_remove.update(coll.objects)
bpy.data.batch_remove(ids=objects_to_remove)
```

See `blender_addon/src/addon/operators/_shared.py:clear_generated()` for reference implementation.

## Testing Guidance

- Keep tests fast (<1s). Avoid filesystem writes outside temp dirs.
- Assert key invariants (counts, cache reuse, deterministic naming).
- Use fixtures in `tests/fixtures/*.sql` to expand scenarios.

## Release (Tag) Flow

Tagging `vX.Y.Z` triggers packaging + GitHub Release:

```bash
make build  # optional local check
make release
```

Ensure `pyproject.toml` version matches intended tag.

## PR Review Checklist (Self-Serve)

- [ ] Lint passes locally (`make lint`)
- [ ] Imports auto-formatted (`make lint-fix` if needed)
- [ ] Tests + coverage pass
- [ ] Docs updated (README / SHADERS / DATA_MODEL where relevant)
- [ ] No accidental large files or DB dumps committed

## Getting Help

Open a draft PR early or file an issue describing intent if scope feels unclear. Keep changes minimal and layered.

Happy hacking o7
