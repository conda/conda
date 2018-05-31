# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
import os
from os.path import basename, dirname, isdir, join
import sys
from tempfile import gettempdir
from unittest import TestCase
from uuid import uuid4

import pytest

from conda import CONDA_PACKAGE_ROOT
from conda._vendor.auxlib.ish import dals
from conda._vendor.toolz.itertoolz import concatv
from conda.activate import Activator, main as activate_main, native_path_to_unix
from conda.base.constants import ROOT_ENV_NAME
from conda.base.context import context, reset_context
from conda.common.compat import iteritems, on_win, string_types
from conda.common.io import captured, env_var, env_vars
from conda.exceptions import EnvironmentLocationNotFound, EnvironmentNameNotFound
from conda.gateways.disk.create import mkdir_p
from conda.gateways.disk.delete import rm_rf
from conda.gateways.disk.update import touch
from tests.helpers import tempdir

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

log = getLogger(__name__)


if on_win:
    import ctypes
    PYTHONIOENCODING = ctypes.cdll.kernel32.GetACP()
else:
    PYTHONIOENCODING = None

POP_THESE = (
    'CONDA_SHLVL',
    'CONDA_DEFAULT_ENV',
    'CONDA_PREFIX',
    'CONDA_PREFIX_0',
    'CONDA_PREFIX_1',
    'CONDA_PREFIX_2',
    'PS1',
    'prompt',
)


