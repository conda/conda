# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Backend logic implementation for `conda doctor`."""

from __future__ import annotations

import os
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING

from requests.exceptions import RequestException

from ....base.constants import PREFIX_PINNED_FILE
from ....base.context import context
from ....common.io import dashlist
from ....common.serialize import json, yaml_safe_dump
from ....core.envs_manager import get_user_environments_txt_file, register_env
from ....core.prefix_data import PrefixData
from ....exceptions import CondaError
from ....gateways.connection.session import get_session
from ....gateways.disk.lock import locking_supported
from ....gateways.disk.read import compute_sum
from ....models.match_spec import MatchSpec
from ....reporters import confirm_yn
from ... import hookimpl
from ...types import CondaHealthCheck

if TYPE_CHECKING:
    from argparse import Namespace

logger = getLogger(__name__)

OK_MARK = "✅"
X_MARK = "❌"


# =============================================================================
# Helper functions
# =============================================================================


def reinstall_packages(args: Namespace, specs: list[str], **kwargs) -> int:
    """Reinstall packages using conda install.

    Common helper for health fixes that need to reinstall packages.

    :param args: Parsed arguments namespace
    :param specs: Package specs to reinstall
    :param kwargs: Override default install options (e.g., force_reinstall=True)
    :return: Exit code from install
    """
    from ....cli.install import install

    args.packages = specs
    args.channel = kwargs.get("channel", None)
    args.override_channels = kwargs.get("override_channels", False)
    args.force_reinstall = kwargs.get("force_reinstall", False)
    args.satisfied_skip_solve = kwargs.get("satisfied_skip_solve", False)
    args.update_deps = kwargs.get("update_deps", False)
    args.only_deps = kwargs.get("only_deps", False)
    args.no_deps = kwargs.get("no_deps", False)
    args.prune = kwargs.get("prune", False)
    args.freeze_installed = kwargs.get("freeze_installed", False)
    args.solver_retries = kwargs.get("solver_retries", 0)

    return install(args)


# =============================================================================
# Detection functions (shared by checks and fixes)
# =============================================================================


def check_envs_txt_file(prefix: str | os.PathLike | Path) -> bool:
    """Checks whether the environment is listed in the environments.txt file"""
    prefix = Path(prefix)
    envs_txt_file = Path(get_user_environments_txt_file())

    def samefile(path1: Path, path2: Path) -> bool:
        try:
            return path1.samefile(path2)
        except FileNotFoundError:
            # FileNotFoundError: path doesn't exist
            return path1 == path2

    try:
        for line in envs_txt_file.read_text().splitlines():
            stripped_line = line.strip()
            if stripped_line and samefile(prefix, Path(stripped_line)):
                return True
    except (IsADirectoryError, FileNotFoundError, PermissionError) as err:
        logger.error(
            f"{envs_txt_file} could not be "
            f"accessed because of the following error: {err}"
        )
    return False


def excluded_files_check(filename: str) -> bool:
    excluded_extensions = (".pyc", ".pyo")
    return filename.endswith(excluded_extensions)


def find_packages_with_missing_files(prefix: str | Path) -> dict[str, list[str]]:
    """Finds packages listed in conda-meta which have missing files."""
    packages_with_missing_files = {}
    prefix = Path(prefix)
    for file in (prefix / "conda-meta").glob("*.json"):
        for file_name in json.loads(file.read_text()).get("files", []):
            # Add warnings if json file has missing "files"
            if (
                not excluded_files_check(file_name)
                and not (prefix / file_name).exists()
            ):
                packages_with_missing_files.setdefault(file.stem, []).append(file_name)
    return packages_with_missing_files


def find_altered_packages(prefix: str | Path) -> dict[str, list[str]]:
    """Finds altered packages"""
    altered_packages = {}

    prefix = Path(prefix)
    for file in (prefix / "conda-meta").glob("*.json"):
        try:
            metadata = json.loads(file.read_text())
        except Exception as exc:
            logger.error(
                f"Could not load the json file {file} because of the following error: {exc}."
            )
            continue

        try:
            paths_data = metadata["paths_data"]
            paths = paths_data["paths"]
        except KeyError:
            continue

        if paths_data.get("paths_version") != 1:
            continue

        for path in paths:
            _path = path.get("_path")
            if excluded_files_check(_path):
                continue

            old_sha256 = path.get("sha256_in_prefix")
            if _path is None or old_sha256 is None:
                continue

            file_location = prefix / _path
            if not file_location.is_file():
                continue

            try:
                new_sha256 = compute_sum(file_location, "sha256")
            except OSError as err:
                raise CondaError(
                    f"Could not generate checksum for file {file_location} "
                    f"because of the following error: {err}."
                )

            if old_sha256 != new_sha256:
                altered_packages.setdefault(file.stem, []).append(_path)

    return altered_packages


