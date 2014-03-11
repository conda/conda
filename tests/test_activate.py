from __future__ import print_function, absolute_import

import sys
from os.path import dirname, join
import tempfile

from .helpers import run_in

# Only run these tests for commands that are installed.

shells = []
for shell in ['bash', 'zsh']:
    stdout, stderr = run_in('echo', shell)
    if not stderr:
        shells.append(shell)

activate = join(dirname(dirname(__file__)), 'bin', 'activate')
deactivate = join(dirname(dirname(__file__)), 'bin', 'deactivate')
# Make sure the subprocess activate calls this python
syspath = dirname(sys.executable)

def test_activate():
    for shell in shells:
        with tempfile.TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            PATH = ':'.join([syspath, '/bin', '/usr/bin'])
            setup = """\
            export PATH="{PATH}"
            export PS1='$'
            cd {here}
            """.format(here=dirname(__file__), PATH=PATH)

            setup_envs = setup + """\
            mkdir -p {envs}/test1/bin
            mkdir -p {envs}/test2/bin
            """.format(envs=envs)

            stdout, stderr = run_in(setup_envs, shell)
            assert not stdout
            assert not stderr

            activate_test1 = setup + """
            source {activate} {envs}/test1
            printf $PATH
            """.format(envs=envs, activate=activate)

            stdout, stderr = run_in(activate_test1, shell)
            assert stdout == envs + "/test1/bin:" + PATH
            assert stderr == 'prepending {envs}/test1/bin to PATH\n'.format(envs=envs)
