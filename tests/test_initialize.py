# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from distutils.sysconfig import get_python_lib
from logging import getLogger
from os.path import join, realpath, isfile
import sys

from conda import CONDA_PACKAGE_ROOT
from conda._vendor.auxlib.ish import dals
from conda.base.context import context
from conda.cli.common import stdout_json
from conda.common.compat import on_win
from conda.initialize import Result, _get_python_info, init_conda_bat, init_conda_csh, \
    init_conda_fish, init_conda_sh, init_conda_xsh, make_entry_point, make_install_plan, \
    make_entry_point_exe
from .helpers import tempdir

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch


log = getLogger(__name__)


def test_get_python_info():
    python_exe, python_version, site_packages_dir = _get_python_info(sys.prefix)
    assert realpath(python_exe) == realpath(sys.executable)
    assert python_version == "%s.%s.%s" % sys.version_info[:3]
    assert site_packages_dir == get_python_lib()


def test_make_initialize_plan_install():
    python_exe = "/darwin/bin/python"
    python_version = "2.6.10"
    site_packages_dir = "/darwin/lib/python2.6/site-packages"

    with patch("conda.initialize._get_python_info", return_value=(
            python_exe, python_version, site_packages_dir
    )):
        plan = make_install_plan("/darwin")
        stdout_json(plan)
        if on_win:
            assert False
        else:
            assert plan == [
                {
                    "function": "make_entry_point",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "func": "main",
                        "module": "conda.cli",
                        "target_path": "/darwin/bin/conda"
                    }
                },
                {
                    "function": "make_entry_point",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "func": "main",
                        "module": "conda_env.cli.main",
                        "target_path": "/darwin/bin/conda-env"
                    }
                },
                {
                    "function": "init_conda_sh",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin/etc/profile.d/conda.sh"
                    }
                },
                {
                    "function": "init_conda_fish",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin/etc/fish/conf.d/conda.fish"
                    }
                },
                {
                    "function": "init_conda_xsh",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin/lib/python2.6/site-packages/xonsh/conda.xsh"
                    }
                },
                {
                    "function": "init_conda_csh",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin/etc/profile.d/conda.csh"
                    }
                }
            ]


def test_make_entry_point():
    with tempdir() as conda_prefix:
        if on_win:
            conda_exe_path = join(conda_prefix, 'Scripts', 'conda-script.py')
        else:
            conda_exe_path = join(conda_prefix, 'bin', 'conda')
        result = make_entry_point(conda_exe_path, conda_prefix, 'conda.entry.point', 'run')
        assert result == Result.MODIFIED

        with open(conda_exe_path) as fh:
            ep_contents = fh.read()

        if on_win:
            assert ep_contents == dals("""
            # -*- coding: utf-8 -*-

            if __name__ == '__main__':
                import sys
                from conda.entry.point import run
                sys.exit(run())
            """) % conda_prefix
        else:
            assert ep_contents == dals("""
            #!%s/bin/python
            # -*- coding: utf-8 -*-

            if __name__ == '__main__':
                import sys
                from conda.entry.point import run
                sys.exit(run())
            """) % conda_prefix

        result = make_entry_point(conda_exe_path, conda_prefix, 'conda.entry.point', 'run')
        assert result == Result.NO_CHANGE


def test_init_conda_sh():
    with tempdir() as conda_prefix:
        target_path = join(conda_prefix, 'etc', 'profile.d', 'conda.sh')
        result = init_conda_sh(target_path, conda_prefix)
        assert result == Result.MODIFIED

        with open(target_path) as fh:
            created_file_contents = fh.read()

        first_line, remainder = created_file_contents.split('\n', 1)
        if on_win:
            assert first_line == "_CONDA_EXE=\"$(cygpath '%s')\"" % context.conda_exe
        else:
            assert first_line == '_CONDA_EXE="%s"' % context.conda_exe

        with open(join(CONDA_PACKAGE_ROOT, 'shell', 'etc', 'profile.d', 'conda.sh')) as fh:
            original_contents = fh.read()
        assert remainder == original_contents

        result = init_conda_sh(target_path, conda_prefix)
        assert result == Result.NO_CHANGE


