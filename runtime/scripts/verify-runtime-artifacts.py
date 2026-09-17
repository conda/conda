#!/usr/bin/env python3
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Validate collected runtime release and update package files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZipInfo

TARGETS = {
    "linux-64": "x86_64-unknown-linux-gnu",
    "linux-aarch64": "aarch64-unknown-linux-gnu",
    "osx-64": "x86_64-apple-darwin",
    "osx-arm64": "aarch64-apple-darwin",
    "win-64": "x86_64-pc-windows-msvc.exe",
}
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
INSTALLER_TEMPLATES = {
    "install.sh": REPOSITORY_ROOT / "installers/install.sh.in",
    "install.ps1": REPOSITORY_ROOT / "installers/install.ps1.in",
}
VERSION_PATTERN = re.compile(r"[0-9]+[.][0-9]+[.][0-9]+(?:[.]post[0-9]+)?")
VERSION_TOKEN = "@CONDA_RUNTIME_VERSION@"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_installers(version: str) -> dict[str, bytes]:
    rendered: dict[str, bytes] = {}
    for asset_name, template_path in INSTALLER_TEMPLATES.items():
        template = template_path.read_text(encoding="utf-8")
        if template.count(VERSION_TOKEN) != 1:
            raise SystemExit(
                f"{template_path} must contain exactly one {VERSION_TOKEN} token"
            )
        rendered[asset_name] = template.replace(VERSION_TOKEN, version).encode("utf-8")
    return rendered


def archive_build_records(root: Path) -> bytes:
    expected = {
        Path(subdir) / name
        for subdir, target in TARGETS.items()
        for name in (
            "pixi.toml",
            "pixi.lock",
            f"conda-{target.removesuffix('.exe')}.runtime.lock",
        )
    }
    actual = {
        path.relative_to(root)
        for path in root.rglob("*")
        if not path.is_dir() or path.is_symlink()
    }
    if actual != expected or any((root / path).is_symlink() for path in expected):
        raise SystemExit(
            "build records must contain exactly the three files for each platform"
        )
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        for relative in sorted(expected):
            info = ZipInfo(relative.as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (root / relative).read_bytes())
    return output.getvalue()


def require_object(value: object, name: str, path: Path) -> dict[str, object]:
    if not isinstance(value, dict):
        raise SystemExit(f"{path} must contain a {name} object")
    return value


def validate_sbom(
    path: Path,
    version: str,
    subdir: str,
    executable_name: str,
) -> None:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SystemExit(f"could not read CycloneDX SBOM {path}: {error}") from error

    document = require_object(document, "CycloneDX document", path)
    expected_header = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.7",
        "version": 1,
    }
    for field, expected in expected_header.items():
        if document.get(field) != expected:
            raise SystemExit(
                f"{path} has unexpected {field}: expected {expected!r}, "
                f"received {document.get(field)!r}"
            )

    metadata = require_object(document.get("metadata"), "metadata", path)
    component = require_object(metadata.get("component"), "metadata.component", path)
    expected_component = {
        "type": "application",
        "name": "conda",
        "version": version,
    }
    for field, expected in expected_component.items():
        if component.get(field) != expected:
            raise SystemExit(
                f"{path} has unexpected metadata.component.{field}: "
                f"expected {expected!r}, received {component.get(field)!r}"
            )

    properties = component.get("properties")
    if not isinstance(properties, list):
        raise SystemExit(f"{path} must contain metadata.component.properties")
    property_values = {
        item.get("name"): item.get("value")
        for item in properties
        if isinstance(item, dict)
    }
    expected_properties = {
        "conda-ship:runtime:name": "conda",
        "conda-ship:artifact:filename": executable_name,
        "conda-ship:artifact:layout": "embedded",
        "conda-ship:target:platform": subdir,
        "conda-ship:sbom:scope": "resolved-conda-packages",
    }
    for name, expected in expected_properties.items():
        if property_values.get(name) != expected:
            raise SystemExit(
                f"{path} has unexpected {name}: expected {expected!r}, "
                f"received {property_values.get(name)!r}"
            )

    components = document.get("components")
    if not isinstance(components, list) or not components:
        raise SystemExit(f"{path} must contain resolved conda package components")
    component_references = set()
    for component_index, package in enumerate(components):
        if not isinstance(package, dict):
            raise SystemExit(f"{path} component {component_index} must be an object")
        if not isinstance(package.get("name"), str) or not package["name"]:
            raise SystemExit(f"{path} component {component_index} must have a name")
        if not isinstance(package.get("version"), str) or not package["version"]:
            raise SystemExit(f"{path} component {component_index} must have a version")
        purl = package.get("purl")
        if not isinstance(purl, str) or not purl.startswith("pkg:conda/"):
            raise SystemExit(
                f"{path} component {component_index} must have a conda package URL"
            )
        component_reference = package.get("bom-ref")
        if not isinstance(component_reference, str):
            raise SystemExit(f"{path} component {component_index} must have a bom-ref")
        if component_reference in component_references:
            raise SystemExit(f"{path} contains duplicate component references")
        component_references.add(component_reference)

    dependencies = document.get("dependencies")
    if not isinstance(dependencies, list) or not dependencies:
        raise SystemExit(f"{path} must contain conda package dependency relationships")

    root_reference = component.get("bom-ref")
    if not isinstance(root_reference, str):
        raise SystemExit(f"{path} metadata.component must have a bom-ref")
    dependency_edges = {}
    dependency_targets = set()
    for dependency_index, dependency in enumerate(dependencies):
        if not isinstance(dependency, dict):
            raise SystemExit(f"{path} dependency {dependency_index} must be an object")
        dependency_reference = dependency.get("ref")
        depends_on = dependency.get("dependsOn")
        if not isinstance(dependency_reference, str) or not isinstance(
            depends_on, list
        ):
            raise SystemExit(
                f"{path} dependency {dependency_index} must have ref and dependsOn"
            )
        if not all(isinstance(target, str) for target in depends_on):
            raise SystemExit(
                f"{path} dependency {dependency_index} has a non-string target"
            )
        if dependency_reference in dependency_edges:
            raise SystemExit(f"{path} contains duplicate dependency references")
        dependency_edges[dependency_reference] = set(depends_on)
        dependency_targets.update(depends_on)

    expected_dependency_references = component_references | {root_reference}
    if set(dependency_edges) != expected_dependency_references:
        raise SystemExit(
            f"{path} dependency entries must cover the runtime and every component"
        )
    if not dependency_edges[root_reference]:
        raise SystemExit(f"{path} runtime dependency entry must reference a component")
    unknown_targets = dependency_targets - component_references
    if unknown_targets:
        raise SystemExit(
            f"{path} dependencies contain unknown component references: "
            f"{sorted(unknown_targets)!r}"
        )

    compositions = document.get("compositions")
    if not isinstance(compositions, list):
        raise SystemExit(f"{path} must describe its incomplete inventory coverage")
    if not any(
        isinstance(composition, dict)
        and composition.get("aggregate") == "incomplete"
        and isinstance(composition.get("assemblies"), list)
        and root_reference in composition["assemblies"]
        for composition in compositions
    ):
        raise SystemExit(f"{path} must mark the runtime inventory as incomplete")


