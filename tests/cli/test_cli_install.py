# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda.base.context import context
from conda.exceptions import UnsatisfiableError
from conda.gateways.disk.delete import rm_rf
from conda.models.match_spec import MatchSpec
from conda.testing.integration import Commands, run_command


@pytest.fixture
def prefix(tmpdir):
    prefix = tmpdir.mkdir("cli_install_prefix")
    test_env = tmpdir.mkdir("cli_install_test_env")
    run_command(Commands.CREATE, str(prefix), "python=3.9")
    yield str(prefix), str(test_env)
    rm_rf(prefix)
    rm_rf(test_env)


@pytest.mark.integration
def test_pre_link_message(test_recipes_channel: None, mocker, prefix):
    prefix, _ = prefix
    mocker.patch("conda.cli.common.confirm_yn", return_value=True)
    stdout, _, _ = run_command(
        Commands.INSTALL, prefix, "pre_link_messages_package", "--use-local"
    )
    assert "Lorem ipsum dolor sit amet" in stdout


@pytest.mark.skipif(
    context.solver == "libmamba",
    reason="conda-libmamba-solver does not use the Resolve interface",
)
@pytest.mark.integration
def test_find_conflicts_called_once(mocker, prefix):
    prefix, test_env = prefix
    bad_deps = {
        "python": {
            (
                (
                    MatchSpec("statistics"),
                    MatchSpec("python[version='>=2.7,<2.8.0a0']"),
                ),
                "python=3",
            )
        }
    }
    mocked_find_conflicts = mocker.patch(
        "conda.resolve.Resolve.find_conflicts",
        side_effect=UnsatisfiableError(bad_deps, strict=True),
    )
    with pytest.raises(UnsatisfiableError):
        # Statistics is a py27 only package allowing us a simple unsatisfiable case
        run_command(Commands.INSTALL, prefix, "statistics")
    assert mocked_find_conflicts.call_count == 1

    mocked_find_conflicts.reset_mock()
    with pytest.raises(UnsatisfiableError):
        run_command(Commands.INSTALL, prefix, "statistics", "--freeze-installed")
    assert mocked_find_conflicts.call_count == 1

    mocked_find_conflicts.reset_mock()
    with pytest.raises(UnsatisfiableError):
        # statistics seems to be available on 3.10 though
        run_command(Commands.CREATE, test_env, "statistics", "python=3.9")
    assert mocked_find_conflicts.call_count == 1
