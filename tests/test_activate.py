from __future__ import print_function, absolute_import

import os
import sys
from os.path import dirname, join, pathsep
import stat

import pytest

from conda.compat import TemporaryDirectory
from conda.config import root_dir, platform
from conda.install import symlink_conda
from conda.cli.activate import pathlist_to_str
import subprocess
import tempfile

# make pathsep unicode for sake of windows backslash string formatting
pathsep = u"%s" % pathsep


def run_in(command, shell='bash'):
    if shell == 'cmd.exe':
        cmd_script = tempfile.NamedTemporaryFile(suffix='.bat', mode='wt', delete=False)
        cmd_script.write(command)
        cmd_script.close()
        p = subprocess.Popen([shell, '/d', '/c', cmd_script.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        os.unlink(cmd_script.name)
    else:
        p = subprocess.Popen([shell, '-c', command], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
    return [stream.strip().decode('utf-8').replace('\r\n', '\n').replace('\\\\', '\\')
                      for stream in (stdout, stderr)]

def assert_equals(a, b):
    assert a == b, "%r != %r" % (a, b)


def assert_in(a, b):
    assert a in b, "%r cannot be found in %r" % (a, b)


def gen_test_env_paths(envs, num_test_folders=3):
    """People need not use all the test folders listed here.
    This is only for shortening the environment string generation.

    Also encapsulates paths in double quotes.
    """
    paths = [join(envs, "test{}".format(test_folder+1)) for test_folder in range(num_test_folders)]
    for path in paths[:2]:      # Create symlinks ONLY for the first two folders.
        symlink_conda(path, sys.prefix)
    return paths


def _envpaths(env_root, env_name=""):
    if 'win' in platform:
        paths = [join(env_root, env_name).rstrip("\\"),
                join(env_root, env_name, 'Scripts'),
                join(env_root, env_name, 'Library', 'bin'),
               ]
    else:
        paths = [join(env_root, env_name).rstrip("/"),
                 join(env_root, env_name, 'bin'), ]
    return paths


PYTHONPATH = os.path.dirname(os.path.dirname(__file__))

BASE_PATH = os.getenv("PATH")
# Make sure the subprocess activate calls this python
syspath = pathsep.join(_envpaths(root_dir))

echo = "echo"

if platform.startswith("win"):
    shells = ['cmd.exe']
    ps_var = "PROMPT"
    var_format = "%{var}%"
    binpath = "\\Scripts\\"  # mind the trailing slash.
    source_setup = "call"
    nul = '1>NUL 2>&1'
    set_var = 'set '
    shell_suffix = ".bat"
    printps1 = '{echo} {var}'.format(echo=echo if os.getenv(ps_var) else "echo.", var=var_format.format(var=ps_var))

else:
    # Only run these tests for commands that are installed.
    shells = ['bash', 'zsh']
    ps_var = "PS1"
    var_format = "${var}"
    binpath = "/bin/"  # mind the trailing slash.
    source_setup = "source"
    nul = '2>/dev/null'
    set_var = ''
    shell_suffix = ""
    printps1 = '{echo} {var}'.format(echo=echo, var=var_format.format(var=ps_var))

for shell in shells[:]:
    try:
        stdout, stderr = run_in('echo', shell)
    except OSError:
        pass
    else:
        if not stderr:
            shells.append(shell)

raw_ps = os.getenv(ps_var, "")
def print_ps1(env_dirs, number):
    ps = ""
    if raw_ps:
        ps = " " + raw_ps
    return u"({})".format(env_dirs[number])+ps

CONDA_ENTRY_POINT = """\
#!{syspath}/python
import sys
from conda.cli import main

sys.exit(main())
"""
printpath = '{echo} {var}'.format(echo=echo, var=var_format.format(var="PATH"))
printdefaultenv = '{echo}.{var}'.format(echo=echo, var=var_format.format(var="CONDA_ACTIVE_ENV"))

command_setup = """\
set {ps_var}={raw_ps}
set PYTHONPATH={PYTHONPATH}
set CONDARC=
""".format(here=dirname(__file__), PYTHONPATH=PYTHONPATH,
           ps_var=ps_var, raw_ps=raw_ps)

if platform.startswith("win"):
    command_setup = "@echo off\n" + command_setup


_format_vars = {
    'nul': nul,
    'printpath': printpath,
    'printdefaultenv': printdefaultenv,
    'printps1': printps1,
    'set_var': set_var,
    'source': source_setup,
    'binpath': binpath,
    'syspath': sys.prefix,
    'shell_suffix': shell_suffix
}

@pytest.mark.slow
def test_activate_test1():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (command_setup + """
            {source} {syspath}{binpath}activate{shell_suffix} "{env_dirs[0]}"
            {printpath}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, u'prepending {envpaths} to PATH'\
                    .format(envpaths=pathlist_to_str(_envpaths(envs, 'test1'))))
            assert_equals(stdout, pathsep.join(_envpaths(envs, 'test1') + [BASE_PATH, ]))


@pytest.mark.slow
def test_activate_test1_test2():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{binpath}activate "{env_dirs[1]}"
            {printpath}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, u'discarding {envpaths1} from PATH\nprepending {envpaths2} to PATH'\
                .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1')),
                        envpaths2=pathlist_to_str(_envpaths(envs, 'test2'))))
            assert_equals(stdout, pathsep.join(_envpaths(envs, 'test2') + [BASE_PATH, ]))


@pytest.mark.slow
def test_activate_test3():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[2]}"
            {printpath}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, u"%s" % BASE_PATH)
            assert_equals(stderr, u'Error: no such directory: {envpaths3}'.format(envpaths3=_envpaths(envs, 'test3')[0]))


@pytest.mark.slow
def test_activate_test1_test3():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{binpath}activate "{env_dirs[2]}"
            {printpath}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, pathsep.join(_envpaths(envs, 'test1')) + pathsep + BASE_PATH)
            assert_equals(stderr, u'Error: no such directory: {envpaths3}'.format(envpaths3=_envpaths(envs, 'test3')[0]))


@pytest.mark.slow
def test_activate_test1_deactivate():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {envs}{binpath}deactivate
            {printpath}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, u"%s" % BASE_PATH)
            assert_equals(stderr, u'discarding {envpaths1} from PATH'\
                .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))))


@pytest.mark.slow
def test_activate_root():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (command_setup + """
            {source} {syspath}{binpath}activate root
            {printpath}
            """).format(envs=envs, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, u"%s" % pathsep.join(_envpaths(root_dir) + [BASE_PATH, ]))
            assert_equals(stderr, u'prepending {syspath} to PATH'\
                .format(syspath=pathlist_to_str(_envpaths(root_dir))))

            commands = (command_setup + """
            {source} {syspath}{binpath}activate root
            {source} {syspath}{binpath}deactivate
            {printpath}
            """).format(envs=envs, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, u"%s" % BASE_PATH)
            assert_equals(stderr, u'prepending {syspath} to PATH\ndiscarding {syspath} from PATH'\
                .format(syspath=pathlist_to_str(_envpaths(root_dir))))


def test_activate_test1_root():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{binpath}activate root
            {printpath}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, u"%s" % pathsep.join(_envpaths(root_dir) + [BASE_PATH, ]))
            assert_equals(stderr, u'discarding {envpaths1} from PATH\nprepending {syspath} to PATH'\
                .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1')),
                    syspath=pathlist_to_str(_envpaths(root_dir))))


@pytest.mark.slow
def test_wrong_args():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (command_setup + """
            {source} {syspath}{binpath}activate two args
            {printpath}
            """).format(envs=envs, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, BASE_PATH)
            assert_equals(stderr, u'Error: did not expect more than one argument.')


@pytest.mark.slow
def test_activate_help():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            if not platform.startswith("win"):
                commands = (command_setup + """
                {envs}{binpath}activate Zanzibar
                """).format(envs=envs, **_format_vars)

                stdout, stderr = run_in(commands, shell)
                assert_equals(stdout, '')
                assert_in("activate must be sourced", stderr)
                assert_in("Usage: source activate ENV", stderr)

            commands = (command_setup + """
            {source} {syspath}{binpath}activate --help
            """).format(envs=envs, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '')
            if platform.startswith("win"):
                assert_in("Usage: activate ENV", stderr)
            else:
                assert_in("Usage: source activate ENV", stderr)

                commands = (command_setup + """
                {deactivate}
                """).format(envs=envs)

                stdout, stderr = run_in(commands, shell)
                assert_equals(stdout, '')
                assert_in("deactivate must be sourced", stderr)
                assert_in("Usage: source deactivate", stderr)

            commands = (command_setup + """
            {source} {syspath}{binpath}deactivate --help
            """).format(envs=envs, **_format_vars)

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
            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}"
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, u'prepending {envpaths1} to PATH'\
                    .format(syspath=pathlist_to_str(_envpaths(root_dir)),
                            envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))))

            env = gen_test_env_paths(envs)[0]
            for f in ['conda', 'activate', 'deactivate']:
                if platform == 'win':
                    file_path = join(env, "Scripts", f + ".bat")
                    assert os.path.exists(file_path)
                    with open(file_path) as batfile:
                        assert root_dir in "".join(batfile.readlines())
                else:
                    file_path = join(env, "bin", f)
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
                    conda, activate, deactivate = (join(syspath, binpath, cmd) for cmd in ("conda", "activate", "deactivate"))
                    prefix_bin_path = gen_test_env_paths(envs)[2] + binpath
                    commands = (command_setup + """
                    mkdir -p {env_dirs[2]}/bin
                    ln -s {activate} {prefix_bin_path}/activate
                    ln -s {deactivate} {prefix_bin_path}/deactivate
                    ln -s {conda} {prefix_bin_path}/conda
                    chmod 555 {prefix_bin_path}
                    {source} activate "{env}"
                    """).format(prefix_bin_path=prefix_bin_path, conda=conda,
                                activate=activate ,deactivate=deactivate,
                                **_format_vars)
                    stdout, stderr = run_in(commands, shell)
                    assert stdout != ''
                    assert_equals(stderr, u'prepending {bin_path} to PATH'.format(prefix_bin_path=prefix_bin_path, syspath=syspath))

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
                    {source} {syspath}{binpath}activate "{envs_dir[3]}"
                    echo $PATH
                    echo $CONDA_ACTIVE_ENV
                    """).format(envs=envs, **_format_vars)

                    stdout, stderr = run_in(commands, shell)
                    assert_equals(stdout, (
                        '{BASE_PATH}' # PATH
                        ''           # CONDA_ACTIVE_ENV
                        ).format(BASE_PATH=BASE_PATH))
                    assert_equals(stderr, (u'Cannot activate environment {envs}/test4, '
                        u'do not have write access to write conda symlink').format(envs=envs))

                finally:
                    # Change the permissions back so that we can delete the directory
                    run_in('chmod 777 {envs}/test3/bin'.format(envs=envs), shell)
                    run_in('chmod 777 {envs}/test4/bin'.format(envs=envs), shell)

def test_PS1():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}"
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, u'prepending {envpaths1} to PATH'\
                    .format(syspath=pathlist_to_str(_envpaths(root_dir)),
                            envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))))
            assert_equals(stdout, print_ps1(env_dirs=gen_test_env_paths(envs), number=0))

            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{binpath}activate "{env_dirs[1]}"
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, sterr = run_in(commands, shell)
            assert_equals(stderr, u'discarding {envpaths1} from PATH\nprepending {envpaths2} to PATH'.format(
                    envpaths1=pathlist_to_str(_envpaths(envs, 'test1')),
                    envpaths2=pathlist_to_str(_envpaths(envs, 'test2'))))

            assert_equals(stdout, print_ps1(env_dirs=gen_test_env_paths(envs), number=1))

            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[2]}"
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, u'Error: no such directory: {envpath3}'.format(envpath3=_envpaths(envs, 'test3')[0]))
            assert_equals(stdout, raw_ps)

            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{envs[0]}" {nul}
            {source} {syspath}{binpath}activate "{envs[3]}"
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, u'Error: no such directory: {envpath3}'.format(envpath3=_envpaths(envs, 'test3')[0]))
            assert_equals(stdout, print_ps1(env_dirs=gen_test_env_paths(envs), number=0))

            commands = (command_setup + """
            {source} {envs}{binpath}deactivate
            {printps1}
            """).format(envs=envs, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'Error: No environment to deactivate')
            assert_equals(stdout, raw_ps)

            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{envs[0]}" {nul}
            {source} {envs}{binpath}deactivate
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, u'discarding {envpaths1} from PATH'\
                    .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))))
            assert_equals(stdout, raw_ps)

            commands = (command_setup + """
            {source} {syspath}{binpath}activate two args
            {printps1}
            """).format(envs=envs, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, 'Error: did not expect more than one argument.')
            assert_equals(stdout, raw_ps)


