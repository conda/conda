from unittest import TestCase
import pytest
from .test_create import (make_temp_env, assert_package_is_installed
    , run_command, Commands, get_conda_list_tuple)
from conda.base.context import context

class PriorityTest(TestCase):

    @pytest.mark.timeout(300)
    def test_channel_order_channel_priority_true(self):
        with make_temp_env("python=3 pycosat==0.6.1") as prefix:
            assert_package_is_installed(prefix, 'python')
            assert_package_is_installed(prefix, 'pycosat')

            # add conda-forge channel
            run_command(Commands.CONFIG, prefix, "--prepend channels conda-forge")
            o, e = run_command(Commands.CONFIG, prefix, '--get channels')
            assert "conda-forge" in o, o

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


    @pytest.mark.timeout(300)
    def test_channel_priority_update(self):
        """
            This case will fail now
        """
        with make_temp_env("python=3 ") as prefix:
            assert_package_is_installed(prefix, 'python')

            # add conda-forge channel
            run_command(Commands.CONFIG, prefix, "--prepend channels conda-forge")
            o, e = run_command(Commands.CONFIG, prefix, '--get channels')
            assert "conda-forge" in o, o

            # update python
            update_stdout, _ = run_command(Commands.UPDATE, prefix, 'python')

            # pycosat should be in the SUPERCEDED list
            superceded_split = update_stdout.split('UPDATED')
            assert len(superceded_split) == 2
            assert 'conda-forge' in superceded_split[1]

            # python sys.version should show conda-forge python
            python_tuple = get_conda_list_tuple(prefix, "python")
            assert python_tuple[3] == 'conda-forge'
