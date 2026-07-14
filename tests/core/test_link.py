# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from conda.core import link
from conda.core.path_actions import RemoveLinkedPackageRecordAction
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
