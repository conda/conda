# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path

from conda.auxlib.ish import dals
from conda.testing import CondaCLIFixture, TmpEnvFixture


def test_compare_success(
    test_recipes_channel: Path, tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture
):
    with tmp_env("dependent=1.0") as prefix:
        env_file = prefix / "env.yml"
        env_file.write_text(
            dals(
                """
                name: dummy
                dependencies:
                  - dependency
                """
            )
        )
        output, _, _ = conda_cli(
            "compare",
            f"--prefix={prefix}",
            env_file,
            "--json",
        )
        assert "Success" in output


def test_compare_fail(
    test_recipes_channel: Path, tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture
):
    with tmp_env("dependent=1.0") as prefix:
        env_file = prefix / "env.yml"
        env_file.write_text(
            dals(
                """
                name: dummy
                dependencies:
                  - something-random
                """
            )
        )
        output, _, _ = conda_cli(
            "compare",
            f"--prefix={prefix}",
            env_file,
            "--json",
        )
        assert "something-random not found" in output
