# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

SCRIPT_PATH = Path(__file__).parents[1] / "scripts/verify-runtime-artifacts.py"
SPEC = importlib.util.spec_from_file_location("verify_runtime_artifacts", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
runtime_artifacts = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime_artifacts
SPEC.loader.exec_module(runtime_artifacts)

RUNTIME_VERSION = "26.7.1.post3"


def sbom_document(version: str, subdir: str, executable_name: str) -> dict:
    root_reference = f"runtime:conda@{version}?platform={subdir}"
    package_reference = f"pkg:conda/conda@26.7.1?build=py312_0&channel=conda-forge&subdir={subdir}&type=conda"
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.7",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "bom-ref": root_reference,
                "name": "conda",
                "version": version,
                "properties": [
                    {"name": "conda-ship:runtime:name", "value": "conda"},
                    {
                        "name": "conda-ship:artifact:filename",
                        "value": executable_name,
                    },
                    {"name": "conda-ship:artifact:layout", "value": "embedded"},
                    {"name": "conda-ship:target:platform", "value": subdir},
                    {
                        "name": "conda-ship:sbom:scope",
                        "value": "resolved-conda-packages",
                    },
                ],
            }
        },
        "components": [
            {
                "type": "library",
                "bom-ref": package_reference,
                "name": "conda",
                "version": "26.7.1",
                "purl": package_reference,
            }
        ],
        "dependencies": [
            {"ref": root_reference, "dependsOn": [package_reference]},
            {"ref": package_reference, "dependsOn": []},
        ],
        "compositions": [
            {
                "aggregate": "incomplete",
                "assemblies": [root_reference],
                "dependencies": [root_reference],
            }
        ],
    }


def staged_distribution(tmp_path: Path, version: str = RUNTIME_VERSION) -> Path:
    root = tmp_path / "staged"
    release_dir = root / "release-assets"
    package_dir = root / "update-packages"
    release_dir.mkdir(parents=True)

    for subdir, target in runtime_artifacts.TARGETS.items():
        executable_name = f"conda-{target}"
        executable = release_dir / executable_name
        executable.write_bytes(f"runtime for {subdir}".encode())

        sbom_name = f"{executable_name.removesuffix('.exe')}.cdx.json"
        (release_dir / sbom_name).write_text(
            json.dumps(sbom_document(version, subdir, executable_name)),
            encoding="utf-8",
        )

        package = package_dir / subdir / f"conda-runtime-{version}-0.conda"
        package.parent.mkdir(parents=True)
        package.write_bytes(f"package for {subdir}".encode())
        records = root / "build-records" / subdir
        records.mkdir(parents=True)
        (records / "pixi.toml").write_text('[workspace]\nname = "conda-runtime"\n')
        (records / "pixi.lock").write_text("version: 6\n")
        (records / f"{executable_name.removesuffix('.exe')}.runtime.lock").write_text(
            "version: 1\n"
        )

    return root


def test_complete_distribution_includes_sboms_in_checksums(tmp_path: Path):
    root = staged_distribution(tmp_path)

    runtime_artifacts.verify_runtime_artifacts(
        root,
        RUNTIME_VERSION,
        write_checksums=True,
    )

    checksum_lines = (root / "release-assets/SHA256SUMS").read_text().splitlines()
    assert len(checksum_lines) == 13
    assert sum(line.endswith(".cdx.json") for line in checksum_lines) == 5


def test_distribution_requires_every_platform_sbom(tmp_path: Path):
    root = staged_distribution(tmp_path)
    (root / "release-assets/conda-aarch64-apple-darwin.cdx.json").unlink()

    with pytest.raises(SystemExit, match="unexpected release assets"):
        runtime_artifacts.verify_runtime_artifacts(
            root,
            RUNTIME_VERSION,
            write_checksums=True,
        )


def test_distribution_rejects_unexpected_windows_update_source(tmp_path: Path):
    root = staged_distribution(tmp_path)
    windows = root / "update-packages/win-64"
    (windows / f"conda-runtime-{RUNTIME_VERSION}-0.conda").rename(
        windows / f"other-runtime-{RUNTIME_VERSION}-0.conda"
    )

    with pytest.raises(SystemExit, match="unexpected update packages"):
        runtime_artifacts.verify_runtime_artifacts(
            root,
            RUNTIME_VERSION,
            write_checksums=True,
        )


def test_distribution_rejects_mislabeled_sbom(tmp_path: Path):
    root = staged_distribution(tmp_path)
    sbom_path = root / "release-assets/conda-x86_64-pc-windows-msvc.cdx.json"
    sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
    sbom["metadata"]["component"]["version"] = "26.7.1"
    sbom_path.write_text(json.dumps(sbom), encoding="utf-8")

    with pytest.raises(SystemExit, match="metadata.component.version"):
        runtime_artifacts.verify_runtime_artifacts(
            root,
            RUNTIME_VERSION,
            write_checksums=True,
        )


