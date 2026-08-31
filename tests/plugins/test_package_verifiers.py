# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from conda import CondaError, CondaMultiError, plugins
from conda.base.context import context, reset_context
from conda.common.path import strip_pkg_extension
from conda.common.url import path_to_url
from conda.core.package_cache_data import do_extract_action
from conda.core.path_actions import (
    CreatePrefixRecordAction,
    ExtractPackageAction,
    LinkPathAction,
    UnlinkPathAction,
)
from conda.exceptions import (
    ChecksumMismatchError,
    CondaVerificationError,
    PluginError,
)
from conda.gateways.disk.read import compute_sum, read_index_json_from_tarball
from conda.misc import get_package_records_from_explicit
from conda.models.match_spec import MatchSpec
from conda.models.records import PackageRecord
from conda.plugins import package_extractors, solvers
from conda.plugins.types import CondaPackageVerifier

from .. import TEST_RECIPES_CHANNEL

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from conda.plugins.manager import CondaPluginManager
    from conda.testing.fixtures import CondaCLIFixture


@pytest.fixture
def package_path() -> Path:
    return TEST_RECIPES_CHANNEL / "noarch" / "small-executable-1.0-0.conda"


@pytest.fixture
def package_record(package_path: Path) -> PackageRecord:
    return PackageRecord.from_objects(
        read_index_json_from_tarball(str(package_path)),
        fn=package_path.name,
        url=path_to_url(str(package_path)),
    )


def register_verifier(
    plugin_manager: CondaPluginManager,
    verifier: CondaPackageVerifier,
) -> None:
    class VerifierPlugin:
        @plugins.hookimpl
        def conda_package_verifiers(self):
            yield verifier

    plugin_manager.register(VerifierPlugin())


