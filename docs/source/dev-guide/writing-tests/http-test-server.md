# HTTP Test Server Fixture

The HTTP test server fixture provides a way to test conda functionality that requires serving files over HTTP, such as:
- Mock conda channels with packages
- Remote environment files (environment.yml)
- Remote configuration files
- Any scenario where conda needs to fetch files from a URL

## Overview

The `http_test_server` and `session_http_test_server` fixtures start a local HTTP server that serves files from a directory you specify. The server runs on a random port and supports both IPv4 and IPv6.

## Basic Usage

### Function-Scoped Fixture

Use `http_test_server` when each test needs its own server instance:

```python
import pytest
import requests


@pytest.mark.http_server_dir("tests/data/mock-channel")
def test_fetch_from_channel(http_test_server):
    # Get URL for a specific file
    repodata_url = http_test_server.get_url("linux-64/repodata.json")

    # Make request
    response = requests.get(repodata_url)
    assert response.status_code == 200

    # The base URL is also available
    print(f"Server running at: {http_test_server.url}")
    print(f"Host: {http_test_server.host}, Port: {http_test_server.port}")
```

### Session-Scoped Fixture

Use `session_http_test_server` when multiple tests can share the same server:

```python
@pytest.mark.http_server_dir("tests/env/support")
def test_remote_env_file_1(session_http_test_server):
    url = session_http_test_server.get_url("example/environment.yml")
    # ... test code ...


@pytest.mark.http_server_dir("tests/env/support")
def test_remote_env_file_2(session_http_test_server):
    url = session_http_test_server.get_url("example/environment_updated.yml")
    # ... test code ...
```

**Important**: All tests using `session_http_test_server` must specify the SAME directory in the marker.

## Marker Requirement

Both fixtures **require** the `@pytest.mark.http_server_dir()` marker:

```python
@pytest.mark.http_server_dir("/absolute/or/relative/path")
def test_example(http_test_server): ...
```

If you forget the marker, you'll get a helpful error:
```
ValueError: Test test_example.py::test_example requires
@pytest.mark.http_server_dir(directory) marker to specify the directory to serve.
Example: @pytest.mark.http_server_dir("tests/data/mock-channel")
```

## Complete Example: Testing a Mock Channel

Here's a full example showing how to test conda against a mock channel:

```python
import pytest
from pathlib import Path
from conda.testing.fixtures import CondaCLIFixture

# Assume we have this directory structure:
# tests/data/mock-channel/
#   ├── noarch/
#   │   └── repodata.json
#   └── linux-64/
#       ├── repodata.json
#       └── example-pkg-1.0.0-0.tar.bz2


@pytest.mark.integration
@pytest.mark.http_server_dir("tests/data/mock-channel")
def test_install_from_mock_channel(
    http_test_server,
    conda_cli: CondaCLIFixture,
    tmp_path: Path,
):
    """Test installing a package from a local mock channel."""
    # The server is serving files from tests/data/mock-channel/
    channel_url = http_test_server.url

    # Create environment with package from mock channel
    stdout, stderr, code = conda_cli(
        "create",
        "--prefix",
        tmp_path,
        "--channel",
        channel_url,
        "example-pkg",
        "--yes",
    )

    assert code == 0
    # Verify package installed
    assert (tmp_path / "conda-meta" / "example-pkg-1.0.0-0.json").exists()
```

## Using with tmp_path

For dynamic content, you can use the server module directly:

```python
import json
from conda.testing import http_test_server


def test_dynamic_content(tmp_path):
    """Create test files dynamically and serve them."""
    # Create test files
    channel_dir = tmp_path / "channel"
    channel_dir.mkdir()
    (channel_dir / "repodata.json").write_text(json.dumps({"packages": {}}))

    # Import and use the server module directly
    server = http_test_server.run_test_server(str(channel_dir))

    try:
        host, port = server.socket.getsockname()[:2]
        url = f"http://{host}:{port}"
        # ... use url in test ...
    finally:
        server.shutdown()
```

## Fixture API Reference

### HttpTestServerFixture

The fixture returns an instance with these attributes and methods:

**Attributes:**
- `server: http.server.ThreadingHTTPServer` - The underlying server instance
- `host: str` - Server host (usually "127.0.0.1")
- `port: int` - Server port (random)
- `url: str` - Base URL (e.g., "http://127.0.0.1:54321")

**Methods:**
- `get_url(path: str = "") -> str` - Get full URL for a path
  - Example: `get_url("linux-64/repodata.json")` → `"http://127.0.0.1:54321/linux-64/repodata.json"`

## Migration from `support_file_server`

If you're using the older `support_file_server` fixture, here's how to migrate:

**Old code:**
```python
def test_remote_files(support_file_server_port):
    url = f"http://127.0.0.1:{support_file_server_port}/example/file.yml"
    ...
```

**New code:**
```python
@pytest.mark.http_server_dir("tests/env/support")
def test_remote_files(session_http_test_server):
    url = session_http_test_server.get_url("example/file.yml")
    ...
```

Benefits of the new approach:
- More flexible (any directory, not just tests/env/support)
- Explicit about what directory is being served
- Better error messages
- Type-safe with IDE support

## Use in Downstream Projects

The HTTP test server fixtures are part of `conda.testing` module and can be used by downstream projects like `conda-libmamba-solver` and `conda-pypi`:

```python
# In your project's conftest.py
pytest_plugins = "conda.testing.fixtures"


# In your tests
@pytest.mark.http_server_dir("tests/my-mock-channel")
def test_with_mock_channel(http_test_server):
    channel_url = http_test_server.url
    # ... your test code ...
```

## Troubleshooting

**"ValueError: requires @pytest.mark.http_server_dir marker"**
- Add the marker to your test: `@pytest.mark.http_server_dir("/path/to/dir")`

**"ValueError: Directory does not exist"**
- Check that the path in the marker exists
- Use absolute paths or paths relative to the repository root
- Use `Path(__file__).parent / "data"` if needed

**"ValueError: Path is not a directory"**
- Ensure the path points to a directory, not a file
- The marker argument must be a directory containing files to serve

**Address already in use**
- The fixture uses random ports, so this is rare
- If it happens, the test will likely fail and retry automatically

**Server not shutting down cleanly**
- This is handled automatically by the fixture
- The server runs on a daemon thread and will be cleaned up when tests finish

## Tips and Best Practices

1. **Use function scope for isolation**: If tests modify the served files or need different setups, use `http_test_server` (function scope) instead of `session_http_test_server`.

2. **Organize test data**: Keep mock channel data in dedicated directories like `tests/data/mock-channels/`.

3. **Document channel structure**: Add a README in your mock channel directories explaining what files are present and why.

4. **Test offline scenarios**: Use the HTTP server to test error handling when repodata is malformed or packages are missing.

5. **Performance**: If multiple tests use the same large channel data, use `session_http_test_server` to avoid repeated server startups.

6. **Cleanup**: The fixtures handle cleanup automatically - no need to manually shut down servers.

## Examples from conda Test Suite

See these files for real-world usage examples:
- `tests/testing/test_http_test_server.py` - Tests for the fixtures themselves
- `tests/env/test_create.py::test_create_update_remote_env_file` - Using remote environment files
- `tests/gateways/test_connection.py` - Connection and download testing
