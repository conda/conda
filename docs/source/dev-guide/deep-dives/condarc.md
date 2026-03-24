(deep_dive_config_management)=

# Programmatic `.condarc` File API

This guide explains how to programmatically read and write conda configuration files (`.condarc`)
using the `ConfigurationFile` class. This is useful for tools that need to modify conda settings
without shelling out to `conda config` commands.

## Overview

The `conda.cli.condarc.ConfigurationFile` class provides a high-level interface for reading,
modifying, and writing conda configuration files (`.condarc`). It handles:

- Configuration file validation
- Type checking and conversion
- Parameter existence checking
- Atomic file operations via context manager
- Support for sequence, map, and primitive parameters

## Basic Usage

### Reading Configuration

```python
from conda.cli.condarc import ConfigurationFile

# Read user's .condarc file
config = ConfigurationFile.from_user_condarc()

# Access the configuration content
print(config.content)
# {'channels': ['defaults', 'conda-forge'], 'auto_update_conda': False}

# Get a specific key
key, value = config.get_key("channels")
print(f"{key}: {value}")
# channels: ['defaults', 'conda-forge']
```

### Writing Configuration

```python
from conda.cli.condarc import ConfigurationFile

# Create a configuration file instance
config = ConfigurationFile.from_user_condarc()

# Set a primitive parameter
config.set_key("auto_update_conda", False)

# Add to a sequence parameter
config.add("channels", "conda-forge", prepend=True)

# Set a map parameter
config.set_key("proxy_servers.http", "http://proxy.example.com")

# Write changes to file
config.write()
```

### Using Context Manager

For atomic operations, use the context manager pattern:

```python
from conda.cli.condarc import ConfigurationFile

# Changes are automatically written on successful exit
with ConfigurationFile.from_user_condarc() as config:
    config.set_key("channels", ["conda-forge", "defaults"])
    config.set_key("auto_update_conda", False)
# File is written here automatically
```

If an exception occurs within the context, changes are not written:

```python
try:
    with ConfigurationFile.from_user_condarc() as config:
        config.set_key("channels", ["conda-forge"])
        raise ValueError("Something went wrong")
except ValueError:
    pass
# File was NOT modified because of the exception
```

## Factory Methods

The `ConfigurationFile` class provides several factory methods for common configuration file locations:

### User Configuration

```python
from conda.cli.condarc import ConfigurationFile

# User's .condarc file (typically ~/.condarc)
config = ConfigurationFile.from_user_condarc()
```

### System Configuration

```python
from conda.cli.condarc import ConfigurationFile

# System-wide .condarc file
config = ConfigurationFile.from_system_condarc()
```

### Environment Configuration

```python
from conda.cli.condarc import ConfigurationFile

# Environment-specific .condarc file at {prefix}/.condarc
config = ConfigurationFile.from_env_condarc(prefix="/path/to/env")

# Or use CONDA_PREFIX environment variable
config = ConfigurationFile.from_env_condarc()
```

### Custom Path

```python
from pathlib import Path
from conda.cli.condarc import ConfigurationFile

# Custom configuration file path
config = ConfigurationFile(path=Path("/custom/path/.condarc"))
```

## Parameter Types

Conda configuration parameters come in three types, and each supports different operations:

### Primitive Parameters

Single scalar values (strings, numbers, booleans):

```python
config.set_key("auto_update_conda", False)
config.set_key("channel_priority", "strict")
config.set_key("rollback_enabled", True)
```

### Sequence Parameters

Lists of values:

```python
# Add to end of list
config.add("channels", "conda-forge", prepend=False)

# Add to beginning of list
config.add("channels", "defaults", prepend=True)

# Remove from list
config.remove_item("channels", "conda-forge")
```

### Map Parameters

Dictionaries with nested values:

```python
# Set a map entry
config.set_key("proxy_servers.http", "http://proxy.example.com")
config.set_key("proxy_servers.https", "https://proxy.example.com")

# Add to a nested sequence within a map
config.add("conda_build.config_file", "/path/to/config.yaml")
```

## Key Validation

The `ConfigurationFile` class validates keys against the current conda context:

```python
from conda.cli.condarc import ConfigurationFile

config = ConfigurationFile.from_user_condarc()

# Check if a key exists
if config.key_exists("channels"):
    print("channels is a valid parameter")

# Attempting to set an invalid key raises an error
try:
    config.set_key("invalid_key", "value")
except Exception as e:
    print(f"Error: {e}")
    # Error: CondaKeyError: 'invalid_key': unknown parameter
```

## Handling Missing Keys

When getting a key that doesn't exist, the method returns a sentinel value:

```python
from conda.cli.condarc import ConfigurationFile, MISSING

config = ConfigurationFile(content={})

key, value = config.get_key("undefined_key")
if value is MISSING:
    print(f"Key '{key}' not found in config")
```

## Working with Plugin Configuration

Plugin parameters use a `plugins.` prefix:

```python
# Set a plugin-specific parameter
config.set_key("plugins.custom_solver.enabled", True)

# Add to a plugin sequence parameter
config.add("plugins.custom_reporters.backends", "custom_backend")
```

