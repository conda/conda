from __future__ import print_function, absolute_import

from distutils.spawn import find_executable
import os
from os.path import dirname, join, pathsep
import shutil
import stat
import subprocess

import pytest

from conda.compat import TemporaryDirectory
from conda.config import root_dir, platform
from conda.cli.activate import pathlist_to_str
from tests.helpers import run_in

def assert_equals(a, b):
    assert a == b, "%r != %r" % (a, b)

def assert_in(a, b):
    assert a in b, "%r cannot be found in %r" % (a, b)

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
        activate = find_executable('activate.bat')
        deactivate = find_executable('deactivate.bat')
        os.makedirs(join(envs, 'Scripts'))
        shutil.copy2(activate, join(envs, 'Scripts', 'activate.bat'))
        shutil.copy2(deactivate, join(envs, 'Scripts', 'deactivate.bat'))
        with open(join(envs, 'Scripts', 'conda-script.py'), 'w') as f:
            f.write(CONDA_ENTRY_POINT.format(syspath=syspath))
        shutil.copy2(join(root_dir, 'Scripts', 'conda.exe'),
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
        activate = find_executable('activate')
        deactivate = find_executable('deactivate')
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
    syspath = pathsep.join(syspath_list)
    PATH = "C:\\Windows\\system32"
    ROOTPATH = syspath + pathsep + PATH
else:
    syspath_list = [join(root_dir, 'bin')]
    syspath = pathsep.join(syspath_list)
    # dirname, which is used in the activate script, is typically installed in
    # /usr/bin (not sure if it has to be)
    PATH = pathsep.join(['/bin', '/usr/bin'])
    ROOTPATH = syspath + pathsep + PATH
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


_format_vars = {
    'nul': nul,
    'printpath': printpath,
    'printdefaultenv': printdefaultenv,
    'printps1': printps1,
    'set_var': set_var,
    'slash': slash,
    'source': source_setup,
}

def _envpaths(env_root, env_name):
    if platform == 'win':
        return [env_root + slash + env_name,
                env_root + slash + env_name + slash + 'Scripts'
               ]
    else:
        return [env_root + slash + env_name + slash + 'bin']


@pytest.mark.slow
def test_activate_test1():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1
            {printpath}
            """).format(activate=activate, envs=envs, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, pathsep.join(_envpaths(envs, 'test1')) + pathsep + PATH + '\n')
            assert_equals(stderr, 'discarding {syspath} from PATH\nprepending {envpaths} to PATH\n'\
                    .format(envpaths=pathlist_to_str(_envpaths(envs, 'test1')),
                            syspath=pathlist_to_str(syspath_list)))


@pytest.mark.slow
def test_activate_test1_test2():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {activate} {envs}{slash}test2
            {printpath}
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, pathsep.join(_envpaths(envs, 'test2')) + os.path.pathsep + PATH + "\n")
            assert_equals(stderr, 'discarding {envpaths1} from PATH\nprepending {envpaths2} to PATH\n'\
                .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1')),
                        envpaths2=pathlist_to_str(_envpaths(envs, 'test2'))))


@pytest.mark.slow
def test_activate_test3():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} {envs}{slash}test3
            {printpath}
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, "%s\n" % ROOTPATH)
            assert_equals(stderr, 'Error: no such directory: {envpaths3}\n'.format(envpaths3=_envpaths(envs, 'test3')[0]))


@pytest.mark.slow
def test_activate_test1_test3():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {activate} {envs}{slash}test3
            {printpath}
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, pathsep.join(_envpaths(envs, 'test1')) + pathsep + PATH + "\n")
            assert_equals(stderr, 'Error: no such directory: {envpaths3}\n'.format(envpaths3=_envpaths(envs, 'test3')[0]))


@pytest.mark.slow
def test_deactivate():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {deactivate}
            {printpath}
            """).format(envs=envs, deactivate=deactivate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, "%s\n" % ROOTPATH)
            assert_equals(stderr, 'Error: No environment to deactivate\n')


@pytest.mark.slow
def test_activate_test1_deactivate():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {deactivate}
            {printpath}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, "%s\n" % ROOTPATH)
            assert_equals(stderr, 'discarding {envpaths1} from PATH\n'\
                .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))))


