from __future__ import print_function, absolute_import

from distutils.spawn import find_executable
import os
from os.path import dirname, join, pathsep, normpath
import shutil
import stat

import pytest

from conda.compat import TemporaryDirectory
from conda.config import root_dir, platform
from conda.cli.activate import pathlist_to_str
from .helpers import run_in


def assert_equals(a, b):
    assert a == b, "%r != %r" % (a, b)

def assert_path_equals(a, b):
    assert set(normpath(pth) for pth in a.strip().split(pathsep)) == set(normpath(pth) for pth in b.strip().split(pathsep))

def assert_in(a, b):
    assert a in b, "%r cannot be found in %r" % (a, b)

def gen_test_env_paths(envs, num_test_folders=5):
    """People need not use all the test folders listed here.
    This is only for shortening the environment string generation.

    Also encapsulates paths in double quotes.
    """
    return [join(envs, "test{}".format(test_folder+1)) for test_folder in range(num_test_folders)]

def _envpaths(env_root, env_name=""):
    if 'win' in platform:
        return [join(env_root, env_name),
                join(env_root, env_name, 'Scripts'),
                join(env_root, env_name, 'Library', 'bin'),
               ]
    else:
        return [join(env_root, env_name, 'bin'),]


ps_format_string = '({env_dirs[{number}]}/test1)$\n'
ps_unchanged_string = '$\n'

PYTHONPATH = os.path.dirname(os.path.dirname(__file__))

def normalize_win_path_from_stdout(path):
    path = path.replace("\\", "\\\\")
    path = path.replase("\r\n", "\n")
    return

if 'win' in platform:
    shells = ['cmd.exe']
    ps_var = "PROMPT"
    raw_ps = "$P$G\n"
    echo = "echo."
    var_format = "%{var}%"

    def _write_entry_points(envs):
        """
        Write entry points to {envs}/Scripts
        """
        os.makedirs(join(envs, 'Scripts'))
        with open(join(envs, 'Scripts', 'conda-script.py'), 'w') as f:
            f.write(CONDA_ENTRY_POINT.format(syspath=syspath))
        return (join(root_dir, 'Scripts', 'activate.bat'),
                join(root_dir, 'Scripts', 'deactivate.bat'),
                join(root_dir, 'Scripts', 'conda.exe'))

    # Make sure the subprocess activate calls this python
    syspath = pathsep.join(_envpaths(root_dir))
    PATH = "C:\\Windows\\system32"
    ROOTPATH = syspath + pathsep + PATH

    source_setup = "call"

    nul = '1>NUL 2>&1'
    set_var = 'set '

else:
    # Only run these tests for commands that are installed.
    shells = ['bash', 'zsh']
    ps_var = "PS1"
    raw_ps = "'$'"
    var_format = "${var}"
    echo = "echo "
    def _write_entry_points(envs):
        """
        Write entry points to {envs}/root/bin

        This is needed because the conda in bin/conda uses #!/usr/bin/env python,
        which doesn't work if you remove the root environment from the PATH. So we
        have to use a conda entry point that has the root Python hard-coded in the
        shebang line.
        """.format(envs=envs)
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

    syspath = pathsep.join(_envpaths(root_dir))
    # dirname, which is used in the activate script, is typically installed in
    # /usr/bin (not sure if it has to be)
    PATH = pathsep.join(['/bin', '/usr/bin'])
    ROOTPATH = syspath + pathsep + PATH

    source_setup = "source"

    nul = '2>/dev/null'
    set_var = ''

for shell in shells[:]:
    try:
        stdout, stderr = run_in('echo', shell)
    except OSError:
        pass
    else:
        if not stderr:
            shells.append(shell)

ps_format_string = "[{env_dirs[{number}]}] "+raw_ps

CONDA_ENTRY_POINT="""\
#!{syspath}/python
import sys
from conda.cli import main

sys.exit(main())
"""
printpath = '{echo}{var}'.format(echo=echo, var=var_format.format(var="PATH"))
printdefaultenv = '{echo}"{var}"'.format(echo=echo, var=var_format.format(var="CONDA_ACTIVE_ENV"))
printps1 = '{echo}{var}'.format(echo=echo, var=var_format.format(var="PS1"))

