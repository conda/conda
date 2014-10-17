from __future__ import print_function, absolute_import

import os
from os.path import dirname, join
import shutil
import stat

from conda.compat import TemporaryDirectory
from conda.config import root_dir, platform
from tests.helpers import run_in

def assert_equals(a, b):
    assert a == b, "%r != %r" % (a, b)

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

if platform == 'win':
    shells = ['cmd.exe']

if platform == 'win':
    def _write_entry_points(envs):
        """
        Write entry points to {envs}/root/Scripts
        """
        activate = join(dirname(dirname(__file__)), 'bin', 'activate.bat')
        deactivate = join(dirname(dirname(__file__)), 'bin', 'deactivate.bat')
        os.makedirs(join(envs, 'Scripts'))
        shutil.copy2(activate, join(envs, 'Scripts', 'activate.bat'))
        shutil.copy2(deactivate, join(envs, 'Scripts', 'deactivate.bat'))
        with open(join(envs, 'Scripts', 'conda-script.py'), 'w') as f:
            f.write(CONDA_ENTRY_POINT.format(syspath=syspath))
        shutil.copy2(join(dirname(dirname(__file__)), 'bin', 'conda.exe'),
            join(envs, 'Scripts', 'conda.exe'))
        return (join(envs, 'Scripts', 'activate.bat'),
                join(envs, 'Scripts', 'deactivate.bat'),
                join(envs, 'Scripts', 'conda.exe'))
else:
    def _write_entry_points(envs):
        """
        Write entry points to {envs}/root/bin

        This is needed because the conda in bin/conda uses #!/usr/bin/env python,
        which doesn't work if you remove the root environment from the PATH. So we
        have to use a conda entry point that has the root Python hard-coded in the
        shebang line.
        """
        activate = join(dirname(dirname(__file__)), 'bin', 'activate')
        deactivate = join(dirname(dirname(__file__)), 'bin', 'deactivate')
        os.makedirs(join(envs, 'bin'))
        shutil.copy2(activate, join(envs, 'bin', 'activate'))
        shutil.copy2(deactivate, join(envs, 'bin', 'deactivate'))
        with open(join(envs, 'bin', 'conda'), 'w') as f:
            f.write(CONDA_ENTRY_POINT.format(syspath=syspath))
        os.chmod(join(envs, 'bin', 'conda'), 0o755)
        return (join(envs, 'bin', 'activate'), join(envs, 'bin', 'deactivate'),
            join(envs, 'bin', 'conda'))

# Make sure the subprocess activate calls this python
if platform == 'win':
    syspath_list = [root_dir, join(root_dir, 'Scripts')]
    syspath = ';'.join(syspath_list)
    PATH = "C:\\Windows\\system32"
    ROOTPATH = syspath + ';' + PATH
else:
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

if platform == 'win':
    command_setup = """\
    @echo off
    set "PATH={ROOTPATH}"
    set PROMPT=$P$G
    set PYTHONPATH={PYTHONPATH}
    set CONDARC=
    cd {here}
    """.format(here=dirname(__file__), ROOTPATH=ROOTPATH, PYTHONPATH=PYTHONPATH)

    source_setup = "call"

    command_setup = command_setup + """
    mkdir {envs}\\test1\\Scripts 2>NUL
    mkdir {envs}\\test2\\Scripts 2>NUL
    """

    printpath = 'echo %PATH%'
    printdefaultenv = 'echo.%CONDA_DEFAULT_ENV%'
    printps1 = 'echo %PROMPT%'
    slash = '\\'
    nul = '1>NUL 2>&1'
    set_var = 'set '

else:
    command_setup = """\
    export PATH="{ROOTPATH}"
    export PS1='$'
    export PYTHONPATH="{PYTHONPATH}"
    export CONDARC=' '
    cd {here}
    """.format(here=dirname(__file__), ROOTPATH=ROOTPATH, PYTHONPATH=PYTHONPATH)

    source_setup = "source"

    command_setup = command_setup + """
    mkdir -p {envs}/test1/bin
    mkdir -p {envs}/test2/bin
    """

    printpath = 'echo $PATH'
    printdefaultenv = 'echo "$CONDA_DEFAULT_ENV"'
    printps1 = 'echo $PS1'
    slash = '/'
    nul = '2>/dev/null'
    set_var = ''

