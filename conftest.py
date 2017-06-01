import sys
import warnings

import pytest

from conda.common.compat import PY3

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


@pytest.fixture()
def suppress_resource_warning():
    # suppress unclosed socket warning
    # https://github.com/kennethreitz/requests/issues/1882
    if PY3:
        warnings.filterwarnings("ignore", category=ResourceWarning)
