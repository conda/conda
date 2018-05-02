# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

from datetime import datetime
import os
from os.path import dirname, join
import subprocess
import sys
import tempfile

import pytest

from conda import CONDA_PACKAGE_ROOT
from conda.base.constants import ROOT_ENV_NAME
from conda.base.context import context
from conda.cli.activate import _get_prefix_paths, binpath_from_arg
from conda.compat import TemporaryDirectory, chain
from conda.gateways.disk.create import mkdir_p
from conda.gateways.disk.update import touch
from conda.utils import on_win, shells, translate_stream, unix_path_to_win
from tests.helpers import assert_equals, assert_in, assert_not_in

# ENVS_PREFIX = "envs" if PY2 else "envsßôç"
ENVS_PREFIX = "envs"


def gen_test_env_paths(envs, shell, num_test_folders=5):
    """People need not use all the test folders listed here.
    This is only for shortening the environment string generation.

    Also encapsulates paths in double quotes.
    """
    paths = [os.path.join(envs, "test {}".format(test_folder+1)) for test_folder in range(num_test_folders)]
    for path in paths[:2]:
        # These tests assume only the first two paths can be activated
        # Create symlinks ONLY for the first two folders.
        # symlink_conda(path, sys.prefix, shell)
        mkdir_p(join(path, 'conda-meta'))
        touch(join(path, 'conda-meta', 'history'))
    converter = shells[shell]["path_to"]
    paths = [converter(path) for path in paths]
    return paths


def _envpaths(env_root, env_name="", shell=None):
    """Supply the appropriate platform executable folders.  rstrip on root removes
       trailing slash if env_name is empty (the default)

    Assumes that any prefix used here exists.  Will not work on prefixes that don't.
    """
    sep = shells[shell]['sep']
    return binpath_from_arg(sep.join([env_root, env_name]), shell)


PYTHONPATH = os.path.dirname(CONDA_PACKAGE_ROOT)


def make_win_ok(path):
    if on_win:
        return unix_path_to_win(path)
    else:
        return path


def print_ps1(env_dirs, raw_ps, number):
    if ')' in raw_ps:
        a, _, b = raw_ps.partition(') ')
        raw_ps = b or a
    return u"(%s) %s" % (make_win_ok(env_dirs[number]), raw_ps)


CONDA_ENTRY_POINT = """\
#!{syspath}/python
import sys
from conda.cli import main

sys.exit(main())
"""

def raw_string(s):
    if isinstance(s, str):
        s = s.encode('string-escape')
    elif isinstance(s, unicode):
        s = s.encode('unicode-escape')
    return s

def strip_leading_library_bin(path_string, shelldict):
    entries = path_string.split(shelldict['pathsep'])
    if "library{}bin".format(shelldict['sep']) in entries[0].lower():
        entries = entries[1:]
    return shelldict['pathsep'].join(entries)


def _format_vars(shell):
    shelldict = shells[shell]

    # base_path, _ = run_in(shelldict['printpath'], shell)
    # # windows forces Library/bin onto PATH when starting up.  Strip it for the purposes of this test.
    # if on_win:
    #     base_path = strip_leading_library_bin(base_path, shelldict)

    raw_ps, _ = run_in(shelldict["printps1"], shell)

    old_path_parts = os.environ['PATH'].split(os.pathsep)

    if on_win:
        new_path_parts = tuple(
            _get_prefix_paths(join(dirname(CONDA_PACKAGE_ROOT), 'conda', 'shell'))
        ) + tuple(
            _get_prefix_paths(sys.prefix)
        )
    else:
        new_path_parts = (
            join(dirname(CONDA_PACKAGE_ROOT), 'conda', 'shell', 'bin'),
            dirname(sys.executable),
        )

    if shell == 'bash.exe':
        from conda.activate import native_path_to_unix
        base_paths = tuple(p for p in chain.from_iterable((new_path_parts, old_path_parts)))
        base_path = ':'.join(native_path_to_unix(base_paths))

    else:
        base_path = shelldict['pathsep'].join(shelldict['path_to'](p)
                                              for p in chain.from_iterable((new_path_parts,
                                                                            old_path_parts)))
    if shell == 'cmd.exe':
        _command_setup = """\
{set} "PYTHONPATH={PYTHONPATH}"
{set} CONDARC=
{set} CONDA_PATH_BACKUP=
{set} "PATH={new_path}"
"""
    else:
        _command_setup = """\
{set} PYTHONPATH="{PYTHONPATH}"
{set} CONDARC=
{set} CONDA_PATH_BACKUP=
{set} PATH="{new_path}"
{set} _CONDA_ROOT="{shellpath}"
"""
        if 'bash' in shell:
            _command_setup += "set -u\n"

    command_setup = _command_setup.format(
        here=dirname(__file__),
        PYTHONPATH=shelldict['path_to'](PYTHONPATH),
        set=shelldict["set_var"],
        new_path=base_path,
        shellpath=join(dirname(CONDA_PACKAGE_ROOT), 'conda', 'shell')
    )
    if shelldict["shell_suffix"] == '.bat':
        command_setup = "@echo off\n" + command_setup

    return {
        'echo': shelldict['echo'],
        'nul': shelldict['nul'],
        'printpath': shelldict['printpath'],
        'printdefaultenv': shelldict['printdefaultenv'],
        'printps1': shelldict['printps1'],
        'raw_ps': raw_ps,
        'set_var': shelldict['set_var'],
        'source': shelldict['source_setup'],
        'binpath': shelldict['binpath'],
        'shell_suffix': shelldict['shell_suffix'],
        'syspath': join(dirname(CONDA_PACKAGE_ROOT), 'conda', 'shell'),
        'command_setup': command_setup,
        'base_path': base_path,
}


