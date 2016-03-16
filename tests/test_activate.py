# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import

import os
from os.path import dirname, join, pathsep
import shutil
import shlex
import stat
import subprocess
import sys

import pytest

from conda.compat import TemporaryDirectory
from conda.config import root_dir, platform
from conda.install import symlink_conda
from conda.utils import (win_path_to_unix, unix_path_to_win, win_path_to_cygwin,
                                cygwin_path_to_win, translate_stream)
from conda.cli.activate import pathlist_to_str
import subprocess
import tempfile

from tests.helpers import assert_equals, assert_in, assert_not_in

# make pathsep unicode for sake of windows backslash string formatting
pathsep = u"%s" % pathsep

def path_identity(path):
    """Used as a dummy path converter where no conversion necessary"""
    return path

# defaults for unix shells.  Note: missing "exe" entry, which should be set to
#    either an executable on PATH, or a full path to an executable for a shell
unix_shell_base = dict(ps_var="PS1",
                       echo="echo",
                       test_echo_extra="",
                       var_format="${}",
                       binpath="/bin/",  # mind the trailing slash.
                       source_setup="source",
                       nul='2>/dev/null',
                       set_var='export ',
                       shell_suffix="",
                       env_script_suffix=".sh",
                       printps1='echo $PS1',
                       printdefaultenv='echo $CONDA_DEFAULT_ENV',
                       printpath="echo $PATH",
                       raw_ps=os.getenv("PS1", ""),
                       shell_args=["-l", "-c"],
                       path_from=path_identity,
                       path_to=path_identity,
                       slash_convert=("\\", "/"),
)

if sys.platform == "win32":
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
        #    env_script_suffix=".ps",
        #    printps1='echo $PS1',
        #    printdefaultenv='echo $CONDA_DEFAULT_ENV',
        #    printpath="echo %PATH%",
        #    raw_ps=os.getenv("PROMPT", ""),
        #    exe="powershell.exe",
        #    path_from=path_identity,
        #    path_to=path_identity,
        #    slash_convert = ("/", "\\"),
        #),
        "cmd.exe": dict(
            echo="echo",
            ps_var="PROMPT",
            var_format="%{}%",
            binpath="\\Scripts\\",  # mind the trailing slash.
            source_setup="call",
            test_echo_extra="",
            nul='1>NUL 2>&1',
            set_var='set ',
            shell_suffix=".bat",
            env_script_suffix=".bat",
            printps1="echo %PROMPT%",
            printdefaultenv='IF NOT "%CONDA_DEFAULT_ENV%" == "" (\n'
                            'echo %CONDA_DEFAULT_ENV% ) ELSE (\n'
                            'echo()', # parens mismatched intentionally.  See http://stackoverflow.com/questions/20691060/how-do-i-echo-a-blank-empty-line-to-the-console-from-a-windows-batch-file
            printpath="echo %PATH%",
            raw_ps=os.getenv("PROMPT", ""),
            exe="cmd.exe",
            shell_args=["/d", "/c"],
            path_from=path_identity,
            path_to=path_identity,
            slash_convert = ("/", "\\"),
        ),
        "cygwin": dict(unix_shell_base,
                       exe="bash",
                       path_from=cygwin_path_to_win,
                       path_to=win_path_to_cygwin),
        # bash is whichever bash is on PATH.  If using Cygwin, you should use the cygwin entry instead.
        # The only major difference is that it handle's cywin's /cygdrive filesystem root.
        "bash": dict(unix_shell_base,
                     exe="bash",
                     path_from=unix_path_to_win,
                     path_to=win_path_to_unix),
    }

else:
    shells = {
        "bash": dict(unix_shell_base, exe="bash"),
        "zsh": dict(unix_shell_base, exe="zsh"),
        #"fish": dict(unix_shell_base, exe="fish",
        #             shell_suffix=".fish",
        #             source_setup=""),
    }

