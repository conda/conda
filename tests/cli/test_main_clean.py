# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from glob import glob
from json import loads as json_loads
from os import listdir
from os.path import basename, isdir, join, exists
from shutil import copy
import pytest
from conda.base.constants import CONDA_TEMP_EXTENSION
from conda.core.subdir_data import create_cache_dir, SubdirData
from conda.testing.integration import make_temp_package_cache, run_command, Commands, make_temp_env


def _get_contents(pkgs_dir):
    return [join(pkgs_dir, d) for d in listdir(pkgs_dir)]


def _get_pkgs(pkgs_dir=None, *, contents=None):
    return [d for d in contents or _get_contents(pkgs_dir) if isdir(d)]


def _get_tars(pkgs_dir=None, *, contents=None):
    return [t for t in contents or _get_contents(pkgs_dir) if t.endswith((".tar.bz2", ".conda"))]


def _get_index_cache():
    return glob(join(create_cache_dir(), "*.json"))


def _get_tempfiles(pkgs_dir=None, *, contents=None):
    return [
        t
        for t in contents or _get_contents(pkgs_dir)
        if t.endswith((".trash", CONDA_TEMP_EXTENSION))
    ]


def _get_all(pkgs_dir):
    contents = _get_contents(pkgs_dir)
    return _get_pkgs(contents=contents), _get_tars(contents=contents), _get_index_cache()


def _any_pkg(name, contents):
    return any(basename(c).startswith(f"{name}-") for c in contents)


@pytest.fixture
def clear_cache():
    SubdirData._cache_.clear()


# conda clean --force-pkgs-dirs
def test_clean_force_pkgs_dirs(clear_cache):
    pkg = "bzip2"

    with make_temp_package_cache() as pkgs_dir:
        # pkgs_dir is a directory
        assert isdir(pkgs_dir)

        with make_temp_env(pkg):
            stdout, _, _ = run_command(Commands.CLEAN, "", "--force-pkgs-dirs", "--yes", "--json")
            json_loads(stdout)  # assert valid json

            # pkgs_dir is removed
            assert not exists(pkgs_dir)

        # pkgs_dir is still removed
        assert not exists(pkgs_dir)


# conda clean --packages
def test_clean_and_packages(clear_cache):
    pkg = "bzip2"

    with make_temp_package_cache() as pkgs_dir:
        # pkg doesn't exist ahead of time
        assert not _any_pkg(pkg, _get_pkgs(pkgs_dir))

        with make_temp_env(pkg) as prefix:
            # pkg exists
            assert _any_pkg(pkg, _get_pkgs(pkgs_dir))

            # --json flag is regression test for #5451
            stdout, _, _ = run_command(Commands.CLEAN, "", "--packages", "--yes", "--json")
            json_loads(stdout)  # assert valid json

            # pkg still exists since its in use by temp env
            assert _any_pkg(pkg, _get_pkgs(pkgs_dir))

            run_command(Commands.REMOVE, prefix, pkg, "--yes", "--json")
            stdout, _, _ = run_command(Commands.CLEAN, "", "--packages", "--yes", "--json")
            json_loads(stdout)  # assert valid json

            # pkg is removed
            assert not _any_pkg(pkg, _get_pkgs(pkgs_dir))

        # pkg is still removed
        assert not _any_pkg(pkg, _get_pkgs(pkgs_dir))


# conda clean --tarballs
def test_clean_tarballs(clear_cache):
    pkg = "bzip2"

    with make_temp_package_cache() as pkgs_dir:
        # tarball doesn't exist ahead of time
        assert not _any_pkg(pkg, _get_tars(pkgs_dir))

        with make_temp_env(pkg):
            # tarball exists
            assert _any_pkg(pkg, _get_tars(pkgs_dir))

            # --json flag is regression test for #5451
            stdout, _, _ = run_command(Commands.CLEAN, "", "--tarballs", "--yes", "--json")
            json_loads(stdout)  # assert valid json

            # tarball is removed
            assert not _any_pkg(pkg, _get_tars(pkgs_dir))

        # tarball is still removed
        assert not _any_pkg(pkg, _get_tars(pkgs_dir))


