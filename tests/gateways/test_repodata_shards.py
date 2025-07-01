"""
Fetch sharded repodata.
"""

from pathlib import Path

from conda.gateways.repodata import RepodataCache


def test_bytes_cache(tmp_path):
    test_data = (
        Path(__file__).parents[1]
        / "data"
        / "conda_format_repo"
        / "linux-64"
        / "repodata_shards.msgpack.zst"
    )
    assert test_data.exists()
    base = tmp_path / "bytes"
    cache = RepodataCache(base, "repodata_shards.msgpack.zst")
    cache.save(test_data.read_bytes())

    data = cache.load(binary=True)
    # also re-reads cache.state from disk
    assert isinstance(cache.state['mtime_ns'], int)
    assert data == test_data.read_bytes()