def run_in(command, shell):
    if shell == 'cmd.exe':
        cmd_script = tempfile.NamedTemporaryFile(suffix='.bat', mode='wt', delete=False)
        cmd_script.write(command)
        cmd_script.close()
        cmd_bits = [shells[shell]["exe"]] + shells[shell]["shell_args"] + [cmd_script.name]
        try:
            p = subprocess.Popen(cmd_bits, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
        finally:
            os.unlink(cmd_script.name)
    elif shell == 'powershell':
        raise NotImplementedError
    else:
        cmd_bits = [shells[shell]["exe"]] + shells[shell]["shell_args"] + [translate_stream(command, shells[shell]["path_to"])]
        p = subprocess.Popen(cmd_bits, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
    output_translator = shells[shell]["path_from"]
    streams = [u"%s" % translate_stream(stream.strip().decode('utf-8').replace('\r\n', '\n'), output_translator)
                      for stream in (stdout, stderr)]
    return streams


def gen_test_env_paths(envs, shell, num_test_folders=3):
    """People need not use all the test folders listed here.
    This is only for shortening the environment string generation.

    Also encapsulates paths in double quotes.
    """
    paths = [join(envs, "test {}".format(test_folder+1)) for test_folder in range(num_test_folders)]
    for path in paths[:2]:      # Create symlinks ONLY for the first two folders.
        symlink_conda(path, sys.prefix, shell)
    converter = shells[shell]["path_to"]
    paths = [converter(path) for path in paths]
    return paths

def _envpaths(env_root, env_name=""):
    """Supply the appropriate platform executable folders.  rstrip on root removes
       trailing slash if env_name is empty (the default)"""
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

cmd_path = '/cmd/'

def print_ps1(env_dirs, shell, number):
    return u" ".join([u"(({}))".format(os.path.split(env_dirs[number])[-1]), escape_curly(os.getenv(shells[shell]["ps_var"], ""))]).strip()


CONDA_ENTRY_POINT = """\
#!{syspath}/python
import sys
from conda.cli import main

sys.exit(main())
"""


def _format_vars(shell):
    shelldict = shells[shell]
    command_setup = """\
set {ps_var}={raw_ps}
set PYTHONPATH={PYTHONPATH}
set CONDARC=
""".format(here=dirname(__file__), PYTHONPATH=PYTHONPATH,
           ps_var=shelldict["ps_var"], raw_ps=shelldict['raw_ps'])

    if shelldict["shell_suffix"] == '.bat':
        command_setup = "@echo off\n" + command_setup

    base_path, _ = run_in(command_setup + shelldict['printpath'], shell)

    return {
        'echo': shelldict['echo'],
        'nul': shelldict['nul'],
        'printpath': shelldict['printpath'],
        'printdefaultenv': shelldict['printdefaultenv'],
        'printps1': shelldict['printps1'],
        'raw_ps': shelldict["raw_ps"],
        'set_var': shelldict['set_var'],
        'source': shelldict['source_setup'],
        'binpath': shelldict['binpath'],
        'shell_suffix': shelldict['shell_suffix'],
        'syspath': sys.prefix,
        'cmd_path': cmd_path.replace(*shelldict["slash_convert"]),
        'command_setup': command_setup,
        'base_path': base_path,
}


def test_path_translation():
    test_cygwin_path = "/usr/bin:/cygdrive/z/documents (x86)/code/conda/tests/envskhkzts/test1:/cygdrive/z/documents/code/conda/tests/envskhkzts/test1/cmd"
    test_unix_path = "/usr/bin:/z/documents (x86)/code/conda/tests/envskhkzts/test1:/z/documents/code/conda/tests/envskhkzts/test1/cmd"
    test_win_path = "z:\\documents (x86)\\code\\conda\\tests\\envskhkzts\\test1;z:\\documents\\code\\conda\\tests\\envskhkzts\\test1\\cmd"
    assert_equals(test_win_path, unix_path_to_win(test_unix_path))
    assert_equals(test_unix_path.replace("/usr/bin:", ""), win_path_to_unix(test_win_path))
    assert_equals(test_cygwin_path.replace("/usr/bin:", ""), win_path_to_cygwin(test_win_path))
    assert_equals(test_win_path, cygwin_path_to_win(test_cygwin_path))


@pytest.mark.slow
def test_activate_test1(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate{shell_suffix}" "{env_dirs[0]}"
        {printpath}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert_equals(stderr, u'prepending {envpaths} to PATH'\
                        .format(envpaths=pathlist_to_str(_envpaths(envs, 'test1'), False)), shell)
        assert_in(pathsep.join(_envpaths(envs, 'test1')), shells[shell]["path_from"](stdout), shell)


@pytest.mark.slow
def test_activate_env_from_env_with_root_activate(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{cmd_path}activate" "{env_dirs[1]}"
        {printpath}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert_equals(stderr, u'prepending {envpaths2} to PATH'\
            .format(envpaths2=pathlist_to_str(_envpaths(envs, 'test2'))))
        assert_in(shells[shell]["path_from"](pathsep.join(_envpaths(envs, 'test2'))),
                  stdout)


@pytest.mark.slow
def test_activate_bad_directory(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[2]}"
        {printpath}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert_not_in(shells[shell]["path_to"](_envpaths(envs, 'test3')[0]), stdout)
        assert_equals(stderr, u'Error: could not find environment: {envpaths3}'.format(envpaths3=_envpaths(envs, 'test3')[0]))


@pytest.mark.slow
def test_activate_bad_env_keeps_existing_good_env(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} {syspath}{cmd_path}activate "{env_dirs[0]}" {nul}
        {source} "{syspath}{cmd_path}activate" "{env_dirs[2]}"
        {printpath}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert_in(pathsep.join(_envpaths(envs, 'test1')),shells[shell]["path_from"](stdout))


@pytest.mark.slow
def test_activate_deactivate(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{cmd_path}deactivate"
        {printpath}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, u"%s" % shell_vars['base_path'])


@pytest.mark.slow
def test_activate_root(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" root
        {printpath}
        """).format(envs=envs, **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert_in(shells[shell]["path_to"](pathsep.join(_envpaths(root_dir))), stdout)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" root
        {source} "{syspath}{cmd_path}deactivate"
        {printpath}
        """).format(envs=envs, **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, u"%s" % shell_vars['base_path'], stderr)


def test_activate_root_env_from_other_env(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{cmd_path}activate" root
        {printpath}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert_in(shells[shell]["path_to"](pathsep.join(_envpaths(root_dir))),
                  stdout)
        assert_not_in(shells[shell]["path_to"](pathsep.join(_envpaths(envs, 'test1'))),
                      stdout)


@pytest.mark.slow
def test_wrong_args(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" two args
        {printpath}
        """).format(envs=envs, **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert_equals(stderr, u'Error: did not expect more than one argument.')
        assert_equals(stdout, shell_vars['base_path'], stderr)


@pytest.mark.slow
def test_activate_help(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        if not platform.startswith("win"):
            commands = (shell_vars['command_setup'] + """
            "{syspath}{cmd_path}activate" Zanzibar
            """).format(envs=envs, **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '')
            assert_in("activate must be sourced", stderr)
            assert_in("Usage: source activate ENV", stderr)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" --help
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
def test_activate_symlinking(shell):
    """Symlinks or bat file redirects are created at activation time.  Make sure that the
    files/links exist, and that they point where they should."""
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}"
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stderr, u'prepending {envpaths1} to PATH'\
                .format(syspath=pathlist_to_str(_envpaths(root_dir)),
                        envpaths1=pathlist_to_str(_envpaths(envs, 'test1'))))

        where = 'Scripts' if sys.platform == 'win32' else 'bin'
        for env in gen_test_env_paths(envs, shell)[:2]:
            scripts = {where: ["conda"],
                        'cmd': ["activate", "deactivate"],
            }
            for where, files in scripts.items():
                for f in files:
                    if sys.platform == "win32":
                        file_path = shells[shell]["slash_convert"][1].join([env, where, f + shells[shell]["shell_suffix"]])
                        # must translate path to windows representation for Python's sake
                        file_path = shells[shell]["path_from"](file_path)
                        assert(os.path.lexists(file_path))
                    else:
                        file_path = join(env, where, f)
                        assert(os.path.lexists(file_path))
                        s = os.lstat(file_path)
                        assert(stat.S_ISLNK(s.st_mode))
                        assert(os.readlink(file_path) == '{root_path}'.format(root_path=join(sys.prefix, where, f)))

        if platform != 'win':
            # Test activate when there are no write permissions in the
            # env.
            prefix_bin_path = join(gen_test_env_paths(envs, shell)[2], 'bin')
            commands = (shell_vars['command_setup'] + """
            mkdir -p {prefix_bin_path}
            chmod 000 {prefix_bin_path}
            {source} activate "{env_dirs[2]}"
            """).format(prefix_bin_path=prefix_bin_path, envs=envs,
                                env_dirs=gen_test_env_paths(envs, shell),
                **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_in("do not have write access", stderr)

            # restore permissions so the dir will get cleaned up
            run_in("chmod 777 {prefix_bin_path}".format(prefix_bin_path=prefix_bin_path), shell)


def test_PS1(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        # activate changes PS1 correctly
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}"
        {printps1}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, print_ps1(env_dirs=gen_test_env_paths(envs, shell), shell=shell, number=0), stderr)

        # second activate replaces earlier actived env PS1
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{cmd_path}activate" "{env_dirs[1]}"
        {printps1}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, sterr = run_in(commands, shell)
        assert_equals(stdout, print_ps1(env_dirs=gen_test_env_paths(envs, shell), shell=shell,number=1), stderr)

        # failed activate does not touch raw PS1
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[2]}"
        {printps1}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)

        # ensure that a failed activate does not touch PS1 (envs[3] folders do not exist.)
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{cmd_path}activate" "{env_dirs[2]}"
        {printps1}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, print_ps1(env_dirs=gen_test_env_paths(envs, shell), shell=shell,number=0), stderr)

        # deactivate doesn't do anything bad to PS1 when no env active to deactivate
        commands = (shell_vars['command_setup'] + """
        {source} {syspath}{cmd_path}deactivate
        {printps1}
        """).format(envs=envs, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)

        # deactivate script in activated env returns us to raw PS1
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}" {nul}
        {source} "{env_dirs[0]}{cmd_path}deactivate"
        {printps1}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)

        # make sure PS1 is unchanged by faulty activate input
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" two args
        {printps1}
        """).format(envs=envs, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)


@pytest.mark.slow
def test_PS1_no_changeps1(shell):
    """Ensure that people's PS1 remains unchanged if they have that setting in their RC file."""
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
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}"
        {printps1}
        """).format(condarc=join(envs, ".condarc"), envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)

        commands = (shell_vars['command_setup'] + condarc + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{cmd_path}activate" "{env_dirs[1]}"
        {printps1}
        """).format(condarc=join(envs, ".condarc"), envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)

        commands = (shell_vars['command_setup'] + condarc + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[2]}"
        {printps1}
        """).format(condarc=join(envs, ".condarc"), envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)

        commands = (shell_vars['command_setup'] + condarc + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{cmd_path}activate" "{env_dirs[2]}"
        {printps1}
        """).format(condarc=join(envs, ".condarc"), envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)

        commands = (shell_vars['command_setup'] + condarc + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}" {nul}
        {source} "{env_dirs[0]}{cmd_path}deactivate"
        {printps1}
        """).format(condarc=join(envs, ".condarc"), envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)

        commands = (shell_vars['command_setup'] + condarc + """
        {source} "{syspath}{cmd_path}activate" two args
        {printps1}
        """).format(condarc=join(envs, ".condarc"), envs=envs, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)


@pytest.mark.slow
def test_CONDA_DEFAULT_ENV(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}"
        {printdefaultenv}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, u'{env_dirs[0]}'.format(envs=envs, env_dirs=gen_test_env_paths(envs, shell)), stderr)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{cmd_path}activate" "{env_dirs[1]}"
        {printdefaultenv}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, u'{env_dirs[1]}'.format(env_dirs=gen_test_env_paths(envs, shell)), stderr)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[2]}"
        {printdefaultenv}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, '', stderr)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{cmd_path}activate" "{env_dirs[2]}"
        {printdefaultenv}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, '{env_dirs[0]}'.format(env_dirs=gen_test_env_paths(envs, shell)), stderr)

        commands = (shell_vars['command_setup'] + """
        {source} {syspath}{cmd_path}deactivate
        {printdefaultenv}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, '', stderr)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}" {nul}
        {source} "{env_dirs[0]}{cmd_path}deactivate"
        {printdefaultenv}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, '', stderr)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" two args
        {printdefaultenv}
        """).format(envs=envs, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, '', stderr)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" root {nul}
        {printdefaultenv}
        """).format(envs=envs, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, u"%s" % sys.prefix, stderr)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" root {nul}
        {source} "{env_dirs[0]}{cmd_path}deactivate" {nul}
        {printdefaultenv}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, '', stderr)

