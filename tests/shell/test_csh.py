# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from shutil import which
from typing import TYPE_CHECKING

import pytest

from conda import __version__ as conda_version

from . import InteractiveShell

if TYPE_CHECKING:
    from typing import Callable

pytestmark = pytest.mark.integration


def basic_csh(shell, prefix, prefix2, prefix3):
    shell.sendline("conda --version")
    shell.expect_exact("conda " + conda_version)
    shell.assert_env_var("CONDA_SHLVL", "0")
    shell.sendline("conda activate base")
    shell.assert_env_var("prompt", "(base).*")
    shell.assert_env_var("CONDA_SHLVL", "1")
    shell.sendline(f'conda activate "{prefix}"')
    shell.assert_env_var("CONDA_SHLVL", "2")
    shell.assert_env_var("CONDA_PREFIX", prefix, True)
    shell.sendline("conda deactivate")
    shell.assert_env_var("CONDA_SHLVL", "1")
    shell.sendline("conda deactivate")
    shell.assert_env_var("CONDA_SHLVL", "0")

    assert "CONDA_PROMPT_MODIFIER" not in str(shell.p.after)

    shell.sendline("conda deactivate")
    shell.assert_env_var("CONDA_SHLVL", "0")


@pytest.mark.parametrize(
    "shell_name,script",
    [
        pytest.param(
            "csh",
            basic_csh,
            marks=[
                pytest.mark.skipif(not which("csh"), reason="csh not installed"),
                pytest.mark.xfail(
                    reason="pure csh doesn't support argument passing to sourced scripts"
                ),
            ],
        ),
        pytest.param(
            "tcsh",
            basic_csh,
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
    script: Callable[[InteractiveShell, str, str, str], None],
):
    with InteractiveShell(shell_name) as shell:
        script(shell, *shell_wrapper_integration)
