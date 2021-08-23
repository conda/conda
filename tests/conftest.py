from functools import partial
import os
import sys
import warnings

import py
import pytest

from conda.common.compat import PY3
from conda.gateways.disk.create import TemporaryDirectory
from conda.core.subdir_data import SubdirData

win_default_shells = ["cmd.exe", "powershell", "git_bash", "cygwin"]
shells = ["bash", "zsh"]

if sys.platform == "win32":
    shells = win_default_shells


def pytest_addoption(parser):
    parser.addoption("--shell", action="append", default=[],
                     help="list of shells to run shell tests on")


def pytest_generate_tests(metafunc):
    if 'shell' in metafunc.fixturenames:
        metafunc.parametrize("shell", metafunc.config.option.shell)


@pytest.fixture(autouse=True)
def suppress_resource_warning():
    '''
Suppress `Unclosed Socket Warning`

It seems urllib3 keeps a socket open to avoid costly recreation costs.

xref: https://github.com/kennethreitz/requests/issues/1882
'''
    if PY3:
        warnings.filterwarnings("ignore", category=ResourceWarning)

@pytest.fixture(scope='function')
def tmpdir(tmpdir, request):
    tmpdir = TemporaryDirectory(dir=str(tmpdir))
    request.addfinalizer(tmpdir.cleanup)
    return py.path.local(tmpdir.name)


@pytest.fixture(autouse=True)
def clear_subdir_cache():
    SubdirData.clear_cached_local_channel_data()
