# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, unicode_literals

import subprocess
import tempfile

import os
import stat
import sys
from textwrap import dedent
import re

from datetime import datetime
import pytest

from conda.compat import TemporaryDirectory
from conda.config import root_dir, platform
from conda.install import symlink_conda
from conda.utils import path_identity, shells, on_win, translate_stream
from conda.cli.activate import binpath_from_arg

from tests.helpers import assert_equals, assert_in, assert_not_in


def gen_test_env_paths(envs, shell, num_test_folders=5):
    """People need not use all the test folders listed here.
    This is only for shortening the environment string generation.

    Also encapsulates paths in double quotes.
    """
    paths = [os.path.join(envs, "test {}".format(test_folder+1)) for test_folder in range(num_test_folders)]
    for path in paths[:2]:      # Create symlinks ONLY for the first two folders.
        symlink_conda(path, sys.prefix, shell)
    converter = shells[shell]["path_to"]
    paths = {i:converter(path) for i, path in enumerate(paths)}
    paths["root"]="root"
    paths["bad"]="foo bar baz qux"
    envname = {k:shells[shell]["var_set"].format(variable="CONDA_ENVNAME",value=path) for k,path in paths.items()}
    return (paths, envname)


def _envpaths(env_root, env_name="", shelldict={}):
    """Supply the appropriate platform executable folders.  rstrip on root removes
       trailing slash if env_name is empty (the default)

    Assumes that any prefix used here exists.  Will not work on prefixes that don't.
    """
    sep = shelldict['sep']
    return binpath_from_arg(sep.join([env_root, env_name]), shelldict=shelldict)


def print_ps1(env_dirs, base_prompt, number):
    return u"({}) {}".format(env_dirs[number],base_prompt)


def raw_string(s):
    if isinstance(s, str):
        s = s.encode('string-escape')
    elif isinstance(s, unicode):
        s = s.encode('unicode-escape')
    return s


def strip_leading_library_bin(path_string, shelldict):
    entries = path_string.split(shelldict['path_delim'])
    if "library{}bin".format(shelldict['sep']) in entries[0].lower():
        entries = entries[1:]
    return shelldict['path_delim'].join(entries)


def _format_vars(shell):
    shelldict = shells[shell]

    base_path, _ = run_in(shelldict['path_print'], shell)
    # windows forces Library/bin onto PATH when starting up. Strip it for the purposes of this test.
    if on_win:
        base_path = strip_leading_library_bin(base_path, shelldict)

    # base_prompt, _ = run_in(shelldict["prompt_print"], shell)
    base_prompt = "test_prompt"

    syspath = shelldict['path_to'](sys.prefix)
    binpath = shelldict['path_to'](shelldict['binpath'])

    setenv_pythonpath=shelldict["envvar_set"].format(
        variable="PYTHONPATH",
        value=shelldict['path_to'](os.path.dirname(os.path.dirname(__file__))))
    # remove any conda RC references
    unsetenv_condarc=shelldict["envvar_unset"].format(
        variable="CONDARC")
    # clear any preset conda environment
    unsetenv_condadefaultenv=shelldict["envvar_unset"].format(
        variable="CONDA_DEFAULT_ENV")
    flags_verbose="{flag_single}v".format(**shelldict)
    flags_help="{flag_single}h".format(**shelldict)
    # set prompt such that we have a prompt to play
    # around and test with since most of the below
    # tests will not be invoked in an interactive
    # login shell and hence wont have the prompt initialized
    #
    # setting this here also means that we no longer have to
    # mess with the .bash_profile during testing to
    # standardize the base prompt
    prompt_set=shelldict["prompt_set"].format(
        value=base_prompt)
    command_setup = dedent("""\
        {setenv_pythonpath}
        {unsetenv_condarc}
        {unsetenv_condadefaultenv}
        {prompt_set}
        """).format(setenv_pythonpath=setenv_pythonpath,
                    unsetenv_condarc=unsetenv_condarc,
                    unsetenv_condadefaultenv=unsetenv_condadefaultenv,
                    prompt_set=prompt_set)

    if shelldict["suffix_script"] == '.bat':
        command_setup = "@ECHO OFF\n" + command_setup

    shelldict.update({
        'base_prompt':      base_prompt,
        'syspath':          syspath,
        'binpath':          binpath,
        'command_setup':    command_setup,
        'base_path':        base_path,
        'flags_verbose':    flags_verbose,
        'flags_help':       flags_help,
    })

    return shelldict


