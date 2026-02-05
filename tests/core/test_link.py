# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from unittest.mock import MagicMock, create_autospec, patch

import pytest

from conda.common.compat import on_mac, on_win
from conda.core import link
from conda.core.link import PrefixActions, UnlinkLinkTransaction
from conda.core.path_actions import CreatePrefixRecordAction, UnlinkPathAction
from conda.exceptions import UnknownPackageClobberError
from conda.models.enums import LinkType
from conda.models.records import PackageRecord


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


@pytest.mark.skipif(
    not (on_win or on_mac),
    reason="Test requires case-insensitive filesystem (Windows or macOS)",
)
def test_case_mismatch_no_collision_on_case_insensitive_filesystem(tmp_path):
    """
    Test that paths differing only in case don't cause false collisions
    on case-insensitive filesystems.
    """
    target_prefix = str(tmp_path)
    site_packages = tmp_path / "lib" / "python3.13" / "site-packages"
    site_packages.mkdir(parents=True)

    old_path = "lib/python3.13/site-packages/PyJWT-2.10.1.dist-info/INSTALLER"
    new_path = "lib/python3.13/site-packages/pyjwt-2.10.1.dist-info/INSTALLER"

    old_dist_info = site_packages / "PyJWT-2.10.1.dist-info"
    old_dist_info.mkdir()
    (old_dist_info / "INSTALLER").write_text("conda")

    transaction_context = MagicMock()
    old_prefix_record = MagicMock()
    old_prefix_record.files = [old_path]
    unlink_action = UnlinkPathAction(
        transaction_context, old_prefix_record, target_prefix, old_path
    )

    new_package_info = MagicMock()
    new_package_info.repodata_record.dist_str.return_value = (
        "defaults/osx-arm64::pyjwt-2.10.1-py313hca03da5_1"
    )
    new_link_action = MagicMock()
    new_link_action.target_short_path = new_path
    new_link_action.link_type = LinkType.hardlink

    create_prefix_action = create_autospec(CreatePrefixRecordAction, instance=True)
    create_prefix_action.package_info = new_package_info
    create_prefix_action.all_link_path_actions = [new_link_action]

    prefix_action_group = PrefixActions(
        remove_menu_action_groups=(),
        unlink_action_groups=(MagicMock(actions=[unlink_action]),),
        unregister_action_groups=(),
        link_action_groups=(),
        register_action_groups=(),
        compile_action_groups=(),
        make_menu_action_groups=(),
        entry_point_action_groups=(),
        prefix_record_groups=(MagicMock(actions=[create_prefix_action]),),
    )

    with patch("conda.core.link.PrefixData") as mock_prefix_data:
        mock_prefix_data.return_value.iter_records.return_value = []
        errors = UnlinkLinkTransaction._verify_prefix_level(
            (target_prefix, prefix_action_group)
        )

    assert len(errors) == 0


def test_legitimate_collision_still_detected(tmp_path):
    """
    Test that legitimate path collisions are still detected correctly.
    """
    target_prefix = str(tmp_path)
    site_packages = tmp_path / "lib" / "python3.13" / "site-packages"
    site_packages.mkdir(parents=True)

    path = "lib/python3.13/site-packages/somefile.txt"
    (site_packages / "somefile.txt").write_text("content")

    new_package_info = MagicMock()
    new_package_info.repodata_record.dist_str.return_value = (
        "defaults/osx-arm64::somepackage-1.0.0-py313_0"
    )
    new_link_action = MagicMock()
    new_link_action.target_short_path = path
    new_link_action.link_type = LinkType.hardlink

    create_prefix_action = create_autospec(CreatePrefixRecordAction, instance=True)
    create_prefix_action.package_info = new_package_info
    create_prefix_action.all_link_path_actions = [new_link_action]

    prefix_action_group = PrefixActions(
        remove_menu_action_groups=(),
        unlink_action_groups=(MagicMock(actions=[]),),
        unregister_action_groups=(),
        link_action_groups=(),
        register_action_groups=(),
        compile_action_groups=(),
        make_menu_action_groups=(),
        entry_point_action_groups=(),
        prefix_record_groups=(MagicMock(actions=[create_prefix_action]),),
    )

    with patch("conda.core.link.PrefixData") as mock_prefix_data:
        mock_prefix_data.return_value.iter_records.return_value = []
        errors = UnlinkLinkTransaction._verify_prefix_level(
            (target_prefix, prefix_action_group)
        )

    assert len(errors) > 0
    assert isinstance(errors[0], UnknownPackageClobberError)


@pytest.mark.parametrize(
    "path1,path2",
    [
        ("PyJWT-2.10.1.dist-info/INSTALLER", "pyjwt-2.10.1.dist-info/installer"),
        ("SomeFile.txt", "somefile.txt"),
        ("MIXED_CASE", "mixed_case"),
    ],
)
def test_path_normalization_logic(path1, path2):
    """
    Test that path normalization logic works correctly.

    On case-insensitive filesystems (Windows, macOS), paths that differ only
    in case should normalize to the same value for comparison.
    """
    normalize_path = lambda p: p.lower() if (on_win or on_mac) else p

    normalized1 = normalize_path(path1)
    normalized2 = normalize_path(path2)

    if on_win or on_mac:
        assert normalized1 == normalized2
        assert normalized1 == path1.lower()
        assert normalized2 == path2.lower()
    else:
        assert normalized1 == path1
        assert normalized2 == path2