def test_activate_test1():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1
            {printpath}
            """).format(source=source_setup, slash=slash, envs=envs,
                        activate=activate, printpath=printpath)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stderr,
                    'discarding {syspath} from PATH\nprepending {envs}{slash}test1, {envs}{slash}test1{slash}Scripts to PATH\n'.format(envs=envs, slash=slash, syspath=', '.join(syspath_list)))
                assert_equals(stdout,
                    '{envs}\\test1;{envs}\\test1\\Scripts;{PATH}\n'.format(envs=envs,PATH=PATH))
            else:
                assert stdout == envs + "/test1/bin:" + PATH + "\n"
                assert stderr == 'discarding {syspath} from PATH\nprepending {envs}/test1/bin to PATH\n'.format(envs=envs, syspath=syspath)

def test_activate_test1_test2():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {activate} {envs}{slash}test2
            {printpath}
            """).format(envs=envs, activate=activate, nul=nul, slash=slash, source=source_setup, printpath=printpath)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout,
                    "{envs}{slash}test2;{envs}{slash}test2{slash}Scripts;{PATH}\n".format(envs=envs, slash=slash,PATH=PATH))
                assert_equals(stderr,
                    'discarding {envs}{slash}test1, {envs}{slash}test1{slash}Scripts from PATH\n'.format(envs=envs, slash=slash) +
                    'prepending {envs}{slash}test2, {envs}{slash}test2{slash}Scripts to PATH\n'.format(envs=envs, slash=slash))
            else:
                assert stdout == envs + "/test2/bin:" + PATH + "\n"
                assert stderr == 'discarding {envs}/test1/bin from PATH\nprepending {envs}/test2/bin to PATH\n'.format(envs=envs)

def test_activate_test3():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} {envs}{slash}test3
            {printpath}
            """).format(envs=envs, activate=activate, nul=nul, slash=slash, source=source_setup, printpath=printpath)

            stdout, stderr = run_in(commands, shell)
            assert stdout == "%s\n" % ROOTPATH
            if platform == 'win':
                assert_equals(stderr, 'Error: no such directory: {envs}{slash}test3\n'.format(envs=envs, slash=slash))
            else:
                assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

def test_activate_test1_test3():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {activate} {envs}{slash}test3
            {printpath}
            """).format(envs=envs, activate=activate, nul=nul, slash=slash, source=source_setup, printpath=printpath)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout,
                    "{envs}{slash}test1;{envs}{slash}test1{slash}Scripts;{PATH}\n".format(envs=envs, slash=slash,PATH=PATH))
                assert_equals(stderr, 'Error: no such directory: {envs}{slash}test3\n'.format(envs=envs, slash=slash))
            else:
                assert stdout == envs + "/test1/bin:" + PATH + "\n"
                assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)


def test_deactivate():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {deactivate}
            {printpath}
            """).format(envs=envs, deactivate=deactivate, source=source_setup, printpath=printpath)

            stdout, stderr = run_in(commands, shell)
            assert stdout == "%s\n" % ROOTPATH
            assert stderr == 'Error: No environment to deactivate\n'


def test_activate_test1_deactivate():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {deactivate}
            {printpath}
            """).format(envs=envs, deactivate=deactivate, activate=activate, nul=nul, slash=slash, source=source_setup, printpath=printpath)

            stdout, stderr = run_in(commands, shell)
            assert stdout == "%s\n" % ROOTPATH
            if platform == 'win':
                assert_equals(stderr,
                    'discarding {envs}{slash}test1, {envs}{slash}test1{slash}Scripts from PATH\n'.format(envs=envs, slash=slash))
            else:
                assert stderr == 'discarding {envs}/test1/bin from PATH\n'.format(envs=envs)

