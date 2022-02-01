# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import json
from os.path import abspath, basename, dirname, join

import pytest

from conda import CondaMultiError
from conda.base.constants import PACKAGE_CACHE_MAGIC_FILE
from conda.base.context import conda_tests_ctxt_mgmt_def_pol
from conda.common.io import env_vars, env_var
from conda.core.index import get_index
from conda.core.package_cache_data import PackageCacheData, ProgressiveFetchExtract
from conda.core.path_actions import CacheUrlAction
from conda.exceptions import ChecksumMismatchError
from conda.exports import url_path
from conda.gateways.disk.create import copy
from conda.gateways.disk.permissions import make_read_only
from conda.gateways.disk.read import isfile, listdir, yield_lines
from conda.models.records import PackageRecord
from conda.testing.integration import make_temp_package_cache
from conda.common.compat import on_win
import datetime

CHANNEL_DIR = abspath(join(dirname(__file__), '..', 'data', 'conda_format_repo'))
CONDA_PKG_REPO = url_path(CHANNEL_DIR)

subdir = "win-64"
zlib_base_fn = "zlib-1.2.11-h62dcd97_3"
zlib_tar_bz2_fn = "zlib-1.2.11-h62dcd97_3.tar.bz2"
zlib_tar_bz2_prec = PackageRecord.from_objects({
      "build": "h62dcd97_3",
      "build_number": 3,
      "depends": [
        "vc >=14.1,<15.0a0"
      ],
      "license": "zlib",
      "license_family": "Other",
      "md5": "a46cf10ba0eece37dffcec2d45a1f4ec",
      "name": "zlib",
      "sha256": "10363f6c023d7fb3d11fdb4cc8de59b5ad5c6affdf960210dd95a252a3fced2b",
      "size": 131285,
      "subdir": "win-64",
      "timestamp": 1542815182812,
      "version": "1.2.11"
    },
    fn=zlib_tar_bz2_fn,
    url="%s/%s/%s" % (CONDA_PKG_REPO, subdir, zlib_tar_bz2_fn),
)
zlib_conda_fn = "zlib-1.2.11-h62dcd97_3.conda"
zlib_conda_prec = PackageRecord.from_objects({
      "build": "h62dcd97_3",
      "build_number": 3,
      "depends": [
        "vc >=14.1,<15.0a0"
      ],
      "legacy_bz2_md5": "a46cf10ba0eece37dffcec2d45a1f4ec",
      "legacy_bz2_size": 131285,
      "license": "zlib",
      "license_family": "Other",
      "md5": "edad165fc3d25636d4f0a61c42873fbc",
      "name": "zlib",
      "sha256": "2fb5900c4a2ca7e0f509ebc344b3508815d7647c86cfb6721a1690365222e55a",
      "size": 112305,
      "subdir": "win-64",
      "timestamp": 1542815182812,
      "version": "1.2.11"
    },
    fn=zlib_conda_fn,
    url="%s/%s/%s" % (CONDA_PKG_REPO, subdir, zlib_conda_fn),
)

def test_ProgressiveFetchExtract_prefers_conda_v2_format():
    # force this to False, because otherwise tests fail when run with old conda-build
    with env_var('CONDA_USE_ONLY_TAR_BZ2', False, stack_callback=conda_tests_ctxt_mgmt_def_pol):
        index = get_index([CONDA_PKG_REPO], prepend=False)
        rec = next(iter(index))
        for rec in index:
            # zlib is the one package in the test index that has a .conda file record
            if rec.name == 'zlib' and rec.version == '1.2.11':
                break
        cache_action, extract_action = ProgressiveFetchExtract.make_actions_for_record(rec)
    assert cache_action.target_package_basename.endswith('.conda')
    assert extract_action.source_full_path.endswith('.conda')


