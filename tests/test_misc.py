# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest

from conda import misc
from conda.common.compat import on_mac, on_win
from conda.core.subdir_data import cache_fn_url
from conda.exceptions import CondaExitZero, ParseError, SpecNotFoundInPackageCache
from conda.misc import (
    _get_url_pattern,
    _match_specs_from_explicit,
    explicit,
    walk_prefix,
)
from conda.utils import Utf8NamedTemporaryFile

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from conda.testing.fixtures import CondaCLIFixture


def test_Utf8NamedTemporaryFile():
    test_string = "ōγђ家固한áêñßôç"
    try:
        with Utf8NamedTemporaryFile(delete=False) as tf:
            tf.write(
                test_string.encode("utf-8")
                if hasattr(test_string, "encode")
                else test_string
            )
            fname = tf.name
        with open(fname, encoding="utf-8") as fh:
            value = fh.read()
        assert value == test_string
    except Exception as exc:
        raise exc


def test_cache_fn_url():
    url = "http://repo.continuum.io/pkgs/pro/osx-64/"

    # implicit repodata.json
    assert cache_fn_url(url) == "7618c8b6.json"

    # explicit repodata.json
    assert cache_fn_url(url, "repodata.json") == "7618c8b6.json"

    # explicit current_repodata.json
    assert cache_fn_url(url, "current_repodata.json") == "8be5dc16.json"

    url = "http://repo.anaconda.com/pkgs/pro/osx-64/"
    assert cache_fn_url(url) == "e42afea8.json"


def test_url_pat_1():
    url_pat = _get_url_pattern()
    match = url_pat.match(
        "http://test/pkgs/linux-64/foo.tar.bz2#d6918b03927360aa1e57c0188dcb781b"
    )
    assert match.group("url_p") == "http://test/pkgs/linux-64"
    assert match.group("fn") == "foo.tar.bz2"
    assert match.group("md5") == "d6918b03927360aa1e57c0188dcb781b"


def test_url_pat_2():
    url_pat = _get_url_pattern()
    match = url_pat.match("http://test/pkgs/linux-64/foo.tar.bz2")
    assert match.group("url_p") == "http://test/pkgs/linux-64"
    assert match.group("fn") == "foo.tar.bz2"
    assert match.group("md5") is None


def test_url_pat_3():
    url_pat = _get_url_pattern()
    match = url_pat.match("http://test/pkgs/linux-64/foo.tar.bz2#1234")
    assert match is None


def test_explicit_no_cache(mocker: MockerFixture) -> None:
    """Test that explicit() raises and notifies if none of the specs were found in the cache."""
    # Patching ProgressiveFetchExtract prevents trying to download a package from the url.
    # Note that we cannot monkeypatch context.dry_run, because explicit() would exit early with that.
    mocker.patch("conda.misc.ProgressiveFetchExtract")

    with pytest.raises(
        SpecNotFoundInPackageCache, match="No package cache records found"
    ):
        explicit(
            [
                "http://test/pkgs/linux-64/foo-1.0.0-py_0.tar.bz2",
                "http://test/pkgs/linux-64/bar-1.0.0-py_0.tar.bz2",
            ],
            "",
        )


def test_explicit_missing_cache_entries(
    test_recipes_channel: Path,
    mocker: MockerFixture,
    conda_cli: CondaCLIFixture,
):
    """Test that explicit() raises and notifies if some of the specs were not found in the cache."""
    # ensure there is something in the cache
    stdout, stderr, excinfo = conda_cli(
        "install",
        "small-executable",
        "--yes",
        "--download-only",
        raises=CondaExitZero,
    )
    assert stdout
    assert not stderr
    assert isinstance(excinfo.value, CondaExitZero)

    # Patching ProgressiveFetchExtract prevents trying to download a package from the url.
    # Note that we cannot monkeypatch context.dry_run, because explicit() would exit early with that.
    mocker.patch("conda.misc.ProgressiveFetchExtract")

    with pytest.raises(
        SpecNotFoundInPackageCache,
        match="Missing package cache records for: test-recipes/noarch::missing==1.0.0=0",
    ):
        schema = "file:///" if on_win else "file://"
        noarch = test_recipes_channel / "noarch"
        explicit(
            [
                f"{schema}{(noarch / 'missing-1.0.0-0.tar.bz2').as_posix()}",
                f"{schema}{(noarch / 'small-executable-1.0.0-0.conda').as_posix()}",
            ],
            None,  # the assertion is raised before the prefix matters
        )


