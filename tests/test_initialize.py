# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from distutils.sysconfig import get_python_lib
from logging import getLogger
from os.path import join, realpath, isfile, abspath, dirname
import sys

import pytest

from conda import CONDA_PACKAGE_ROOT
from conda._vendor.auxlib.ish import dals
from conda.base.context import context, reset_context
from conda.cli.common import stdout_json
from conda.common.compat import on_win
from conda.common.io import env_var, captured
from conda.common.path import get_python_short_path
from conda.exceptions import CondaValueError
from conda.gateways.disk.create import create_link, mkdir_p
from conda.initialize import Result, _get_python_info, install_conda_bat, install_conda_csh, \
    install_conda_fish, install_conda_sh, install_conda_xsh, make_entry_point, make_install_plan, \
    make_entry_point_exe, install, initialize_dev, make_initialize_plan
from conda.models.enums import LinkType
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


def test_make_install_plan():
    python_exe = "/darwin/bin/python"
    python_version = "2.6.10"
    site_packages_dir = "/darwin/lib/python2.6/site-packages"

    with patch("conda.initialize._get_python_info", return_value=(
            python_exe, python_version, site_packages_dir
    )):
        plan = make_install_plan("/darwin")
        stdout_json(plan)
        if on_win:
            assert plan == [
                {
                    "function": "make_entry_point_exe",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin\\Scripts\\conda.exe"
                    }
                },
                {
                    "function": "make_entry_point_exe",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin\\Scripts\\conda-env.exe"
                    }
                },
                {
                    "function": "make_entry_point",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "func": "main",
                        "module": "conda.cli",
                        "target_path": "/darwin\\Scripts\\conda-script.py"
                    }
                },
                {
                    "function": "make_entry_point",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "func": "main",
                        "module": "conda_env.cli.main",
                        "target_path": "/darwin\\Scripts\\conda-env-script.py"
                    }
                },
                {
                    "function": "install_conda_bat",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin\\Library\\bin\\conda.bat"
                    }
                },
                {
                    "function": "install_condacmd_conda_bat",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin\\condacmd\\conda.bat"
                    }
                },
                {
                    "function": "install_condacmd_hook_bat",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin\\condacmd\\conda-hook.bat"
                    }
                },
                {
                    "function": "install_activate_bat",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin\\Scripts\\activate.bat"
                    }
                },
                {
                    "function": "install_deactivate_bat",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin\\Scripts\\deactivate.bat"
                    }
                },
                {
                    "function": "install_activate",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin\\Scripts\\activate"
                    }
                },
                {
                    "function": "install_deactivate",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin\\Scripts\\deactivate"
                    }
                },
                {
                    "function": "install_conda_sh",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin\\etc\\profile.d\\conda.sh"
                    }
                },
                {
                    "function": "install_conda_fish",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin\\etc\\fish\\conf.d\\conda.fish"
                    }
                },
                {
                    "function": "install_conda_xsh",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin/lib/python2.6/site-packages\\xonsh\\conda.xsh"
                    }
                },
                {
                    "function": "install_conda_csh",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin\\etc\\profile.d\\conda.csh"
                    }
                }
            ]
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
                    "function": "install_activate",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin/bin/activate"
                    }
                },
                {
                    "function": "install_deactivate",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin/bin/deactivate"
                    }
                },
                {
                    "function": "install_conda_sh",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin/etc/profile.d/conda.sh"
                    }
                },
                {
                    "function": "install_conda_fish",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin/etc/fish/conf.d/conda.fish"
                    }
                },
                {
                    "function": "install_conda_xsh",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin/lib/python2.6/site-packages/xonsh/conda.xsh"
                    }
                },
                {
                    "function": "install_conda_csh",
                    "kwargs": {
                        "conda_prefix": "/darwin",
                        "target_path": "/darwin/etc/profile.d/conda.csh"
                    }
                }
            ]


def test_make_initialize_plan_bash_zsh():
    with tempdir() as conda_temp_prefix:
        plan = make_initialize_plan(conda_temp_prefix, ('bash', 'zsh'), for_user=True,
                                    for_system=True, anaconda_prompt=False)
        steps = tuple(step for step in plan if step['function'] == 'init_sh_user')
        assert len(steps) == 2
        steps = tuple(step for step in plan if step['function'] == 'init_sh_system')
        assert len(steps) == 1


