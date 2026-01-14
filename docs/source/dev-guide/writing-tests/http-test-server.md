# HTTP Test Server Fixture

The HTTP test server fixture provides a way to test conda functionality that requires serving files over HTTP, such as:

- Mock conda channels with packages
- Remote environment files (`environment.yml`)
- Remote configuration files
- Any scenario where conda needs to fetch files from a URL

## Overview

The `http_test_server` fixture starts a local HTTP server that serves files from a directory. The server runs on a random port and supports both IPv4 and IPv6.

The fixture can be used in two ways:

1. **Without `@pytest.mark.parametrize`** - Use a temporary directory that you populate dynamically
2. **With `@pytest.mark.parametrize`** - Serve files from a pre-existing directory

```{tip}
For proper type hints, import `HttpTestServerFixture` from `conda.testing.fixtures` under `TYPE_CHECKING`.
See the [complete example](#complete-example-testing-a-mock-channel) for the full import pattern.
```

## Basic Usage

### Dynamic Content (No Marker)

The simplest usage - no marker needed. The server automatically uses a temporary directory that you can populate:

```python
def test_dynamic_repodata(http_test_server: HttpTestServerFixture):
    """Create content on the fly - no setup needed."""
    # Populate files directly in the server's directory
    (http_test_server.directory / "repodata.json").write_text('{"packages": {}}')

    # Make request
    response = requests.get(http_test_server.get_url("repodata.json"))
    assert response.status_code == 200
    assert response.json() == {"packages": {}}
```

This pattern is ideal for:

- Creating mock repodata files
- Testing with minimal setup
- Extending and creating your own fixtures programmatically

### Pre-existing Directory (With Parametrize)

Use `@pytest.mark.parametrize()` with `indirect=True` when you have test data already prepared:

```python
@pytest.mark.parametrize(
    "http_test_server",
    ["tests/data/mock-channel"],
    indirect=True,
)
def test_fetch_from_channel(http_test_server: HttpTestServerFixture):
    # Server serves files from tests/data/mock-channel/
    repodata_url = http_test_server.get_url("linux-64/repodata.json")

    response = requests.get(repodata_url)
    assert response.status_code == 200
```

The `indirect=True` parameter tells pytest to pass the directory path to the fixture rather than directly to the test function.

This pattern is ideal for:

- Complex directory structures
- Sharing test data across multiple tests
- Binary files (packages, archives)
- Large test datasets

## Testing Multiple Directories

One of the benefits of using `@pytest.mark.parametrize` is that you can easily test the same logic against multiple directories:

```python
@pytest.mark.parametrize(
    "http_test_server",
    [
        "tests/data/channel1",
        "tests/data/channel2",
        "tests/data/channel3",
    ],
    indirect=True,
)
def test_multiple_channels(http_test_server: HttpTestServerFixture):
    # This test runs three times, once for each channel directory
    response = requests.get(http_test_server.get_url("repodata.json"))
    assert response.status_code == 200
    assert "packages" in response.json()
```

Each test run will use a different directory, making it easy to verify behavior across multiple datasets.

You can also mix pre-existing directories with dynamic content by using `None`:

```python
@pytest.mark.parametrize(
    "http_test_server",
    [
        "tests/data/channel1",
        None,
        "tests/data/channel2",
    ],
    indirect=True,
)
def test_mixed_sources(http_test_server: HttpTestServerFixture):
    # Runs 3 times: channel1, dynamic tmp dir, channel2
    # When None, http_test_server.directory is a fresh temporary directory
    ...
```

## Complete Example: Testing a Mock Channel

Here's a full example with all imports showing dynamic content generation:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import requests

if TYPE_CHECKING:
    from conda.testing.fixtures import CondaCLIFixture, HttpTestServerFixture


def test_install_from_mock_channel(
    http_test_server: HttpTestServerFixture,
    conda_cli: CondaCLIFixture,
    tmp_path: Path,
):
    """Test installing from a dynamically created mock channel."""
    # Create channel structure on the fly
    noarch = http_test_server.directory / "noarch"
    noarch.mkdir()

    # Create minimal repodata
    repodata = {"packages": {}, "packages.conda": {}, "repodata_version": 1}
    (noarch / "repodata.json").write_text(json.dumps(repodata))

    # Use the channel
    channel_url = http_test_server.url
    stdout, stderr, code = conda_cli(
        "search",
        f"--channel={channel_url}",
        "--override-channels",
        "*",
    )

    # Verify it worked (no packages found but channel was accessible)
    assert code == 0


