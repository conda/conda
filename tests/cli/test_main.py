# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda.testing import CondaCLIFixture


def test_main():
    with pytest.raises(SystemExit):
        __import__("conda.__main__")


@pytest.mark.parametrize("option", ("--trace", "-v", "--debug", "--json"))
def test_ensure_no_command_provided_returns_help(
    conda_cli: CondaCLIFixture, capsys, option
):
    """
    Regression test to make sure that invoking with just any of the options listed as parameters
    will not return a traceback.
    """
    with pytest.raises(SystemExit):
        conda_cli(option)

    captured = capsys.readouterr()

    assert "error: the following arguments are required: COMMAND" in captured.err
