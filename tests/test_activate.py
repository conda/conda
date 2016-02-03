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

def convert_path_to_dos(path_list):
    """For bash on Windows: convert paths to dos style for native comparison"""
    print(path_list)
    if not path_list:
        return path_list
    p = subprocess.Popen([shell, '-c', 'cygpath.exe -w -p "%s"' % path_list], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    streams = [stream.strip().decode('utf-8').replace('\r\n', '\n').replace('\\\\', '\\')
                      for stream in (stdout, stderr)]
    return streams[0]

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
        p = subprocess.Popen([shell, '-c', command.replace("\\", "/")], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
    streams = [stream.strip().decode('utf-8').replace('\r\n', '\n').replace('\\\\', '\\')
                      for stream in (stdout, stderr)]
    if sys.platform == "win32":
        if shell == 'bash':
            # MinGW/Cygwin has /usr/bin on the end and it gets concatenated incorrectly
            streams[0] = convert_path_to_dos(streams[0])
            if streams[0].endswith("\\usr\\bin"):
                streams[0] = streams[0][:-8] + u"\\bin;"
        streams = [stream.replace("/", "\\") for stream in streams]
    return streams

def assert_equals(a, b, output=""):
    output = "%r != %r" % (a.lower(), b.lower()) + "\n\n" + output
    assert a.lower() == b.lower(), output

def assert_not_in(a, b):
    assert a.lower() not in b.lower(), "%r should not be found in %r" % (a.lower(), b.lower())

def assert_in(a, b):
    assert a.lower() in b.lower(), "%r cannot be found in %r" % (a.lower(), b.lower())


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
                join(env_root, env_name, 'cmd'),
                join(env_root, env_name, 'Scripts'),
                join(env_root, env_name, 'Library', 'bin'),
               ]
    else:
        paths = [join(env_root, env_name).rstrip("/"),
                 join(env_root, env_name, 'cmd'),
                 join(env_root, env_name, 'bin'), ]
    return paths


PYTHONPATH = os.path.dirname(os.path.dirname(__file__))

# Make sure the subprocess activate calls this python
syspath = pathsep.join(_envpaths(root_dir))

echo = "echo"

escape_curly = lambda x: x.replace("{", "{{").replace("}", "}}")

unix_shell_base = dict(ps_var="PS1",
                       echo="echo",
                       test_echo_extra="",
                       var_format="${var}",
                       binpath="/bin/",  # mind the trailing slash.
                       source_setup="source",
                       nul='2>/dev/null',
                       set_var='export ',
                       shell_suffix="",
                       printps1='echo $PS1',
                       printdefaultenv='echo $CONDA_DEFAULT_ENV',
                       printpath="echo $PATH",
                       raw_ps=os.getenv("PS1", ""),
)

if platform.startswith("win"):
    shells = {
        #"powershell": dict(
        #    echo="echo",
        #    test_echo_extra=" .",
        #    ps_var="PS1",
        #    var_format="${var}",
        #    binpath="/bin/",  # mind the trailing slash.
        #    source_setup="source",
        #    nul='2>/dev/null',
        #    set_var='export ',
        #    shell_suffix=".ps",
        #    printps1='echo $PS1',
        #    printdefaultenv='echo $CONDA_DEFAULT_ENV',
        #    printpath="echo %PATH%",
        #    raw_ps=os.getenv("PROMPT", ""),
        #),
        "cmd.exe": dict(
            echo="echo",
            ps_var="PROMPT",
            var_format="%{var}%",
            binpath="\\Scripts\\",  # mind the trailing slash.
            source_setup="call",
            test_echo_extra="",
            nul='1>NUL 2>&1',
            set_var='set ',
            shell_suffix=".bat",
            printps1="echo %PROMPT%",
            printdefaultenv='IF NOT "%CONDA_DEFAULT_ENV%" == "" (\n'
                            'echo %CONDA_DEFAULT_ENV% ) ELSE (\n'
                            'echo()', # parens mismatched intentionally.  See http://stackoverflow.com/questions/20691060/how-do-i-echo-a-blank-empty-line-to-the-console-from-a-windows-batch-file
            printpath="echo %PATH%",
            raw_ps=os.getenv("PROMPT", ""),
        ),
        "bash": unix_shell_base.copy(),
    }

else:
    shells = {"bash": unix_shell_base.copy(),
              "zsh": unix_shell_base.copy()
    }

cmd_path = '/cmd/'
if sys.platform == 'win32':
    cmd_path = cmd_path.replace('/', '\\')

working_shells = {}
for shell in shells:
    try:
        stdout, stderr = run_in('echo' + shells[shell]['test_echo_extra'], shell)
    except OSError:
        pass
    else:
        if not stderr:
            working_shells[shell]=shells[shell]

shells = working_shells

def print_ps1(env_dirs, shell, number):
    return u" ".join([u"(({}))".format(os.path.split(env_dirs[number])[-1]), escape_curly(os.getenv(shells[shell]["ps_var"], ""))]).strip()

CONDA_ENTRY_POINT = """\
#!{syspath}/python
import sys
from conda.cli import main

sys.exit(main())
"""

def _format_vars(shell):

    base_path, stderr = run_in(shells[shell]['printpath'], shell)

    shell = shells[shell]
    command_setup = """\
set {ps_var}={raw_ps}
set PYTHONPATH={PYTHONPATH}
set CONDARC=
""".format(here=dirname(__file__), PYTHONPATH=PYTHONPATH,
           ps_var=shell["ps_var"], raw_ps=shell['raw_ps'])

    if shell["shell_suffix"] == '.bat':
        command_setup = "@echo off\n" + command_setup


    return {
        'nul': shell['nul'],
        'printpath': shell['printpath'],
        'printdefaultenv': shell['printdefaultenv'],
        'printps1': shell['printps1'],
        'raw_ps': shell["raw_ps"],
        'set_var': shell['set_var'],
        'source': shell['source_setup'],
        'binpath': shell['binpath'],
        'shell_suffix': shell['shell_suffix'],
        'syspath': sys.prefix,
        'cmd_path': cmd_path,
        'command_setup': command_setup,
        'base_path': base_path,
}

@pytest.mark.slow
def test_activate_test1():
    for shell in shells:
        shell_vars = _format_vars(shell)
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate{shell_suffix} "{env_dirs[0]}"
            {printpath}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, u'prepending {envpaths} to PATH'\
                    .format(envpaths=pathlist_to_str(_envpaths(envs, 'test1'))))
            assert_in(pathsep.join(_envpaths(envs, 'test1')), stdout)


