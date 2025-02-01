# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from shutil import which

import pytest

from conda import __version__ as conda_version

from . import InteractiveShell

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "shell_name",
    [
        pytest.param(
            "csh",
            marks=[
                pytest.mark.skipif(not which("csh"), reason="csh not installed"),
                pytest.mark.xfail(
                    reason="pure csh doesn't support argument passing to sourced scripts"
                ),
            ],
        ),
        pytest.param(
            "tcsh",
            marks=[
                pytest.mark.skipif(not which("tcsh"), reason="tcsh not installed"),
                pytest.mark.xfail(
                    reason="punting until we officially enable support for tcsh"
                ),
            ],
        ),
    ],
)
def test_basic_integration(
    shell_wrapper_integration: tuple[str, str, str],
    shell_name: str,
):
    prefix, _, _ = shell_wrapper_integration
    with InteractiveShell(shell_name) as sh:
        sh.sendline("conda --version")
        sh.expect_exact("conda " + conda_version)
        sh.assert_env_var("CONDA_SHLVL", "0")
        sh.sendline("conda activate base")
        sh.assert_env_var("prompt", "(base).*")
        sh.assert_env_var("CONDA_SHLVL", "1")
        sh.sendline(f'conda activate "{prefix}"')
        sh.assert_env_var("CONDA_SHLVL", "2")
        sh.assert_env_var("CONDA_PREFIX", prefix, True)
        sh.sendline("conda deactivate")
        sh.assert_env_var("CONDA_SHLVL", "1")
        sh.sendline("conda deactivate")
        sh.assert_env_var("CONDA_SHLVL", "0")

        assert "CONDA_PROMPT_MODIFIER" not in str(sh.p.after)

        sh.sendline("conda deactivate")
        sh.assert_env_var("CONDA_SHLVL", "0")
