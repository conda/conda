# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Local test server based on http.server
"""

import contextlib
import http.server
import queue
import socket
import threading


def run_test_server(directory: str) -> http.server.ThreadingHTTPServer:
    """
    Run a test server on a random port. Inspect returned server to get port,
    shutdown etc.
    """

    class DualStackServer(http.server.ThreadingHTTPServer):
        daemon_threads = False  # These are per-request threads
        allow_reuse_address = True  # Good for tests
        request_queue_size = 64  # Should be more than the number of test packages

        def server_bind(self):
            # suppress exception when protocol is IPv4
            with contextlib.suppress(Exception):
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            return super().server_bind()

        def finish_request(self, request, client_address):
            self.RequestHandlerClass(request, client_address, self, directory=directory)

    def start_server(queue):
        with DualStackServer(
            ("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler
        ) as httpd:
            host, port = httpd.socket.getsockname()[:2]
            queue.put(httpd)
            url_host = f"[{host}]" if ":" in host else host
            print(
                f"Serving HTTP on {host} port {port} "
                f"(http://{url_host}:{port}/) ..."
            )
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nKeyboard interrupt received, exiting.")

    started = queue.Queue()

    threading.Thread(target=start_server, args=(started,), daemon=True).start()

    return started.get(timeout=1)


if __name__ == "__main__":
    server = run_test_server(directory=".")
    print(server)