def test_make_initialize_plan_cmd_exe():
    with tempdir() as conda_temp_prefix:
        plan = make_initialize_plan(conda_temp_prefix, ('cmd.exe',), for_user=True,
                                    for_system=True, anaconda_prompt=True)
        steps = tuple(step for step in plan if step['function'] == 'init_cmd_exe_registry')
        assert len(steps) == 2
        steps = tuple(step for step in plan if step['function'] == 'install_anaconda_prompt')
        assert len(steps) == 2


def test_make_entry_point():
    with tempdir() as conda_temp_prefix:
        conda_prefix = abspath(sys.prefix)
        if on_win:
            conda_exe_path = join(conda_temp_prefix, 'Scripts', 'conda-script.py')
        else:
            conda_exe_path = join(conda_temp_prefix, 'bin', 'conda')
        result = make_entry_point(conda_exe_path, conda_prefix, 'conda.entry.point', 'run')
        assert result == Result.MODIFIED

        with open(conda_exe_path) as fh:
            ep_contents = fh.read()

        if on_win:
            assert ep_contents == dals("""
            # -*- coding: utf-8 -*-
            import sys

            if __name__ == '__main__':
                from conda.entry.point import run
                sys.exit(run())
            """)
        else:
            assert ep_contents == dals("""
            #!%s/bin/python
            # -*- coding: utf-8 -*-
            import sys

            if __name__ == '__main__':
                from conda.entry.point import run
                sys.exit(run())
            """) % conda_prefix

        result = make_entry_point(conda_exe_path, conda_prefix, 'conda.entry.point', 'run')
        assert result == Result.NO_CHANGE


def test_make_entry_point_exe():
    with tempdir() as conda_temp_prefix:
        conda_prefix = abspath(sys.prefix)
        target_path = join(conda_temp_prefix, 'Scripts', 'conda-env.exe')
        result = make_entry_point_exe(target_path, conda_prefix)
        assert result == Result.MODIFIED

        assert isfile(target_path)

        result = make_entry_point_exe(target_path, conda_prefix)
        assert result == Result.NO_CHANGE


def test_install_conda_sh():
    with tempdir() as conda_prefix:
        target_path = join(conda_prefix, 'etc', 'profile.d', 'conda.sh')
        result = install_conda_sh(target_path, conda_prefix)
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

        result = install_conda_sh(target_path, conda_prefix)
        assert result == Result.NO_CHANGE


def test_install_conda_fish():
    with tempdir() as conda_temp_prefix:
        conda_prefix = abspath(sys.prefix)
        target_path = join(conda_temp_prefix, 'etc', 'fish', 'conf.d', 'conda.fish')
        result = install_conda_fish(target_path, conda_prefix)
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

        result = install_conda_fish(target_path, conda_prefix)
        assert result == Result.NO_CHANGE


def test_install_conda_xsh():
    with tempdir() as conda_temp_prefix:
        conda_prefix = abspath(sys.prefix)
        target_path = join(conda_temp_prefix, 'Lib', 'site-packages', 'conda.xsh')
        result = install_conda_xsh(target_path, conda_prefix)
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

        result = install_conda_xsh(target_path, conda_prefix)
        assert result == Result.NO_CHANGE


def test_install_conda_csh():
    with tempdir() as conda_temp_prefix:
        conda_prefix = abspath(sys.prefix)
        target_path = join(conda_temp_prefix, 'etc', 'profile.d', 'conda.csh')
        result = install_conda_csh(target_path, conda_prefix)
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

        result = install_conda_csh(target_path, conda_prefix)
        assert result == Result.NO_CHANGE


def test_install_conda_bat():
    with tempdir() as conda_temp_prefix:
        conda_prefix = abspath(sys.prefix)
        target_path = join(conda_temp_prefix, 'Library', 'bin', 'conda.bat')
        result = install_conda_bat(target_path, conda_prefix)
        assert result == Result.MODIFIED

        with open(target_path) as fh:
            created_file_contents = fh.read()

        first_line, remainder = created_file_contents.split('\n', 1)
        assert first_line == '@SET "_CONDA_EXE=%s"' % join(conda_prefix, 'Scripts', 'conda.exe')

        with open(join(CONDA_PACKAGE_ROOT, 'shell', 'Library', 'bin', 'conda.bat')) as fh:
            original_contents = fh.read()
        assert remainder == original_contents

        result = install_conda_bat(target_path, conda_prefix)
        assert result == Result.NO_CHANGE


def test__get_python_info():
    python_exe, python_version, site_packages_dir = _get_python_info(sys.prefix)
    assert python_exe == sys.executable
    assert python_version == '%d.%d.%d' % sys.version_info[:3]
    assert site_packages_dir.endswith('site-packages')


