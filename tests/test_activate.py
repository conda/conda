from __future__ import print_function, absolute_import

import os
from os.path import dirname, join

from conda.compat import TemporaryDirectory
from conda.config import root_dir
from .helpers import run_in

# Only run these tests for commands that are installed.

shells = []
for shell in ['bash', 'zsh']:
    try:
        stdout, stderr = run_in('echo', shell)
    except OSError:
        pass
    else:
        if not stderr:
            shells.append(shell)

activate = join(dirname(dirname(__file__)), 'bin', 'activate')
deactivate = join(dirname(dirname(__file__)), 'bin', 'deactivate')
# Make sure the subprocess activate calls this python
syspath = join(root_dir, 'bin')
PATH = ':'.join(['/bin', '/usr/bin'])
ROOTPATH = syspath + ':' + PATH
PYTHONPATH = os.path.dirname(os.path.dirname(__file__))

setup = """\
export PATH="{ROOTPATH}"
export PS1='$'
export PYTHONPATH="{PYTHONPATH}"
cd {here}
""".format(here=dirname(__file__), ROOTPATH=ROOTPATH, PYTHONPATH=PYTHONPATH)

setup = setup + """
mkdir -p {envs}/test1/bin
mkdir -p {envs}/test2/bin
"""

def test_activate_test1():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (setup + """
            source {activate} {envs}/test1
            printf $PATH
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == envs + "/test1/bin:" + PATH
            assert stderr == 'prepending {envs}/test1/bin to PATH\n'.format(envs=envs)

def test_activate_test1_test2():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {activate} {envs}/test2
            printf $PATH
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == envs + "/test2/bin:" + PATH
            assert stderr == 'discarding {envs}/test1/bin from PATH\nprepending {envs}/test2/bin to PATH\n'.format(envs=envs)

def test_activate_test3():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (setup + """
            source {activate} {envs}/test3
            printf $PATH
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

def test_activate_test1_test3():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {activate} {envs}/test3
            printf $PATH
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == envs + "/test1/bin:" + PATH
            assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)


def test_deactivate():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (setup + """
            source {deactivate}
            printf $PATH
            """).format(envs=envs, deactivate=deactivate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'Error: No environment to deactivate\n'


def test_activate_test1_deactivate():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {deactivate}
            printf $PATH
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'discarding {envs}/test1/bin from PATH\n'.format(envs=envs)

def test_wrong_args():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (setup + """
            source {activate}
            printf $PATH
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'Error: no environment provided.\n'

            commands = (setup + """
            source {activate} two args
            printf $PATH
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'Error: did not expect more than one argument.\n'

            commands = (setup + """
            source {deactivate} test
            printf $PATH
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'Error: too many arguments.\n'

            commands = (setup + """
            source {deactivate} {envs}/test
            printf $PATH
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'Error: too many arguments.\n'

def test_activate_help():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (setup + """
            {activate} {envs}/test1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert "Usage: source activate ENV" in stderr

            commands = (setup + """
            source {activate} --help
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert "Usage: source activate ENV" in stderr

            commands = (setup + """
            {deactivate}
            """).format(envs=envs, deactivate=deactivate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert "Usage: source deactivate" in stderr

            commands = (setup + """
            source {deactivate} --help
            """).format(envs=envs, deactivate=deactivate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert "Usage: source deactivate" in stderr

# TODO:
# - Test activating an env by name
# - Test activating "root"
# - Test PS1
# - Test CONDA_DEFAULT_ENV
