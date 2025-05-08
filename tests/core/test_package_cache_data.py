# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import datetime
import json
from os.path import abspath, basename, dirname, join
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from conda import CondaError, CondaMultiError
from conda.base.constants import PACKAGE_CACHE_MAGIC_FILE
from conda.base.context import context, reset_context
from conda.common.compat import on_win
from conda.core import package_cache_data
from conda.core.index import get_index
from conda.core.package_cache_data import (
    PackageCacheData,
    PackageCacheRecord,
    PackageRecord,
    ProgressiveFetchExtract,
)
from conda.core.path_actions import CacheUrlAction
from conda.gateways.disk.create import copy
from conda.gateways.disk.permissions import make_read_only
from conda.gateways.disk.read import isfile, listdir, yield_lines
from conda.models.match_spec import MatchSpec
from conda.testing.helpers import CHANNEL_DIR_V1
from conda.utils import url_path

assert CHANNEL_DIR_V1 == abspath(
    join(dirname(__file__), "..", "data", "conda_format_repo")
)
CONDA_PKG_REPO = url_path(CHANNEL_DIR_V1)

subdir = "win-64"
zlib_base_fn = "zlib-1.2.11-h62dcd97_3"
zlib_tar_bz2_fn = "zlib-1.2.11-h62dcd97_3.tar.bz2"
zlib_tar_bz2_prec = PackageRecord.from_objects(
    {
        "build": "h62dcd97_3",
        "build_number": 3,
        "depends": ["vc >=14.1,<15.0a0"],
        "license": "zlib",
        "license_family": "Other",
        "md5": "a46cf10ba0eece37dffcec2d45a1f4ec",
        "name": "zlib",
        "sha256": "10363f6c023d7fb3d11fdb4cc8de59b5ad5c6affdf960210dd95a252a3fced2b",
        "size": 131285,
        "subdir": "win-64",
        "timestamp": 1542815182812,
        "version": "1.2.11",
    },
    fn=zlib_tar_bz2_fn,
    url=f"{CONDA_PKG_REPO}/{subdir}/{zlib_tar_bz2_fn}",
)
zlib_conda_fn = "zlib-1.2.11-h62dcd97_3.conda"
zlib_conda_prec = PackageRecord.from_objects(
    {
        "build": "h62dcd97_3",
        "build_number": 3,
        "depends": ["vc >=14.1,<15.0a0"],
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
        "version": "1.2.11",
    },
    fn=zlib_conda_fn,
    url=f"{CONDA_PKG_REPO}/{subdir}/{zlib_conda_fn}",
)


def test_ProgressiveFetchExtract_prefers_conda_v2_format(monkeypatch: MonkeyPatch):
    # force this to False, because otherwise tests fail when run with old conda-build
    # zlib is available in local "linux-64" subdir
    monkeypatch.setenv("CONDA_USE_ONLY_TAR_BZ2", "False")
    monkeypatch.setenv("CONDA_SUBDIR", "linux-64")
    reset_context()
    assert not context.use_only_tar_bz2
    assert context.subdir == "linux-64"

    index = get_index([CONDA_PKG_REPO], prepend=False)
    rec = next(iter(index))
    for rec in index:
        # zlib is the one package in the test index that has a .conda file record
        if rec.name == "zlib" and rec.version == "1.2.11":
            break
    cache_action, extract_action = ProgressiveFetchExtract.make_actions_for_record(rec)

    assert cache_action
    assert cache_action.target_package_basename.endswith(".conda")
    assert extract_action
    assert extract_action.source_full_path.endswith(".conda")


@pytest.mark.skipif(
    on_win and datetime.datetime.now() < datetime.datetime(2020, 1, 30),
    reason="time bomb",
)
def test_tar_bz2_in_pkg_cache_used_instead_of_conda_pkg(tmp_pkgs_dir: Path):
    """
    Test that if a .tar.bz2 package is downloaded and extracted in a package cache, the
    complementary .conda package is not downloaded/extracted
    """
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

    assert isfile(join(tmp_pkgs_dir, zlib_tar_bz2_fn))
    assert isfile(join(tmp_pkgs_dir, zlib_base_fn, "info", "repodata_record.json"))

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
    urls_text = tuple(yield_lines(join(tmp_pkgs_dir, "urls.txt")))
    assert urls_text[0] == zlib_tar_bz2_prec.url


