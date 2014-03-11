from __future__ import print_function, absolute_import

import sys
from os.path import dirname, join

from conda.compat import TemporaryDirectory
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
syspath = dirname(sys.executable)
PATH = ':'.join([syspath, '/bin', '/usr/bin'])

setup = """\
export PATH="{PATH}"
export PS1='$'
cd {here}
""".format(here=dirname(__file__), PATH=PATH)

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
            assert stdout == PATH
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
            assert stdout == PATH
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
            assert stdout == PATH
            assert stderr == 'discarding {envs}/test1/bin from PATH\n'.format(envs=envs)
