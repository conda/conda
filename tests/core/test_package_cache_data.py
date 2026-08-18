# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import datetime
import json
from concurrent.futures import ThreadPoolExecutor
from os.path import abspath, basename, dirname, join
from pathlib import Path
from threading import Barrier, Event, Lock
from types import SimpleNamespace

import pytest
from pytest import MonkeyPatch

from conda import CondaError, CondaMultiError
from conda.base.constants import PACKAGE_CACHE_MAGIC_FILE, SafetyChecks
from conda.base.context import context, reset_context
from conda.common.compat import on_win
from conda.common.path import strip_pkg_extension
from conda.core import package_cache_data
from conda.core.index import Index
from conda.core.package_cache_data import (
    PackageCacheData,
    PackageCacheRecord,
    PackageRecord,
    ProgressiveFetchExtract,
)
from conda.core.path_actions import CacheUrlAction
from conda.gateways.disk.create import copy
from conda.gateways.disk.permissions import make_read_only
from conda.gateways.disk.read import (
    compute_sum,
    isfile,
    listdir,
    read_index_json,
    yield_lines,
)
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


def fresh_zlib_records():
    return (
        PackageRecord.from_objects(zlib_tar_bz2_prec),
        PackageRecord.from_objects(zlib_conda_prec),
    )


@pytest.fixture
def process_pool_as_threads(mocker):
    mocker.patch.object(package_cache_data, "EXTRACT_PROCESSES", 3)
    mocker.patch.object(
        package_cache_data,
        "ProcessPoolExecutor",
        side_effect=lambda **kwargs: ThreadPoolExecutor(kwargs["max_workers"]),
    )
    mocker.patch.object(
        context.plugin_manager,
        "get_package_extractor",
        return_value=SimpleNamespace(name="conda-package"),
    )


def test_process_extract_finishes_when_later_fetch_fails(
    mocker,
    process_pool_as_threads,
):
    extracted = Event()
    good = PackageRecord(name="good", version="1", build="0", build_number=0)
    bad = PackageRecord(name="bad", version="1", build="0", build_number=0)
    good_cache = mocker.MagicMock()
    bad_cache = mocker.MagicMock()
    good_extract = mocker.MagicMock(
        source_full_path="/tmp/good.conda",
        target_full_path="/tmp/good",
    )
    bad_extract = mocker.MagicMock(
        source_full_path="/tmp/bad.conda",
        target_full_path="/tmp/bad",
    )
    pfe = ProgressiveFetchExtract(())
    pfe.paired_actions = {
        good: (good_cache, good_extract),
        bad: (bad_cache, bad_extract),
    }
    pfe._prepared = True

    def cache_action(record, *args, **kwargs):
        if record == bad:
            assert extracted.wait(timeout=5)
            raise OSError("fetch failed")
        return record

    mocker.patch.object(package_cache_data, "do_cache_action", side_effect=cache_action)
    mocker.patch.object(
        package_cache_data,
        "extract_conda_package_archive",
        side_effect=lambda *args: extracted.set(),
    )
    mocker.patch.object(pfe, "_progress_bar", return_value=mocker.MagicMock())

    with pytest.raises(CondaMultiError, match="fetch failed"):
        pfe.execute()

    good_extract._finish_extract.assert_called_once_with()
    good_extract.cleanup.assert_called_once_with()
    bad_extract._finish_extract.assert_not_called()


def test_process_extract_gates_each_archive_on_concurrent_verifier(
    mocker,
    process_pool_as_threads,
):
    records = tuple(
        PackageRecord(name=name, version="1", build="0", build_number=0)
        for name in ("accepted", "rejected-one", "rejected-two")
    )
    barrier = Barrier(len(records))
    accepted_extracted = Event()
    lock = Lock()
    verified = set()

    def verify(name):
        barrier.wait(timeout=5)
        with lock:
            verified.add(name)
        if name.startswith("rejected"):
            assert accepted_extracted.wait(timeout=5)
            raise CondaError(name)

    mocker.patch.object(
        context.plugin_manager,
        "get_package_verifiers",
        return_value=(SimpleNamespace(name="test-verifier", verify=verify),),
    )
    extracted = []

    def extract(source_full_path, target_full_path):
        assert target_full_path == "/tmp/accepted"
        extracted.append(target_full_path)
        accepted_extracted.set()

    mocker.patch.object(
        package_cache_data,
        "extract_conda_package_archive",
        side_effect=extract,
    )
    actions = {}
    for record in records:
        action = mocker.MagicMock(
            source_full_path=f"/tmp/{record.name}.conda",
            target_full_path=f"/tmp/{record.name}",
        )
        action.verify.side_effect = lambda name=record.name: verify(name)
        actions[record] = (None, action)
    pfe = ProgressiveFetchExtract(())
    pfe.paired_actions = actions
    pfe._prepared = True
    mocker.patch.object(pfe, "_progress_bar", return_value=mocker.MagicMock())

    with pytest.raises(CondaMultiError) as exc_info:
        pfe.execute()

    assert {str(error) for error in exc_info.value.errors} == {
        "rejected-one",
        "rejected-two",
    }
    assert verified == {record.name for record in records}
    assert extracted == ["/tmp/accepted"]
    for record, (_, action) in actions.items():
        if record.name.startswith("rejected"):
            action._prepare_extract.assert_not_called()