## Advanced Usage

### Custom Context

You can provide a custom context instance for testing or specialized configurations:

```python
from conda.base.context import Context
from conda.cli.condarc import ConfigurationFile

# Create a custom context
custom_context = Context()

# Use it with ConfigurationFile
config = ConfigurationFile(path="/path/to/config", context=custom_context)
```

### Warning Handlers

Customize how warnings are reported:

```python
warnings = []


def collect_warnings(msg):
    warnings.append(msg)


config = ConfigurationFile(path="/path/to/config", warning_handler=collect_warnings)

config.add("channels", "defaults", prepend=False)
# If "defaults" already exists, a warning is collected
print(warnings)
```

### Manual Read/Write Control

For more control over when files are read or written:

```python
from conda.cli.condarc import ConfigurationFile

config = ConfigurationFile(path="/path/to/.condarc")

# Explicitly read
config.read()

# Make changes
config.content["channels"] = ["conda-forge"]

# Explicitly write
config.write()

# Or write to a different location
config.write(path="/different/path/.condarc")
```

### Working with Content Directly

The `content` property provides direct access to the underlying configuration dictionary:

```python
config = ConfigurationFile.from_user_condarc()

# Access content
current_channels = config.content.get("channels", [])

# Modify content directly (use with caution)
config.content["channels"] = ["conda-forge", "defaults"]
config.write()
```

**Note**: Direct content manipulation bypasses validation. Use the provided methods
(`set_key`, `add`, `remove_item`, etc.) for safer operations.

## Complete Example

Here's a complete example that demonstrates multiple operations:

```python
from conda.cli.condarc import ConfigurationFile

# Use context manager for atomic operations
with ConfigurationFile.from_user_condarc() as config:
    # Set primitive parameters
    config.set_key("auto_update_conda", False)
    config.set_key("channel_priority", "strict")

    # Configure channels
    config.set_key("channels", [])  # Clear existing
    config.add("channels", "conda-forge", prepend=False)
    config.add("channels", "defaults", prepend=False)

    # Set proxy servers
    config.set_key("proxy_servers.http", "http://proxy.example.com:8080")
    config.set_key("proxy_servers.https", "https://proxy.example.com:8080")

    # Configure conda-build
    config.add("conda_build.config_file", "/path/to/conda_build_config.yaml")

    # Print current configuration
    print("Current configuration:")
    for key, value in config.content.items():
        print(f"  {key}: {value}")

# File is automatically written when exiting the context manager
print("Configuration saved!")
```

## Migration Guide

If you were previously using the private functions from `conda.cli.main_config`, here's how to migrate:

### Before (deprecated)

```python
from conda.cli.main_config import (
    _read_rc,
    _write_rc,
    _set_key,
    _get_key,
    _remove_key,
)

# Old way
rc_config = _read_rc("/path/to/.condarc")
_set_key("auto_update_conda", False, rc_config)
_write_rc("/path/to/.condarc", rc_config)
```

### After (recommended)

```python
from conda.cli.condarc import ConfigurationFile

# New way
config = ConfigurationFile(path="/path/to/.condarc")
config.set_key("auto_update_conda", False)
config.write()

# Or even simpler with context manager
with ConfigurationFile(path="/path/to/.condarc") as config:
    config.set_key("auto_update_conda", False)
```

## Error Handling

The `ConfigurationFile` class raises specific exceptions for different error conditions:

```python
from conda.cli.condarc import ConfigurationFile
from conda.exceptions import CondaKeyError, CondaValueError, CouldntParseError

config = ConfigurationFile.from_user_condarc()

try:
    # Unknown parameter
    config.set_key("unknown_param", "value")
except CondaKeyError as e:
    print(f"Invalid key: {e}")

try:
    # Invalid operation for parameter type
    config.set_key("channels", "not-a-list")
except CondaKeyError as e:
    print(f"Invalid operation: {e}")

try:
    # Adding to a non-sequence parameter
    config.add("auto_update_conda", "value")
except CondaValueError as e:
    print(f"Type error: {e}")
```

## Thread Safety

The `ConfigurationFile` class is not thread-safe. If you need to access configuration from multiple
threads, consider using locks or creating separate instances for each thread.

## Best Practices

1. **Use context managers**: For atomic operations, always use the context manager pattern to ensure
   changes are only written on success.

2. **Validate keys**: Use `key_exists()` to check parameter validity before attempting operations.

3. **Use factory methods**: Prefer `from_user_condarc()`, `from_system_condarc()`, and
   `from_env_condarc()` over manual path construction.

4. **Handle missing keys**: Always check for `MISSING` when using `get_key()` to handle undefined
   parameters gracefully.

5. **Avoid direct content manipulation**: Use the provided methods (`set_key`, `add`, etc.) instead
   of modifying `content` directly to ensure proper validation.

6. **Custom warning handlers**: For library code, provide custom warning handlers to integrate with
   your logging system.

## See Also

- {ref}`deep_dive_context` - Understanding the conda context object
- {doc}`/configuration` - User-facing configuration documentation
- {doc}`/dev-guide/api/conda/cli/index` - CLI API documentation
