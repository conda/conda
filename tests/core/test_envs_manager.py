# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from logging import getLogger
from tempfile import gettempdir
from unittest import TestCase
from uuid import uuid4

from os.path import join, isdir, lexists

from conda import CondaError

from conda.base.context import reset_context, context

from conda.common.io import env_var
import pytest

from conda.core.envs_manager import EnvsDirectory
from conda.gateways.disk import mkdir_p
from conda.gateways.disk.delete import rm_rf
from conda.models.enums import LeasedPathType
from conda.models.leased_path_entry import LeasedPathEntry

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

        assert ed.get_registered_env_by_location(chopo_location) == {
            'name': 'chopo',
            'location': chopo_location,
        } == ed.get_registered_env_by_name('chopo')

        assert ed.to_prefix('chopo') == chopo_location

        ed.unregister_env(chopo_location)
        ed.unregister_env(chopo_location)  # should be idempotent

        assert ed.get_registered_env_by_location(chopo_location) is None
        assert ed.get_registered_env_by_name('chopo') is None

        # test EnvsDirectory cache
        assert EnvsDirectory(ed) is ed
        assert EnvsDirectory(envs_dir) is ed

    def test_register_unregister_location_env(self):
        envs_dir = join(self.prefix, 'envs')
        ed = EnvsDirectory(envs_dir)
        assert ed.is_writable

        gascon_location = join(self.prefix, 'gascon')
        ed.register_env(gascon_location)
        ed.register_env(gascon_location)  # should be completely idempotent

        assert ed.get_registered_env_by_location(gascon_location) == {
            'name': None,
            'location': gascon_location,
        }
        assert ed.get_registered_env_by_name('gascon') is None

        ed.unregister_env(gascon_location)
        ed.unregister_env(gascon_location)  # should be idempotent

        assert ed.get_registered_env_by_location(gascon_location) is None
        assert ed.get_registered_env_by_name('gascon') is None

    def test_register_unregister_root_env(self):
        envs_dir = join(self.prefix, 'envs')
        ed = EnvsDirectory(envs_dir)
        assert ed.is_writable

        root_location = self.prefix
        ed.register_env(root_location)
        ed.register_env(root_location)  # should be completely idempotent

        assert ed.get_registered_env_by_location(root_location) == {
            'name': 'root',
            'location': root_location,
        } == ed.get_registered_env_by_name('root')

        assert ed.to_prefix('root') == root_location

        ed.unregister_env(root_location)
        ed.unregister_env(root_location)  # should be idempotent

        assert ed.get_registered_env_by_location(root_location) is None
        assert ed.get_registered_env_by_name('root') is None

    def test_leased_paths(self):
        with env_var('CONDA_ROOT_PREFIX', self.prefix, reset_context):
            alamos_env = EnvsDirectory.preferred_env_to_prefix('alamos')
            lpe_1 = LeasedPathEntry(
                _path='bin/alamos',
                target_path=join(alamos_env, 'bin', 'alamos'),
                target_prefix=alamos_env,
                leased_path=join(context.root_prefix, 'bin', 'alamos'),
                package_name='alamos',
                leased_path_type=LeasedPathType.application_entry_point,
            )

            ed = EnvsDirectory(join(context.root_prefix, 'envs'))
            ed.add_leased_path(lpe_1)

            with pytest.raises(CondaError):
                ed.add_leased_path(lpe_1)

            lpe_2 = LeasedPathEntry(
                _path='bin/itsamalbec',
                target_path=join(alamos_env, 'bin', 'itsamalbec'),
                target_prefix=alamos_env,
                leased_path=join(context.root_prefix, 'bin', 'itsamalbec'),
                package_name='alamos',
                leased_path_type=LeasedPathType.application_entry_point,
            )
            ed.add_leased_path(lpe_2)

            assert len(ed.get_leased_path_entries_for_package('alamos')) == 2

            assert ed.get_leased_path_entry('bin/itsamalbec') == lpe_2

            ed.remove_leased_paths_for_package('alamos')

            assert len(ed.get_leased_path_entries_for_package('alamos')) == 0
            assert ed.get_leased_path_entry('bin/itsamalbec') is None
