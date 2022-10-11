"""
Flask-based conda repository server for testing.

Change contents to simulate an updating repository.

Must be imported by conftest.py for pytest to see the fixtures.
"""

import multiprocessing
import socket
import time
from pathlib import Path

import flask
import pytest
from werkzeug.serving import WSGIRequestHandler, make_server, prepare_socket

app = flask.Flask(__name__)

base = Path(__file__).parents[1] / "data" / "conda_format_repo"

LATENCY = 0


@app.route("/shutdown")
def shutdown():
    server.shutdown()
    return "Goodbye"


@app.route("/latency/<float:delay>")
def latency(delay):
    """
    Set delay before each file response.
    """
    global LATENCY
    LATENCY = delay
    return "OK"


# flask.send_from_directory(directory, path, **kwargs)
# Send a file from within a directory using send_file().
@app.route("/<subdir>/<path:name>")
def download_file(subdir, name):
    time.sleep(LATENCY)
    # conditional=True is the default
    # Could have layers, and while raises NotFound (check next base directory)
    return flask.send_from_directory(base, name)


class NoLoggingWSGIRequestHandler(WSGIRequestHandler):
    def log(self, format, *args):
        pass


def make_server_with_socket(socket: socket.socket):
    global server
    assert isinstance(socket.fileno(), int)
    server = make_server(
        "127.0.0.1",
        port=0,
        app=app,
        fd=socket.fileno(),
        threaded=True,
        request_handler=NoLoggingWSGIRequestHandler,
    )
    server.serve_forever()


def run_on_random_port():
    """
    Run in a new process to minimize interference with test.
    """
    return next(_package_server())


def _package_server(cleanup=True):
    socket = prepare_socket("127.0.0.1", 0)
    context = multiprocessing.get_context("spawn")
    process = context.Process(
        target=make_server_with_socket, args=(socket,), daemon=True
    )
    process.start()
    yield socket
    process.kill()


@pytest.fixture(scope="session")
def package_server():
    yield from _package_server()


if __name__ == "__main__":

    print(run_on_random_port())
    time.sleep(60)
