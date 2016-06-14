# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import

import os
from os.path import dirname
import stat
import sys

import pytest

from conda.compat import TemporaryDirectory
from conda.config import root_dir, platform
from conda.install import symlink_conda
from conda.utils import path_identity, run_in, shells
from conda.cli.activate import pathlist_to_str, binpath_from_arg

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
    paths = [converter(path) for path in paths]
    return paths

def _envpaths(env_root, env_name="", shelldict={}):
    """Supply the appropriate platform executable folders.  rstrip on root removes
       trailing slash if env_name is empty (the default)

    Assumes that any prefix used here exists.  Will not work on prefixes that don't.
    """
    sep = shelldict['sep']
    return binpath_from_arg(sep.join([env_root, env_name]), shelldict=shelldict)


PYTHONPATH = os.path.dirname(os.path.dirname(__file__))

# Make sure the subprocess activate calls this python
syspath = os.pathsep.join(_envpaths(root_dir, shelldict={"path_to": path_identity,
                                                         "path_from": path_identity,
                                                         "sep": os.sep}))

def print_ps1(env_dirs, raw_ps, number):
    return (u"(({})) ".format(os.path.split(env_dirs[number])[-1]) + raw_ps)


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

    base_path, _ = run_in(shelldict['printpath'], shell)
    # windows forces Library/bin onto PATH when starting up.  Strip it for the purposes of this test.
    if sys.platform == "win32":
        base_path = strip_leading_library_bin(base_path, shelldict)

    raw_ps, _ = run_in(shelldict["printps1"], shell)

    command_setup = """\
{set} PYTHONPATH="{PYTHONPATH}"
{set} CONDARC=
{set} CONDA_PATH_BACKUP=
""".format(here=dirname(__file__), PYTHONPATH=shelldict['path_to'](PYTHONPATH),
           set=shelldict["set_var"])
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
        'syspath': shelldict['path_to'](sys.prefix),
        'binpath': shelldict['binpath'],
        'command_setup': command_setup,
        'base_path': base_path,
}


@pytest.fixture(scope="module")
def bash_profile(request):
    profile=os.path.join(os.path.expanduser("~"), ".bash_profile")
    if os.path.isfile(profile):
        os.rename(profile, profile+"_backup")
    with open(profile, "w") as f:
        f.write("export PS1=test_ps1\n")
        f.write("export PROMPT=test_ps1\n")
    def fin():
        if os.path.isfile(profile+"_backup"):
            os.remove(profile)
            os.rename(profile+"_backup", profile)
    request.addfinalizer(fin)
    return request  # provide the fixture value


