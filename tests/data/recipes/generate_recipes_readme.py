#!/usr/bin/env python3
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Generate a test-recipes README from rendered package metadata.

This reads package metadata from artifacts in ``tests/data/test-recipes``:
- ``info/index.json`` for package name and version (source of truth)
- ``info/recipe/meta.yaml`` for ``extra.test_purpose`` when present

Supports ``*.tar.bz2`` packages and ``*.conda`` packages (``info-*.tar.zst``).
"""

from __future__ import annotations

import json
import sys
import tarfile
import zipfile
from dataclasses import dataclass
from itertools import groupby
from pathlib import Path
from typing import TYPE_CHECKING

try:
    import yaml  # type: ignore[import-not-found]
except ModuleNotFoundError:
    raise ImportError(
        "PyYAML is required to parse recipe metadata. "
        "Run via pre-commit or install pyyaml."
    )

if sys.version_info < (3, 14):
    raise ImportError(
        "Python 3.14+ is required to parse .conda package metadata. "
        "Run via pre-commit or install Python 3.14+."
    )

if TYPE_CHECKING:
    from collections.abc import Iterator

RECIPES_ROOT = Path(__file__).parent
CHANNEL_ROOT = RECIPES_ROOT.parent / "test-recipes"
README = RECIPES_ROOT / "README.md"
UNKNOWN = "-"

# Paths inside the package info archive (normalize leading "./").
_META_PATH = "info/recipe/meta.yaml"
_INDEX_PATH = "info/index.json"


@dataclass(frozen=True)
class RecipeInfo:
    artifact: str
    subdir: str
    package: str | None
    version: str | None
    purpose: str | None


def _normalize(value: object) -> str | None:
    if value is None:
        return None
    return " ".join(str(value).split())


def _member_name(name: str) -> str:
    return name[2:] if name.startswith("./") else name


def _extract_info(tf: tarfile.TarFile) -> tuple[str | None, str | None]:
    """Return ``(meta.yaml text, index.json text)`` from a package info tar."""
    meta_yaml = None
    index_json = None
    for member in tf:
        name = _member_name(member.name)
        if name == _META_PATH and meta_yaml is None:
            stream = tf.extractfile(member)
            meta_yaml = stream.read().decode("utf-8") if stream else None
        elif name == _INDEX_PATH and index_json is None:
            stream = tf.extractfile(member)
            index_json = stream.read().decode("utf-8") if stream else None
        if meta_yaml is not None and index_json is not None:
            break
    return meta_yaml, index_json


def _read_info_from_tar_bz2(artifact: Path) -> tuple[str | None, str | None]:
    # .tar.bz2 is a tarfile of files
    with tarfile.open(artifact, mode="r|bz2") as tf:
        return _extract_info(tf)


def _read_info_from_conda(artifact: Path) -> tuple[str | None, str | None]:
    # .conda is a zipfile of tar.zst files
    with zipfile.ZipFile(artifact) as zf:
        try:
            name = next(
                name
                for name in zf.namelist()
                if name.startswith("info-") and name.endswith(".tar.zst")
            )
        except StopIteration:
            return None, None
        with zf.open(name) as stream, tarfile.open(fileobj=stream, mode="r|zst") as tf:
            return _extract_info(tf)


def _read_package_info(artifact: Path) -> tuple[str | None, str | None]:
    if not artifact.is_file():
        return None, None
    elif artifact.name.endswith(".conda"):
        return _read_info_from_conda(artifact)
    elif artifact.name.endswith(".tar.bz2"):
        return _read_info_from_tar_bz2(artifact)
    return None, None


def _parse_artifact(artifact: Path) -> RecipeInfo | None:
    if not (artifact.name.endswith(".conda") or artifact.name.endswith(".tar.bz2")):
        return None

    meta_yaml_text, index_json_text = _read_package_info(artifact)

    package_name = None
    version = None
    purpose = None

    if index_json_text:
        try:
            index = json.loads(index_json_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse index.json in {artifact.name}") from exc
        if isinstance(index, dict):
            package_name = _normalize(index.get("name"))
            version = _normalize(index.get("version"))

    if meta_yaml_text:
        try:
            parsed = yaml.safe_load(meta_yaml_text) or {}
        except yaml.YAMLError as exc:
            raise ValueError(
                f"Failed to parse rendered recipe metadata in {artifact.name}"
            ) from exc

        if not isinstance(parsed, dict):
            parsed = {}

        # Prefer index.json for name/version; fall back to recipe metadata.
        package = parsed.get("package")
        if isinstance(package, dict):
            package_name = package_name or _normalize(package.get("name"))
            version = version or _normalize(package.get("version"))

        extra = parsed.get("extra")
        if isinstance(extra, dict):
            purpose = _normalize(extra.get("test_purpose"))

    if not package_name:
        # skip package if package_name cannot be determined
        print(
            f"warning: skipping {artifact.relative_to(CHANNEL_ROOT.parent)}: "
            f"missing {_META_PATH} and {_INDEX_PATH}",
            file=sys.stderr,
        )
        return None
    elif not meta_yaml_text:
        # warn that meta.yaml is not included in the package
        print(
            f"warning: skipping {artifact.relative_to(CHANNEL_ROOT.parent)}: "
            f"missing {_META_PATH} (fallback to {_INDEX_PATH})",
            file=sys.stderr,
        )

    return RecipeInfo(
        artifact=artifact.name,
        subdir=artifact.parent.name,
        package=package_name,
        version=version,
        purpose=purpose,
    )


def _generate_readme(grouped: list[list[RecipeInfo]]) -> Iterator[str]:
    yield "# Test Recipes"
    yield ""
    yield "<!-- This file is generated by tests/data/recipes/generate_recipes_readme.py -->"
    yield "<!-- Run: python tests/data/recipes/generate_recipes_readme.py -->"
    yield ""
    yield "Overview of package artifacts and their intended purpose."
    yield ""
    yield "| Package | Version | Subdirs | Purpose |"
    yield "| --- | --- | --- | --- |"
    details = []
    for recipes in grouped:
        if not recipes:
            continue
        versions = "<br>".join(
            f"`{version}`"
            for version in sorted(
                {recipe.version for recipe in recipes if recipe.version}
            )
        )
        subdirs = "<br>".join(
            f"`{subdir}`" for subdir in sorted({recipe.subdir for recipe in recipes})
        )
        recipe = recipes[0]
        link = ""
        if purpose := list(
            {recipe.purpose: recipe for recipe in recipes if recipe.purpose}.values()
        ):
            details.append(purpose)
            link = f"[#{recipe.package}](#{recipe.package})"
        yield f"| `{recipe.package}` | {versions} | {subdirs} | {link} |"
    yield ""
    for recipes in details:
        yield f"## {recipes[0].package}"
        for recipe in recipes:
            if len(recipes) > 1:
                yield f"### `{recipe.version}` `{recipe.subdir}`"
            yield f"{recipe.purpose}"
        yield ""


def main() -> int:
    recipes = sorted(
        (
            info
            for subdir in next(CHANNEL_ROOT.walk())[1]
            for artifact in (CHANNEL_ROOT / subdir).iterdir()
            if (info := _parse_artifact(artifact))
        ),
        key=lambda recipe: recipe.artifact,
    )
    grouped = [
        list(recipes)
        for _, recipes in groupby(recipes, key=lambda recipe: recipe.package)
    ]
    rendered = "\n".join(_generate_readme(grouped))
    README.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
