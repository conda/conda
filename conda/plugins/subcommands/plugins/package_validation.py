# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Validation for plugin package operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....base.context import context
from ....core.package_cache_data import PackageCacheData
from ....core.prefix_data import PrefixData
from ....exceptions import CondaValueError
from ....gateways.disk.read import read_package_info
from ....models.match_spec import MatchSpec

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ....core.link import UnlinkLinkTransaction
    from ....models.records import PackageCacheRecord


def require_installed_plugin_specs(specs: Iterable[str], command: str) -> None:
    installed_names = frozenset(
        plugin["name"] for plugin in context.plugin_manager.get_installed_plugins()
    )
    invalid_specs: list[str] = []

    for spec in specs:
        if MatchSpec(spec).name not in installed_names:
            invalid_specs.append(spec)

    if invalid_specs:
        installed = ", ".join(sorted(installed_names)) or "none"
        raise CondaValueError(
            f"`conda plugins {command}` can only operate on installed conda "
            f"plugin packages. Not installed as conda plugins: "
            f"{', '.join(invalid_specs)}. Installed conda plugins: {installed}."
        )


def require_plugin_install_transaction(
    unlink_link_transaction: UnlinkLinkTransaction,
    *,
    inspect_link_precs: bool = False,
) -> None:
    """Validate requested plugin install specs in a transaction."""
    invalid_specs = []

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
