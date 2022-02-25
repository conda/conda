# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# Attempt to move any conda entries in PATH to the front of it.
# IDEs have their own ideas about how PATH should be managed and
# they do dumb stuff like add /usr/bin to the front of it
# meaning conda takes a submissive role and the wrong stuff
# runs (when other conda prefixes get activated they replace
# the wrongly placed entries with newer wrongly placed entries).
#
# Note, there's still condabin to worry about here, and also should
# we not remove all traces of conda instead of just this fixup?
# Ideally we'd have two modes, 'removed' and 'fixed'. I have seen
# condabin come from an entirely different installation than
# CONDA_PREFIX too in some instances and that really needs fixing.

import os
import sys
from os.path import dirname, normpath, join, isfile
from subprocess import check_output


def encode_for_env_var(value):
    if isinstance(value, str):
        return value
    if sys.version_info[0] == 2:
        _unicode = unicode
    else:
        _unicode = str
    if isinstance(value, (str, _unicode)):
        try:
            return bytes(value, encoding='utf-8')
        except:
            return value.encode('utf-8')
    return str(value)


def conda_ensure_sys_python_is_base_env_python():
    # Exit if we try to run tests from a non-base env. The tests end up installing
    # menuinst into the env they are called with and that breaks non-base env activation
    # as it emits a message to stderr:
    # WARNING menuinst_win32:<module>(157): menuinst called from non-root env
    # C:\opt\conda\envs\py27
    # So lets just sys.exit on that.

    if 'CONDA_PYTHON_EXE' in os.environ:
        if os.path.normpath(os.environ['CONDA_PYTHON_EXE']) != sys.executable:
            print("ERROR :: Running tests from a non-base Python interpreter. "
                  " Tests requires installing menuinst and that causes stderr "
                  " output when activated.", file=sys.stderr)
            sys.exit(-1)


def conda_move_to_front_of_PATH():
    if 'CONDA_PREFIX' in os.environ:
        from conda.activate import (PosixActivator, CmdExeActivator)
        if os.name == 'nt':
            activator_cls = CmdExeActivator
        else:
            activator_cls = PosixActivator
        activator = activator_cls()
        # But why not just use _replace_prefix_in_path? => because moving
        # the entries to the front of PATH is the goal here, not swapping
        # x for x (which would be pointless anyway).
        p = None
        # It might be nice to have a parameterised fixture with choices of:
        # 'System default PATH',
        # 'IDE default PATH',
        # 'Fully activated conda',
        # 'PATHly activated conda'
        # This will do for now => Note, if you have conda activated multiple
        # times it could mask some test failures but _remove_prefix_from_path
        # cannot be used multiple times; it will only remove *one* conda
        # prefix from the *original* value of PATH, calling it N times will
        # just return the same value every time, even if you update PATH.
        p = activator._remove_prefix_from_path(os.environ['CONDA_PREFIX'])

        # Replace any non sys.prefix condabin with sys.prefix condabin
        new_p = []
        found_condabin = False
        for pe in p:
            if pe.endswith('condabin'):
                if not found_condabin:
                    found_condabin = True
                    if join(sys.prefix, 'condabin') != pe:
                        condabin_path = join(sys.prefix, 'condabin')
                        print("Incorrect condabin, swapping {} to {}".format(pe, condabin_path))
                        new_p.append(condabin_path)
                    else:
                        new_p.append(pe)
            else:
                new_p.append(pe)

        new_path = os.pathsep.join(new_p)
        new_path = encode_for_env_var(new_path)
        os.environ['PATH'] = new_path
        activator = activator_cls()
        p = activator._add_prefix_to_path(os.environ['CONDA_PREFIX'])
        new_path = os.pathsep.join(p)
        new_path = encode_for_env_var(new_path)
        os.environ['PATH'] = new_path


def conda_check_versions_aligned():
    # Next problem. If we use conda to provide our git or otherwise do not
    # have it on PATH and if we also have no .version file then conda is
    # unable to figure out its version without throwing an exception. The
    # tests this broke most badly (test_activate.py) have a workaround of
    # installing git into one of the conda prefixes that gets used but it
    # is slow. Instead write .version if it does not exist, and also fix
    # it if it disagrees.

    import conda
    version_file = normpath(join(dirname(conda.__file__), '.version'))
    if isfile(version_file):
        version_from_file = open(version_file, 'rt').read().split('\n')[0]
    else:
        version_from_file = None

    git_exe = 'git.exe' if sys.platform == 'win32' else 'git'
    version_from_git = None
    for pe in os.environ.get('PATH', '').split(os.pathsep):
        if isfile(join(pe, git_exe)):
            try:
                cmd = join(pe, git_exe) + ' describe --tags --long'
                version_from_git = check_output(cmd).decode('utf-8').split('\n')[0]
                from conda.auxlib.packaging import _get_version_from_git_tag
                version_from_git = _get_version_from_git_tag(version_from_git)
                break
            except:
                continue
    if not version_from_git:
        print("WARNING :: Could not check versions.")

    if version_from_git and version_from_git != version_from_file:
        print("WARNING :: conda/.version ({}) and git describe ({}) "
              "disagree, rewriting .version".format(version_from_git, version_from_file))
        with open(version_file, 'w') as fh:
            fh.write(version_from_git)
