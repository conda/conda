# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from pathlib import Path

from conda.base.context import reset_context
from conda.core import link
from conda.core.path_actions import RemoveLinkedPackageRecordAction
from conda.models.channel import Channel
from conda.models.enums import FileMode, PathEnum
from conda.models.package_info import PackageInfo
from conda.models.records import PackageRecord, PathDataV1, PathsData, PrefixRecord


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


def test_verify_uses_parallel_prefix_rewrite_actions(tmp_path, mocker, monkeypatch):
    source_dir = tmp_path / "pkgs"
    prefix_placeholder = "/" + "placeholder" * 30
    path_data = []
    (source_dir / "info").mkdir(parents=True)
    (source_dir / "info" / "index.json").write_text("{}", encoding="utf-8")
    for index in range(4):
        source_short_path = f"bin/tool-{index}"
        source_path = source_dir / "bin" / f"tool-{index}"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(
            b"\x7fELF..." + prefix_placeholder.encode() + b"/bin/python\0"
        )
        path_data.append(
            PathDataV1(
                _path=source_short_path,
                path_type=PathEnum.hardlink,
                prefix_placeholder=prefix_placeholder,
                file_mode=FileMode.binary,
            )
        )
    repodata_record = PackageRecord(
        build=0,
        build_number=0,
        name="test-prefix-replace",
        version=0,
        channel="defaults",
        subdir="linux-64",
        fn="test-prefix-replace-0-0.conda",
        md5="0123456789",
    )
    package_info = PackageInfo(
        extracted_package_dir=str(source_dir),
        package_tarball_full_path=str(source_dir / "test-prefix-replace-0-0.conda"),
        channel=Channel("defaults"),
        repodata_record=repodata_record,
        url="https://example.invalid/test-prefix-replace-0-0.conda",
        package_metadata=None,
        paths_data=PathsData(paths_version=1, paths=path_data),
    )
    target_prefix = str(tmp_path / "prefix")
    link_prec = package_info.repodata_record
    setup = link.PrefixSetup(
        target_prefix,
        (),
        (link_prec,),
        (),
        (),
        (),
    )
    mocker.patch(
        "conda.core.link.PackageCacheData.get_entry_to_link", return_value=object()
    )
    mocker.patch("conda.core.package_cache_data.ProgressiveFetchExtract.execute")
    mocker.patch("conda.core.link.read_package_info", return_value=package_info)
    monkeypatch.setenv("CONDA_VERIFY_THREADS", "2")
    reset_context()

    transaction = link.UnlinkLinkTransaction(setup)

    transaction.verify()

    link_actions = tuple(
        action
        for action_group in transaction.prefix_action_groups[
            target_prefix
        ].link_action_groups
        for action in action_group.actions
        if getattr(action, "prefix_placeholder", None)
    )
    assert len(link_actions) == 4
    for action in link_actions:
        assert action.verified
        assert action.prefix_path_data.file_mode == FileMode.binary
        assert Path(action.intermediate_path).exists()
        assert (
            bytes(target_prefix, encoding="utf-8")
            in Path(action.intermediate_path).read_bytes()
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
