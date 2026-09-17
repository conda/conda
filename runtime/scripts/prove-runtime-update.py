#!/usr/bin/env python3
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Prove standalone conda runtime updates against one temporary channel."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import tomllib
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlsplit

from conda_runtime_updater.helper import invoke_helper, validate_check
from conda_runtime_updater.locking import acquire_lock, release_lock
from conda_runtime_updater.metadata import discover_runtime
from ruamel.yaml import YAML

from conda.models.match_spec import MatchSpec

if TYPE_CHECKING:
    from typing import Any, BinaryIO

    from conda_runtime_updater.metadata import RuntimeMetadata

OUTPUT_LIMIT = 2_000
COMPETING_CONDA_VERSION = "9999.0.0"


@dataclass(frozen=True)
class LockedPackage:
    url: str
    filename: str
    subdir: str
    sha256: str
    size: int | None


@dataclass(frozen=True)
class RuntimeBuild:
    binary: Path
    info: Path


@dataclass(frozen=True)
class Scenario:
    root: Path
    prefix: Path
    stable: Path
    envs: Path
    packages: Path
    platform: str


@dataclass(frozen=True)
class RuntimeState:
    executable_sha256: str
    metadata_sha256: str
    conda_metadata: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class GenerationVersions:
    runtime: str
    conda: str


def tail(value: str, limit: int = OUTPUT_LIMIT) -> str:
    value = value.strip()
    return value if len(value) <= limit else f"...{value[-limit:]}"


def format_command(command: list[str | os.PathLike[str]]) -> str:
    return subprocess.list2cmdline([os.fspath(part) for part in command])


def run(
    command: list[str | os.PathLike[str]],
    *,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    check: bool = True,
    timeout: int = 1_800,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [os.fspath(part) for part in command],
        capture_output=True,
        check=False,
        encoding="utf-8",
        env=env,
        input=input_text,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"command failed with exit code {result.returncode}: {format_command(command)}\n"
            f"stdout:\n{tail(result.stdout) or '<empty>'}\n"
            f"stderr:\n{tail(result.stderr) or '<empty>'}"
        )
    return result


def require_mapping(value: object, description: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError(f"{description} must be a mapping")
    return value


def require_list(value: object, description: str) -> list[Any]:
    if not isinstance(value, list):
        raise RuntimeError(f"{description} must be a list")
    return value


def package_url(record: dict[str, Any], description: str) -> str:
    value = record.get("conda")
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"{description} has no package URL")
    return value