@pytest.mark.slow
def test_PS1_no_changeps1():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            with open(join(envs, '.condarc'), 'w') as f:
                f.write("""\
changeps1: no
""")
            condarc = """
            {set_var}CONDARC={condarc}
            """
            commands = (command_setup + condarc + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}"
            {printps1}
            """).format(condarc=join(envs, ".condarc"), envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, u'prepending {envpaths1} to PATH'\
                    .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1')),
                            syspath=pathlist_to_str(_envpaths(root_dir))))
            assert_equals(stdout, raw_ps)

            commands = (command_setup + condarc + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{binpath}activate "{env_dirs[1]}"
            {printps1}
            """).format(condarc=join(envs, ".condarc"), envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, u'discarding {envpaths1} from PATH\nprepending {envpaths2} to PATH'\
                    .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1')),
                            envpaths2=pathlist_to_str(_envpaths(envs, 'test2'))))
            assert_equals(stdout, raw_ps)

            commands = (command_setup + condarc + """
            {source} {syspath}{binpath}activate "{env_dirs[2]}"
            {printps1}
            """).format(condarc=join(envs, ".condarc"), envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, raw_ps)
            if platform == 'win':
                assert_equals(stderr, u'Error: no such directory: {env_dirs[2]}'.format(envs=envs,
                                                                             env_dirs=gen_test_env_paths(envs)))
            else:
                assert_equals(stderr, u'Error: no such directory: {env_dirs[2]}/bin'.format(envs=envs,
                                                                             env_dirs=gen_test_env_paths(envs)))

            commands = (command_setup + condarc + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{binpath}activate "{env_dirs[2]}"
            {printps1}
            """).format(condarc=join(envs, ".condarc"), envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, raw_ps)
            if platform == 'win':
                assert_equals(stderr, u'Error: no such directory: {env_dirs[2]}'.format(envs=envs, env_dirs=gen_test_env_paths(envs)))
            else:
                assert_equals(stderr, u'Error: no such directory: {env_dirs[2]}/bin'.format(envs=envs, env_dirs=gen_test_env_paths(envs)))

            commands = (command_setup + condarc + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {envs}{binpath}deactivate
            {printps1}
            """).format(condarc=join(envs, ".condarc"), envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, u'discarding {envpaths1} from PATH'.format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))))
            assert_equals(stdout, raw_ps)

            commands = (command_setup + condarc + """
            {source} {syspath}{binpath}activate two args
            {printps1}
            """).format(condarc=join(envs, ".condarc"), envs=envs, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, raw_ps)
            assert_equals(stderr, 'Error: did not expect more than one argument.')