# @pytest.fixture(scope="module")
# def bash_profile(request):
#     # profile=os.path.join(os.path.expanduser("~"), ".bash_profile")
#     # if os.path.isfile(profile):
#     #     os.rename(profile, profile+"_backup")
#     # with open(profile, "w") as f:
#     #     f.write("export PS1=test_ps1\n")
#     #     f.write("export PROMPT=test_ps1\n")
#     # def fin():
#     #     if os.path.isfile(profile+"_backup"):
#     #         os.remove(profile)
#     #         os.rename(profile+"_backup", profile)
#     # request.addfinalizer(fin)
#     return request  # provide the fixture value


@pytest.mark.installed
def test_activate_test1(shell):
    if shell == 'bash.exe':
        pytest.skip("usage of cygpath in win_path_to_unix messes this test up")
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix=ENVS_PREFIX, dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate{shell_suffix}" "{env_dirs[0]}"
        {printpath}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert_in(shells[shell]['pathsep'].join(_envpaths(envs, 'test 1', shell)),
                 stdout, shell)


@pytest.mark.installed
def test_activate_env_from_env_with_root_activate(shell):
    if shell == 'bash.exe':
        pytest.skip("usage of cygpath in win_path_to_unix messes this test up")
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix=ENVS_PREFIX, dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{binpath}activate" "{env_dirs[1]}"
        {printpath}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert not stderr
        assert_in(shells[shell]['pathsep'].join(_envpaths(envs, 'test 2', shell)), stdout)