def find_inconsistent_packages(
    prefix_data: PrefixData,
) -> tuple[dict[str, dict[str, list]], set[str]]:
    """Find packages with missing or inconsistent dependencies.

    Returns a tuple of (issues dict, missing dependency names set).
    The issues dict maps package name -> {"missing": [...], "inconsistent": [...]}.
    """
    pm = context.plugin_manager
    virtual_packages = {
        record.name: record for record in pm.get_virtual_package_records()
    }

    issues = {}
    missing_deps = set()

    for record in prefix_data.iter_records():
        for dependency in record.depends:
            match_spec = MatchSpec(dependency)
            dep_record = prefix_data.get(
                match_spec.name, default=virtual_packages.get(match_spec.name)
            )
            if dep_record is None:
                issues.setdefault(record.name, {}).setdefault("missing", []).append(
                    str(match_spec)
                )
                missing_deps.add(match_spec.name)
            elif not match_spec.match(dep_record):
                issues.setdefault(record.name, {}).setdefault(
                    "inconsistent", []
                ).append({"expected": str(match_spec), "installed": str(dep_record)})

        for constrain in record.constrains:
            package_found = prefix_data.get(
                MatchSpec(constrain).name,
                default=virtual_packages.get(MatchSpec(constrain).name),
            )
            if package_found is not None and not MatchSpec(constrain).match(
                package_found
            ):
                issues.setdefault(record.name, {}).setdefault(
                    "inconsistent", []
                ).append(
                    {
                        "expected": str(MatchSpec(constrain)),
                        "installed": f"{package_found.name}[version='{package_found.version}']",
                    }
                )

    return issues, missing_deps


def find_malformed_pinned_specs(prefix_data: PrefixData) -> list[MatchSpec]:
    """Find pinned specs that reference packages not installed in the environment.

    Returns a list of MatchSpec objects for packages that might be typos.
    """
    try:
        pinned_specs = prefix_data.get_pinned_specs()
    except Exception:
        return []

    if not pinned_specs:
        return []

    return [
        pinned for pinned in pinned_specs if not any(prefix_data.query(pinned.name))
    ]


# =============================================================================
# Health check action functions (display status)
# =============================================================================


def missing_files(prefix: str, verbose: bool) -> None:
    missing = find_packages_with_missing_files(prefix)
    if missing:
        print(f"{X_MARK} Missing Files:\n")
        for package_name, files in missing.items():
            if verbose:
                delimiter = "\n  "
                print(f"{package_name}:{delimiter}{delimiter.join(files)}")
            else:
                print(f"{package_name}: {len(files)}\n")
    else:
        print(f"{OK_MARK} There are no packages with missing files.\n")


def altered_files(prefix: str, verbose: bool) -> None:
    altered = find_altered_packages(prefix)
    if altered:
        print(f"{X_MARK} Altered Files:\n")
        for package_name, files in altered.items():
            if verbose:
                delimiter = "\n  "
                print(f"{package_name}:{delimiter}{delimiter.join(files)}\n")
            else:
                print(f"{package_name}: {len(files)}\n")
    else:
        print(f"{OK_MARK} There are no packages with altered files.\n")


def env_txt_check(prefix: str, verbose: bool) -> None:
    if check_envs_txt_file(prefix):
        print(f"{OK_MARK} The environment is listed in the environments.txt file.\n")
    else:
        print(f"{X_MARK} The environment is not listed in the environments.txt file.\n")