def test_wrong_args():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate}
            {printpath}
            """).format(envs=envs, deactivate=deactivate, activate=activate, source=source_setup, printpath=printpath)

            stdout, stderr = run_in(commands, shell)
            assert stdout == "%s\n" % ROOTPATH
            assert stderr == 'Error: no environment provided.\n'

            commands = (command_setup + """
            {source} {activate} two args
            {printpath}
            """).format(envs=envs, deactivate=deactivate, activate=activate, source=source_setup, printpath=printpath)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH + "\n"
            assert stderr == 'Error: did not expect more than one argument.\n'

            commands = (command_setup + """
            {source} {deactivate} test
            {printpath}
            """).format(envs=envs, deactivate=deactivate, activate=activate, source=source_setup, printpath=printpath)

            stdout, stderr = run_in(commands, shell)
            assert stdout == "%s\n" % ROOTPATH
            assert stderr == 'Error: too many arguments.\n'

            commands = (command_setup + """
            {source} {deactivate} {envs}{slash}test
            {printpath}
            """).format(envs=envs, deactivate=deactivate, activate=activate, slash=slash, source=source_setup, printpath=printpath)

            stdout, stderr = run_in(commands, shell)
            assert stdout == "%s\n" % ROOTPATH
            assert stderr == 'Error: too many arguments.\n'


def test_activate_help():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)

            if not platform == 'win':
                commands = (command_setup + """
                {activate} {envs}{slash}test1
                """).format(envs=envs, activate=activate, slash=slash)

                stdout, stderr = run_in(commands, shell)
                assert stdout == '\n'
                assert "activate must be sourced" in stderr
                assert "Usage: source activate ENV" in stderr

            commands = (command_setup + """
            {source} {activate} --help
            """).format(envs=envs, activate=activate, source=source_setup)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            if platform == "win":
                assert "Usage: activate ENV" in stderr
            else:
                assert "Usage: source activate ENV" in stderr

            if not platform == 'win':
                commands = (command_setup + """
                {deactivate}
                """).format(envs=envs, deactivate=deactivate)

                stdout, stderr = run_in(commands, shell)
                assert stdout == ''
                assert "deactivate must be sourced" in stderr
                assert "Usage: source deactivate" in stderr

            commands = (command_setup + """
            {source} {deactivate} --help
            """).format(envs=envs, deactivate=deactivate, source=source_setup)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            if platform == 'win':
                assert "Usage: deactivate" in stderr
            else:
                assert "Usage: source deactivate" in stderr

def test_activate_symlinking():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1
            """).format(envs=envs, activate=activate, source=source_setup, slash=slash)

            stdout, stderr = run_in(commands, shell)
            assert stdout != '\n'
            if platform == 'win':
                assert stderr == 'discarding {syspath} from PATH\nprepending {envs}\\test1, {envs}\\test1\\Scripts to PATH\n'.format(envs=envs, syspath=", ".join(syspath_list))
            else:
                assert stderr == 'discarding {syspath} from PATH\nprepending {envs}/test1/bin to PATH\n'.format(envs=envs, syspath=syspath)
            for f in ['conda', 'activate', 'deactivate']:
                if platform == 'win':
                    # TODO: fix checks for Windows
                    pass
                else:
                    assert os.path.lexists('{envs}/test1/bin/{f}'.format(envs=envs, f=f))
                    assert os.path.exists('{envs}/test1/bin/{f}'.format(envs=envs, f=f))
                    s = os.lstat('{envs}/test1/bin/{f}'.format(envs=envs, f=f))
                    assert stat.S_ISLNK(s.st_mode)
                    assert os.readlink('{envs}/test1/bin/{f}'.format(envs=envs,
                        f=f)) == '{syspath}/{f}'.format(syspath=syspath, f=f)

            if platform != 'win':
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
                    {source} {activate} {envs}/test3
                    """).format(envs=envs, activate=activate, deactivate=deactivate, conda=conda)
                    stdout, stderr = run_in(commands, shell)
                    assert stdout != '\n'
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
                    {source} {activate} {envs}/test4
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

def test_PS1():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1
            {printps1}
            """).format(envs=envs, activate=activate, source=source_setup, slash=slash, printps1=printps1, set_var=set_var)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "[{envs}{slash}test1] $P$G\n".format(envs=envs, slash=slash))
                assert_equals(stderr, 'discarding {syspath} from PATH\nprepending {envs}{slash}test1, {envs}{slash}test1{slash}Scripts to PATH\n'.format(envs=envs, slash=slash, syspath=", ".join(syspath_list)))
            else:
                assert stdout == '({envs}/test1)$\n'.format(envs=envs)
                assert stderr == 'discarding {syspath} from PATH\nprepending {envs}/test1/bin to PATH\n'.format(envs=envs, syspath=syspath)

            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {activate} {envs}{slash}test2
            {printps1}
            """).format(envs=envs, activate=activate, source=source_setup, slash=slash, printps1=printps1, set_var=set_var, nul=nul)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "[{envs}{slash}test2] $P$G\n".format(envs=envs, slash=slash))
                assert_equals(stderr,
                    'discarding {envs}{slash}test1, {envs}{slash}test1{slash}Scripts from PATH\n'.format(envs=envs, slash=slash) +
                    'prepending {envs}{slash}test2, {envs}{slash}test2{slash}Scripts to PATH\n'.format(envs=envs, slash=slash))
            else:
                assert stdout == '({envs}/test2)$\n'.format(envs=envs)
                assert stderr == 'discarding {envs}/test1/bin from PATH\nprepending {envs}/test2/bin to PATH\n'.format(envs=envs)

            commands = (command_setup + """
            {source} {activate} {envs}{slash}test3
            {printps1}
            """).format(envs=envs, activate=activate, source=source_setup, slash=slash, printps1=printps1, set_var=set_var)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr, 'Error: no such directory: {envs}{slash}test3\n'.format(envs=envs, slash=slash))
            else:
                assert stdout == '$\n'
                assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {activate} {envs}{slash}test3
            {printps1}
            """).format(envs=envs, activate=activate, source=source_setup, slash=slash, printps1=printps1, set_var=set_var, nul=nul)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "[{envs}{slash}test1] $P$G\n".format(envs=envs,slash=slash))
                assert_equals(stderr, 'Error: no such directory: {envs}{slash}test3\n'.format(envs=envs, slash=slash))
            else:
                assert stdout == '({envs}/test1)$\n'.format(envs=envs)
                assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

            commands = (command_setup + """
            {source} {deactivate}
            {printps1}
            """).format(envs=envs, deactivate=deactivate, source=source_setup, slash=slash, printps1=printps1, set_var=set_var)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr, 'Error: No environment to deactivate\n')
            else:
                assert stdout == '$\n'
                assert stderr == 'Error: No environment to deactivate\n'

            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {deactivate}
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, source=source_setup, slash=slash, printps1=printps1, set_var=set_var, nul=nul)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr, 'discarding {envs}{slash}test1, {envs}{slash}test1{slash}Scripts from PATH\n'.format(envs=envs, slash=slash))
            else:
                assert stdout == '$\n'
                assert stderr == 'discarding {envs}/test1/bin from PATH\n'.format(envs=envs)

            commands = (command_setup + """
            {source} {activate}
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, source=source_setup, printps1=printps1, set_var=set_var, slash=slash)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'Error: no environment provided.\n')
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
            else:
                assert stdout == '$\n'

            commands = (command_setup + """
            {source} {activate} two args
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, source=source_setup, printps1=printps1, set_var=set_var, slash=slash)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr, 'Error: did not expect more than one argument.\n')
            else:
                assert stdout == '$\n'
                assert stderr == 'Error: did not expect more than one argument.\n'

            commands = (command_setup + """
            {source} {deactivate} test
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, source=source_setup, printps1=printps1, set_var=set_var, slash=slash)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'Error: too many arguments.\n')
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
            else:
                assert stdout == '$\n'

            commands = (command_setup + """
            {source} {deactivate} {envs}{slash}test
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, source=source_setup, slash=slash, printps1=printps1, set_var=set_var)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'Error: too many arguments.\n')
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
            else:
                assert stdout == '$\n'

