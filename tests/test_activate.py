# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
import os
from os.path import join, isdir
import sys
from tempfile import gettempdir
from unittest import TestCase
from uuid import uuid4

from conda._vendor.auxlib.ish import dals
import pytest

from conda.activate import Activator
from conda.base.context import context, reset_context
from conda.common.compat import on_win, string_types
from conda.common.io import env_var
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


class ActivatorUnitTests(TestCase):

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
            assert activator._prompt_modifier('root') == '(root) '

            instructions = activator.build_activate("root")
            assert instructions['set_vars']['CONDA_PROMPT_MODIFIER'] == '(root) '

    def test_PS1_no_changeps1(self):
        with env_var("CONDA_CHANGEPS1", "no", reset_context):
            activator = Activator('posix')
            assert activator._prompt_modifier('root') == ''

            instructions = activator.build_activate("root")
            assert instructions['set_vars']['CONDA_PROMPT_MODIFIER'] == ''

    def test_add_prefix_to_path(self):
        activator = Activator('posix')

        path_dirs = activator.path_conversion(*['/path1/bin', '/path2/bin', '/usr/local/bin', '/usr/bin', '/bin'])
        assert len(path_dirs) == 5
        test_prefix = '/usr/mytest/prefix'
        added_paths = activator.path_conversion(*tuple(activator._get_path_dirs(test_prefix)))
        if isinstance(added_paths, string_types):
            added_paths = added_paths,

        new_path = activator._add_prefix_to_path(test_prefix, path_dirs)
        assert new_path == added_paths + path_dirs

    def test_remove_prefix_from_path_1(self):
        activator = Activator('posix')
        original_path = tuple(activator._get_starting_path_list())
        keep_path = activator.path_conversion('/keep/this/path')
        final_path = (keep_path,) + original_path
        final_path = activator.path_conversion(*final_path)

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
        final_path = activator.path_conversion(*final_path)

        test_prefix = join(os.getcwd(), 'mytestpath')
        prefix_added_path = (keep_path,) + original_path
        new_path = activator._remove_prefix_from_path(test_prefix, prefix_added_path)

        assert final_path == new_path

    def test_replace_prefix_in_path_1(self):
        activator = Activator('posix')
        original_path = tuple(activator._get_starting_path_list())
        new_prefix = join(os.getcwd(), 'mytestpath-new')
        new_paths = activator.path_conversion(*tuple(activator._get_path_dirs(new_prefix)))
        if isinstance(new_paths, string_types):
            new_paths = new_paths,
        keep_path = activator.path_conversion('/keep/this/path')
        final_path = (keep_path,) + new_paths + original_path
        final_path = activator.path_conversion(*final_path)

        replace_prefix = join(os.getcwd(), 'mytestpath')
        replace_paths = tuple(activator._get_path_dirs(replace_prefix))
        prefix_added_path = (keep_path,) + replace_paths + original_path
        new_path = activator._replace_prefix_in_path(replace_prefix, new_prefix, prefix_added_path)

        assert final_path == new_path

    def test_default_env(self):
        activator = Activator('posix')
        assert 'root' == activator._default_env(context.root_prefix)

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

                    assert builder['unset_vars'] == ()

                    set_vars = {
                        'CONDA_PYTHON_EXE': sys.executable,
                        'PATH': new_path,
                        'CONDA_PREFIX': td,
                        'CONDA_SHLVL': 1,
                        'CONDA_DEFAULT_ENV': td,
                        'CONDA_PROMPT_MODIFIER': "(%s) " % td,
                    }
                    assert builder['set_vars'] == set_vars
                    assert builder['activate_scripts'] == [activate_d_1]
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

                    assert builder['unset_vars'] == ()

                    set_vars = {
                        'PATH': new_path,
                        'CONDA_PREFIX': td,
                        'CONDA_PREFIX_1': old_prefix,
                        'CONDA_SHLVL': 2,
                        'CONDA_DEFAULT_ENV': td,
                        'CONDA_PROMPT_MODIFIER': "(%s) " % td,
                    }
                    assert builder['set_vars'] == set_vars
                    assert builder['activate_scripts'] == [activate_d_1]
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

                    assert builder['unset_vars'] == ()

                    set_vars = {
                        'PATH': new_path,
                        'CONDA_PREFIX': td,
                        'CONDA_DEFAULT_ENV': td,
                        'CONDA_PROMPT_MODIFIER': "(%s) " % td,
                    }
                    assert builder['set_vars'] == set_vars
                    assert builder['activate_scripts'] == [activate_d_1]
                    assert builder['deactivate_scripts'] == [deactivate_d_1]

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

            with env_var('CONDA_SHLVL', '2'):
                with env_var('CONDA_PREFIX', old_prefix):
                    activator = Activator('posix')
                    builder = activator.build_activate(td)

                    assert builder['unset_vars'] == ()
                    assert builder['set_vars'] == {}
                    assert builder['activate_scripts'] == [activate_d_1]
                    assert builder['deactivate_scripts'] == [deactivate_d_1]

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

                        new_path = activator.pathsep_join(activator.path_conversion(*original_path))

                        set_vars = {
                            'PATH': new_path,
                            'CONDA_SHLVL': 1,
                            'CONDA_PREFIX': old_prefix,
                            'CONDA_DEFAULT_ENV': old_prefix,
                            'CONDA_PROMPT_MODIFIER': "(%s) " % old_prefix,
                        }
                        assert builder['set_vars'] == set_vars
                        assert builder['activate_scripts'] == [activate_d_1]
                        assert builder['deactivate_scripts'] == [deactivate_d_1]

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
                        'CONDA_PROMPT_MODIFIER',
                    )

                    new_path = activator.pathsep_join(activator.path_conversion(*original_path))
                    assert builder['set_vars'] == {
                        'PATH': new_path,
                        'CONDA_SHLVL': 0,
                    }
                    assert builder['activate_scripts'] == ()
                    assert builder['deactivate_scripts'] == [deactivate_d_1]


