# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime
from logging import getLogger
import os
from os.path import dirname, isdir, join
import sys
from tempfile import gettempdir
from unittest import TestCase
from uuid import uuid4

from conda import CONDA_PACKAGE_ROOT
from conda._vendor.auxlib.ish import dals
from conda._vendor.toolz.itertoolz import concatv
from conda.activate import CmdExeActivator, CshActivator, FishActivator, PosixActivator, \
    PowerShellActivator, XonshActivator, activator_map, main as activate_main, native_path_to_unix
from conda.base.constants import ROOT_ENV_NAME
from conda.base.context import context, conda_tests_ctxt_mgmt_def_pol
from conda.common.compat import ensure_text_type, iteritems, on_win, \
    string_types
from conda.common.io import captured, env_var, env_vars
from conda.common.path import which
from conda.exceptions import EnvironmentLocationNotFound, EnvironmentNameNotFound
from conda.gateways.disk.create import mkdir_p
from conda.gateways.disk.delete import rm_rf
from conda.gateways.disk.update import touch
import pytest
from tests.helpers import tempdir
from tests.test_create import Commands, run_command

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
        activator = PosixActivator()

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
        with env_var("CONDA_CHANGEPS1", "yes", conda_tests_ctxt_mgmt_def_pol):
            activator = PosixActivator()
            assert activator._prompt_modifier('/dont/matter', ROOT_ENV_NAME) == '(%s) ' % ROOT_ENV_NAME

            instructions = activator.build_activate("base")
            assert instructions['export_vars']['CONDA_PROMPT_MODIFIER'] == '(%s) ' % ROOT_ENV_NAME

    def test_PS1_no_changeps1(self):
        with env_var("CONDA_CHANGEPS1", "no", conda_tests_ctxt_mgmt_def_pol):
            activator = PosixActivator()
            assert activator._prompt_modifier('/dont/matter', 'root') == ''

            instructions = activator.build_activate("base")
            assert instructions['export_vars']['CONDA_PROMPT_MODIFIER'] == ''

    def test_add_prefix_to_path_posix(self):
        if on_win and "PWD" not in os.environ:
            pytest.skip("This test cannot be run from the cmd.exe shell.")

        activator = PosixActivator()

        path_dirs = activator.path_conversion(['/path1/bin', '/path2/bin', '/usr/local/bin', '/usr/bin', '/bin'])
        assert len(path_dirs) == 5
        test_prefix = '/usr/mytest/prefix'
        added_paths = activator.path_conversion(activator._get_path_dirs(test_prefix))
        if isinstance(added_paths, string_types):
            added_paths = added_paths,

        new_path = activator._add_prefix_to_path(test_prefix, path_dirs)
        condabin_dir = context.conda_prefix + "/condabin"
        assert new_path == added_paths + (condabin_dir,) + path_dirs

    @pytest.mark.skipif(not on_win, reason="windows-specific test")
    def test_add_prefix_to_path_cmdexe(self):
        activator = CmdExeActivator()

        path_dirs = activator.path_conversion(["C:\\path1", "C:\\Program Files\\Git\\cmd", "C:\\WINDOWS\\system32"])
        assert len(path_dirs) == 3
        test_prefix = '/usr/mytest/prefix'
        added_paths = activator.path_conversion(activator._get_path_dirs(test_prefix))
        if isinstance(added_paths, string_types):
            added_paths = added_paths,

        new_path = activator._add_prefix_to_path(test_prefix, path_dirs)
        assert new_path[:len(added_paths)] == added_paths
        assert new_path[-len(path_dirs):] == path_dirs
        assert len(new_path) == len(added_paths) + len(path_dirs) + 1
        assert new_path[len(added_paths)].endswith("condabin")

    def test_remove_prefix_from_path_1(self):
        activator = PosixActivator()
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
        activator = PosixActivator()
        original_path = tuple(activator._get_starting_path_list())
        keep_path = activator.path_conversion('/keep/this/path')
        final_path = (keep_path,) + original_path
        final_path = activator.path_conversion(final_path)

        test_prefix = join(os.getcwd(), 'mytestpath')
        prefix_added_path = (keep_path,) + original_path
        new_path = activator._remove_prefix_from_path(test_prefix, prefix_added_path)

        assert final_path == new_path

    def test_replace_prefix_in_path_1(self):
        activator = PosixActivator()
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

    @pytest.mark.skipif(not on_win, reason="windows-specific test")
    def test_replace_prefix_in_path_2(self):
        path1 = join("c:\\", "temp", "6663 31e0")
        path2 = join("c:\\", "temp", "6663 31e0", "envs", "charizard")
        one_more = join("d:\\", "one", "more")
        #   old_prefix: c:\users\builder\appdata\local\temp\6663 31e0
        #   new_prefix: c:\users\builder\appdata\local\temp\6663 31e0\envs\charizard
        activator = CmdExeActivator()
        old_path = activator.pathsep_join(activator._add_prefix_to_path(path1))
        old_path = one_more + ";" + old_path
        with env_var('PATH', old_path):
            activator = PosixActivator()
            path_elements = activator._replace_prefix_in_path(path1, path2)
        old_path = native_path_to_unix(old_path.split(";"))

        assert path_elements[0] == native_path_to_unix(one_more)
        assert path_elements[1] == native_path_to_unix(next(activator._get_path_dirs(path2)))
        assert len(path_elements) == len(old_path)

    def test_default_env(self):
        activator = PosixActivator()
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
                    activator = PosixActivator()
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

    @pytest.mark.skipif(on_win, reason="cygpath isn't always on PATH")
    def test_build_activate_shlvl_1(self):
        with tempdir() as td:
            mkdir_p(join(td, 'conda-meta'))
            activate_d_dir = mkdir_p(join(td, 'etc', 'conda', 'activate.d'))
            activate_d_1 = join(activate_d_dir, 'see-me.sh')
            activate_d_2 = join(activate_d_dir, 'dont-see-me.bat')
            touch(join(activate_d_1))
            touch(join(activate_d_2))

            old_prefix = '/old/prefix'
            activator = PosixActivator()
            old_path = activator.pathsep_join(activator._add_prefix_to_path(old_prefix))

            with env_vars({
                'CONDA_SHLVL': '1',
                'CONDA_PREFIX': old_prefix,
                'PATH': old_path,
                'CONDA_ENV_PROMPT': '({default_env})',
            }, conda_tests_ctxt_mgmt_def_pol):
                activator = PosixActivator()
                builder = activator.build_activate(td)
                new_path = activator.pathsep_join(activator._replace_prefix_in_path(old_prefix, td))
                conda_prompt_modifier = "(%s)" % td
                ps1 = conda_prompt_modifier + os.environ.get('PS1', '')

                assert td in new_path
                assert old_prefix not in new_path

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

                with env_vars({
                    'PATH': new_path,
                    'CONDA_PREFIX': td,
                    'CONDA_PREFIX_1': old_prefix,
                    'CONDA_SHLVL': 2,
                    'CONDA_DEFAULT_ENV': td,
                    'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
                }):
                    activator = PosixActivator()
                    builder = activator.build_deactivate()

                    assert builder['unset_vars'] == (
                        'CONDA_PREFIX_1',
                    )
                    assert builder['set_vars'] == {
                        'PS1': '(/old/prefix)',
                    }
                    assert builder['export_vars'] == {
                        'CONDA_DEFAULT_ENV': old_prefix,
                        'CONDA_PREFIX': old_prefix,
                        'CONDA_PROMPT_MODIFIER': '(%s)' % old_prefix,
                        'CONDA_SHLVL': 1,
                        'PATH': old_path,
                    }
                    assert builder['activate_scripts'] == ()
                    assert builder['deactivate_scripts'] == ()

    @pytest.mark.skipif(on_win, reason="cygpath isn't always on PATH")
    def test_build_stack_shlvl_1(self):
        with tempdir() as td:
            mkdir_p(join(td, 'conda-meta'))
            activate_d_dir = mkdir_p(join(td, 'etc', 'conda', 'activate.d'))
            activate_d_1 = join(activate_d_dir, 'see-me.sh')
            activate_d_2 = join(activate_d_dir, 'dont-see-me.bat')
            touch(join(activate_d_1))
            touch(join(activate_d_2))

            old_prefix = '/old/prefix'
            activator = PosixActivator()
            old_path = activator.pathsep_join(activator._add_prefix_to_path(old_prefix))

            with env_vars({
                'CONDA_SHLVL': '1',
                'CONDA_PREFIX': old_prefix,
                'PATH': old_path,
                'CONDA_ENV_PROMPT': '({default_env})',
            }, conda_tests_ctxt_mgmt_def_pol):
                activator = PosixActivator()
                builder = activator.build_stack(td)
                new_path = activator.pathsep_join(activator._add_prefix_to_path(td))
                conda_prompt_modifier = "(%s)" % td
                ps1 = conda_prompt_modifier + os.environ.get('PS1', '')

                assert builder['unset_vars'] == ()

                assert td in new_path
                assert old_prefix in new_path

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
                    'CONDA_STACKED_2': 'true',
                }
                assert builder['set_vars'] == set_vars
                assert builder['export_vars'] == export_vars
                assert builder['activate_scripts'] == (activator.path_conversion(activate_d_1),)
                assert builder['deactivate_scripts'] == ()

                with env_vars({
                    'PATH': new_path,
                    'CONDA_PREFIX': td,
                    'CONDA_PREFIX_1': old_prefix,
                    'CONDA_SHLVL': 2,
                    'CONDA_DEFAULT_ENV': td,
                    'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
                    'CONDA_STACKED_2': 'true',
                }):
                    activator = PosixActivator()
                    builder = activator.build_deactivate()

                    assert builder['unset_vars'] == (
                        'CONDA_PREFIX_1',
                        'CONDA_STACKED_2',
                    )
                    assert builder['set_vars'] == {
                        'PS1': '(/old/prefix)',
                    }
                    assert builder['export_vars'] == {
                        'CONDA_DEFAULT_ENV': old_prefix,
                        'CONDA_PREFIX': old_prefix,
                        'CONDA_PROMPT_MODIFIER': '(%s)' % old_prefix,
                        'CONDA_SHLVL': 1,
                        'PATH': old_path,
                    }
                    assert builder['activate_scripts'] == ()
                    assert builder['deactivate_scripts'] == ()

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
                    activator = PosixActivator()

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

    @pytest.mark.skipif(on_win, reason="cygpath isn't always on PATH")
    def test_build_deactivate_shlvl_2_from_stack(self):
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

            activator = PosixActivator()
            original_path = activator.pathsep_join(activator._add_prefix_to_path(old_prefix))
            with env_var('PATH', original_path):
                activator = PosixActivator()
                starting_path = activator.pathsep_join(activator._add_prefix_to_path(td))

                with env_vars({
                    'CONDA_SHLVL': '2',
                    'CONDA_PREFIX_1': old_prefix,
                    'CONDA_PREFIX': td,
                    'CONDA_STACKED_2': 'true',
                    'PATH': starting_path,
                }, conda_tests_ctxt_mgmt_def_pol):
                    activator = PosixActivator()
                    builder = activator.build_deactivate()

                    assert builder['unset_vars'] == (
                        'CONDA_PREFIX_1',
                        'CONDA_STACKED_2',
                    )

                    conda_prompt_modifier = "(%s) " % old_prefix
                    ps1 = conda_prompt_modifier + os.environ.get('PS1', '')

                    set_vars = {
                        'PS1': ps1,
                    }
                    export_vars = {
                        'PATH': original_path,
                        'CONDA_SHLVL': 1,
                        'CONDA_PREFIX': old_prefix,
                        'CONDA_DEFAULT_ENV': old_prefix,
                        'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
                    }
                    assert builder['set_vars'] == set_vars
                    assert builder['export_vars'] == export_vars
                    assert builder['activate_scripts'] == (activator.path_conversion(activate_d_1),)
                    assert builder['deactivate_scripts'] == (activator.path_conversion(deactivate_d_1),)

    @pytest.mark.skipif(on_win, reason="cygpath isn't always on PATH")
    def test_build_deactivate_shlvl_2_from_activate(self):
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

            activator = PosixActivator()
            original_path = activator.pathsep_join(activator._add_prefix_to_path(old_prefix))
            new_path = activator.pathsep_join(activator._add_prefix_to_path(td))
            with env_vars({
                'CONDA_SHLVL': '2',
                'CONDA_PREFIX_1': old_prefix,
                'CONDA_PREFIX': td,
                'PATH': new_path,
            }, conda_tests_ctxt_mgmt_def_pol):
                activator = PosixActivator()
                builder = activator.build_deactivate()

                assert builder['unset_vars'] == ('CONDA_PREFIX_1',)

                conda_prompt_modifier = "(%s) " % old_prefix
                ps1 = conda_prompt_modifier + os.environ.get('PS1', '')

                set_vars = {
                    'PS1': ps1,
                }
                export_vars = {
                    'PATH': original_path,
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
                    activator = PosixActivator()
                    original_path = tuple(activator._get_starting_path_list())
                    builder = activator.build_deactivate()

                    assert builder['unset_vars'] == (
                        'CONDA_PREFIX',
                        'CONDA_DEFAULT_ENV',
                        'CONDA_PYTHON_EXE',
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
        activator = PosixActivator()
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
            activator = PosixActivator()
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
        activator = CmdExeActivator()
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
        @CALL "%(activate1)s"
        """) % {
            'converted_prefix': activator.path_conversion(self.prefix),
            'native_prefix': self.prefix,
            'new_path': activator.pathsep_join(new_path_parts),
            'sys_executable': activator.path_conversion(sys.executable),
            'activate1': activator.path_conversion(join(self.prefix, 'etc', 'conda', 'activate.d', 'activate1.bat')),
            'conda_exe': activator.path_conversion(context.conda_exe),
        }

        with env_vars({
            'CONDA_PREFIX': self.prefix,
            'CONDA_SHLVL': '1',
            'PATH': os.pathsep.join(concatv(new_path_parts, (os.environ['PATH'],))),
        }):
            activator = CmdExeActivator()
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
        activator = CshActivator()
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
            activator = CshActivator()
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
        activator = XonshActivator()
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
            activator = XonshActivator()
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
        activator = FishActivator()
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
            activator = FishActivator()
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
        activator = PowerShellActivator()
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
            activator = PowerShellActivator()
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
            Remove-Item Env:/CONDA_DEFAULT_ENV
            Remove-Item Env:/CONDA_PREFIX
            Remove-Item Env:/CONDA_PROMPT_MODIFIER
            Remove-Item Env:/CONDA_PYTHON_EXE
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
            'init_command': 'env | sort && eval "$(python -m conda \"shell.posix\" \"hook\")"',
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
            'init_command': 'env | sort && eval "$(python -m conda \"shell.zsh\" \"hook\")"',
        },
        'cmd.exe': {
            'activator': 'cmd.exe',
            'init_command': 'set "CONDA_SHLVL=" '
                            '&& @CALL {}\\shell\\condabin\\conda_hook.bat '
                            '&& set "CONDA_EXE={}"'.format(CONDA_PACKAGE_ROOT,
                                                           join(sys.prefix, "Scripts", "conda.exe")),
            'print_env_var': '@echo %%%s%%',
        },
        'csh': {
            'activator': 'csh',
            # Trying to use -x with `tcsh` on `macOS` results in some problems:
            # This error from `PyCharm`:
            # BrokenPipeError: [Errno 32] Broken pipe (writing to self.proc.stdin).
            # .. and this one from the `macOS` terminal:
            # pexpect.exceptions.EOF: End Of File (EOF).
            # 'args': ('-x',),
            'init_command': 'set _CONDA_EXE=\"{CPR}/shell/bin/conda\"; '
                            'source {CPR}/shell/etc/profile.d/conda.csh; '.format(CPR=CONDA_PACKAGE_ROOT),
            'print_env_var': 'echo "$%s"',
        },
        'tcsh': {
            'base_shell': 'csh',
        },
        'fish': {
            'activator': 'fish',
            'init_command': 'eval (python -m conda "shell.fish" "hook")',
            'print_env_var': 'echo $%s',
        },
        # We don't know if the PowerShell executable is called
        # powershell, pwsh, or pwsh-preview.
        'powershell': {
            'activator': 'powershell',
            'args': ('-NoProfile', '-NoLogo'),
            'init_command': 'python -m conda "shell.powershell" "hook" | Out-String | Invoke-Expression',
            'print_env_var': '$Env:%s',
            'exit_cmd': 'exit'
        },
        'pwsh': {
            'base_shell': 'powershell'
        },
        'pwsh-preview': {
            'base_shell': 'powershell'
        },
    }

    def __init__(self, shell_name):
        self.shell_name = shell_name
        base_shell = self.shells[shell_name].get('base_shell')
        shell_vals = self.shells.get(base_shell, {})
        shell_vals.update(self.shells[shell_name])
        for key, value in iteritems(shell_vals):
            setattr(self, key, value)
        self.activator = activator_map[shell_vals['activator']]()
        self.exit_cmd = self.shells[shell_name].get('exit_cmd', None)
        self.args = []
        if base_shell:
            self.args.extend(list(self.shells[base_shell].get('args', [])))
        self.args.extend(list(self.shells[shell_name].get('args', [])))

    def __enter__(self):
        from pexpect.popen_spawn import PopenSpawn

        # remove all CONDA_ env vars
        # this ensures that PATH is shared with any msys2 bash shell, rather than starting fresh
        os.environ["MSYS2_PATH_TYPE"] = "inherit"
        os.environ["CHERE_INVOKING"] = "1"
        env = {str(k): str(v) for k, v in iteritems(os.environ)}
        remove_these = {var_name for var_name in env if var_name.startswith('CONDA_')}
        for var_name in remove_these:
            del env[var_name]
        from conda.utils import quote_for_shell
        p = PopenSpawn(quote_for_shell([self.shell_name] + self.args),
                       timeout=12, maxread=5000, searchwindowsize=None,
                       logfile=sys.stdout, cwd=os.getcwd(), env=env, encoding=None,
                       codec_errors='strict')

        # set state for context
        joiner = os.pathsep.join if self.shell_name == 'fish' else self.activator.pathsep_join
        PATH = joiner(self.activator.path_conversion(concatv(
            (dirname(sys.executable),),
            self.activator._get_starting_path_list(),
            (dirname(which(self.shell_name)),),
        )))
        self.original_path = PATH
        env = {
            'CONDA_AUTO_ACTIVATE_BASE': 'false',
            'PYTHONPATH': CONDA_PACKAGE_ROOT,
            'PATH': PATH,
        }
        for ev in ('CONDA_TEST_SAVE_TEMPS', 'CONDA_TEST_TMPDIR', 'CONDA_TEST_USER_ENVIRONMENTS_TXT_FILE'):
            if ev in os.environ: env[ev] = os.environ[ev]

        for name, val in iteritems(env):
            p.sendline(self.activator.export_var_tmpl % (name, val))

        if self.init_command:
            p.sendline(self.init_command)
        self.p = p
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            print("Exception encountered: {}".format(exc_val))
        if self.p:
            if self.exit_cmd:
                self.sendline(self.exit_cmd)
            import signal
            self.p.kill(signal.SIGINT)

    def sendline(self, s):
        return self.p.sendline(s)

    def expect(self, pattern, timeout=-1, searchwindowsize=-1, async_=False):
        return self.p.expect(pattern, timeout, searchwindowsize, async_)

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

    def get_env_var(self, env_var, default=None):
        if self.shell_name == 'cmd.exe':
            self.sendline("@echo %%%s%%" % env_var)
            self.expect("@echo %%%s%%\r\n([^\r]*)\r" % env_var)
            value = self.p.match.groups()[0]
        elif self.shell_name == 'powershell':
            self.sendline(self.print_env_var % env_var)
            # The \r\n\( is the newline after the env var and the start of the prompt.
            # If we knew the active env we could add that in as well as the closing )
            self.expect(r'\$Env:{}\r\n([^\r]*)(\r\n)+\('.format(env_var))
            value = self.p.match.groups()[0]
        else:
            self.sendline('echo get_var_start')
            self.sendline(self.print_env_var % env_var)
            self.sendline('echo get_var_end')
            self.expect('get_var_start(.*)get_var_end')
            value = self.p.match.groups()[0]
        if value is None:
            return default
        return ensure_text_type(value).strip()

def which_powershell():
    r"""
    Since we don't know whether PowerShell is installed as powershell, pwsh, or pwsh-preview,
    it's helpful to have a utility function that returns the name of the best PowerShell
    executable available, or `None` if there's no PowerShell installed.

    If PowerShell is found, this function returns both the kind of PowerShell install
    found and a path to its main executable.
    E.g.: ('pwsh', r'C:\Program Files\PowerShell\6.0.2\pwsh.exe)
    """
    if on_win:
        posh =  which('powershell.exe')
        if posh:
            return 'powershell', posh
    
    posh = which('pwsh')
    if posh:
        return 'pwsh', posh

    posh = which('pwsh-preview')
    if posh:
        return 'pwsh-preview', posh

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

        self.prefix2 = join(self.prefix, 'envs', 'charizard')
        mkdir_p(join(self.prefix2, 'conda-meta'))
        touch(join(self.prefix2, 'conda-meta', 'history'))

        self.prefix3 = join(self.prefix, 'envs', 'venusaur')
        mkdir_p(join(self.prefix3, 'conda-meta'))
        touch(join(self.prefix3, 'conda-meta', 'history'))

        # We can engineer ourselves out of having `git` on PATH if we install
        # it via conda, so, when we have no git on PATH, install this. Yes it
        # is variable, but at least it is not slow.
        if not which('git') or which('git').startswith(sys.prefix):
            log.warning("Installing `git` into {} because during these tests"
                         "`conda` uses `git` to get its version, and the git"
                         "found on `PATH` on this system seems to be part of"
                         "a conda env. They stack envs which means that the"
                         "the original sys.prefix conda env falls off of it."
                        .format(sys.prefix))
            run_command(Commands.INSTALL, self.prefix3, "git")

    def tearDown(self):
        rm_rf(self.prefix)

    def basic_posix(self, shell):
        num_paths_added = len(tuple(PosixActivator()._get_path_dirs(self.prefix)))
        shell.assert_env_var('CONDA_SHLVL', '0')
        PATH0 = shell.get_env_var('PATH', '').strip(':')
        assert any(p.endswith("condabin") for p in PATH0.split(":"))

        shell.sendline('conda activate base')
        # shell.sendline('env | sort')
        shell.assert_env_var('PS1', '(base).*')
        shell.assert_env_var('CONDA_SHLVL', '1')
        PATH1 = shell.get_env_var('PATH', '').strip(':')
        assert len(PATH0.split(':')) + num_paths_added == len(PATH1.split(':'))

        shell.sendline('conda activate "%s"' % self.prefix)
        # shell.sendline('env | sort')
        shell.assert_env_var('CONDA_SHLVL', '2')
        shell.assert_env_var('CONDA_PREFIX', self.prefix, True)
        PATH2 = shell.get_env_var('PATH', '').strip(':')
        assert len(PATH0.split(':')) + num_paths_added == len(PATH2.split(':'))

        shell.sendline('env | sort | grep CONDA')
        shell.expect('CONDA_')
        shell.sendline("echo \"PATH=$PATH\"")
        shell.expect('PATH=')
        shell.sendline('conda activate "%s"' % self.prefix2)
        shell.sendline('env | sort | grep CONDA')
        shell.expect('CONDA_')
        shell.sendline("echo \"PATH=$PATH\"")
        shell.expect('PATH=')
        shell.assert_env_var('PS1', '(charizard).*')
        shell.assert_env_var('CONDA_SHLVL', '3')
        PATH3 = shell.get_env_var('PATH').strip(':')
        assert len(PATH0.split(':')) + num_paths_added == len(PATH3.split(':'))

        shell.sendline('conda install -yq proj4=5.2.0')
        shell.expect('Executing transaction: ...working... done.*\n', timeout=60)
        shell.assert_env_var('?', '0', True)

        shell.sendline('proj')
        shell.expect(r'.*Rel\. 5\.2\.0,.*')

        # TODO: assert that reactivate worked correctly

        # conda run integration test, hmm, which prefix though?
        shell.sendline('conda run proj')
        shell.expect(r'.*Rel\. 5\.2\.0,.*', timeout=100000)

        # regression test for #6840
        shell.sendline('conda install --blah')
        shell.assert_env_var('?', '2', use_exact=True)
        shell.sendline('conda list --blah')
        shell.assert_env_var('?', '2', use_exact=True)

        shell.sendline('conda deactivate')
        shell.assert_env_var('CONDA_SHLVL', '2')
        PATH = shell.get_env_var('PATH').strip(':')
        assert len(PATH0.split(':')) + num_paths_added == len(PATH.split(':'))

        shell.sendline('conda deactivate')
        shell.assert_env_var('CONDA_SHLVL', '1')
        PATH = shell.get_env_var('PATH').strip(':')
        assert len(PATH0.split(':')) + num_paths_added == len(PATH.split(':'))

        shell.sendline('conda deactivate')
        shell.assert_env_var('CONDA_SHLVL', '0')
        PATH = shell.get_env_var('PATH').strip(':')
        assert len(PATH0.split(':')) == len(PATH.split(':'))

        shell.sendline(shell.print_env_var % 'PS1')
        shell.expect('.*\n')
        assert 'CONDA_PROMPT_MODIFIER' not in str(shell.p.after)

        shell.sendline('conda deactivate')
        shell.assert_env_var('CONDA_SHLVL', '0')
        PATH0 = shell.get_env_var('PATH').strip(':')

        shell.sendline('conda activate "%s"' % self.prefix2)
        shell.assert_env_var('CONDA_SHLVL', '1')
        PATH1 = shell.get_env_var('PATH').strip(':')
        assert len(PATH0.split(':')) + num_paths_added == len(PATH1.split(':'))

        shell.sendline('conda activate "%s" --stack' % self.prefix3)
        shell.assert_env_var('CONDA_SHLVL', '2')
        PATH2 = shell.get_env_var('PATH').strip(':')
        assert 'charizard' in PATH2
        assert 'venusaur' in PATH2
        assert len(PATH0.split(':')) + num_paths_added * 2 == len(PATH2.split(':'))

        shell.sendline('conda activate "%s"' % self.prefix)
        shell.assert_env_var('CONDA_SHLVL', '3')
        PATH3 = shell.get_env_var('PATH')
        assert 'charizard' in PATH3
        assert 'venusaur' not in PATH3
        assert len(PATH0.split(':')) + num_paths_added * 2 == len(PATH3.split(':'))

        shell.sendline('conda deactivate')
        shell.assert_env_var('CONDA_SHLVL', '2')
        PATH4 = shell.get_env_var('PATH').strip(':')
        assert 'charizard' in PATH4
        assert 'venusaur' in PATH4
        assert PATH4 == PATH2

    @pytest.mark.skipif(not which('bash'), reason='bash not installed')
    def test_bash_basic_integration(self):
        with InteractiveShell('bash') as shell:
            self.basic_posix(shell)

    @pytest.mark.skipif(not which('dash') or on_win, reason='dash not installed')
    def test_dash_basic_integration(self):
        with InteractiveShell('dash') as shell:
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

    @pytest.mark.skipif(not which_powershell(), reason='PowerShell not installed')
    def test_powershell_basic_integration(self):
        charizard = join(self.prefix, 'envs', 'charizard')
        venusaur = join(self.prefix, 'envs', 'venusaur')
        posh_kind, posh_path = which_powershell()
        print('## [PowerShell integration] Using {}.'.format(posh_path))
        with InteractiveShell(posh_kind) as shell:
            print('## [PowerShell integration] Starting test.')
            shell.sendline('(Get-Command conda).CommandType')
            shell.p.expect_exact('Alias')
            shell.sendline('(Get-Command conda).Definition')
            shell.p.expect_exact('Invoke-Conda')

            print('## [PowerShell integration] Activating.')
            shell.sendline('conda activate "%s"' % charizard)
            shell.assert_env_var('CONDA_SHLVL', '1\r?')
            PATH = shell.get_env_var('PATH')
            assert 'charizard' in PATH
            shell.sendline('conda activate "%s"' % self.prefix)
            shell.assert_env_var('CONDA_SHLVL', '2\r?')
            shell.assert_env_var('CONDA_PREFIX', self.prefix, True)

            shell.sendline('conda deactivate')
            PATH = shell.get_env_var('PATH')
            assert 'charizard' in PATH
            shell.sendline('conda activate -stack "%s"' % venusaur)
            PATH = shell.get_env_var('PATH')
            assert 'venusaur' in PATH
            assert 'charizard' in PATH

            print('## [PowerShell integration] Installing.')
            shell.sendline('conda install -yq proj4=5.2.0')
            shell.expect('Executing transaction: ...working... done.*\n', timeout=600)
            shell.sendline('$LASTEXITCODE')
            shell.expect('0')
            # TODO: assert that reactivate worked correctly

            print('## [PowerShell integration] Checking installed version.')
            shell.sendline('proj')
            shell.expect(r'.*Rel\. 5\.2\.0,.*')

            # conda run integration test
            print('## [PowerShell integration] Checking conda run.')
            shell.sendline('conda run proj')
            shell.expect(r'.*Rel\. 5\.2\.0,.*')

            print('## [PowerShell integration] Deactivating')
            shell.sendline('conda deactivate')
            shell.assert_env_var('CONDA_SHLVL', '1\r?')
            shell.sendline('conda deactivate')
            shell.assert_env_var('CONDA_SHLVL', '0\r?')
            shell.sendline('conda deactivate')
            shell.assert_env_var('CONDA_SHLVL', '0\r?')



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

            # TODO: Make a dummy package and release it (somewhere?)
            #       should be a relatively light package, but also
            #       one that has activate.d or deactivate.d scripts.
            #       More imporant than size or script though, it must
            #       not require an old or incompatible version of any
            #       library critical to the correct functioning of
            #       Python (e.g. OpenSSL).
            shell.sendline('conda install -yq proj4=5.2.0')
            shell.expect('Executing transaction: ...working... done.*\n', timeout=60)
            shell.assert_env_var('errorlevel', '0', True)
            # TODO: assert that reactivate worked correctly

            shell.sendline('proj')
            shell.expect(r'.*Rel\. 5\.2\.0,.*')

            # conda run integration test
            shell.sendline('conda run proj')
            shell.expect(r'.*Rel\. 5\.2\.0,.*')

            shell.sendline('conda deactivate')
            shell.assert_env_var('CONDA_SHLVL', '1\r')
            shell.sendline('conda deactivate')
            shell.assert_env_var('CONDA_SHLVL', '0\r')
            shell.sendline('conda deactivate')
            shell.assert_env_var('CONDA_SHLVL', '0\r')

    @pytest.mark.skipif(not which('bash'), reason='bash not installed')
    @pytest.mark.skipif(on_win and
                        which('bash') and
                        which('bash').startswith(sys.prefix), reason='bash installed from m2-bash in prefix {}. '
                                                                     'This is not currently supported. Use upstream'
                                                                     'MSYS2 and have it be on PATH'.format(sys.prefix))
    def test_bash_activate_error(self):
        with InteractiveShell('bash') as shell:
            if on_win:
                shell.sendline("uname -o")
                shell.expect('Msys|Cygwin')
            shell.sendline("conda activate environment-not-found-doesnt-exist")
            shell.expect('Could not find conda environment: environment-not-found-doesnt-exist')
            shell.assert_env_var('CONDA_SHLVL', '0')

            shell.sendline("conda activate -h blah blah")
            shell.expect('usage: conda activate')

    @pytest.mark.skipif(not which('cmd.exe'), reason='cmd.exe not installed')
    def test_cmd_exe_activate_error(self):
        with InteractiveShell('cmd.exe') as shell:
            shell.sendline("conda activate environment-not-found-doesnt-exist")
            shell.expect('Could not find conda environment: environment-not-found-doesnt-exist')
            shell.assert_env_var('errorlevel', '1\r')

            shell.sendline("conda activate -h blah blah")
            shell.expect('usage: conda activate')

    @pytest.mark.skipif(not which('bash'), reason='bash not installed')
    def test_legacy_activate_deactivate_bash(self):
        with InteractiveShell('bash') as shell:
            shell.sendline("export _CONDA_ROOT='%s/shell'" % CONDA_PACKAGE_ROOT)
            shell.sendline("source activate \"%s\"" % self.prefix2)
            PATH = shell.get_env_var("PATH")
            assert 'charizard' in PATH

            shell.sendline("source activate \"%s\"" % self.prefix3)
            PATH = shell.get_env_var("PATH")
            assert 'venusaur' in PATH

            shell.sendline("source deactivate")
            PATH = shell.get_env_var("PATH")
            assert 'charizard' in PATH

            shell.sendline("source deactivate")
            shell.assert_env_var('CONDA_SHLVL', '0')

    @pytest.mark.skipif(not which('cmd.exe'), reason='cmd.exe not installed')
    def test_legacy_activate_deactivate_cmd_exe(self):
        with InteractiveShell('cmd.exe') as shell:
            shell.sendline("echo off")

            shell.sendline("SET \"PATH=%s\\shell\\Scripts;%%PATH%%\"" % CONDA_PACKAGE_ROOT)
            shell.sendline("activate \"%s\"" % self.prefix2)
            PATH = shell.get_env_var("PATH")
            assert 'charizard' in PATH

            shell.sendline("activate \"%s\"" % self.prefix3)
            PATH = shell.get_env_var("PATH")
            assert 'venusaur' in PATH

            shell.sendline("deactivate")
            PATH = shell.get_env_var("PATH")
            assert 'charizard' in PATH

            shell.sendline("deactivate")
            conda_shlvl = shell.get_env_var('CONDA_SHLVL')
            assert int(conda_shlvl) == 0, conda_shlvl