def verify_runtime_artifacts(
    root: Path,
    version: str,
    *,
    write_checksums: bool = False,
) -> None:
    if VERSION_PATTERN.fullmatch(version) is None:
        raise SystemExit(
            "runtime versions must use X.Y.Z or X.Y.Z.postN, such as 26.5.3"
        )

    release_dir = root / "release-assets"
    package_dir = root / "update-packages"
    generated_assets = render_installers(version)
    generated_assets["conda-build-records.zip"] = archive_build_records(
        root / "build-records"
    )
    if write_checksums:
        for asset_name, contents in generated_assets.items():
            (release_dir / asset_name).write_bytes(contents)

    executables = {subdir: f"conda-{target}" for subdir, target in TARGETS.items()}
    sboms = {
        subdir: f"{executable.removesuffix('.exe')}.cdx.json"
        for subdir, executable in executables.items()
    }
    expected_assets = {
        *executables.values(),
        *sboms.values(),
        *generated_assets,
    }
    expected_packages = {
        Path(subdir) / f"conda-runtime-{version}-0.conda" for subdir in TARGETS
    }

    actual_assets = {
        path.name
        for path in release_dir.iterdir()
        if path.is_file() and path.name != "SHA256SUMS"
    }
    actual_packages = {
        path.relative_to(package_dir)
        for path in package_dir.rglob("*")
        if path.is_file()
    }

    if actual_assets != expected_assets:
        raise SystemExit(
            f"unexpected release assets: expected {sorted(expected_assets)!r}, "
            f"received {sorted(actual_assets)!r}"
        )
    for asset_name, contents in generated_assets.items():
        if (release_dir / asset_name).read_bytes() != contents:
            raise SystemExit(
                f"{asset_name} does not match the generated release contents"
            )
    for subdir, sbom_name in sboms.items():
        validate_sbom(
            release_dir / sbom_name,
            version,
            subdir,
            executables[subdir],
        )
    if actual_packages != expected_packages:
        raise SystemExit(
            "unexpected update packages: expected "
            f"{sorted(map(str, expected_packages))!r}, received "
            f"{sorted(map(str, actual_packages))!r}"
        )

    checksum_path = release_dir / "SHA256SUMS"
    lines = [
        f"{sha256(release_dir / name)}  {name}\n" for name in sorted(expected_assets)
    ]
    expected_checksums = "".join(lines)
    if write_checksums:
        checksum_path.write_text(expected_checksums, encoding="utf-8")
    elif (
        not checksum_path.is_file()
        or checksum_path.read_text(encoding="utf-8") != expected_checksums
    ):
        raise SystemExit("SHA256SUMS does not match the release assets")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("version")
    parser.add_argument("--write-checksums", action="store_true")
    args = parser.parse_args()
    verify_runtime_artifacts(
        args.root,
        args.version,
        write_checksums=args.write_checksums,
    )


if __name__ == "__main__":
    main()