def test_PS1_no_changeps1():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            with open(join(envs, '.condarc'), 'w') as f:
                f.write("""\
changeps1: no
""")
            condarc = """
            {set_var}CONDARC={envs}{slash}.condarc
            """
            commands = (command_setup + condarc + """
            {source} {activate} {envs}{slash}test1
            {printps1}
            """).format(envs=envs, activate=activate, source=source_setup, slash=slash, printps1=printps1, set_var=set_var)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr, 'discarding {syspath} from PATH\nprepending {envs}{slash}test1, {envs}{slash}test1{slash}Scripts to PATH\n'.format(envs=envs, slash=slash, syspath=", ".join(syspath_list)))
            else:
                assert stdout == '$\n'
                assert stderr == 'discarding {syspath} from PATH\nprepending {envs}/test1/bin to PATH\n'.format(envs=envs, syspath=syspath)

            commands = (command_setup + condarc + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {activate} {envs}{slash}test2
            {printps1}
            """).format(envs=envs, activate=activate, source=source_setup, slash=slash, printps1=printps1, set_var=set_var, nul=nul)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr,
                    'discarding {envs}{slash}test1, {envs}{slash}test1{slash}Scripts from PATH\n'.format(envs=envs, slash=slash) +
                    'prepending {envs}{slash}test2, {envs}{slash}test2{slash}Scripts to PATH\n'.format(envs=envs, slash=slash))
            else:
                assert stdout == '$\n'
                assert stderr == 'discarding {envs}/test1/bin from PATH\nprepending {envs}/test2/bin to PATH\n'.format(envs=envs)

            commands = (command_setup + condarc + """
            {source} {activate} {envs}{slash}test3
            {printps1}
            """).format(envs=envs, activate=activate, source=source_setup, slash=slash, printps1=printps1, set_var=set_var)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr, 'Error: no such directory: {envs}{slash}test3\n'.format(envs=envs, slash=slash))
            else:
                assert stdout == '$\n'
                assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

            commands = (command_setup + condarc + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {activate} {envs}{slash}test3
            {printps1}
            """).format(envs=envs, activate=activate, source=source_setup, slash=slash, printps1=printps1, set_var=set_var, nul=nul)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr, 'Error: no such directory: {envs}{slash}test3\n'.format(envs=envs, slash=slash))
            else:
                assert stdout == '$\n'
                assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

            commands = (command_setup + condarc + """
            {source} {deactivate}
            {printps1}
            """).format(envs=envs, deactivate=deactivate, source=source_setup, slash=slash, printps1=printps1, set_var=set_var)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr, 'Error: No environment to deactivate\n')
            else:
                assert stdout == '$\n'
                assert stderr == 'Error: No environment to deactivate\n'

            commands = (command_setup + condarc + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {deactivate}
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, source=source_setup, slash=slash, printps1=printps1, set_var=set_var, nul=nul)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr, 'discarding {envs}{slash}test1, {envs}{slash}test1{slash}Scripts from PATH\n'.format(envs=envs, slash=slash))
            else:
                assert stdout == '$\n'
                assert stderr == 'discarding {envs}/test1/bin from PATH\n'.format(envs=envs)

            commands = (command_setup + condarc + """
            {source} {activate}
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, source=source_setup, printps1=printps1, set_var=set_var, slash=slash)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr, 'Error: no environment provided.\n')
            else:
                assert stdout == '$\n'
                assert stderr == 'Error: no environment provided.\n'

            commands = (command_setup + condarc + """
            {source} {activate} two args
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, source=source_setup, printps1=printps1, set_var=set_var, slash=slash)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr, 'Error: did not expect more than one argument.\n')
            else:
                assert stdout == '$\n'
                assert stderr == 'Error: did not expect more than one argument.\n'

            commands = (command_setup + condarc + """
            {source} {deactivate} test
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, source=source_setup, printps1=printps1, set_var=set_var, slash=slash)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr, 'Error: too many arguments.\n')
            else:
                assert stdout == '$\n'
                assert stderr == 'Error: too many arguments.\n'

            commands = (command_setup + condarc + """
            {source} {deactivate} {envs}{slash}test
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, source=source_setup, slash=slash, printps1=printps1, set_var=set_var)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr, 'Error: too many arguments.\n')
            else:
                assert stdout == '$\n'
                assert stderr == 'Error: too many arguments.\n'