@pytest.mark.slow
def test_activate_root():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} root
            {printpath}
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, "%s\n" % ROOTPATH)
            assert_equals(stderr, 'discarding {syspath} from PATH\nprepending {syspath} to PATH\n'\
                .format(syspath=pathlist_to_str(syspath_list)))

            commands = (command_setup + """
            {source} {activate} root
            {source} {deactivate}
            {printpath}
            """).format(envs=envs, activate=activate, deactivate=deactivate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, "%s\n" % ROOTPATH)
            assert_equals(stderr, 'discarding {syspath} from PATH\nprepending {syspath} to PATH\n'\
                .format(syspath=pathlist_to_str(syspath_list)))


def test_activate_test1_root():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {activate} root
            {printpath}
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, "%s\n" % ROOTPATH)
            assert_equals(stderr, 'discarding {envpaths1} from PATH\nprepending {syspath} to PATH\n'\
                .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1')),
                    syspath=pathlist_to_str(syspath_list)))


@pytest.mark.slow
def test_wrong_args():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate}
            {printpath}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, "%s\n" % ROOTPATH)
            assert_equals(stderr, 'Error: no environment provided.\n')

            commands = (command_setup + """
            {source} {activate} two args
            {printpath}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, "%s\n" % ROOTPATH)
            assert_equals(stderr, 'Error: did not expect more than one argument.\n')

            commands = (command_setup + """
            {source} {deactivate} test
            {printpath}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, "%s\n" % ROOTPATH)
            assert_equals(stderr, 'Error: too many arguments.\n')

            commands = (command_setup + """
            {source} {deactivate} {envs}{slash}test
            {printpath}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, "%s\n" % ROOTPATH)
            assert_equals(stderr, 'Error: too many arguments.\n')


@pytest.mark.slow
def test_activate_help():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)

            if not platform == 'win':
                commands = (command_setup + """
                {activate} {envs}{slash}test1
                """).format(envs=envs, activate=activate, **_format_vars)

                stdout, stderr = run_in(commands, shell)
                assert_equals(stdout, '')
                assert_in("activate must be sourced", stderr)
                assert_in("Usage: source activate ENV", stderr)

            commands = (command_setup + """
            {source} {activate} --help
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '')
            if platform == "win":
                assert_in("Usage: activate ENV", stderr)
            else:
                assert_in("Usage: source activate ENV", stderr)

            if not platform == 'win':
                commands = (command_setup + """
                {deactivate}
                """).format(envs=envs, deactivate=deactivate)

                stdout, stderr = run_in(commands, shell)
                assert_equals(stdout, '')
                assert_in("deactivate must be sourced", stderr)
                assert_in("Usage: source deactivate", stderr)

            commands = (command_setup + """
            {source} {deactivate} --help
            """).format(envs=envs, deactivate=deactivate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '')
            if platform == 'win':
                assert_in("Usage: deactivate", stderr)
            else:
                assert_in("Usage: source deactivate", stderr)