@pytest.mark.installed
def test_activate_bad_directory(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix=ENVS_PREFIX, dir=dirname(__file__)) as envs:
        env_dirs = gen_test_env_paths(envs, shell)
        # Strange semicolons are here to defeat MSYS' automatic path conversion.
        #   See http://www.mingw.org/wiki/Posix_path_conversion
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[3]}"
        {printpath}
        """).format(envs=envs, env_dirs=env_dirs, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        # another semicolon here for comparison reasons with one above.
        assert 'could not find conda environment' in stderr.lower() or 'not a conda environment' in stderr.lower()
        assert_not_in(env_dirs[3], stdout)


@pytest.mark.installed
def test_activate_bad_env_keeps_existing_good_env(shell):
    if shell == 'bash.exe':
        pytest.skip("usage of cygpath in win_path_to_unix messes this test up")
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix=ENVS_PREFIX, dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
        {source} "{syspath}{binpath}activate" "{env_dirs[3]}"
        {printpath}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert_in(shells[shell]['pathsep'].join(_envpaths(envs, 'test 1', shell)), stdout)


@pytest.mark.installed
def test_activate_deactivate(shell):
    if shell == 'bash.exe':
        pytest.skip("usage of cygpath in win_path_to_unix messes this test up")
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix=ENVS_PREFIX, dir=dirname(__file__)) as envs:

        # debug TODO: remove
        if shell == 'bash.exe':
            commands = (shell_vars['command_setup'] + """
            env | sort
            {source} "{syspath}{binpath}activate" "{env_dirs[0]}" {nul}
            env | sort
            set -x
            {source} "{syspath}{binpath}deactivate"
            env | sort
            {printpath}
            """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
            stdout, stderr = run_in(commands, shell)
            sys.stdout.write(stdout)
            sys.stderr.write(stderr)




        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{binpath}deactivate"
        {printpath}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert not stderr
        stdout = strip_leading_library_bin(stdout, shells[shell])
        assert_equals(stdout, u"%s" % shell_vars['base_path'])


@pytest.mark.installed
def test_activate_root_simple(shell):
    if shell == 'bash.exe':
        pytest.skip("usage of cygpath in win_path_to_unix messes this test up")
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix=ENVS_PREFIX, dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" root
        {printpath}
        """).format(envs=envs, **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert_in(shells[shell]['pathsep'].join(_envpaths(context.root_prefix, shell=shell)), stdout, stderr)
        assert not stderr

        # debug TODO: remove
        if shell == 'bash.exe':
            commands = (shell_vars['command_setup'] + """
            env | sort
            {source} "{syspath}{binpath}activate" root
            env | sort
            echo {source} "{syspath}{binpath}deactivate"
            {source} "{syspath}{binpath}deactivate"
            env | sort
            {printpath}
            """).format(envs=envs, **shell_vars)
            stdout, stderr = run_in(commands, shell)
            sys.stdout.write(stdout)
            sys.stderr.write(stderr)


        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" root
        {source} "{syspath}{binpath}deactivate"
        {printpath}
        """).format(envs=envs, **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert not stderr
        stdout = strip_leading_library_bin(stdout, shells[shell])
        assert_equals(stdout, u'%s' % shell_vars['base_path'])


@pytest.mark.installed
def test_wrong_args(shell):
    if shell == 'bash.exe':
        pytest.skip("usage of cygpath in win_path_to_unix messes this test up")
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix=ENVS_PREFIX, dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" two args
        {printpath}
        """).format(envs=envs, **shell_vars)

        stdout, stderr = run_in(commands, shell)
        stdout = strip_leading_library_bin(stdout, shells[shell])
        assert_in("activate does not accept more than one argument", stderr)
        assert_equals(stdout, shell_vars['base_path'], stderr)


@pytest.mark.installed
def test_PS1_changeps1(shell):  # , bash_profile
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix=ENVS_PREFIX, dir=dirname(__file__)) as envs:
        # activate changes PS1 correctly
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}"
        {printps1}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert not stderr
        assert_equals(stdout.strip(), print_ps1(env_dirs=gen_test_env_paths(envs, shell),
                                        raw_ps=shell_vars["raw_ps"], number=0).strip(), stderr)

        # second activate replaces earlier activated env PS1
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{binpath}activate" "{env_dirs[1]}"
        {printps1}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, sterr = run_in(commands, shell)
        assert_equals(stdout.strip(), print_ps1(env_dirs=gen_test_env_paths(envs, shell),
                                        raw_ps=shell_vars["raw_ps"], number=1).strip(), stderr)

        # failed activate does not touch raw PS1
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[2]}"
        {printps1}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)

        # ensure that a failed activate does not touch PS1 (envs[3] folders do not exist.)
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{binpath}activate" "{env_dirs[2]}"
        {printps1}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout.strip(), print_ps1(env_dirs=gen_test_env_paths(envs, shell),
                                        raw_ps=shell_vars["raw_ps"], number=0).strip(), stderr)

        # deactivate script in activated env returns us to raw PS1
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{binpath}deactivate"
        {printps1}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)

        # make sure PS1 is unchanged by faulty activate input
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" two args
        {printps1}
        """).format(envs=envs, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)

        # deactivate doesn't do anything bad to PS1 when no env active to deactivate
        commands = (shell_vars['command_setup'] + """
        {source} {syspath}{binpath}deactivate
        {printps1}
        """).format(envs=envs, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)


@pytest.mark.installed
def test_PS1_no_changeps1(shell):  # , bash_profile
    """Ensure that people's PS1 remains unchanged if they have that setting in their RC file."""
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix=ENVS_PREFIX, dir=dirname(__file__)) as envs:
        rc_file = os.path.join(envs, ".condarc")
        with open(rc_file, 'w') as f:
            f.write("changeps1: False\n")
        condarc = "{set_var}CONDARC=%s\n" % rc_file
        commands = (shell_vars['command_setup'] + condarc + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}"
        {printps1}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)

        commands = (shell_vars['command_setup'] + condarc + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{binpath}activate" "{env_dirs[1]}"
        {printps1}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)

        commands = (shell_vars['command_setup'] + condarc + """
        {source} "{syspath}{binpath}activate" "{env_dirs[2]}"
        {printps1}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)

        commands = (shell_vars['command_setup'] + condarc + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{binpath}activate" "{env_dirs[2]}"
        {printps1}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)

        commands = (shell_vars['command_setup'] + condarc + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{binpath}deactivate"
        {printps1}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)

        commands = (shell_vars['command_setup'] + condarc + """
        {source} "{syspath}{binpath}activate" two args
        {printps1}
        """).format(envs=envs, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)


@pytest.mark.installed
def test_CONDA_DEFAULT_ENV(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix=ENVS_PREFIX, dir=dirname(__file__)) as envs:
        env_dirs=gen_test_env_paths(envs, shell)
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}"
        {printdefaultenv}
        """).format(envs=envs, env_dirs=env_dirs, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout.rstrip(), make_win_ok(env_dirs[0]), stderr)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{binpath}activate" "{env_dirs[1]}"
        {printdefaultenv}
        """).format(envs=envs, env_dirs=env_dirs, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout.rstrip(), make_win_ok(env_dirs[1]), stderr)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[2]}"
        {printdefaultenv}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, '', stderr)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{binpath}activate" "{env_dirs[2]}"
        {printdefaultenv}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout.rstrip(), make_win_ok(env_dirs[0]), stderr)

        commands = (shell_vars['command_setup'] + """
        {source} {syspath}{binpath}deactivate
        {printdefaultenv}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, '', stderr)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{binpath}deactivate"
        {printdefaultenv}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, '', stderr)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" two args
        {printdefaultenv}
        """).format(envs=envs, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, '', stderr)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" root {nul}
        {printdefaultenv}
        """).format(envs=envs, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout.rstrip(), ROOT_ENV_NAME, stderr)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" root {nul}
        {source} "{syspath}{binpath}deactivate" {nul}
        {printdefaultenv}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, '', stderr)


