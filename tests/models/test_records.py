# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for conda.models.records."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.base.context import context
from conda.core.prefix_data import PrefixData
from conda.models.channel import Channel
from conda.models.enums import NoarchType, PackageType
from conda.models.match_spec import MatchSpec
from conda.models.records import (
    PackageCacheRecord,
    PackageRecord,
    PrefixRecord,
    SolvedRecord,
)

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any


COMMON_KWARGS: dict[str, Any] = dict(
    name="numpy",
    version="1.21.0",
    build="py39h_0",
    build_number=0,
    channel="conda-forge",
    subdir="linux-64",
    fn="numpy-1.21.0-py39h_0.conda",
)


@pytest.fixture()
def dc_record() -> PackageRecord:
    return PackageRecord(**COMMON_KWARGS)


def test_prefix_record_no_channel() -> None:
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


def test_timestamp_seconds() -> None:
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


def test_timestamp_milliseconds() -> None:
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


def test_feature_factory() -> None:
    feature_name = "test_feature_name"
    package_name = f"{feature_name}@"
    feature_record = PackageRecord.feature(feature_name)
    md5 = "12345678901234567890123456789012"
    reference = PackageRecord(
        name=package_name,
        version="0",
        build="0",
        channel="@",
        subdir=context.subdir,
        md5=md5,
        track_features=(feature_name,),
        build_number=0,
        fn=package_name,
    )
    assert feature_record == reference
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
def test_virtual_package(version: str | None, build_string: str | None) -> None:
    name = "test_vpkg_name"
    effective_version = version or "0"
    effective_build_string = build_string or "0"
    vpkg = PackageRecord.virtual_package(name, version, build_string)
    md5 = "12345678901234567890123456789012"
    reference = PackageRecord(
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
    assert vpkg == reference
    assert vpkg.effective_package_type() == PackageType.VIRTUAL_SYSTEM
    assert vpkg.md5 == md5


@pytest.mark.parametrize(
    "name,version,build,expected_spec,expected_no_build",
    [
        ("numpy", "1.21.0", "py39h_0", "numpy=1.21.0=py39h_0", "numpy=1.21.0"),
        (
            "my-package",
            "2.1.0-alpha",
            "py38_custom.build",
            "my-package=2.1.0-alpha=py38_custom.build",
            "my-package=2.1.0-alpha",
        ),
        (
            "scipy_special",
            "1.7.0",
            "py39_1",
            "scipy_special=1.7.0=py39_1",
            "scipy_special=1.7.0",
        ),
        (
            "tensorflow",
            "2.8.0",
            "cuda112py39_0",
            "tensorflow=2.8.0=cuda112py39_0",
            "tensorflow=2.8.0",
        ),
    ],
)
def test_spec_strings(
    name: str,
    version: str,
    build: str,
    expected_spec: str,
    expected_no_build: str,
) -> None:
    rec = PackageRecord(
        name=name,
        version=version,
        build=build,
        build_number=0,
        channel=Channel("conda-forge"),
        subdir="linux-64",
        fn=f"{name}-{version}-{build}.conda",
    )
    assert rec.spec == expected_spec
    assert rec.spec_no_build == expected_no_build


def test_spec_strings_vs_str() -> None:
    rec = PackageRecord(
        name="scipy",
        version="1.7.0",
        build="py39_1",
        build_number=1,
        channel=Channel("conda-forge"),
        subdir="osx-64",
        fn="scipy-1.7.0-py39_1.conda",
    )
    assert rec.spec == "scipy=1.7.0=py39_1"
    assert rec.spec_no_build == "scipy=1.7.0"
    assert str(rec) == "conda-forge/osx-64::scipy==1.7.0=py39_1"
    assert rec.spec != str(rec)


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
def test_spec_strings_inheritance(
    record_class: type[PackageRecord],
    extra_kwargs: dict[str, Any],
) -> None:
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
    assert rec.spec == "requests=2.25.1=pyhd3eb1b0_0"
    assert rec.spec_no_build == "requests=2.25.1"


def test_cross_subclass_equality() -> None:
    kwargs: dict[str, Any] = dict(
        name="x",
        version="1",
        build="0",
        build_number=0,
        channel="@",
        subdir="linux-64",
    )
    pr = PackageRecord(**kwargs)
    sr = SolvedRecord(**kwargs)
    pfx = PrefixRecord(**kwargs)
    assert pr == sr == pfx
    assert hash(pr) == hash(sr) == hash(pfx)
    assert sr in {pr}
    assert pfx in {pr, sr}


def test_invalidate_pkey() -> None:
    rec = PackageRecord(
        name="a",
        version="1",
        build="0",
        build_number=0,
        channel="@",
        subdir="linux-64",
    )
    h1 = hash(rec)
    rec.invalidate_pkey()
    object.__setattr__(rec, "channel", Channel("conda-forge"))
    assert hash(rec) != h1


def test_from_objects_dict() -> None:
    src: dict[str, Any] = {
        "name": "foo",
        "version": "1.0",
        "build": "py39",
        "build_number": 0,
        "channel": "defaults",
        "subdir": "linux-64",
    }
    rec = PackageRecord.from_objects(src)
    assert rec.name == "foo"
    assert rec.channel.canonical_name == Channel("defaults").canonical_name


def test_from_objects_entity() -> None:
    entity = PackageRecord(**COMMON_KWARGS)
    dc = PackageRecord.from_objects(entity)
    assert dc.name == entity.name
    assert dc._pkey == entity._pkey


def test_from_json() -> None:
    import json

    data: dict[str, Any] = {
        "name": "test",
        "version": "1",
        "build": "0",
        "build_number": 0,
        "channel": "@",
        "subdir": "linux-64",
    }
    rec = PackageRecord.from_json(json.dumps(data))
    assert rec.name == "test"


@pytest.mark.parametrize(
    "cls,extra_kwargs",
    [
        (PackageRecord, {}),
        (SolvedRecord, {"requested_spec": "numpy>=1.20"}),
        (PrefixRecord, {"files": ["lib/foo.py"], "md5": "abc123"}),
    ],
)
def test_round_trip(cls: type[PackageRecord], extra_kwargs: dict[str, Any]) -> None:
    kwargs: dict[str, Any] = {**COMMON_KWARGS, **extra_kwargs}
    rec = cls(**kwargs)
    dumped = rec.dump()
    rec2 = cls(**dumped)
    assert dict(rec2.dump()) == dict(dumped)


def test_alias_build_string() -> None:
    rec = PackageRecord(
        name="t",
        version="1",
        build_string="py39",
        build_number=0,
    )
    assert rec.build == "py39"


def test_alias_schannel() -> None:
    rec = PackageRecord(
        name="t",
        version="1",
        build="0",
        build_number=0,
        schannel="conda-forge",
    )
    assert isinstance(rec.channel, Channel)


def test_alias_filename() -> None:
    rec = PackageRecord(
        name="t",
        version="1",
        build="0",
        build_number=0,
        filename="test-1-0.conda",
    )
    assert rec.fn == "test-1-0.conda"


def test_noarch_coercion() -> None:
    rec = PackageRecord(
        name="t",
        version="1",
        build="0",
        build_number=0,
        noarch="python",
    )
    assert rec.noarch == NoarchType.python


def test_features_coercion_from_string() -> None:
    rec = PackageRecord(
        name="t",
        version="1",
        build="0",
        build_number=0,
        track_features="feat1 feat2",
    )
    assert rec.track_features == ("feat1", "feat2")


def test_features_coercion_from_list() -> None:
    rec = PackageRecord(
        name="t",
        version="1",
        build="0",
        build_number=0,
        track_features=["feat1", "feat2"],
    )
    assert rec.track_features == ("feat1", "feat2")


def test_depends_as_tuple() -> None:
    rec = PackageRecord(
        name="t",
        version="1",
        build="0",
        build_number=0,
        depends=["python >=3.9", "numpy"],
    )
    assert isinstance(rec.depends, tuple)
    assert rec.depends == ("python >=3.9", "numpy")


def test_channel_derived_from_url() -> None:
    rec = PackageRecord(
        name="austin",
        version="1.2.3",
        build="py34_2",
        build_number=2,
        url="https://repo.anaconda.com/pkgs/main/win-32/austin-1.2.3-py34_2.tar.bz2",
    )
    assert rec.channel is not None
    assert rec.channel.canonical_name == "defaults"
    assert rec.fn == "austin-1.2.3-py34_2.tar.bz2"


def test_subdir_derived_from_url() -> None:
    rec = PackageRecord(
        name="t",
        version="1",
        build="0",
        build_number=0,
        url="https://repo.anaconda.com/pkgs/main/win-32/t-1-0.tar.bz2",
    )
    assert rec.subdir == "win-32"


def test_effective_package_type_from_noarch() -> None:
    rec = PackageRecord(
        name="t",
        version="1",
        build="0",
        build_number=0,
        noarch="python",
    )
    assert rec.effective_package_type() == PackageType.NOARCH_PYTHON


def test_get_method() -> None:
    rec = PackageRecord(**COMMON_KWARGS)
    assert rec.get("version") == "1.21.0"
    assert rec.get("nonexistent", "default") == "default"
    assert rec.get("md5") is None


def test_solved_record_requested_specs() -> None:
    srec = SolvedRecord(
        name="n",
        version="1",
        build="0",
        build_number=0,
        requested_specs=["n>=1", "n"],
    )
    assert srec.requested_specs == ("n>=1", "n")
    d = srec.dump()
    assert "requested_specs" in d
    assert d["requested_specs"] == ["n>=1", "n"]


def test_solved_record_single_spec_fallback() -> None:
    srec = SolvedRecord(
        name="n",
        version="1",
        build="0",
        build_number=0,
        requested_spec="n>=1",
    )
    assert srec.requested_specs == ("n>=1",)
    d = srec.dump()
    assert d["requested_specs"] == ["n>=1"]


def test_prefix_record_files_coercion() -> None:
    prec = PrefixRecord(
        name="t",
        version="1",
        build="0",
        build_number=0,
        files=["lib/foo.py", "bin/bar"],
    )
    assert isinstance(prec.files, tuple)
    assert prec.files == ("lib/foo.py", "bin/bar")


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


@pytest.mark.parametrize(
    "name",
    [
        "NoarchField",
        "TimestampField",
        "_FeaturesField",
        "ChannelField",
        "SubdirField",
        "FilenameField",
        "PackageTypeField",
        "Md5Field",
    ],
)
def test_legacy_field_descriptors_are_deprecated(name: str) -> None:
    """Legacy ``auxlib.Entity`` field descriptors are importable with a warning."""
    import conda.models.records as records

    with pytest.warns(PendingDeprecationWarning, match=name):
        cls = getattr(records, name)
    assert isinstance(cls, type)
    assert cls.__module__ == "conda.models._legacy_record_fields"


@pytest.fixture
def pkg_tarball(tmp_path) -> Path:
    """Write a deterministic tarball file and return its path."""
    tarball = tmp_path / "pkg.tar.bz2"
    tarball.write_bytes(b"hello world")
    return tarball


@pytest.fixture
def cache_record_factory(pkg_tarball):
    """Build :class:`PackageCacheRecord` instances backed by ``pkg_tarball``."""

    def _make(**overrides) -> PackageCacheRecord:
        fields = dict(
            name="pkg",
            version="1.0",
            build="0",
            build_number=0,
            channel="@",
            subdir="noarch",
            package_tarball_full_path=str(pkg_tarball),
        )
        fields.update(overrides)
        return PackageCacheRecord(**fields)

    return _make


def test_package_cache_record_md5_auto_compute_is_deprecated(
    cache_record_factory,
) -> None:
    """Unset ``md5`` still returns the tarball hash but emits a deprecation."""
    record = cache_record_factory()

    with pytest.warns(PendingDeprecationWarning, match="calculate_md5sum"):
        value = record.md5

    assert value == "5eb63bbbe01eeed093cb22bb8f5acdc3"


@pytest.mark.parametrize(
    "initial, updated",
    [
        pytest.param("explicit", "new-value", id="preset-then-overwrite"),
        pytest.param(None, "assigned", id="unset-then-assign"),
    ],
)
def test_package_cache_record_md5_explicit_values_do_not_warn(
    cache_record_factory,
    recwarn,
    initial: str | None,
    updated: str,
) -> None:
    """Explicit md5 values short-circuit auto-compute and stay silent."""
    kwargs = {"md5": initial} if initial is not None else {}
    record = cache_record_factory(**kwargs)

    if initial is not None:
        assert record.md5 == initial

    record.md5 = updated
    assert record.md5 == updated
    assert not [
        w
        for w in recwarn.list
        if issubclass(w.category, (DeprecationWarning, PendingDeprecationWarning))
    ]