@pytest.mark.integration
def test_tar_bz2_in_pkg_cache_doesnt_overwrite_conda_pkg(
    monkeypatch: MonkeyPatch, tmp_pkgs_dir: Path
):
    """
    Test that if a .tar.bz2 package is downloaded and extracted in a package cache, the
    complementary .conda package replaces it if that's what is requested.
    """
    monkeypatch.setenv("CONDA_SEPARATE_FORMAT_CACHE", "True")
    reset_context()
    assert context.separate_format_cache

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

    assert isfile(join(tmp_pkgs_dir, zlib_tar_bz2_fn))
    assert isfile(join(tmp_pkgs_dir, zlib_base_fn, "info", "repodata_record.json"))

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

    with open(join(tmp_pkgs_dir, zlib_base_fn, "info", "repodata_record.json")) as fh:
        repodata_record = json.load(fh)
    assert repodata_record["fn"] == zlib_conda_fn

    # Now check urls.txt to make sure extensions are included.
    urls_text = tuple(yield_lines(join(tmp_pkgs_dir, "urls.txt")))
    assert urls_text[0] == zlib_tar_bz2_prec.url
    assert urls_text[1] == zlib_conda_prec.url


@pytest.mark.integration
def test_conda_pkg_in_pkg_cache_doesnt_overwrite_tar_bz2(
    monkeypatch: MonkeyPatch, tmp_pkgs_dir: Path
):
    """
    Test that if a .conda package is downloaded and extracted in a package cache, the
    complementary .tar.bz2 package replaces it if that's what is requested.
    """
    monkeypatch.setenv("CONDA_SEPARATE_FORMAT_CACHE", "True")
    reset_context()
    assert context.separate_format_cache

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

    assert isfile(join(tmp_pkgs_dir, zlib_conda_fn))
    assert isfile(join(tmp_pkgs_dir, zlib_base_fn, "info", "repodata_record.json"))

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

    with open(join(tmp_pkgs_dir, zlib_base_fn, "info", "repodata_record.json")) as fh:
        repodata_record = json.load(fh)
    assert repodata_record["fn"] == zlib_tar_bz2_fn


# TODO: need to ask Kale about this one.  I think we don't trigger any sha256 stuff because we go through
#     the local logic, which only uses md5.  Should this be using sha256, too?  I thought we agreed to
#     keep sha256 for only doing the download verification from internet sources.
# def test_bad_sha256_enforcement(tmp_pkgs_dir: Path):
#     zlib_conda_prec_bad = PackageRecord.from_objects(zlib_conda_prec, sha256="0" * 10)
#     assert zlib_conda_prec_bad.sha256 == "0" * 10
#     pfe = ProgressiveFetchExtract((zlib_conda_prec_bad,))
#     pfe.prepare()
#     assert len(pfe.cache_actions) == 1
#     assert len(pfe.extract_actions) == 1
#     cache_action = pfe.cache_actions[0]
#     extact_action = pfe.extract_actions[0]
#     assert basename(cache_action.target_full_path) == zlib_conda_fn
#     assert cache_action.target_full_path == extact_action.source_full_path
#     assert basename(extact_action.target_full_path) == zlib_base_fn
#     with pytest.raises(CondaMultiError) as exc:
#         pfe.execute()
#     assert len(exc.value.errors) == 1
#     assert isinstance(exc.value.errors[0], ChecksumMismatchError)
#     assert "expected sha256: 0000000000" in repr(exc.value.errors[0])


@pytest.mark.skipif(
    on_win and datetime.datetime.now() < datetime.datetime(2020, 1, 30),
    reason="time bomb",
)
def test_tar_bz2_in_cache_not_extracted(tmp_pkgs_dir: Path):
    """
    Test that if a .tar.bz2 exists in the package cache (not extracted), and the complementary
    .conda package is requested, the .tar.bz2 package in the cache is used by default.
    """
    copy(
        join(CHANNEL_DIR_V1, subdir, zlib_tar_bz2_fn),
        join(tmp_pkgs_dir, zlib_tar_bz2_fn),
    )
    pfe = ProgressiveFetchExtract((zlib_tar_bz2_prec,))
    pfe.prepare()
    assert len(pfe.cache_actions) == 1
    assert len(pfe.extract_actions) == 1

    pfe.execute()

    pkgs_dir_files = listdir(tmp_pkgs_dir)
    assert zlib_base_fn in pkgs_dir_files
    assert zlib_tar_bz2_fn in pkgs_dir_files

    # Now ensure download/extract for the complementary .conda package uses the
    # extracted .tar.bz2
    pfe = ProgressiveFetchExtract((zlib_conda_prec,))
    pfe.prepare()
    assert len(pfe.cache_actions) == 0
    assert len(pfe.extract_actions) == 0