def test_init_conda_fish():
    with tempdir() as conda_prefix:
        target_path = join(conda_prefix, 'etc', 'fish', 'conf.d', 'conda.fish')
        result = init_conda_fish(target_path, conda_prefix)
        assert result == Result.MODIFIED

        with open(target_path) as fh:
            created_file_contents = fh.read()

        first_line, second_line, remainder = created_file_contents.split('\n', 2)
        if on_win:
            win_conda_exe = join(conda_prefix, 'Scripts', 'conda.exe')
            assert first_line == 'set _CONDA_ROOT (cygpath %s)' % conda_prefix
            assert second_line == 'set _CONDA_EXE (cygpath %s)' % win_conda_exe
        else:
            assert first_line == 'set _CONDA_ROOT "%s"' % conda_prefix
            assert second_line == 'set _CONDA_EXE "%s"' % join(conda_prefix, 'bin', 'conda')

        with open(join(CONDA_PACKAGE_ROOT, 'shell', 'etc', 'fish', 'conf.d', 'conda.fish')) as fh:
            original_contents = fh.read()
        assert remainder == original_contents

        result = init_conda_fish(target_path, conda_prefix)
        assert result == Result.NO_CHANGE


def test_init_conda_xsh():
    with tempdir() as conda_prefix:
        target_path = join(conda_prefix, 'Lib', 'site-packages', 'conda.xsh')
        result = init_conda_xsh(target_path, conda_prefix)
        assert result == Result.MODIFIED

        with open(target_path) as fh:
            created_file_contents = fh.read()

        first_line, remainder = created_file_contents.split('\n', 1)
        if on_win:
            assert first_line == '_CONDA_EXE = "%s"' % join(conda_prefix, 'Scripts', 'conda.exe')
        else:
            assert first_line == '_CONDA_EXE = "%s"' % join(conda_prefix, 'bin', 'conda')

        with open(join(CONDA_PACKAGE_ROOT, 'shell', 'conda.xsh')) as fh:
            original_contents = fh.read()
        assert remainder == original_contents

        result = init_conda_xsh(target_path, conda_prefix)
        assert result == Result.NO_CHANGE


def test_init_conda_csh():
    with tempdir() as conda_prefix:
        target_path = join(conda_prefix, 'etc', 'profile.d', 'conda.csh')
        result = init_conda_csh(target_path, conda_prefix)
        assert result == Result.MODIFIED

        with open(target_path) as fh:
            created_file_contents = fh.read()

        first_line, second_line, remainder = created_file_contents.split('\n', 2)
        if on_win:
            assert first_line == 'setenv _CONDA_ROOT `cygpath %s`' % conda_prefix
            assert second_line == 'setenv _CONDA_EXE `cygpath %s`' % join(conda_prefix, 'Scripts', 'conda.exe')
        else:
            assert first_line == 'setenv _CONDA_ROOT "%s"' % conda_prefix
            assert second_line == 'setenv _CONDA_EXE "%s"' % join(conda_prefix, 'bin', 'conda')

        with open(join(CONDA_PACKAGE_ROOT, 'shell', 'etc', 'profile.d', 'conda.csh')) as fh:
            original_contents = fh.read()
        assert remainder == original_contents

        result = init_conda_csh(target_path, conda_prefix)
        assert result == Result.NO_CHANGE


def test_init_conda_bat():
    with tempdir() as conda_prefix:
        target_path = join(conda_prefix, 'Library', 'bin', 'conda.bat')
        result = init_conda_bat(target_path, conda_prefix)
        assert result == Result.MODIFIED

        with open(target_path) as fh:
            created_file_contents = fh.read()

        first_line, remainder = created_file_contents.split('\n', 1)
        assert first_line == '@SET "_CONDA_EXE=%s"' % join(conda_prefix, 'Scripts', 'conda.exe')

        with open(join(CONDA_PACKAGE_ROOT, 'shell', 'Library', 'bin', 'conda.bat')) as fh:
            original_contents = fh.read()
        assert remainder == original_contents

        result = init_conda_bat(target_path, conda_prefix)
        assert result == Result.NO_CHANGE


def test_make_entry_point_exe():
    with tempdir() as conda_prefix:
        target_path = join(conda_prefix, 'Scripts', 'conda-env.exe')
        result = make_entry_point_exe(target_path, conda_prefix)
        assert result == Result.MODIFIED

        assert isfile(target_path)

        result = make_entry_point_exe(target_path, conda_prefix)
        assert result == Result.NO_CHANGE