@pytest.mark.installed
def test_activate_from_env(shell):
    """Tests whether the activate bat file or link in the activated environment works OK"""
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix=ENVS_PREFIX, dir=dirname(__file__)) as envs:
        env_dirs=gen_test_env_paths(envs, shell)
        commands = (shell_vars['command_setup'] + """
        {source} {syspath}{binpath}activate "{env_dirs[0]}"
        {source} activate "{env_dirs[1]}"
        {printdefaultenv}
        """).format(envs=envs, env_dirs=env_dirs, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert not stderr
        # rstrip on output is because the printing to console picks up an extra space
        assert_equals(stdout.rstrip(), make_win_ok(env_dirs[1]), stderr)


@pytest.mark.installed
def test_deactivate_from_env(shell):
    """Tests whether the deactivate bat file or link in the activated environment works OK"""
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix=ENVS_PREFIX, dir=dirname(__file__)) as envs:
        commands = shell_vars['command_setup']
        if 'ash' in shell:
            commands += "set +u\n"
        commands += """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}"
        {source} deactivate
        {printdefaultenv}
        """
        commands = (commands).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert not stderr
        assert_equals(stdout, u'', stderr)


# @pytest.mark.installed
# def test_activate_relative_path(shell):
#     """
#     current directory should be searched for environments
#     """
#     shell_vars = _format_vars(shell)
#     with TemporaryDirectory(prefix=ENVS_PREFIX, dir=dirname(__file__)) as envs:
#         env_dirs = gen_test_env_paths(envs, shell)
#         env_dir = os.path.basename(env_dirs[0])
#         work_dir = os.path.dirname(env_dir)
#         commands = (shell_vars['command_setup'] + """
#         cd {work_dir}
#         {source} "{syspath}{binpath}activate" "{env_dir}"
#         {printdefaultenv}
#         """).format(work_dir=envs, envs=envs, env_dir=env_dir, **shell_vars)
#         cwd = os.getcwd()
#         # this is not effective for running bash on windows.  It starts
#         #    in your home dir no matter what.  That's what the cd is for above.
#         os.chdir(envs)
#         try:
#             stdout, stderr = run_in(commands, shell, cwd=envs)
#         except:
#             raise
#         finally:
#             os.chdir(cwd)
#         assert not stderr
#         assert_equals(stdout.rstrip(), make_win_ok(env_dirs[0]), stderr)