@pytest.mark.slow
def test_activate_symlinking():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert stdout != '\n'
            assert_equals(stderr, 'discarding {syspath} from PATH\nprepending {envpaths1} to PATH\n'\
                    .format(syspath=pathlist_to_str(syspath_list),
                            envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))))

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
                    """).format(envs=envs, activate=activate, deactivate=deactivate,
                            conda=conda, **_format_vars)
                    stdout, stderr = run_in(commands, shell)
                    assert stdout != '\n'
                    assert_equals(stderr, 'discarding {syspath} from PATH\nprepending {envs}/test3/bin to PATH\n'.format(envs=envs, syspath=syspath))

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
                    """).format(envs=envs, activate=activate, deactivate=deactivate,
                            **_format_vars)

                    stdout, stderr = run_in(commands, shell)
                    assert_equals(stdout, (
                        '{ROOTPATH}\n' # PATH
                        '\n'           # CONDA_DEFAULT_ENV
                        ).format(ROOTPATH=ROOTPATH))
                    assert_equals(stderr, ('Cannot activate environment {envs}/test4, '
                        'do not have write access to write conda symlink\n').format(envs=envs))

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
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'discarding {syspath} from PATH\nprepending {envpaths1} to PATH\n'\
                    .format(syspath=pathlist_to_str(syspath_list),
                            envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))))
            if platform == 'win':
                assert_equals(stdout, "[{envs}{slash}test1] $P$G\n".format(envs=envs, slash=slash))
            else:
                assert_equals(stdout, '({envs}/test1)$\n'.format(envs=envs))

            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {activate} {envs}{slash}test2
            {printps1}
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'discarding {envpaths1} from PATH\nprepending {envpaths2} to PATH\n'\
                    .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1')),
                            envpaths2=pathlist_to_str(_envpaths(envs, 'test2'))))
            if platform == 'win':
                assert_equals(stdout, "[{envs}{slash}test2] $P$G\n".format(envs=envs, slash=slash))
            else:
                assert_equals(stdout, '({envs}/test2)$\n'.format(envs=envs))

            commands = (command_setup + """
            {source} {activate} {envs}{slash}test3
            {printps1}
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'Error: no such directory: {envpath3}\n'.format(envpath3=_envpaths(envs, 'test3')[0]))
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
            else:
                assert_equals(stdout, '$\n')

            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {activate} {envs}{slash}test3
            {printps1}
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'Error: no such directory: {envpath3}\n'.format(envpath3=_envpaths(envs, 'test3')[0]))
            if platform == 'win':
                assert_equals(stdout, "[{envs}{slash}test1] $P$G\n".format(envs=envs,slash=slash))
            else:
                assert_equals(stdout, '({envs}/test1)$\n'.format(envs=envs))

            commands = (command_setup + """
            {source} {deactivate}
            {printps1}
            """).format(envs=envs, deactivate=deactivate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'Error: No environment to deactivate\n')
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
            else:
                assert_equals(stdout, '$\n')

            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {deactivate}
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'discarding {envpaths1} from PATH\n'\
                    .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))))
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
            else:
                assert_equals(stdout, '$\n')

            commands = (command_setup + """
            {source} {activate}
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'Error: no environment provided.\n')
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
            else:
                assert_equals(stdout, '$\n')

            commands = (command_setup + """
            {source} {activate} two args
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'Error: did not expect more than one argument.\n')
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
            else:
                assert_equals(stdout, '$\n')

            commands = (command_setup + """
            {source} {deactivate} test
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'Error: too many arguments.\n')
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
            else:
                assert_equals(stdout, '$\n')

            commands = (command_setup + """
            {source} {deactivate} {envs}{slash}test
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'Error: too many arguments.\n')
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
            else:
                assert_equals(stdout, '$\n')

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
            {set_var}CONDARC={envs}{slash}.condarc
            """
            commands = (command_setup + condarc + """
            {source} {activate} {envs}{slash}test1
            {printps1}
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'discarding {syspath} from PATH\nprepending {envpaths1} to PATH\n'\
                    .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1')),
                            syspath=pathlist_to_str(syspath_list)))
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
            else:
                assert_equals(stdout, '$\n')

            commands = (command_setup + condarc + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {activate} {envs}{slash}test2
            {printps1}
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'discarding {envpaths1} from PATH\nprepending {envpaths2} to PATH\n'\
                    .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1')),
                            envpaths2=pathlist_to_str(_envpaths(envs, 'test2'))))
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
            else:
                assert_equals(stdout, '$\n')

            commands = (command_setup + condarc + """
            {source} {activate} {envs}{slash}test3
            {printps1}
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr, 'Error: no such directory: {envs}{slash}test3\n'.format(envs=envs, slash=slash))
            else:
                assert_equals(stdout, '$\n')
                assert_equals(stderr, 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs))

            commands = (command_setup + condarc + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {activate} {envs}{slash}test3
            {printps1}
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr, 'Error: no such directory: {envs}{slash}test3\n'.format(envs=envs, slash=slash))
            else:
                assert_equals(stdout, '$\n')
                assert_equals(stderr, 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs))

            commands = (command_setup + condarc + """
            {source} {deactivate}
            {printps1}
            """).format(envs=envs, deactivate=deactivate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr, 'Error: No environment to deactivate\n')
            else:
                assert_equals(stdout, '$\n')
                assert_equals(stderr, 'Error: No environment to deactivate\n')

            commands = (command_setup + condarc + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {deactivate}
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'discarding {envpaths1} from PATH\n'.format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))))
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
            else:
                assert_equals(stdout, '$\n')

            commands = (command_setup + condarc + """
            {source} {activate}
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr, 'Error: no environment provided.\n')
            else:
                assert_equals(stdout, '$\n')
                assert_equals(stderr, 'Error: no environment provided.\n')

            commands = (command_setup + condarc + """
            {source} {activate} two args
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr, 'Error: did not expect more than one argument.\n')
            else:
                assert_equals(stdout, '$\n')
                assert_equals(stderr, 'Error: did not expect more than one argument.\n')

            commands = (command_setup + condarc + """
            {source} {deactivate} test
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr, 'Error: too many arguments.\n')
            else:
                assert_equals(stdout, '$\n')
                assert_equals(stderr, 'Error: too many arguments.\n')

            commands = (command_setup + condarc + """
            {source} {deactivate} {envs}{slash}test
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            if platform == 'win':
                assert_equals(stdout, "$P$G\n")
                assert_equals(stderr, 'Error: too many arguments.\n')
            else:
                assert_equals(stdout, '$\n')
                assert_equals(stderr, 'Error: too many arguments.\n')

@pytest.mark.slow
def test_CONDA_DEFAULT_ENV():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1
            {printdefaultenv}
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '{envs}{slash}test1\n'.format(envs=envs, slash=slash))
            assert_equals(stderr, 'discarding {syspath} from PATH\nprepending {envpaths1} to PATH\n'.format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1')), syspath=pathlist_to_str(syspath_list)))

            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {activate} {envs}{slash}test2
            {printdefaultenv}
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '{envs}{slash}test2\n'.format(envs=envs, slash=slash))
            assert_equals(stderr,
                'discarding {envpaths1} from PATH\n'.format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))) +
                'prepending {envpaths2} to PATH\n'.format(envpaths2=pathlist_to_str(_envpaths(envs, 'test2'))))

            commands = (command_setup + """
            {source} {activate} {envs}{slash}test3
            {printdefaultenv}
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '\n')
            assert_equals(stderr, 'Error: no such directory: {envpaths3}\n'.format(envpaths3=_envpaths(envs, 'test3')[0]))

            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {activate} {envs}{slash}test3
            {printdefaultenv}
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '{envs}{slash}test1\n'.format(envs=envs, slash=slash))
            assert_equals(stderr, 'Error: no such directory: {envpaths3}\n'.format(envpaths3=_envpaths(envs, 'test3')[0]))

            commands = (command_setup + """
            {source} {deactivate}
            {printdefaultenv}
            """).format(envs=envs, deactivate=deactivate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '\n')
            assert_equals(stderr, 'Error: No environment to deactivate\n')

            commands = (command_setup + """
            {source} {activate} {envs}{slash}test1 {nul}
            {source} {deactivate}
            {printdefaultenv}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '\n')
            assert_equals(stderr, 'discarding {envpaths1} from PATH\n'\
                    .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))))

            commands = (command_setup + """
            {source} {activate}
            {printdefaultenv}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '\n')
            assert_equals(stderr, 'Error: no environment provided.\n')

            commands = (command_setup + """
            {source} {activate} two args
            {printdefaultenv}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '\n')
            assert_equals(stderr, 'Error: did not expect more than one argument.\n')

            commands = (command_setup + """
            {source} {deactivate} test
            {printdefaultenv}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '\n')
            assert_equals(stderr, 'Error: too many arguments.\n')

            commands = (command_setup + """
            {source} {deactivate} {envs}/test
            {printdefaultenv}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '\n')
            assert_equals(stderr, 'Error: too many arguments.\n')

            commands = (command_setup + """
            {source} {activate} root {nul}
            {printdefaultenv}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, 'root\n')
            assert_equals(stderr, '')

            commands = (command_setup + """
            {source} {activate} root {nul}
            {source} {deactivate} {nul}
            {printdefaultenv}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '\n')
            assert_equals(stderr, '')

# TODO:
# - Test activating an env by name
# - Check 'symlinking' on Windows
