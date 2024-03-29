# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import importlib

import pytest


@pytest.mark.parametrize(
    "old_path, new_path",
    [
        ("conda_env.cli.common.base_env_name", "conda.base.constants.ROOT_ENV_NAME"),
        ("conda_env.cli.common.print_result", "conda.env.env.print_result"),
        ("conda_env.cli.common.get_filename", "conda.env.env.get_filename"),
        ("conda_env.cli.main.show_help_on_empty_command", None),
        ("conda_env.cli.main.create_parser", None),
        ("conda_env.cli.main.do_call", None),
        ("conda_env.cli.main.main", None),
        ("conda_env.cli.main_config.config_description", None),
        ("conda_env.cli.main_config.config_example", None),
        (
            "conda_env.cli.main_config.configure_parser",
            "conda.cli.main_env_config.configure_parser",
        ),
        ("conda_env.cli.main_config.execute", "conda.cli.main_env_config.execute"),
        ("conda_env.cli.main_create.description", None),
        ("conda_env.cli.main_create.example", None),
        (
            "conda_env.cli.main_create.configure_parser",
            "conda.cli.main_env_create.configure_parser",
        ),
        ("conda_env.cli.main_create.execute", "conda.cli.main_env_create.execute"),
        ("conda_env.cli.main_export.description", None),
        ("conda_env.cli.main_export.example", None),
        (
            "conda_env.cli.main_export.configure_parser",
            "conda.cli.main_export.configure_parser",
        ),
        ("conda_env.cli.main_export.execute", "conda.cli.main_export.execute"),
        (
            "conda_env.cli.main_export.configure_parser",
            "conda.cli.main_env_export.configure_parser",
        ),
        ("conda_env.cli.main_export.execute", "conda.cli.main_env_export.execute"),
        ("conda_env.cli.main_list.description", None),
        ("conda_env.cli.main_list.example", None),
        (
            "conda_env.cli.main_list.configure_parser",
            "conda.cli.main_env_list.configure_parser",
        ),
        ("conda_env.cli.main_list.execute", "conda.cli.main_env_list.execute"),
        ("conda_env.cli.main_remove._help", None),
        ("conda_env.cli.main_remove._description", None),
        ("conda_env.cli.main_remove._example", None),
        (
            "conda_env.cli.main_remove.configure_parser",
            "conda.cli.main_env_remove.configure_parser",
        ),
        ("conda_env.cli.main_remove.execute", "conda.cli.main_env_remove.execute"),
        ("conda_env.cli.main_update.description", None),
        ("conda_env.cli.main_update.example", None),
        (
            "conda_env.cli.main_update.configure_parser",
            "conda.cli.main_env_update.configure_parser",
        ),
        ("conda_env.cli.main_update.execute", "conda.cli.main_env_update.execute"),
        ("conda_env.cli.main_vars.var_description", None),
        ("conda_env.cli.main_vars.var_example", None),
        ("conda_env.cli.main_vars.list_description", None),
        ("conda_env.cli.main_vars.list_example", None),
        ("conda_env.cli.main_vars.set_description", None),
        ("conda_env.cli.main_vars.set_example", None),
        ("conda_env.cli.main_vars.unset_description", None),
        ("conda_env.cli.main_vars.unset_example", None),
        (
            "conda_env.cli.main_vars.configure_parser",
            "conda.cli.main_env_vars.configure_parser",
        ),
        (
            "conda_env.cli.main_vars.execute_list",
            "conda.cli.main_env_vars.execute_list",
        ),
        ("conda_env.cli.main_vars.execute_set", "conda.cli.main_env_vars.execute_set"),
        (
            "conda_env.cli.main_vars.execute_unset",
            "conda.cli.main_env_vars.execute_unset",
        ),
        ("conda_env.env.VALID_KEYS", "conda.env.env.VALID_KEYS"),
        ("conda_env.env.validate_keys", "conda.env.env.validate_keys"),
        ("conda_env.env.from_environment", "conda.env.env.from_environment"),
        ("conda_env.env.from_yaml", "conda.env.env.from_yaml"),
        ("conda_env.env._expand_channels", "conda.env.env._expand_channels"),
        ("conda_env.env.from_file", "conda.env.env.from_file"),
        ("conda_env.env.Dependencies", "conda.env.env.Dependencies"),
        ("conda_env.env.Environment", "conda.env.env.Environment"),
        ("conda_env.installers.base.ENTRY_POINT", None),
        (
            "conda_env.installers.base.InvalidInstaller",
            "conda.exceptions.InvalidInstaller",
        ),
        (
            "conda_env.installers.base.get_installer",
            "conda.env.installers.base.get_installer",
        ),
        ("conda_env.installers.conda._solve", "conda.env.installers.conda._solve"),
        ("conda_env.installers.conda.dry_run", "conda.env.installers.conda.dry_run"),
        ("conda_env.installers.conda.install", "conda.env.installers.conda.install"),
        (
            "conda_env.installers.pip._pip_install_via_requirements",
            "conda.env.installers.pip._pip_install_via_requirements",
        ),
        ("conda_env.installers.pip.install", "conda.env.installers.pip.install"),
        ("conda_env.pip_util.pip_subprocess", "conda.env.pip_util.pip_subprocess"),
        (
            "conda_env.pip_util.get_pip_installed_packages",
            "conda.env.pip_util.get_pip_installed_packages",
        ),
        ("conda_env.pip_util._canonicalize_regex", None),
        (
            "conda_env.specs.get_spec_class_from_file",
            "conda.env.specs.get_spec_class_from_file",
        ),
        ("conda_env.specs.FileSpecTypes", "conda.env.specs.FileSpecTypes"),
        ("conda_env.specs.SpecTypes", "conda.env.specs.SpecTypes"),
        ("conda_env.specs.detect", "conda.env.specs.detect"),
        (
            "conda_env.specs.binstar.ENVIRONMENT_TYPE",
            "conda.env.specs.binstar.ENVIRONMENT_TYPE",
        ),
        ("conda_env.specs.binstar.BinstarSpec", "conda.env.specs.binstar.BinstarSpec"),
        (
            "conda_env.specs.requirements.RequirementsSpec",
            "conda.env.specs.requirements.RequirementsSpec",
        ),
        (
            "conda_env.specs.yaml_file.EnvironmentFileSpec",
            "conda.env.specs.yaml_file.EnvironmentFileSpec",
        ),
    ],
)
def test_moved_conda_env_module_imports(old_path: str, new_path: str | None):
    old_module, old_name = old_path.rsplit(".", 1)
    old = getattr(importlib.import_module(old_module), old_name)

    if not new_path:
        # the old thing is deprecated! nothing new to compare it with!
        assert old
    else:
        # the old thing has moved to a new place!
        new_module, new_name = new_path.rsplit(".", 1)
        new = getattr(importlib.import_module(new_module), new_name)
        assert old is new
