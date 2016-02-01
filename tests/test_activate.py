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

def assert_equals(a, b, output=""):
    output = "%r != %r" % (a, b) + "\n\n" + output
    assert a == b, output


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

escape_curly = lambda x: x.replace("{", "{{").replace("}", "}}")

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
    set_var = 'export '
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

raw_ps = escape_curly(os.getenv(ps_var, ""))
def print_ps1(env_dirs, number):
    return u" ".join([u"({})".format(os.path.split(env_dirs[number])[-1]), raw_ps]).strip()

CONDA_ENTRY_POINT = """\
#!{syspath}/python
import sys
from conda.cli import main

sys.exit(main())
"""
printpath = '{echo} {var}'.format(echo=echo, var=var_format.format(var="PATH"))
if sys.platform == "win32":
    printdefaultenv = '{echo}.{var}'.format(echo=echo, var=var_format.format(var="CONDA_DEFAULT_ENV"))
else:
    printdefaultenv = '{echo} {var}'.format(echo=echo, var=var_format.format(var="CONDA_DEFAULT_ENV"))

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
def test_activate_env_from_env_with_root_activate():
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
def test_activate_bad_directory():
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
def test_activate_bad_env_keeps_existing_good_env():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{binpath}activate "{env_dirs[2]}"
            {printpath}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, pathsep.join(_envpaths(envs, 'test1')) + pathsep + BASE_PATH, stderr)


@pytest.mark.slow
def test_activate_deactivate():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{binpath}deactivate
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
            assert_equals(stdout, u"%s" % pathsep.join(_envpaths(root_dir) + [BASE_PATH, ]), stderr)

            commands = (command_setup + """
            {source} {syspath}{binpath}activate root
            {source} {syspath}{binpath}deactivate
            {printpath}
            """).format(envs=envs, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, u"%s" % BASE_PATH, stderr)


def test_activate_root_env_from_other_env():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{binpath}activate root
            {printpath}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, u"%s" % pathsep.join(_envpaths(root_dir) + [BASE_PATH, ]), stderr)


@pytest.mark.slow
def test_wrong_args():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (command_setup + """
            {source} {syspath}{binpath}activate two args
            {printpath}
            """).format(envs=envs, **_format_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, u'Error: did not expect more than one argument.')
            assert_equals(stdout, BASE_PATH, stderr)


@pytest.mark.slow
def test_activate_help():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            if not platform.startswith("win"):
                commands = (command_setup + """
                {syspath}{binpath}activate Zanzibar
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
                {syspath}{binpath}deactivate
                """).format(envs=envs, **_format_vars)
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

            for env in gen_test_env_paths(envs)[:2]:
                for f in ['conda', 'activate', 'deactivate']:
                    if platform.startswith('win'):
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
                        assert os.readlink(file_path) == '{root_path}'.format(root_path=join(sys.prefix, "bin", f))

            if platform != 'win':
                # Test activate when there are no write permissions in the
                # env. 
                prefix_bin_path = gen_test_env_paths(envs)[2] + binpath
                commands = (command_setup + """
                mkdir -p {prefix_bin_path}
                chmod 000 {prefix_bin_path}
                {source} activate "{env_dirs[2]}"
                """).format(prefix_bin_path=prefix_bin_path, envs=envs, 
                                    env_dirs=gen_test_env_paths(envs),
                    **_format_vars)
                stdout, stderr = run_in(commands, shell)
                assert_in("do not have write access", stderr)

                # restore permissions so the dir will get cleaned up
                run_in("chmod 777 {prefix_bin_path}".format(prefix_bin_path=prefix_bin_path))


