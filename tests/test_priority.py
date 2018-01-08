from datetime import datetime
from unittest import TestCase

import pytest

from conda.base.context import context, reset_context
from conda.common.compat import on_win
from conda.common.io import env_var
from .test_create import Commands, assert_package_is_installed, get_conda_list_tuple, \
    make_temp_env, run_command


@pytest.mark.integration
class PriorityIntegrationTests(TestCase):

    def test_channel_order_channel_priority_true(self):
        with env_var("CONDA_PINNED_PACKAGES", "python=3.5", reset_context):
            with make_temp_env("pycosat==0.6.1") as prefix:
                assert_package_is_installed(prefix, 'python-3.5')
                assert_package_is_installed(prefix, 'pycosat')

                # add conda-forge channel
                o, e = run_command(Commands.CONFIG, prefix, "--prepend channels conda-forge", '--json')

                assert context.channels == ("conda-forge", "defaults"), o + e
                # update --all
                update_stdout, _ = run_command(Commands.UPDATE, prefix, '--all')

                # this assertion works with the pinned_packages config to make sure
                # conda update --all still respects the pinned python version
                assert_package_is_installed(prefix, 'python-3.5')

                # pycosat should be in the SUPERSEDED list
                # after the 4.4 solver work, looks like it's in the DOWNGRADED list
                # This language needs changed anyway here.
                # For packages that CHANGE because they're being moved to a higher-priority channel
                # the message should be
                #
                # The following packages will be UPDATED to a higher-priority channel:
                #
                installed_str, x = update_stdout.split('UPDATED')
                updated_str, downgraded_str = x.split('DOWNGRADED')
                assert 'pycosat:' in updated_str

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
        with make_temp_env("python=3.5.3=0") as prefix:
            assert_package_is_installed(prefix, 'python')

            # add conda-forge channel
            o, e = run_command(Commands.CONFIG, prefix, "--prepend channels conda-forge", '--json')
            assert context.channels == ("conda-forge", "defaults"), o+e

            # update python
            update_stdout, _ = run_command(Commands.UPDATE, prefix, 'python')

            # pycosat should be in the SUPERSEDED list
            superceded_split = update_stdout.split('UPDATED')
            assert len(superceded_split) == 2
            assert 'conda-forge' in superceded_split[1]

            # python sys.version should show conda-forge python
            python_tuple = get_conda_list_tuple(prefix, "python")
            assert python_tuple[3] == 'conda-forge'
