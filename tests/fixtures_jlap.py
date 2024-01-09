# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Flask-based conda repository server for testing.

Change contents to simulate an updating repository.

Must be imported by conftest.py for pytest to see the fixtures.
"""

from __future__ import annotations

import multiprocessing
import shutil
import socket
import time
from pathlib import Path

import flask
import pytest
from werkzeug.serving import WSGIRequestHandler, generate_adhoc_ssl_context, make_server

app = flask.Flask(__name__)

TEST_REPOSITORY = Path(__file__).parents[0] / "data" / "conda_format_repo"

base = TEST_REPOSITORY  # set to per-test-run value

LATENCY = 0
LATENCY_PER_FILE = {}


@app.route("/shutdown")
def shutdown():
    server.shutdown()
    return "Goodbye"


@app.route("/latency/<float:delay>")
def latency(delay):
    """Set delay before each file response."""
    global LATENCY
    LATENCY = delay
    return "OK"


# @app.route("/latency_per_file/<float:delay>")
# def latency(delay):
#     """
#     Set delay before each file is returned, to simulate bandwidth, file size or
#     streaming compression delays.
#     """
#     LATENCY_PER_FILE[request.args.get("name")] = delay
#     return "OK"


# flask.send_from_directory(directory, path, **kwargs)
# Send a file from within a directory using send_file().
@app.route("/test/<subdir>/<path:name>")
def download_file(subdir, name):
    time.sleep(LATENCY)
    # conditional=True is the default
    # Could have layers, and while raises NotFound (check next base directory)
    return flask.send_from_directory(Path(base, subdir), name)


class NoLoggingWSGIRequestHandler(WSGIRequestHandler):
    def log(self, format, *args):
        pass


def make_server_with_socket(socket: socket.socket, base_: Path = base, ssl=False):
    global server, base
    base = base_
    assert isinstance(socket.fileno(), int)
    ssl_context = None

    if ssl:
        # openssl may fail when mixing defaults + conda-forge
        ssl_context = generate_adhoc_ssl_context()

    server = make_server(
        "127.0.0.1",
        port=0,
        app=app,
        fd=socket.fileno(),
        threaded=True,
        request_handler=NoLoggingWSGIRequestHandler,
        ssl_context=ssl_context,
    )
    server.serve_forever()


def run_on_random_port():
    """Run in a new process to minimize interference with test."""
    return next(_package_server())


def prepare_socket() -> socket.socket:
    """Prepare a socket for use by the WSGI server.

    Based on Werkzeug prepare_socket, removed in 2.2.3
    """
    host = "127.0.0.1"
    port = 0  # automatically choose an available port
    server_address = (host, port)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.set_inheritable(True)
    s.bind(server_address)
    s.listen()
    return s


def _package_server(cleanup=True, base: Path | None = None, ssl=False):
    socket = prepare_socket()
    context = multiprocessing.get_context("spawn")
    process = context.Process(
        target=make_server_with_socket, args=(socket, base, ssl), daemon=True
    )
    process.start()
    yield socket
    process.kill()


@pytest.fixture(scope="session")
def package_repository_base(tmp_path_factory):
    """
    Copy tests/index_data to avoid writing changes to repository.

    Could be made session-scoped if we don't mind re-using the index cache
    during tests.
    """
    # destination can't exist for shutil.copytree(); create its parent
    destination = tmp_path_factory.mktemp("repo") / TEST_REPOSITORY.name
    shutil.copytree(TEST_REPOSITORY, destination)
    return destination


@pytest.fixture(scope="session")
def package_server(package_repository_base):
    yield from _package_server(base=package_repository_base)


@pytest.fixture(scope="session")
def package_server_ssl(package_repository_base):
    yield from _package_server(base=package_repository_base, ssl=True)


if __name__ == "__main__":
    print(run_on_random_port())
    time.sleep(60)