class ActivatorUnitTests(TestCase):

    def setUp(self):
        self.hold_environ = os.environ.copy()
        for var in POP_THESE:
            os.environ.pop(var, None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.hold_environ)

    def test_activate_environment_not_found(self):
        activator = Activator('posix')

        with tempdir() as td:
            with pytest.raises(EnvironmentLocationNotFound):
                activator.build_activate(td)

        with pytest.raises(EnvironmentLocationNotFound):
            activator.build_activate('/not/an/environment')

        with pytest.raises(EnvironmentNameNotFound):
            activator.build_activate('wontfindmeIdontexist_abc123')

    def test_wrong_args(self):
        pass

    def test_activate_help(self):
        pass

    def test_PS1(self):
        with env_var("CONDA_CHANGEPS1", "yes", reset_context):
            activator = Activator('posix')
            assert activator._prompt_modifier(ROOT_ENV_NAME) == '(%s) ' % ROOT_ENV_NAME

            instructions = activator.build_activate("base")
            assert instructions['export_vars']['CONDA_PROMPT_MODIFIER'] == '(%s) ' % ROOT_ENV_NAME

    def test_PS1_no_changeps1(self):
        with env_var("CONDA_CHANGEPS1", "no", reset_context):
            activator = Activator('posix')
            assert activator._prompt_modifier('root') == ''

            instructions = activator.build_activate("base")
            assert instructions['export_vars']['CONDA_PROMPT_MODIFIER'] == ''

    def test_add_prefix_to_path(self):
        activator = Activator('posix')

        path_dirs = activator.path_conversion(['/path1/bin', '/path2/bin', '/usr/local/bin', '/usr/bin', '/bin'])
        assert len(path_dirs) == 5
        test_prefix = '/usr/mytest/prefix'
        added_paths = activator.path_conversion(activator._get_path_dirs(test_prefix))
        if isinstance(added_paths, string_types):
            added_paths = added_paths,

        new_path = activator._add_prefix_to_path(test_prefix, path_dirs)
        assert new_path == added_paths + path_dirs

    def test_remove_prefix_from_path_1(self):
        activator = Activator('posix')
        original_path = tuple(activator._get_starting_path_list())
        keep_path = activator.path_conversion('/keep/this/path')
        final_path = (keep_path,) + original_path
        final_path = activator.path_conversion(final_path)

        test_prefix = join(os.getcwd(), 'mytestpath')
        new_paths = tuple(activator._get_path_dirs(test_prefix))
        prefix_added_path = (keep_path,) + new_paths + original_path
        new_path = activator._remove_prefix_from_path(test_prefix, prefix_added_path)
        assert final_path == new_path

    def test_remove_prefix_from_path_2(self):
        # this time prefix doesn't actually exist in path
        activator = Activator('posix')
        original_path = tuple(activator._get_starting_path_list())
        keep_path = activator.path_conversion('/keep/this/path')
        final_path = (keep_path,) + original_path
        final_path = activator.path_conversion(final_path)

        test_prefix = join(os.getcwd(), 'mytestpath')
        prefix_added_path = (keep_path,) + original_path
        new_path = activator._remove_prefix_from_path(test_prefix, prefix_added_path)

        assert final_path == new_path

    def test_replace_prefix_in_path_1(self):
        activator = Activator('posix')
        original_path = tuple(activator._get_starting_path_list())
        new_prefix = join(os.getcwd(), 'mytestpath-new')
        new_paths = activator.path_conversion(activator._get_path_dirs(new_prefix))
        if isinstance(new_paths, string_types):
            new_paths = new_paths,
        keep_path = activator.path_conversion('/keep/this/path')
        final_path = (keep_path,) + new_paths + original_path
        final_path = activator.path_conversion(final_path)

        replace_prefix = join(os.getcwd(), 'mytestpath')
        replace_paths = tuple(activator._get_path_dirs(replace_prefix))
        prefix_added_path = (keep_path,) + replace_paths + original_path
        new_path = activator._replace_prefix_in_path(replace_prefix, new_prefix, prefix_added_path)

        assert final_path == new_path

    def test_default_env(self):
        activator = Activator('posix')
        assert ROOT_ENV_NAME == activator._default_env(context.root_prefix)

        with tempdir() as td:
            assert td == activator._default_env(td)

            p = mkdir_p(join(td, 'envs', 'named-env'))
            assert 'named-env' == activator._default_env(p)

    def test_build_activate_shlvl_0(self):
        with tempdir() as td:
            mkdir_p(join(td, 'conda-meta'))
            activate_d_dir = mkdir_p(join(td, 'etc', 'conda', 'activate.d'))
            activate_d_1 = join(activate_d_dir, 'see-me.sh')
            activate_d_2 = join(activate_d_dir, 'dont-see-me.bat')
            touch(join(activate_d_1))
            touch(join(activate_d_2))

            with env_var('CONDA_SHLVL', '0'):
                with env_var('CONDA_PREFIX', ''):
                    activator = Activator('posix')
                    builder = activator.build_activate(td)
                    new_path = activator.pathsep_join(activator._add_prefix_to_path(td))
                    conda_prompt_modifier = "(%s) " % td
                    ps1 = conda_prompt_modifier + os.environ.get('PS1', '')

                    assert builder['unset_vars'] == ()

                    set_vars = {
                        'PS1': ps1,
                    }
                    export_vars = {
                        'CONDA_PYTHON_EXE': activator.path_conversion(sys.executable),
                        'CONDA_EXE': activator.path_conversion(context.conda_exe),
                        'PATH': new_path,
                        'CONDA_PREFIX': td,
                        'CONDA_SHLVL': 1,
                        'CONDA_DEFAULT_ENV': td,
                        'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
                    }
                    assert builder['set_vars'] == set_vars
                    assert builder['export_vars'] == export_vars
                    assert builder['activate_scripts'] == (activator.path_conversion(activate_d_1),)
                    assert builder['deactivate_scripts'] == ()

    def test_build_activate_shlvl_1(self):
        with tempdir() as td:
            mkdir_p(join(td, 'conda-meta'))
            activate_d_dir = mkdir_p(join(td, 'etc', 'conda', 'activate.d'))
            activate_d_1 = join(activate_d_dir, 'see-me.sh')
            activate_d_2 = join(activate_d_dir, 'dont-see-me.bat')
            touch(join(activate_d_1))
            touch(join(activate_d_2))

            old_prefix = '/old/prefix'
            with env_var('CONDA_SHLVL', '1'):
                with env_var('CONDA_PREFIX', old_prefix):
                    activator = Activator('posix')
                    builder = activator.build_activate(td)
                    new_path = activator.pathsep_join(activator._add_prefix_to_path(td))
                    conda_prompt_modifier = "(%s) " % td
                    ps1 = conda_prompt_modifier + os.environ.get('PS1', '')

                    assert builder['unset_vars'] == ()

                    set_vars = {
                        'PS1': ps1,
                    }
                    export_vars = {
                        'PATH': new_path,
                        'CONDA_PREFIX': td,
                        'CONDA_PREFIX_1': old_prefix,
                        'CONDA_SHLVL': 2,
                        'CONDA_DEFAULT_ENV': td,
                        'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
                    }
                    assert builder['set_vars'] == set_vars
                    assert builder['export_vars'] == export_vars
                    assert builder['activate_scripts'] == (activator.path_conversion(activate_d_1),)
                    assert builder['deactivate_scripts'] == ()

    def test_build_activate_shlvl_2(self):
        with tempdir() as td:
            mkdir_p(join(td, 'conda-meta'))
            activate_d_dir = mkdir_p(join(td, 'etc', 'conda', 'activate.d'))
            activate_d_1 = join(activate_d_dir, 'see-me.sh')
            activate_d_2 = join(activate_d_dir, 'dont-see-me.bat')
            touch(join(activate_d_1))
            touch(join(activate_d_2))

            old_prefix = join(td, 'old')
            deactivate_d_dir = mkdir_p(join(old_prefix, 'etc', 'conda', 'deactivate.d'))
            deactivate_d_1 = join(deactivate_d_dir, 'see-me.sh')
            deactivate_d_2 = join(deactivate_d_dir, 'dont-see-me.bat')
            touch(join(deactivate_d_1))
            touch(join(deactivate_d_2))

            with env_var('CONDA_SHLVL', '2'):
                with env_var('CONDA_PREFIX', old_prefix):
                    activator = Activator('posix')
                    builder = activator.build_activate(td)
                    new_path = activator.pathsep_join(activator._add_prefix_to_path(td))
                    conda_prompt_modifier = "(%s) " % td
                    ps1 = conda_prompt_modifier + os.environ.get('PS1', '')

                    assert builder['unset_vars'] == ()

                    set_vars = {
                        'PS1': ps1,
                    }
                    export_vars = {
                        'PATH': new_path,
                        'CONDA_PREFIX': td,
                        'CONDA_DEFAULT_ENV': td,
                        'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
                    }
                    assert builder['set_vars'] == set_vars
                    assert builder['export_vars'] == export_vars
                    assert builder['activate_scripts'] == (activator.path_conversion(activate_d_1),)
                    assert builder['deactivate_scripts'] == (activator.path_conversion(deactivate_d_1),)

    def test_activate_same_environment(self):
        with tempdir() as td:
            mkdir_p(join(td, 'conda-meta'))
            activate_d_dir = mkdir_p(join(td, 'etc', 'conda', 'activate.d'))
            activate_d_1 = join(activate_d_dir, 'see-me.sh')
            activate_d_2 = join(activate_d_dir, 'dont-see-me.bat')
            touch(join(activate_d_1))
            touch(join(activate_d_2))

            old_prefix = td
            deactivate_d_dir = mkdir_p(join(old_prefix, 'etc', 'conda', 'deactivate.d'))
            deactivate_d_1 = join(deactivate_d_dir, 'see-me.sh')
            deactivate_d_2 = join(deactivate_d_dir, 'dont-see-me.bat')
            touch(join(deactivate_d_1))
            touch(join(deactivate_d_2))

            with env_var('CONDA_SHLVL', '1'):
                with env_var('CONDA_PREFIX', old_prefix):
                    activator = Activator('posix')

                    builder = activator.build_activate(td)

                    new_path_parts = activator._replace_prefix_in_path(old_prefix, old_prefix)
                    conda_prompt_modifier = "(%s) " % old_prefix
                    ps1 = conda_prompt_modifier + os.environ.get('PS1', '')

                    set_vars = {
                        'PS1': ps1,
                    }
                    export_vars = {
                        'PATH': activator.pathsep_join(new_path_parts),
                        'CONDA_PROMPT_MODIFIER': "(%s) " % td,
                        'CONDA_SHLVL': 1,
                    }
                    assert builder['unset_vars'] == ()
                    assert builder['set_vars'] == set_vars
                    assert builder['export_vars'] == export_vars
                    assert builder['activate_scripts'] == (activator.path_conversion(activate_d_1),)
                    assert builder['deactivate_scripts'] == (activator.path_conversion(deactivate_d_1),)

    def test_build_deactivate_shlvl_2(self):
        with tempdir() as td:
            mkdir_p(join(td, 'conda-meta'))
            deactivate_d_dir = mkdir_p(join(td, 'etc', 'conda', 'deactivate.d'))
            deactivate_d_1 = join(deactivate_d_dir, 'see-me-deactivate.sh')
            deactivate_d_2 = join(deactivate_d_dir, 'dont-see-me.bat')
            touch(join(deactivate_d_1))
            touch(join(deactivate_d_2))

            old_prefix = join(td, 'old')
            activate_d_dir = mkdir_p(join(old_prefix, 'etc', 'conda', 'activate.d'))
            activate_d_1 = join(activate_d_dir, 'see-me-activate.sh')
            activate_d_2 = join(activate_d_dir, 'dont-see-me.bat')
            touch(join(activate_d_1))
            touch(join(activate_d_2))

            with env_var('CONDA_SHLVL', '2'):
                with env_var('CONDA_PREFIX_1', old_prefix):
                    with env_var('CONDA_PREFIX', td):
                        activator = Activator('posix')
                        original_path = tuple(activator._get_starting_path_list())

                        builder = activator.build_deactivate()

                        assert builder['unset_vars'] == ('CONDA_PREFIX_1',)

                        new_path = activator.pathsep_join(activator.path_conversion(original_path))
                        conda_prompt_modifier = "(%s) " % old_prefix
                        ps1 = conda_prompt_modifier + os.environ.get('PS1', '')

                        set_vars = {
                            'PS1': ps1,
                        }
                        export_vars = {
                            'PATH': new_path,
                            'CONDA_SHLVL': 1,
                            'CONDA_PREFIX': old_prefix,
                            'CONDA_DEFAULT_ENV': old_prefix,
                            'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
                        }
                        assert builder['set_vars'] == set_vars
                        assert builder['export_vars'] == export_vars
                        assert builder['activate_scripts'] == (activator.path_conversion(activate_d_1),)
                        assert builder['deactivate_scripts'] == (activator.path_conversion(deactivate_d_1),)

    def test_build_deactivate_shlvl_1(self):
        with tempdir() as td:
            mkdir_p(join(td, 'conda-meta'))
            deactivate_d_dir = mkdir_p(join(td, 'etc', 'conda', 'deactivate.d'))
            deactivate_d_1 = join(deactivate_d_dir, 'see-me-deactivate.sh')
            deactivate_d_2 = join(deactivate_d_dir, 'dont-see-me.bat')
            touch(join(deactivate_d_1))
            touch(join(deactivate_d_2))

            with env_var('CONDA_SHLVL', '1'):
                with env_var('CONDA_PREFIX', td):
                    activator = Activator('posix')
                    original_path = tuple(activator._get_starting_path_list())
                    builder = activator.build_deactivate()

                    assert builder['unset_vars'] == (
                        'CONDA_PREFIX',
                        'CONDA_DEFAULT_ENV',
                        'CONDA_PYTHON_EXE',
                        'CONDA_EXE',
                        'CONDA_PROMPT_MODIFIER',
                    )

                    new_path = activator.pathsep_join(activator.path_conversion(original_path))
                    assert builder['set_vars'] == {
                        'PS1': os.environ.get('PS1', ''),
                    }
                    assert builder['export_vars'] == {
                        'PATH': new_path,
                        'CONDA_SHLVL': 0,
                    }
                    assert builder['activate_scripts'] == ()
                    assert builder['deactivate_scripts'] == (activator.path_conversion(deactivate_d_1),)