def requests_ca_bundle_check(prefix: str, verbose: bool) -> None:
    # Use a channel aliases url since users may be on an intranet and
    # have customized their conda setup to point to an internal mirror.
    ca_bundle_test_url = context.channel_alias.urls()[0]

    requests_ca_bundle = os.getenv("REQUESTS_CA_BUNDLE")
    if not requests_ca_bundle:
        return
    elif not Path(requests_ca_bundle).exists():
        print(
            f"{X_MARK} Env var `REQUESTS_CA_BUNDLE` is pointing to a non existent file.\n"
        )
    else:
        session = get_session(ca_bundle_test_url)
        try:
            response = session.get(ca_bundle_test_url)
            response.raise_for_status()
            print(f"{OK_MARK} `REQUESTS_CA_BUNDLE` was verified.\n")
        except (OSError, RequestException) as e:
            print(
                f"{X_MARK} The following error occured while verifying `REQUESTS_CA_BUNDLE`: {e}\n"
            )


def consistent_env_check(prefix: str, verbose: bool) -> None:
    pd = PrefixData(prefix)
    issues, _ = find_inconsistent_packages(pd)

    if issues:
        print(f"{X_MARK} The environment is not consistent.\n")
        if verbose:
            print(yaml_safe_dump(issues))
    else:
        print(f"{OK_MARK} The environment is consistent.\n")


def pinned_well_formatted_check(prefix: str, verbose: bool) -> None:
    prefix_data = PrefixData(prefix_path=prefix)
    pinned_file = prefix_data.prefix_path / PREFIX_PINNED_FILE

    try:
        pinned_specs = prefix_data.get_pinned_specs()
    except OSError as err:
        print(f"{X_MARK} Unable to open pinned file at {pinned_file}:\n\t{err}")
        return
    except Exception as err:
        print(
            f"{X_MARK} An error occurred trying to read pinned file at {pinned_file}:\n\t{err}"
        )
        return

    if not pinned_specs:
        print(f"{OK_MARK} No pinned specs found in {pinned_file}.")
        return

    maybe_malformed = find_malformed_pinned_specs(prefix_data)

    if maybe_malformed:
        print(f"{X_MARK} The following specs in {pinned_file} are maybe malformed:")
        print(dashlist((spec.name for spec in maybe_malformed), indent=4))
        return

    print(f"{OK_MARK} The pinned file in {pinned_file} seems well formatted.")


def file_locking_check(prefix: str, verbose: bool):
    """
    Report if file locking is supported or not.
    """
    if locking_supported():
        if context.no_lock:
            print(
                f"{X_MARK} File locking is supported but currently disabled using the CONDA_NO_LOCK=1 setting.\n"
            )
        else:
            print(f"{OK_MARK} File locking is supported.\n")
    else:
        print(f"{X_MARK} File locking is not supported.\n")


# =============================================================================
# Health fix functions (apply fixes)
# =============================================================================


def fix_missing_files(prefix: str, args: Namespace) -> int:
    """Fix missing files by reinstalling affected packages."""
    packages_with_missing = find_packages_with_missing_files(prefix)

    if not packages_with_missing:
        print("No packages with missing files found.")
        return 0

    print(f"Found {len(packages_with_missing)} package(s) with missing files:")
    for pkg_name, files in sorted(packages_with_missing.items()):
        print(f"  {pkg_name}: {len(files)} missing file(s)")

    print()
    confirm_yn(
        "Reinstall these packages to restore missing files?",
        default="no",
        dry_run=context.dry_run,
    )

    specs = list(packages_with_missing.keys())
    return reinstall_packages(args, specs, force_reinstall=True)


def fix_altered_files(prefix: str, args: Namespace) -> int:
    """Fix altered files by reinstalling affected packages."""
    altered = find_altered_packages(prefix)

    if not altered:
        print("No packages with altered files found.")
        return 0

    print(f"Found {len(altered)} package(s) with altered files:")
    for pkg_name, files in sorted(altered.items()):
        print(f"  {pkg_name}: {len(files)} altered file(s)")

    print()
    confirm_yn(
        "Reinstall these packages to restore original files?",
        default="no",
        dry_run=context.dry_run,
    )

    specs = list(altered.keys())
    return reinstall_packages(args, specs, force_reinstall=True)


