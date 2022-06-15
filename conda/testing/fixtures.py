# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from typing import Callable
import warnings
import py
import pytest
from _pytest.capture import CaptureResult

from conda.base.context import context
from conda.cli.conda_argparse import do_call, generate_parser
from conda.gateways.disk.create import TemporaryDirectory
from conda.core.subdir_data import SubdirData
from conda.auxlib.ish import dals
from conda.base.context import reset_context, context
from conda.common.configuration import YamlRawParameter
from conda.common.compat import odict
from conda.common.serialize import yaml_round_trip_load
from conda_env.cli.main import create_parser as env_create_parser, do_call as env_do_call


@pytest.fixture(autouse=True)
def suppress_resource_warning():
    """
    Suppress `Unclosed Socket Warning`

    It seems urllib3 keeps a socket open to avoid costly recreation costs.

    xref: https://github.com/kennethreitz/requests/issues/1882
    """
    warnings.filterwarnings("ignore", category=ResourceWarning)


@pytest.fixture(scope='function')
def tmpdir(tmpdir, request):
    tmpdir = TemporaryDirectory(dir=str(tmpdir))
    request.addfinalizer(tmpdir.cleanup)
    return py.path.local(tmpdir.name)


@pytest.fixture(autouse=True)
def clear_subdir_cache():
    SubdirData.clear_cached_local_channel_data()


@pytest.fixture(scope="function")
def disable_channel_notices():
    """
    Fixture that will set "context.number_channel_notices" to 0 and then set
    it back to its original value.

    This is also a good example of how to override values in the context object.
    """
    yaml_str = dals(
        """
        number_channel_notices: 0
        """
    )
    reset_context(())
    rd = odict(
        testdata=YamlRawParameter.make_raw_parameters("testdata", yaml_round_trip_load(yaml_str))
    )
    context._set_raw_data(rd)

    yield

    reset_context(())


@pytest.fixture(scope="function")
def reset_conda_context():
    """
    Resets the context object after each test function is run.
    """
    yield

    reset_context()

def get_do_call(capsys, parser_func: Callable, do_call_func: Callable) -> Callable:
    """
    Returns a function that testers can use to call either conda or conda env commands.

    The parser_func and do_call_func parameters are meant to be filled in either by
    conda or conda_env equivalents.

    The function that is returned allows you to pass in arguments such as:
    - ['create', '-n', 'my-env', '-y']
    - ['rename', '-n', 'my-env', 'another-env']
    - ['info', '--json']
    - (basically all conda commands minus the word "conda")

    We want this to be just like you are calling conda on the CLI to make intended usage
    from tests very clear (if you have the built-in `subprocess.run` this should feel
    familiar).

    For introspection, we use the pytest capsys fixture to capture out/err. This is
    returned when the return function is called.
    """

    def _do_call(args) -> CaptureResult:
        """ """
        capsys.readouterr()  # Flushes previous output that we don't want to include

        parser = parser_func()
        args = parser.parse_args(args)

        # Update context with values from our parser
        context._set_argparse_args(args)
        do_call_func(args, parser)

        return capsys.readouterr()

    return _do_call


@pytest.fixture
def conda_cli(capsys):
    return get_do_call(capsys, generate_parser, do_call)


@pytest.fixture
def conda_env_cli(capsys):
    return get_do_call(capsys, env_create_parser, env_do_call)