@pytest.mark.skipif(on_win and datetime.datetime.now() < datetime.datetime(2020, 1, 30), reason="time bomb")
def test_tar_bz2_in_pkg_cache_used_instead_of_conda_pkg():
    """
    Test that if a .tar.bz2 package is downloaded and extracted in a package cache, the
    complementary .conda package is not downloaded/extracted
    """
    with make_temp_package_cache() as pkgs_dir:
        # Cache the .tar.bz2 file in the package cache and extract it
        pfe = ProgressiveFetchExtract((zlib_tar_bz2_prec,))
        pfe.prepare()
        assert len(pfe.cache_actions) == 1
        assert len(pfe.extract_actions) == 1
        cache_action = pfe.cache_actions[0]
        extact_action = pfe.extract_actions[0]
        assert basename(cache_action.target_full_path) == zlib_tar_bz2_fn
        assert cache_action.target_full_path == extact_action.source_full_path
        assert basename(extact_action.target_full_path) == zlib_base_fn

        # Go ahead with executing download and extract now
        pfe.execute()

        assert isfile(join(pkgs_dir, zlib_tar_bz2_fn))
        assert isfile(join(pkgs_dir, zlib_base_fn, "info", "repodata_record.json"))

        # Ensure second download/extract is a no-op
        pfe = ProgressiveFetchExtract((zlib_tar_bz2_prec,))
        pfe.prepare()
        assert len(pfe.cache_actions) == 0
        assert len(pfe.extract_actions) == 0

        # Now ensure download/extract for the complementary .conda package uses the cache
        pfe = ProgressiveFetchExtract((zlib_conda_prec,))
        pfe.prepare()
        assert len(pfe.cache_actions) == 0
        assert len(pfe.extract_actions) == 0

        # Now check urls.txt to make sure extensions are included.
        urls_text = tuple(yield_lines(join(pkgs_dir, "urls.txt")))
        assert urls_text[0] == zlib_tar_bz2_prec.url


