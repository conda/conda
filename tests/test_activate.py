# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
import os
from unittest import TestCase

from os.path import join
import pytest
import sys

from conda.common.compat import on_win
from conda._vendor.toolz.itertoolz import concatv

from conda.activate import Activator, expand, native_path_list_to_unix
from conda.base.context import reset_context, context
from conda.common.io import env_var
from conda.exceptions import EnvironmentLocationNotFound, EnvironmentNameNotFound
from conda.gateways.disk.create import mkdir_p
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
        path = '/path1/bin:/path2/bin:/usr/local/bin:/usr/bin:/bin'
        test_prefix = '/usr/mytest/prefix'
        with env_var('PATH', path):
            activator = Activator('posix')
            old_path = os.environ['PATH']
            new_path = activator._add_prefix_to_path(old_path, test_prefix)
            assert new_path == (activator.pathsep.join(activator._get_path_dirs(test_prefix))
                                + activator.pathsep + path)

    def test_remove_prefix_from_path(self):
        activator = Activator('posix')
        test_prefix = join(os.getcwd(), 'mytestpath')
        old_path = activator._add_prefix_to_path(os.environ['PATH'], test_prefix)
        old_path = activator.pathsep.join(('/keep/this/path', old_path))
        new_path_expected = activator.pathsep.join(('/keep/this/path', os.environ['PATH']))
        new_path = activator._remove_prefix_from_path(old_path, test_prefix)
        assert new_path_expected == new_path

    def test_replace_prefix_in_path(self):
        path = os.environ['PATH']
        prepend_path = expand('~')
        with env_var('PATH', path):
            activator = Activator('posix')
            test_prefix_1 = join(os.getcwd(), 'mytestpath1')
            test_prefix_2 = join(os.getcwd(), 'mytestpath2')
            old_path = activator._add_prefix_to_path(os.environ['PATH'], test_prefix_1)
            old_path = activator.pathsep.join((prepend_path, old_path))

            expected_new_path = activator._add_prefix_to_path(os.environ['PATH'], test_prefix_2)
            expected_new_path = activator.pathsep.join((prepend_path, expected_new_path))

            new_path = activator._replace_prefix_in_path(old_path, test_prefix_1, test_prefix_2)
            assert expected_new_path == new_path

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

            original_path = os.environ['PATH']
            with env_var('CONDA_SHLVL', '0'):
                with env_var('CONDA_PREFIX', ''):
                    activator = Activator('posix')
                    builder = activator.build_activate(td)
                    new_path = activator._add_prefix_to_path(original_path, td)

                    assert builder['unset_vars'] == ()

                    set_vars = {
                        'CONDA_PYTHON_PATH': sys.executable,
                        'PATH': native_path_list_to_unix(new_path),
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

            original_path = os.environ['PATH']
            old_prefix = '/old/prefix'
            with env_var('CONDA_SHLVL', '1'):
                with env_var('CONDA_PREFIX', old_prefix):
                    activator = Activator('posix')
                    builder = activator.build_activate(td)
                    new_path = activator._add_prefix_to_path(original_path, td)

                    assert builder['unset_vars'] == ()

                    set_vars = {
                        'PATH': native_path_list_to_unix(new_path),
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

            original_path = os.environ['PATH']
            with env_var('CONDA_SHLVL', '2'):
                with env_var('CONDA_PREFIX', old_prefix):
                    activator = Activator('posix')
                    builder = activator.build_activate(td)
                    new_path = activator._add_prefix_to_path(original_path, td)

                    assert builder['unset_vars'] == ()

                    set_vars = {
                        'PATH': native_path_list_to_unix(new_path),
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

            original_path = os.environ['PATH']
            with env_var('CONDA_SHLVL', '2'):
                with env_var('CONDA_PREFIX_1', old_prefix):
                    with env_var('CONDA_PREFIX', td):
                        activator = Activator('posix')
                        start_path = concatv(activator._get_path_dirs(td),
                                             original_path.split(os.pathsep))
                        with env_var('PATH', os.pathsep.join(start_path)):
                            builder = activator.build_deactivate()

                            assert builder['unset_vars'] == ('CONDA_PREFIX_1',)

                            set_vars = {
                                'PATH': native_path_list_to_unix(original_path),
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

            original_path = os.environ['PATH']
            with env_var('CONDA_SHLVL', '1'):
                with env_var('CONDA_PREFIX', td):
                    activator = Activator('posix')
                    start_path = concatv(activator._get_path_dirs(td), original_path.split(os.pathsep))
                    with env_var('PATH', os.pathsep.join(start_path)):
                        builder = activator.build_deactivate()

                        assert builder['unset_vars'] == (
                            'CONDA_PREFIX',
                            'CONDA_DEFAULT_ENV',
                            'CONDA_PYTHON_PATH',
                            'CONDA_PROMPT_MODIFIER',
                        )
                        assert builder['set_vars'] == {
                            'PATH': native_path_list_to_unix(original_path),
                            'CONDA_SHLVL': 0,
                        }
                        assert builder['activate_scripts'] == ()
                        assert builder['deactivate_scripts'] == [deactivate_d_1]


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