@pytest.mark.skipif(
    on_win and datetime.datetime.now() < datetime.datetime(2020, 1, 30),
    reason="time bomb",
)
def test_instantiating_package_cache_when_both_tar_bz2_and_conda_exist(
    tmp_pkgs_dir: Path,
):
    """
    If both .tar.bz2 and .conda packages exist in a writable package cache, but neither is
    unpacked, the .conda package should be preferred and unpacked in place.
    """
    # copy .tar.bz2 to package cache
    cache_action = CacheUrlAction(
        f"{CONDA_PKG_REPO}/{subdir}/{zlib_tar_bz2_fn}",
        tmp_pkgs_dir,
        zlib_tar_bz2_fn,
    )
    cache_action.verify()
    cache_action.execute()
    cache_action.cleanup()

    # copy .conda to package cache
    cache_action = CacheUrlAction(
        f"{CONDA_PKG_REPO}/{subdir}/{zlib_conda_fn}",
        tmp_pkgs_dir,
        zlib_conda_fn,
    )
    cache_action.verify()
    cache_action.execute()
    cache_action.cleanup()

    PackageCacheData._cache_.clear()
    pcd = PackageCacheData(tmp_pkgs_dir)
    pcrecs = tuple(pcd.iter_records())
    assert len(pcrecs) == 1
    pcrec = pcrecs[0]

    # ensure the package was actually extracted by presence of repodata_record.json
    with open(join(tmp_pkgs_dir, zlib_base_fn, "info", "repodata_record.json")) as fh:
        repodata_record = json.load(fh)

    assert pcrec.fn == zlib_conda_fn == repodata_record["fn"]
    assert pcrec.md5 == repodata_record["md5"]

    pkgs_dir_files = listdir(tmp_pkgs_dir)
    assert zlib_base_fn in pkgs_dir_files
    assert zlib_tar_bz2_fn in pkgs_dir_files
    assert zlib_conda_fn in pkgs_dir_files


def test_instantiating_package_cache_when_both_tar_bz2_and_conda_exist_read_only(
    tmp_pkgs_dir: Path,
):
    """
    If both .tar.bz2 and .conda packages exist in a read-only package cache, but neither is
    unpacked, the .conda package should be preferred and pcrec loaded from that package.
    """
    # instantiate to create magic file
    PackageCacheData(tmp_pkgs_dir)

    # copy .tar.bz2 to package cache
    cache_action = CacheUrlAction(
        f"{CONDA_PKG_REPO}/{subdir}/{zlib_tar_bz2_fn}",
        tmp_pkgs_dir,
        zlib_tar_bz2_fn,
    )
    cache_action.verify()
    cache_action.execute()
    cache_action.cleanup()

    # copy .conda to package cache
    cache_action = CacheUrlAction(
        f"{CONDA_PKG_REPO}/{subdir}/{zlib_conda_fn}",
        tmp_pkgs_dir,
        zlib_conda_fn,
    )
    cache_action.verify()
    cache_action.execute()
    cache_action.cleanup()

    make_read_only(join(tmp_pkgs_dir, PACKAGE_CACHE_MAGIC_FILE))
    PackageCacheData._cache_.clear()

    pcd = PackageCacheData(tmp_pkgs_dir)
    pcrecs = tuple(pcd.iter_records())
    assert len(pcrecs) == 1
    pcrec = pcrecs[0]

    # no repodata_record.json file should be created
    assert not isfile(join(tmp_pkgs_dir, zlib_base_fn, "info", "repodata_record.json"))

    assert pcrec.fn == zlib_conda_fn
    assert pcrec.md5 == "edad165fc3d25636d4f0a61c42873fbc"
    assert pcrec.size == 112305

    pkgs_dir_files = listdir(tmp_pkgs_dir)
    assert zlib_base_fn not in pkgs_dir_files
    assert zlib_tar_bz2_fn in pkgs_dir_files
    assert zlib_conda_fn in pkgs_dir_files


