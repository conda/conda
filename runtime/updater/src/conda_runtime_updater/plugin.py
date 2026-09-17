# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Coordinate stamped executable updates with root-prefix conda transactions."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from conda import plugins
from conda.base.constants import UpdateModifier
from conda.base.context import context
from conda.common.path import paths_equal
from conda.exceptions import CondaError, CondaSystemExit
from conda.models.match_spec import MatchSpec
from conda.plugins.types import CondaPostCommand, CondaPreSolve
from conda.reporters import confirm_yn

from .helper import invoke_helper, validate_check
from .locking import acquire_lock, release_lock
from .metadata import conda_version_from_runtime, discover_runtime

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import BinaryIO

    from .metadata import RuntimeMetadata


@dataclass
class UpdateSession:
    runtime: RuntimeMetadata
    lock: BinaryIO


_session: UpdateSession | None = None


def should_coordinate(specs_to_add: frozenset[MatchSpec]) -> bool:
    """Return whether this solve can update the managed root conda package."""

    return paths_equal(context.target_prefix, context.root_prefix) and (
        context.update_modifier == UpdateModifier.UPDATE_ALL
        or any(spec.name == "conda" for spec in specs_to_add)
    )


def pin_runtime_conda(runtime_version: str) -> None:
    """Pin the inner conda package to the outer runtime release."""

    conda_version = conda_version_from_runtime(runtime_version)
    pins = tuple(pin for pin in context.pinned_packages if MatchSpec(pin).name != "conda")
    context.pinned_packages = (*pins, f"conda =={conda_version}")


def pre_solve(
    specs_to_add: frozenset[MatchSpec],
    specs_to_remove: frozenset[MatchSpec],
) -> None:
    """Check and stage an outer update before a matching root solve."""

    del specs_to_remove
    global _session

    if _session is not None or not should_coordinate(specs_to_add):
        return

    runtime = discover_runtime(Path(context.root_prefix))
    if runtime is None:
        return
    if context.ignore_pinned:
        raise CondaError("The conda runtime update cannot be coordinated with --no-pin.")
    if context.dry_run:
        pin_runtime_conda(runtime.version)
        return

    lock = acquire_lock(runtime.lock_path)
    try:
        result = invoke_helper(runtime, "check")
        check = validate_check(result, runtime)
        if not check["available"]:
            pin_runtime_conda(runtime.version)
            return

        candidate_version = check["version"]
        conda_version_from_runtime(candidate_version)
        if runtime.ownership == "external":
            instruction = (
                check["instruction"]
                or runtime.instruction
                or (
                    "Update the conda executable with the package manager that installed it, "
                    "then retry."
                )
            )
            raise CondaError(instruction)

        if not context.json:
            try:
                confirm_yn(
                    f"Update the conda runtime to {candidate_version} together with "
                    "its managed conda installation?",
                    default="yes",
                )
            except CondaSystemExit as error:
                error.allow_retry = False
                raise

        staged = invoke_helper(runtime, "stage", candidate=check["sha256"])
        if staged.get("staged") is not True:
            raise CondaError("The conda binary update was not staged.")

        pin_runtime_conda(candidate_version)
        _session = UpdateSession(runtime=runtime, lock=lock)
        lock = None
    finally:
        if lock is not None:
            release_lock(lock)


def post_command(command: str) -> None:
    """Apply a staged outer update after the inner command succeeds."""

    del command
    global _session

    if _session is None:
        return

    session = _session
    _session = None
    failure: Exception | None = None
    try:
        applied = invoke_helper(session.runtime, "apply")
        if applied.get("applied") is not True and applied.get("replacement_pending") is not True:
            raise CondaError("The conda binary update was not applied.")
    except Exception as error:
        failure = error
    try:
        release_lock(session.lock)
    except Exception as error:
        if failure is None:
            failure = error

    if failure is None:
        return
    if not context.json:
        raise failure
    if not context.quiet:
        print(
            "The conda package update succeeded, but the executable update requires "
            f"recovery: {failure}",
            file=sys.stderr,
        )


@plugins.hookimpl
def conda_pre_solves() -> Iterable[CondaPreSolve]:
    yield CondaPreSolve(name="conda-runtime-update", action=pre_solve)


@plugins.hookimpl
def conda_post_commands() -> Iterable[CondaPostCommand]:
    yield CondaPostCommand(
        name="conda-runtime-update",
        action=post_command,
        run_for={"create", "env_update", "install", "update"},
    )
