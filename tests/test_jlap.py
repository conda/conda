# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Test that SubdirData is able to use (or skip) incremental jlap downloads.
"""
from pathlib import Path

import requests

from conda.gateways.repodata import repo_jlap


def test_server_available(package_server):
    port = package_server.getsockname()[1]
    response = requests.get(f"http://127.0.0.1:{port}/notfound")
    assert response.status_code == 404


def test_jlap_fetch(package_server, tmpdir):
    host, port = package_server.getsockname()
    base = f"http://{host}:{port}/test"

    url = f"{base}/osx-64"
    repo = repo_jlap.JlapRepoInterface(
        url,
        repodata_fn="repodata.json",
        cache_path_json=Path(tmpdir, "repodata.json"),
        cache_path_state=Path(tmpdir, "repodata.state.json"),
    )

    state = {}
    data_json = repo.repodata(state)

    # second will try to fetch (non-existent) .jlap, then fall back to .json
    data_json = repo.repodata(state)  # a 304?