def test_process_extract_does_not_start_after_interrupt(
    mocker,
    process_pool_as_threads,
):
    record = PackageRecord(name="package", version="1", build="0", build_number=0)
    extract_action = mocker.MagicMock(
        source_full_path="/tmp/package.conda",
        target_full_path="/tmp/package",
    )
    pfe = ProgressiveFetchExtract(())
    pfe.paired_actions = {record: (None, extract_action)}
    pfe._prepared = True

    mocker.patch.object(
        context.plugin_manager,
        "get_package_verifiers",
        return_value=(mocker.MagicMock(),),
    )
    mocker.patch.object(pfe, "_progress_bar", return_value=mocker.MagicMock())
    extract = mocker.patch.object(
        package_cache_data,
        "extract_conda_package_archive",
    )
    verifier_started = Event()
    release_verifier = Event()

    def verify():
        verifier_started.set()
        assert release_verifier.wait(timeout=5)

    extract_action.verify.side_effect = verify
    wait_calls = 0

    def interrupt_after_fetch(futures, **kwargs):
        nonlocal wait_calls
        wait_calls += 1
        if wait_calls == 1:
            return {next(iter(futures))}, set()
        assert verifier_started.wait(timeout=5)
        release_verifier.set()
        raise KeyboardInterrupt

    mocker.patch.object(package_cache_data, "wait", side_effect=interrupt_after_fetch)

    with pytest.raises(CondaMultiError):
        pfe.execute()

    extract_action.verify.assert_called_once_with()
    extract_action._prepare_extract.assert_not_called()
    extract.assert_not_called()


def test_ProgressiveFetchExtract_prefers_conda_v2_format(monkeypatch: MonkeyPatch):
    # force this to False, because otherwise tests fail when run with old conda-build
    # zlib is available in local "linux-64" subdir
    monkeypatch.setenv("CONDA_USE_ONLY_TAR_BZ2", "False")
    monkeypatch.setenv("CONDA_SUBDIR", "linux-64")
    reset_context()
    assert not context.use_only_tar_bz2
    assert context.subdir == "linux-64"

    index = Index(channels=[CONDA_PKG_REPO], prepend=False)
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


def test_download_filename_from_url_basename():
    """
    Test that the download filename is extracted from URL, not the fn attribute.

    For repodata v3, the fn attribute may contain the repodata key which
    differs from the actual filename. For example, wheel packages where
    the key uses underscores (idna-3.10-py3_none_any_0) but the actual
    filename uses hyphens (idna-3.10-py3-none-any.whl).

    See: https://github.com/conda/conda/issues/15620
    """
    # Create a package record that simulates repodata v3 format
    # where fn contains the repodata key but URL contains the actual filename
    package_url = "https://example.com/noarch/idna-3.10-py3-none-any.whl"
    package_prec = PackageRecord.from_objects(
        {
            "name": "idna",
            "version": "3.10",
            "build": "py3_none_any_0",
            "build_number": 0,
            "depends": ["python >=3.6"],
            "sha256": "b49df1a1923a9398542b6a713875dcea6d8cd80b3c5b9ca68ecf1d76bcf1ff3e",
            "size": 5718,
            "subdir": "noarch",
        },
        # This simulates repodata v3 where fn is the repodata key (differs from URL)
        fn="idna-3.10-py3_none_any_0.whl",
        url=package_url,
    )

    cache_action, extract_action = ProgressiveFetchExtract.make_actions_for_record(
        package_prec
    )

    # The cache action should use the URL basename, not fn
    assert cache_action is not None
    assert cache_action.target_package_basename == "idna-3.10-py3-none-any.whl"
    assert cache_action.target_package_basename != package_prec.fn

    assert extract_action is not None
    # Computed dynamically so the assertion holds regardless of which plugins
    # (e.g. conda-pypi registering .whl) are installed in the test environment.
    assert (
        extract_action.target_extracted_dirname
        == strip_pkg_extension(cache_action.target_package_basename)[0]
    )