@pytest.mark.slow
def test_CONDA_ACTIVE_ENV():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}"
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, u'{env_dirs[0]}'.format(envs=envs, env_dirs=gen_test_env_paths(envs)))
            assert_equals(stderr, u'prepending {envpaths1} to PATH'.format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))))

            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{binpath}activate "{env_dirs[1]}"
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, u'{env_dirs[1]}'.format(env_dirs=gen_test_env_paths(envs)))
            assert_equals(stderr,
                u'discarding {envpaths1} from PATH\n'.format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))) +
                u'prepending {envpaths2} to PATH'.format(envpaths2=pathlist_to_str(_envpaths(envs, 'test2'))))

            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[2]}"
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '')
            assert_equals(stderr, u'Error: no such directory: {envpaths3}'.format(envpaths3=_envpaths(envs, 'test3')[0]))

            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{binpath}activate "{env_dirs[2]}"
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '{env_dirs[0]}'.format(env_dirs=gen_test_env_paths(envs)))
            assert_equals(stderr, u'Error: no such directory: {envpaths3}'.format(envpaths3=_envpaths(envs, 'test3')[0]))

            commands = (command_setup + """
            {source} {envs}{binpath}deactivate
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '')
            assert_equals(stderr, '')

            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {envs}{binpath}deactivate
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '')
            assert_equals(stderr, u'discarding {envpaths1} from PATH'\
                    .format(envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))))

            commands = (command_setup + """
            {source} {syspath}{binpath}activate two args
            {printdefaultenv}
            """).format(envs=envs, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '')
            assert_equals(stderr, 'Error: did not expect more than one argument.')

            commands = (command_setup + """
            {source} {syspath}{binpath}activate root {nul}
            {printdefaultenv}
            """).format(envs=envs, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, 'root')
            assert_equals(stderr, '')

            commands = (command_setup + """
            {source} {syspath}{binpath}activate root {nul}
            {source} {envs}{binpath}deactivate {nul}
            {printdefaultenv}
            """).format(envs=envs, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '')
            assert_equals(stderr, '')

