from __future__ import print_function, absolute_import

import os
from os.path import dirname, join
import shutil
import stat
import subprocess

import pytest

from conda.compat import TemporaryDirectory
from conda.config import root_dir, platform
from tests.helpers import run_in

# Only run these tests for commands that are installed.


if platform == 'win':
    skip_tests = True
    shells = []
else:

    shells = []
    for shell in ['bash', 'zsh']:
        try:
            stdout, stderr = run_in('echo', shell)
        except OSError:
            pass
        else:
            if not stderr:
                shells.append(shell)

        # activate and deactivate are no longer part conda, so we can't copy them
        # from the source tree.  They should normally be installed, so this pulls
        # them from the path.
        process = subprocess.Popen(['which', 'activate'], stdout=subprocess.PIPE)
        output = process.communicate()[0]
        activate_path = output.strip().decode('utf-8')
        deactivate_path = join(dirname(activate_path), 'deactivate')



def _write_entry_points(envs):
    """
    Write entry points to {envs}/root/bin

    This is needed because the conda in bin/conda uses #!/usr/bin/env python,
    which doesn't work if you remove the root environment from the PATH. So we
    have to use a conda entry point that has the root Python hard-coded in the
    shebang line.
    """
    activate = activate_path
    deactivate = deactivate_path
    os.makedirs(join(envs, 'bin'))
    shutil.copy2(activate, join(envs, 'bin', 'activate'))
    shutil.copy2(deactivate, join(envs, 'bin', 'deactivate'))
    with open(join(envs, 'bin', 'conda'), 'w') as f:
        f.write(CONDA_ENTRY_POINT.format(syspath=syspath))
    os.chmod(join(envs, 'bin', 'conda'), 0o755)
    return (join(envs, 'bin', 'activate'), join(envs, 'bin', 'deactivate'),
        join(envs, 'bin', 'conda'))

# Make sure the subprocess activate calls this python
syspath = join(root_dir, 'bin')
# dirname, which is used in the activate script, is typically installed in
# /usr/bin (not sure if it has to be)
PATH = ':'.join(['/bin', '/usr/bin'])
ROOTPATH = syspath + ':' + PATH
PYTHONPATH = os.path.dirname(os.path.dirname(__file__))

CONDA_ENTRY_POINT="""\
#!{syspath}/python
import sys
from conda.cli import main

sys.exit(main())
"""

command_setup = """\
export PATH="{ROOTPATH}"
export PS1='$'
export PYTHONPATH="{PYTHONPATH}"
export CONDARC=' '
cd {here}
""".format(here=dirname(__file__), ROOTPATH=ROOTPATH, PYTHONPATH=PYTHONPATH)

command_setup = command_setup + """
mkdir -p {envs}/test1/bin
mkdir -p {envs}/test2/bin
"""


@pytest.mark.slow
def test_activate_test1():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            source {activate} {envs}/test1
            printf $PATH
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == envs + "/test1/bin:" + PATH
            assert stderr == 'discarding {syspath} from PATH\nprepending {envs}/test1/bin to PATH\n'.format(envs=envs, syspath=syspath)


@pytest.mark.slow
def test_activate_test1_test2():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {activate} {envs}/test2
            printf $PATH
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == envs + "/test2/bin:" + PATH
            assert stderr == 'discarding {envs}/test1/bin from PATH\nprepending {envs}/test2/bin to PATH\n'.format(envs=envs)


@pytest.mark.slow
def test_activate_test3():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            source {activate} {envs}/test3
            printf $PATH
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)


@pytest.mark.slow
def test_activate_test1_test3():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {activate} {envs}/test3
            printf $PATH
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == envs + "/test1/bin:" + PATH
            assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)


