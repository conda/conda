# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import socket
import tempfile
from pathlib import Path

import pytest

from .helpers import have_minio


def s3_server(xprocess):
    """
    Mock a local S3 server using `minio`

    This requires:
    - pytest-xprocess: runs the background process
    - minio: the executable must be in PATH

    Note it will be given EMPTY! The test function needs
    to populate it. You can use
    `conda.testing.helpers.populate_s3_server` for that.
    """
    # The 'name' below will be the name of the S3 bucket containing
    # keys like `noarch/repodata.json`
    NAME = "s3_server"
    PORT = 9000

    from xprocess import ProcessStarter

    temp = tempfile.TemporaryDirectory()
    (Path(temp.name) / NAME).mkdir()

    print("Starting mock_s3_server")

    class Starter(ProcessStarter):

        pattern = "https://docs.min.io"
        terminate_on_interrupt = True
        timeout = 10
        args = [
            "minio",
            "server",
            f"--address=:{PORT}",
            str(temp.name),
        ]

        def startup_check(self, port=PORT):
            s = socket.socket()
            address = "localhost"
            error = False
            try:
                s.connect((address, port))
            except Exception as e:
                print("something's wrong with %s:%d. Exception is %s" % (address, port, e))
                error = True
            finally:
                s.close()

            return not error

    logfile = xprocess.ensure(NAME, Starter)

    yield f"http://localhost:{PORT}/{NAME}"

    xprocess.getinfo(NAME).terminate()


if have_minio:
    s3_server = pytest.fixture(autouse=True)(s3_server)
