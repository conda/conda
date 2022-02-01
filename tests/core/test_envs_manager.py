# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
import os
from os.path import isdir, join, lexists
from tempfile import gettempdir
from unittest import TestCase
from uuid import uuid4

from conda.auxlib.collection import AttrDict
from conda.base.constants import PREFIX_MAGIC_FILE
from conda.base.context import context, reset_context, conda_tests_ctxt_mgmt_def_pol
from conda.common.io import env_var
from conda.common.path import paths_equal
from conda.core.envs_manager import list_all_known_prefixes, register_env, \
    get_user_environments_txt_file, \
    unregister_env, _clean_environments_txt
from conda.gateways.disk import mkdir_p
from conda.gateways.disk.delete import rm_rf
from conda.gateways.disk.read import yield_lines
from conda.gateways.disk.update import touch

import pytest

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

log = getLogger(__name__)


class EnvsManagerUnitTests(TestCase):

    def setUp(self):
        tempdirdir = gettempdir()
        dirname = str(uuid4())[:8]
        self.prefix = join(tempdirdir, dirname)
        mkdir_p(self.prefix)
        assert isdir(self.prefix)


    def tearDown(self):
        rm_rf(self.prefix)
        assert not lexists(self.prefix)

    def test_register_unregister_location_env(self):
        user_environments_txt_file = get_user_environments_txt_file()
        if (not os.path.exists(user_environments_txt_file)
            or user_environments_txt_file == os.devnull):
            pytest.skip('user environments.txt file {} does not exist'.format(user_environments_txt_file))

        gascon_location = join(self.prefix, 'gascon')
        touch(join(gascon_location, PREFIX_MAGIC_FILE), mkdir=True)
        assert gascon_location not in list_all_known_prefixes()

        touch(user_environments_txt_file, mkdir=True, sudo_safe=True)
        register_env(gascon_location)
        assert gascon_location in yield_lines(user_environments_txt_file)
        assert len(tuple(x for x in yield_lines(user_environments_txt_file) if paths_equal(gascon_location, x))) == 1

        register_env(gascon_location)  # should be completely idempotent
        assert len(tuple(x for x in yield_lines(user_environments_txt_file) if x == gascon_location)) == 1

        unregister_env(gascon_location)
        assert gascon_location not in list_all_known_prefixes()
        unregister_env(gascon_location)  # should be idempotent
        assert gascon_location not in list_all_known_prefixes()

    def test_prefix_cli_flag(self):
        envs_dirs = (join(self.prefix, 'first-envs-dir'), join(self.prefix, 'seconds-envs-dir'))
        with env_var('CONDA_ENVS_DIRS', os.pathsep.join(envs_dirs), stack_callback=conda_tests_ctxt_mgmt_def_pol):

            # even if prefix doesn't exist, it can be a target prefix
            reset_context((), argparse_args=AttrDict(prefix='./blarg', func='create'))
            target_prefix = join(os.getcwd(), 'blarg')
            assert context.target_prefix == target_prefix
            assert not isdir(target_prefix)

    def test_rewrite_environments_txt_file(self):
        mkdir_p(join(self.prefix, 'conda-meta'))
        touch(join(self.prefix, 'conda-meta', 'history'))
        doesnt_exist = join(self.prefix, 'blarg')
        environments_txt_path = join(self.prefix, 'environments.txt')
        with open(environments_txt_path, 'w') as fh:
            fh.write(self.prefix + '\n')
            fh.write(doesnt_exist + '\n')
        cleaned_1 = _clean_environments_txt(environments_txt_path)
        assert cleaned_1 == (self.prefix,)
        with patch('conda.core.envs_manager._rewrite_environments_txt') as _rewrite_patch:
            cleaned_2 = _clean_environments_txt(environments_txt_path)
            assert cleaned_2 == (self.prefix,)
            assert _rewrite_patch.call_count == 0


@patch("conda.core.envs_manager.context")
@patch("conda.core.envs_manager.get_user_environments_txt_file")
@patch("conda.core.envs_manager._clean_environments_txt")
def test_list_all_known_prefixes_with_permission_error(mock_clean_env, mock_get_user_env, mock_context, tmp_path):
    # Mock context
    myenv_dir = tmp_path / "envs"
    myenv_dir.mkdir()
    mock_context.envs_dirs = str(myenv_dir)
    mock_context.root_prefix = "root_prefix"
    # Mock get_user_environments_txt_file to return a file
    env_txt_file = tmp_path / "environment.txt"
    touch(env_txt_file)
    mock_get_user_env.return_value = env_txt_file
    # Mock _clean_environments_txt to raise PermissionError
    mock_clean_env.side_effect = PermissionError()
    all_env_paths = list_all_known_prefixes()
    # On Windows, all_env_paths can contain more paths (like '\\Miniconda')
    assert "root_prefix" in all_env_paths