@pytest.mark.slow
def test_activate_from_env(shell):
    """Tests whether the activate bat file or link in the activated environment works OK"""
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}"
        {source} "{env_dirs[0]}{cmd_path}activate" "{env_dirs[1]}"
        {printdefaultenv}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, u'{env_dirs[1]}'.format(envs=envs, env_dirs=gen_test_env_paths(envs, shell)), stderr)


@pytest.mark.slow
def test_deactivate_from_env(shell):
    """Tests whether the deactivate bat file or link in the activated environment works OK"""
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}"
        {source} "{env_dirs[0]}{cmd_path}deactivate"
        {printdefaultenv}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, u'', stderr)


@pytest.mark.slow
def test_activate_relative_path(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        start_dir = os.getcwd()
        env_dirs = gen_test_env_paths(envs, shell)
        os.chdir(envs)
        env_dir = os.path.basename(env_dirs[0])
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dir}"
        {printdefaultenv}
        """).format(envs=envs, env_dir=env_dir, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        os.chdir(start_dir)
        assert_equals(stdout, u'{env_dirs[0]}'.format(envs=envs, env_dirs=env_dirs), stderr)


@pytest.mark.slow
def test_activate_does_not_leak_echo_setting(shell):
    """Test that activate's setting of echo to off does not disrupt later echo calls"""

    if sys.platform != "win32" or shell != "cmd.exe":
        pytest.skip("test only relevant for cmd.exe on win")
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        @echo on
        call "{syspath}{cmd_path}activate.bat" "{env_dirs[0]}"
        @echo
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, u'ECHO is on.', stderr)