class ShellWrapperUnitTests(TestCase):

    def setUp(self):
        tempdirdir = gettempdir()

        prefix_dirname = str(uuid4())[:4] + ' ' + str(uuid4())[:4]
        self.prefix = join(tempdirdir, prefix_dirname)
        mkdir_p(join(self.prefix, 'conda-meta'))
        assert isdir(self.prefix)
        touch(join(self.prefix, 'conda-meta', 'history'))

        self.hold_environ = os.environ.copy()
        for var in POP_THESE:
            os.environ.pop(var, None)

    def tearDown(self):
        rm_rf(self.prefix)
        os.environ.clear()
        os.environ.update(self.hold_environ)

    def make_dot_d_files(self, extension):
        mkdir_p(join(self.prefix, 'etc', 'conda', 'activate.d'))
        mkdir_p(join(self.prefix, 'etc', 'conda', 'deactivate.d'))

        touch(join(self.prefix, 'etc', 'conda', 'activate.d', 'ignore.txt'))
        touch(join(self.prefix, 'etc', 'conda', 'deactivate.d', 'ignore.txt'))

        touch(join(self.prefix, 'etc', 'conda', 'activate.d', 'activate1' + extension))
        touch(join(self.prefix, 'etc', 'conda', 'deactivate.d', 'deactivate1' + extension))

    def test_native_path_to_unix(self):
        def assert_unix_path(path):
            assert '\\' not in path, path
            assert ':' not in path, path
            return True

        path1 = join(self.prefix, 'path', 'number', 'one')
        path2 = join(self.prefix, 'path', 'two')
        path3 = join(self.prefix, 'three')
        paths = (path1, path2, path3)

        if on_win:
            assert_unix_path(native_path_to_unix(path1))
        else:
            assert native_path_to_unix(path1) == path1

        if on_win:
            assert all(assert_unix_path(p) for p in native_path_to_unix(paths))
        else:
            assert native_path_to_unix(paths) == paths

    def test_posix_basic(self):
        activator = Activator('posix')
        self.make_dot_d_files(activator.script_extension)

        with captured() as c:
            rc = activate_main(('', 'shell.posix', 'activate', self.prefix))
        assert not c.stderr
        assert rc == 0
        activate_data = c.stdout

        new_path_parts = activator._add_prefix_to_path(self.prefix)
        assert activate_data == dals("""
        PS1='%(ps1)s'
        \\export CONDA_DEFAULT_ENV='%(native_prefix)s'
        \\export CONDA_EXE='%(conda_exe)s'
        \\export CONDA_PREFIX='%(native_prefix)s'
        \\export CONDA_PROMPT_MODIFIER='(%(native_prefix)s) '
        \\export CONDA_PYTHON_EXE='%(sys_executable)s'
        \\export CONDA_SHLVL='1'
        \\export PATH='%(new_path)s'
        \\. "%(activate1)s"
        """) % {
            'converted_prefix': activator.path_conversion(self.prefix),
            'native_prefix': self.prefix,
            'new_path': activator.pathsep_join(new_path_parts),
            'sys_executable': activator.path_conversion(sys.executable),
            'activate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'activate.d', 'activate1.sh')),
            'ps1': '(%s) ' % self.prefix + os.environ.get('PS1', ''),
            'conda_exe': activator.path_conversion(context.conda_exe),
        }

        with env_vars({
            'CONDA_PREFIX': self.prefix,
            'CONDA_SHLVL': '1',
            'PATH': os.pathsep.join(concatv(new_path_parts, (os.environ['PATH'],))),
        }):
            activator = Activator('posix')
            with captured() as c:
                rc = activate_main(('', 'shell.posix', 'reactivate'))
            assert not c.stderr
            assert rc == 0
            reactivate_data = c.stdout

            new_path_parts = activator._replace_prefix_in_path(self.prefix, self.prefix)
            assert reactivate_data == dals("""
            \\. "%(deactivate1)s"
            PS1='%(ps1)s'
            \\export CONDA_PROMPT_MODIFIER='(%(native_prefix)s) '
            \\export CONDA_SHLVL='1'
            \\export PATH='%(new_path)s'
            \\. "%(activate1)s"
            """) % {
                'activate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'activate.d', 'activate1.sh')),
                'deactivate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'deactivate.d', 'deactivate1.sh')),
                'native_prefix': self.prefix,
                'new_path': activator.pathsep_join(new_path_parts),
                'ps1': '(%s) ' % self.prefix + os.environ.get('PS1', ''),
            }

            with captured() as c:
                rc = activate_main(('', 'shell.posix', 'deactivate'))
            assert not c.stderr
            assert rc == 0
            deactivate_data = c.stdout

            new_path = activator.pathsep_join(activator._remove_prefix_from_path(self.prefix))
            assert deactivate_data == dals("""
            \\. "%(deactivate1)s"
            \\unset CONDA_DEFAULT_ENV
            \\unset CONDA_EXE
            \\unset CONDA_PREFIX
            \\unset CONDA_PROMPT_MODIFIER
            \\unset CONDA_PYTHON_EXE
            PS1='%(ps1)s'
            \\export CONDA_SHLVL='0'
            \\export PATH='%(new_path)s'
            """) % {
                'new_path': new_path,
                'deactivate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'deactivate.d', 'deactivate1.sh')),
                'ps1': os.environ.get('PS1', ''),
            }

    @pytest.mark.skipif(not on_win, reason="cmd.exe only on Windows")
    def test_cmd_exe_basic(self):
        activator = Activator('cmd.exe')
        self.make_dot_d_files(activator.script_extension)

        with captured() as c:
            rc = activate_main(('', 'shell.cmd.exe', 'activate', '', self.prefix))
        assert not c.stderr
        assert rc == 0
        activate_result = c.stdout

        with open(activate_result) as fh:
            activate_data = fh.read()
        rm_rf(activate_result)

        new_path_parts = activator._add_prefix_to_path(self.prefix)
        assert activate_data == dals("""
        @SET "CONDA_DEFAULT_ENV=%(native_prefix)s"
        @SET "CONDA_EXE=%(conda_exe)s"
        @SET "CONDA_PREFIX=%(converted_prefix)s"
        @SET "CONDA_PROMPT_MODIFIER=(%(native_prefix)s) "
        @SET "CONDA_PYTHON_EXE=%(sys_executable)s"
        @SET "CONDA_SHLVL=1"
        @SET "PATH=%(new_path)s"
        @SET "PYTHONIOENCODING=%(PYTHONIOENCODING)s"
        @CALL "%(activate1)s"
        """) % {
            'converted_prefix': activator.path_conversion(self.prefix),
            'native_prefix': self.prefix,
            'new_path': activator.pathsep_join(new_path_parts),
            'sys_executable': activator.path_conversion(sys.executable),
            'activate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'activate.d', 'activate1.bat')),
            'PYTHONIOENCODING': PYTHONIOENCODING,
            'conda_exe': activator.path_conversion(context.conda_exe),
        }

        with env_vars({
            'CONDA_PREFIX': self.prefix,
            'CONDA_SHLVL': '1',
            'PATH': os.pathsep.join(concatv(new_path_parts, (os.environ['PATH'],))),
        }):
            activator = Activator('cmd.exe')
            with captured() as c:
                assert activate_main(('', 'shell.cmd.exe', 'reactivate')) == 0
            assert not c.stderr
            reactivate_result = c.stdout

            with open(reactivate_result) as fh:
                reactivate_data = fh.read()
            rm_rf(reactivate_result)

            new_path_parts = activator._replace_prefix_in_path(self.prefix, self.prefix)
            assert reactivate_data == dals("""
            @CALL "%(deactivate1)s"
            @SET "CONDA_PROMPT_MODIFIER=(%(native_prefix)s) "
            @SET "CONDA_SHLVL=1"
            @SET "PATH=%(new_path)s"
            @CALL "%(activate1)s"
            """) % {
                'activate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'activate.d', 'activate1.bat')),
                'deactivate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'deactivate.d', 'deactivate1.bat')),
                'native_prefix': self.prefix,
                'new_path': activator.pathsep_join(new_path_parts),
            }

            with captured() as c:
                assert activate_main(('', 'shell.cmd.exe', 'deactivate')) == 0
            assert not c.stderr
            deactivate_result = c.stdout

            with open(deactivate_result) as fh:
                deactivate_data = fh.read()
            rm_rf(deactivate_result)

            new_path = activator.pathsep_join(activator._remove_prefix_from_path(self.prefix))
            assert deactivate_data == dals("""
            @CALL "%(deactivate1)s"
            @SET CONDA_DEFAULT_ENV=
            @SET CONDA_EXE=
            @SET CONDA_PREFIX=
            @SET CONDA_PROMPT_MODIFIER=
            @SET CONDA_PYTHON_EXE=
            @SET "CONDA_SHLVL=0"
            @SET "PATH=%(new_path)s"
            """) % {
                'new_path': new_path,
                'deactivate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'deactivate.d', 'deactivate1.bat')),
            }

    def test_csh_basic(self):
        activator = Activator('csh')
        self.make_dot_d_files(activator.script_extension)

        with captured() as c:
            rc = activate_main(('', 'shell.csh', 'activate', self.prefix))
        assert not c.stderr
        assert rc == 0
        activate_data = c.stdout

        new_path_parts = activator._add_prefix_to_path(self.prefix)
        assert activate_data == dals("""
        set prompt='%(prompt)s';
        setenv CONDA_DEFAULT_ENV "%(native_prefix)s";
        setenv CONDA_EXE "%(conda_exe)s";
        setenv CONDA_PREFIX "%(native_prefix)s";
        setenv CONDA_PROMPT_MODIFIER "(%(native_prefix)s) ";
        setenv CONDA_PYTHON_EXE "%(sys_executable)s";
        setenv CONDA_SHLVL "1";
        setenv PATH "%(new_path)s";
        source "%(activate1)s";
        """) % {
            'converted_prefix': activator.path_conversion(self.prefix),
            'native_prefix': self.prefix,
            'new_path': activator.pathsep_join(new_path_parts),
            'sys_executable': activator.path_conversion(sys.executable),
            'activate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'activate.d', 'activate1.csh')),
            'prompt': '(%s) ' % self.prefix + os.environ.get('prompt', ''),
            'conda_exe': activator.path_conversion(context.conda_exe),
        }

        with env_vars({
            'CONDA_PREFIX': self.prefix,
            'CONDA_SHLVL': '1',
            'PATH': os.pathsep.join(concatv(new_path_parts, (os.environ['PATH'],))),
        }):
            activator = Activator('csh')
            with captured() as c:
                rc = activate_main(('', 'shell.csh', 'reactivate'))
            assert not c.stderr
            assert rc == 0
            reactivate_data = c.stdout

            new_path_parts = activator._replace_prefix_in_path(self.prefix, self.prefix)
            assert reactivate_data == dals("""
            source "%(deactivate1)s";
            set prompt='%(prompt)s';
            setenv CONDA_PROMPT_MODIFIER "(%(native_prefix)s) ";
            setenv CONDA_SHLVL "1";
            setenv PATH "%(new_path)s";
            source "%(activate1)s";
            """) % {
                'prompt': '(%s) ' % self.prefix + os.environ.get('prompt', ''),
                'new_path': activator.pathsep_join(new_path_parts),
                'activate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'activate.d', 'activate1.csh')),
                'deactivate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'deactivate.d', 'deactivate1.csh')),
                'native_prefix': self.prefix,
            }

            with captured() as c:
                rc = activate_main(('', 'shell.csh', 'deactivate'))
            assert not c.stderr
            assert rc == 0
            deactivate_data = c.stdout

            new_path = activator.pathsep_join(activator._remove_prefix_from_path(self.prefix))
            assert deactivate_data == dals("""
            source "%(deactivate1)s";
            unsetenv CONDA_DEFAULT_ENV;
            unsetenv CONDA_EXE;
            unsetenv CONDA_PREFIX;
            unsetenv CONDA_PROMPT_MODIFIER;
            unsetenv CONDA_PYTHON_EXE;
            set prompt='%(prompt)s';
            setenv CONDA_SHLVL "0";
            setenv PATH "%(new_path)s";
            """) % {
                'new_path': new_path,
                'deactivate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'deactivate.d', 'deactivate1.csh')),
                'prompt': os.environ.get('prompt', ''),
            }

    def test_xonsh_basic(self):
        activator = Activator('xonsh')
        self.make_dot_d_files(activator.script_extension)

        with captured() as c:
            rc = activate_main(('', 'shell.xonsh', 'activate', self.prefix))
        assert not c.stderr
        assert rc == 0
        activate_result = c.stdout

        with open(activate_result) as fh:
            activate_data = fh.read()
        rm_rf(activate_result)

        new_path_parts = activator._add_prefix_to_path(self.prefix)
        assert activate_data == dals("""
        $CONDA_DEFAULT_ENV = '%(native_prefix)s'
        $CONDA_EXE = '%(conda_exe)s'
        $CONDA_PREFIX = '%(native_prefix)s'
        $CONDA_PROMPT_MODIFIER = '(%(native_prefix)s) '
        $CONDA_PYTHON_EXE = '%(sys_executable)s'
        $CONDA_SHLVL = '1'
        $PATH = '%(new_path)s'
        source "%(activate1)s"
        """) % {
            'converted_prefix': activator.path_conversion(self.prefix),
            'native_prefix': self.prefix,
            'new_path': activator.pathsep_join(new_path_parts),
            'sys_executable': activator.path_conversion(sys.executable),
            'activate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'activate.d', 'activate1.xsh')),
            'conda_exe': activator.path_conversion(context.conda_exe),
        }

        with env_vars({
            'CONDA_PREFIX': self.prefix,
            'CONDA_SHLVL': '1',
            'PATH': os.pathsep.join(concatv(new_path_parts, (os.environ['PATH'],))),
        }):
            activator = Activator('xonsh')
            with captured() as c:
                assert activate_main(('', 'shell.xonsh', 'reactivate')) == 0
            assert not c.stderr
            reactivate_result = c.stdout

            with open(reactivate_result) as fh:
                reactivate_data = fh.read()
            rm_rf(reactivate_result)

            new_path_parts = activator._replace_prefix_in_path(self.prefix, self.prefix)
            assert reactivate_data == dals("""
            source "%(deactivate1)s"
            $CONDA_PROMPT_MODIFIER = '(%(native_prefix)s) '
            $CONDA_SHLVL = '1'
            $PATH = '%(new_path)s'
            source "%(activate1)s"
            """) % {
                'activate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'activate.d', 'activate1.xsh')),
                'deactivate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'deactivate.d', 'deactivate1.xsh')),
                'native_prefix': self.prefix,
                'new_path': activator.pathsep_join(new_path_parts),
            }

            with captured() as c:
                assert activate_main(('', 'shell.xonsh', 'deactivate')) == 0
            assert not c.stderr
            deactivate_result = c.stdout

            with open(deactivate_result) as fh:
                deactivate_data = fh.read()
            rm_rf(deactivate_result)

            new_path = activator.pathsep_join(activator._remove_prefix_from_path(self.prefix))
            assert deactivate_data == dals("""
            source "%(deactivate1)s"
            del $CONDA_DEFAULT_ENV
            del $CONDA_EXE
            del $CONDA_PREFIX
            del $CONDA_PROMPT_MODIFIER
            del $CONDA_PYTHON_EXE
            $CONDA_SHLVL = '0'
            $PATH = '%(new_path)s'
            """) % {
                'new_path': new_path,
                'deactivate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'deactivate.d', 'deactivate1.xsh')),
            }

    def test_fish_basic(self):
        activator = Activator('fish')
        self.make_dot_d_files(activator.script_extension)

        with captured() as c:
            rc = activate_main(('', 'shell.fish', 'activate', self.prefix))
        assert not c.stderr
        assert rc == 0
        activate_data = c.stdout

        new_path_parts = activator._add_prefix_to_path(self.prefix)
        assert activate_data == dals("""
        set -gx CONDA_DEFAULT_ENV "%(native_prefix)s";
        set -gx CONDA_EXE "%(conda_exe)s";
        set -gx CONDA_PREFIX "%(native_prefix)s";
        set -gx CONDA_PROMPT_MODIFIER "(%(native_prefix)s) ";
        set -gx CONDA_PYTHON_EXE "%(sys_executable)s";
        set -gx CONDA_SHLVL "1";
        set -gx PATH "%(new_path)s";
        source "%(activate1)s";
        """) % {
            'converted_prefix': activator.path_conversion(self.prefix),
            'native_prefix': self.prefix,
            'new_path': activator.pathsep_join(new_path_parts),
            'sys_executable': activator.path_conversion(sys.executable),
            'activate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'activate.d', 'activate1.fish')),
            'conda_exe': activator.path_conversion(context.conda_exe),
        }

        with env_vars({
            'CONDA_PREFIX': self.prefix,
            'CONDA_SHLVL': '1',
            'PATH': os.pathsep.join(concatv(new_path_parts, (os.environ['PATH'],))),
        }):
            activator = Activator('fish')
            with captured() as c:
                rc = activate_main(('', 'shell.fish', 'reactivate'))
            assert not c.stderr
            assert rc == 0
            reactivate_data = c.stdout

            new_path_parts = activator._replace_prefix_in_path(self.prefix, self.prefix)
            assert reactivate_data == dals("""
            source "%(deactivate1)s";
            set -gx CONDA_PROMPT_MODIFIER "(%(native_prefix)s) ";
            set -gx CONDA_SHLVL "1";
            set -gx PATH "%(new_path)s";
            source "%(activate1)s";
            """) % {
                'new_path': activator.pathsep_join(new_path_parts),
                'activate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'activate.d', 'activate1.fish')),
                'deactivate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'deactivate.d', 'deactivate1.fish')),
                'native_prefix': self.prefix,
            }

            with captured() as c:
                rc = activate_main(('', 'shell.fish', 'deactivate'))
            assert not c.stderr
            assert rc == 0
            deactivate_data = c.stdout

            new_path = activator.pathsep_join(activator._remove_prefix_from_path(self.prefix))
            assert deactivate_data == dals("""
            source "%(deactivate1)s";
            set -e CONDA_DEFAULT_ENV;
            set -e CONDA_EXE;
            set -e CONDA_PREFIX;
            set -e CONDA_PROMPT_MODIFIER;
            set -e CONDA_PYTHON_EXE;
            set -gx CONDA_SHLVL "0";
            set -gx PATH "%(new_path)s";
            """) % {
                'new_path': new_path,
                'deactivate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'deactivate.d', 'deactivate1.fish')),

            }

    def test_powershell_basic(self):
        activator = Activator('powershell')
        self.make_dot_d_files(activator.script_extension)

        with captured() as c:
            rc = activate_main(('', 'shell.powershell', 'activate', self.prefix))
        assert not c.stderr
        assert rc == 0
        activate_data = c.stdout

        new_path_parts = activator._add_prefix_to_path(self.prefix)
        assert activate_data == dals("""
        $env:CONDA_DEFAULT_ENV = "%(prefix)s"
        $env:CONDA_EXE = "%(conda_exe)s"
        $env:CONDA_PREFIX = "%(prefix)s"
        $env:CONDA_PROMPT_MODIFIER = "(%(prefix)s) "
        $env:CONDA_PYTHON_EXE = "%(sys_executable)s"
        $env:CONDA_SHLVL = "1"
        $env:PATH = "%(new_path)s"
        . "%(activate1)s"
        """) % {
            'prefix': self.prefix,
            'new_path': activator.pathsep_join(new_path_parts),
            'sys_executable': sys.executable,
            'activate1': join(self.prefix, 'etc', 'conda', 'activate.d', 'activate1.ps1'),
            'conda_exe': context.conda_exe,
        }

        with env_vars({
            'CONDA_PREFIX': self.prefix,
            'CONDA_SHLVL': '1',
            'PATH': os.pathsep.join(concatv(new_path_parts, (os.environ['PATH'],))),
        }):
            activator = Activator('powershell')
            with captured() as c:
                rc = activate_main(('', 'shell.powershell', 'reactivate'))
            assert not c.stderr
            assert rc == 0
            reactivate_data = c.stdout

            new_path_parts = activator._replace_prefix_in_path(self.prefix, self.prefix)
            assert reactivate_data == dals("""
            . "%(deactivate1)s"
            $env:CONDA_PROMPT_MODIFIER = "(%(prefix)s) "
            $env:CONDA_SHLVL = "1"
            $env:PATH = "%(new_path)s"
            . "%(activate1)s"
            """) % {
                'activate1': join(self.prefix, 'etc', 'conda', 'activate.d', 'activate1.ps1'),
                'deactivate1': join(self.prefix, 'etc', 'conda', 'deactivate.d', 'deactivate1.ps1'),
                'prefix': self.prefix,
                'new_path': activator.pathsep_join(new_path_parts),
            }

            with captured() as c:
                rc = activate_main(('', 'shell.powershell', 'deactivate'))
            assert not c.stderr
            assert rc == 0
            deactivate_data = c.stdout

            new_path = activator.pathsep_join(activator._remove_prefix_from_path(self.prefix))
            assert deactivate_data == dals("""
            . "%(deactivate1)s"
            Remove-Variable CONDA_DEFAULT_ENV
            Remove-Variable CONDA_EXE
            Remove-Variable CONDA_PREFIX
            Remove-Variable CONDA_PROMPT_MODIFIER
            Remove-Variable CONDA_PYTHON_EXE
            $env:CONDA_SHLVL = "0"
            $env:PATH = "%(new_path)s"
            """) % {
                'new_path': new_path,
                'deactivate1': join(self.prefix, 'etc', 'conda', 'deactivate.d', 'deactivate1.ps1'),

            }

    def test_unicode(self):
        shell = 'shell.posix'
        prompt = 'PS1'
        prompt_value = u'%{\xc2\xbb'.encode(sys.getfilesystemencoding())
        with env_vars({prompt: prompt_value}):
            # use a file as output stream to simulate PY2 default stdout
            with tempdir() as td:
                with open(join(td, "stdout"), "wt") as stdout:
                    with captured(stdout=stdout) as c:
                        rc = activate_main(('', shell, 'activate', self.prefix))


