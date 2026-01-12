# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Health check: Environment listed in environments.txt."""

from __future__ import annotations

from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING

from .....base.constants import OK_MARK, X_MARK
from .....core.envs_manager import get_user_environments_txt_file, register_env
from .... import hookimpl
from ....types import CondaHealthCheck

if TYPE_CHECKING:
    import os
    from argparse import Namespace
    from collections.abc import Iterable

    from ....types import ConfirmCallback

logger = getLogger(__name__)


def check_envs_txt_file(prefix: str | os.PathLike | Path) -> bool:
    """Checks whether the environment is listed in the environments.txt file."""
    prefix = Path(prefix)
    envs_txt_file = Path(get_user_environments_txt_file())

    def samefile(path1: Path, path2: Path) -> bool:
        try:
            return path1.samefile(path2)
        except FileNotFoundError:
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


def env_txt_check(prefix: str, verbose: bool) -> None:
    """Health check action: Check if environment is in environments.txt."""
    if check_envs_txt_file(prefix):
        print(f"{OK_MARK} The environment is listed in the environments.txt file.\n")
    else:
        print(f"{X_MARK} The environment is not listed in the environments.txt file.\n")


def fix_env_txt(prefix: str, args: Namespace, confirm: ConfirmCallback) -> int:
    """Register environment in environments.txt."""
    if check_envs_txt_file(prefix):
        print(f"Environment is already registered in environments.txt: {prefix}")
        return 0

    envs_txt = get_user_environments_txt_file()
    print(f"Environment not found in {envs_txt}")
    print(f"  Environment: {prefix}")

    print()
    confirm("Register this environment?")

    register_env(prefix)
    print(f"Environment registered: {prefix}")
    return 0


@hookimpl
def conda_health_checks() -> Iterable[CondaHealthCheck]:
    """Register the environment.txt health check."""
    yield CondaHealthCheck(
        name="environment-txt",
        action=env_txt_check,
        fixer=fix_env_txt,
        summary="Verify environment is registered in environments.txt",
        fix="Add environment to environments.txt",
    )