@pytest.mark.integration
def test_tar_bz2_in_pkg_cache_doesnt_overwrite_conda_pkg():
    """
    Test that if a .tar.bz2 package is downloaded and extracted in a package cache, the
    complementary .conda package replaces it if that's what is requested.
    """
    with env_vars({'CONDA_SEPARATE_FORMAT_CACHE': True},
                  stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with make_temp_package_cache() as pkgs_dir:
            # Cache the .tar.bz2 file in the package cache and extract it
            pfe = ProgressiveFetchExtract((zlib_tar_bz2_prec,))
            pfe.prepare()
            assert len(pfe.cache_actions) == 1
            assert len(pfe.extract_actions) == 1
            cache_action = pfe.cache_actions[0]
            extact_action = pfe.extract_actions[0]
            assert basename(cache_action.target_full_path) == zlib_tar_bz2_fn
            assert cache_action.target_full_path == extact_action.source_full_path
            assert basename(extact_action.target_full_path) == zlib_base_fn

            # Go ahead with executing download and extract now
            pfe.execute()

            assert isfile(join(pkgs_dir, zlib_tar_bz2_fn))
            assert isfile(join(pkgs_dir, zlib_base_fn, "info", "repodata_record.json"))

            # Ensure second download/extract is a no-op
            pfe = ProgressiveFetchExtract((zlib_tar_bz2_prec,))
            pfe.prepare()
            assert len(pfe.cache_actions) == 0
            assert len(pfe.extract_actions) == 0

            # Now ensure download/extract for the complementary .conda package replaces the
            # extracted .tar.bz2
            pfe = ProgressiveFetchExtract((zlib_conda_prec,))
            pfe.prepare()
            assert len(pfe.cache_actions) == 1
            assert len(pfe.extract_actions) == 1
            cache_action = pfe.cache_actions[0]
            extact_action = pfe.extract_actions[0]
            assert basename(cache_action.target_full_path) == zlib_conda_fn
            assert cache_action.target_full_path == extact_action.source_full_path
            assert basename(extact_action.target_full_path) == zlib_base_fn

            pfe.execute()

            with open(join(pkgs_dir, zlib_base_fn, "info", "repodata_record.json")) as fh:
                repodata_record = json.load(fh)
            assert repodata_record["fn"] == zlib_conda_fn

            # Now check urls.txt to make sure extensions are included.
            urls_text = tuple(yield_lines(join(pkgs_dir, "urls.txt")))
            assert urls_text[0] == zlib_tar_bz2_prec.url
            assert urls_text[1] == zlib_conda_prec.url


@pytest.mark.integration
def test_conda_pkg_in_pkg_cache_doesnt_overwrite_tar_bz2():
    """
    Test that if a .conda package is downloaded and extracted in a package cache, the
    complementary .tar.bz2 package replaces it if that's what is requested.
    """
    with env_vars({'CONDA_SEPARATE_FORMAT_CACHE': True},
                  stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with make_temp_package_cache() as pkgs_dir:
            # Cache the .conda file in the package cache and extract it
            pfe = ProgressiveFetchExtract((zlib_conda_prec,))
            pfe.prepare()
            assert len(pfe.cache_actions) == 1
            assert len(pfe.extract_actions) == 1
            cache_action = pfe.cache_actions[0]
            extact_action = pfe.extract_actions[0]
            assert basename(cache_action.target_full_path) == zlib_conda_fn
            assert cache_action.target_full_path == extact_action.source_full_path
            assert basename(extact_action.target_full_path) == zlib_base_fn

            # Go ahead with executing download and extract now
            pfe.execute()

            assert isfile(join(pkgs_dir, zlib_conda_fn))
            assert isfile(join(pkgs_dir, zlib_base_fn, "info", "repodata_record.json"))

            # Ensure second download/extract is a no-op
            pfe = ProgressiveFetchExtract((zlib_conda_prec,))
            pfe.prepare()
            assert len(pfe.cache_actions) == 0
            assert len(pfe.extract_actions) == 0

            # Now ensure download/extract for the complementary .conda package replaces the
            # extracted .tar.bz2
            pfe = ProgressiveFetchExtract((zlib_tar_bz2_prec,))
            pfe.prepare()
            assert len(pfe.cache_actions) == 1
            assert len(pfe.extract_actions) == 1
            cache_action = pfe.cache_actions[0]
            extact_action = pfe.extract_actions[0]
            assert basename(cache_action.target_full_path) == zlib_tar_bz2_fn
            assert cache_action.target_full_path == extact_action.source_full_path
            assert basename(extact_action.target_full_path) == zlib_base_fn

            pfe.execute()

            with open(join(pkgs_dir, zlib_base_fn, "info", "repodata_record.json")) as fh:
                repodata_record = json.load(fh)
            assert repodata_record["fn"] == zlib_tar_bz2_fn


# TODO: need to ask Kale about this one.  I think we don't trigger any sha256 stuff because we go through
#     the local logic, which only uses md5.  Should this be using sha256, too?  I thought we agreed to
#     keep sha256 for only doing the download verification from internet sources.
# def test_bad_sha256_enforcement():
#     with make_temp_package_cache() as pkgs_dir:
#         zlib_conda_prec_bad = PackageRecord.from_objects(zlib_conda_prec, sha256="0" * 10)
#         assert zlib_conda_prec_bad.sha256 == "0" * 10
#         pfe = ProgressiveFetchExtract((zlib_conda_prec_bad,))
#         pfe.prepare()
#         assert len(pfe.cache_actions) == 1
#         assert len(pfe.extract_actions) == 1
#         cache_action = pfe.cache_actions[0]
#         extact_action = pfe.extract_actions[0]
#         assert basename(cache_action.target_full_path) == zlib_conda_fn
#         assert cache_action.target_full_path == extact_action.source_full_path
#         assert basename(extact_action.target_full_path) == zlib_base_fn
#         with pytest.raises(CondaMultiError) as exc:
#             pfe.execute()
#         assert len(exc.value.errors) == 1
#         assert isinstance(exc.value.errors[0], ChecksumMismatchError)
#         assert "expected sha256: 0000000000" in repr(exc.value.errors[0])

@pytest.mark.skipif(on_win and datetime.datetime.now() < datetime.datetime(2020, 1, 30), reason="time bomb")
def test_tar_bz2_in_cache_not_extracted():
    """
    Test that if a .tar.bz2 exists in the package cache (not extracted), and the complementary
    .conda package is requested, the .tar.bz2 package in the cache is used by default.
    """
    with make_temp_package_cache() as pkgs_dir:
        copy(join(CHANNEL_DIR, subdir, zlib_tar_bz2_fn), join(pkgs_dir, zlib_tar_bz2_fn))
        pfe = ProgressiveFetchExtract((zlib_tar_bz2_prec,))
        pfe.prepare()
        assert len(pfe.cache_actions) == 1
        assert len(pfe.extract_actions) == 1

        pfe.execute()

        pkgs_dir_files = listdir(pkgs_dir)
        assert zlib_base_fn in pkgs_dir_files
        assert zlib_tar_bz2_fn in pkgs_dir_files

        # Now ensure download/extract for the complementary .conda package uses the
        # extracted .tar.bz2
        pfe = ProgressiveFetchExtract((zlib_conda_prec,))
        pfe.prepare()
        assert len(pfe.cache_actions) == 0
        assert len(pfe.extract_actions) == 0

@pytest.mark.skipif(on_win and datetime.datetime.now() < datetime.datetime(2020, 1, 30), reason="time bomb")
def test_instantiating_package_cache_when_both_tar_bz2_and_conda_exist():
    """
    If both .tar.bz2 and .conda packages exist in a writable package cache, but neither is
    unpacked, the .conda package should be preferred and unpacked in place.
    """
    with make_temp_package_cache() as pkgs_dir:
        # copy .tar.bz2 to package cache
        cache_action = CacheUrlAction(
            "%s/%s/%s" % (CONDA_PKG_REPO, subdir, zlib_tar_bz2_fn),
            pkgs_dir,
            zlib_tar_bz2_fn,
        )
        cache_action.verify()
        cache_action.execute()
        cache_action.cleanup()

        # copy .conda to package cache
        cache_action = CacheUrlAction(
            "%s/%s/%s" % (CONDA_PKG_REPO, subdir, zlib_conda_fn),
            pkgs_dir,
            zlib_conda_fn,
        )
        cache_action.verify()
        cache_action.execute()
        cache_action.cleanup()

        PackageCacheData._cache_.clear()
        pcd = PackageCacheData(pkgs_dir)
        pcrecs = tuple(pcd.iter_records())
        assert len(pcrecs) == 1
        pcrec = pcrecs[0]

        # ensure the package was actually extracted by presence of repodata_record.json
        with open(join(pkgs_dir, zlib_base_fn, "info", "repodata_record.json")) as fh:
            repodata_record = json.load(fh)

        assert pcrec.fn == zlib_conda_fn == repodata_record["fn"]
        assert pcrec.md5 == repodata_record["md5"]

        pkgs_dir_files = listdir(pkgs_dir)
        assert zlib_base_fn in pkgs_dir_files
        assert zlib_tar_bz2_fn in pkgs_dir_files
        assert zlib_conda_fn in pkgs_dir_files


def test_instantiating_package_cache_when_both_tar_bz2_and_conda_exist_read_only():
    """
    If both .tar.bz2 and .conda packages exist in a read-only package cache, but neither is
    unpacked, the .conda package should be preferred and pcrec loaded from that package.
    """
    with make_temp_package_cache() as pkgs_dir:
        # instantiate to create magic file
        PackageCacheData(pkgs_dir)

        # copy .tar.bz2 to package cache
        cache_action = CacheUrlAction(
            "%s/%s/%s" % (CONDA_PKG_REPO, subdir, zlib_tar_bz2_fn),
            pkgs_dir,
            zlib_tar_bz2_fn,
        )
        cache_action.verify()
        cache_action.execute()
        cache_action.cleanup()

        # copy .conda to package cache
        cache_action = CacheUrlAction(
            "%s/%s/%s" % (CONDA_PKG_REPO, subdir, zlib_conda_fn),
            pkgs_dir,
            zlib_conda_fn,
        )
        cache_action.verify()
        cache_action.execute()
        cache_action.cleanup()

        make_read_only(join(pkgs_dir, PACKAGE_CACHE_MAGIC_FILE))
        PackageCacheData._cache_.clear()

        pcd = PackageCacheData(pkgs_dir)
        pcrecs = tuple(pcd.iter_records())
        assert len(pcrecs) == 1
        pcrec = pcrecs[0]

        # no repodata_record.json file should be created
        assert not isfile(join(pkgs_dir, zlib_base_fn, "info", "repodata_record.json"))

        assert pcrec.fn == zlib_conda_fn
        assert pcrec.md5 == "edad165fc3d25636d4f0a61c42873fbc"
        assert pcrec.size == 112305

        pkgs_dir_files = listdir(pkgs_dir)
        assert zlib_base_fn not in pkgs_dir_files
        assert zlib_tar_bz2_fn in pkgs_dir_files
        assert zlib_conda_fn in pkgs_dir_files