@pytest.mark.slow
def test_activate_non_ascii_char_in_path(shell):
    if shell.lower() not in ["cmd.exe", "powershell"]:
        pytest.xfail("subprocess with python 2.7 is broken with unicode")
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='Ånvs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}"
        {source} "{env_dirs[0]}{cmd_path}deactivate"
        {printdefaultenv}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, u'', stderr)


@pytest.mark.slow
def test_activate_has_extra_env_vars(shell):
    """Test that environment variables in activate.d show up when activated"""
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        env_dirs=gen_test_env_paths(envs, shell)
        act_path = shells[shell]["path_from"](join(env_dirs[0], "etc", "conda", "activate.d"))
        deact_path = shells[shell]["path_from"](join(env_dirs[0], "etc", "conda", "deactivate.d"))
        os.makedirs(act_path)
        os.makedirs(deact_path)
        with open(join(act_path, "test" + shells[shell]["env_script_suffix"]), "w") as f:
            f.write(shells[shell]["set_var"] + "TEST_VAR=test\n")
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}"
        {echo} {var}
        """).format(envs=envs, env_dirs=env_dirs, var=shells[shell]["var_format"].format("TEST_VAR"), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, u'test', stderr)

        # Make sure the variable is reset after deactivation
        with open(join(deact_path, "test" + shells[shell]["env_script_suffix"]), "w") as f:
            f.write(shells[shell]["set_var"] + "TEST_VAR=\n")
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{cmd_path}activate" "{env_dirs[0]}"
        {source} "{env_dirs[0]}{cmd_path}deactivate"
        {echo} {var}
        """).format(envs=envs, env_dirs=env_dirs, var=shells[shell]["var_format"].format("TEST_VAR"), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, u'', stderr)