command_setup = """\
@echo off
set "PATH={ROOTPATH}"
set {ps_var}={raw_ps}
set PYTHONPATH={PYTHONPATH}
set CONDARC=
cd {here}
""".format(here=dirname(__file__), ROOTPATH=ROOTPATH, PYTHONPATH=PYTHONPATH,
           ps_var=ps_var, raw_ps=raw_ps)

_format_vars = {
    'nul': nul,
    'printpath': printpath,
    'printdefaultenv': printdefaultenv,
    'printps1': printps1,
    'set_var': set_var,
    'source': source_setup,
}

@pytest.mark.slow
def test_activate_test1():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} "{env_dirs[0]}"
            {printpath}
            """).format(activate=activate, envs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_path_equals(stdout, pathsep.join(_envpaths(envs, 'test1')) + pathsep + PATH + '\n')
            assert_equals(stderr, 'discarding {syspath} from PATH\nprepending {envpaths} to PATH\n'\
                    .format(envpaths=pathlist_to_str(_envpaths(envs, 'test1')),
                            syspath=pathlist_to_str(_envpaths(root_dir))))


@pytest.mark.slow
def test_activate_test1_test2():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} "{env_dirs[0]}" {nul}
            {source} {activate} "{env_dirs[1]}"
            {printpath}
            """).format(envs=gen_test_env_paths(envs), activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_path_equals(stdout, pathsep.join(_envpaths(envs, 'test2')) + os.path.pathsep + PATH + "\n")
            assert_equals(stderr, 'discarding {envpaths1} from PATH\nprepending {envpaths2} to PATH\n'\
                .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1')),
                        envpaths2=pathlist_to_str(_envpaths(envs, 'test2'))))