def test_CONDA_DEFAULT_ENV():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1
            {printdefaultenv}
            """).format(envs=envs, activate=activate, source=source_setup, printdefaultenv=printdefaultenv, slash=slash)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '{envs}{slash}test1\n'.format(envs=envs, slash=slash))
            if platform == 'win':
                assert_equals(stderr,
                    'discarding {syspath} from PATH\nprepending {envs}{slash}test1, {envs}{slash}test1{slash}Scripts to PATH\n'.format(envs=envs, slash=slash, syspath=", ".join(syspath_list)))
            else:
                assert_equals(stderr, 'discarding {syspath} from PATH\nprepending {envs}/test1/bin to PATH\n'.format(envs=envs, syspath=syspath))

            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {activate} {envs}{slash}test2
            {printdefaultenv}
            """).format(envs=envs, activate=activate, source=source_setup, printdefaultenv=printdefaultenv, nul=nul, slash=slash)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '{envs}{slash}test2\n'.format(envs=envs, slash=slash))
            if platform == 'win':
                assert_equals(stderr,
                    'discarding {envs}{slash}test1, {envs}{slash}test1{slash}Scripts from PATH\n'.format(envs=envs, slash=slash) +
                    'prepending {envs}{slash}test2, {envs}{slash}test2{slash}Scripts to PATH\n'.format(envs=envs, slash=slash))
            else:
                assert stderr == 'discarding {envs}/test1/bin from PATH\nprepending {envs}/test2/bin to PATH\n'.format(envs=envs)

            commands = (command_setup + """
            {source} {activate} {envs}{slash}test3
            {printdefaultenv}
            """).format(envs=envs, activate=activate, source=source_setup, printdefaultenv=printdefaultenv, slash=slash)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '\n')
            if platform == 'win':
                assert_equals(stderr, 'Error: no such directory: {envs}{slash}test3\n'.format(envs=envs, slash=slash))
            else:
                assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {activate} {envs}{slash}test3
            {printdefaultenv}
            """).format(envs=envs, activate=activate, source=source_setup, printdefaultenv=printdefaultenv, nul=nul, slash=slash)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '{envs}{slash}test1\n'.format(envs=envs, slash=slash))
            if platform == 'win':
                assert_equals(stderr, 'Error: no such directory: {envs}{slash}test3\n'.format(envs=envs, slash=slash))
            else:
                assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

            commands = (command_setup + """
            {source} {deactivate}
            {printdefaultenv}
            """).format(envs=envs, deactivate=deactivate, source=source_setup, printdefaultenv=printdefaultenv)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '\n')
            assert_equals(stderr, 'Error: No environment to deactivate\n')

            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {deactivate}
            {printdefaultenv}
            """).format(envs=envs, deactivate=deactivate, activate=activate, source=source_setup, printdefaultenv=printdefaultenv, nul=nul, slash=slash)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '\n')
            if platform == 'win':
                assert_equals(stderr, 'discarding {envs}{slash}test1, {envs}{slash}test1{slash}Scripts from PATH\n'.format(envs=envs, slash=slash))
            else:
                assert stderr == 'discarding {envs}/test1/bin from PATH\n'.format(envs=envs)

            commands = (command_setup + """
            {source} {activate}
            {printdefaultenv}
            """).format(envs=envs, deactivate=deactivate, activate=activate, source=source_setup, printdefaultenv=printdefaultenv)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '\n')
            assert_equals(stderr, 'Error: no environment provided.\n')

            commands = (command_setup + """
            {source} {activate} two args
            {printdefaultenv}
            """).format(envs=envs, deactivate=deactivate, activate=activate, source=source_setup, printdefaultenv=printdefaultenv)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '\n')
            assert_equals(stderr, 'Error: did not expect more than one argument.\n')

            commands = (command_setup + """
            {source} {deactivate} test
            {printdefaultenv}
            """).format(envs=envs, deactivate=deactivate, activate=activate, source=source_setup, printdefaultenv=printdefaultenv)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '\n')
            assert_equals(stderr, 'Error: too many arguments.\n')

            commands = (command_setup + """
            {source} {deactivate} {envs}/test
            {printdefaultenv}
            """).format(envs=envs, deactivate=deactivate, activate=activate, source=source_setup, printdefaultenv=printdefaultenv)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '\n')
            assert_equals(stderr, 'Error: too many arguments.\n')

            # commands = (command_setup + """
            # {source} {activate} root
            # printf "$CONDA_DEFAULT_ENV"
            # """).format(envs=envs, deactivate=deactivate, activate=activate, source=source_setup)
            #
            # stdout, stderr = run_in(commands, shell)
            # assert stdout == 'root'
            # assert stderr == 'Error: too many arguments.\n'

# TODO:
# - Test activating an env by name
# - Test activating "root"
# - Test activating "root" and then deactivating
# - Check 'symlinking' on Windows
# - remove asserts with assert_equals
# - Make test code platform-independent by constructing expected paths outputs
# - Clean up activate.bat and deactivate.bat
