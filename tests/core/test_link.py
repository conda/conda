# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import pytest

from conda.base.context import context, reset_context
from conda.core import link
from conda.core.link import PrefixSetup, UnlinkLinkTransaction
from conda.core.path_actions import RemoveLinkedPackageRecordAction
from conda.core.prefix_data import PrefixData
from conda.exceptions import RemoveError
from conda.models.records import PackageRecord, PrefixRecord


def test_make_unlink_actions_uses_prefix_record_json_filename_for_conda_meta():
    prefix_record = PrefixRecord(
        name="idna",
        version="3.10",
        build="py3_none_any_0",
        build_number=0,
        channel="https://example.com/noarch",
        subdir="noarch",
        fn="idna-3.10-py3-none-any.whl",
        url="https://example.com/noarch/idna-3.10-py3-none-any.whl",
        extracted_package_dir="/pkgs/idna-3.10-py3-none-any",
        files=(),
    )

    actions = link.make_unlink_actions({}, "/target", prefix_record)
    remove_record_action = next(
        action
        for action in actions
        if isinstance(action, RemoveLinkedPackageRecordAction)
    )

    assert (
        remove_record_action.target_short_path
        == "conda-meta/idna-3.10-py3_none_any_0.json"
    )


def test_calculate_change_report_revised_variant():
    """
    Test to ensure that the change report will categorize a change in variant as
    a "REVISED" package.
    """
    unlink_precs = [
        PackageRecord(
            **{
                "channel": "pkgs/main/linux-64",
                "name": "mypackage_decrease_build",
                "version": "2.3.9",
                "build": "py35_0",
                # notice the build number decrease between the unlink and link precs
                "build_number": 200,
            }
        ),
        PackageRecord(
            **{
                "channel": "pkgs/main/linux-64",
                "name": "mypackage",
                "version": "2.3.9",
                "build": "py35_0",
                # notice the build number stay the same between the unlink and link precs
                "build_number": 0,
            }
        ),
    ]

    link_precs = [
        PackageRecord(
            **{
                "channel": "pkgs/main/linux-64",
                "name": "mypackage_decrease_build",
                "version": "2.3.9",
                "build": "py36_0",
                "build_number": 100,
            }
        ),
        PackageRecord(
            **{
                "channel": "pkgs/main/linux-64",
                "name": "mypackage",
                "version": "2.3.9",
                "build": "py36_0",
                "build_number": 0,
            }
        ),
    ]

    change_report = link.UnlinkLinkTransaction._calculate_change_report(
        "notarealprefix", unlink_precs, link_precs, (), (), ()
    )

    assert (
        change_report.revised_precs.get("global:mypackage_decrease_build") is not None
    )
    assert change_report.revised_precs.get("global:mypackage") is not None


def test_calculate_change_report_downgrade():
    """
    Test to ensure that the change report will categorize a downgrade of a package
    """
    unlink_precs = [
        PackageRecord(
            **{
                "channel": "pkgs/main/linux-64",
                "name": "mypackage_downgrade_version",
                "version": "2.3.9",
                "build": "py36_0",
                "build_number": 0,
            }
        ),
        PackageRecord(
            **{
                "channel": "pkgs/main/linux-64",
                "name": "mypackage_downgrade_build",
                "version": "2.3.9",
                "build": "py36_0",
                "build_number": 1,
            }
        ),
    ]

    link_precs = [
        PackageRecord(
            **{
                "channel": "pkgs/main/linux-64",
                "name": "mypackage_downgrade_version",
                "version": "2.3.8",
                "build": "py36_0",
                "build_number": 0,
            }
        ),
        PackageRecord(
            **{
                "channel": "pkgs/main/linux-64",
                "name": "mypackage_downgrade_build",
                "version": "2.3.9",
                "build": "py36_0",
                "build_number": 0,
            }
        ),
    ]

    change_report = link.UnlinkLinkTransaction._calculate_change_report(
        "notarealprefix", unlink_precs, link_precs, (), (), ()
    )

    # ensure downgrade version gets added to the downgrade section
    assert (
        change_report.downgraded_precs.get("global:mypackage_downgrade_version")
        is not None
    )

    # ensure downgrade build number gets added to the downgrade section
    assert (
        change_report.downgraded_precs.get("global:mypackage_downgrade_build")
        is not None
    )


def test_calculate_change_report_update():
    """
    Test to ensure that the change report will categorize an upgrade of a package
    """
    unlink_precs = [
        PackageRecord(
            **{
                "channel": "pkgs/main/linux-64",
                "name": "mypackage",
                "version": "2.3.9",
                "build": "py35_0",
                "build_number": 0,
            }
        ),
        PackageRecord(
            **{
                "channel": "pkgs/main/linux-64",
                "name": "mypackage_upgrade_build",
                "version": "2.3.9",
                "build": "py36_0",
                "build_number": 1,
            }
        ),
    ]

    link_precs = [
        PackageRecord(
            **{
                "channel": "pkgs/main/linux-64",
                "name": "mypackage",
                "version": "2.4.9",
                "build": "py36_0",
                "build_number": 0,
            }
        ),
        PackageRecord(
            **{
                "channel": "pkgs/main/linux-64",
                "name": "mypackage_upgrade_build",
                "version": "2.3.9",
                "build": "py36_0",
                "build_number": 2,
            }
        ),
    ]

    change_report = link.UnlinkLinkTransaction._calculate_change_report(
        "notarealprefix", unlink_precs, link_precs, (), (), ()
    )

    assert change_report.updated_precs.get("global:mypackage") is not None
    assert change_report.updated_precs.get("global:mypackage_upgrade_build") is not None


