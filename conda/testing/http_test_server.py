# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
HTTP test server for serving local files during tests.

This module provides a local HTTP server that can be used in pytest fixtures
to serve files from a specified directory. The server runs on a random port
and supports both IPv4 and IPv6.

The server is commonly used for testing:
- Mock conda channels with packages and repodata
- Remote environment files (environment.yml)
- Remote configuration files
- Any scenario where conda needs to fetch files from HTTP URLs

Example usage:

    from conda.testing import http_test_server

    def test_something():
        server = http_test_server.run_test_server("/path/to/files")
        host, port = server.socket.getsockname()[:2]
        url = f"http://{host}:{port}/file.txt"

        # Make HTTP requests to url...

        server.shutdown()

For pytest fixtures that wrap this functionality, see:
- `http_test_server` - function-scoped fixture

The fixture can be configured via `@pytest.mark.parametrize("http_test_server", ["<directory>"], indirect=True)`
to specify the directory to serve, or used without parametrize (or with `None`) for dynamic content generation.
"""

from collections.abc import Callable
from contextlib import suppress
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from queue import Queue
from socket import IPPROTO_IPV6, IPV6_V6ONLY
from threading import Thread


def run_test_server(
    directory: str,
    finish_request_action: Callable[[], None] | None = None,
) -> ThreadingHTTPServer:
    """
    Run a test server on a random port. Inspect returned server to get port,
    shutdown etc.

    Args:
        directory: Directory to serve files from.
        finish_request_action: Optional callable invoked before each request is
            handled (e.g. to inject latency or failures).
    """

    class DualStackServer(ThreadingHTTPServer):
        daemon_threads = False  # These are per-request threads
        allow_reuse_address = True  # Good for tests
        request_queue_size = 64  # Should be more than the number of test packages

        def server_bind(self):
            # suppress exception when protocol is IPv4
            with suppress(Exception):
                self.socket.setsockopt(IPPROTO_IPV6, IPV6_V6ONLY, 0)
            return super().server_bind()

        def finish_request(self, request, client_address):
            if finish_request_action:
                finish_request_action()
            super().finish_request(request, client_address)

    def start_server(queue):
        try:
            with DualStackServer(
                ("127.0.0.1", 0),
                partial(SimpleHTTPRequestHandler, directory=directory),
            ) as httpd:
                host, port = httpd.socket.getsockname()[:2]
                queue.put(httpd)
                url_host = f"[{host}]" if ":" in host else host
                print(
                    f"Serving HTTP on {host} port {port} (http://{url_host}:{port}/) ..."
                )
                try:
                    httpd.serve_forever()
                except KeyboardInterrupt:
                    print("\nKeyboard interrupt received, exiting.")
        except Exception as exc:
            queue.put(exc)

    started: Queue[ThreadingHTTPServer | Exception] = Queue()

    Thread(target=start_server, args=(started,), daemon=True).start()

    result = started.get(timeout=1)
    if isinstance(result, Exception):
        raise result
    return result


if __name__ == "__main__":
    server = run_test_server(directory=".")
    print(server)