def test_download_filename_strips_url_fragment():
    """
    Test that a URL fragment (e.g. #sha256=...) is stripped from the cached filename.

    PyPI URLs include a #sha256=... integrity fragment. Without stripping it, the
    cached file ends up with the fragment in its name, causing the package extractor
    plugin lookup to fail because `endswith(".whl")` no longer matches.
    """
    sha256 = "46bf16173620e97c3a9fcb75457fca6b32b40b5a97887fdeed4c6c37d3c7ba6e"
    package_url = f"https://files.pythonhosted.org/packages/noarch/idna-3.10-py3-none-any.whl#{sha256}"
    package_prec = PackageRecord.from_objects(
        {
            "name": "idna",
            "version": "3.10",
            "build": "py3_none_any_0",
            "build_number": 0,
            "depends": ["python >=3.6"],
            "sha256": sha256,
            "size": 5718,
            "subdir": "noarch",
        },
        fn="idna-3.10-py3_none_any_0.whl",
        url=package_url,
    )

    cache_action, extract_action = ProgressiveFetchExtract.make_actions_for_record(
        package_prec
    )

    assert cache_action is not None
    # The fragment must not appear in the cached filename
    assert "#" not in cache_action.target_package_basename
    assert cache_action.target_package_basename == "idna-3.10-py3-none-any.whl"
    assert cache_action.target_full_path.endswith(".whl")

    assert extract_action is not None
    assert "#" not in extract_action.source_full_path
    assert extract_action.source_full_path.endswith(".whl")


def test_download_filename_backward_compat_old_repodata():
    """
    Test backward compatibility with old repodata format.

    For traditional conda packages (repodata v1/v2), the fn attribute matches
    the URL basename. This test ensures the fix for repodata v3 doesn't break
    existing behavior.
    """
    # Create a package record that simulates traditional repodata format
    # where fn matches the URL basename
    package_url = "https://conda.anaconda.org/conda-forge/noarch/numpy-1.26.4-py312h8753938_0.conda"
    package_prec = PackageRecord.from_objects(
        {
            "name": "numpy",
            "version": "1.26.4",
            "build": "py312h8753938_0",
            "build_number": 0,
            "depends": ["python >=3.12"],
            "sha256": "abc123def456",
            "size": 12345678,
            "subdir": "noarch",
        },
        # Traditional repodata: fn matches the URL basename
        fn="numpy-1.26.4-py312h8753938_0.conda",
        url=package_url,
    )

    cache_action, extract_action = ProgressiveFetchExtract.make_actions_for_record(
        package_prec
    )

    # The cache action should use the URL basename (which matches fn)
    assert cache_action is not None
    assert cache_action.target_package_basename == "numpy-1.26.4-py312h8753938_0.conda"
    assert cache_action.target_package_basename == package_prec.fn

    # The extract action should correctly strip the .conda extension
    assert extract_action is not None
    assert extract_action.target_extracted_dirname == "numpy-1.26.4-py312h8753938_0"


def test_download_filename_backward_compat_tar_bz2():
    """
    Test backward compatibility with .tar.bz2 packages.

    Ensures the fix works correctly for the older .tar.bz2 package format.
    """
    package_url = "https://conda.anaconda.org/defaults/noarch/requests-2.32.3-py313h06a4308_0.tar.bz2"
    package_prec = PackageRecord.from_objects(
        {
            "name": "requests",
            "version": "2.32.3",
            "build": "py313h06a4308_0",
            "build_number": 0,
            "depends": ["python >=3.13"],
            "sha256": "def456abc789",
            "size": 87654,
            "subdir": "noarch",
        },
        fn="requests-2.32.3-py313h06a4308_0.tar.bz2",
        url=package_url,
    )

    cache_action, extract_action = ProgressiveFetchExtract.make_actions_for_record(
        package_prec
    )

    # The cache action should use the URL basename
    assert cache_action is not None
    assert (
        cache_action.target_package_basename
        == "requests-2.32.3-py313h06a4308_0.tar.bz2"
    )

    # The extract action should correctly strip the .tar.bz2 extension
    assert extract_action is not None
    assert extract_action.target_extracted_dirname == "requests-2.32.3-py313h06a4308_0"


