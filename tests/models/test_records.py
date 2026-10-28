# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda.auxlib import NULL
from conda.base.context import context
from conda.core.prefix_data import PrefixData
from conda.exceptions import CondaValueError
from conda.models.channel import Channel
from conda.models.enums import PackageType
from conda.models.match_spec import MatchSpec
from conda.models.records import PackageCacheRecord, PackageRecord, PrefixRecord

blas_value = "accelerate" if context.subdir == "osx-64" else "openblas"


def test_prefix_record_no_channel():
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


def test_package_record_extra_depends():
    record = PackageRecord(name="pkg", version="1", build="0", build_number=0)
    assert not record.extra_depends
    assert "extra_depends" not in record.dump()

    record = PackageRecord(
        name="pkg",
        version="1",
        build="0",
        build_number=0,
        extra_depends={"cli": ["dep>=1"]},
    )
    assert dict(record.extra_depends) == {"cli": ("dep>=1",)}
    assert record.json()


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


@pytest.mark.integration
def test_requested_spec(tmp_env, test_recipes_channel):
    specs = ("dependent", "dependent[version='>=2']")
    with tmp_env(*specs) as prefix:
        requested = PrefixData(prefix).get("dependent")
        transitive = PrefixData(prefix).get("dependency")
        assert requested.requested_spec == str(MatchSpec.merge(specs)[0]) == specs[1]
        assert sorted(requested.requested_specs) == sorted(specs)
        assert not transitive.get("requested_spec")
        assert not transitive.get("requested_specs")


@pytest.fixture
def attestation_record_data():
    return dict(
        name="demo",
        version="1",
        build="0",
        build_number=0,
        channel="https://example.test/channel",
        subdir="noarch",
        fn="demo-1-0.conda",
        url="https://example.test/channel/noarch/demo-1-0.conda",
        sha256="b" * 64,
        md5="c" * 32,
        size=42,
    )


@pytest.mark.parametrize(
    "record_class", [PackageRecord, PackageCacheRecord, PrefixRecord]
)
@pytest.mark.parametrize("advertisement", [{}, {"attestations_sha256": "a" * 64}])
def test_attestation_digest_round_trip(
    record_class, advertisement, attestation_record_data, tmp_path
):
    if record_class is PackageCacheRecord:
        attestation_record_data.update(
            package_tarball_full_path=str(tmp_path / "demo-1-0.conda"),
            extracted_package_dir=str(tmp_path / "demo-1-0"),
        )
    record = record_class(**attestation_record_data, **advertisement)
    for copied in (
        record,
        record_class(**record.dump()),
        record_class.from_objects(record),
    ):
        assert ("attestations_sha256" in copied.dump()) == bool(advertisement)
        assert copied.get("attestations_sha256") == advertisement.get(
            "attestations_sha256"
        )


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        False,
        int("1" * 64),
        32,
        [],
        {},
        "",
        "a" * 63,
        "a" * 65,
        "A" * 64,
        "g" * 64,
        "https://secret:password@example.test/token",
    ],
    ids=[
        "null",
        "true",
        "false",
        "64-digit-number",
        "number",
        "list",
        "object",
        "empty",
        "short",
        "long",
        "uppercase",
        "non-hex",
        "credential-url",
    ],
)
@pytest.mark.parametrize("construction", ["constructor", "from-objects", "assignment"])
def test_attestation_digest_rejects_invalid_metadata(
    value, construction, attestation_record_data
):
    with pytest.raises(CondaValueError, match="attestations_sha256") as exc:
        if construction == "constructor":
            PackageRecord(**attestation_record_data, attestations_sha256=value)
        elif construction == "from-objects":
            PackageRecord.from_objects(
                {**attestation_record_data, "attestations_sha256": value}
            )
        else:
            record = PackageRecord(**attestation_record_data)
            record.attestations_sha256 = value
    assert "password" not in str(exc.value)
    assert "example.test" not in str(exc.value)


@pytest.mark.parametrize("use_override", [False, True])
def test_attestation_digest_null_does_not_fall_back(
    use_override, attestation_record_data
):
    fallback = PackageRecord(**attestation_record_data, attestations_sha256="a" * 64)
    with pytest.raises(CondaValueError, match="attestations_sha256"):
        if use_override:
            PackageRecord.from_objects(fallback, attestations_sha256=None)
        else:
            PackageRecord.from_objects({"attestations_sha256": None}, fallback)


def test_attestation_digest_explicit_absence_blocks_fallback(attestation_record_data):
    original = PackageRecord(**attestation_record_data, attestations_sha256="a" * 64)
    copied = PackageRecord.from_objects(original, attestations_sha256=NULL)
    assert "attestations_sha256" not in copied.dump()
    assert copied.get("attestations_sha256") is None
    assert original.attestations_sha256 == "a" * 64


def test_attestation_digest_partial_records_keep_normal_precedence(
    attestation_record_data,
):
    original = PackageRecord(**attestation_record_data, attestations_sha256="a" * 64)
    copied = PackageRecord.from_objects({"license": "BSD-3-Clause"}, original)
    assert copied.attestations_sha256 == "a" * 64
    assert copied.license == "BSD-3-Clause"
    overridden = PackageRecord.from_objects(original, attestations_sha256="d" * 64)
    assert overridden.attestations_sha256 == "d" * 64


def test_attestation_digest_does_not_change_package_equality(attestation_record_data):
    record = PackageRecord(**attestation_record_data)
    advertised = PackageRecord(**attestation_record_data, attestations_sha256="a" * 64)
    revised = PackageRecord(**attestation_record_data, attestations_sha256="d" * 64)
    assert record == advertised == revised
    assert hash(record) == hash(advertised) == hash(revised)


@pytest.mark.parametrize(
    "cached_changes, matches",
    [
        ({}, True),
        ({"fn": "demo-1-0.tar.bz2"}, False),
        ({"sha256": None}, False),
        ({"sha256": "d" * 64}, False),
        ({"md5": None}, False),
        ({"md5": "e" * 32}, False),
        ({"size": None}, False),
        ({"size": 43}, False),
    ],
    ids=[
        "exact",
        "other-format",
        "missing-sha256",
        "different-sha256",
        "missing-md5",
        "different-md5",
        "missing-size",
        "different-size",
    ],
)
def test_advertised_cache_record_requires_exact_metadata(
    cached_changes, matches, attestation_record_data, tmp_path
):
    selected = PackageRecord(**attestation_record_data, attestations_sha256="a" * 64)
    cached_data = {**attestation_record_data, **cached_changes}
    if cached_data.get("size") is None:
        cached_data.pop("size")
    cached = PackageCacheRecord(
        **cached_data,
        package_tarball_full_path=str(tmp_path / "demo-1-0.conda"),
        extracted_package_dir=str(tmp_path / "demo-1-0"),
    )
    assert cached.matches_metadata(selected) is matches


def test_unadvertised_cache_record_keeps_legacy_matching(
    attestation_record_data, tmp_path
):
    selected = PackageRecord(
        **attestation_record_data, legacy_bz2_md5="d" * 32, legacy_bz2_size=41
    )
    cached = PackageCacheRecord(
        **{
            **attestation_record_data,
            "fn": "demo-1-0.tar.bz2",
            "sha256": None,
            "md5": "d" * 32,
            "size": 41,
        },
        package_tarball_full_path=str(tmp_path / "demo-1-0.tar.bz2"),
        extracted_package_dir=str(tmp_path / "demo-1-0"),
    )
    assert cached.matches_metadata(selected)