class InteractiveShell(object):
    activator = None
    init_command = None
    print_env_var = None
    shells = {
        'posix': {
            'activator': 'posix',
            'init_command': 'set -u && . conda/shell/etc/profile.d/conda.sh',
            'print_env_var': 'echo "$%s"',
        },
        'bash': {
            'base_shell': 'posix',  # inheritance implemented in __init__
        },
        'dash': {
            'base_shell': 'posix',  # inheritance implemented in __init__
        },
        'zsh': {
            'base_shell': 'posix',  # inheritance implemented in __init__
        },
        'cmd.exe': {
            'activator': 'cmd.exe',
            'init_command': None,
            'print_env_var': '@echo %%%s%%',
        },
        'csh': {
            'activator': 'csh',
            'init_command': 'source conda/shell/etc/profile.d/conda.csh',
            'print_env_var': 'echo "$%s"',
        },
        'tcsh': {
            'base_shell': 'csh',
        },
        'fish': {
            'activator': 'fish',
            'init_command': 'source shell/etc/fish/conf.d/conda.fish',
            'print_env_var': 'echo $%s',
        },
    }

    def __init__(self, shell_name):
        self.shell_name = shell_name
        base_shell = self.shells[shell_name].get('base_shell')
        shell_vals = self.shells.get(base_shell, {})
        shell_vals.update(self.shells[shell_name])
        for key, value in iteritems(shell_vals):
            setattr(self, key, value)
        self.activator = Activator(shell_vals['activator'])

    def __enter__(self):
        from pexpect.popen_spawn import PopenSpawn

        cwd = os.getcwd()
        env = os.environ.copy()
        joiner = os.pathsep.join if self.shell_name == 'fish' else self.activator.pathsep_join
        env['PATH'] = joiner(self.activator.path_conversion(concatv(
            self.activator._get_path_dirs(join(cwd, 'conda', 'shell')),
            (dirname(sys.executable),),
            self.activator._get_starting_path_list(),
        )))
        env['PYTHONPATH'] = CONDA_PACKAGE_ROOT
        env = {str(k): str(v) for k, v in iteritems(env)}

        p = PopenSpawn(self.shell_name, timeout=6, maxread=2000, searchwindowsize=None,
                       logfile=sys.stdout, cwd=cwd, env=env, encoding=None,
                       codec_errors='strict')
        if self.init_command:
            p.sendline(self.init_command)
        self.p = p
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.p:
            import signal
            self.p.kill(signal.SIGINT)

    def sendline(self, s):
        return self.p.sendline(s)

    def expect(self, pattern, timeout=-1, searchwindowsize=-1, async=False):
        return self.p.expect(pattern, timeout, searchwindowsize, async)

    def assert_env_var(self, env_var, value, use_exact=False):
        # value is actually a regex
        self.sendline(self.print_env_var % env_var)
        try:
            if use_exact:
                self.p.expect_exact(value)
                self.expect('.*\n')
            else:
                self.expect('%s\n' % value)
        except:
            print(self.p.before)
            print(self.p.after)
            raise