@pytest.mark.skipif(
    on_win and datetime.datetime.now() < datetime.datetime(2020, 1, 30),
    reason="time bomb",
)
def test_tar_bz2_in_pkg_cache_used_instead_of_conda_pkg(tmp_pkgs_dir: Path):
    """
    Test that if a .tar.bz2 package is downloaded and extracted in a package cache, the
    complementary .conda package is not downloaded/extracted
    """
    tar_bz2_prec, conda_prec = fresh_zlib_records()

    # Cache the .tar.bz2 file in the package cache and extract it
    pfe = ProgressiveFetchExtract((tar_bz2_prec,))
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
    pfe = ProgressiveFetchExtract((tar_bz2_prec,))
    pfe.prepare()
    assert len(pfe.cache_actions) == 0
    assert len(pfe.extract_actions) == 0

    # Now ensure download/extract for the complementary .conda package uses the cache
    pfe = ProgressiveFetchExtract((conda_prec,))
    pfe.prepare()
    assert len(pfe.cache_actions) == 0
    assert len(pfe.extract_actions) == 0

    # Now check urls.txt to make sure extensions are included.
    urls_text = tuple(yield_lines(join(tmp_pkgs_dir, "urls.txt")))
    assert urls_text[0] == tar_bz2_prec.url


def test_package_verifier_does_not_reuse_complementary_format(
    tmp_pkgs_dir: Path,
    mocker,
):
    tar_bz2_prec, conda_prec = fresh_zlib_records()
    ProgressiveFetchExtract((tar_bz2_prec,)).execute()
    mocker.patch.object(
        context.plugin_manager,
        "get_package_verifiers",
        return_value=(mocker.MagicMock(),),
    )

    pfe = ProgressiveFetchExtract((conda_prec,))
    pfe.prepare()

    assert len(pfe.cache_actions) == 1
    assert pfe.cache_actions[0].target_package_basename == conda_prec.fn
    assert pfe.extract_actions[0].sha256 == conda_prec.sha256


def test_package_verifier_uses_exact_retained_format(
    tmp_pkgs_dir: Path,
    mocker,
):
    for filename in (zlib_tar_bz2_fn, zlib_conda_fn):
        cache_action = CacheUrlAction(
            f"{CONDA_PKG_REPO}/{subdir}/{filename}",
            tmp_pkgs_dir,
            filename,
        )
        cache_action.verify()
        cache_action.execute()
        cache_action.cleanup()

    verify = mocker.stub(name="verify")
    mocker.patch.object(
        context.plugin_manager,
        "get_package_verifiers",
        return_value=(SimpleNamespace(name="test-verifier", verify=verify),),
    )
    mocker.patch.object(package_cache_data, "EXTRACT_PROCESSES", 1)
    selected = PackageRecord.from_objects(
        zlib_tar_bz2_prec,
        url=f"https://mirror.example/{subdir}/{zlib_tar_bz2_fn}",
    )

    pfe = ProgressiveFetchExtract((selected,))
    pfe.prepare()

    assert not pfe.cache_actions
    assert Path(pfe.extract_actions[0].source_full_path) == Path(
        tmp_pkgs_dir,
        zlib_tar_bz2_fn,
    )

    pfe.execute()

    verify.assert_called_once()
    assert verify.call_args.args[0] is selected


