# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from pytest import MonkeyPatch

from conda.base.context import context, reset_context
from conda.testing import CondaCLIFixture

from . import support_file
from .utils import make_temp_envs_dir


@pytest.mark.integration
def test_update_no_imports_after_install(
    conda_cli: CondaCLIFixture, monkeypatch: MonkeyPatch
):
    # It is possible that "conda env update" will change the modules in conda itself.
    # If this occurs it may not be possible to import new modules because the underlying
    # file have moved or been removed.
    # See https://github.com/conda/conda/issues/13560 for more details
    with make_temp_envs_dir() as envs_dir:
        monkeypatch.setenv("CONDA_ENVS_DIRS", envs_dir)
        reset_context()
        assert context.envs_dirs[0] == envs_dir

        env_name = str(uuid4())[:8]
        prefix = Path(envs_dir, env_name)

        conda_cli(
            *("env", "create"),
            *("--name", env_name),
            *("--file", support_file("simple.yml")),
        )
        assert prefix.exists()

        # Remove all conda modules from sys.modules
        # Ideally all modules would be removed but this is not safe.
        for key in tuple(sys.modules.keys()):
            if key.startswith("conda"):
                print(key)
                del sys.modules[key]

        import conda.env.installers.conda
        from conda.env.installers.conda import install as real_install

        module_count_before_update = None

        def patched_install(prefix, specs, args, env, *_, **kwargs):
            nonlocal module_count_before_update
            result = real_install(prefix, specs, args, env, **kwargs)
            module_count_before_update = len(sys.modules)
            return result

        monkeypatch.setattr(conda.env.installers.conda, "install", patched_install)

        conda_cli(
            *("env", "update"),
            *("--name", env_name),
            *("--file", support_file("simple.yml")),
        )

        # Compare the module count after the install portion of the env update
        # to the count after the entire command completes.
        # If these are different a module was imported after the install step which
        # might fail if the module was removed in the install step.
        module_count_after_update = len(sys.modules)
        assert module_count_before_update == module_count_after_update
