# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda.base.context import context
from conda.core.prefix_data import PrefixData
from conda.models.channel import Channel
from conda.models.enums import PackageType
from conda.models.match_spec import MatchSpec
from conda.models.records import PackageCacheRecord, PackageRecord, PrefixRecord
from conda.models.version import VersionOrder

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


def test_package_record_comparison_names():
    """Ensure PackageRecords with different names sort alphabetically."""
    r_a = PackageRecord(name="arrow", version="1.0.0", build="0", build_number=0)
    r_z = PackageRecord(name="zstandard", version="0.1.0", build="0", build_number=0)
    assert r_a < r_z
    assert r_z > r_a
    assert r_a <= r_z
    assert r_z >= r_a
    assert r_a != r_z


def test_package_record_comparison_versions():
    """Ensure PackageRecords sort by VersionOrder instead of string comparison."""
    r_1_3 = PackageRecord(name="maturin", version="1.3.0", build="0", build_number=0)
    r_1_11 = PackageRecord(name="maturin", version="1.11.5", build="0", build_number=0)
    assert r_1_3 < r_1_11
    assert not (r_1_11 < r_1_3)
    assert r_1_3 <= r_1_11
    assert r_1_11 >= r_1_3


def test_package_record_comparison_semantically_equivalent_versions():
    """Ensure semantically equivalent VersionOrder strings tie-break deterministically."""
    r1 = PackageRecord(name="pkg", version="1.1", build="0", build_number=0)
    r2 = PackageRecord(name="pkg", version="1.1.0", build="0", build_number=0)
    # Both have VersionOrder('1.1') == VersionOrder('1.1.0')
    # Deterministic tie-breaker on raw version string ensures total order
    assert r1 < r2
    assert not (r2 < r1)
    assert r1 != r2


def test_package_record_comparison_equivalent_versions_conflicting_build_numbers():
    """Ensure authoritative build_number takes precedence over raw version string.

    When two records have semantically equivalent VersionOrder (e.g. '1.1' and '1.1.0'),
    the authoritative numeric build_number must decide the order, not lexical
    comparison of the raw version strings.
    """
    # r_b2 has version '1.1' (lexically < '1.1.0') but build_number 2
    r_b2 = PackageRecord(name="pkg", version="1.1", build="2", build_number=2)
    # r_b1 has version '1.1.0' (lexically > '1.1') but build_number 1
    r_b1 = PackageRecord(name="pkg", version="1.1.0", build="1", build_number=1)

    assert VersionOrder(r_b2.version) == VersionOrder(r_b1.version)
    # build_number 1 must sort before build_number 2
    assert r_b1 < r_b2
    assert not (r_b2 < r_b1)
    assert r_b1 <= r_b2
    assert r_b2 >= r_b1
    assert r_b1 != r_b2

    # When both semantic version and build_number are identical,
    # raw version string breaks the tie deterministically
    r_same1 = PackageRecord(name="pkg", version="1.1", build="1", build_number=1)
    r_same2 = PackageRecord(name="pkg", version="1.1.0", build="1", build_number=1)
    assert r_same1 < r_same2
    assert not (r_same2 < r_same1)


def test_package_record_comparison_build_numbers():
    """Ensure numeric build numbers are ordered numerically (e.g. 2 before 10)."""
    r_2 = PackageRecord(name="pkg", version="1.0.0", build="py312_2", build_number=2)
    r_10 = PackageRecord(name="pkg", version="1.0.0", build="py312_10", build_number=10)
    assert r_2 < r_10
    assert r_10 > r_2
    assert r_2 <= r_10
    assert r_10 >= r_2

    # Authoritative metadata precedence: build_number 1 sorts before build_number 2
    # even if build string had an unusual suffix
    r_meta1 = PackageRecord(
        name="pkg", version="1.0.0", build="cuda_99", build_number=1
    )
    r_meta2 = PackageRecord(name="pkg", version="1.0.0", build="cuda_0", build_number=2)
    assert r_meta1 < r_meta2


def test_package_record_comparison_build_strings():
    """Ensure BuildString tie-breaker orders variant suffixes when build_numbers match."""
    r_cpu = PackageRecord(
        name="pkg", version="1.0.0", build="py312_0_cpu", build_number=0
    )
    r_cuda = PackageRecord(
        name="pkg", version="1.0.0", build="py312_0_cuda", build_number=0
    )
    assert r_cpu < r_cuda
    assert r_cuda > r_cpu


def test_package_record_comparison_equality_and_hash_invariance():
    """Ensure rich comparison is strictly consistent with __eq__ and __hash__."""
    r1 = PackageRecord(name="pkg", version="1.0.0", build="0", build_number=0)
    r2 = PackageRecord(name="pkg", version="1.0.0", build="0", build_number=0)

    assert r1 == r2
    assert not (r1 < r2)
    assert not (r2 < r1)
    assert r1 <= r2
    assert r2 <= r1
    assert r1 >= r2
    assert r2 >= r1
    assert hash(r1) == hash(r2)

    # Dictionary / set key behaviour
    s = {r1}
    assert r2 in s
    d = {r1: "value"}
    assert d[r2] == "value"


