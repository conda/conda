# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Validation for plugin package operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....base.context import context
from ....core.package_cache_data import PackageCacheData, ProgressiveFetchExtract
from ....core.prefix_data import PrefixData
from ....exceptions import CondaValueError
from ....gateways.disk.read import read_package_info
from ....models.match_spec import MatchSpec

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ....common.path import PathType
    from ....core.link import UnlinkLinkTransaction
    from ....models.environment import Environment
    from ....models.records import PackageCacheRecord


def get_installed_plugin_package_names(prefix: PathType) -> frozenset[str]:
    """Return conda plugin package names installed in a prefix."""
    prefix_data = PrefixData(prefix)
    prefix_data.assert_environment()
    return frozenset(
        record.name
        for record in prefix_data.get_conda_packages()
        if context.plugin_manager.is_conda_plugin_package(
            record,
            prefix=prefix_data.prefix_path,
        )
    )


def require_installed_plugin_specs(
    specs: Iterable[str | MatchSpec],
    prefix: PathType,
    *,
    command: str,
) -> None:
    installed_names = get_installed_plugin_package_names(prefix)
    invalid_specs: list[str] = []

    for spec in specs:
        if MatchSpec(spec).name not in installed_names:
            invalid_specs.append(str(spec))

    if invalid_specs:
        installed = ", ".join(sorted(installed_names)) or "none"
        raise CondaValueError(
            f"`conda plugins {command}` can only operate on installed conda "
            f"plugin packages. Not installed as conda plugins: "
            f"{', '.join(invalid_specs)}. Installed conda plugins: {installed}."
        )


def require_plugin_update_environment(environment: Environment) -> None:
    """Validate requested plugin updates after merging file input."""
    if environment.external_packages:
        installers = ", ".join(sorted(environment.external_packages))
        raise CondaValueError(
            "`conda plugins update` cannot update packages managed by external "
            f"installers. External installers: {installers}."
        )

    if environment.variables:
        raise CondaValueError(
            "`conda plugins update` cannot set environment variables from "
            "environment files."
        )

    require_installed_plugin_specs(
        environment.requested_packages,
        environment.prefix,
        command="update",
    )


def require_plugin_install_transaction(
    unlink_link_transaction: UnlinkLinkTransaction,
    *,
    prefetch_link_precs: bool = False,
) -> None:
    """Validate requested plugin install specs in a transaction."""
    invalid_specs = []
    inspect_link_precs = prefetch_link_precs and not context.dry_run

    if inspect_link_precs:
        requested_link_precs = tuple(
            link_prec
            for setup in unlink_link_transaction.prefix_setups.values()
            for link_prec in setup.link_precs
            if any(spec.match(link_prec) for spec in setup.update_specs)
        )
        if requested_link_precs:
            ProgressiveFetchExtract(requested_link_precs).execute()

    for setup in unlink_link_transaction.prefix_setups.values():
        prefix_data = PrefixData(setup.target_prefix)

        for spec in setup.update_specs:
            link_prec = next(
                (prec for prec in setup.link_precs if spec.match(prec)),
                None,
            )
            if link_prec is not None:
                if inspect_link_precs:
                    package_cache_record = PackageCacheData.get_entry_to_link(link_prec)
                    package_info = read_package_info(link_prec, package_cache_record)
                    if not context.plugin_manager.is_conda_plugin_package(package_info):
                        invalid_specs.append(str(spec))
                continue

            prefix_record = prefix_data.get(spec.name, None) if spec.name else None
            if prefix_record is not None and spec.match(prefix_record):
                if not context.plugin_manager.is_conda_plugin_package(
                    prefix_record,
                    prefix=setup.target_prefix,
                ):
                    invalid_specs.append(str(spec))
            elif inspect_link_precs:
                invalid_specs.append(str(spec))

    if invalid_specs:
        raise CondaValueError(
            "`conda plugins install` can only install conda plugin packages. "
            f"Not conda plugin packages: {', '.join(invalid_specs)}."
        )


def require_explicit_plugin_packages(
    package_records: Iterable[PackageCacheRecord],
) -> None:
    invalid_packages = []

    for package_record in package_records:
        package_info = read_package_info(package_record, package_record)
        if not context.plugin_manager.is_conda_plugin_package(package_info):
            invalid_packages.append(package_record.name)

    if invalid_packages:
        raise CondaValueError(
            "`conda plugins install` can only install conda plugin packages. "
            f"Not conda plugin packages: {', '.join(invalid_packages)}."
        )