@pytest.mark.installed
def test_activate_test1(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {}
                {{path_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}"
                {{path_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_in(shell_vars['path_delim'].join(_envpaths(envs, 'test 1', shelldict=shell_vars)),
                stdout, shell)
            assert_equals(stderr,'')


@pytest.mark.installed
def test_activate_noleftoverargs(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        # get env results before any changes
        commands = shell_vars['command_setup'] + dedent("""\
            {envvar_getall}
            """).format(
                **shell_vars)
        stdout_init, _ = run_in(commands, shell)
        stdout_init = set(s.split("=")[0] for s in stdout_init.split("\n"))

        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {}
                {{envvar_getall}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}"
                {{envvar_getall}}
                """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)
            stdout = set(s.split("=")[0] for s in stdout.split("\n"))
            stdout_diff = list(stdout - stdout_init)
            stdout_diff = [s for s in stdout_diff if not s.startswith("_")]

            print("commands:",commands)
            print("stdout_init:","\n".join(stdout_init))
            print("stdout:","\n".join(stdout))
            print("stdout_diff:","\n".join(stdout_diff))
            print("stderr:",stderr)

            # since this is the activate process we expect 3/4 new variables
            # since other variable's value may be updated we do not check for that
            if shell.endswith(".msys"):
                # CONDA_PREFIX,CONDA_PS1_BACKUP,CONDA_DEFAULT_ENV,MSYS2_ENV_CONV_EXCL
                assert len(stdout_diff) == 4
            else:
                # CONDA_PREFIX,CONDA_PS1_BACKUP,CONDA_DEFAULT_ENV
                assert len(stdout_diff) == 3
            assert "CONDA_PS1_BACKUP" in stdout_diff
            assert "CONDA_DEFAULT_ENV" in stdout_diff
            assert "CONDA_PREFIX" in stdout_diff
            assert_equals(stderr,'')


@pytest.mark.installed
def test_deactivate_noleftoverargs(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        # get env results before any changes
        commands = shell_vars['command_setup'] + dedent("""\
            {envvar_getall}
            """).format(
                **shell_vars)
        stdout_init, _ = run_in(commands, shell)
        stdout_init = set(stdout_init.split("\n"))

        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_deactivate = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}deactivate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {}
                {}
                {{envvar_getall}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}"
                {}
                {{envvar_getall}}
                """)]

        for script in scripts:
            script = script.format(src_activate,src_deactivate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)
            stdout = set(stdout.split("\n"))
            stdout_diff = list(stdout - stdout_init)
            stdout_diff = [s for s in stdout_diff if not s.startswith("_")]

            print("commands:",commands)
            print("stdout_init:","\n".join(stdout_init))
            print("stdout:","\n".join(stdout))
            print("stdout_diff:","\n".join(stdout_diff))
            print("stderr:",stderr)

            # since this is the deactivate process we expect absolutely no differences
            # from the original environment, this includes the actual values of the
            # variables as well
            assert len(stdout_diff) == 0
            assert_equals(stderr,'')


@pytest.mark.installed
def test_activate_env_from_env_with_root_activate(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_activate_0 = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {} {{nul}}
                {{env_vars[1]}}
                {}
                {{path_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}" {{nul}}
                {} "{{env_dirs[1]}}"
                {{path_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate,src_activate_0)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:", commands)
            print("stdout:", stdout)
            print("stderr:", stderr)

            assert_in(shell_vars['path_delim'].join(_envpaths(envs, 'test 2', shelldict=shell_vars)),
                stdout, shell)
            assert_equals(stderr,'')


@pytest.mark.installed
def test_activate_bad_directory(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        # Strange semicolons are here to defeat MSYS' automatic path conversion.
        # See http://www.mingw.org/wiki/Posix_path_conversion
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[2]}}
                {}
                {{path_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[2]}}"
                {{path_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            # another semicolon here for comparison reasons with one above.
            assert_in('could not find environment',stderr,shell)
            assert_not_in(env_dirs[2], stdout, shell)


@pytest.mark.installed
def test_activate_bad_env_keeps_existing_good_env(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_activate_0 = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {} {{nul}}
                {{env_vars[2]}}
                {}
                {{path_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}" {{nul}}
                {} "{{env_dirs[2]}}"
                {{path_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate,src_activate_0)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_in(shell_vars['path_delim'].join(_envpaths(envs, 'test 1', shelldict=shell_vars)),
                stdout, shell)
            assert_in("Could not find environment",stderr)


@pytest.mark.installed
def test_activate_deactivate(shell):
    if shell == "bash.exe" and datetime.now() < datetime(2017, 3, 1):
        pytest.xfail("fix this soon")
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_deactivate = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}deactivate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {} {{nul}}
                {}
                {{path_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}" {{nul}}
                {}
                {{path_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate,src_deactivate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)
            stdout = strip_leading_library_bin(stdout, shell_vars)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, u"%s" % shell_vars['base_path'], stderr)
            assert_equals(stderr,'')


@pytest.mark.installed
def test_activate_root_simple(shell):
    if shell == "bash.exe" and datetime.now() < datetime(2017, 3, 1):
        pytest.xfail("fix this soon")
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[root]}}
                {}
                {{path_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[root]}}"
                {{path_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_in(shell_vars['path_delim'].join(_envpaths(root_dir, shelldict=shell_vars)),
                stdout, shell)
            assert_equals(stderr,'')


@pytest.mark.installed
def test_activate_deactivate_root(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_deactivate = shell_vars['source'].format(
            "{syspath}{binpath}deactivate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[root]}}
                {}
                {}
                {{path_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[root]}}"
                {}
                {{path_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate,src_deactivate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)
            stdout = strip_leading_library_bin(stdout, shell_vars)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, u"%s" % shell_vars['base_path'], stderr)
            assert_equals(stderr,'')


@pytest.mark.installed
def test_activate_root_env_from_other_env(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_activate_0 = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {} {{nul}}
                {{env_vars[root]}}
                {}
                {{path_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}" {{nul}}
                {} "{{env_dirs[root]}}"
                {{path_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate,src_activate_0)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_in(shell_vars['path_delim'].join(_envpaths(root_dir, shelldict=shell_vars)),
                stdout, shell)
            assert_not_in(shell_vars['path_delim'].join(_envpaths(envs, 'test 1', shelldict=shell_vars)),
                stdout, shell)
            assert_equals(stderr,'')


@pytest.mark.installed
def test_wrong_args(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        # cannot accidentally pass too many args to program when setting environment variables
        scripts += []
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
            {} two args
            {{path_print}}
            """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)
            stdout = strip_leading_library_bin(stdout, shell_vars)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, u"%s" % shell_vars['base_path'], stderr)
            assert_in("[ACTIVATE]: ERROR: Unknown/Invalid flag/parameter (args)",
                stderr, shell)


@pytest.mark.installed
def test_activate_check_sourcing(shell):
    if shell in ['powershell.exe', 'cmd.exe']:
        pytest.skip("the concept of sourcing to modify one's current environment is only applicable for UNIX")

    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        scripts = []
        src_activate = "{syspath}{binpath}activate{suffix_executable}"

        # all unix shells support environment variables instead of parameter passing
        scripts += [dedent("""\
            {{env_vars[0]}}
            {}
            """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}"
                """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, '', stderr)
            assert_in(dedent("""\
                [ACTIVATE]: ERROR: Only supports sourcing from tcsh/csh and bash/zsh/dash/posh/ksh."""),
                stderr, shell)


@pytest.mark.installed
def test_activate_help(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{help_var}}
                {}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} {{flags_help}}
                """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                help_var=shell_vars["var_set"].format(variable="CONDA_HELP",value="true"),
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, '', stderr)
            if shell in ["cmd.exe"]:
                assert_in('Usage: activate [ENV] [/h] [/v]', stderr, shell)
            elif shell in ["powershell.exe"]:
                assert_in('Usage: activate [ENV] [-h] [-v]', stderr, shell)
            elif shell in ["csh","tcsh"]:
                assert_in('Usage: source "`which activate`" [ENV] [-h] [-v]', stderr, shell)
            else:
                assert_in('Usage: . activate [ENV] [-h] [-v]', stderr, shell)


@pytest.mark.installed
def test_deactivate_check_sourcing(shell):
    if shell in ['powershell.exe', 'cmd.exe']:
        pytest.skip("the concept of sourcing to modify one's current environment is only applicable for UNIX")

    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        scripts = []
        src_deactivate = "{syspath}{binpath}deactivate{suffix_executable}"

        # since this is just the deactivate then no special testing is necessary
        # for environment variables vs. parameter passing
        scripts += [dedent("""\
            {}
            """)]

        for script in scripts:
            script = script.format(src_deactivate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, '', stderr)
            assert_in(dedent("""\
                [DEACTIVATE]: ERROR: Only supports sourcing from tcsh/csh and bash/zsh/dash/posh/ksh."""),
                stderr, shell)


@pytest.mark.installed
def test_deactivate_help(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        scripts = []
        src_deactivate = shell_vars['source'].format(
            "{syspath}{binpath}deactivate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{help_var}}
                {}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} {{flags_help}}
                """)]

        for script in scripts:
            script = script.format(src_deactivate)
            script = script.format(
                help_var=shell_vars["var_set"].format(variable="CONDA_HELP",value="true"),
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, '', stderr)
            if shell in ["cmd.exe"]:
                assert_in('Usage: deactivate [/h] [/v]', stderr, shell)
            elif shell in ["powershell"]:
                assert_in('Usage: deactivate [-h] [-v]', stderr, shell)
            elif shell in ["csh","tcsh"]:
                assert_in('Usage: source "`which deactivate`" [-h] [-v]', stderr, shell)
            else:
                assert_in('Usage: . deactivate [-h] [-v]', stderr, shell)


@pytest.mark.installed
def test_activate_symlinking(shell):
    """Symlinks or bat file redirects are created at activation time.  Make sure that the
    files/links exist, and that they point where they should."""
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        for k in [0,1]:
            for f in ["conda", "activate", "deactivate"]:
                file_path = "{env_dir}{binpath}{f}{suffix_executable}".format(
                    env_dir=env_dirs[k],
                    f=f,
                    **shell_vars)

                if on_win:
                    # must translate path to windows representation for Python's sake
                    file_path = shell_vars["path_from"](file_path)

                    print("on_win:")
                    print("file_path:",file_path)

                    assert(os.path.lexists(file_path))
                else:
                    real_path = "{syspath}{binpath}{f}{suffix_executable}".format(
                        f=f,
                        **shell_vars)

                    print("not on_win:")
                    print("file_path:",file_path)
                    print("real_path:",real_path)

                    assert(os.path.lexists(file_path))
                    assert(stat.S_ISLNK(os.lstat(file_path).st_mode))
                    assert(os.readlink(file_path) == real_path)

        if not on_win:
            # test activate when there are no write permissions in the env

            scripts = []
            src_activate = shell_vars['source'].format(
                "{syspath}{binpath}activate{suffix_executable}")

            # all unix shells support environment variables instead of parameter passing
            scripts += [dedent("""\
                mkdir -p  "{{env_dirs[2]}}{{binpath}}"
                chmod 444 "{{env_dirs[2]}}{{binpath}}"
                {{env_vars[2]}}
                {}
                """)]
            # most unix shells support parameter passing, dash is the exception
            if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
                scripts += [dedent("""\
                    mkdir -p  "{{env_dirs[2]}}{{binpath}}"
                    chmod 444 "{{env_dirs[2]}}{{binpath}}"
                    {} "{{env_dirs[2]}}"
                    """)]

            for script in scripts:
                script = script.format(src_activate)
                script = script.format(
                    env_vars=env_vars,
                    env_dirs=env_dirs,
                    **shell_vars)

                commands = shell_vars['command_setup'] + script
                stdout, stderr = run_in(commands, shell)

                print("commands:",commands)
                print("stdout:",stdout)
                print("stderr:",stderr)

                assert_equals(stdout,'')
                assert_in("not have write access", stderr, shell)

            # restore permissions so the dir will get cleaned up
            commands = dedent("""\
                chmod 777 "{env_dirs[2]}{binpath}"
                """).format(
                    env_vars=env_vars,
                    env_dirs=env_dirs,
                    **shell_vars)
            run_in(commands, shell)


@pytest.mark.installed
def test_PS1(shell):
    if shell in ['powershell.exe']:
        pytest.skip("powershell.exe doesn't support prompt modifications yet")

    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        #-----------------------------------------------------------------------
        # TEST 1: activate changes PS1 correctly
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {}
                {{prompt_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}"
                {{prompt_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, print_ps1(env_dirs=env_dirs,
                                            base_prompt=shell_vars["base_prompt"],
                                            number=0), stderr)
            assert_equals(stderr,'')

        #-----------------------------------------------------------------------
        # TEST 2: second activate replaces earlier activated env PS1
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_activate_0 = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {} {{nul}}
                {{env_vars[1]}}
                {}
                {{prompt_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}" {{nul}}
                {} "{{env_dirs[1]}}"
                {{prompt_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate,src_activate_0)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, sterr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, print_ps1(env_dirs=env_dirs,
                                            base_prompt=shell_vars["base_prompt"],
                                            number=1), stderr)
            assert_equals(stderr,'')

        #-----------------------------------------------------------------------
        # TEST 3: failed activate does not touch raw PS1
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[2]}}
                {}
                {{prompt_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[2]}}"
                {{prompt_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, shell_vars['base_prompt'], stderr)
            assert_in("Could not find environment",stderr)

        #-----------------------------------------------------------------------
        # TEST 4: ensure that a failed activate does not touch PS1
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_activate_0 = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {} {{nul}}
                {{env_vars[2]}}
                {}
                {{prompt_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}" {{nul}}
                {} "{{env_dirs[2]}}"
                {{prompt_print}}
                """)]

        if script in scripts:
            script = script.format(src_activate,src_activate_0)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, print_ps1(env_dirs=env_dirs,
                                            base_prompt=shell_vars["base_prompt"],
                                            number=0), stderr)
            assert_equals(stderr,'')

        #-----------------------------------------------------------------------
        # TEST 5: deactivate doesn't do anything bad to PS1 when no env active to deactivate
        #-----------------------------------------------------------------------
        scripts = []
        src_deactivate = shell_vars['source'].format(
            "{syspath}{binpath}deactivate{suffix_executable}")

        # since this is just the deactivate then no special testing is necessary
        # for environment variables vs. parameter passing
        scripts += [dedent("""\
            {}
            {{prompt_print}}
            """)]

        for script in scripts:
            script = script.format(src_deactivate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, shell_vars['base_prompt'], stderr)
            assert_equals(stderr,'')

        #-----------------------------------------------------------------------
        # TEST 6: deactivate script in activated env returns us to raw PS1
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_deactivate = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}deactivate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {} {{nul}}
                {}
                {{prompt_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}" {{nul}}
                {}
                {{prompt_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate,src_deactivate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, shell_vars['base_prompt'], stderr)
            assert_equals(stderr,'')

        #-----------------------------------------------------------------------
        # TEST 7: make sure PS1 is unchanged by faulty activate input
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        # cannot accidentally pass too many args to program when setting environment variables
        scripts += []
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} two args
                {{prompt_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, shell_vars['base_prompt'], stderr)
            assert_in('[ACTIVATE]: ERROR: Unknown/invalid flag/parameter',stderr)


@pytest.mark.installed
def test_PS1_no_changeps1(shell):
    """Ensure that people's PS1 remains unchanged if they have that setting in their RC file."""
    if shell in ['powershell.exe']:
        pytest.skip("powershell.exe doesn't support prompt modifications yet")

    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        rc_file = os.path.join(envs, ".condarc")
        with open(rc_file, 'w') as f:
            f.write("changeps1: False\n")
        setenv_condarc = shell_vars["envvar_set"].format(
            variable="CONDARC",
            value=rc_file)

        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        #-----------------------------------------------------------------------
        # TEST 1: activate changes PS1 correctly
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{setenv_condarc}}
                {{env_vars[0]}}
                {}
                {{prompt_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {{setenv_condarc}}
                {} "{{env_dirs[0]}}"
                {{prompt_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                setenv_condarc=setenv_condarc,
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, shell_vars["base_prompt"], stderr)
            assert_equals(stderr,'')

        #-----------------------------------------------------------------------
        # TEST 2: second activate replaces earlier activated env PS1
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_activate_0 = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{setenv_condarc}}
                {{env_vars[0]}}
                {} {{nul}}
                {{env_vars[1]}}
                {}
                {{prompt_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {{setenv_condarc}}
                {} "{{env_dirs[0]}}" {{nul}}
                {} "{{env_dirs[1]}}"
                {{prompt_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate,src_activate_0)
            script = script.format(
                setenv_condarc=setenv_condarc,
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, sterr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, shell_vars["base_prompt"], stderr)
            assert_equals(stderr,'')

        #-----------------------------------------------------------------------
        # TEST 3: failed activate does not touch raw PS1
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{setenv_condarc}}
                {{env_vars[2]}}
                {}
                {{prompt_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {{setenv_condarc}}
                {} "{{env_dirs[2]}}"
                {{prompt_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                setenv_condarc=setenv_condarc,
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, shell_vars["base_prompt"], stderr)
            assert_in("Could not find environment",stderr)

        #-----------------------------------------------------------------------
        # TEST 4: ensure that a failed activate does not touch PS1
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_activate_0 = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{setenv_condarc}}
                {{env_vars[0]}}
                {} {{nul}}
                {{env_vars[2]}}
                {}
                {{prompt_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {{setenv_condarc}}
                {} "{{env_dirs[0]}}" {{nul}}
                {} "{{env_dirs[2]}}"
                {{prompt_print}}
                """)]

        if script in scripts:
            script = script.format(src_activate,src_activate_0)
            script = script.format(
                setenv_condarc=setenv_condarc,
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, shell_vars["base_prompt"], stderr)
            assert_equals(stderr,'')

        #-----------------------------------------------------------------------
        # TEST 5: deactivate doesn't do anything bad to PS1 when no env active to deactivate
        #-----------------------------------------------------------------------
        scripts = []
        src_deactivate = shell_vars['source'].format(
            "{syspath}{binpath}deactivate{suffix_executable}")

        # since this is just the deactivate then no special testing is necessary
        # for environment variables vs. parameter passing
        scripts += [dedent("""\
            {{setenv_condarc}}
            {}
            {{prompt_print}}
            """)]

        for script in scripts:
            script = script.format(src_deactivate)
            script = script.format(
                setenv_condarc=setenv_condarc,
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, shell_vars["base_prompt"], stderr)
            assert_equals(stderr,'')

        #-----------------------------------------------------------------------
        # TEST 6: deactivate script in activated env returns us to raw PS1
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_deactivate = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}deactivate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{setenv_condarc}}
                {{env_vars[0]}}
                {} {{nul}}
                {}
                {{prompt_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {{setenv_condarc}}
                {} "{{env_dirs[0]}}" {{nul}}
                {}
                {{prompt_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate,src_deactivate)
            script = script.format(
                setenv_condarc=setenv_condarc,
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, shell_vars['base_prompt'], stderr)
            assert_equals(stderr,'')

        #-----------------------------------------------------------------------
        # TEST 7: make sure PS1 is unchanged by faulty activate input
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        # cannot accidentally pass too many args to program when setting environment variables
        scripts += []
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {{setenv_condarc}}
                {} two args
                {{prompt_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                setenv_condarc=setenv_condarc,
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, shell_vars["base_prompt"], stderr)
            assert_in('[ACTIVATE]: ERROR: Unknown/invalid flag/parameter',stderr)


@pytest.mark.installed
def test_CONDA_DEFAULT_ENV(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        #-----------------------------------------------------------------------
        # TEST 1: activate sets CONDA_DEFAULT_ENV correctly
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {}
                {{defaultenv_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}"
                {{defaultenv_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout.rstrip(), env_dirs[0], stderr)
            assert_equals(stderr,'')

        #-----------------------------------------------------------------------
        # TEST 2: second activate replaces earlier activated env CONDA_DEFAULT_ENV
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_activate_0 = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {} {{nul}}
                {{env_vars[1]}}
                {}
                {{defaultenv_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}" {{nul}}
                {} "{{env_dirs[1]}}"
                {{defaultenv_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate,src_activate_0)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout.rstrip(), env_dirs[1], stderr)
            assert_equals(stderr,'')

        #-----------------------------------------------------------------------
        # TEST 3: failed activate does not set CONDA_DEFAULT_ENV
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[2]}}
                {}
                {{defaultenv_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[2]}}"
                {{defaultenv_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, '', stderr)
            assert_in("Could not find environment",stderr)

        #-----------------------------------------------------------------------
        # TEST 4: ensure that a failed activate does not overwrite CONDA_DEFAULT_ENV
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_activate_0 = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {} {{nul}}
                {{env_vars[2]}}
                {}
                {{defaultenv_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}" {{nul}}
                {} "{{env_dirs[2]}}"
                {{defaultenv_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate,src_activate_0)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout.rstrip(), env_dirs[0], stderr)
            assert_in("Could not find environment",stderr)

        #-----------------------------------------------------------------------
        # TEST 5: deactivate doesn't set CONDA_DEFAULT_ENV when no env active to deactivate
        #-----------------------------------------------------------------------
        scripts = []
        src_deactivate = shell_vars['source'].format(
            "{syspath}{binpath}deactivate{suffix_executable}")

        # since this is just the deactivate then no special testing is necessary
        # for environment variables vs. parameter passing
        scripts += [dedent("""\
            {}
            {{envvar_getall}}
            """)]

        for script in scripts:
            script = script.format(src_deactivate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)
            stdout = [s.split("=")[0] for s in stdout.split("\n")]

            print("commands:",commands)
            print("stdout:","\n".join(stdout))
            print("stderr:",stderr)

            assert "CONDA_DEFAULT_ENV" not in stdout, "{} cannot find CONDA_DEFAULT_ENV in environment".format(stderr)
            assert_equals(stderr,'')

        #-----------------------------------------------------------------------
        # TEST 6: deactivate script in activated env unsets CONDA_DEFAULT_ENV
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_deactivate = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}deactivate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {} {{nul}}
                {}
                {{envvar_getall}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} {{nul}}
                {}
                {{envvar_getall}}
                """)]

        for script in scripts:
            script = script.format(src_activate,src_deactivate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)
            stdout = [s.split("=")[0] for s in stdout.split("\n")]

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert "CONDA_DEFAULT_ENV" not in stdout, "{} cannot find CONDA_DEFAULT_ENV in environment".format(stderr)
            assert_equals(stderr,'')

        #-----------------------------------------------------------------------
        # TEST 7: make sure CONDA_DEFAULT_ENV is not set by faulty activate input
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        # cannot accidentally pass too many args to program when setting environment variables
        scripts += []
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} two args
                {{defaultenv_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, '', stderr)
            assert_in('[ACTIVATE]: ERROR: Unknown/invalid flag/parameter',stderr)

        #-----------------------------------------------------------------------
        # TEST 8: activating root sets CONDA_DEFAULT_ENV correctly
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[root]}}
                {} {{nul}}
                {{defaultenv_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[root]}}" {{nul}}
                {{defaultenv_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout.rstrip(), 'root', stderr)
            assert_equals(stderr,'')

        #-----------------------------------------------------------------------
        # TEST 9: activating and deactivating from root unsets CONDA_DEFAULT_ENV correctly
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_deactivate = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}deactivate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[root]}}
                {} {{nul}}
                {} {{nul}}
                {{envvar_getall}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[root]}}" {{nul}}
                {} {{nul}}
                {{envvar_getall}}
                """)]

        for script in scripts:
            script = script.format(src_activate,src_deactivate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)
            stdout = [s.split("=")[0] for s in stdout.split("\n")]

            print("commands:",commands)
            print("stdout:","\n".join(stdout))
            print("stderr:",stderr)

            assert "CONDA_DEFAULT_ENV" not in stdout, "{} cannot find CONDA_DEFAULT_ENV in environment".format(stderr)
            assert_equals(stderr,'')


@pytest.mark.installed
def test_activate_from_env(shell):
    """Tests whether the activate bat file or link in the activated environment works OK"""
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_activate_0 = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {}
                {{env_vars[1]}}
                {}
                {{defaultenv_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}"
                {} "{{env_dirs[1]}}"
                {{defaultenv_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate,src_activate_0)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            # rstrip on output is because the printing to console picks up an extra space
            assert_equals(stdout.rstrip(), env_dirs[1], stderr)
            assert_equals(stderr,'')


@pytest.mark.installed
def test_deactivate_from_env(shell):
    """Tests whether the deactivate bat file or link in the activated environment works OK"""
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_deactivate = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}deactivate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {}
                {}
                {{envvar_getall}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}"
                {}
                {{envvar_getall}}
                """)]

        for script in scripts:
            script = script.format(src_activate,src_deactivate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                var="CONDA_DEFAULT_ENV",
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)
            stdout = [s.split("=")[0] for s in stdout.split("\n")]

            print("commands:",commands)
            print("stdout:","\n".join(stdout))
            print("stderr:",stderr)

            assert "CONDA_DEFAULT_ENV" not in stdout, "{} cannot find CONDA_DEFAULT_ENV in environment".format(stderr)
            assert_equals(stderr,'')


@pytest.mark.installed
def test_activate_relative_path(shell):
    """
    current directory should be searched for environments
    """
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        work_dir = os.path.dirname(env_dirs[0])
        env_dir = os.path.basename(env_dirs[0])
        env_var = shell_vars["var_set"].format(variable="CONDA_ENVNAME",value=env_dir)

        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                cd {{work_dir}}
                {{env_var}}
                {}
                {{defaultenv_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                cd {{work_dir}}
                {} "{{env_dir}}"
                {{defaultenv_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                work_dir=work_dir,
                env_var=env_var,
                env_dir=env_dir,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            cwd = os.getcwd()
            # this is not effective for running bash on windows.  It starts
            # in your home dir no matter what. That's what the cd is for above.
            os.chdir(envs)
            try:
                stdout, stderr = run_in(commands, shell, cwd=envs)
            except:
                raise
            finally:
                os.chdir(cwd)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout.rstrip(), env_dir, stderr)
            assert_equals(stderr,'')

@pytest.mark.installed
def test_activate_does_not_leak_echo_setting(shell):
    """Test that activate's setting of echo to off does not disrupt later echo calls"""

    if not on_win or shell != "cmd.exe":
        pytest.skip("echo leaking is only relevant on Window's CMD.EXE")

    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # since we are only testing for cmd.exe only need to check for parameter passing
        scripts += [dedent("""\
            @ECHO ON
            {} "{{env_dirs[0]}}"
            @ECHO
            """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, u'ECHO is on.', stderr)
            assert_equals(stderr, '')


@pytest.mark.skip(reason="I just can't with this test right now.")
@pytest.mark.installed
def test_activate_non_ascii_char_in_path(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='Ånvs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_deactivate = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}deactivate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {}
                {}
                {{defaultenv_print}}.
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}"
                {}
                {{defaultenv_print}}.
                """)]

        for script in scripts:
            script = script.format(src_activate,src_deactivate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, u'.', stderr)
            assert_equals(stderr,'')


@pytest.mark.installed
def test_activate_has_extra_env_vars(shell):
    """Test that environment variables in activate.d show up when activated"""
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        testvariable="TEST_VAR"
        testvalue="test"

        dir=os.path.join(shell_vars['path_from'](env_dirs[0]), "etc", "conda", "activate.d")
        os.makedirs(dir)
        file="test{}".format(shell_vars["suffix_script"])
        file=os.path.join(dir,file)
        with open(file, 'w') as f:
            # do long winded format to ensure that script ends with a newline
            f.write(dedent("""\
                {}
                """).format(shell_vars["envvar_set"].format(
                variable=testvariable,
                value=testvalue)))

        with open(file, 'r') as f:
            print(f.read())

        dir=os.path.join(shell_vars['path_from'](env_dirs[0]), "etc", "conda", "deactivate.d")
        os.makedirs(dir)
        file="test{}".format(shell_vars["suffix_script"])
        file=os.path.join(dir,file)
        with open(file, 'w') as f:
            # do long winded format to ensure that script ends with a newline
            f.write(dedent("""\
                {}
                """).format(shell_vars["envvar_unset"].format(
                variable=testvariable)))

        with open(file, 'r') as f:
            print(f.read())

        #-----------------------------------------------------------------------
        # TEST ACTIVATE
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {}
                {{envvar_getall}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}"
                {{envvar_getall}}
                """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)
            stdout = [s.split("=")[0] for s in stdout.split("\n")]

            print("commands:",commands)
            print("stdout:","\n".join(stdout))
            print("stderr:",stderr)

            assert testvariable in stdout, "{} cannot find {} in environment".format(stderr,testvariable)
            assert_equals(stderr,'')

        #-----------------------------------------------------------------------
        # TEST DEACTIVATE
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_deactivate = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}deactivate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {}
                {}
                {{envvar_getall}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}"
                {}
                {{envvar_getall}}
                """)]

        for script in scripts:
            script = script.format(src_activate,src_deactivate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)
            stdout = [s.split("=")[0] for s in stdout.split("\n")]

            print("commands:",commands)
            print("stdout:","\n".join(stdout))
            print("stderr:",stderr)

            assert testvariable not in stdout, "{} cannot find {} in environment".format(stderr,testvariable)
            assert_equals(stderr,'')


@pytest.mark.installed
def test_activate_verbose(shell):
    """Test that environment variables in activate.d show up when activated"""
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        testvariable="TEST_VAR"
        testvalue="test"

        dir=os.path.join(shell_vars['path_from'](env_dirs[0]), "etc", "conda", "activate.d")
        os.makedirs(dir)
        file="test{}".format(shell_vars["suffix_script"])
        file=os.path.join(dir,file)
        with open(file, 'w') as f:
            f.write(shell_vars["envvar_set"].format(
                variable=testvariable,
                value=testvalue))

        dir=os.path.join(shell_vars['path_from'](env_dirs[0]), "etc", "conda", "deactivate.d")
        os.makedirs(dir)
        file="test{}".format(shell_vars["suffix_script"])
        file=os.path.join(dir,file)
        with open(file, 'w') as f:
            f.write(shell_vars["envvar_unset"].format(
                variable=testvariable))

        #-----------------------------------------------------------------------
        # TEST ACTIVATE
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {{verbose_var}}
                {}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}" "{{flags_verbose}}"
                """)]

            for script in scripts:
                script = script.format(src_activate)
                script = script.format(
                    verbose_var=shell_vars["var_set"].format(variable="CONDA_VERBOSE",value="true"),
                    env_vars=env_vars,
                    env_dirs=env_dirs,
                    **shell_vars)

                commands = shell_vars['command_setup'] + script
                stdout, stderr = run_in(commands, shell)

                print("commands:",commands)
                print("stdout:",stdout)
                print("stderr:",stderr)

                assert_in('[ACTIVATE]: Sourcing',stdout,shell)
                assert_equals(stderr,'')

        #-----------------------------------------------------------------------
        # TEST DEACTIVATE
        #-----------------------------------------------------------------------
        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_deactivate = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}deactivate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{env_vars[0]}}
                {}
                {{verbose_var}}
                {}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {} "{{env_dirs[0]}}"
                {} "{{flags_verbose}}"
                """)]

        for script in scripts:
            script = script.format(src_activate,src_deactivate)
            script = script.format(
                verbose_var=shell_vars["var_set"].format(variable="CONDA_VERBOSE",value="true"),
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_in('[DEACTIVATE]: Sourcing',stdout,shell)
            assert_equals(stderr,'')


@pytest.mark.installed
def test_activate_noPS1(shell):
    if shell in ['powershell.exe']:
        pytest.skip("powershell.exe doesn't support prompt modifications yet")

    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        # all unix shells support environment variables instead of parameter passing
        # windows supports this but is complicated in how it works and hence difficult to test
        if shell not in ["cmd.exe","bash.exe"]:
            scripts += [dedent("""\
                {{prompt_unset}}
                {{env_vars[0]}}
                {}
                {{path_print}}
                """)]
        # most unix shells support parameter passing, dash is the exception
        if shell.split(".")[0] not in ["dash","sh","csh","posh"]:
            scripts += [dedent("""\
                {{prompt_unset}}
                {} "{{env_dirs[0]}}"
                {{path_print}}
                """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell)

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_in(shell_vars['path_delim'].join(_envpaths(envs, 'test 1', shelldict=shell_vars)),
                stdout, shell)
            assert_equals(stderr,'')


@pytest.mark.installed
def test_activate_with_e(shell):
    if shell.split(".")[0] not in ["bash"]:
        pytest.skip("-e only available on bash")

    # in certain cases it is desired to run activate with -e (as is done
    # when running conda-build)
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")

        scripts += [dedent("""\
            {{env_vars[0]}}
            {}
            {{path_print}}
            """)]
        scripts += [dedent("""\
            {} "{{env_dirs[0]}}"
            {{path_print}}
            """)]

        for script in scripts:
            script = script.format(src_activate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell, extra_args="-e")

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_in(shell_vars['path_delim'].join(_envpaths(envs, 'test 1', shelldict=shell_vars)),
                stdout, shell)
            assert_equals(stderr,'')


@pytest.mark.installed
def test_deactivate_with_e(shell):
    if shell.split(".")[0] not in ["bash"]:
        pytest.skip("-e only available on bash")

    # in certain cases it is desired to run activate with -e (as is done
    # when running conda-build)
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
        env_dirs,env_vars=gen_test_env_paths(envs, shell)

        scripts = []
        src_activate = shell_vars['source'].format(
            "{syspath}{binpath}activate{suffix_executable}")
        src_deactivate = shell_vars['source'].format(
            "{env_dirs[0]}{binpath}deactivate{suffix_executable}")

        scripts += [dedent("""\
            {{env_vars[0]}}
            {}
            {}
            {{path_print}}
            """)]
        scripts += [dedent("""\
            {} "{{env_dirs[0]}}"
            {}
            {{path_print}}
            """)]

        for script in scripts:
            script = script.format(src_activate,src_deactivate)
            script = script.format(
                env_vars=env_vars,
                env_dirs=env_dirs,
                **shell_vars)

            commands = shell_vars['command_setup'] + script
            stdout, stderr = run_in(commands, shell, extra_args="-e")

            print("commands:",commands)
            print("stdout:",stdout)
            print("stderr:",stderr)

            assert_equals(stdout, u"%s" % shell_vars['base_path'], stderr)
            assert_equals(stderr,'')


# @pytest.mark.slow
# def test_activate_keeps_PATH_order(shell):
#     if not on_win or shell != "cmd.exe":
#         pytest.xfail("test only implemented for cmd.exe on win")
#     shell_vars = _format_vars(shell)
#     with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
#         commands = shell_vars['command_setup'] + dedent("""\
#             @set "PATH=somepath;CONDA_PATH_PLACEHOLDER;%PATH%"
#             @call "{syspath}{binpath}activate.bat"
#             {path_print}
#             """).format(
#                 envs=envs,
#                 env_dirs=gen_test_env_paths(envs, shell),
#                 **shell_vars)
#         stdout, stderr = run_in(commands, shell)
#         assert stdout.startswith("somepath;" + sys.prefix)

# @pytest.mark.slow
# def test_deactivate_placeholder(shell):
#     if not on_win or shell != "cmd.exe":
#         pytest.xfail("test only implemented for cmd.exe on win")
#     shell_vars = _format_vars(shell)
#     with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
#         commands = shell_vars['command_setup'] + dedent("""\
#             @set "PATH=flag;%PATH%"
#             @call "{syspath}{binpath}activate.bat"
#             @call "{syspath}{binpath}deactivate.bat" "hold"
#             {path_print}
#             """).format(
#                 envs=envs,
#                 env_dirs=gen_test_env_paths(envs, shell),
#                 **shell_vars)
#         stdout, stderr = run_in(commands, shell)
#         assert stdout.startswith("CONDA_PATH_PLACEHOLDER;flag")


# This test depends on files that are copied/linked in the conda recipe.  It is unfortunately not going to run after
#    a setup.py install step
# @pytest.mark.slow
# def test_activate_from_exec_folder(shell):
#     """The exec folder contains only the activate and conda commands.  It is for users
#     who want to avoid conda packages shadowing system ones."""
#     shell_vars = _format_vars(shell)
#     with TemporaryDirectory(prefix='envs', dir=os.path.dirname(__file__)) as envs:
#         env_dirs=gen_test_env_paths(envs, shell)
#         commands = shell_vars['command_setup'] + dedent("""\
#             {source} "{syspath}/exec/activate{suffix_executable}" "{env_dirs[0]}"
#             {echo} {var}
#             """).format(
#                 envs=envs,
#                 env_dirs=env_dirs,
#                 var=shell_vars["var_format"].format("TEST_VAR"),
#                 **shell_vars)
#         stdout, stderr = run_in(commands, shell)
#         assert_equals(stdout, u'test', stderr)


def run_in(command, shell, cwd=None, env=None, extra_args=""):
    if hasattr(shell, "keys"):
        shell = shell["exe"]

    if shell in ["cmd.exe","powershell.exe"]:
        # create temporary script with the commands to run, then execute script
        with tempfile.NamedTemporaryFile(suffix=shells[shell]["suffix_script"],
                                         mode='w+t',
                                         delete=False) as cmd_script:
            cmd_name=cmd_script.name
            cmd_script.write(command)

        with open(cmd_name, "r") as f:
            print("cmd_bits: {{{}}}".format(f.read()))

        cmd_bits = dedent("""\
            {exe} {shell_args} {script}
            """).format(
                script=cmd_name,
                **shells[shell])

        try:
            p = subprocess.Popen(cmd_bits,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 cwd=cwd,
                                 env=env)
            streams = p.communicate()
        finally:
            # unlink temporary file such that it is garbage collected
            os.unlink(cmd_name)
    elif any(map(lambda ext: shell.endswith(ext), [".cygwin",".mingw",".msys"])):
        with tempfile.NamedTemporaryFile(suffix=shells["cmd.exe"]["suffix_script"],
                                         mode='w+b',
                                         delete=False) as cmd_script:
            cmd_name=cmd_script.name
            cmd_script.write(dedent("""\
                : <<TRAMPOLINE
                @CALL {exe} -c "exit 0" || (@ECHO Shell {exe} not found on PATH & @EXIT /b 1)
                @SET "PATH={pathprefix};%PATH%"
                @CALL {exe} {shell_args} {extra_args} "%~f0"
                @GOTO :EOF
                TRAMPOLINE
                #####################
                #!/usr/bin/env {shebang}
                {command}
                """).format(
                    command=command,
                    extra_args=extra_args,
                    # using .exe in shebang causes issues
                    shebang=re.sub(r'\.\w+$',r'',os.path.basename(shells[shell]["exe"])),
                    **shells[shell]).encode())

        with open(cmd_name, "r") as f:
            print("cmd_bits: {{{}}}".format(f.read()))

        cmd_bits = dedent("""\
            {exe} {shell_args} {script}
            """).format(
                script=cmd_name,
                **shells["cmd.exe"])

        try:
            p = subprocess.Popen(cmd_bits,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 cwd=cwd,
                                 env=env)
            streams = p.communicate()
        finally:
            # unlink temporary file such that it is garbage collected
            os.unlink(cmd_name)
    else:
        # heredoc/hereword are the closest we can get to truly mimicking a
        # proper sourcing of the activate/deactivate scripts
        #
        # must use heredoc to avoid Ubuntu/dash incompatibility with hereword
        cmd_bits = dedent("""\
            {exe} {shell_args} {extra_args} <<- 'HEREDOC'
            {command}
            HEREDOC
            """).format(
                command=translate_stream(command, shells[shell]["path_to"]),
                extra_args=extra_args,
                **shells[shell])

        print("cmd_bits: {{{}}}".format(cmd_bits))

        p = subprocess.Popen(cmd_bits,
                             shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             cwd=cwd,
                             env=env)
        streams = p.communicate()
    return map(lambda s: u"{}".format(s.decode('utf-8').replace('\r\n', '\n').rstrip("\n")), streams)