def test_distribution_requires_explicit_incomplete_coverage(tmp_path: Path):
    root = staged_distribution(tmp_path)
    sbom_path = root / "release-assets/conda-x86_64-unknown-linux-gnu.cdx.json"
    sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
    sbom["compositions"] = []
    sbom_path.write_text(json.dumps(sbom), encoding="utf-8")

    with pytest.raises(SystemExit, match="mark the runtime inventory as incomplete"):
        runtime_artifacts.verify_runtime_artifacts(
            root,
            RUNTIME_VERSION,
            write_checksums=True,
        )


def test_distribution_rejects_unknown_dependency_target(tmp_path: Path):
    root = staged_distribution(tmp_path)
    sbom_path = root / "release-assets/conda-x86_64-unknown-linux-gnu.cdx.json"
    sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
    sbom["dependencies"][0]["dependsOn"] = ["pkg:conda/missing@1.0"]
    sbom_path.write_text(json.dumps(sbom), encoding="utf-8")

    with pytest.raises(SystemExit, match="unknown component references"):
        runtime_artifacts.verify_runtime_artifacts(
            root,
            RUNTIME_VERSION,
            write_checksums=True,
        )


def test_distribution_requires_runtime_dependency_root(tmp_path: Path):
    root = staged_distribution(tmp_path)
    sbom_path = root / "release-assets/conda-x86_64-unknown-linux-gnu.cdx.json"
    sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
    sbom["dependencies"][0]["dependsOn"] = []
    sbom_path.write_text(json.dumps(sbom), encoding="utf-8")

    with pytest.raises(SystemExit, match="must reference a component"):
        runtime_artifacts.verify_runtime_artifacts(
            root,
            RUNTIME_VERSION,
            write_checksums=True,
        )


def test_checksums_detect_modified_executable(tmp_path: Path):
    root = staged_distribution(tmp_path)
    runtime_artifacts.verify_runtime_artifacts(
        root, RUNTIME_VERSION, write_checksums=True
    )
    runtime_artifacts.verify_runtime_artifacts(root, RUNTIME_VERSION)
    (root / "release-assets/conda-aarch64-apple-darwin").write_bytes(b"changed")

    with pytest.raises(SystemExit, match="SHA256SUMS"):
        runtime_artifacts.verify_runtime_artifacts(root, RUNTIME_VERSION)


def test_build_records_archive_is_complete_and_deterministic(tmp_path: Path):
    root = staged_distribution(tmp_path)
    runtime_artifacts.verify_runtime_artifacts(
        root, RUNTIME_VERSION, write_checksums=True
    )
    archive_path = root / "release-assets/conda-build-records.zip"
    contents = archive_path.read_bytes()
    with ZipFile(archive_path) as archive:
        assert len(archive.namelist()) == 15
        assert archive.namelist() == sorted(archive.namelist())
        for entry in archive.infolist():
            assert entry.date_time == (1980, 1, 1, 0, 0, 0)
            assert entry.external_attr >> 16 == 0o100644
            assert (
                archive.read(entry)
                == (root / "build-records" / entry.filename).read_bytes()
            )
    for path in (root / "build-records").rglob("*"):
        if path.is_file():
            path.touch()
    runtime_artifacts.verify_runtime_artifacts(
        root, RUNTIME_VERSION, write_checksums=True
    )
    assert archive_path.read_bytes() == contents


@pytest.mark.parametrize("changed", ["archive", "records"])
def test_build_records_archive_rejects_changed_contents(tmp_path: Path, changed: str):
    root = staged_distribution(tmp_path)
    runtime_artifacts.verify_runtime_artifacts(
        root, RUNTIME_VERSION, write_checksums=True
    )
    if changed == "archive":
        with ZipFile(root / "release-assets/conda-build-records.zip", "a") as archive:
            archive.writestr("unexpected.lock", "changed")
    else:
        (root / "build-records/linux-64/pixi.lock").write_text("changed")
    with pytest.raises(SystemExit, match="conda-build-records.zip does not match"):
        runtime_artifacts.verify_runtime_artifacts(root, RUNTIME_VERSION)


@pytest.mark.parametrize("changed", ["missing", "extra"])
def test_build_records_require_exact_platform_files(tmp_path: Path, changed: str):
    root = staged_distribution(tmp_path)
    path = root / "build-records/win-64/pixi.lock"
    if changed == "missing":
        path.unlink()
    else:
        path.with_name("unexpected.lock").write_text("unexpected")
    with pytest.raises(SystemExit, match="build records must contain exactly"):
        runtime_artifacts.verify_runtime_artifacts(
            root, RUNTIME_VERSION, write_checksums=True
        )