@pytest.mark.parametrize("explicit", (False, True))
def test_package_verifier_runs_before_extraction(
    explicit: bool,
    package_path: Path,
    package_record: PackageRecord,
    plugin_manager: CondaPluginManager,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    events = []

    def verify(record_or_spec, source_full_path, sha256):
        assert record_or_spec == expected_record_or_spec
        staged_archive = Path(source_full_path)
        assert staged_archive.name == package_path.name
        assert staged_archive.parent.parent == tmp_path
        assert staged_archive.parent.name.startswith(".conda-verify-")
        assert sha256 == compute_sum(package_path, "sha256")
        events.append("verify")

    register_verifier(
        plugin_manager,
        CondaPackageVerifier(name="test-verifier", verify=verify),
    )
    plugin_manager.load_plugins(*package_extractors.plugins)
    expected_record_or_spec = (
        MatchSpec(url=path_to_url(str(package_path))) if explicit else package_record
    )
    action = ExtractPackageAction(
        source_full_path=str(package_path),
        target_pkgs_dir=tmp_path,
        target_extracted_dirname="extracted",
        record_or_spec=expected_record_or_spec,
        sha256=None,
        size=None,
        md5=None,
    )
    extract_package = plugin_manager.extract_package

    def extract(*args):
        events.append("extract")
        extract_package(*args)

    mocker.patch.object(plugin_manager, "extract_package", side_effect=extract)

    do_extract_action(package_record, action, mocker.MagicMock())

    assert events == ["verify", "extract"]


def test_package_verifier_failure_prevents_extraction(
    package_path: Path,
    package_record: PackageRecord,
    plugin_manager: CondaPluginManager,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    error = CondaVerificationError("rejected")

    def reject(*args):
        raise error

    register_verifier(
        plugin_manager,
        CondaPackageVerifier(name="test-verifier", verify=reject),
    )
    extract = mocker.patch.object(plugin_manager, "extract_package")
    action = ExtractPackageAction(
        source_full_path=str(package_path),
        target_pkgs_dir=tmp_path,
        target_extracted_dirname="extracted",
        record_or_spec=package_record,
        sha256=None,
        size=None,
        md5=None,
    )

    with pytest.raises(CondaVerificationError, match="rejected") as exc_info:
        do_extract_action(package_record, action, mocker.MagicMock())

    assert exc_info.value is error
    extract.assert_not_called()


def test_package_verifier_unexpected_error_names_plugin(
    package_path: Path,
    package_record: PackageRecord,
    plugin_manager: CondaPluginManager,
    tmp_path: Path,
) -> None:
    def fail(*args):
        raise ValueError("broken verifier")

    register_verifier(
        plugin_manager,
        CondaPackageVerifier(name="test-verifier", verify=fail),
    )
    action = ExtractPackageAction(
        source_full_path=str(package_path),
        target_pkgs_dir=tmp_path,
        target_extracted_dirname="extracted",
        record_or_spec=package_record,
        sha256=None,
        size=None,
        md5=None,
    )

    with pytest.raises(PluginError, match="test-verifier.*broken verifier") as exc_info:
        action.verify()

    assert isinstance(exc_info.value.__cause__, ValueError)


def test_explicit_package_runs_verifier(
    package_path: Path,
    plugin_manager_with_reporter_backends: CondaPluginManager,
    mocker: MockerFixture,
    tmp_pkgs_dir: Path,
) -> None:
    plugin_manager = plugin_manager_with_reporter_backends
    verify = mocker.stub(name="verify")
    register_verifier(
        plugin_manager,
        CondaPackageVerifier(name="test-verifier", verify=verify),
    )
    plugin_manager.load_plugins(*package_extractors.plugins)

    records = tuple(get_package_records_from_explicit([package_path.as_uri()]))

    assert len(records) == 1
    verify.assert_called_once()
    record_or_spec, archive_path, sha256 = verify.call_args.args
    assert isinstance(record_or_spec, MatchSpec)
    assert Path(archive_path).name == package_path.name
    assert Path(archive_path).parent.parent == tmp_pkgs_dir
    assert sha256 == compute_sum(package_path, "sha256")
    assert (tmp_pkgs_dir / "urls.txt").read_text().splitlines() == [
        package_path.as_uri()
    ]


def test_explicit_install_rejection_prevents_prefix_changes(
    package_path: Path,
    plugin_manager_with_reporter_backends: CondaPluginManager,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
    tmp_path: Path,
    tmp_pkgs_dir: Path,
) -> None:
    plugin_manager = plugin_manager_with_reporter_backends
    reject = mocker.MagicMock(side_effect=CondaError("rejected"))
    register_verifier(
        plugin_manager,
        CondaPackageVerifier(name="test-verifier", verify=reject),
    )
    plugin_manager.load_plugins(*package_extractors.plugins)
    prefix = tmp_path / "prefix"

    _, _, exc = conda_cli(
        "create",
        f"--prefix={prefix}",
        package_path,
        "--yes",
        raises=CondaMultiError,
    )

    assert exc.match("rejected")
    reject.assert_called_once()
    assert not (prefix / "conda-meta").exists()


@pytest.mark.integration
@pytest.mark.parametrize("download_only", (False, True))
def test_solved_install_rejection_prevents_prefix_changes(
    download_only: bool,
    parametrized_solver_fixture: str,
    package_record: PackageRecord,
    plugin_manager_with_reporter_backends: CondaPluginManager,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
    tmp_path: Path,
    tmp_pkgs_dir: Path,
) -> None:
    plugin_manager = plugin_manager_with_reporter_backends
    plugin_manager.load_plugins(solvers)
    if parametrized_solver_fixture == "libmamba":
        from conda_libmamba_solver import plugin as libmamba_solver_plugin

        plugin_manager.load_plugins(libmamba_solver_plugin)
    reject = mocker.MagicMock(side_effect=CondaVerificationError("rejected"))
    register_verifier(
        plugin_manager,
        CondaPackageVerifier(name="test-verifier", verify=reject),
    )
    plugin_manager.load_plugins(*package_extractors.plugins)
    prefix = tmp_path / parametrized_solver_fixture

    arguments = [
        "create",
        f"--prefix={prefix}",
        "--channel",
        str(TEST_RECIPES_CHANNEL),
        "--override-channels",
        package_record.name,
        "--yes",
    ]
    if download_only:
        arguments.append("--download-only")

    _, _, exc = conda_cli(
        *arguments,
        raises=CondaMultiError,
    )

    assert exc.match("rejected")
    reject.assert_called_once()
    assert isinstance(reject.call_args.args[0], PackageRecord)
    archive_path = Path(reject.call_args.args[1])
    assert not archive_path.exists()
    assert not Path(strip_pkg_extension(str(archive_path))[0]).exists()
    assert not (prefix / "conda-meta").exists()


@pytest.mark.integration
def test_rejection_precedes_prefix_actions_when_rollback_is_disabled(
    parametrized_solver_fixture: str,
    package_record: PackageRecord,
    plugin_manager_with_reporter_backends: CondaPluginManager,
    conda_cli: CondaCLIFixture,
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    tmp_path: Path,
    tmp_pkgs_dir: Path,
) -> None:
    plugin_manager = plugin_manager_with_reporter_backends
    plugin_manager.load_plugins(solvers)
    if parametrized_solver_fixture == "libmamba":
        from conda_libmamba_solver import plugin as libmamba_solver_plugin

        plugin_manager.load_plugins(libmamba_solver_plugin)
    plugin_manager.load_plugins(*package_extractors.plugins)
    prefix = tmp_path / parametrized_solver_fixture
    conda_cli(
        "create",
        f"--prefix={prefix}",
        "--channel",
        str(TEST_RECIPES_CHANNEL),
        "--override-channels",
        package_record.name,
        "--yes",
    )
    before = {
        path.relative_to(prefix): path.read_bytes()
        for path in prefix.rglob("*")
        if path.is_file()
    }

    monkeypatch.setenv("CONDA_ROLLBACK_ENABLED", "false")
    reset_context()
    assert not context.rollback_enabled
    reject = mocker.MagicMock(side_effect=CondaVerificationError("rejected"))
    register_verifier(
        plugin_manager,
        CondaPackageVerifier(name="test-verifier", verify=reject),
    )
    unlink = mocker.spy(UnlinkPathAction, "execute")
    link = mocker.spy(LinkPathAction, "execute")
    prefix_record = mocker.spy(CreatePrefixRecordAction, "execute")

    _, _, exc = conda_cli(
        "install",
        f"--prefix={prefix}",
        "--channel",
        str(TEST_RECIPES_CHANNEL),
        "--override-channels",
        "--force-reinstall",
        package_record.name,
        "--yes",
        raises=CondaMultiError,
    )

    assert exc.match("rejected")
    reject.assert_called_once()
    unlink.assert_not_called()
    link.assert_not_called()
    prefix_record.assert_not_called()
    assert {
        path.relative_to(prefix): path.read_bytes()
        for path in prefix.rglob("*")
        if path.is_file()
    } == before


@pytest.mark.parametrize(
    ("sha256", "size", "md5"),
    (
        pytest.param("0" * 64, None, None, id="sha256"),
        pytest.param(None, 0, None, id="size"),
        pytest.param(None, None, "0" * 32, id="md5-fallback"),
    ),
)
def test_package_integrity_mismatch_prevents_verifier(
    sha256: str | None,
    size: int | None,
    md5: str | None,
    package_path: Path,
    package_record: PackageRecord,
    plugin_manager: CondaPluginManager,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    verify = mocker.stub(name="verify")
    register_verifier(
        plugin_manager,
        CondaPackageVerifier(name="test-verifier", verify=verify),
    )
    action = ExtractPackageAction(
        source_full_path=str(package_path),
        target_pkgs_dir=tmp_path,
        target_extracted_dirname="extracted",
        record_or_spec=package_record,
        sha256=sha256,
        size=size,
        md5=md5,
    )

    with pytest.raises(ChecksumMismatchError):
        action.verify()

    verify.assert_not_called()


@pytest.mark.parametrize("checksum_name", ("sha256", "md5"))
def test_package_archive_is_rehashed_before_verifier(
    checksum_name: str,
    package_path: Path,
    package_record: PackageRecord,
    plugin_manager: CondaPluginManager,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / package_path.name
    archive_path.write_bytes(package_path.read_bytes())
    expected_checksum = compute_sum(archive_path, checksum_name)
    verify = mocker.stub(name="verify")
    register_verifier(
        plugin_manager,
        CondaPackageVerifier(name="test-verifier", verify=verify),
    )
    extract = mocker.patch.object(plugin_manager, "extract_package")
    action = ExtractPackageAction(
        source_full_path=str(archive_path),
        target_pkgs_dir=tmp_path,
        target_extracted_dirname="extracted",
        record_or_spec=package_record,
        sha256=expected_checksum if checksum_name == "sha256" else None,
        size=None,
        md5=expected_checksum if checksum_name == "md5" else None,
    )
    archive_path.write_bytes(b"x" * archive_path.stat().st_size)

    with pytest.raises(ChecksumMismatchError):
        do_extract_action(package_record, action, mocker.MagicMock())

    verify.assert_not_called()
    extract.assert_not_called()


def test_extractor_uses_verified_staged_archive(
    package_path: Path,
    plugin_manager: CondaPluginManager,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / package_path.name
    original_bytes = package_path.read_bytes()
    archive_path.write_bytes(original_bytes)
    expected_sha256 = compute_sum(archive_path, "sha256")
    expected_md5 = compute_sum(archive_path, "md5")

    def replace_cache_archive(_record_or_spec, staged_path, sha256):
        assert Path(staged_path).name == archive_path.name
        assert sha256 == expected_sha256
        archive_path.write_bytes(b"replaced after verification")

    register_verifier(
        plugin_manager,
        CondaPackageVerifier(
            name="test-verifier",
            verify=replace_cache_archive,
        ),
    )
    plugin_manager.load_plugins(*package_extractors.plugins)
    explicit_spec = MatchSpec(url=archive_path.as_uri())
    action = ExtractPackageAction(
        source_full_path=str(archive_path),
        target_pkgs_dir=tmp_path,
        target_extracted_dirname="extracted",
        record_or_spec=explicit_spec,
        sha256=expected_sha256,
        size=None,
        md5=None,
    )

    do_extract_action(explicit_spec, action, mocker.MagicMock())

    assert archive_path.read_bytes() == original_bytes
    assert (tmp_path / "extracted" / "info" / "index.json").exists()
    repodata_record = json.loads(
        (tmp_path / "extracted" / "info" / "repodata_record.json").read_text()
    )
    assert repodata_record["sha256"] == expected_sha256
    assert repodata_record["md5"] == expected_md5
    assert repodata_record["size"] == len(original_bytes)
    assert not tuple(tmp_path.glob(".conda-verify-*"))


def test_package_archive_is_hashed_once_for_verifiers(
    package_path: Path,
    package_record: PackageRecord,
    plugin_manager: CondaPluginManager,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / package_path.name
    archive_path.write_bytes(package_path.read_bytes())
    expected_sha256 = compute_sum(archive_path, "sha256")
    compute_checksum = mocker.patch(
        "conda.core.path_actions.compute_sum",
        wraps=compute_sum,
    )

    def verify(record_or_spec, source_full_path, sha256):
        assert sha256 == expected_sha256
        assert Path(source_full_path).name == archive_path.name
        compute_checksum.assert_called_once_with(source_full_path, "sha256")

    register_verifier(
        plugin_manager,
        CondaPackageVerifier(name="test-verifier", verify=verify),
    )
    action = ExtractPackageAction(
        source_full_path=str(archive_path),
        target_pkgs_dir=tmp_path,
        target_extracted_dirname="extracted",
        record_or_spec=package_record,
        sha256=None,
        size=None,
        md5=None,
    )

    action.verify()

    staged_archive = Path(compute_checksum.call_args.args[0])
    assert staged_archive.name == archive_path.name
    assert staged_archive.parent.parent == tmp_path
    compute_checksum.assert_called_once_with(str(staged_archive), "sha256")
