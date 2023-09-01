# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import codecs
import sys
import warnings
from unittest.mock import patch

import pytest
from pytest_mock import MockerFixture

from conda.core.subdir_data import cache_fn_url
from conda.misc import explicit, url_pat, walk_prefix
from conda.testing import CondaCLIFixture, TmpEnvFixture
from conda.utils import Utf8NamedTemporaryFile


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
        with codecs.open(fname, mode="rb", encoding="utf-8") as fh:
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
    match = url_pat.match(
        "http://test/pkgs/linux-64/foo.tar.bz2" "#d6918b03927360aa1e57c0188dcb781b"
    )
    assert match.group("url_p") == "http://test/pkgs/linux-64"
    assert match.group("fn") == "foo.tar.bz2"
    assert match.group("md5") == "d6918b03927360aa1e57c0188dcb781b"


def test_url_pat_2():
    match = url_pat.match("http://test/pkgs/linux-64/foo.tar.bz2")
    assert match.group("url_p") == "http://test/pkgs/linux-64"
    assert match.group("fn") == "foo.tar.bz2"
    assert match.group("md5") is None


def test_url_pat_3():
    match = url_pat.match("http://test/pkgs/linux-64/foo.tar.bz2#1234")
    assert match is None


# Patching ProgressiveFetchExtract prevents trying to download a package from the url.
# Note that we cannot monkeypatch context.dry_run, because explicit() would exit early with that.
@patch("conda.misc.ProgressiveFetchExtract")
def test_explicit_no_cache(ProgressiveFetchExtract):
    """Test that explicit() raises and notifies if none of the specs were found in the cache."""
    with pytest.raises(AssertionError, match="No package cache records found"):
        explicit(
            [
                "http://test/pkgs/linux-64/foo-1.0.0-py_0.tar.bz2",
                "http://test/pkgs/linux-64/bar-1.0.0-py_0.tar.bz2",
            ],
            "",
        )


def test_explicit_missing_cache_entries(
    mocker: MockerFixture,
    conda_cli: CondaCLIFixture,
    tmp_env: TmpEnvFixture,
):
    """Test that explicit() raises and notifies if some of the specs were not found in the cache."""
    from conda.core.package_cache_data import PackageCacheData

    with tmp_env() as prefix:  # ensure writable env
        if len(PackageCacheData.get_all_extracted_entries()) == 0:
            # Package cache e.g. ./devenv/Darwin/x86_64/envs/devenv-3.9-c/pkgs/ can
            # be empty in certain cases (Noted in OSX with Python 3.9, when
            # Miniconda installs Python 3.10). Install a small package.
            warnings.warn("test_explicit_missing_cache_entries: No packages in cache.")
            conda_cli("install", "--prefix", prefix, "heapdict", "--yes")

        # Patching ProgressiveFetchExtract prevents trying to download a package from the url.
        # Note that we cannot monkeypatch context.dry_run, because explicit() would exit early with that.
        mocker.patch("conda.misc.ProgressiveFetchExtract")

        with pytest.raises(
            AssertionError,
            match="Missing package cache records for: pkgs/linux-64::foo==1.0.0=py_0",
        ):
            explicit(
                [
                    "http://test/pkgs/linux-64/foo-1.0.0-py_0.tar.bz2",  # does not exist
                    PackageCacheData.get_all_extracted_entries()[0].url,  # exists
                ],
                prefix,
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
    if sys.platform != "darwin":
        answer.add("python.app")

    assert walk_prefix(tmpdir.strpath) == answer
