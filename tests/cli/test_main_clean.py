# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from glob import glob
from json import loads as json_loads
from os import listdir
from os.path import basename, isdir, join
from conda.core.subdir_data import create_cache_dir
from conda.testing.integration import make_temp_package_cache, run_command, Commands, make_temp_env


def test_clean_index_cache():
    prefix = ""

    # make sure we have something in the index cache
    stdout, _, _ = run_command(Commands.INFO, prefix, "bzip2", "--json")
    assert "bzip2" in json_loads(stdout)
    index_cache_dir = create_cache_dir()
    assert glob(join(index_cache_dir, "*.json"))

    # now clear it
    run_command(Commands.CLEAN, prefix, "--index-cache")
    assert not glob(join(index_cache_dir, "*.json"))


def test_clean_tarballs_and_packages():
    with make_temp_package_cache() as pkgs_dir:
        filter_pkgs = lambda x: [f for f in x if f.endswith((".tar.bz2", ".conda"))]
        with make_temp_env("bzip2") as prefix:
            pkgs_dir_contents = [join(pkgs_dir, d) for d in listdir(pkgs_dir)]
            pkgs_dir_dirs = [d for d in pkgs_dir_contents if isdir(d)]
            pkgs_dir_tarballs = filter_pkgs(pkgs_dir_contents)
            assert any(basename(d).startswith("bzip2-") for d in pkgs_dir_dirs)
            assert any(basename(f).startswith("bzip2-") for f in pkgs_dir_tarballs)

            # --json flag is regression test for #5451
            run_command(Commands.CLEAN, prefix, "--packages", "--yes", "--json")

            # --json flag is regression test for #5451
            run_command(Commands.CLEAN, prefix, "--tarballs", "--yes", "--json")

            pkgs_dir_contents = [join(pkgs_dir, d) for d in listdir(pkgs_dir)]
            pkgs_dir_dirs = [d for d in pkgs_dir_contents if isdir(d)]
            pkgs_dir_tarballs = filter_pkgs(pkgs_dir_contents)

            assert any(basename(d).startswith("bzip2-") for d in pkgs_dir_dirs)
            assert not any(basename(f).startswith("bzip2-") for f in pkgs_dir_tarballs)

            run_command(Commands.REMOVE, prefix, "bzip2", "--yes", "--json")

        run_command(Commands.CLEAN, prefix, "--packages", "--yes")

        pkgs_dir_contents = [join(pkgs_dir, d) for d in listdir(pkgs_dir)]
        pkgs_dir_dirs = [d for d in pkgs_dir_contents if isdir(d)]
        assert not any(basename(d).startswith("bzip2-") for d in pkgs_dir_dirs)