@pytest.mark.slow
def test_activate_env_from_env_with_root_activate():
    for shell in shells:
        shell_vars = _format_vars(shell)
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{cmd_path}activate "{env_dirs[1]}"
            {printpath}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, u'prepending {envpaths2} to PATH'\
                .format(envpaths2=pathlist_to_str(_envpaths(envs, 'test2'))))
            assert_in(pathsep.join(_envpaths(envs, 'test2')), stdout)


@pytest.mark.slow
def test_activate_bad_directory():
    for shell in shells:
        shell_vars = _format_vars(shell)
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate "{env_dirs[2]}"
            {printpath}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)

            stdout, stderr = run_in(commands, shell)
            assert_not_in(_envpaths(envs, 'test3')[0], stdout)
            assert_equals(stderr, u'Error: could not find environment: {envpaths3}'.format(envpaths3=_envpaths(envs, 'test3')[0]))


@pytest.mark.slow
def test_activate_bad_env_keeps_existing_good_env():
    for shell in shells:
        shell_vars = _format_vars(shell)
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{cmd_path}activate "{env_dirs[2]}"
            {printpath}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)

            stdout, stderr = run_in(commands, shell)
            assert_in(pathsep.join(_envpaths(envs, 'test1')), stdout)


@pytest.mark.slow
def test_activate_deactivate():
    for shell in shells:
        shell_vars = _format_vars(shell)
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{cmd_path}deactivate
            {printpath}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)

            print(commands)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, u"%s" % shell_vars['base_path'])


@pytest.mark.slow
def test_activate_root():
    for shell in shells:
        shell_vars = _format_vars(shell)
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate root
            {printpath}
            """).format(envs=envs, **shell_vars)

            stdout, stderr = run_in(commands, shell)
            assert_in(pathsep.join(_envpaths(root_dir)), stdout)

            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate root
            {source} {syspath}{cmd_path}deactivate
            {printpath}
            """).format(envs=envs, **shell_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, u"%s" % shell_vars['base_path'], stderr)


def test_activate_root_env_from_other_env():
    for shell in shells:
        shell_vars = _format_vars(shell)
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{cmd_path}activate root
            {printpath}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)

            stdout, stderr = run_in(commands, shell)
            assert_in(pathsep.join(_envpaths(root_dir)), stdout)
            assert_not_in(pathsep.join(_envpaths(envs, 'test1')), stdout)