@pytest.mark.parametrize("checksum", ("sha256", "md5"))
def test_package_verifier_reuses_download_checksum(
    checksum: str,
    tmp_pkgs_dir: Path,
    mocker,
):
    source = Path(CHANNEL_DIR_V1, subdir, zlib_tar_bz2_fn)
    record_data = zlib_tar_bz2_prec.dump()
    record_data["url"] = f"https://example.invalid/{subdir}/{zlib_tar_bz2_fn}"
    if checksum == "md5":
        record_data.pop("sha256")
    else:
        record_data["sha256"] = record_data["sha256"].upper()
    selected = PackageRecord(**record_data)

    def download(url, target_full_path, **kwargs):
        copy(source, target_full_path)

    download_package = mocker.patch(
        "conda.core.path_actions.download",
        side_effect=download,
    )
    compute_checksum = mocker.patch(
        "conda.core.path_actions.compute_sum",
        wraps=compute_sum,
    )

    def verify(record_or_spec, source_full_path, sha256):
        assert record_or_spec is selected
        assert sha256 == zlib_tar_bz2_prec.sha256
        if checksum == "sha256":
            compute_checksum.assert_not_called()
        else:
            compute_checksum.assert_called_once_with(source_full_path, "sha256")

    mocker.patch.object(
        context.plugin_manager,
        "get_package_verifiers",
        return_value=(SimpleNamespace(name="test-verifier", verify=verify),),
    )
    mocker.patch.object(package_cache_data, "EXTRACT_PROCESSES", 1)

    pfe = ProgressiveFetchExtract((selected,))
    pfe.execute()

    download_package.assert_called_once()
    assert download_package.call_args.kwargs[checksum] == getattr(selected, checksum)
    if checksum == "sha256":
        compute_checksum.assert_not_called()
        extract_action = pfe.extract_actions[0]
        extract_action._verified_checksum = ("sha256", selected.sha256)
        extract_action.verify()
        compute_checksum.assert_not_called()
    else:
        compute_checksum.assert_called_once_with(
            str(Path(tmp_pkgs_dir, zlib_tar_bz2_fn)),
            "sha256",
        )


def test_package_verifier_uses_exact_read_only_archive(
    tmp_pkgs_dir: Path,
    tmp_path: Path,
    mocker,
):
    read_only_pkgs_dir = tmp_path / "read-only-pkgs"
    read_only_pkgs_dir.mkdir()
    magic_file = read_only_pkgs_dir / PACKAGE_CACHE_MAGIC_FILE
    magic_file.touch()
    copy(
        join(CHANNEL_DIR_V1, subdir, zlib_tar_bz2_fn),
        read_only_pkgs_dir / zlib_tar_bz2_fn,
    )
    make_read_only(magic_file)
    mocker.patch(
        "conda.base.context.Context.pkgs_dirs",
        new_callable=mocker.PropertyMock,
        return_value=(str(tmp_pkgs_dir), str(read_only_pkgs_dir)),
    )
    PackageCacheData.clear()
    verify = mocker.stub(name="verify")
    mocker.patch.object(
        context.plugin_manager,
        "get_package_verifiers",
        return_value=(SimpleNamespace(name="test-verifier", verify=verify),),
    )
    mocker.patch.object(package_cache_data, "EXTRACT_PROCESSES", 1)

    pfe = ProgressiveFetchExtract((zlib_tar_bz2_prec,))
    pfe.prepare()

    assert len(pfe.cache_actions) == 1
    assert pfe.cache_actions[0].url == (read_only_pkgs_dir / zlib_tar_bz2_fn).as_uri()

    pfe.execute()

    verify.assert_called_once()
    assert Path(verify.call_args.args[1]).parent == tmp_pkgs_dir


def test_package_verifier_extracts_into_first_writable_cache(
    tmp_pkgs_dir: Path,
    tmp_path: Path,
    mocker,
):
    ProgressiveFetchExtract((zlib_tar_bz2_prec,)).execute()
    Path(tmp_pkgs_dir, zlib_tar_bz2_fn).unlink()
    stale_marker = Path(tmp_pkgs_dir, zlib_base_fn, "stale")
    stale_marker.touch()

    second_pkgs_dir = tmp_path / "second-pkgs"
    second_pkgs_dir.mkdir()
    Path(second_pkgs_dir, PACKAGE_CACHE_MAGIC_FILE).touch()
    copy(
        join(CHANNEL_DIR_V1, subdir, zlib_tar_bz2_fn),
        second_pkgs_dir / zlib_tar_bz2_fn,
    )
    mocker.patch(
        "conda.base.context.Context.pkgs_dirs",
        new_callable=mocker.PropertyMock,
        return_value=(str(tmp_pkgs_dir), str(second_pkgs_dir)),
    )
    PackageCacheData.clear()
    verify = mocker.stub(name="verify")
    mocker.patch.object(
        context.plugin_manager,
        "get_package_verifiers",
        return_value=(SimpleNamespace(name="test-verifier", verify=verify),),
    )
    mocker.patch.object(package_cache_data, "EXTRACT_PROCESSES", 1)

    pfe = ProgressiveFetchExtract((zlib_tar_bz2_prec,))
    pfe.prepare()

    assert len(pfe.cache_actions) == 1
    assert pfe.cache_actions[0].url == (second_pkgs_dir / zlib_tar_bz2_fn).as_uri()
    assert Path(pfe.cache_actions[0].target_full_path).parent == tmp_pkgs_dir

    pfe.execute()

    verify.assert_called_once()
    assert Path(verify.call_args.args[1]).parent == tmp_pkgs_dir
    assert not stale_marker.exists()
    entry = PackageCacheData.get_entry_to_link(zlib_tar_bz2_prec)
    assert entry is not None
    assert Path(entry.extracted_package_dir).parent == tmp_pkgs_dir