def fix_env_txt(prefix: str, args: Namespace) -> int:
    """Register environment in environments.txt."""
    if check_envs_txt_file(prefix):
        print(f"Environment is already registered in environments.txt: {prefix}")
        return 0

    envs_txt = get_user_environments_txt_file()
    print(f"Environment not found in {envs_txt}")
    print(f"  Environment: {prefix}")

    print()
    confirm_yn(
        "Register this environment?",
        default="yes",
        dry_run=context.dry_run,
    )

    register_env(prefix)
    print(f"Environment registered: {prefix}")
    return 0


def fix_inconsistent_packages(prefix: str, args: Namespace) -> int:
    """Fix inconsistent packages by updating the environment."""
    prefix_data = PrefixData(prefix)
    issues, missing_deps = find_inconsistent_packages(prefix_data)

    if not issues:
        print("No inconsistent packages found.")
        return 0

    print(f"Found {len(issues)} package(s) with dependency issues:")
    for pkg_name, pkg_issues in sorted(issues.items()):
        missing = pkg_issues.get("missing", [])
        inconsistent = pkg_issues.get("inconsistent", [])
        print(f"  {pkg_name}:", end="")
        if missing:
            print(f" {len(missing)} missing", end="")
        if inconsistent:
            print(f" {len(inconsistent)} inconsistent", end="")
        print()

    print()
    confirm_yn(
        "Attempt to resolve these dependency issues?",
        default="no",
        dry_run=context.dry_run,
    )

    # Install missing dependencies and update inconsistent ones
    specs = list(missing_deps) if missing_deps else []

    # Also add packages with inconsistent deps to trigger solver
    for pkg_name in issues:
        if pkg_name not in specs:
            specs.append(pkg_name)

    return reinstall_packages(args, specs, update_deps=True)


def fix_malformed_pinned(prefix: str, args: Namespace) -> int:
    """Clean up malformed specs in pinned file."""
    prefix_data = PrefixData(prefix)
    pinned_file = Path(prefix) / PREFIX_PINNED_FILE

    if not pinned_file.exists():
        print(f"No pinned file found at {pinned_file}")
        return 0

    malformed = find_malformed_pinned_specs(prefix_data)

    if not malformed:
        print("No malformed specs found in pinned file.")
        return 0

    print(f"Found {len(malformed)} potentially malformed spec(s) in {pinned_file}:")
    for spec in malformed:
        print(f"  {spec} (package not installed)")

    print()
    confirm_yn(
        "Remove these specs from the pinned file?",
        default="no",
        dry_run=context.dry_run,
    )

    # Read the current file and filter out malformed specs
    malformed_names = {spec.name for spec in malformed}
    lines = pinned_file.read_text().splitlines()
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue

        # Parse the spec to get the name
        try:
            spec = MatchSpec(stripped)
            if spec.name not in malformed_names:
                new_lines.append(line)
            else:
                print(f"Removing: {stripped}")
        except Exception:
            # Keep lines we can't parse
            new_lines.append(line)

    # Write back
    pinned_file.write_text("\n".join(new_lines) + "\n" if new_lines else "")
    print(f"Updated {pinned_file}")
    return 0


# =============================================================================
# Plugin hook registration
# =============================================================================


@hookimpl
def conda_health_checks():
    yield CondaHealthCheck(
        name="Missing Files",
        action=missing_files,
        fix=fix_missing_files,
        summary="Reinstall packages with missing files",
    )
    yield CondaHealthCheck(
        name="Altered Files",
        action=altered_files,
        fix=fix_altered_files,
        summary="Reinstall packages with altered files",
    )
    yield CondaHealthCheck(
        name="Environment.txt File Check",
        action=env_txt_check,
        fix=fix_env_txt,
        summary="Register environment in environments.txt",
    )
    yield CondaHealthCheck(
        name="REQUESTS_CA_BUNDLE Check",
        action=requests_ca_bundle_check,
        # No fix - user must configure this manually
    )
    yield CondaHealthCheck(
        name="Consistent Environment Check",
        action=consistent_env_check,
        fix=fix_inconsistent_packages,
        summary="Resolve missing or inconsistent dependencies",
    )
    yield CondaHealthCheck(
        name=f"{PREFIX_PINNED_FILE} Well Formatted Check",
        action=pinned_well_formatted_check,
        fix=fix_malformed_pinned,
        summary="Clean up invalid specs in pinned file",
    )
    yield CondaHealthCheck(
        name="File Locking Supported Check",
        action=file_locking_check,
        # No fix - system-level issue
    )
