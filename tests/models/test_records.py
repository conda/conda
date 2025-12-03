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


@pytest.mark.parametrize(
    "name,version,build,expected_exact,expected_version",
    [
        # Basic case
        ("numpy", "1.21.0", "py39h_0", "numpy=1.21.0=py39h_0", "numpy=1.21.0"),
        # Special characters in name, version, and build
        (
            "my-package",
            "2.1.0-alpha",
            "py38_custom.build",
            "my-package=2.1.0-alpha=py38_custom.build",
            "my-package=2.1.0-alpha",
        ),
        # Underscores and numbers
        (
            "scipy_special",
            "1.7.0",
            "py39_1",
            "scipy_special=1.7.0=py39_1",
            "scipy_special=1.7.0",
        ),
        # Complex build strings
        (
            "tensorflow",
            "2.8.0",
            "cuda112py39_0",
            "tensorflow=2.8.0=cuda112py39_0",
            "tensorflow=2.8.0",
        ),
    ],
)
def test_package_record_spec_strings(
    name, version, build, expected_exact, expected_version
):
    """Test the spec and spec_no_build properties of PackageRecord."""
    rec = PackageRecord(
        name=name,
        version=version,
        build=build,
        build_number=0,
        channel=Channel("conda-forge"),
        subdir="linux-64",
        fn=f"{name}-{version}-{build}.conda",
    )

    # Test spec property (includes build string)
    assert rec.spec == expected_exact

    # Test spec_no_build property (excludes build string)
    assert rec.spec_no_build == expected_version


def test_package_record_spec_strings_vs_str():
    """Test the spec and spec_no_build properties of PackageRecord."""
    rec = PackageRecord(
        name="scipy",
        version="1.7.0",
        build="py39_1",
        build_number=1,
        channel=Channel("conda-forge"),
        subdir="osx-64",
        fn="scipy-1.7.0-py39_1.conda",
    )

    # The properties should not include channel/subdir information
    assert rec.spec == "scipy=1.7.0=py39_1"  # Full spec (single equals)
    assert rec.spec_no_build == "scipy=1.7.0"  # No build spec (single equals)

    # The __str__ method includes channel/subdir information
    assert str(rec) == "conda-forge/osx-64::scipy==1.7.0=py39_1"

    # Verify they are different
    assert rec.spec != str(rec)
    assert rec.spec_no_build != str(rec)


@pytest.mark.parametrize(
    "record_class,extra_kwargs",
    [
        (PackageRecord, {}),
        (
            PrefixRecord,
            {
                "url": "https://repo.anaconda.com/pkgs/main/noarch/requests-2.25.1-pyhd3eb1b0_0.conda",
                "md5": "12345678901234567890123456789012",
                "files": (),
            },
        ),
    ],
)
def test_record_spec_strings_inheritance(record_class, extra_kwargs):
    """Test that both PackageRecord and PrefixRecord have spec string properties."""
    rec = record_class(
        name="requests",
        version="2.25.1",
        build="pyhd3eb1b0_0",
        build_number=0,
        channel=Channel("defaults"),
        subdir="noarch",
        fn="requests-2.25.1-pyhd3eb1b0_0.conda",
        **extra_kwargs,
    )

    # Both record types should have the spec string properties
    assert rec.spec == "requests=2.25.1=pyhd3eb1b0_0"
    assert rec.spec_no_build == "requests=2.25.1"

    # Verify that the properties exist (important for environment export)
    assert hasattr(rec, "spec")
    assert hasattr(rec, "spec_no_build")