def test_PS1():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            # activate changes PS1 correctly
            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}"
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, print_ps1(env_dirs=gen_test_env_paths(envs), number=0), stderr)

            # second activate replaces earlier actived env PS1
            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{binpath}activate "{env_dirs[1]}"
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)
            stdout, sterr = run_in(commands, shell)
            assert_equals(stdout, print_ps1(env_dirs=gen_test_env_paths(envs), number=1), stderr)

            # failed activate does not touch raw PS1
            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[2]}"
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, raw_ps, stderr)

            # ensure that a failed activate does not touch PS1 (envs[3] folders do not exist.)
            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{binpath}activate "{env_dirs[2]}"
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, print_ps1(env_dirs=gen_test_env_paths(envs), number=0), stderr)

            # deactivate doesn't do anything bad to PS1 when no env active to deactivate
            commands = (command_setup + """
            {source} {syspath}{binpath}deactivate
            {printps1}
            """).format(envs=envs, **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, raw_ps, stderr)

            # deactivate script in activated env returns us to raw PS1
            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {env_dirs[0]}{binpath}deactivate
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, raw_ps, stderr)

            # make sure PS1 is unchanged by faulty activate input
            commands = (command_setup + """
            {source} {syspath}{binpath}activate two args
            {printps1}
            """).format(envs=envs, **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, raw_ps, stderr)


@pytest.mark.slow
def test_PS1_no_changeps1():
    """Ensure that people's PS1 remains unchanged if they have that setting in their RC file."""
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
            assert_equals(stdout, raw_ps, stderr)

            commands = (command_setup + condarc + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{binpath}activate "{env_dirs[1]}"
            {printps1}
            """).format(condarc=join(envs, ".condarc"), envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, raw_ps, stderr)

            commands = (command_setup + condarc + """
            {source} {syspath}{binpath}activate "{env_dirs[2]}"
            {printps1}
            """).format(condarc=join(envs, ".condarc"), envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, raw_ps, stderr)

            commands = (command_setup + condarc + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{binpath}activate "{env_dirs[2]}"
            {printps1}
            """).format(condarc=join(envs, ".condarc"), envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, raw_ps, stderr)

            commands = (command_setup + condarc + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {env_dirs[0]}{binpath}deactivate
            {printps1}
            """).format(condarc=join(envs, ".condarc"), envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, raw_ps, stderr)

            commands = (command_setup + condarc + """
            {source} {syspath}{binpath}activate two args
            {printps1}
            """).format(condarc=join(envs, ".condarc"), envs=envs, **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, raw_ps, stderr)


@pytest.mark.slow
def test_CONDA_DEFAULT_ENV():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}"
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, u'{env_dirs[0]}'.format(envs=envs, env_dirs=gen_test_env_paths(envs)), stderr)

            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{binpath}activate "{env_dirs[1]}"
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, u'{env_dirs[1]}'.format(env_dirs=gen_test_env_paths(envs)), stderr)

            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[2]}"
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '', stderr)

            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{binpath}activate "{env_dirs[2]}"
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '{env_dirs[0]}'.format(env_dirs=gen_test_env_paths(envs)), stderr)

            commands = (command_setup + """
            {source} {syspath}{binpath}deactivate
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '', stderr)

            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
            {source} {env_dirs[0]}{binpath}deactivate
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '', stderr)

            commands = (command_setup + """
            {source} {syspath}{binpath}activate two args
            {printdefaultenv}
            """).format(envs=envs, **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '', stderr)

            commands = (command_setup + """
            {source} {syspath}{binpath}activate root {nul}
            {printdefaultenv}
            """).format(envs=envs, **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, 'root', stderr)

            commands = (command_setup + """
            {source} {syspath}{binpath}activate root {nul}
            {source} {env_dirs[0]}{binpath}deactivate {nul}
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '', stderr)

@pytest.mark.slow
def test_activate_from_env():
    """Tests whether the activate bat file or link in the activated environment works OK"""
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}"
            {source} {env_dirs[0]}{binpath}activate "{env_dirs[1]}"
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, u'{env_dirs[1]}'.format(envs=envs, env_dirs=gen_test_env_paths(envs)), stderr)


@pytest.mark.slow
def test_deactivate_from_env():
    """Tests whether the deactivate bat file or link in the activated environment works OK"""
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (command_setup + """
            {source} {syspath}{binpath}activate "{env_dirs[0]}"
            {source} {env_dirs[0]}{binpath}deactivate
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **_format_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, u'', stderr)