@pytest.mark.slow
def test_activate_test1(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate{shell_suffix}" "{env_dirs[0]}"
        {printpath}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert_equals(stderr, u'prepending {envpaths} to PATH'\
                        .format(envpaths=pathlist_to_str(_envpaths(envs, 'test 1',
                                                                   shelldict=shells[shell]),
                                                         escape_backslashes=True)), shell)
        assert_in(shells[shell]['pathsep'].join(_envpaths(envs, 'test 1', shelldict=shells[shell])),
                 stdout, shell)


@pytest.mark.slow
def test_activate_env_from_env_with_root_activate(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{binpath}activate" "{env_dirs[1]}"
        {printpath}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert_equals(stderr, u'prepending {envpaths2} to PATH'\
            .format(envpaths2=pathlist_to_str(_envpaths(envs, 'test 2', shelldict=shells[shell]))))
        assert_in(shells[shell]['pathsep'].join(_envpaths(envs, 'test 2', shelldict=shells[shell])), stdout)


@pytest.mark.slow
def test_activate_bad_directory(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        env_dirs = gen_test_env_paths(envs, shell)
        # Strange semicolons are here to defeat MSYS' automatic path conversion.
        #   See http://www.mingw.org/wiki/Posix_path_conversion
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[2]}"
        {printpath}
        """).format(envs=envs, env_dirs=env_dirs, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        # another semicolon here for comparison reasons with one above.
        assert 'could not find environment' in stderr
        assert_not_in(env_dirs[2], stdout)


@pytest.mark.slow
def test_activate_bad_env_keeps_existing_good_env(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} {syspath}{binpath}activate "{env_dirs[0]}" {nul}
        {source} "{syspath}{binpath}activate" "{env_dirs[2]}"
        {printpath}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert_in(shells[shell]['pathsep'].join(_envpaths(envs, 'test 1', shelldict=shells[shell])),stdout)


@pytest.mark.slow
def test_activate_deactivate(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{binpath}deactivate"
        {printpath}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)

        stdout, stderr = run_in(commands, shell)
        stdout = strip_leading_library_bin(stdout, shells[shell])
        assert_equals(stdout, u"%s" % shell_vars['base_path'])


@pytest.mark.slow
def test_activate_root(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" root
        {printpath}
        """).format(envs=envs, **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert_in(shells[shell]['pathsep'].join(_envpaths(root_dir, shelldict=shells[shell])), stdout, stderr)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" root
        {source} "{syspath}{binpath}deactivate"
        {printpath}
        """).format(envs=envs, **shell_vars)

        stdout, stderr = run_in(commands, shell)
        stdout = strip_leading_library_bin(stdout, shells[shell])
        assert_equals(stdout, u"%s" % shell_vars['base_path'], stderr)


def test_activate_root_env_from_other_env(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{binpath}activate" root
        {printpath}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert_in(shells[shell]['pathsep'].join(_envpaths(root_dir, shelldict=shells[shell])),
                  stdout)
        assert_not_in(shells[shell]['pathsep'].join(_envpaths(envs, 'test 1', shelldict=shells[shell])), stdout)


@pytest.mark.slow
def test_wrong_args(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" two args
        {printpath}
        """).format(envs=envs, **shell_vars)

        stdout, stderr = run_in(commands, shell)
        stdout = strip_leading_library_bin(stdout, shells[shell])
        assert_equals(stderr, u'Error: did not expect more than one argument.\n    (got two args)')
        assert_equals(stdout, shell_vars['base_path'], stderr)


@pytest.mark.slow
def test_activate_help(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        if shell not in ['powershell.exe', 'cmd.exe']:
            commands = (shell_vars['command_setup'] + """
            "{syspath}{binpath}activate" Zanzibar
            """).format(envs=envs, **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '')
            assert_in("activate must be sourced", stderr)
            assert_in("Usage: source activate ENV", stderr)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" --help
        """).format(envs=envs, **shell_vars)

        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, '')

        if shell in ["cmd.exe", "powershell"]:
            assert_in("Usage: activate ENV", stderr)
        else:
            assert_in("Usage: source activate ENV", stderr)

            commands = (shell_vars['command_setup'] + """
            {syspath}{binpath}deactivate
            """).format(envs=envs, **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_equals(stdout, '')
            assert_in("deactivate must be sourced", stderr)
            assert_in("Usage: source deactivate", stderr)

        commands = (shell_vars['command_setup'] + """
        {source} {syspath}{binpath}deactivate --help
        """).format(envs=envs, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, '')
        if shell in ["cmd.exe", "powershell"]:
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
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}"
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stderr, u'prepending {envpaths1} to PATH'\
                .format(syspath=pathlist_to_str(_envpaths(root_dir, shelldict=shells[shell])),
                        envpaths1=shells[shell]["path_to"](pathlist_to_str(_envpaths(envs,
                                                                                     'test 1',
                                                                                     shelldict=shells[shell])))))

        where = 'Scripts' if sys.platform == 'win32' else 'bin'
        for env in gen_test_env_paths(envs, shell)[:2]:
            scripts = ["conda", "activate", "deactivate"]
            for f in scripts:
                if sys.platform == "win32":
                    file_path = os.path.join(env, where, f + shells[shell]["shell_suffix"])
                    # must translate path to windows representation for Python's sake
                    file_path = shells[shell]["path_from"](file_path)
                    assert(os.path.lexists(file_path))
                else:
                    file_path = os.path.join(env, where, f)
                    assert(os.path.lexists(file_path))
                    s = os.lstat(file_path)
                    assert(stat.S_ISLNK(s.st_mode))
                    assert(os.readlink(file_path) == '{root_path}'.format(root_path=os.path.join(sys.prefix, where, f)))

        if platform != 'win':
            # Test activate when there are no write permissions in the
            # env.
            prefix_bin_path = os.path.join(gen_test_env_paths(envs, shell)[2], 'bin')
            commands = (shell_vars['command_setup'] + """
            mkdir -p "{prefix_bin_path}"
            chmod 444 "{prefix_bin_path}"
            {source} activate "{env_dirs[2]}"
            """).format(prefix_bin_path=prefix_bin_path, envs=envs,
                                env_dirs=gen_test_env_paths(envs, shell),
                **shell_vars)
            stdout, stderr = run_in(commands, shell)
            assert_in("not have write access", stderr)

            # restore permissions so the dir will get cleaned up
            run_in('chmod 777 "{prefix_bin_path}"'.format(prefix_bin_path=prefix_bin_path), shell)


@pytest.mark.slow
def test_PS1(shell, bash_profile):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        # activate changes PS1 correctly
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}"
        {printps1}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, print_ps1(env_dirs=gen_test_env_paths(envs, shell),
                                        raw_ps=shell_vars["raw_ps"], number=0), stderr)

        # second activate replaces earlier activated env PS1
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{binpath}activate" "{env_dirs[1]}"
        {printps1}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, sterr = run_in(commands, shell)
        assert_equals(stdout, print_ps1(env_dirs=gen_test_env_paths(envs, shell),
                                        raw_ps=shell_vars["raw_ps"], number=1), stderr)

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
        assert_equals(stdout, print_ps1(env_dirs=gen_test_env_paths(envs, shell),
                                        raw_ps=shell_vars["raw_ps"], number=0), stderr)

        # deactivate doesn't do anything bad to PS1 when no env active to deactivate
        commands = (shell_vars['command_setup'] + """
        {source} {syspath}{binpath}deactivate
        {printps1}
        """).format(envs=envs, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, shell_vars['raw_ps'], stderr)

        # deactivate script in activated env returns us to raw PS1
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}" {nul}
        {source} "{env_dirs[0]}{binpath}deactivate"
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


@pytest.mark.slow
def test_PS1_no_changeps1(shell, bash_profile):
    """Ensure that people's PS1 remains unchanged if they have that setting in their RC file."""
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
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
        {source} "{env_dirs[0]}{binpath}deactivate"
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


@pytest.mark.slow
def test_CONDA_DEFAULT_ENV(shell):
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        env_dirs=gen_test_env_paths(envs, shell)
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}"
        {printdefaultenv}
        """).format(envs=envs, env_dirs=env_dirs, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout.rstrip(), env_dirs[0], stderr)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}" {nul}
        {source} "{syspath}{binpath}activate" "{env_dirs[1]}"
        {printdefaultenv}
        """).format(envs=envs, env_dirs=env_dirs, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout.rstrip(), env_dirs[1], stderr)

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
        assert_equals(stdout.rstrip(), env_dirs[0], stderr)

        commands = (shell_vars['command_setup'] + """
        {source} {syspath}{binpath}deactivate
        {printdefaultenv}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, '', stderr)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}" {nul}
        {source} "{env_dirs[0]}{binpath}deactivate"
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
        assert_equals(stdout.rstrip(), shells[shell]['path_to'](sys.prefix), stderr)

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" root {nul}
        {source} "{env_dirs[0]}{binpath}deactivate" {nul}
        {printdefaultenv}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, '', stderr)

@pytest.mark.slow
def test_activate_from_env(shell):
    """Tests whether the activate bat file or link in the activated environment works OK"""
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        env_dirs=gen_test_env_paths(envs, shell)
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}"
        {source} "{env_dirs[0]}{binpath}activate" "{env_dirs[1]}"
        {printdefaultenv}
        """).format(envs=envs, env_dirs=env_dirs, **shell_vars)
        stdout, stderr = run_in(commands, shell)
        # rstrip on output is because the printing to console picks up an extra space
        assert_equals(stdout.rstrip(), env_dirs[1], stderr)