def make_mock_directory(tmpdir, mock_directory):
    for key, value in mock_directory.items():
        if value is None:
            tmpdir.join(key).write("TEST")
        else:
            make_mock_directory(tmpdir.mkdir(key), value)


def test_walk_prefix(tmpdir):  # tmpdir is a py.test utility
    # Each directory is a dict whose keys are names. If the value is
    # None, then that key represents a file. If it's another dict, that key is
    # a file
    mock_directory = {
        "LICENSE.txt": None,
        "envs": {"ignore1": None, "ignore2": None},
        "python.app": None,
        "bin": {"activate": None, "conda": None, "deactivate": None, "testfile": None},
        "testdir1": {"testfile": None, "testdir2": {"testfile": None}},
        "testfile1": None,
    }

    make_mock_directory(tmpdir, mock_directory)

    # walk_prefix has windows_forward_slahes on by default, so we don't need
    # any special-casing there

    answer = {
        "testfile1",
        "bin/testfile",
        "testdir1/testfile",
        "testdir1/testdir2/testfile",
    }
    if not on_mac:
        answer.add("python.app")

    assert walk_prefix(tmpdir.strpath) == answer


@pytest.mark.parametrize(
    "url, checksum, raises",
    (
        [
            "https://conda.anaconda.org/conda-forge/noarch/doc8-1.1.1-pyhd8ed1ab_0.conda",
            "5e9e17751f19d03c4034246de428582e",
            None,
        ],
        [
            "https://conda.anaconda.org/conda-forge/noarch/conda-24.1.0-pyhd3eb1b0_0.conda",
            "2707f68aada792d1cf3a44c51d55b38b0cd65b0c192d2a5f9ef0550dc149a7d3",
            None,
        ],
        [
            "https://conda.anaconda.org/conda-forge/noarch/conda-24.1.0-pyhd3eb1b0_0.conda",
            "sha256:2707f68aada792d1cf3a44c51d55b38b0cd65b0c192d2a5f9ef0550dc149a7d3",
            None,
        ],
        [
            "https://conda.anaconda.org/conda-forge/noarch/conda-24.1.0-pyhd3eb1b0_0.conda",
            "sha123:2707f68aada792d1cf3a44c51d55b38b0cd65b0c192d2a5f9ef0550dc149a7d3",
            ParseError,
        ],
        [
            "https://conda.anaconda.org/conda-forge/noarch/conda-24.1.0-pyhd3eb1b0_0.conda",
            "md5:5e9e17751f19d03c4034246de428582e",  # this is not valid syntax; use without 'md5:'
            ParseError,
        ],
        [
            "doc8-1.1.1-pyhd8ed1ab_0.conda",
            "5e9e17751f19d03c4034246de428582e",
            None,
        ],
        [
            "../doc8-1.1.1-pyhd8ed1ab_0.conda",
            "5e9e17751f19d03c4034246de428582e",
            None,
        ],
        [
            "../doc8-1.1.1-pyhd8ed1ab_0.conda",
            "5e9e17751f19d03",
            ParseError,
        ],
    ),
)
def test_explicit_parser(url: str, checksum: str, raises: Exception | None):
    lines = [url + (f"#{checksum}" if checksum else "")]
    with pytest.raises(raises) if raises else nullcontext():
        specs = list(_match_specs_from_explicit(lines))

        assert len(specs) == 1
        spec = specs[0]
        assert spec.get("url").split("/")[-1] == url.split("/")[-1]
        assert checksum.rsplit(":", 1)[-1] in (spec.get("md5"), spec.get("sha256"))


@pytest.mark.parametrize(
    "function,raises",
    [
        ("url_pat", TypeError),
    ],
)
def test_deprecations(function: str, raises: type[Exception] | None) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(misc, function)()