def test_package_verifier_reacquires_unhashed_explicit_package(
    tmp_pkgs_dir: Path,
    mocker,
):
    requested = Path(CHANNEL_DIR_V1, "win-64", zlib_tar_bz2_fn)
    wrong = Path(
        CHANNEL_DIR_V1,
        "linux-64",
        "zlib-1.2.11-h7b6447c_3.tar.bz2",
    )
    copy(wrong, Path(tmp_pkgs_dir, requested.name))
    verify = mocker.stub(name="verify")
    mocker.patch.object(
        context.plugin_manager,
        "get_package_verifiers",
        return_value=(SimpleNamespace(name="test-verifier", verify=verify),),
    )
    mocker.patch.object(package_cache_data, "EXTRACT_PROCESSES", 1)

    ProgressiveFetchExtract((MatchSpec(url=requested.as_uri()),)).execute()

    verify.assert_called_once()
    assert verify.call_args.args[2] == compute_sum(requested, "sha256")
    assert read_index_json(Path(tmp_pkgs_dir, zlib_base_fn))["subdir"] == "win-64"


@pytest.mark.skipif(on_win, reason="creating symlinks requires extra privileges")
def test_package_verifier_does_not_follow_cached_archive_symlink(
    tmp_pkgs_dir: Path,
    mocker,
):
    Path(tmp_pkgs_dir, zlib_tar_bz2_fn).symlink_to(
        Path(CHANNEL_DIR_V1, subdir, zlib_tar_bz2_fn)
    )
    mocker.patch.object(
        context.plugin_manager,
        "get_package_verifiers",
        return_value=(mocker.MagicMock(),),
    )

    pfe = ProgressiveFetchExtract((zlib_tar_bz2_prec,))
    pfe.prepare()

    assert len(pfe.cache_actions) == 1


def test_package_verifier_rechecks_cached_package(tmp_pkgs_dir: Path, mocker):
    pfe = ProgressiveFetchExtract((zlib_tar_bz2_prec,))
    pfe.prepare()
    pfe.execute()

    archive_path = str(Path(tmp_pkgs_dir, zlib_tar_bz2_fn))
    compute_checksum = None

    def reject(*args):
        compute_checksum.assert_called_once_with(archive_path, "sha256")
        raise CondaError("rejected")

    verify = mocker.MagicMock(side_effect=reject)
    mocker.patch.object(
        context.plugin_manager,
        "get_package_verifiers",
        return_value=(SimpleNamespace(verify=verify),),
    )
    mocker.patch.object(package_cache_data, "EXTRACT_PROCESSES", 1)
    extract = mocker.patch.object(context.plugin_manager, "extract_package")
    pfe = ProgressiveFetchExtract((zlib_tar_bz2_prec,))
    pfe.prepare()
    compute_checksum = mocker.patch(
        "conda.core.path_actions.compute_sum",
        wraps=compute_sum,
    )

    with pytest.raises(CondaMultiError, match="rejected"):
        pfe.execute()

    verify.assert_called_once()
    assert verify.call_args.args[0] is zlib_tar_bz2_prec
    assert verify.call_args.args[1] == archive_path
    assert verify.call_args.args[2] == zlib_tar_bz2_prec.sha256
    compute_checksum.assert_called_once_with(archive_path, "sha256")
    extract.assert_not_called()
    assert Path(tmp_pkgs_dir, zlib_base_fn, "info", "index.json").exists()

    Path(tmp_pkgs_dir, zlib_tar_bz2_fn).unlink()
    cache_action, extract_action = ProgressiveFetchExtract.make_actions_for_record(
        zlib_tar_bz2_prec
    )
    assert cache_action is not None
    assert extract_action is not None


