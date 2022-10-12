"""
Test that SubdirData is able to use (or skip) incremental jlap downloads.
"""

import requests


def test_server_available(package_server):
    port = package_server.getsockname()[1]
    response = requests.get(f"http://127.0.0.1:{port}/notfound")
    assert response.status_code == 404

# test falls back when current_repodata.json is not available

# ...
