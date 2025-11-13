# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Backend logic implementation for `conda doctor`."""

from __future__ import annotations

import os
from logging import getLogger
from pathlib import Path

from requests.exceptions import RequestException

from ....base.constants import PREFIX_PINNED_FILE
from ....base.context import context
from ....common.io import dashlist
from ....common.serialize import json, yaml_safe_dump
from ....core.envs_manager import get_user_environments_txt_file
from ....core.prefix_data import PrefixData
from ....exceptions import CondaError
from ....gateways.connection.session import get_session
from ....gateways.disk.lock import locking_supported
from ....gateways.disk.read import compute_sum
from ....models.match_spec import MatchSpec
from ... import hookimpl
from ...types import CondaHealthCheck

logger = getLogger(__name__)

OK_MARK = "✅"
X_MARK = "❌"


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


def missing_files(prefix: str, verbose: bool) -> None:
    missing_files = find_packages_with_missing_files(prefix)
    if missing_files:
        print(f"{X_MARK} Missing Files:\n")
        for package_name, missing_files in missing_files.items():
            if verbose:
                delimiter = "\n  "
                print(f"{package_name}:{delimiter}{delimiter.join(missing_files)}")
            else:
                print(f"{package_name}: {len(missing_files)}\n")
    else:
        print(f"{OK_MARK} There are no packages with missing files.\n")


def altered_files(prefix: str, verbose: bool) -> None:
    altered_packages = find_altered_packages(prefix)
    if altered_packages:
        print(f"{X_MARK} Altered Files:\n")
        for package_name, altered_files in altered_packages.items():
            if verbose:
                delimiter = "\n  "
                print(f"{package_name}:{delimiter}{delimiter.join(altered_files)}\n")
            else:
                print(f"{package_name}: {len(altered_files)}\n")
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
    # get the plugin manager from context
    pm = context.plugin_manager

    # get prefix data
    pd = PrefixData(prefix)

    # get virtual packages record
    virtual_packages = {
        record.name: record for record in pm.get_virtual_package_records()
    }

    # collect missing dependency issues in a list
    issues = {}

    # check if dependencies are present
    for record in pd.iter_records():
        for dependency in record.depends:
            match_spec = MatchSpec(dependency)
            dependency_record = pd.get(
                match_spec.name, default=virtual_packages.get(match_spec.name, None)
            )
            if dependency_record is None:
                issues.setdefault(record.name, {}).setdefault("missing", []).append(
                    str(match_spec)
                )
            elif not match_spec.match(dependency_record):
                inconsistent = {
                    "expected": str(match_spec),
                    "installed": str(dependency_record),
                }
                issues.setdefault(record.name, {}).setdefault(
                    "inconsistent", []
                ).append(inconsistent)

        for constrain in record.constrains:
            package_found = pd.get(
                MatchSpec(constrain).name,
                default=virtual_packages.get(MatchSpec(constrain).name, None),
            )
            if package_found is not None:
                if not MatchSpec(constrain).match(package_found):
                    inconsistent_constrain = {
                        "expected": str(MatchSpec(constrain)),
                        "installed": f"{package_found.name}[version='{package_found.version}']",
                    }
                    issues.setdefault(record.name, {}).setdefault(
                        "inconsistent", []
                    ).append(inconsistent_constrain)

    if issues:
        print(f"{X_MARK} The environment is not consistent.\n")
        if verbose:
            print(yaml_safe_dump(issues))
    else:
        print(f"{OK_MARK} The environment is consistent.\n")


def pinned_well_formatted_check(prefix: str, verbose: bool) -> None:
    prefix_data = PrefixData(prefix_path=prefix)

    try:
        pinned_specs = prefix_data.get_pinned_specs()
    except OSError as err:
        print(
            f"{X_MARK} Unable to open pinned file at {prefix_data.prefix_path / PREFIX_PINNED_FILE}:\n\t{err}"
        )
    except Exception as err:
        print(
            f"{X_MARK} An error occurred trying to read pinned file at {prefix_data.prefix_path / PREFIX_PINNED_FILE}:\n\t{err}"
        )
        return

    # If there are no pinned specs, exit early
    if not pinned_specs:
        print(
            f"{OK_MARK} No pinned specs found in {prefix_data.prefix_path / PREFIX_PINNED_FILE}."
        )
        return

    # If there is a pinned package that does not exist in the prefix, that
    # is an indication that it might be a typo.
    maybe_malformed = [
        pinned for pinned in pinned_specs if not any(prefix_data.query(pinned.name))
    ]

    # Inform the user of any packages that might be malformed
    if maybe_malformed:
        print(
            f"{X_MARK} The following specs in {prefix_data.prefix_path / PREFIX_PINNED_FILE} are maybe malformed:"
        )
        print(dashlist((spec.name for spec in maybe_malformed), indent=4))
        return

    # If there are no malformed packages, the pinned file is well formatted
    print(
        f"{OK_MARK} The pinned file in {prefix_data.prefix_path / PREFIX_PINNED_FILE} seems well formatted."
    )


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


@hookimpl
def conda_health_checks():
    yield CondaHealthCheck(name="Missing Files", action=missing_files)
    yield CondaHealthCheck(name="Altered Files", action=altered_files)
    yield CondaHealthCheck(name="Environment.txt File Check", action=env_txt_check)
    yield CondaHealthCheck(
        name="REQUESTS_CA_BUNDLE Check", action=requests_ca_bundle_check
    )
    yield CondaHealthCheck(
        name="Consistent Environment Check", action=consistent_env_check
    )
    yield CondaHealthCheck(
        name=f"{PREFIX_PINNED_FILE} Well Formatted Check",
        action=pinned_well_formatted_check,
    )
    yield CondaHealthCheck(
        name="File Locking Supported Check",
        action=file_locking_check,
    )