class ShellWrapperUnitTests(TestCase):

    def setUp(self):
        self.environ_save = os.environ.copy()
        tempdirdir = gettempdir()

        prefix_dirname = str(uuid4())[:4] + ' ' + str(uuid4())[:4]
        self.prefix = join(tempdirdir, prefix_dirname)
        mkdir_p(join(self.prefix, 'conda-meta'))
        assert isdir(self.prefix)
        touch(join(self.prefix, 'conda-meta', 'history'))

    def tearDown(self):
        rm_rf(self.prefix)
        os.environ = self.environ_save

    def make_dot_d_files(self, extension):
        mkdir_p(join(self.prefix, 'etc', 'conda', 'activate.d'))
        mkdir_p(join(self.prefix, 'etc', 'conda', 'deactivate.d'))

        touch(join(self.prefix, 'etc', 'conda', 'activate.d', 'ignore.txt'))
        touch(join(self.prefix, 'etc', 'conda', 'deactivate.d', 'ignore.txt'))

        touch(join(self.prefix, 'etc', 'conda', 'activate.d', 'activate1' + extension))
        touch(join(self.prefix, 'etc', 'conda', 'deactivate.d', 'deactivate1' + extension))

    def test_xonsh_basic(self):
        activator = Activator('xonsh')
        self.make_dot_d_files(activator.script_extension)

        activate_result = activator.activate(self.prefix)
        with open(activate_result) as fh:
            activate_data = fh.read()
        rm_rf(activate_result)

        new_path = activator.pathsep_join(activator._add_prefix_to_path(self.prefix))
        assert activate_data == dals("""
        $CONDA_DEFAULT_ENV = "%(prefix)s"
        $CONDA_PREFIX = "%(prefix)s"
        $CONDA_PROMPT_MODIFIER = "(%(prefix)s) "
        $CONDA_PYTHON_EXE = "%(sys_executable)s"
        $CONDA_SHLVL = "1"
        $PATH = "%(new_path)s"
        source "%(prefix)s/etc/conda/activate.d/activate1.xsh"
        """) % {
            'prefix': self.prefix,
            'new_path': new_path,
            'sys_executable': sys.executable,
        }

        os.environ['CONDA_PREFIX'] = self.prefix
        os.environ['CONDA_SHLVL'] = '1'
        os.environ['PATH'] = new_path

        deactivate_result = activator.deactivate()
        with open(deactivate_result) as fh:
            deactivate_data = fh.read()
        rm_rf(deactivate_result)

        new_path = activator.pathsep_join(activator._remove_prefix_from_path(self.prefix))
        assert deactivate_data == dals("""
        del $CONDA_DEFAULT_ENV
        del $CONDA_PREFIX
        del $CONDA_PROMPT_MODIFIER
        del $CONDA_PYTHON_EXE
        $CONDA_SHLVL = "0"
        $PATH = "%(new_path)s"
        source "%(prefix)s/etc/conda/deactivate.d/deactivate1.xsh"
        """) % {
            'new_path': new_path,
            'prefix': self.prefix,
        }


@pytest.mark.integration
class ActivatorIntegrationTests(TestCase):

    def test_activate_bad_env_keeps_existing_good_env(self):
        pass

    def test_activate_deactivate(self):
        pass

    @pytest.mark.skipif(not on_win, reason="only relevant on windows")
    def test_activate_does_not_leak_echo_setting(shell):
        """Test that activate's setting of echo to off does not disrupt later echo calls"""
        if not on_win or shell != "cmd.exe":
            pytest.skip("test only relevant for cmd.exe on win")

    def test_activate_non_ascii_char_in_path(shell):
        pass

    def test_activate_has_extra_env_vars(shell):
        """Test that environment variables in activate.d show up when activated"""
        pass
