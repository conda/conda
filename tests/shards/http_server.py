# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Custom HTTP server utilities for serving sharded repodata in tests.
"""

from __future__ import annotations

import contextlib
import http.server
import queue
import socket
import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from http.server import BaseHTTPRequestHandler


def request_handler(request: BaseHTTPRequestHandler, base_path: str | Path) -> None:
    """
    Serve a file from the base_path directory based on the request path.

    This is a simple file serving handler compatible with HTTP request handlers.
    It serves files relative to base_path, returning 404 for missing files.

    :param request: The HTTP request handler instance
    :param base_path: The root directory to serve files from
    """
    base_path = Path(base_path).resolve()

    # Get the requested file path
    file_path = base_path / request.path.lstrip("/")
    file_path = file_path.resolve()

    # Security check: ensure the resolved path is still within base_path
    try:
        file_path.relative_to(base_path)
    except ValueError:
        # Path escape attempt detected
        request.send_error(404, "Not Found")
        return

    # Check if file exists and is a file (not a directory)
    if file_path.is_file():
        try:
            with open(file_path, "rb") as f:
                file_data = f.read()
                request.send_response(200)
                request.send_header("Content-type", "application/octet-stream")
                request.send_header("Content-Length", str(len(file_data)))
                request.end_headers()
                request.wfile.write(file_data)
        except OSError:
            request.send_error(500, "Internal Server Error")
    else:
        request.send_error(404, "Not Found")


def run_server(
    handler: Callable[[BaseHTTPRequestHandler, str], None],
    host: str = "127.0.0.1",
    base_path: str | Path | None = None,
) -> http.server.ThreadingHTTPServer:
    """
    Run a custom HTTP server on a random port with a provided handler function.

    The handler function is called for each request and receives:
    - request: The HTTP request handler instance
    - base_path: The base path provided to run_server

    :param handler: Callable that handles HTTP requests
    :param host: The host to bind to (default "127.0.0.1")
    :param base_path: Base path to pass to the handler
    :return: The running ThreadingHTTPServer instance
    """
    base_path = str(base_path) if base_path else ""

    class CustomRequestHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            handler(self, base_path)

        def log_message(self, format, *args):
            # Suppress logging
            pass

    class DualStackServer(http.server.ThreadingHTTPServer):
        daemon_threads = False
        allow_reuse_address = True
        request_queue_size = 64

        def server_bind(self):
            with contextlib.suppress(Exception):
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            return super().server_bind()

    def start_server(q: queue.Queue):
        with DualStackServer((host, 0), CustomRequestHandler) as httpd:
            q.put(httpd)
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                pass

    q: queue.Queue = queue.Queue()
    thread = threading.Thread(target=start_server, args=(q,), daemon=True)
    thread.start()

    return q.get(timeout=1)