def package_from_record(
    record: dict[str, Any], url: str, platform: str, lock_path: Path
) -> LockedPackage:
    parsed = urlsplit(url)
    if not parsed.scheme or (
        parsed.scheme not in {"https", "file"} and Path(url).is_absolute()
    ):
        url = (lock_path.parent / url).resolve().as_uri()
        parsed = urlsplit(url)
    if parsed.scheme not in {"https", "file"}:
        raise RuntimeError(
            f"source lock package is not HTTPS or a local archive: {url}"
        )
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeError(
            "source lock package URL contains credentials, a query, or a fragment"
        )
    filename = unquote(Path(parsed.path).name)
    if not filename.endswith((".conda", ".tar.bz2")):
        raise RuntimeError(f"source lock package has an invalid filename: {url}")
    subdir = record.get("subdir") or unquote(Path(parsed.path).parent.name)
    if subdir not in {"noarch", platform}:
        raise RuntimeError(
            f"source lock package has subdir {subdir!r}, expected 'noarch' or {platform!r}: {url}"
        )

    digest = record.get("sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise RuntimeError(f"source lock package has an invalid SHA-256 digest: {url}")
    size = record.get("size")
    if size is not None and (
        not isinstance(size, int) or isinstance(size, bool) or size < 1
    ):
        raise RuntimeError(f"source lock package has an invalid size: {url}")
    return LockedPackage(url, filename, subdir, digest, size)


def selected_packages(lock_path: Path, platform: str) -> list[LockedPackage]:
    data = require_mapping(YAML(typ="safe").load(lock_path), str(lock_path))
    if data.get("version") not in {6, 7}:
        raise RuntimeError(f"unsupported Pixi lock version in {lock_path}")

    environments = require_mapping(data.get("environments"), "lockfile environments")
    ship = require_mapping(environments.get("ship"), "lockfile ship environment")
    platform_packages = require_mapping(ship.get("packages"), "ship package platforms")
    references = require_list(
        platform_packages.get(platform), f"ship packages for platform {platform}"
    )
    records: dict[str, dict[str, Any]] = {}
    for index, value in enumerate(
        require_list(data.get("packages"), "lockfile packages")
    ):
        record = require_mapping(value, f"lockfile package {index}")
        url = package_url(record, f"lockfile package {index}")
        if url in records:
            raise RuntimeError(f"duplicate package URL in source lock: {url}")
        records[url] = record

    selected = []
    for index, value in enumerate(references):
        reference = require_mapping(value, f"ship package reference {index}")
        url = package_url(reference, f"ship package reference {index}")
        record = records.get(url)
        if record is None:
            raise RuntimeError(f"package reference has no trusted lock record: {url}")
        selected.append(package_from_record(record, url, platform, lock_path))
    if not selected:
        raise RuntimeError(f"source lock has no packages for {platform}: {lock_path}")
    return selected


def copy_runtime_root(source: Path, destination: Path, channel_uri: str) -> None:
    if not source.is_dir():
        raise RuntimeError(f"runtime root is missing: {source}")
    destination.mkdir()
    for name in ("pixi.toml", "pixi.lock", "runtime.condarc"):
        if (source / name).is_file():
            shutil.copy2(source / name, destination / name)
    rewrite_update_channel(destination / "pixi.toml", channel_uri)
    rewrite_condarc(destination / "runtime.condarc", channel_uri)


def runtime_version(root: Path) -> str:
    manifest = require_mapping(
        tomllib.loads((root / "pixi.toml").read_text(encoding="utf-8")),
        f"{root / 'pixi.toml'}",
    )
    tool = require_mapping(manifest.get("tool"), "manifest tool configuration")
    ship = require_mapping(tool.get("conda-ship"), "manifest conda-ship configuration")
    version = ship.get("runtime-version")
    if not isinstance(version, str) or not version:
        raise RuntimeError(f"runtime version is missing from {root / 'pixi.toml'}")
    return version


def rewrite_update_channel(manifest_path: Path, channel_uri: str) -> None:
    lines = manifest_path.read_text(encoding="utf-8").splitlines(keepends=True)
    section = ""
    replaced = False
    rendered = []
    for line in lines:
        match = re.match(r"^\s*\[([^]]+)]\s*$", line)
        if match:
            section = match.group(1)
        if section == "tool.conda-ship.update" and re.match(r"^\s*channel\s*=", line):
            newline = "\n" if line.endswith("\n") else ""
            line = f"channel = {json.dumps(channel_uri)}{newline}"
            replaced = True
        rendered.append(line)
    if not replaced:
        raise RuntimeError(f"update channel is missing from {manifest_path}")
    manifest_path.write_text("".join(rendered), encoding="utf-8")


def rewrite_condarc(condarc_path: Path, channel_uri: str) -> None:
    yaml = YAML()
    data = require_mapping(yaml.load(condarc_path), str(condarc_path))
    data["channels"] = [channel_uri]
    with condarc_path.open("w", encoding="utf-8") as stream:
        yaml.dump(data, stream)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(package: LockedPackage, destination: Path) -> None:
    temporary = destination.with_suffix(destination.suffix + ".part")
    digest = hashlib.sha256()
    size = 0
    request = urllib.request.Request(
        package.url, headers={"User-Agent": "conda-runtime-proof"}
    )
    try:
        with (
            urllib.request.urlopen(request, timeout=120) as response,
            temporary.open("wb") as stream,
        ):
            while chunk := response.read(1024 * 1024):
                stream.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        if package.size is not None and size != package.size:
            raise RuntimeError(
                f"package size mismatch for {package.url}: expected {package.size}, received {size}"
            )
        if digest.hexdigest() != package.sha256:
            raise RuntimeError(f"package SHA-256 mismatch for {package.url}")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def initialize_channel(channel: Path) -> None:
    noarch = channel / "noarch"
    noarch.mkdir(parents=True)
    repodata = {
        "info": {"subdir": "noarch"},
        "packages": {},
        "packages.conda": {},
        "removed": [],
        "repodata_version": 1,
    }
    (noarch / "repodata.json").write_text(json.dumps(repodata), encoding="utf-8")


def mirror_packages(
    channel: Path, channel_uri: str, packages: list[LockedPackage], staging: Path
) -> None:
    by_location: dict[tuple[str, str], LockedPackage] = {}
    for package in packages:
        location = (package.subdir, package.filename)
        previous = by_location.get(location)
        if previous is not None and previous.sha256 != package.sha256:
            raise RuntimeError(
                "package location has different content: "
                f"{package.subdir}/{package.filename}"
            )
        by_location.setdefault(location, package)

    staging.mkdir()
    archives = []
    for (subdir, filename), package in sorted(by_location.items()):
        archive = staging / subdir / filename
        archive.parent.mkdir(parents=True, exist_ok=True)
        download(package, archive)
        archives.append(archive)

    initialize_channel(channel)
    run(["rattler-build", "publish", "--to", channel_uri, *archives])
    for package in by_location.values():
        published = channel / package.subdir / package.filename
        if not published.is_file():
            raise RuntimeError(f"published package is missing: {published}")
        if (
            package.size is not None and published.stat().st_size != package.size
        ) or sha256(published) != package.sha256:
            raise RuntimeError(f"published package changed: {published}")


def publish_competing_conda(channel_uri: str, root: Path) -> None:
    recipe = root / "recipe.yaml"
    output = root / "output"
    root.mkdir()
    recipe.write_text(
        f"""\
package:
  name: conda
  version: {COMPETING_CONDA_VERSION}

build:
  number: 0
  string: runtime_pin_sentinel_0
  noarch: generic

about:
  summary: Test-only candidate used to prove standalone runtime version pinning
  license: BSD-3-Clause
""",
        encoding="utf-8",
    )
    run(
        [
            "rattler-build",
            "build",
            "--recipe",
            recipe,
            "--output-dir",
            output,
            "--package-format",
            "conda",
            "--test",
            "skip",
            "--no-include-recipe",
        ]
    )
    packages = list(output.rglob(f"conda-{COMPETING_CONDA_VERSION}-*.conda"))
    if len(packages) != 1:
        raise RuntimeError(
            f"expected one competing conda package in {output}, found {packages}"
        )
    run(["rattler-build", "publish", "--to", channel_uri, packages[0]])


def find_conda_package(packages: list[LockedPackage]) -> tuple[LockedPackage, str]:
    matches = []
    for package in packages:
        spec = MatchSpec.from_dist_str(package.filename)
        if spec.name == "conda":
            matches.append((package, str(spec.version)))
    if len(matches) != 1:
        raise RuntimeError(
            "expected one conda archive, found "
            f"{[package.url for package, _version in matches]}"
        )
    return matches[0]


def prepare(args: argparse.Namespace) -> None:
    work = args.work.resolve()
    if work.exists() and any(work.iterdir()):
        raise RuntimeError(f"proof work directory is not empty: {work}")
    work.mkdir(parents=True, exist_ok=True)

    source_gen2 = args.gen2_root.resolve()
    channel = work / "channel"
    channel_uri = channel.resolve().as_uri()
    gen1 = work / "gen1"
    gen2 = work / "gen2"
    copy_runtime_root(source_gen2, gen1, channel_uri)
    copy_runtime_root(source_gen2, gen2, channel_uri)
    baseline_manifest = gen1 / "pixi.toml"
    contents = baseline_manifest.read_text(encoding="utf-8")
    for name, value in (
        ("conda", {"version": f"=={args.baseline_version}", "channel": "conda-forge"}),
        ("runtime-version", args.baseline_version),
    ):
        rendered = (
            "{ "
            + ", ".join(f"{key} = {json.dumps(item)}" for key, item in value.items())
            + " }"
            if isinstance(value, dict)
            else json.dumps(value)
        )
        contents, count = re.subn(
            rf"^{name} = .+$", f"{name} = {rendered}", contents, flags=re.MULTILINE
        )
        if count != 1:
            raise RuntimeError(
                f"expected one {name} setting in the generated runtime manifest"
            )
    baseline_manifest.write_text(contents, encoding="utf-8")
    for root in (gen1, gen2):
        run(["pixi", "lock", "--manifest-path", root / "pixi.toml"])
    gen1_packages = selected_packages(gen1 / "pixi.lock", args.platform)
    gen2_packages = selected_packages(gen2 / "pixi.lock", args.platform)
    mirror_packages(
        channel, channel_uri, gen1_packages + gen2_packages, work / "downloads"
    )
    publish_competing_conda(channel_uri, work / "competing-conda")


def package_update(
    cs_path: Path, build: RuntimeBuild, out_dir: Path, channel_uri: str
) -> None:
    run(
        [
            cs_path,
            "package-update",
            "--info",
            build.info,
            "--binary",
            build.binary,
            "--out-dir",
            out_dir,
        ]
    )
    packages = list(out_dir.glob("*.conda"))
    if len(packages) != 1:
        raise RuntimeError(
            f"expected one runtime update package in {out_dir}, found {packages}"
        )
    run(["rattler-build", "publish", "--to", channel_uri, packages[0]])


def new_scenario(root: Path, binary: Path, platform: str) -> Scenario:
    if root.exists():
        raise RuntimeError(f"proof scenario already exists: {root}")
    stable = root / "bin" / ("conda.exe" if platform == "win-64" else "conda")
    stable.parent.mkdir(parents=True)
    shutil.copy2(binary, stable)
    return Scenario(
        root=root,
        prefix=root / "prefix",
        stable=stable,
        envs=root / "envs",
        packages=root / "packages",
        platform=platform,
    )


def runtime_environment(scenario: Scenario, *, offline: bool = False) -> dict[str, str]:
    env = os.environ.copy()
    for name in (
        "CONDA_PREFIX",
        "CONDA_DEFAULT_ENV",
        "CONDA_SHLVL",
        "CONDA_PROMPT_MODIFIER",
        "CONDA_ROOT_PREFIX",
        "CONDA_EXE",
        "CONDA_PYTHON_EXE",
        "CONDA_CHANNELS",
        "CONDA_ALWAYS_YES",
        "CONDA_NO_PLUGINS",
        "CONDA_DRY_RUN",
        "CONDA_JSON",
        "CONDA_QUIET",
        "CONDA_OFFLINE",
        "CONDA_PINNED_PACKAGES",
        "CONDA_REPODATA_FNS",
        "CONDA_SOLVER",
        "CONDA_SUBDIR",
        "CONDA_USE_ONLY_TAR_BZ2",
        "CONDARC",
        "PYTHONPATH",
        "RATTLER_CACHE_DIR",
        "_CE_CONDA",
        "_CE_M",
    ):
        env.pop(name, None)
    scenario.envs.mkdir(parents=True, exist_ok=True)
    scenario.packages.mkdir(parents=True, exist_ok=True)
    env["CONDA_SHIP_PREFIX"] = str(scenario.prefix)
    env["CONDA_ENVS_PATH"] = str(scenario.envs)
    env["CONDA_PKGS_DIRS"] = str(scenario.packages)
    env["CONDARC"] = str(scenario.prefix / ".condarc")
    env["CONDA_ALWAYS_YES"] = "false"
    env["RATTLER_CACHE_DIR"] = str(scenario.root / "rattler-cache")
    if offline:
        env["CONDA_OFFLINE"] = "1"
    return env


def runtime_run(
    scenario: Scenario,
    arguments: list[str],
    *,
    offline: bool = False,
    input_text: str | None = None,
    check: bool = True,
    timeout: int = 1_800,
) -> subprocess.CompletedProcess[str]:
    return run(
        [scenario.stable, *arguments],
        env=runtime_environment(scenario, offline=offline),
        input_text=input_text,
        check=check,
        timeout=timeout,
    )


def runtime_record_path(prefix: Path) -> Path:
    runtime = discover_runtime(prefix)
    if runtime is None:
        raise RuntimeError(f"no runtime record was found in {prefix}")
    return runtime.path


def runtime_record(prefix: Path) -> dict[str, Any]:
    path = runtime_record_path(prefix)
    return require_mapping(json.loads(path.read_text(encoding="utf-8")), str(path))


def pending_phase(prefix: Path) -> str | None:
    update = require_mapping(
        runtime_record(prefix).get("update"), "runtime update metadata"
    )
    pending = update.get("pending")
    if pending is None:
        return None
    pending_data = require_mapping(pending, "pending runtime update")
    phase = pending_data.get("phase")
    if not isinstance(phase, str):
        raise RuntimeError("pending runtime update has no phase")
    return phase


def installed_package_version(prefix: Path, package_name: str) -> str:
    matches = []
    for path in (prefix / "conda-meta").glob("*.json"):
        data = require_mapping(json.loads(path.read_text(encoding="utf-8")), str(path))
        if data.get("name") == package_name and isinstance(data.get("version"), str):
            matches.append(data["version"])
    if len(matches) != 1:
        raise RuntimeError(
            f"expected one installed {package_name} record in {prefix}, found {matches}"
        )
    return matches[0]


def installed_conda_version(prefix: Path) -> str:
    return installed_package_version(prefix, "conda")


def snapshot(scenario: Scenario) -> RuntimeState:
    metadata = runtime_record_path(scenario.prefix)
    conda_metadata = tuple(
        (str(path.relative_to(scenario.prefix)), sha256(path))
        for path in sorted((scenario.prefix / "conda-meta").rglob("*"))
        if path.is_file()
    )
    return RuntimeState(sha256(scenario.stable), sha256(metadata), conda_metadata)


def require_unchanged(
    before: RuntimeState, scenario: Scenario, description: str
) -> None:
    after = snapshot(scenario)
    if after != before:
        raise RuntimeError(f"{description} changed the executable or managed prefix")


def verify_conda_version(
    scenario: Scenario, conda_version: str, *, offline: bool = False
) -> None:
    version = runtime_run(scenario, ["--version"], offline=offline)
    if version.stdout.strip() != f"conda {conda_version}":
        raise RuntimeError(f"unexpected conda version output: {version.stdout!r}")
    if installed_conda_version(scenario.prefix) != conda_version:
        raise RuntimeError(f"installed conda metadata does not report {conda_version}")


def verify_identity(
    scenario: Scenario, conda_version: str, *, offline: bool = False
) -> None:
    verify_conda_version(scenario, conda_version, offline=offline)
    info_result = runtime_run(scenario, ["info", "--json"], offline=offline)
    info = require_mapping(json.loads(info_result.stdout), "conda info JSON")
    if info.get("conda_version") != conda_version:
        raise RuntimeError(
            f"conda info reports the wrong version: {info.get('conda_version')!r}"
        )
    root_prefix = info.get("root_prefix")
    if (
        not isinstance(root_prefix, str)
        or Path(root_prefix).resolve() != scenario.prefix.resolve()
    ):
        raise RuntimeError(f"conda info reports the wrong root prefix: {root_prefix!r}")
    self_version = runtime_run(scenario, ["self", "--version"], offline=offline)
    installed_self = installed_package_version(scenario.prefix, "conda-self")
    release = re.match(r"^(\d+)\.(\d+)\.(\d+)", installed_self)
    if (
        self_version.stdout.strip() != f"conda-self {installed_self}"
        or release is None
        or tuple(map(int, release.groups())) < (0, 2, 1)
    ):
        raise RuntimeError(
            f"unexpected conda-self version output: {self_version.stdout!r}"
        )


def verify_outer_identity(
    scenario: Scenario,
    version: str,
    ownership: str,
    *,
    installation: str | None = None,
) -> None:
    record = runtime_record(scenario.prefix)
    update = require_mapping(record.get("update"), "runtime update metadata")
    executable = update.get("executable")
    if (
        record.get("version") != version
        or update.get("ownership") != ownership
        or update.get("package") != "conda-runtime"
        or (installation is not None and update.get("installation") != installation)
        or update.get("sha256") != sha256(scenario.stable)
        or not isinstance(executable, str)
        or Path(executable).resolve() != scenario.stable.resolve()
    ):
        raise RuntimeError(
            f"runtime metadata does not match {ownership} outer executable {version}"
        )


def record_external_installation(scenario: Scenario) -> None:
    env = runtime_environment(scenario)
    env.update(
        {
            "CONDA_SHIP_INTERNAL_UPDATE": "v1/record-installation",
            "CONDA_SHIP_INTERNAL_UPDATE_OWNERSHIP": "external",
            "CONDA_SHIP_INTERNAL_UPDATE_INSTALLATION": "proof",
            "CONDA_SHIP_INTERNAL_UPDATE_EXECUTABLE": str(scenario.stable),
            "CONDA_SHIP_INTERNAL_UPDATE_INSTRUCTION": (
                "Replace the executable with the proof package manager, "
                "then retry conda self update."
            ),
        }
    )
    result = run([scenario.stable], env=env)
    response = require_mapping(
        json.loads(result.stdout), "record-installation response"
    )
    if response.get("recorded") is not True:
        raise RuntimeError("runtime did not record the external installation")


def poll_sha256(path: Path, expected: str, timeout: int = 60) -> None:
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        try:
            last = sha256(path)
        except (FileNotFoundError, PermissionError):
            pass
        if last == expected:
            return
        time.sleep(0.1)
    raise RuntimeError(
        f"timed out waiting for {path} to have SHA-256 {expected}, last was {last}"
    )


def poll_pending_phase(prefix: Path, expected: str, timeout: int = 60) -> None:
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = pending_phase(prefix)
        if last == expected:
            return
        time.sleep(0.1)
    raise RuntimeError(
        f"timed out waiting for runtime update phase {expected!r}, last was {last!r}"
    )


def replace_executable(source: Path, destination: Path) -> None:
    temporary = destination.with_name(f".{destination.name}.external")
    temporary.unlink(missing_ok=True)
    shutil.copy2(source, temporary)
    deadline = time.monotonic() + 60
    while True:
        try:
            os.replace(temporary, destination)
            return
        except PermissionError:
            if os.name != "nt" or time.monotonic() >= deadline:
                raise
            time.sleep(0.1)


def prove_direct_update(
    scenario: Scenario,
    gen2_binary: Path,
    missing_conda_archive: Path,
    gen1: GenerationVersions,
    gen2: GenerationVersions,
) -> None:
    verify_identity(scenario, gen1.conda, offline=True)
    verify_outer_identity(scenario, gen1.runtime, "direct")
    initial = snapshot(scenario)

    runtime_run(scenario, ["self", "update", "--dry-run", "--yes"])
    require_unchanged(initial, scenario, "dry-run")

    json_result = runtime_run(
        scenario, ["self", "update", "--json", "--dry-run", "--yes"]
    )
    json.loads(json_result.stdout)
    require_unchanged(initial, scenario, "JSON dry-run")

    quiet = runtime_run(scenario, ["self", "update", "--quiet", "--dry-run", "--yes"])
    quiet_output = f"{quiet.stdout}\n{quiet.stderr}".lower()
    if "updating conda (installed:" in quiet_output or any(
        message in quiet_output
        for message in (
            "update the standalone conda runtime",
            "standalone conda executable",
            "requires recovery",
        )
    ):
        raise RuntimeError(
            f"quiet dry-run produced updater output:\nstdout:\n{tail(quiet.stdout)}\n"
            f"stderr:\n{tail(quiet.stderr)}"
        )
    require_unchanged(initial, scenario, "quiet dry-run")

    declined = runtime_run(
        scenario,
        ["self", "update"],
        input_text="n\n",
        check=False,
    )
    prompt = f"{declined.stdout}\n{declined.stderr}".lower()
    if (
        declined.returncode != 0
        or prompt.count("update the standalone conda runtime") != 1
    ):
        raise RuntimeError(
            "declined update did not exit cleanly after one runtime prompt: "
            f"exit code {declined.returncode}\n{tail(prompt)}"
        )
    require_unchanged(initial, scenario, "declined update")

    hidden = missing_conda_archive.with_name(
        f".{missing_conda_archive.name}.unavailable"
    )
    if not missing_conda_archive.is_file() or hidden.exists():
        raise RuntimeError(
            f"cannot create the inner transaction failure for {missing_conda_archive}"
        )
    missing_conda_archive.replace(hidden)
    try:
        failed = runtime_run(
            scenario,
            ["self", "update", "--yes"],
            check=False,
        )
    finally:
        hidden.replace(missing_conda_archive)
    if failed.returncode == 0:
        raise RuntimeError(
            "inner conda update unexpectedly succeeded with its archive missing"
        )
    if sha256(scenario.stable) != initial.executable_sha256:
        raise RuntimeError("inner failure replaced the outer executable")
    if installed_conda_version(scenario.prefix) != gen1.conda:
        raise RuntimeError("inner failure changed the installed conda version")

    fresh = runtime_run(scenario, ["--version"])
    if fresh.stdout.strip() != f"conda {gen1.conda}":
        raise RuntimeError(
            f"runtime was not usable after inner failure: {fresh.stdout!r}"
        )
    if sha256(scenario.stable) != initial.executable_sha256:
        raise RuntimeError("startup recovery promoted the unapproved outer executable")
    verify_outer_identity(scenario, gen1.runtime, "direct")
    if pending_phase(scenario.prefix) is not None:
        raise RuntimeError("startup recovery left the unapproved outer update pending")

    expected_gen2_sha256 = sha256(gen2_binary)
    update = runtime_run(scenario, ["self", "update", "--json", "--yes"])
    update_result = json.loads(update.stdout)
    if not isinstance(update_result, dict):
        raise RuntimeError("successful update did not produce one JSON object")
    if os.name == "nt":
        poll_pending_phase(scenario.prefix, "cleanup")
        if sha256(scenario.stable) != expected_gen2_sha256:
            raise RuntimeError("Windows update worker installed the wrong executable")
    else:
        poll_sha256(scenario.stable, expected_gen2_sha256)
    verify_identity(scenario, gen2.conda)
    verify_outer_identity(scenario, gen2.runtime, "direct")

    updated = snapshot(scenario)
    runtime_run(scenario, ["self", "update", "--yes"])
    require_unchanged(updated, scenario, "repeated update")


def prove_external_reconciliation(
    scenario: Scenario,
    gen2_binary: Path,
    gen1: GenerationVersions,
    gen2: GenerationVersions,
) -> None:
    verify_conda_version(scenario, gen1.conda)
    record_external_installation(scenario)
    verify_outer_identity(
        scenario,
        gen1.runtime,
        "external",
        installation="proof",
    )
    initial = snapshot(scenario)

    blocked = runtime_run(
        scenario,
        ["self", "update", "--yes"],
        check=False,
    )
    blocked_output = f"{blocked.stdout}\n{blocked.stderr}"
    if (
        blocked.returncode == 0
        or "Replace the executable with the proof package manager" not in blocked_output
    ):
        raise RuntimeError(
            "external update did not stop with its recorded instruction: "
            f"exit code {blocked.returncode}\n{tail(blocked_output)}"
        )
    require_unchanged(initial, scenario, "blocked external update")

    replacement_sha256 = sha256(gen2_binary)
    replace_executable(gen2_binary, scenario.stable)

    result = runtime_run(scenario, ["--version"])
    if result.stdout.strip() != f"conda {gen1.conda}":
        raise RuntimeError(
            "external replacement unexpectedly changed the inner conda version"
        )
    record = runtime_record(scenario.prefix)
    update = require_mapping(record.get("update"), "external runtime update metadata")
    if record.get("version") != gen2.runtime or update.get("ownership") != "external":
        raise RuntimeError("external executable replacement was not reconciled")
    if update.get("sha256") != replacement_sha256:
        raise RuntimeError(
            "external executable reconciliation recorded the wrong digest"
        )

    runtime_run(scenario, ["self", "update", "--yes"])
    if sha256(scenario.stable) != replacement_sha256:
        raise RuntimeError("inner update replaced an externally owned executable")
    verify_conda_version(scenario, gen2.conda)
    verify_outer_identity(
        scenario,
        gen2.runtime,
        "external",
        installation="proof",
    )


def stage_outer_update(scenario: Scenario) -> tuple[RuntimeMetadata, BinaryIO]:
    runtime = discover_runtime(scenario.prefix)
    if runtime is None:
        raise RuntimeError("managed prefix has no discoverable runtime update metadata")
    lock = acquire_lock(runtime.lock_path)
    try:
        check = validate_check(invoke_helper(runtime, "check"), runtime)
        if check.get("available") is not True:
            raise RuntimeError("manual recovery scenario found no outer runtime update")
        staged = invoke_helper(runtime, "stage", candidate=check["sha256"])
        if staged.get("staged") is not True:
            raise RuntimeError(
                f"manual recovery scenario did not stage an update: {staged}"
            )
        return runtime, lock
    except BaseException:
        release_lock(lock)
        raise


def prove_unix_replacement_recovery(
    scenario: Scenario,
    gen2_binary: Path,
    gen1: GenerationVersions,
    gen2: GenerationVersions,
) -> None:
    verify_conda_version(scenario, gen1.conda, offline=True)
    verify_outer_identity(scenario, gen1.runtime, "direct")
    initial_sha256 = sha256(scenario.stable)
    expected_sha256 = sha256(gen2_binary)
    runtime, lock = stage_outer_update(scenario)
    directory = scenario.stable.parent
    original_mode = directory.stat().st_mode & 0o7777
    apply_failed = False
    try:
        directory.chmod(0o555)
        try:
            invoke_helper(runtime, "apply")
        except Exception:
            apply_failed = True
        if not apply_failed:
            raise RuntimeError(
                "read-only executable directory did not interrupt replacement"
            )
        if pending_phase(scenario.prefix) != "replacing":
            raise RuntimeError(
                "interrupted Unix replacement did not retain replacing metadata"
            )
        if sha256(scenario.stable) != initial_sha256:
            raise RuntimeError(
                "interrupted Unix replacement changed the stable executable"
            )
    finally:
        directory.chmod(original_mode)
        release_lock(lock)

    verify_conda_version(scenario, gen1.conda)
    poll_sha256(scenario.stable, expected_sha256)
    if pending_phase(scenario.prefix) is not None:
        raise RuntimeError("Unix startup recovery left pending update metadata")
    verify_outer_identity(scenario, gen2.runtime, "direct")


def full(args: argparse.Namespace) -> None:
    work = args.work.resolve()
    channel = work / "channel"
    channel_uri = channel.resolve().as_uri()
    gen1_root = work / "gen1"
    gen2_root = work / "gen2"
    _gen1_conda, gen1_conda_version = find_conda_package(
        selected_packages(gen1_root / "pixi.lock", args.platform)
    )
    gen2_conda, gen2_conda_version = find_conda_package(
        selected_packages(gen2_root / "pixi.lock", args.platform)
    )
    gen2_conda_archive = channel / gen2_conda.subdir / gen2_conda.filename
    gen1_versions = GenerationVersions(
        runtime=runtime_version(gen1_root),
        conda=gen1_conda_version,
    )
    gen2_versions = GenerationVersions(
        runtime=runtime_version(gen2_root),
        conda=gen2_conda_version,
    )
    cs_path = args.cs_path.resolve()
    gen1_binary = args.gen1_binary.resolve()
    gen2_binary = args.gen2_binary.resolve()
    gen2_info = args.gen2_info.resolve()
    if not cs_path.is_file():
        raise RuntimeError(f"released conda-ship builder is missing: {cs_path}")
    if not gen1_binary.is_file():
        raise RuntimeError(f"action-built Gen1 executable is missing: {gen1_binary}")
    if not gen2_binary.is_file():
        raise RuntimeError(f"action-built Gen2 executable is missing: {gen2_binary}")
    if not gen2_info.is_file():
        raise RuntimeError(f"action-built Gen2 info is missing: {gen2_info}")

    proof = work / "full"
    if proof.exists():
        raise RuntimeError(f"full proof output already exists: {proof}")
    proof.mkdir()
    gen2_build = RuntimeBuild(binary=gen2_binary, info=gen2_info)
    package_update(
        cs_path,
        gen2_build,
        proof / "transport",
        channel_uri,
    )

    direct = new_scenario(proof / "direct", gen1_binary, args.platform)
    prove_direct_update(
        direct,
        gen2_build.binary,
        gen2_conda_archive,
        gen1_versions,
        gen2_versions,
    )

    external = new_scenario(proof / "external", gen1_binary, args.platform)
    prove_external_reconciliation(
        external,
        gen2_build.binary,
        gen1_versions,
        gen2_versions,
    )

    if args.platform.startswith("linux-"):
        interrupted = new_scenario(proof / "interrupted", gen1_binary, args.platform)
        prove_unix_replacement_recovery(
            interrupted,
            gen2_build.binary,
            gen1_versions,
            gen2_versions,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser(
        "prepare", help="prepare one local proof channel"
    )
    prepare_parser.add_argument("--work", required=True, type=Path)
    prepare_parser.add_argument("--platform", required=True)
    prepare_parser.add_argument("--gen2-root", required=True, type=Path)
    prepare_parser.add_argument("--baseline-version", default="26.5.2")
    prepare_parser.set_defaults(handler=prepare)

    full_parser = subparsers.add_parser("full", help="run the complete update proof")
    full_parser.add_argument("--work", required=True, type=Path)
    full_parser.add_argument("--platform", required=True)
    full_parser.add_argument("--cs-path", required=True, type=Path)
    full_parser.add_argument("--gen1-binary", required=True, type=Path)
    full_parser.add_argument("--gen2-binary", required=True, type=Path)
    full_parser.add_argument("--gen2-info", required=True, type=Path)
    full_parser.set_defaults(handler=full)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        args.handler(args)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
