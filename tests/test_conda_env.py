# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import importlib

import pytest


@pytest.mark.parametrize(
    "conda_env_module, conda_cli_module, function_name",
    [
        ("conda_env.cli.main_config", "conda.cli.main_env_config", "configure_parser"),
        ("conda_env.cli.main_config", "conda.cli.main_env_config", "execute"),
        ("conda_env.cli.main_create", "conda.cli.main_env_create", "configure_parser"),
        ("conda_env.cli.main_create", "conda.cli.main_env_create", "execute"),
        ("conda_env.cli.main_export", "conda.cli.main_env_export", "configure_parser"),
        ("conda_env.cli.main_export", "conda.cli.main_env_export", "execute"),
        ("conda_env.cli.main_list", "conda.cli.main_env_list", "configure_parser"),
        ("conda_env.cli.main_list", "conda.cli.main_env_list", "execute"),
        ("conda_env.cli.main_remove", "conda.cli.main_env_remove", "configure_parser"),
        ("conda_env.cli.main_remove", "conda.cli.main_env_remove", "execute"),
        ("conda_env.cli.main_update", "conda.cli.main_env_update", "configure_parser"),
        ("conda_env.cli.main_update", "conda.cli.main_env_update", "execute"),
        ("conda_env.cli.main_vars", "conda.cli.main_env_vars", "configure_parser"),
        ("conda_env.cli.main_vars", "conda.cli.main_env_vars", "execute_list"),
        ("conda_env.cli.main_vars", "conda.cli.main_env_vars", "execute_set"),
        ("conda_env.cli.main_vars", "conda.cli.main_env_vars", "execute_unset"),
        ("conda_env.env", "conda.env.env", "from_environment"),
        ("conda_env.env", "conda.env.env", "from_file"),
        ("conda_env.env", "conda.env.env", "VALID_KEYS"),
        ("conda_env.env", "conda.env.env", "Dependencies"),
        ("conda_env.env", "conda.env.env", "Environment"),
        ("conda_env.env", "conda.env.env", "from_yaml"),
        ("conda_env.env", "conda.env.env", "validate_keys"),
        ("conda_env.pip_util", "conda.env.pip_util", "get_pip_installed_packages"),
        ("conda_env.pip_util", "conda.env.pip_util", "pip_subprocess"),
        (
            "conda_env.specs.requirements",
            "conda.env.specs.requirements",
            "RequirementsSpec",
        ),
        ("conda_env.specs.yaml_file", "conda.env.specs.yaml_file", "YamlFileSpec"),
        ("conda_env.specs.binstar", "conda.env.specs.binstar", "BinstarSpec"),
    ],
)
def test_moved_conda_env_module_imports(
    conda_env_module, conda_cli_module, function_name
):
    deprecated = importlib.import_module(conda_env_module)
    redirect_module = importlib.import_module(conda_cli_module)

    assert getattr(deprecated, function_name) is getattr(redirect_module, function_name)
