# Documentation Index

This directory contains comprehensive documentation for the EVE Frontier Data Visualizer Blender add-on.

## Core Documentation

### Architecture & Design

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture, layer design, data flow, and extensibility points
- **[DATA_MODEL.md](DATA_MODEL.md)** - Database schema, dataclass definitions, and data relationships

### Features & Usage

- **[FEATURES.md](FEATURES.md)** - User-facing feature descriptions and usage guides
- **[NODE_BASED_STRATEGIES.md](NODE_BASED_STRATEGIES.md)** - GPU-driven visualization strategies and node group architecture
- **[SHADERS.md](SHADERS.md)** - Shader implementation details and material system
- **[SHADER_PROPERTIES.md](SHADER_PROPERTIES.md)** - Custom properties used by shader nodes

## Development Documentation

### Testing & Quality

- **[TESTING.md](TESTING.md)** - Test suite setup, running tests, coverage requirements
- **[CI_DOCUMENTATION.md](CI_DOCUMENTATION.md)** - Continuous integration setup and workflows
- **[BLENDER_BEST_PRACTICES_REVIEW.md](BLENDER_BEST_PRACTICES_REVIEW.md)** - Blender add-on best practices compliance review

### Code Reviews

- **[CODE_REVIEW_FINDINGS.md](CODE_REVIEW_FINDINGS.md)** - Historical code review findings and improvements

## Quick Links

### For Users

Start with [FEATURES.md](FEATURES.md) to understand what the add-on can do, then see the main [README.md](../README.md) for installation instructions.

### For Developers

1. Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand the system design
2. Review [DATA_MODEL.md](DATA_MODEL.md) for data structures
3. See [TESTING.md](TESTING.md) for running tests
4. Check [BLENDER_BEST_PRACTICES_REVIEW.md](BLENDER_BEST_PRACTICES_REVIEW.md) for coding standards

### For Contributors

See [CONTRIBUTING.md](../../CONTRIBUTING.md) in the repository root for contribution guidelines.

## Documentation Standards

All documentation follows:

- Markdown format with consistent formatting
- Enforced via `markdown_lint.py` script
- Code blocks must be surrounded by blank lines (MD031)
- Lists must be surrounded by blank lines (MD032)

---

**Last Updated:** October 5, 2025