@pytest.mark.slow
def test_activate_test3():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} "{env_dirs[2]}"
            {printpath}
            """).format(envs=gen_test_env_paths(envs), activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_path_equals(stdout, "%s\n" % ROOTPATH)
            assert_equals(stderr, 'Error: no such directory: {envpaths3}\n'.format(envpaths3=_envpaths(envs, 'test3')[0]))


@pytest.mark.slow
def test_activate_test1_test3():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} "{env_dirs[0]}" {nul}
            {source} {activate} ""{env_dirs[2]}"
            {printpath}
            """).format(envs=gen_test_env_paths(envs), activate=activate, **_format_vars)

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
            {source} {activate} {env_dirs[0]} {nul}
            {source} {deactivate}
            {printpath}
            """).format(envs=gen_test_env_paths(envs), deactivate=deactivate, activate=activate, **_format_vars)

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
            assert_path_equals(stdout, "%s\n" % ROOTPATH)
            assert_equals(stderr, 'discarding {syspath} from PATH\nprepending {syspath} to PATH\n'\
                .format(syspath=pathlist_to_str(_envpaths(root_dir))))

            commands = (command_setup + """
            {source} {activate} root
            {source} {deactivate}
            {printpath}
            """).format(envs=envs, activate=activate, deactivate=deactivate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, "%s\n" % ROOTPATH)
            assert_equals(stderr, 'discarding {syspath} from PATH\nprepending {syspath} to PATH\n'\
                .format(syspath=pathlist_to_str(_envpaths(root_dir))))


def test_activate_test1_root():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} "{env_dirs[0]} {nul}
            {source} {activate} root
            {printpath}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, "%s\n" % ROOTPATH)
            assert_equals(stderr, 'discarding {envpaths1} from PATH\nprepending {syspath} to PATH\n'\
                .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1')),
                    syspath=pathlist_to_str(_envpaths(root_dir))))


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
            assert_path_equals(stdout, ROOTPATH)
            assert_equals(stderr, 'Error: no environment provided.\n')

            commands = (command_setup + """
            {source} {activate} two args
            {printpath}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_path_equals(stdout, ROOTPATH)
            assert_equals(stderr, 'Error: did not expect more than one argument.\n')

            commands = (command_setup + """
            {source} {deactivate} test
            {printpath}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_path_equals(stdout, ROOTPATH)
            assert_equals(stderr, 'Error: too many arguments.\n')

            commands = (command_setup + """
            {source} {deactivate} "{env}
            {printpath}
            """).format(env=join(envs, "test"), deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_path_equals(stdout, ROOTPATH)
            assert_equals(stderr, 'Error: too many arguments.\n')


@pytest.mark.slow
def test_activate_help():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)

            if not "win" in platform:
                commands = (command_setup + """
                {activate} "{env}
                """).format(env=join(envs, "test1"), activate=activate, **_format_vars)

                stdout, stderr = run_in(commands, shell)
                assert_equals(stdout, '')
                assert_in("activate must be sourced", stderr)
                assert_in("Usage: source activate ENV", stderr)

            commands = (command_setup + """
            {source} {activate} --help
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '')
            if "win" in platform:
                assert_in("Usage: activate ENV", stderr)
            else:
                assert_in("Usage: source activate ENV", stderr)

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
            {source} {activate} "{env_dirs[0]}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert stdout != '\n'
            assert_equals(stderr, 'discarding {syspath} from PATH\nprepending {envpaths1} to PATH\n'\
                    .format(syspath=pathlist_to_str(_envpaths(root_dir)),
                            envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))))

            env = gen_test_env_paths(envs)[0]
            for f in ['conda', 'activate', 'deactivate']:
                if platform == 'win':
                    file_path = join(env, "Scripts", f)
                    assert os.path.exists(file_path)
                    # TODO: assert that script in sub-env eventually finds the one in root,
                    #   Since that is our only authoritative one
                    raise NotImplementedError("Still working on verifying validity of conda env bat shortcuts on windows.")
                else:
                    file_path = join(env, "bin", "f")
                    assert os.path.lexists(file_path)
                    assert os.path.exists(file_path)
                    s = os.lstat(file_path)
                    assert stat.S_ISLNK(s.st_mode)
                    assert os.readlink(file_path) == '{syspath}/{f}'.format(syspath=syspath, f=f)

            if platform != 'win':
                try:
                    # Test activate when there are no write permissions in the
                    # env. There are two cases:
                    # - conda/deactivate/activate are already symlinked
                    bin_path = join(gen_test_env_paths(envs)[2], "bin")
                    commands = (command_setup + """
                    mkdir -p {env_dirs[2]}/bin
                    ln -s {activate} {bin_path}/activate
                    ln -s {deactivate} {bin_path}/deactivate
                    ln -s {conda} {bin_path}/conda
                    chmod 555 {bin_path}
                    {source} {activate} "{env}
                    """).format(bin_path=bin_path, env=gen_test_env_paths(envs)[2],
                                activate=activate, deactivate=deactivate,
                                conda=conda, **_format_vars)
                    stdout, stderr = run_in(commands, shell)
                    assert stdout != '\n'
                    assert_equals(stderr, 'discarding {syspath} from PATH\nprepending {bin_path} to PATH\n'.format(bin_path=bin_path, syspath=syspath))

                    # Make sure it stays the same
                    for f in ['conda', 'activate', 'deactivate']:
                        file_path = join(gen_test_env_paths(envs)[2], "bin", f)
                        assert os.path.lexists(file_path)
                        assert os.path.exists(file_path)
                        s = os.lstat(file_path)
                        assert stat.S_ISLNK(s.st_mode)
                        assert os.readlink(file_path) == '{f}'.format(f=locals()[f])

                    # - conda/deactivate/activate are not symlinked. In this case,
                    # activate should fail
                    commands = (command_setup + """
                    mkdir -p {envs_dir[3]}/bin
                    chmod 555 {envs_dir[3]}/bin
                    {source} {activate} "{envs_dir[3]}"
                    echo $PATH
                    echo $CONDA_ACTIVE_ENV
                    """).format(envs=envs, activate=activate, deactivate=deactivate,
                            **_format_vars)

                    stdout, stderr = run_in(commands, shell)
                    assert_equals(stdout, (
                        '{ROOTPATH}\n' # PATH
                        '\n'           # CONDA_ACTIVE_ENV
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
            {source} {activate} "{env_dirs[0]}"
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'discarding {syspath} from PATH\nprepending {envpaths1} to PATH\n'\
                    .format(syspath=pathlist_to_str(_envpaths(root_dir)),
                            envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))))
            assert_equals(stdout, ps_format_string.format(envs=envs, env_dirs=gen_test_env_paths(envs), number=0))

            commands = (command_setup + """
            {source} {activate} "{env1} {nul}
            {source} {activate} "{env2}
            {printps1}
            """).format(env1=join(envs, "test1"), env2=join(envs, "test2"), activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'discarding {envpaths1} from PATH\nprepending {envpaths2} to PATH\n'\
                    .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1')),
                            envpaths2=pathlist_to_str(_envpaths(envs, 'test2'))))

            assert_equals(stdout, ps_format_string.format(envs=envs, env_dirs=gen_test_env_paths(envs), number=1))

            commands = (command_setup + """
            {source} {activate} "{env}
            {printps1}
            """).format(env=join(envs, "test3"), activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'Error: no such directory: {envpath3}\n'.format(envpath3=_envpaths(envs, 'test3')[0]))
            assert_equals(stdout, ps_unchanged_string)

            commands = (command_setup + """
            {source} {activate} "{env1} {nul}
            {source} {activate} "{env3}
            {printps1}
            """).format(env1=join(envs, "test1"), env3=join(envs, "test3"), activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'Error: no such directory: {envpath3}\n'.format(envpath3=_envpaths(envs, 'test3')[0]))
            assert_equals(stdout, ps_format_string.format(envs=envs, env_dirs=gen_test_env_paths(envs), number=0))

            commands = (command_setup + """
            {source} {deactivate}
            {printps1}
            """).format(envs=envs, deactivate=deactivate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'Error: No environment to deactivate\n')
            assert_equals(stdout, ps_unchanged_string)

            commands = (command_setup + """
            {source} {activate} "{env} {nul}
            {source} {deactivate}
            {printps1}
            """).format(env=join(envs, "test1"), deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'discarding {envpaths1} from PATH\n'\
                    .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))))
            assert_equals(stdout, ps_unchanged_string)

            commands = (command_setup + """
            {source} {activate}
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'Error: no environment provided.\n')
            assert_equals(stdout, ps_unchanged_string)

            commands = (command_setup + """
            {source} {activate} two args
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'Error: did not expect more than one argument.\n')
            assert_equals(stdout, ps_unchanged_string)

            commands = (command_setup + """
            {source} {deactivate} test
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'Error: too many arguments.\n')
            assert_equals(stdout, ps_unchanged_string)

            commands = (command_setup + """
            {source} {deactivate} "{env}
            {printps1}
            """).format(env=join(envs, "test"), deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'Error: too many arguments.\n')
            assert_equals(stdout, ps_unchanged_string)

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
            {set_var}CONDARC={condarc}
            """
            commands = (command_setup + condarc + """
            {source} {activate} "{env_dirs[0]}"
            {printps1}
            """).format(condarc=join(envs, ".condarc"), envs=envs, env_dirs=gen_test_env_paths(envs), activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'discarding {syspath} from PATH\nprepending {envpaths1} to PATH\n'\
                    .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1')),
                            syspath=pathlist_to_str(_envpaths(root_dir))))
            assert_equals(stdout, ps_unchanged_string)

            commands = (command_setup + condarc + """
            {source} {activate} "{env_dirs[0]}" {nul}
            {source} {activate} "{env_dirs[1]}"
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'discarding {envpaths1} from PATH\nprepending {envpaths2} to PATH\n'\
                    .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1')),
                            envpaths2=pathlist_to_str(_envpaths(envs, 'test2'))))
            assert_equals(stdout, ps_unchanged_string)

            commands = (command_setup + condarc + """
            {source} {activate} "{env_dirs[2]}"
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, ps_unchanged_string)
            if platform == 'win':
                assert_equals(stderr, 'Error: no such directory: {env_dirs[2]}\n'.format(envs=envs, env_dirs=gen_test_env_paths(envs)))
            else:
                assert_equals(stderr, 'Error: no such directory: {env_dirs[2]}/bin\n'.format(envs=envs, env_dirs=gen_test_env_paths(envs)))

            commands = (command_setup + condarc + """
            {source} {activate} "{env_dirs[0]}" {nul}
            {source} {activate} "{env_dirs[2]}"
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, ps_unchanged_string)
            if platform == 'win':
                assert_equals(stderr, 'Error: no such directory: {env_dirs[2]}\n'.format(envs=envs, env_dirs=gen_test_env_paths(envs)))
            else:
                assert_equals(stderr, 'Error: no such directory: {env_dirs[2]}/bin\n'.format(envs=envs, env_dirs=gen_test_env_paths(envs)))

            commands = (command_setup + condarc + """
            {source} {deactivate}
            {printps1}
            """).format(deactivate=deactivate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, ps_unchanged_string)
            if platform == 'win':
                assert_equals(stderr, 'Error: No environment to deactivate\n')
            else:
                assert_equals(stderr, 'Error: No environment to deactivate\n')

            commands = (command_setup + condarc + """
            {source} {activate} "{env_dirs[0]}" {nul}
            {source} {deactivate}
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'discarding {envpaths1} from PATH\n'.format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))))
            assert_equals(stdout, ps_unchanged_string)

            commands = (command_setup + condarc + """
            {source} {activate}
            {printps1}
            """).format(envs=envs, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, ps_unchanged_string)
            assert_equals(stderr, 'Error: no environment provided.\n')

            commands = (command_setup + condarc + """
            {source} {activate} two args
            {printps1}
            """).format(envs=envs, deactivate=deactivate, activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, ps_unchanged_string)
            assert_equals(stderr, 'Error: did not expect more than one argument.\n')

            commands = (command_setup + condarc + """
            {source} {deactivate} test
            {printps1}
            """).format(envs=envs, deactivate=deactivate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, ps_unchanged_string)
            assert_equals(stderr, 'Error: too many arguments.\n')

            commands = (command_setup + condarc + """
            {source} {deactivate} "{env_dirs[0]}"
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), deactivate=deactivate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, ps_unchanged_string)
            assert_equals(stderr, 'Error: too many arguments.\n')

@pytest.mark.slow
def test_CONDA_ACTIVE_ENV():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = _write_entry_points(envs)
            commands = (command_setup + """
            {source} {activate} "{env_dirs[0]}"
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '{env_dirs[0]}\n'.format(envs=envs, env_dirs=gen_test_env_paths(envs)))
            assert_equals(stderr, 'discarding {syspath} from PATH\nprepending {envpaths1} to PATH\n'.format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1')),
                                                                                                            syspath=pathlist_to_str(_envpaths(root_dir))))

            commands = (command_setup + """
            {source} {activate} "{env_dirs[0]}" {nul}
            {source} {activate} "{env_dirs[1]}"
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '{env_dirs[1]}\n'.format(envs=gen_test_env_paths()))
            assert_equals(stderr,
                'discarding {envpaths1} from PATH\n'.format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))) +
                'prepending {envpaths2} to PATH\n'.format(envpaths2=pathlist_to_str(_envpaths(envs, 'test2'))))

            commands = (command_setup + """
            {source} {activate} "{env_dirs[2]}"
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '\n')
            assert_equals(stderr, 'Error: no such directory: {envpaths3}\n'.format(envpaths3=_envpaths(envs, 'test3')[0]))

            commands = (command_setup + """
            {source} {activate} "{env_dirs[0]}" {nul}
            {source} {activate} "{env_dirs[0]}"
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), activate=activate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '{env_dirs[0]}\n'.format(envs=gen_test_env_paths()))
            assert_equals(stderr, 'Error: no such directory: {envpaths3}\n'.format(envpaths3=_envpaths(envs, 'test3')[0]))

            commands = (command_setup + """
            {source} {deactivate}
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), deactivate=deactivate, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '\n')
            assert_equals(stderr, 'Error: No environment to deactivate\n')

            commands = (command_setup + """
            {source} {activate} "{env_dirs[0]}" {nul}
            {source} {deactivate}
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), deactivate=deactivate, activate=activate, **_format_vars)

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
            {source} {deactivate} "{envs}/test
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