@pytest.mark.slow
def test_wrong_args():
    for shell in shells:
        shell_vars = _format_vars(shell)
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate two args
            {printpath}
            """).format(envs=envs, **shell_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, u'Error: did not expect more than one argument.')
            assert_equals(stdout, shell_vars['base_path'], stderr)


@pytest.mark.slow
def test_activate_help():
    for shell in shells:
        shell_vars = _format_vars(shell)
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            if not platform.startswith("win"):
                commands = (shell_vars['command_setup'] + """
                {syspath}{cmd_path}activate Zanzibar
                """).format(envs=envs, **shell_vars)
                stdout, stderr = run_in(commands, shell)
                assert_equals(stdout, '')
                assert_in("activate must be sourced", stderr)
                assert_in("Usage: source activate ENV", stderr)

            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate --help
            """).format(envs=envs, **shell_vars)

            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '')
            if platform.startswith("win") and shell in ["cmd.exe", "powershell"]:
                assert_in("Usage: activate ENV", stderr)
            else:
                assert_in("Usage: source activate ENV", stderr)

                commands = (shell_vars['command_setup'] + """
                {syspath}{cmd_path}deactivate
                """).format(envs=envs, **shell_vars)
                stdout, stderr = run_in(commands, shell)
                assert_equals(stdout, '')
                assert_in("deactivate must be sourced", stderr)
                assert_in("Usage: source deactivate", stderr)

            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}deactivate --help
            """).format(envs=envs, **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '')
            if platform == 'win' and shell in ["cmd.exe", "powershell"]:
                assert_in("Usage: deactivate", stderr)
            else:
                assert_in("Usage: source deactivate", stderr)

@pytest.mark.slow
def test_activate_symlinking():
    for shell in shells:
        shell_vars = _format_vars(shell)
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate "{env_dirs[0]}"
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stderr, u'prepending {envpaths1} to PATH'\
                    .format(syspath=pathlist_to_str(_envpaths(root_dir)),
                            envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))))

            where = 'Scripts' if sys.platform == 'win32' else 'bin'
            for env in gen_test_env_paths(envs)[:2]:
                scripts = {where: ["conda"],
                           'cmd': ["activate", "deactivate"],
                }
                for where, files in scripts.items():
                    for f in files:
                        if platform.startswith('win'):
                            file_path = join(env, where, f + ".bat")
                            assert os.path.exists(file_path)
                            with open(file_path) as batfile:
                                assert root_dir in "".join(batfile.readlines())
                        else:
                            file_path = join(env, where, f)
                            assert os.path.lexists(file_path)
                            assert os.path.exists(file_path)
                            s = os.lstat(file_path)
                            assert stat.S_ISLNK(s.st_mode)
                            assert os.readlink(file_path) == '{root_path}'.format(root_path=join(sys.prefix, "bin", f))

            if platform != 'win':
                # Test activate when there are no write permissions in the
                # env. 
                prefix_bin_path = gen_test_env_paths(envs)[2] + binpath
                commands = (shell_vars['command_setup'] + """
                mkdir -p {prefix_bin_path}
                chmod 000 {prefix_bin_path}
                {source} activate "{env_dirs[2]}"
                """).format(prefix_bin_path=prefix_bin_path, envs=envs, 
                                    env_dirs=gen_test_env_paths(envs),
                    **shell_vars)
                stdout, stderr = run_in(commands, shell)
                assert_in("do not have write access", stderr)

                # restore permissions so the dir will get cleaned up
                run_in("chmod 777 {prefix_bin_path}".format(prefix_bin_path=prefix_bin_path))


def test_PS1():
    for shell in shells:
        shell_vars = _format_vars(shell)
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            # activate changes PS1 correctly
            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate "{env_dirs[0]}"
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, print_ps1(env_dirs=gen_test_env_paths(envs), shell=shell, number=0), stderr)

            # second activate replaces earlier actived env PS1
            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{cmd_path}activate "{env_dirs[1]}"
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)
            stdout, sterr = run_in(commands, shell)
            assert_equals(stdout, print_ps1(env_dirs=gen_test_env_paths(envs), shell=shell,number=1), stderr)

            # failed activate does not touch raw PS1
            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate "{env_dirs[2]}"
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, shell_vars['raw_ps'], stderr)

            # ensure that a failed activate does not touch PS1 (envs[3] folders do not exist.)
            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{cmd_path}activate "{env_dirs[2]}"
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, print_ps1(env_dirs=gen_test_env_paths(envs), shell=shell,number=0), stderr)

            # deactivate doesn't do anything bad to PS1 when no env active to deactivate
            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}deactivate
            {printps1}
            """).format(envs=envs, **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, shell_vars['raw_ps'], stderr)

            # deactivate script in activated env returns us to raw PS1
            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate "{env_dirs[0]}" {nul}
            {source} {env_dirs[0]}{cmd_path}deactivate
            {printps1}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, shell_vars['raw_ps'], stderr)

            # make sure PS1 is unchanged by faulty activate input
            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate two args
            {printps1}
            """).format(envs=envs, **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, shell_vars['raw_ps'], stderr)


@pytest.mark.slow
def test_PS1_no_changeps1():
    """Ensure that people's PS1 remains unchanged if they have that setting in their RC file."""
    for shell in shells:
        shell_vars = _format_vars(shell)
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            with open(join(envs, '.condarc'), 'w') as f:
                f.write("""\
changeps1: no
""")
            condarc = """
            {set_var}CONDARC={condarc}
            """
            commands = (shell_vars['command_setup'] + condarc + """
            {source} {syspath}{cmd_path}activate "{env_dirs[0]}"
            {printps1}
            """).format(condarc=join(envs, ".condarc"), envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, shell_vars['raw_ps'], stderr)

            commands = (shell_vars['command_setup'] + condarc + """
            {source} {syspath}{cmd_path}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{cmd_path}activate "{env_dirs[1]}"
            {printps1}
            """).format(condarc=join(envs, ".condarc"), envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, shell_vars['raw_ps'], stderr)

            commands = (shell_vars['command_setup'] + condarc + """
            {source} {syspath}{cmd_path}activate "{env_dirs[2]}"
            {printps1}
            """).format(condarc=join(envs, ".condarc"), envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, shell_vars['raw_ps'], stderr)

            commands = (shell_vars['command_setup'] + condarc + """
            {source} {syspath}{cmd_path}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{cmd_path}activate "{env_dirs[2]}"
            {printps1}
            """).format(condarc=join(envs, ".condarc"), envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, shell_vars['raw_ps'], stderr)

            commands = (shell_vars['command_setup'] + condarc + """
            {source} {syspath}{cmd_path}activate "{env_dirs[0]}" {nul}
            {source} {env_dirs[0]}{cmd_path}deactivate
            {printps1}
            """).format(condarc=join(envs, ".condarc"), envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, shell_vars['raw_ps'], stderr)

            commands = (shell_vars['command_setup'] + condarc + """
            {source} {syspath}{cmd_path}activate two args
            {printps1}
            """).format(condarc=join(envs, ".condarc"), envs=envs, **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, shell_vars['raw_ps'], stderr)