@pytest.mark.parametrize(
    "http_test_server",
    ["tests/data/mock-channel"],
    # Assume the following structure:
    # tests/data/mock-channel/
    #   ├── noarch/
    #   │   └── repodata.json
    #   └── linux-64/
    #       ├── repodata.json
    #       └── example-pkg-1.0.0-0.tar.bz2
    indirect=True,
)
def test_install_from_preexisting_channel(
    http_test_server: HttpTestServerFixture,
    conda_cli: CondaCLIFixture,
    tmp_path: Path,
):
    """Test installing from pre-existing mock channel."""
    channel_url = http_test_server.url

    stdout, stderr, code = conda_cli(
        "create",
        f"--prefix={tmp_path}",
        f"--channel={channel_url}",
        "example-pkg",
        "--yes",
    )

    assert code == 0
    assert (tmp_path / "conda-meta" / "example-pkg-1.0.0-0.json").exists()
```

## Fixture API Reference

### HttpTestServerFixture

The fixture returns an instance with these attributes and methods:

#### Attributes:

- `server: http.server.ThreadingHTTPServer` - The underlying server instance
- `host: str` - Server host (usually `127.0.0.1`)
- `port: int` - Server port (random)
- `url: str` - Base URL (e.g., `http://127.0.0.1:54321`)
- `directory: Path` - The directory being served (writable, use to populate content)

#### Methods:

- `get_url(path: str = "") -> str` - Get full URL for a path
  - Example: `get_url("linux-64/repodata.json")` → `"http://127.0.0.1:54321/linux-64/repodata.json"`

#### Using the `directory` attribute:

```python
def test_dynamic_files(http_test_server: HttpTestServerFixture):
    # Write files directly to the served directory
    (http_test_server.directory / "file.txt").write_text("content")

    # Create subdirectories
    subdir = http_test_server.directory / "subdir"
    subdir.mkdir()
    (subdir / "nested.json").write_text('{"key": "value"}')

    # Files are immediately accessible via HTTP
    response = requests.get(http_test_server.get_url("subdir/nested.json"))
    assert response.json() == {"key": "value"}
```

## Use in Downstream Projects

The HTTP test server fixture is part of the `conda.testing` module and can be used by downstream projects:

```python
# In your project's conftest.py
pytest_plugins = "conda.testing.fixtures"
```

Then use it in your tests:

```python
@pytest.mark.parametrize("http_test_server", ["tests/my-mock-channel"], indirect=True)
def test_with_mock_channel(http_test_server: HttpTestServerFixture):
    channel_url = http_test_server.url
    # ... your test code ...
```

## Troubleshooting

### "ValueError: Directory does not exist"

- This error occurs when using `@pytest.mark.parametrize()` with an invalid path
- Check that the directory path provided in parametrize exists
- Use absolute paths or paths relative to the repository root
- Use `Path(__file__).parent / "data"` if needed
- Or omit the parametrize decorator entirely to use a temporary directory

### "ValueError: Path is not a directory"

- This error occurs when the parametrize value points to a file instead of a directory
- Ensure the path in `@pytest.mark.parametrize(..., indirect=True)` points to a directory
- Or use the fixture without parametrize for dynamic content

### Address already in use

- The fixture uses random ports, so this is rare
- If it happens, the test will likely fail and retry automatically

### Server not shutting down cleanly

- This is handled automatically by the fixture
- The server runs on a daemon thread and will be cleaned up when tests finish

### Files not appearing in HTTP responses

- Make sure files are written before making the HTTP request
- Check that file paths don't have leading slashes when using `get_url()`
- Verify the directory structure with `list(http_test_server.directory.iterdir())`

## Tips and Best Practices

1. **Prefer dynamic content**: Use the fixture without parametrize (dynamic content) for simple use cases. It's simpler and doesn't require maintaining test data files.

2. **Use parametrize for complex data**: Use `@pytest.mark.parametrize(..., indirect=True)` when you have complex directory structures, binary files, or data shared across many tests.

3. **Function scope for isolation**: Each test gets its own temporary directory with the `http_test_server` fixture (function scope), providing complete isolation.

4. **Organize test data**: When using parametrize, keep mock channel data in dedicated directories like `tests/data/mock-channels/` with README files explaining the structure.

5. **Test error scenarios**: Use dynamic content to easily test edge cases like malformed repodata, missing packages, or network timeouts.

6. **Cleanup is automatic**: The fixture handles cleanup automatically - no need to manually shut down servers or delete temporary files.

## Examples from conda Test Suite

See these files for real-world usage examples:

- `tests/testing/test_http_test_server.py` - Tests for the fixture itself
- `tests/env/test_create.py::test_create_update_remote_env_file` - Using remote environment files
- `tests/gateways/test_connection.py` - Connection and download testing
