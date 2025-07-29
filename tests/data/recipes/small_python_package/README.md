# small-python-package

A minimal Python package for conda testing purposes.

## Purpose

This package is used in conda's test suite to test:
- Python package installation via pip
- CLI entry points
- pyproject.toml-based package building
- Python package interoperability with conda

## Usage

```bash
# After installation
spp --help
spp --greet
```

## Building Wheel File

To create a wheel (.whl) file for testing purposes:

```bash
# From the conda source root directory
pip wheel tests/data/recipes/small_python_package --wheel-dir tests/data/wheelhouse/ --no-deps

# This creates or updates: tests/data/wheelhouse/small_python_package-1.0.0-py3-none-any.whl
```

The wheel file is used for testing pip package installations and interoperability with conda.

## Structure

- `pyproject.toml` - Modern Python packaging configuration
- `small_python_package/` - Python package source code
  - `__init__.py` - Package module with hello() function
  - `cli.py` - Command-line interface