@pytest.mark.slow
def test_CONDA_DEFAULT_ENV():
    for shell in shells:
        shell_vars = _format_vars(shell)
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate "{env_dirs[0]}"
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, u'{env_dirs[0]}'.format(envs=envs, env_dirs=gen_test_env_paths(envs)), stderr)

            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{cmd_path}activate "{env_dirs[1]}"
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, u'{env_dirs[1]}'.format(env_dirs=gen_test_env_paths(envs)), stderr)

            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate "{env_dirs[2]}"
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '', stderr)

            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate "{env_dirs[0]}" {nul}
            {source} {syspath}{cmd_path}activate "{env_dirs[2]}"
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '{env_dirs[0]}'.format(env_dirs=gen_test_env_paths(envs)), stderr)

            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}deactivate
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '', stderr)

            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate "{env_dirs[0]}" {nul}
            {source} {env_dirs[0]}{cmd_path}deactivate
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '', stderr)

            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate two args
            {printdefaultenv}
            """).format(envs=envs, **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '', stderr)

            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate root {nul}
            {printdefaultenv}
            """).format(envs=envs, **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, u"%s" % sys.prefix, stderr)

            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate root {nul}
            {source} {env_dirs[0]}{cmd_path}deactivate {nul}
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '', stderr)

@pytest.mark.slow
def test_activate_from_env():
    """Tests whether the activate bat file or link in the activated environment works OK"""
    for shell in shells:
        shell_vars = _format_vars(shell)
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate "{env_dirs[0]}"
            {source} {env_dirs[0]}{cmd_path}activate "{env_dirs[1]}"
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, u'{env_dirs[1]}'.format(envs=envs, env_dirs=gen_test_env_paths(envs)), stderr)


@pytest.mark.slow
def test_deactivate_from_env():
    """Tests whether the deactivate bat file or link in the activated environment works OK"""
    for shell in shells:
        shell_vars = _format_vars(shell)
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            commands = (shell_vars['command_setup'] + """
            {source} {syspath}{cmd_path}activate "{env_dirs[0]}"
            {source} {env_dirs[0]}{cmd_path}deactivate
            {printdefaultenv}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs), **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, u'', stderr)
