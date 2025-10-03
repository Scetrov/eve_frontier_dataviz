# CI/CD Pipeline Documentation

This document describes the automated checks and workflows in the GitHub Actions CI/CD pipeline.

## Workflows Overview

### 1. CI Workflow (`.github/workflows/ci.yml`)

**Triggers**: Push to main, pull requests, version tags

**Purpose**: Core build, test, and validation pipeline

**Checks Performed**:

#### Code Quality Checks

1. **Markdown Linting**
   - Validates all `.md` files for formatting consistency
   - Uses custom `markdown_lint.py` script
   - Enforces blank lines around lists, fenced code blocks, etc.

2. **Unused Code Detection**
   - Scans for unused imports (Ruff F401)
   - Detects unused variables (Ruff F841)
   - Runs on `blender_addon/src/` directory
   - **Fails build** if found

3. **Ruff Comprehensive Lint**
   - Full linting suite
   - Import ordering (I001)
   - Error detection
   - Code quality rules
   - **Fails build** if errors found

4. **Documentation Existence Validation**
   - Verifies required documentation files exist:
     - `FEATURES.md`
     - `ARCHITECTURE.md`
     - `SHADERS.md`
     - `DATA_MODEL.md`
   - **Fails build** if any missing

5. **TODO/FIXME Scanner**
   - Searches for untracked TODO/FIXME comments
   - Issues **warning** (doesn't fail build)
   - Helps track technical debt

#### Testing Checks

1. **Unit Tests with Coverage**
   - Runs pytest test suite
   - Generates XML coverage report for Codecov
   - Produces term-missing report for local debugging

2. **Coverage Threshold Enforcement**
   - Parses `coverage.xml`
   - Calculates coverage percentage
   - **Fails build** if below 90%
   - Currently at 91% ✓

3. **Codecov Upload**
   - Uploads coverage data to codecov.io
   - Uses `CODECOV_TOKEN` secret
   - Verbose logging enabled
   - Non-blocking (continues on failure)

#### Build Validation

1. **Add-on Build Test**
   - Runs `build_addon.py` script
   - Verifies ZIP creation succeeds
   - Validates packaging structure

2. **Artifact Upload**
   - Stores built ZIP as GitHub artifact
   - Available for 90 days
   - Used by release workflow

### 2. Code Quality Deep Scan (`.github/workflows/code-quality.yml`)

**Triggers**:

- Weekly schedule (Mondays 9 AM UTC)
- Manual dispatch (`workflow_dispatch`)
- PRs touching `src/addon/**/*.py` or `docs/**/*.md`

**Purpose**: In-depth code quality analysis (informational, doesn't block)

**Checks Performed**:

1. **Cyclomatic Complexity Analysis**
   - Uses `radon` tool
   - Reports average complexity
   - Highlights functions with complexity > 10
   - **Warning only** (doesn't fail)

2. **Maintainability Index**
   - Calculates MI score per module
   - Higher is better (A=excellent, C=poor)
   - Helps identify refactoring candidates

3. **Dead Code Detection**
   - Uses `vulture` tool
   - Minimum confidence: 80%
   - May have false positives (Blender API usage)
   - **Informational only**

4. **Documentation Coverage Analysis**
   - Lists all `EVE_OT_*` operators
   - Compares with mentions in FEATURES.md
   - Ensures new operators are documented
   - **Manual review required**

5. **Hardcoded Path Detection**
   - Searches for `/home/`, `/Users/`, `C:\\`
   - Excludes test files and examples
   - **Warning only**

6. **Print Statement Detection**
   - Finds `print()` calls in operators
   - Suggests using `self.report()` or logging
   - Excludes comments marked `# OK` or `# debug`
   - **Warning only**

7. **Import Ordering Validation**
   - Runs `ruff --select I`
   - Ensures isort compatibility
   - **Warning only**

8. **Large File Detection**
   - Finds Python files > 500KB
   - Suggests splitting large modules
   - **Warning only**

9. **Security Scan (Bandit)**
   - Scans for common security issues
   - Generates JSON report
   - **Warning only** (Blender context may have false positives)

10. **Per-Module Coverage Report**
    - Shows coverage breakdown by file
    - Highlights modules < 80%
    - Helps prioritize testing efforts

**Artifacts Generated**:

- `code-quality-report.md` - Summary report
- `bandit-report.json` - Security scan results
- Retained for 30 days

### 3. Documentation Quality (`.github/workflows/doc-quality.yml`)

**Triggers**:

- PRs touching `docs/**`, `README.md`, `CONTRIBUTING.md`
- Push to main (docs changes)
- Manual dispatch

**Purpose**: Ensure documentation quality and consistency

**Checks Performed**:

1. **Internal Link Validation**
   - Extracts all `[text](path.md)` links
   - Resolves relative paths
   - **Fails** if any broken links found

2. **Outdated Example Detection**
   - Searches for old strategy names:
     - `NameFirstCharHue`
     - `ChildCountEmission`
     - `BlackholeBoost`
   - **Fails** if found (should use current names)

3. **Documentation Structure Verification**
   - Ensures all required docs exist:
     - `FEATURES.md`
     - `ARCHITECTURE.md`
     - `SHADERS.md`
     - `DATA_MODEL.md`
     - `SHADER_PROPERTIES.md`
     - `NODE_BASED_STRATEGIES.md`
     - `README.md`
     - `CONTRIBUTING.md`
   - **Fails** if any missing

4. **Operator Documentation Coverage**
   - Extracts all operator class names
   - Checks if mentioned in any `.md` file
   - **Warns** if undocumented operators found

5. **TODO/FIXME in Documentation**
   - Finds incomplete documentation markers
   - **Warning only**

6. **Markdown Formatting**
   - Same as main CI workflow
   - Uses custom `markdown_lint.py`

7. **Terminology Consistency**
   - Checks for consistent hyphenation:
     - "node-based" (not "node based")
     - "GPU-driven" (not "GPU driven")
   - **Warning only**

**Artifacts Generated**:

- `documentation-quality-report.md`
- Retained for 30 days

### 4. Release Workflow (part of `ci.yml`)

**Triggers**: Git tags matching `v*` (e.g., `v0.1.0`)

**Purpose**: Automated GitHub Releases

**Steps**:

1. Runs full CI pipeline first
2. Downloads built add-on ZIP
3. Extracts version from git tag
4. Creates GitHub Release
5. Attaches ZIP file
6. Sets as latest release

## Pre-commit Hooks (Local Development)

**File**: `.pre-commit-config.yaml`

**Hooks**:

1. `ruff` - Auto-fix lint issues
2. `ruff-format` - Format code
3. `markdown-lint` - Check markdown
4. `pytest` - Run fast test suite

**Usage**:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

## Coverage Requirements

**Current Threshold**: 90%  
**Current Coverage**: 91%

**Enforcement**:

- CI fails if coverage drops below 90%
- Coverage calculated from pytest XML report
- Uploaded to Codecov for tracking trends

**Excluded from Coverage**:

- Blender-dependent code (bpy imports)
- `__init__.py` registration boilerplate
- Operator UI code (requires Blender runtime)

## Secrets Required

### `CODECOV_TOKEN`

**Purpose**: Upload coverage to codecov.io  
**Location**: Repository Settings → Secrets → Actions  
**How to Get**:

1. Sign in to codecov.io with GitHub
2. Add repository
3. Copy upload token
4. Add as repository secret

## Workflow Status Badges

Add to README.md:

```markdown
[![CI](https://github.com/Scetrov/eve_frontier_dataviz/actions/workflows/ci.yml/badge.svg)](https://github.com/Scetrov/eve_frontier_dataviz/actions/workflows/ci.yml)
[![Code Quality](https://github.com/Scetrov/eve_frontier_dataviz/actions/workflows/code-quality.yml/badge.svg)](https://github.com/Scetrov/eve_frontier_dataviz/actions/workflows/code-quality.yml)
[![Documentation](https://github.com/Scetrov/eve_frontier_dataviz/actions/workflows/doc-quality.yml/badge.svg)](https://github.com/Scetrov/eve_frontier_dataviz/actions/workflows/doc-quality.yml)
```

## Debugging Failed Workflows

### CI Fails on Coverage

**Symptom**: "Coverage X% is below 90% threshold"

**Solutions**:

1. Check which modules dropped coverage: `pytest --cov=addon --cov-report=term`
2. Add tests for uncovered lines
3. If Blender-dependent code, add `# pragma: no cover` comment

### CI Fails on Unused Imports

**Symptom**: "F401 unused import"

**Solutions**:

1. Remove unused import
2. If needed for type checking: `from typing import TYPE_CHECKING; if TYPE_CHECKING: import X`
3. If needed by downstream: Add `# noqa: F401` comment

### Documentation Quality Fails

**Symptom**: "Broken link in docs"

**Solutions**:

1. Check relative path is correct
2. Ensure linked file exists
3. Use absolute paths from repo root if needed

### Code Quality Warnings

**Non-blocking** - Review and address when convenient:

- Complexity > 10: Consider refactoring
- Dead code: Verify with `vulture`, may be false positive
- Print statements: Use `self.report()` in operators

## Adding New Checks

### To Main CI (Blocking)

1. Edit `.github/workflows/ci.yml`
2. Add step before "Upload coverage"
3. Use `exit 1` to fail build
4. Test locally first

### To Deep Scan (Non-blocking)

1. Edit `.github/workflows/code-quality.yml`
2. Add step anywhere in job
3. Use `continue-on-error: true` for warnings
4. Add results to quality report

### To Documentation Check

1. Edit `.github/workflows/doc-quality.yml`
2. Add validation step
3. Use `::error::` for failures, `::warning::` for suggestions

## Performance Optimization

**Current CI Runtime**: ~1-2 minutes (main CI)

**Optimization Strategies**:

1. **Caching**: pip dependencies cached by `setup-python@v5`
2. **Parallel Jobs**: Could split test/lint into separate jobs
3. **Conditional Workflows**: Doc quality only runs on doc changes
4. **Selective Testing**: pytest markers for fast vs slow tests

## Best Practices

1. **Run Pre-commit Locally**: Catch issues before push
2. **Check Coverage Locally**: `pytest --cov`
3. **Review Deep Scan Weekly**: Address technical debt
4. **Update Docs with Features**: Prevents doc quality failures
5. **Use Conventional Commits**: Better changelog generation

## Future Enhancements

**Potential Additions**:

- [ ] Dependency vulnerability scanning (GitHub Dependabot)
- [ ] License compliance checking
- [ ] Automated changelog generation
- [ ] Performance regression tests
- [ ] Visual regression tests (screenshot comparison)
- [ ] Automatic version bumping
- [ ] Docker build for headless Blender tests
- [ ] Integration tests (requires Blender runtime)

## See Also

- `CODE_REVIEW_FINDINGS.md` - Results from manual code review
- `CONTRIBUTING.md` - Development workflow
- `README_TESTING.md` - Local testing guide