def test_package_record_comparison_transitivity_and_totality():
    """Ensure comparison operators satisfy strict total order laws."""
    records = [
        PackageRecord(name="a", version="1.0", build="0", build_number=0),
        PackageRecord(name="b", version="0.9", build="0", build_number=0),
        PackageRecord(name="b", version="1.3.0", build="0", build_number=0),
        PackageRecord(name="b", version="1.11.5", build="0", build_number=0),
        PackageRecord(name="b", version="1.11.5", build="1", build_number=1),
        PackageRecord(name="b", version="1.11.5", build="10", build_number=10),
    ]
    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            assert records[i] < records[j]
            assert not (records[j] < records[i])
            assert records[i] <= records[j]
            assert not (records[j] <= records[i])
            for k in range(j + 1, len(records)):
                assert records[i] < records[k]


def test_package_record_comparison_separate_format_cache(monkeypatch):
    """Ensure separate_format_cache includes filename in tie-breaker consistently."""
    # When separate_format_cache is False (default), records test equal
    monkeypatch.setattr(context, "separate_format_cache", False)
    r_tar = PackageRecord(
        name="pkg", version="1.0", build="0", build_number=0, fn="pkg-1.0-0.tar.bz2"
    )
    r_conda = PackageRecord(
        name="pkg", version="1.0", build="0", build_number=0, fn="pkg-1.0-0.conda"
    )
    assert r_tar == r_conda
    assert not (r_tar < r_conda)
    assert not (r_conda < r_tar)
    assert r_tar <= r_conda
    assert r_conda <= r_tar

    # When separate_format_cache is True, filename is part of identity and sort order
    monkeypatch.setattr(context, "separate_format_cache", True)
    r_tar2 = PackageRecord(
        name="pkg", version="1.0", build="0", build_number=0, fn="pkg-1.0-0.tar.bz2"
    )
    r_conda2 = PackageRecord(
        name="pkg", version="1.0", build="0", build_number=0, fn="pkg-1.0-0.conda"
    )
    assert r_tar2 != r_conda2
    # '.conda' sorts before '.tar.bz2'
    assert r_conda2 < r_tar2
    assert not (r_tar2 < r_conda2)


def test_package_record_comparison_none_fields():
    """Ensure None in optional fields does not raise TypeError during comparison."""
    r1 = PackageRecord(
        name="pkg",
        version="1.0",
        build="0",
        build_number=0,
        channel=None,
        subdir=None,
        fn=None,
    )
    r2 = PackageRecord(
        name="pkg",
        version="2.0",
        build="0",
        build_number=0,
        channel=Channel("defaults"),
        subdir="noarch",
        fn="pkg-2.0-0.conda",
    )
    assert r1 < r2
    assert r2 > r1


def test_package_record_cross_subclass_comparison():
    """Ensure PackageRecord, PrefixRecord, and PackageCacheRecord compare consistently."""
    pr = PrefixRecord(
        name="pkg",
        version="1.0",
        build="0",
        build_number=0,
        url="https://repo.anaconda.com/pkgs/main/noarch/pkg-1.0-0.conda",
        md5="12345678901234567890123456789012",
        files=(),
    )
    cache = PackageCacheRecord(
        name="pkg",
        version="1.5",
        build="0",
        build_number=0,
        package_tarball_full_path="C:/cache/pkg-1.5-0.tar.bz2",
        extracted_package_dir="C:/cache/pkg-1.5-0",
    )
    prec = PackageRecord(name="pkg", version="2.0", build="0", build_number=0)

    assert pr < cache < prec
    assert prec > cache > pr
    assert pr <= cache <= prec
    assert prec >= cache >= pr


def test_package_record_unsupported_operands():
    """Ensure comparing PackageRecord to incompatible types raises TypeError."""
    prec = PackageRecord(name="pkg", version="1.0", build="0", build_number=0)
    for bad in (None, 123, "pkg-1.0-0", MatchSpec("pkg")):
        with pytest.raises(TypeError):
            _ = prec < bad
        with pytest.raises(TypeError):
            _ = prec <= bad
        with pytest.raises(TypeError):
            _ = prec > bad
        with pytest.raises(TypeError):
            _ = prec >= bad