@pytest.mark.installed
def test_activate_does_not_leak_echo_setting(shell):
    """Test that activate's setting of echo to off does not disrupt later echo calls"""
    if not on_win or shell != "cmd.exe":
        pytest.skip("test only relevant for cmd.exe on win")
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix=ENVS_PREFIX, dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        @echo on
        @call "{syspath}{binpath}activate.bat" "{env_dirs[0]}"
        @echo
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, u'ECHO is on.', stderr)


@pytest.mark.skipif(True, reason="save for later")
@pytest.mark.installed
def test_activate_non_ascii_char_in_path(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='Ånvs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}"
        {source} "{syspath}{binpath}deactivate"
        {printdefaultenv}.
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert not stderr

        if shell == 'cmd.exe':
            assert_equals(stdout, u'', stderr)
        else:
            assert_equals(stdout, u'.', stderr)


@pytest.mark.installed
def test_activate_has_extra_env_vars(shell):
    """Test that environment variables in activate.d show up when activated"""
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix=ENVS_PREFIX, dir=dirname(__file__)) as envs:
        env_dirs=gen_test_env_paths(envs, shell)
        for path in ["activate", "deactivate"]:
            dir = os.path.join(shells[shell]['path_from'](env_dirs[0]), "etc", "conda", "%s.d" % path)
            os.makedirs(dir)
            file = os.path.join(dir, "test" + shells[shell]["env_script_suffix"])
            setting = "test" if path == "activate" else ""
            with open(file, 'w') as f:
                f.write(shells[shell]["set_var"] + "TEST_VAR=%s\n" % setting)
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}"
        {echo} {var}
        """).format(envs=envs, env_dirs=env_dirs, var=shells[shell]["var_format"].format("TEST_VAR"), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert not stderr
        assert_equals(stdout, u'test', stderr)

        # Make sure the variable is reset after deactivation

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}"
        {source} "{syspath}{binpath}deactivate"
        {echo} {var}.
        """).format(envs=envs, env_dirs=env_dirs, var=shells[shell]["var_format"].format("TEST_VAR"), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        # period here is because when var is blank, windows prints out the current echo setting.
        assert_equals(stdout, u'.', stderr)


# This test depends on files that are copied/linked in the conda recipe.  It is unfortunately not going to run after
#    a setup.py install step
# @pytest.mark.slow
# def test_activate_from_exec_folder(shell):
#     """The exec folder contains only the activate and conda commands.  It is for users
#     who want to avoid conda packages shadowing system ones."""
#     shell_vars = _format_vars(shell)
#     with TemporaryDirectory(prefix=ENVS_PREFIX, dir=dirname(__file__)) as envs:
#         env_dirs=gen_test_env_paths(envs, shell)
#         commands = (shell_vars['command_setup'] + """
#         {source} "{syspath}/exec/activate" "{env_dirs[0]}"
#         {echo} {var}
#         """).format(envs=envs, env_dirs=env_dirs, var=shells[shell]["var_format"].format("TEST_VAR"), **shell_vars)
#         stdout, stderr = run_in(commands, shell)
#         assert_equals(stdout, u'test', stderr)


def run_in(command, shell, cwd=None, env=None):
    if hasattr(shell, "keys"):
        shell = shell["exe"]
    if shell == 'cmd.exe':
        cmd_script = tempfile.NamedTemporaryFile(suffix='.bat', mode='wt', delete=False)
        cmd_script.write(command)
        cmd_script.close()
        cmd_bits = [shells[shell]["exe"]] + shells[shell]["shell_args"] + [cmd_script.name]
        try:
            print(cmd_bits)
            print(command)
            p = subprocess.Popen(cmd_bits, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 cwd=cwd, env=env)
            stdout, stderr = p.communicate()
        finally:
            os.unlink(cmd_script.name)
    elif shell == 'powershell':
        raise NotImplementedError
    else:
        cmd_bits = ([shells[shell]["exe"]] + shells[shell]["shell_args"] +
                    [translate_stream(command, shells[shell]["path_to"])])
        print(cmd_bits)
        p = subprocess.Popen(cmd_bits, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
    streams = [u"%s" % stream.decode('utf-8').replace('\r\n', '\n').rstrip("\n")
               for stream in (stdout, stderr)]
    return streams