# conda clean --index-cache
def test_clean_index_cache(clear_cache):
    pkg = "bzip2"

    with make_temp_package_cache():
        # index cache doesn't exist ahead of time
        assert not _get_index_cache()

        with make_temp_env(pkg):
            # index cache exists
            assert _get_index_cache()

            stdout, _, _ = run_command(Commands.CLEAN, "", "--index-cache", "--yes", "--json")
            json_loads(stdout)  # assert valid json

            # index cache is cleared
            assert not _get_index_cache()

        # index cache is still cleared
        assert not _get_index_cache()


# conda clean --tempfiles
def test_clean_tempfiles(clear_cache):
    """Tempfiles are either suffixed with .c~ or .trash.

    .c~ is used to indicate that conda is actively using that file. If the conda process is
    terminated unexpectedly these .c~ files may remain and hence can be cleaned up after the fact.

    .trash appears to be a legacy suffix that is no longer used by conda.

    Since the presence of .c~ and .trash files are dependent upon irregular termination we create
    our own temporary files to confirm they get cleaned up.
    """
    pkg = "bzip2"

    with make_temp_package_cache() as pkgs_dir:
        # tempfiles don't exist ahead of time
        assert not _get_tempfiles(pkgs_dir)

        with make_temp_env(pkg):
            # mimic tempfiles being created
            path = _get_tars(contents=glob(join(pkgs_dir, f"{pkg}-*")))[0]
            copy(path, f"{path}{CONDA_TEMP_EXTENSION}")
            copy(path, f"{path}.trash")

            # tempfiles exist
            assert len(_get_tempfiles(pkgs_dir)) == 2

            # --json flag is regression test for #5451
            stdout, _, _ = run_command(
                Commands.CLEAN, "", "--tempfiles", pkgs_dir, "--yes", "--json"
            )
            json_loads(stdout)  # assert valid json

            # tempfiles removed
            assert not _get_tempfiles(pkgs_dir)

        # tempfiles still removed
        assert not _get_tempfiles(pkgs_dir)


# conda clean --all
def test_clean_all(clear_cache):
    pkg = "bzip2"

    with make_temp_package_cache() as pkgs_dir:
        # pkg, tarball, & index cache doesn't exist ahead of time
        pkgs, tars, cache = _get_all(pkgs_dir)
        assert not _any_pkg(pkg, pkgs)
        assert not _any_pkg(pkg, tars)
        assert not cache

        with make_temp_env(pkg) as prefix:
            # pkg, tarball, & index cache exists
            pkgs, tars, cache = _get_all(pkgs_dir)
            assert _any_pkg(pkg, pkgs)
            assert _any_pkg(pkg, tars)
            assert cache

            stdout, _, _ = run_command(Commands.CLEAN, "", "--all", "--yes", "--json")
            json_loads(stdout)  # assert valid json

            # pkg still exists since its in use by temp env
            # tarball is removed
            # index cache is cleared
            pkgs, tars, cache = _get_all(pkgs_dir)
            assert _any_pkg(pkg, pkgs)
            assert not _any_pkg(pkg, tars)
            assert not cache

            run_command(Commands.REMOVE, prefix, pkg, "--yes", "--json")
            stdout, _, _ = run_command(Commands.CLEAN, "", "--packages", "--yes", "--json")
            json_loads(stdout)  # assert valid json

            # pkg is removed
            # tarball is still removed
            # index cache is still cleared
            pkgs, tars, index_cache = _get_all(pkgs_dir)
            assert not _any_pkg(pkg, pkgs)
            assert not _any_pkg(pkg, tars)
            assert not cache

        # pkg is still removed
        # tarball is still removed
        # index cache is still cleared
        pkgs, tars, index_cache = _get_all(pkgs_dir)
        assert not _any_pkg(pkg, pkgs)
        assert not _any_pkg(pkg, tars)
        assert not cache