@pytest.mark.slow
def test_deactivate_from_env(shell):
    """Tests whether the deactivate bat file or link in the activated environment works OK"""
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}"
        {source} "{env_dirs[0]}{binpath}deactivate"
        {printdefaultenv}
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, u'', stderr)


@pytest.mark.slow
def test_activate_relative_path(shell):
    """
    current directory should be searched for environments
    """
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        env_dirs = gen_test_env_paths(envs, shell)
        env_dir = os.path.basename(env_dirs[0])
        work_dir = os.path.dirname(env_dir)
        commands = (shell_vars['command_setup'] + """
        cd {work_dir}
        {source} "{syspath}{binpath}activate" "{env_dir}"
        {printdefaultenv}
        """).format(work_dir=envs, envs=envs, env_dir=env_dir, **shell_vars)
        cwd = os.getcwd()
        # this is not effective for running bash on windows.  It starts
        #    in your home dir no matter what.  That's what the cd is for above.
        os.chdir(envs)
        try:
            stdout, stderr = run_in(commands, shell, cwd=envs)
        except:
            raise
        finally:
            os.chdir(cwd)
        assert_equals(stdout.rstrip(), env_dirs[0], stderr)


@pytest.mark.slow
def test_activate_does_not_leak_echo_setting(shell):
    """Test that activate's setting of echo to off does not disrupt later echo calls"""

    if sys.platform != "win32" or shell != "cmd.exe":
        pytest.skip("test only relevant for cmd.exe on win")
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        @echo on
        @call "{syspath}{binpath}activate.bat" "{env_dirs[0]}"
        @echo
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, u'ECHO is on.', stderr)


@pytest.mark.slow
def test_activate_non_ascii_char_in_path(shell):
    pytest.xfail("subprocess with python 2.7 is broken with unicode")
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='Ånvs', dir=dirname(__file__)) as envs:
        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}"
        {source} "{env_dirs[0]}{binpath}deactivate"
        {printdefaultenv}.
        """).format(envs=envs, env_dirs=gen_test_env_paths(envs, shell), **shell_vars)
        stdout, stderr = run_in(commands, shell)
        assert_equals(stdout, u'.', stderr)


@pytest.mark.slow
def test_activate_has_extra_env_vars(shell):
    """Test that environment variables in activate.d show up when activated"""
    shell_vars = _format_vars(shell)
    with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
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
        assert_equals(stdout, u'test', stderr)

        # Make sure the variable is reset after deactivation

        commands = (shell_vars['command_setup'] + """
        {source} "{syspath}{binpath}activate" "{env_dirs[0]}"
        {source} "{env_dirs[0]}{binpath}deactivate"
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
#     with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
#         env_dirs=gen_test_env_paths(envs, shell)
#         commands = (shell_vars['command_setup'] + """
#         {source} "{syspath}/exec/activate" "{env_dirs[0]}"
#         {echo} {var}
#         """).format(envs=envs, env_dirs=env_dirs, var=shells[shell]["var_format"].format("TEST_VAR"), **shell_vars)
#         stdout, stderr = run_in(commands, shell)
#         assert_equals(stdout, u'test', stderr)