def test_instantiating_package_cache_when_unpacked_conda_exist(tmp_pkgs_dir: Path):
    """
    If .conda package exist in a writable package cache, but is unpacked,
    the .conda package should be unpacked in place.
    """
    # copy .conda to package cache
    pkg_url = f"{CONDA_PKG_REPO}/{subdir}/{zlib_conda_fn}"
    cache_action = CacheUrlAction(
        pkg_url,
        tmp_pkgs_dir,
        zlib_conda_fn,
    )
    cache_action.verify()
    cache_action.execute()
    cache_action.cleanup()

    PackageCacheData._cache_.clear()
    pcd = PackageCacheData(tmp_pkgs_dir)
    pcrecs = tuple(pcd.iter_records())
    assert len(pcrecs) == 1
    pcrec = pcrecs[0]

    # ensure the package was actually extracted by presence of repodata_record.json
    with open(join(tmp_pkgs_dir, zlib_base_fn, "info", "repodata_record.json")) as fh:
        repodata_record = json.load(fh)

    assert pcrec.fn == zlib_conda_fn == repodata_record["fn"]
    assert pcrec.md5 == repodata_record["md5"]

    pkgs_dir_files = listdir(tmp_pkgs_dir)
    assert zlib_base_fn in pkgs_dir_files
    assert zlib_conda_fn in pkgs_dir_files

    # PackageRecord should have valid url otherwise query won't find a match when MatchSpec is an explicit url
    assert pcrec.url == pkg_url
    pcrec_match = tuple(pcd.query(MatchSpec(pkg_url)))
    assert len(pcrec_match) == 1


def test_cover_reverse():
    class f:
        def result(self):
            raise Exception()

    class action:
        def reverse(self):
            pass

    class progress:
        def close(self):
            pass

        def finish(self):
            pass

    def not_cancelled():
        return True

    exceptions = []

    package_cache_data.done_callback(f(), (action(),), progress(), exceptions)  # type: ignore
    package_cache_data.do_cache_action("dummy", None, None, cancelled=not_cancelled)
    package_cache_data.do_extract_action("dummy", None, None)


def test_cover_get_entry_to_link(tmp_pkgs_dir: Path):
    with pytest.raises(CondaError):
        PackageCacheData.get_entry_to_link(
            PackageRecord(name="does-not-exist", version="4", build_number=0, build="")
        )

    exists_record = PackageRecord(
        name="brotlipy", version="0.7.0", build_number=1003, build="py38h9ed2024_1003"
    )

    exists = PackageCacheRecord(
        _hash=4599667980631885143,
        name="brotlipy",
        version="0.7.0",
        build="py38h9ed2024_1003",
        build_number=1003,
        subdir="osx-64",
        fn="brotlipy-0.7.0-py38h9ed2024_1003.conda",
        url="https://repo.anaconda.com/pkgs/main/osx-64/brotlipy-0.7.0-py38h9ed2024_1003.conda",
        sha256="8cd905ec746456419b0ba8b58003e35860f4c1205fc2be810de06002ba257418",
        arch="x86_64",
        platform="darwin",
        depends=("cffi >=1.0.0", "python >=3.8,<3.9.0a0"),
        constrains=(),
        track_features=(),
        features=(),
        license="MIT",
        license_family="MIT",
        timestamp=1605539545.169,
        size=339408,
        package_tarball_full_path="/pkgs/brotlipy-0.7.0-py38h9ed2024_1003.conda",
        extracted_package_dir="/pkgs/brotlipy-0.7.0-py38h9ed2024_1003",
        md5="41b0bc0721aecf75336a098f4d5314b8",
    )

    first_writable = PackageCacheData(tmp_pkgs_dir)
    assert first_writable._package_cache_records is not None
    first_writable._package_cache_records[exists] = exists
    PackageCacheData.get_entry_to_link(exists_record)
    del first_writable._package_cache_records[exists]


def test_cover_fetch_not_exists():
    """
    Conda collects all exceptions raised during ProgressiveFetchExtract into a
    CondaMultiError. TODO: Is this necessary?
    """
    with pytest.raises(CondaMultiError):
        ProgressiveFetchExtract(
            [
                MatchSpec(
                    url="http://localhost:8080/conda-test/fakepackage-1.2.12-testing_3.conda"
                ),
                MatchSpec(
                    url="http://localhost:8080/conda-test/phonypackage-0.0.1-testing_3.conda"
                ),
            ]
        ).execute()


def test_cover_extract_bad_package(tmp_path):
    filename = "fakepackage-1.2.12-testing_3.conda"
    fullpath = tmp_path / filename
    with open(fullpath, "w") as archive:
        archive.write("")
    PackageCacheData.first_writable()._make_single_record(str(fullpath))
