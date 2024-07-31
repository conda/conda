# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda.common.toposort import pop_key, toposort


def test_pop_key():
    key = pop_key({"a": {"b", "c"}, "b": {"c"}})
    assert key == "b"

    key = pop_key({"a": {"b"}, "b": {"c", "a"}})
    assert key == "a"

    key = pop_key({"a": {"b"}, "b": {"a"}})
    assert key == "a"


def test_simple():
    data = {"a": "bc", "b": "c"}
    results = toposort(data, safe=True)
    assert results == ["c", "b", "a"]
    results = toposort(data, safe=False)
    assert results == ["c", "b", "a"]


def test_cycle():
    data = {"a": "b", "b": "a"}

    with pytest.raises(ValueError):
        toposort(data, False)

    results = toposort(data)
    # Results do not have an guaranteed order
    assert set(results) == {"b", "a"}


def test_cycle_best_effort():
    data = {"a": "bc", "b": "c", "1": "2", "2": "1"}

    results = toposort(data)
    assert results[:3] == ["c", "b", "a"]

    # Cycles come last
    # Results do not have an guaranteed order
    assert set(results[3:]) == {"1", "2"}


def test_python_is_prioritized():
    """
    This test checks a special invariant related to 'python' specifically.
    Python is part of a cycle (pip <--> python), which can cause it to be
    installed *after* packages that need python (possibly in
    post-install.sh).

    A special case in toposort() breaks the cycle, to ensure that python
    isn't installed too late.  Here, we verify that it works.
    """
    # This is the actual dependency graph for python (as of the time of this writing, anyway)
    data = {
        "python": ["pip", "openssl", "readline", "sqlite", "tk", "xz", "zlib"],
        "pip": ["python", "setuptools", "wheel"],
        "setuptools": ["python"],
        "wheel": ["python"],
        "openssl": [],
        "readline": [],
        "sqlite": [],
        "tk": [],
        "xz": [],
        "zlib": [],
    }

    # Here are some extra pure-python libs, just for good measure.
    data.update(
        {
            "psutil": ["python"],
            "greenlet": ["python"],
            "futures": ["python"],
            "six": ["python"],
        }
    )

    results = toposort(data)

    # Python always comes before things that need it!
    assert results.index("python") < results.index("setuptools")
    assert results.index("python") < results.index("wheel")
    assert results.index("python") < results.index("pip")
    assert results.index("python") < results.index("psutil")
    assert results.index("python") < results.index("greenlet")
    assert results.index("python") < results.index("futures")
    assert results.index("python") < results.index("six")


def test_degenerate():
    """Edge cases."""
    assert toposort({}) == []
    assert toposort({}, safe=False) == []
