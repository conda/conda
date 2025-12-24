"""CLI reimplementation for update"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def execute(args: Namespace, parser: ArgumentParser) -> int:
    from rattler import MatchSpec

    from conda.base.context import context
    from conda.exceptions import ArgumentError
    from conda.history import History

    from .common import as_virtual_package
    from .install import install, installed_packages

    prefix = context.target_prefix

    history = [
        MatchSpec(str(spec))
        for spec in History(prefix).get_requested_specs_map().values()
    ]
    installed = {
        pkg.name.normalized: pkg for pkg in installed_packages(context.target_prefix)
    }
    specs = []
    for spec in args.packages:
        spec = MatchSpec(spec)
        if spec.name.normalized not in installed:
            raise ArgumentError(
                "conda update only allows updating installed packages; use conda install."
            )
        if str(spec) != spec.name.normalized:
            raise ArgumentError(
                "conda update only allows name-only specs; use conda install."
            )

    virtual_packages = [
        as_virtual_package(pkg)
        for pkg in context.plugin_manager.get_virtual_package_records()
    ]
    install(
        specs=specs,
        history=history,
        channels=context.channels,
        platform=context.subdir,
        target_prefix=context.target_prefix,
        locked_packages=list(installed.values()),
        virtual_packages=virtual_packages,
        report=not context.quiet and not context.json,
        verbose=context.verbosity >= 1,
        dry_run=context.dry_run,
    )

    return 0