def test_calculate_change_report_superseded():
    """
    Test to ensure that the change report will categorize a superseded package
    """
    unlink_precs = [
        PackageRecord(
            **{
                "channel": "pkgs/main/linux-64",
                "name": "mypackage",
                "version": "2.3.9",
                "build": "py35_0",
                "build_number": 0,
            }
        ),
    ]

    link_precs = [
        PackageRecord(
            **{
                "channel": "conda-forge/linux-64",
                "name": "mypackage",
                "version": "2.3.9",
                "build": "py36_0",
                "build_number": 0,
            }
        ),
    ]

    change_report = link.UnlinkLinkTransaction._calculate_change_report(
        "notarealprefix", unlink_precs, link_precs, (), (), ()
    )

    assert change_report.superseded_precs.get("global:mypackage") is not None


def test_cleanup_transaction_artifacts_removes_only_created_prefixes(tmp_path):
    """
    A prefix created by this transaction must be removed on cleanup, while a
    prefix that already existed must be left untouched.
    See https://github.com/conda/conda/issues/16076.
    """
    created = tmp_path / "created"
    created.mkdir()
    (created / "conda-meta").mkdir()

    preexisting = tmp_path / "preexisting"
    preexisting.mkdir()
    (preexisting / "conda-meta").mkdir()

    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()

    txn = object.__new__(UnlinkLinkTransaction)
    txn.transaction_context = {
        "temp_dir": str(temp_dir),
        "created_prefixes": {str(created)},
    }

    txn._cleanup_transaction_artifacts()

    assert not created.exists()
    assert not temp_dir.exists()
    assert preexisting.exists()


def test_execute_failure_removes_created_prefixes(tmp_path, mocker):
    """Execute failure must remove prefixes this transaction created."""
    created = tmp_path / "created"
    created.mkdir()
    (created / "conda-meta").mkdir()

    preexisting = tmp_path / "preexisting"
    preexisting.mkdir()
    (preexisting / "conda-meta").mkdir()

    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()

    txn = object.__new__(UnlinkLinkTransaction)
    txn._verified = True
    txn.prefix_action_groups = {}
    txn.transaction_context = {
        "temp_dir": str(temp_dir),
        "created_prefixes": {str(created)},
    }
    mocker.patch.object(txn, "_execute", side_effect=RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        txn.execute()

    assert not created.exists()
    assert not temp_dir.exists()
    assert preexisting.exists()


def _package(name: str) -> PackageRecord:
    return PackageRecord(name=name, version="1.0", build="0", build_number=0)


def _conda_root(tmp_path, monkeypatch, depends: tuple[str, ...]) -> str:
    """Prefix that conda treats as its own root, with a conda record installed."""
    prefix = tmp_path / "root"
    (prefix / "conda-meta").mkdir(parents=True)
    monkeypatch.setenv("CONDA_ROOT_PREFIX", str(prefix))
    reset_context()
    prefix_str = context.root_prefix
    PrefixData(prefix_str).insert(
        PrefixRecord(
            name="conda",
            version="1.0",
            build="0",
            build_number=0,
            channel="test",
            subdir="noarch",
            fn="conda-1.0-0.conda",
            url="https://example.com/conda-1.0-0.conda",
            depends=depends,
        )
    )
    monkeypatch.setattr(
        type(context),
        "conda_prefix",
        property(lambda self: prefix_str),
    )
    return prefix_str


def _verify(prefix: str, *, link_precs=(), unlink_precs=()) -> list:
    setup = PrefixSetup(prefix, tuple(unlink_precs), tuple(link_precs), (), (), ())
    return [
        exc
        for exc in UnlinkLinkTransaction._verify_transaction_level({prefix: setup})
        if isinstance(exc, RemoveError)
    ]


def test_missing_conda_dependency_does_not_block_other_changes(tmp_path, monkeypatch):
    """A conda dependency absent from conda-meta is not a removal (#14051)."""
    prefix = _conda_root(tmp_path, monkeypatch, ("missing-dep",))

    assert _verify(prefix, link_precs=(_package("small-executable"),)) == []


def test_unlinking_conda_dependency_is_still_blocked(tmp_path, monkeypatch):
    """Replacing conda while dropping one of its dependencies is still rejected."""
    prefix = _conda_root(tmp_path, monkeypatch, ())
    replacement = PackageRecord(
        name="conda",
        version="2.0",
        build="0",
        build_number=0,
        depends=["missing-dep"],
    )

    errors = _verify(
        prefix,
        link_precs=(replacement,),
        unlink_precs=(_package("missing-dep"),),
    )

    assert len(errors) == 1
    assert "missing-dep" in str(errors[0])