def which(executable):
    from distutils.spawn import find_executable
    return find_executable(executable)


@pytest.mark.integration
class ShellWrapperIntegrationTests(TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            mkdir_p(join(sys.prefix, 'conda-meta'))
            touch(join(sys.prefix, 'conda-meta', 'history'))
        except Exception:
            pass

    def setUp(self):
        tempdirdir = gettempdir()

        prefix_dirname = str(uuid4())[:4] + ' ' + str(uuid4())[:4]
        self.prefix = join(tempdirdir, prefix_dirname)
        mkdir_p(join(self.prefix, 'conda-meta'))
        assert isdir(self.prefix)
        touch(join(self.prefix, 'conda-meta', 'history'))

        mkdir_p(join(self.prefix, 'envs', 'charizard', 'conda-meta'))
        touch(join(self.prefix, 'envs', 'charizard', 'conda-meta', 'history'))

    def tearDown(self):
        rm_rf(self.prefix)

    def basic_posix(self, shell):
        shell.assert_env_var('CONDA_SHLVL', '0')
        shell.sendline('conda activate base')
        shell.assert_env_var('PS1', '(base).*')
        shell.assert_env_var('CONDA_SHLVL', '1')
        shell.sendline('conda activate "%s"' % self.prefix)
        shell.assert_env_var('CONDA_SHLVL', '2')
        shell.assert_env_var('CONDA_PREFIX', self.prefix, True)

        shell.sendline('conda install -yq sqlite openssl')  # TODO: this should be a relatively light package, but also one that has activate.d or deactivate.d scripts
        shell.expect('Executing transaction: ...working... done.*\n', timeout=35)
        shell.assert_env_var('?', '0', True)
        # TODO: assert that reactivate worked correctly

        # regression test for #6840
        shell.sendline('conda install --blah')
        shell.assert_env_var('?', '2', use_exact=True)
        shell.sendline('conda list --blah')
        shell.assert_env_var('?', '2', use_exact=True)

        shell.sendline('conda deactivate')
        shell.assert_env_var('CONDA_SHLVL', '1')
        shell.sendline('conda deactivate')
        shell.assert_env_var('CONDA_SHLVL', '0')

        shell.sendline(shell.print_env_var % 'PS1')
        shell.expect('.*\n')
        assert 'CONDA_PROMPT_MODIFIER' not in str(shell.p.after)

        shell.sendline('conda deactivate')
        shell.assert_env_var('CONDA_SHLVL', '0')

    @pytest.mark.skipif(not which('bash'), reason='bash not installed')
    def test_bash_basic_integration(self):
        with InteractiveShell('bash') as shell:
            self.basic_posix(shell)

    @pytest.mark.skipif(not which('dash') or on_win, reason='dash not installed')
    def test_dash_basic_integration(self):
        with InteractiveShell('dash') as shell:
            shell.sendline('env | sort')
            self.basic_posix(shell)

    @pytest.mark.skipif(not which('zsh'), reason='zsh not installed')
    def test_zsh_basic_integration(self):
        with InteractiveShell('zsh') as shell:
            self.basic_posix(shell)

    def basic_csh(self, shell):
        shell.assert_env_var('CONDA_SHLVL', '0')
        shell.sendline('conda activate base')
        shell.assert_env_var('prompt', '(base).*')
        shell.assert_env_var('CONDA_SHLVL', '1')
        shell.sendline('conda activate "%s"' % self.prefix)
        shell.assert_env_var('CONDA_SHLVL', '2')
        shell.assert_env_var('CONDA_PREFIX', self.prefix, True)
        shell.sendline('conda deactivate')
        shell.assert_env_var('CONDA_SHLVL', '1')
        shell.sendline('conda deactivate')
        shell.assert_env_var('CONDA_SHLVL', '0')

        assert 'CONDA_PROMPT_MODIFIER' not in str(shell.p.after)

        shell.sendline('conda deactivate')
        shell.assert_env_var('CONDA_SHLVL', '0')

    @pytest.mark.skipif(not which('csh'), reason='csh not installed')
    @pytest.mark.xfail(reason="pure csh doesn't support argument passing to sourced scripts")
    def test_csh_basic_integration(self):
        with InteractiveShell('csh') as shell:
            self.basic_csh(shell)

    @pytest.mark.skipif(not which('tcsh'), reason='tcsh not installed')
    def test_tcsh_basic_integration(self):
        with InteractiveShell('tcsh') as shell:
            self.basic_csh(shell)

    @pytest.mark.skipif(not which('fish'), reason='fish not installed')
    @pytest.mark.xfail(reason="fish and pexpect don't seem to work together?")
    def test_fish_basic_integration(self):
        with InteractiveShell('fish') as shell:
            shell.sendline('env | sort')
            # We should be seeing environment variable output to terminal with this line, but
            # we aren't.  Haven't experienced this problem yet with any other shell...

            shell.assert_env_var('CONDA_SHLVL', '0')
            shell.sendline('conda activate base')
            shell.assert_env_var('CONDA_SHLVL', '1')
            shell.sendline('conda activate "%s"' % self.prefix)
            shell.assert_env_var('CONDA_SHLVL', '2')
            shell.assert_env_var('CONDA_PREFIX', self.prefix, True)
            shell.sendline('conda deactivate')
            shell.assert_env_var('CONDA_SHLVL', '1')
            shell.sendline('conda deactivate')
            shell.assert_env_var('CONDA_SHLVL', '0')

            shell.sendline(shell.print_env_var % 'PS1')
            shell.expect('.*\n')
            assert 'CONDA_PROMPT_MODIFIER' not in str(shell.p.after)

            shell.sendline('conda deactivate')
            shell.assert_env_var('CONDA_SHLVL', '0')

    @pytest.mark.skipif(not which('cmd.exe'), reason='cmd.exe not installed')
    def test_cmd_exe_basic_integration(self):
        charizard = join(self.prefix, 'envs', 'charizard')
        with InteractiveShell('cmd.exe') as shell:
            shell.sendline('where conda')
            shell.p.expect_exact('conda.bat')
            shell.expect('.*\n')
            shell.sendline('conda activate "%s"' % charizard)
            shell.assert_env_var('CONDA_SHLVL', '1\r')
            shell.sendline('conda activate "%s"' % self.prefix)
            shell.assert_env_var('CONDA_SHLVL', '2\r')
            shell.assert_env_var('CONDA_PREFIX', self.prefix, True)

            shell.sendline('conda install -yq sqlite openssl')  # TODO: this should be a relatively light package, but also one that has activate.d or deactivate.d scripts
            shell.expect('Executing transaction: ...working... done.*\n', timeout=25)
            shell.assert_env_var('errorlevel', '0', True)
            # TODO: assert that reactivate worked correctly

            shell.sendline('conda deactivate')
            shell.assert_env_var('CONDA_SHLVL', '1\r')
            shell.sendline('conda deactivate')
            shell.assert_env_var('CONDA_SHLVL', '0\r')
            shell.sendline('conda deactivate')
            shell.assert_env_var('CONDA_SHLVL', '0\r')

    @pytest.mark.skipif(not which('bash'), reason='bash not installed')
    def test_bash_activate_error(self):
        with InteractiveShell('bash') as shell:
            shell.sendline("conda activate environment-not-found-doesnt-exist")
            shell.expect('Could not find conda environment: environment-not-found-doesnt-exist')
            shell.assert_env_var('CONDA_SHLVL', '0')

            shell.sendline("conda activate -h blah blah")
            shell.expect('help requested for activate')

    @pytest.mark.skipif(not which('cmd.exe'), reason='cmd.exe not installed')
    def test_cmd_exe_activate_error(self):
        with InteractiveShell('cmd.exe') as shell:
            shell.sendline("conda activate environment-not-found-doesnt-exist")
            shell.expect('Could not find conda environment: environment-not-found-doesnt-exist')
            shell.assert_env_var('errorlevel', '1\r')

            shell.sendline("conda activate -h blah blah")
            shell.expect('help requested for activate')
