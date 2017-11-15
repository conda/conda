# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
import os
from os.path import isdir, join, lexists
from tempfile import gettempdir
from unittest import TestCase
from uuid import uuid4

from conda._vendor.auxlib.collection import AttrDict
from conda.base.context import context, reset_context
from conda.common.io import env_var
from conda.core.envs_manager import EnvsDirectory
from conda.gateways.disk import mkdir_p
from conda.gateways.disk.delete import rm_rf
from conda.gateways.disk.read import yield_lines
from conda.gateways.disk.update import touch

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

    def test_register_unregister_named_env(self):
        envs_dir = join(self.prefix, 'envs')
        ed = EnvsDirectory(envs_dir)
        assert ed.is_writable

        chopo_location = join(envs_dir, 'chopo')
        ed.register_env(chopo_location)
        ed.register_env(chopo_location)  # should be completely idempotent

        assert len(tuple(yield_lines(ed.catalog_file))) == 0

    def test_register_unregister_location_env(self):
        envs_dir = join(self.prefix, 'envs')
        ed = EnvsDirectory(envs_dir)
        assert ed.is_writable

        gascon_location = join(self.prefix, 'gascon')
        ed.register_env(gascon_location)
        ed.register_env(gascon_location)  # should be completely idempotent

        environments_txt_lines = tuple(yield_lines(ed.catalog_file))
        assert len(environments_txt_lines) == 1
        assert environments_txt_lines[0] == gascon_location

        ed.unregister_env(gascon_location)
        assert len(tuple(yield_lines(ed.catalog_file))) == 0
        ed.unregister_env(gascon_location)  # should be idempotent
        assert len(tuple(yield_lines(ed.catalog_file))) == 0

    def test_register_unregister_root_env(self):
        envs_dir = join(self.prefix, 'envs')
        ed = EnvsDirectory(envs_dir)
        assert ed.is_writable

        root_location = self.prefix
        ed.register_env(root_location)
        ed.register_env(root_location)  # should be completely idempotent

        assert len(tuple(yield_lines(ed.catalog_file))) == 0

        assert ed.to_prefix('root') == root_location

        ed.unregister_env(root_location)
        ed.unregister_env(root_location)  # should be idempotent

        assert len(tuple(yield_lines(ed.catalog_file))) == 0

    def test_default_target_is_root_prefix(self):
        assert context.target_prefix == context.root_prefix

    def test_name_cli_flag(self):
        envs_dirs = (join(self.prefix, 'first-envs-dir'), join(self.prefix, 'seconds-envs-dir'))
        with env_var('CONDA_ENVS_DIRS', os.pathsep.join(envs_dirs), reset_context):

            # with both dirs writable, choose first
            reset_context((), argparse_args=AttrDict(name='blarg', func='create'))
            assert context.target_prefix == join(envs_dirs[0], 'blarg')

            # with first dir read-only, choose second
            EnvsDirectory(envs_dirs[0])._is_writable = False
            reset_context((), argparse_args=AttrDict(name='blarg', func='create'))
            assert context.target_prefix == join(envs_dirs[1], 'blarg')

            # if first dir is read-only but environment exists, choose first
            EnvsDirectory._cache_.pop(envs_dirs[0])
            mkdir_p(join(envs_dirs[0], 'blarg'))
            touch(join(envs_dirs[0], 'blarg', 'history'))
            reset_context((), argparse_args=AttrDict(name='blarg', func='create'))
            assert context.target_prefix == join(envs_dirs[0], 'blarg')

            EnvsDirectory._cache_ = {}

    def test_prefix_cli_flag(self):
        envs_dirs = (join(self.prefix, 'first-envs-dir'), join(self.prefix, 'seconds-envs-dir'))
        with env_var('CONDA_ENVS_DIRS', os.pathsep.join(envs_dirs), reset_context):

            # even if prefix doesn't exist, it can be a target prefix
            reset_context((), argparse_args=AttrDict(prefix='./blarg', func='create'))
            target_prefix = join(os.getcwd(), 'blarg')
            assert context.target_prefix == target_prefix
            assert not isdir(target_prefix)
