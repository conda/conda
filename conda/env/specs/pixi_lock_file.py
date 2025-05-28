# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define pixi.lock spec."""

from __future__ import annotations

import os
from logging import getLogger
from typing import TYPE_CHECKING

from ...base.context import context
from ...common.serialize import yaml_safe_load
from ...exceptions import CondaError
from ...plugins.types import EnvironmentSpecBase
from ..env import Environment

if TYPE_CHECKING:
    from typing import Any

log = getLogger(__name__)


class PixiLockFile(EnvironmentSpecBase):
    extensions = {".lock"}

    def __init__(
        self,
        filename=None,
        lock_environment_name="default",
        platform=context.subdir,
        **kwargs,
    ):
        self.filename: str = filename
        self._yaml_data: dict[str, Any] | None = None
        self._lock_environment_name = lock_environment_name
        self._platform = platform

    def can_handle(self) -> bool:
        """
        Validates loader can process environment definition.
        This can handle if:
            * the provided file exists
            * the provided file ends in .lock
            * the file has pixi.lock like fields.
        """
        # Extract the file extension (e.g., '.txt' or '' if no extension)
        _, file_ext = os.path.splitext(self.filename)

        # Check if the file has a supported extension and exists
        if not any(spec_ext == file_ext for spec_ext in PixiLockFile.extensions):
            return False

        try:
            with open(self.filename, "rb") as fp:
                yamlb = fp.read()
                yamlstr = yamlb.decode("utf-8")
                yaml_data: dict[str, Any] = yaml_safe_load(yamlstr)
                if "environments" in yaml_data and yaml_data.get("version") == 6:
                    self._yaml_data = yaml_data
                    return True
            return False
        except Exception:
            log.debug("Failed to load %s as `pixi.lock`.", self.filename, exc_info=True)
            return False

    @property
    def environment(self):
        # read in data if needed
        if not self._yaml_data:
            self.can_handle()

        # validate that the environment exists in the lock file
        lock_environment = self._lock_environment_name
        env = self._yaml_data["environments"].get(lock_environment)
        if not env:
            raise CondaError(
                f"Environment {lock_environment} not found. "
                f"Available environment names: {sorted(self._yaml_data['environments'])}."
            )

        # validate that the lock file specifies an environment for the target platform
        env_packages = env["packages"].get(self._platform)
        if not env_packages:
            raise CondaError(
                f"Environment {lock_environment} does not list packages for platform "
                f"{self._platform}. Available platforms: {sorted(env['packages'])}."
            )

        # parse the conda and pypi packages
        conda: dict[str, dict[str, Any]] = {}
        pypi: dict[str, dict[str, Any]] = {}
        for env_package in env_packages:
            for package_type, url in env_package.items():
                if package_type == "conda":
                    conda[url] = {}
                elif package_type == "pypi":
                    pypi[url] = {}
        for pkg_metadata in self._yaml_data.get("packages", ()):
            if "conda" in pkg_metadata:
                url = pkg_metadata["conda"]
                if url in conda:
                    conda[url].update(pkg_metadata)
                    conda[url].pop("conda", None)
            elif "pypi" in pkg_metadata:
                url = pkg_metadata["pypi"]
                if url in pypi:
                    pypi[url].update(pkg_metadata)
                    pypi[url].pop("pypi", None)

        # create an Environment instance that described the environment
        dependencies = []
        if conda:
            dependencies.append({"conda_direct": conda})
        if pypi:
            dependencies.append({"pip_direct": pypi})
        environment = Environment(
            dependencies=dependencies,
        )
        return environment
