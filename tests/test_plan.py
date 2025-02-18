# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.base.context import context, reset_context
from conda.core.solve import get_pinned_specs
from conda.models.match_spec import MatchSpec

if TYPE_CHECKING:
    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture

    from conda.testing.fixtures import CondaCLIFixture, TmpEnvFixture


def test_pinned_specs_CONDA_PINNED_PACKAGES(monkeypatch: MonkeyPatch) -> None:
    # Test pinned specs environment variable
    specs = ("numpy 1.11", "python >3")

    monkeypatch.setenv("CONDA_PINNED_PACKAGES", "&".join(specs))
    reset_context()
    assert context.pinned_packages == specs

    pinned_specs = get_pinned_specs("/none")
    assert pinned_specs != specs
    assert pinned_specs == tuple(MatchSpec(spec, optional=True) for spec in specs)


def test_pinned_specs_conda_meta_pinned(tmp_env: TmpEnvFixture):
    # Test pinned specs conda environment file
    specs = ("scipy ==0.14.2", "openjdk >=8")
    with tmp_env() as prefix:
        (prefix / "conda-meta" / "pinned").write_text("\n".join(specs) + "\n")

        pinned_specs = get_pinned_specs(prefix)
        assert pinned_specs != specs
        assert pinned_specs == tuple(MatchSpec(spec, optional=True) for spec in specs)


def test_pinned_specs_condarc(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
):
    # Test pinned specs conda environment file
    specs = ("requests ==2.13",)
    with tmp_env() as prefix:
        # mock active prefix
        mocker.patch(
            "conda.base.context.Context.active_prefix",
            new_callable=mocker.PropertyMock,
            return_value=str(prefix),
        )

        conda_cli("config", "--env", "--add", "pinned_packages", *specs)

        pinned_specs = get_pinned_specs(prefix)
        assert pinned_specs != specs
        assert pinned_specs == tuple(MatchSpec(spec, optional=True) for spec in specs)


def test_pinned_specs_all(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    # Test pinned specs conda configuration and pinned specs conda environment file
    specs1 = ("numpy 1.11", "python >3")
    specs2 = ("scipy ==0.14.2", "openjdk >=8")
    specs3 = ("requests=2.13",)
    specs = (*specs1, *specs3, *specs2)

    monkeypatch.setenv("CONDA_PINNED_PACKAGES", "&".join(specs1))
    reset_context()
    assert context.pinned_packages == specs1

    with tmp_env() as prefix:
        (prefix / "conda-meta" / "pinned").write_text("\n".join(specs2) + "\n")

        # mock active prefix
        mocker.patch(
            "conda.base.context.Context.active_prefix",
            new_callable=mocker.PropertyMock,
            return_value=str(prefix),
        )

        conda_cli("config", "--env", "--add", "pinned_packages", *specs3)

        pinned_specs = get_pinned_specs(prefix)
        assert pinned_specs != specs
        assert pinned_specs == tuple(MatchSpec(spec, optional=True) for spec in specs)


@pytest.mark.parametrize(
    "constant",
    [
        None,  # ensure module is deprecated
        "sys",
        "defaultdict",
        "log",
        "IndexedSet",
        "DEFAULTS_CHANNEL_NAME",
        "UNKNOWN_CHANNEL",
        "context",
        "reset_context",
        "TRACE",
        "dashlist",
        "env_vars",
        "time_recorder",
        "groupby",
        "LAST_CHANNEL_URLS",
        "PrefixSetup",
        "UnlinkLinkTransaction",
        "FETCH",
        "LINK",
        "SYMLINK_CONDA",
        "UNLINK",
        "Channel",
        "prioritize_channels",
        "Dist",
        "LinkType",
        "MatchSpec",
        "PackageRecord",
        "normalized_version",
        "human_bytes",
        "log",
    ],
)
def test_deprecations(constant: str | None) -> None:
    with pytest.deprecated_call():
        import conda.plan

        if constant:
            getattr(conda.plan, constant)
