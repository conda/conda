from unittest import TestCase

import pytest

from conda.base.context import context
from .test_create import (make_temp_env, assert_package_is_installed,
                          run_command, Commands, get_conda_list_tuple)


@pytest.mark.integration
class PriorityIntegrationTests(TestCase):

    def test_channel_order_channel_priority_true(self):
        with make_temp_env("python=3.5 pycosat==0.6.1") as prefix:
            assert_package_is_installed(prefix, 'python')
            assert_package_is_installed(prefix, 'pycosat')

            # add conda-forge channel
            o, e = run_command(Commands.CONFIG, prefix, "--prepend channels conda-forge", '--json')

            assert context.channels == ("conda-forge", "defaults"), o + e
            # update --all
            update_stdout, _ = run_command(Commands.UPDATE, prefix, '--all')

            # pycosat should be in the SUPERCEDED list
            superceded_split = update_stdout.split('SUPERCEDED')
            assert len(superceded_split) == 2
            assert 'pycosat' in superceded_split[1]

            # python sys.version should show conda-forge python
            python_tuple = get_conda_list_tuple(prefix, "python")
            assert python_tuple[3] == 'conda-forge'
            # conda list should show pycosat coming from conda-forge
            pycosat_tuple = get_conda_list_tuple(prefix, "pycosat")
            assert pycosat_tuple[3] == 'conda-forge'

    def test_channel_priority_update(self):
        """
            This case will fail now
        """
        with make_temp_env("python=3.5") as prefix:
            assert_package_is_installed(prefix, 'python')

            # add conda-forge channel
            o, e = run_command(Commands.CONFIG, prefix, "--prepend channels conda-forge", '--json')
            assert context.channels == ("conda-forge", "defaults"), o+e

            # update python
            update_stdout, _ = run_command(Commands.UPDATE, prefix, 'python')

            # pycosat should be in the SUPERCEDED list
            superceded_split = update_stdout.split('UPDATED')
            assert len(superceded_split) == 2
            assert 'conda-forge' in superceded_split[1]

            # python sys.version should show conda-forge python
            python_tuple = get_conda_list_tuple(prefix, "python")
            assert python_tuple[3] == 'conda-forge'