def test_install_1():
    with env_var('CONDA_DRY_RUN', 'true', reset_context):
        with tempdir() as conda_temp_prefix:
            with captured() as c:
                install(conda_temp_prefix)

    assert "WARNING: Cannot install xonsh wrapper" in c.stderr
    if on_win:
        modified_files = (
            'conda.exe',
            'conda-env.exe',
            'conda-script.py',
            'conda-env-script.py',
            'conda.bat',
            'conda.bat',
            'conda-hook.bat',
            'activate.bat',
            'deactivate.bat',
            'activate',
            'deactivate',
            'conda.sh',
            'conda.fish',
            'conda.csh',
        )
    else:
        modified_files = (
            'conda',
            'conda-env',
            'activate',
            'deactivate',
            'conda.sh',
            'conda.fish',
            'conda.csh',
        )

    print(c.stdout)
    print(c.stderr, file=sys.stderr)

    assert c.stdout.count('modified') == len(modified_files)
    stdout = "".join(s.strip('\n\r') for s in c.stdout.splitlines())
    for fn in modified_files:
        assert '%s  modified' % fn in stdout


def test_initialize_dev_bash():
    with pytest.raises(CondaValueError):
        initialize_dev('bash', conda_source_root=join('a', 'b', 'c'))

    with env_var('CONDA_DRY_RUN', 'true', reset_context):
        with tempdir() as conda_temp_prefix:
            new_py = join(conda_temp_prefix, get_python_short_path())
            mkdir_p(dirname(new_py))
            create_link(sys.executable, new_py, LinkType.hardlink)
            with captured() as c:
                initialize_dev('bash', dev_env_prefix=conda_temp_prefix)

    print(c.stdout)
    print(c.stderr, file=sys.stderr)

    if on_win:
        modified_files = (
            'conda.exe',
            'conda-env.exe',
            'conda-script.py',
            'conda-env-script.py',
            'conda.bat',
            'conda.bat',
            'conda-hook.bat',
            'activate.bat',
            'deactivate.bat',
            'activate',
            'deactivate',
            'conda.sh',
            'conda.fish',
            'conda.xsh',
            'conda.csh',
            'site-packages',
            'conda-dev.pth',
        )
    else:
        modified_files = (
            'conda',
            'conda-env',
            'activate',
            'deactivate',
            'conda.sh',
            'conda.fish',
            'conda.xsh',
            'conda.csh',
            'site-packages',  # remove conda in site-packages dir
            'conda-dev.pth',
        )

    stderr = c.stderr.replace('no change', 'modified')
    assert stderr.count('modified') == len(modified_files)

    stderr = "".join(s.strip('\n\r') for s in stderr.splitlines())
    for fn in modified_files:
        assert '%s  modified' % fn in stderr

    assert "unset CONDA_SHLVL" in c.stdout


def test_initialize_dev_cmd_exe():
    with env_var('CONDA_DRY_RUN', 'true', reset_context):
        with tempdir() as conda_temp_prefix:
            new_py = join(conda_temp_prefix, get_python_short_path())
            mkdir_p(dirname(new_py))
            create_link(sys.executable, new_py, LinkType.hardlink)
            with captured() as c:
                initialize_dev('cmd.exe', dev_env_prefix=conda_temp_prefix)

    print(c.stdout)
    print(c.stderr, file=sys.stderr)

    if on_win:
        modified_files = (
            'conda.exe',
            'conda-env.exe',
            'conda-script.py',
            'conda-env-script.py',
            'conda.bat',
            'conda.bat',
            'conda-hook.bat',
            'activate.bat',
            'deactivate.bat',
            'activate',
            'deactivate',
            'conda.sh',
            'conda.fish',
            'conda.xsh',
            'conda.csh',
            'site-packages',
            'conda-dev.pth',
        )
    else:
        modified_files = (
            'conda',
            'conda-env',
            'activate',
            'deactivate',
            'conda.sh',
            'conda.fish',
            'conda.xsh',
            'conda.csh',
            'site-packages',  # remove conda in site-packages dir
            'conda-dev.pth',
        )

    stderr = c.stderr.replace('no change', 'modified')
    assert stderr.count('modified') == len(modified_files)

    stderr = "".join(s.strip('\n\r') for s in stderr.splitlines())
    for fn in modified_files:
        assert '%s  modified' % fn in stderr