def test_package_verifier_prevents_extraction_during_cache_scan(
    tmp_pkgs_dir: Path,
    mocker,
):
    copy(
        join(CHANNEL_DIR_V1, subdir, zlib_tar_bz2_fn),
        join(tmp_pkgs_dir, zlib_tar_bz2_fn),
    )
    mocker.patch.object(
        context.plugin_manager,
        "get_package_verifiers",
        return_value=(mocker.MagicMock(),),
    )

    record = PackageCacheData(tmp_pkgs_dir)._make_single_record(zlib_tar_bz2_fn)

    assert record is not None
    assert record.is_fetched
    assert not record.is_extracted


def test_package_verifier_blocks_process_extraction_when_safety_checks_disabled(
    tmp_pkgs_dir: Path,
    monkeypatch: MonkeyPatch,
    mocker,
):
    monkeypatch.setenv("CONDA_SAFETY_CHECKS", "disabled")
    reset_context()
    assert context.safety_checks == SafetyChecks.disabled
    reject = mocker.MagicMock(side_effect=CondaError("rejected"))
    mocker.patch.object(
        context.plugin_manager,
        "get_package_verifiers",
        return_value=(SimpleNamespace(verify=reject),),
    )
    mocker.patch.object(package_cache_data, "EXTRACT_PROCESSES", 2)
    extract = mocker.patch.object(
        package_cache_data,
        "extract_conda_package_archive",
    )

    with pytest.raises(CondaMultiError, match="rejected") as exc_info:
        ProgressiveFetchExtract((zlib_tar_bz2_prec,)).execute()

    assert len(exc_info.value.errors) == 1
    reject.assert_called_once()
    extract.assert_not_called()
    assert not Path(tmp_pkgs_dir, zlib_tar_bz2_fn).exists()
    assert not Path(tmp_pkgs_dir, zlib_base_fn).exists()


@pytest.mark.parametrize("same_size", (False, True))
def test_package_verifier_rejection_restores_previous_archive(
    same_size: bool,
    tmp_pkgs_dir: Path,
    mocker,
):
    target = Path(tmp_pkgs_dir, zlib_tar_bz2_fn)
    if same_size:
        target.write_bytes(b"\0" * zlib_tar_bz2_prec.size)
    else:
        copy(
            Path(
                CHANNEL_DIR_V1,
                "linux-64",
                "zlib-1.2.11-h7b6447c_3.tar.bz2",
            ),
            target,
        )
    previous_bytes = target.read_bytes()
    urls_path = Path(tmp_pkgs_dir, "urls.txt")
    previous_urls = urls_path.read_bytes() if urls_path.exists() else None
    reject = mocker.MagicMock(side_effect=CondaError("rejected"))
    mocker.patch.object(
        context.plugin_manager,
        "get_package_verifiers",
        return_value=(SimpleNamespace(verify=reject),),
    )

    with pytest.raises(CondaMultiError, match="rejected"):
        ProgressiveFetchExtract((zlib_tar_bz2_prec,)).execute()

    reject.assert_called_once()
    assert target.read_bytes() == previous_bytes
    current_urls = urls_path.read_bytes() if urls_path.exists() else None
    assert current_urls == previous_urls


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
    tar_bz2_prec, conda_prec = fresh_zlib_records()

    # Cache the .tar.bz2 file in the package cache and extract it
    pfe = ProgressiveFetchExtract((tar_bz2_prec,))
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
    pfe = ProgressiveFetchExtract((tar_bz2_prec,))
    pfe.prepare()
    assert len(pfe.cache_actions) == 0
    assert len(pfe.extract_actions) == 0

    # Now ensure download/extract for the complementary .conda package replaces the
    # extracted .tar.bz2
    pfe = ProgressiveFetchExtract((conda_prec,))
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
    assert urls_text[0] == tar_bz2_prec.url
    assert urls_text[1] == conda_prec.url


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
    tar_bz2_prec, conda_prec = fresh_zlib_records()

    # Cache the .conda file in the package cache and extract it
    pfe = ProgressiveFetchExtract((conda_prec,))
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
    pfe = ProgressiveFetchExtract((conda_prec,))
    pfe.prepare()
    assert len(pfe.cache_actions) == 0
    assert len(pfe.extract_actions) == 0

    # Now ensure download/extract for the complementary .conda package replaces the
    # extracted .tar.bz2
    pfe = ProgressiveFetchExtract((tar_bz2_prec,))
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