@pytest.mark.slow
def test_deactivate():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            source {deactivate}
            printf $PATH
            """).format(envs=envs, deactivate=deactivate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'Error: No environment to deactivate\n'


@pytest.mark.slow
def test_activate_test1_deactivate():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {deactivate}
            printf $PATH
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'discarding {envs}/test1/bin from PATH\n'.format(envs=envs)


@pytest.mark.slow
def test_wrong_args():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            source {activate}
            printf $PATH
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'Error: no environment provided.\n'

            commands = (command_setup + """
            source {activate} two args
            printf $PATH
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'Error: did not expect more than one argument.\n'

            commands = (command_setup + """
            source {deactivate} test
            printf $PATH
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'Error: too many arguments.\n'

            commands = (command_setup + """
            source {deactivate} {envs}/test
            printf $PATH
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'Error: too many arguments.\n'


@pytest.mark.slow
def test_activate_help():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {activate} {envs}/test1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert "activate must be sourced" in stderr
            assert "Usage: source activate ENV" in stderr

            commands = (command_setup + """
            source {activate} --help
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert "Usage: source activate ENV" in stderr

            commands = (command_setup + """
            {deactivate}
            """).format(envs=envs, deactivate=deactivate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert "deactivate must be sourced" in stderr
            assert "Usage: source deactivate" in stderr

            commands = (command_setup + """
            source {deactivate} --help
            """).format(envs=envs, deactivate=deactivate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert "Usage: source deactivate" in stderr


@pytest.mark.slow
@pytest.mark.skipif(True, reason="because refactor asap PR #1727")
def test_activate_symlinking():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            source {activate} {envs}/test1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert not stdout
            assert stderr == 'discarding {syspath} from PATH\nprepending {envs}/test1/bin to PATH\n'.format(envs=envs, syspath=syspath)
            for f in ['conda', 'activate', 'deactivate']:
                assert os.path.lexists('{envs}/test1/bin/{f}'.format(envs=envs, f=f))
                assert os.path.exists('{envs}/test1/bin/{f}'.format(envs=envs, f=f))
                s = os.lstat('{envs}/test1/bin/{f}'.format(envs=envs, f=f))
                assert stat.S_ISLNK(s.st_mode)
                assert os.readlink('{envs}/test1/bin/{f}'.format(envs=envs,
                    f=f)) == '{syspath}/{f}'.format(syspath=syspath, f=f)

            try:
                # Test activate when there are no write permissions in the
                # env. There are two cases:
                # - conda/deactivate/activate are already symlinked
                commands = (command_setup + """
                mkdir -p {envs}/test3/bin
                ln -s {activate} {envs}/test3/bin/activate
                ln -s {deactivate} {envs}/test3/bin/deactivate
                ln -s {conda} {envs}/test3/bin/conda
                chmod 555 {envs}/test3/bin
                source {activate} {envs}/test3
                """).format(envs=envs, activate=activate, deactivate=deactivate, conda=conda)
                stdout, stderr = run_in(commands, shell)
                assert not stdout
                assert stderr == 'discarding {syspath} from PATH\nprepending {envs}/test3/bin to PATH\n'.format(envs=envs, syspath=syspath)

                # Make sure it stays the same
                for f in ['conda', 'activate', 'deactivate']:
                    assert os.path.lexists('{envs}/test3/bin/{f}'.format(envs=envs, f=f))
                    assert os.path.exists('{envs}/test3/bin/{f}'.format(envs=envs, f=f))
                    s = os.lstat('{envs}/test3/bin/{f}'.format(envs=envs, f=f))
                    assert stat.S_ISLNK(s.st_mode)
                    assert os.readlink('{envs}/test3/bin/{f}'.format(envs=envs,
                        f=f)) == '{f}'.format(f=locals()[f])

                # - conda/deactivate/activate are not symlinked. In this case,
                # activate should fail
                commands = (command_setup + """
                mkdir -p {envs}/test4/bin
                chmod 555 {envs}/test4/bin
                source {activate} {envs}/test4
                echo $PATH
                echo $CONDA_DEFAULT_ENV
                """).format(envs=envs, activate=activate, deactivate=deactivate, conda=conda)

                stdout, stderr = run_in(commands, shell)
                assert stdout == (
                    '{ROOTPATH}\n' # PATH
                    '\n'           # CONDA_DEFAULT_ENV
                    ).format(ROOTPATH=ROOTPATH)
                assert stderr == ('Cannot activate environment {envs}/test4, '
                'do not have write access to write conda symlink\n').format(envs=envs)

            finally:
                # Change the permissions back so that we can delete the directory
                run_in('chmod 777 {envs}/test3/bin'.format(envs=envs), shell)
                run_in('chmod 777 {envs}/test4/bin'.format(envs=envs), shell)


@pytest.mark.slow
def test_PS1():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            source {activate} {envs}/test1
            printf $PS1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '({envs}/test1)$'.format(envs=envs)
            assert stderr == 'discarding {syspath} from PATH\nprepending {envs}/test1/bin to PATH\n'.format(envs=envs, syspath=syspath)

            commands = (command_setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {activate} {envs}/test2
            printf $PS1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '({envs}/test2)$'.format(envs=envs)
            assert stderr == 'discarding {envs}/test1/bin from PATH\nprepending {envs}/test2/bin to PATH\n'.format(envs=envs)

            commands = (command_setup + """
            source {activate} {envs}/test3
            printf $PS1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

            commands = (command_setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {activate} {envs}/test3
            printf $PS1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '({envs}/test1)$'.format(envs=envs)
            assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

            commands = (command_setup + """
            source {deactivate}
            printf $PS1
            """).format(envs=envs, deactivate=deactivate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: No environment to deactivate\n'

            commands = (command_setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {deactivate}
            printf $PS1
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'discarding {envs}/test1/bin from PATH\n'.format(envs=envs)

            commands = (command_setup + """
            source {activate}
            printf $PS1
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: no environment provided.\n'

            commands = (command_setup + """
            source {activate} two args
            printf $PS1
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: did not expect more than one argument.\n'

            commands = (command_setup + """
            source {deactivate} test
            printf $PS1
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: too many arguments.\n'

            commands = (command_setup + """
            source {deactivate} {envs}/test
            printf $PS1
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: too many arguments.\n'


@pytest.mark.slow
def test_PS1_no_changeps1():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            with open(join(envs, '.condarc'), 'w') as f:
                f.write("""\
changeps1: no
""")
            condarc = """
            CONDARC="{envs}/.condarc"
            """
            commands = (command_setup + condarc + """
            source {activate} {envs}/test1
            printf $PS1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'discarding {syspath} from PATH\nprepending {envs}/test1/bin to PATH\n'.format(envs=envs, syspath=syspath)

            commands = (command_setup + condarc + """
            source {activate} {envs}/test1 2> /dev/null
            source {activate} {envs}/test2
            printf $PS1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'discarding {envs}/test1/bin from PATH\nprepending {envs}/test2/bin to PATH\n'.format(envs=envs)

            commands = (command_setup + condarc + """
            source {activate} {envs}/test3
            printf $PS1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

            commands = (command_setup + condarc + """
            source {activate} {envs}/test1 2> /dev/null
            source {activate} {envs}/test3
            printf $PS1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

            commands = (command_setup + condarc + """
            source {deactivate}
            printf $PS1
            """).format(envs=envs, deactivate=deactivate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: No environment to deactivate\n'

            commands = (command_setup + condarc + """
            source {activate} {envs}/test1 2> /dev/null
            source {deactivate}
            printf $PS1
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'discarding {envs}/test1/bin from PATH\n'.format(envs=envs)

            commands = (command_setup + condarc + """
            source {activate}
            printf $PS1
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: no environment provided.\n'

            commands = (command_setup + condarc + """
            source {activate} two args
            printf $PS1
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: did not expect more than one argument.\n'

            commands = (command_setup + condarc + """
            source {deactivate} test
            printf $PS1
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: too many arguments.\n'

            commands = (command_setup + condarc + """
            source {deactivate} {envs}/test
            printf $PS1
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: too many arguments.\n'


@pytest.mark.slow
def test_CONDA_DEFAULT_ENV():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            source {activate} {envs}/test1
            printf "$CONDA_DEFAULT_ENV"
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '{envs}/test1'.format(envs=envs)
            assert stderr == 'discarding {syspath} from PATH\nprepending {envs}/test1/bin to PATH\n'.format(envs=envs, syspath=syspath)

            commands = (command_setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {activate} {envs}/test2
            printf "$CONDA_DEFAULT_ENV"
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '{envs}/test2'.format(envs=envs)
            assert stderr == 'discarding {envs}/test1/bin from PATH\nprepending {envs}/test2/bin to PATH\n'.format(envs=envs)

            commands = (command_setup + """
            source {activate} {envs}/test3
            printf "$CONDA_DEFAULT_ENV"
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

            commands = (command_setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {activate} {envs}/test3
            printf "$CONDA_DEFAULT_ENV"
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '{envs}/test1'.format(envs=envs)
            assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

            commands = (command_setup + """
            source {deactivate}
            printf "$CONDA_DEFAULT_ENV"
            """).format(envs=envs, deactivate=deactivate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert stderr == 'Error: No environment to deactivate\n'

            commands = (command_setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {deactivate}
            printf "$CONDA_DEFAULT_ENV"
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert stderr == 'discarding {envs}/test1/bin from PATH\n'.format(envs=envs)

            commands = (command_setup + """
            source {activate}
            printf "$CONDA_DEFAULT_ENV"
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert stderr == 'Error: no environment provided.\n'

            commands = (command_setup + """
            source {activate} two args
            printf "$CONDA_DEFAULT_ENV"
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert stderr == 'Error: did not expect more than one argument.\n'

            commands = (command_setup + """
            source {deactivate} test
            printf "$CONDA_DEFAULT_ENV"
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert stderr == 'Error: too many arguments.\n'

            commands = (command_setup + """
            source {deactivate} {envs}/test
            printf "$CONDA_DEFAULT_ENV"
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert stderr == 'Error: too many arguments.\n'

            # commands = (command_setup + """
            # source {activate} root
            # printf "$CONDA_DEFAULT_ENV"
            # """).format(envs=envs, deactivate=deactivate, activate=activate)
            #
            # stdout, stderr = run_in(commands, shell)
            # assert stdout == 'root'
            # assert stderr == 'Error: too many arguments.\n'

# TODO:
# - Test activating an env by name
# - Test activating "root"
# - Test activating "root" and then deactivating