def test_package_record_comparison_none_vs_empty_channel_subdir_fn(monkeypatch):
    """Ensure None and empty string in optional fields do not collide in _sort_key.

    Tests both valid model records and defensive conditions across all six
    comparison operations (<, <=, >, >=, ==, !=) and hashing consistency.
    """
    from unittest.mock import Mock

    from conda.models.records import _safe_opt_str

    def assert_strict_total_order(lesser, greater):
        # Identity / distinctness
        assert lesser is not greater
        assert lesser != greater
        assert greater != lesser
        assert not (lesser == greater)
        assert not (greater == lesser)

        # Strict ordering
        assert lesser < greater
        assert lesser <= greater
        assert not (lesser > greater)
        assert not (lesser >= greater)
        assert greater > lesser
        assert greater >= lesser
        assert not (greater < lesser)
        assert not (greater <= lesser)

    # 1. Channel: valid empty canonical name vs named channel
    r_c_empty = PackageRecord(
        name="pkg", version="1.0", build="0", build_number=0, channel=Channel("")
    )
    r_c_def = PackageRecord(
        name="pkg",
        version="1.0",
        build="0",
        build_number=0,
        channel=Channel("defaults"),
    )
    assert_strict_total_order(r_c_empty, r_c_def)

    # Verify equal-but-distinct hashing and symmetric equality
    r_c_def_clone = PackageRecord(
        name="pkg",
        version="1.0",
        build="0",
        build_number=0,
        channel=Channel("defaults"),
    )
    assert r_c_def is not r_c_def_clone
    assert r_c_def == r_c_def_clone
    assert r_c_def_clone == r_c_def
    assert hash(r_c_def) == hash(r_c_def_clone)
    assert not (r_c_def < r_c_def_clone)
    assert not (r_c_def_clone < r_c_def)
    assert r_c_def <= r_c_def_clone
    assert r_c_def_clone <= r_c_def

    # 1b. Channel defensive: channel_name is None vs empty string
    r_c_none = PackageRecord(name="pkg", version="1.0", build="0", build_number=0)
    c_mock = Mock()
    c_mock.canonical_name = None
    r_c_none.__dict__["channel"] = c_mock
    assert r_c_none.channel_name is None
    assert_strict_total_order(r_c_none, r_c_empty)

    # 2. Subdir: valid empty subdir vs named subdir
    r_s_empty = PackageRecord(
        name="pkg", version="1.0", build="0", build_number=0, subdir=""
    )
    r_s_noarch = PackageRecord(
        name="pkg", version="1.0", build="0", build_number=0, subdir="noarch"
    )
    assert_strict_total_order(r_s_empty, r_s_noarch)

    # 2b. Subdir defensive: verify _safe_opt_str guarantees None < "" < values
    assert _safe_opt_str(None) < _safe_opt_str("")
    assert _safe_opt_str("") < _safe_opt_str("noarch")

    # 3. Fn: valid empty fn vs package filename under separate_format_cache
    monkeypatch.setattr(context, "separate_format_cache", True)
    r_fn_empty = PackageRecord(
        name="pkg", version="1.0", build="0", build_number=0, fn=""
    )
    r_fn_pkg = PackageRecord(
        name="pkg",
        version="1.0",
        build="0",
        build_number=0,
        fn="pkg-1.0-0.conda",
    )
    assert_strict_total_order(r_fn_empty, r_fn_pkg)

    # 3b. Fn defensive: verify _safe_opt_str guarantees None < "" < filenames
    assert _safe_opt_str(None) < _safe_opt_str("")
    assert _safe_opt_str("") < _safe_opt_str("pkg-1.0-0.conda")


def test_package_record_subclass_custom_pkey():
    """Verify behavior when a PackageRecord subclass customizes _pkey.

    Distinct subclass identities can share a base _sort_key. If a subclass
    customizes _pkey (e.g. to include a custom tracking attribute) without
    overriding _sort_key, instances with identical base package metadata will
    compare unequal under __eq__, yet evaluate as ordering-equivalent ties in
    _sort_key comparisons (neither < nor >).

    The total order consistent with equality applies across standard PackageRecord
    instances. Subclasses introducing additional identity dimensions must also
    override _sort_key if those dimensions should be distinguished during sorting.
    """

    class CustomTrackingRecord(PackageRecord):
        @property
        def _pkey(self):
            return (*super()._pkey, getattr(self, "tracking_tag", ""))

    c1 = CustomTrackingRecord(name="pkg", version="1.0", build="0", build_number=0)
    c1.tracking_tag = "tag-alpha"
    c2 = CustomTrackingRecord(name="pkg", version="1.0", build="0", build_number=0)
    c2.tracking_tag = "tag-beta"

    # Distinct tracking tags cause distinct _pkey and unequal identity
    assert c1 != c2
    assert c2 != c1

    # Base _sort_key considers standard fields only, resulting in an ordering tie
    assert not (c1 < c2)
    assert not (c2 < c1)
    assert c1 <= c2
    assert c2 <= c1
    assert c1 >= c2
    assert c2 >= c1
