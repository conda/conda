# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Keep the pixi dev environments in sync with tests/requirements*.txt."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
PIXI = tomllib.loads((REPO / "pyproject.toml").read_text())["tool"]["pixi"]

# python is pinned per pixi pyXYZ feature instead of by the requirements file
UNSYNCED = {"python"}


def read_requirements(name: str) -> dict[str, str]:
    """Map package name to normalized version spec for a requirements file."""
    requirements = {}
    for line in (REPO / "tests" / name).read_text().splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        # "conda-forge::xonsh" -> "xonsh"
        line = line.rpartition("::")[-1]
        pkg, spec = re.fullmatch(r"([\w.\-]+)\s*(.*)", line).groups()
        requirements[pkg] = spec.replace(" ", "") or "*"
    return requirements


def pixi_dependencies(table: dict) -> dict[str, str]:
    """Map package name to version spec for a pixi dependencies table."""
    return {
        pkg: (spec["version"] if isinstance(spec, dict) else spec)
        for pkg, spec in table.items()
    }


def pixi_feature_dependencies() -> dict[str, str]:
    """All dependencies of the version/channel/target tables (no s3/typing)."""
    tables = [
        feature.get("dependencies", {})
        for name, feature in PIXI["feature"].items()
        if name not in ("s3", "typing")
    ]
    tables += [target.get("dependencies", {}) for target in PIXI["target"].values()]
    return {
        pkg: spec for table in tables for pkg, spec in pixi_dependencies(table).items()
    }


COMMON = {**pixi_dependencies(PIXI["dependencies"]), **pixi_feature_dependencies()}


@pytest.mark.parametrize(
    "requirements",
    [
        pytest.param("requirements.txt", id="requirements"),
        pytest.param("requirements-ci.txt", id="ci"),
        pytest.param("requirements-Linux.txt", id="linux"),
        pytest.param("requirements-Windows.txt", id="windows"),
        pytest.param("requirements-s3.txt", id="s3"),
        pytest.param("requirements-typing.txt", id="typing"),
    ],
)
def test_requirements_in_pixi(requirements: str) -> None:
    pixi = {
        **COMMON,
        **pixi_dependencies(PIXI["feature"]["s3"]["dependencies"]),
        **pixi_dependencies(PIXI["feature"]["typing"]["dependencies"]),
    }
    for pkg, spec in read_requirements(requirements).items():
        if pkg in UNSYNCED:
            continue
        assert pkg in pixi, f"{pkg} from {requirements} missing from [tool.pixi]"
        assert pixi[pkg] == spec, f"{pkg}: {pixi[pkg]!r} != {spec!r} ({requirements})"


def test_pixi_in_requirements() -> None:
    required = {
        pkg
        for name in (
            "requirements.txt",
            "requirements-ci.txt",
            "requirements-Linux.txt",
            "requirements-Windows.txt",
            "requirements-s3.txt",
            "requirements-typing.txt",
        )
        for pkg in read_requirements(name)
    }
    extra = set(COMMON) - required - UNSYNCED
    assert not extra, f"in [tool.pixi] but not in tests/requirements*.txt: {extra}"


@pytest.mark.parametrize(
    "pixi_condarc,ci_condarc",
    [
        pytest.param("condarc-main.yml", "condarc-defaults", id="main"),
        pytest.param(
            "condarc-conda-forge.yml", "condarc-conda-forge", id="conda-forge"
        ),
    ],
)
def test_condarc_matches_ci(pixi_condarc: str, ci_condarc: str) -> None:
    pixi = (REPO / "dev" / "pixi" / pixi_condarc).read_text()
    ci = (REPO / ".github" / ci_condarc).read_text()
    assert pixi == ci, f"dev/pixi/{pixi_condarc} differs from .github/{ci_condarc}"


def test_environments_use_one_channel() -> None:
    for name, env in PIXI["environments"].items():
        channels = {"main", "conda-forge"} & set(env["features"])
        assert len(channels) == 1, f"{name} must use exactly one channel feature"
        pythons = [f for f in env["features"] if re.fullmatch(r"py3\d+", f)]
        assert len(pythons) == 1, f"{name} must use exactly one python feature"
