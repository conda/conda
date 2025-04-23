# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context
from conda.common.io import env_unmodified
from conda.models.channel import Channel
from conda.models.enums import PackageType
from conda.models.records import PackageRecord, PrefixRecord

blas_value = "accelerate" if context.subdir == "osx-64" else "openblas"


def test_prefix_record_no_channel():
    with env_unmodified(conda_tests_ctxt_mgmt_def_pol):
        pr = PrefixRecord(
            name="austin",
            version="1.2.3",
            build_string="py34_2",
            build_number=2,
            url="https://repo.anaconda.com/pkgs/main/win-32/austin-1.2.3-py34_2.tar.bz2",
            subdir="win-32",
            md5="0123456789",
            files=(),
        )
        assert (
            pr.url
            == "https://repo.anaconda.com/pkgs/main/win-32/austin-1.2.3-py34_2.tar.bz2"
        )
        assert pr.channel.canonical_name == "defaults"
        assert pr.subdir == "win-32"
        assert pr.fn == "austin-1.2.3-py34_2.tar.bz2"
        channel_str = str(
            Channel(
                "https://repo.anaconda.com/pkgs/main/win-32/austin-1.2.3-py34_2.tar.bz2"
            )
        )
        assert channel_str == "https://repo.anaconda.com/pkgs/main/win-32"
        assert dict(pr.dump()) == dict(
            name="austin",
            version="1.2.3",
            build="py34_2",
            build_number=2,
            url="https://repo.anaconda.com/pkgs/main/win-32/austin-1.2.3-py34_2.tar.bz2",
            md5="0123456789",
            files=(),
            channel=channel_str,
            subdir="win-32",
            fn="austin-1.2.3-py34_2.tar.bz2",
            constrains=(),
            depends=(),
        )


def test_package_record_timestamp():
    # regression test for #6096
    ts_secs = 1507565728
    ts_millis = ts_secs * 1000
    rec = PackageRecord(
        name="test-package",
        version="1.2.3",
        build="2",
        build_number=2,
        timestamp=ts_secs,
    )
    assert rec.timestamp == ts_secs
    assert rec.dump()["timestamp"] == ts_millis

    ts_millis = 1507565728999
    ts_secs = ts_millis / 1000
    rec = PackageRecord(
        name="test-package",
        version="1.2.3",
        build="2",
        build_number=2,
        timestamp=ts_secs,
    )
    assert rec.timestamp == ts_secs
    assert rec.dump()["timestamp"] == ts_millis


def test_package_record_feature():
    feature_name = "test_feature_name"
    package_name = f"{feature_name}@"
    feature_record = PackageRecord.feature(feature_name)
    md5 = "12345678901234567890123456789012"
    track_features = (feature_name,)
    reference_package = PackageRecord(
        name=package_name,
        version="0",
        build="0",
        channel="@",
        subdir=context.subdir,
        md5=md5,
        track_features=track_features,
        build_number=0,
        fn=package_name,
    )
    assert feature_record == reference_package
    assert feature_record.md5 == md5
    assert feature_record.track_features == (feature_name,)


@pytest.mark.parametrize(
    "version,build_string",
    [
        (None, None),
        (None, "testbuild"),
        ("123", "testbuild"),
    ],
)
def test_package_virtual_package(version, build_string):
    name = "test_vpkg_name"
    effective_version = version or "0"
    effective_build_string = build_string or "0"
    vpkg_record = PackageRecord.virtual_package(name, version, build_string)
    md5 = "12345678901234567890123456789012"
    reference_package = PackageRecord(
        package_type=PackageType.VIRTUAL_SYSTEM,
        name=name,
        version=effective_version,
        build_string=effective_build_string,
        channel="@",
        subdir=context.subdir,
        md5=md5,
        build_number=0,
        fn=name,
    )
    assert vpkg_record == reference_package
    assert vpkg_record.package_type == PackageType.VIRTUAL_SYSTEM
    assert vpkg_record.md5 == md5
