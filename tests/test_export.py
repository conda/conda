import pytest
import tempfile
from conda.gateways.disk.delete import rm_rf
from datetime import datetime
from os.path import exists, join
from unittest import TestCase

from .test_create import (Commands, PYTHON_BINARY, assert_package_is_installed, make_temp_env,
                          make_temp_prefix, run_command)


@pytest.mark.integration
class ExportIntegrationTests(TestCase):

    def test_basic(self):
        with make_temp_env("python=3.5") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'python-3')

            output, error = run_command(Commands.LIST, prefix, "-e")

            with tempfile.NamedTemporaryFile(mode="w", suffix="txt", delete=False) as env_txt:
                env_txt.write(output)
                env_txt.flush()
                env_txt.close()
                prefix2 = make_temp_prefix()
                run_command(Commands.CREATE, prefix2 , "--file " + env_txt.name)

                assert_package_is_installed(prefix2, "python")

            output2, error= run_command(Commands.LIST, prefix2, "-e")
            self.assertEqual(output, output2)

    @pytest.mark.xfail(datetime.now() < datetime(2017, 3, 1), reason="Bring back `conda list --export` #3445", strict=True)
    def test_multi_channel_export(self):
        """
            When try to import from txt
            every package should come from same channel
        """
        with make_temp_env("python=3.5") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'python-3')

            run_command(Commands.INSTALL, prefix, "six", "-c", "conda-forge")
            assert_package_is_installed(prefix, "six")

            output, error = run_command(Commands.LIST, prefix, "-e")
            self.assertIn("conda-forge", output)

            try:
                with tempfile.NamedTemporaryFile(mode="w", suffix="txt", delete=False) as env_txt:
                    env_txt.write(output)
                    env_txt.close()
                    prefix2 = make_temp_prefix()
                    run_command(Commands.CREATE, prefix2 , "--file " + env_txt.name)

                    assert_package_is_installed(prefix2, "python")
                output2, error = run_command(Commands.LIST, prefix2, "-e")
                self.assertEqual(output, output2)
            finally:
                rm_rf(env_txt.name)

    def test_multi_channel_explicit(self):
        """
            When try to import from txt
            every package should come from same channel
        """
        with make_temp_env("python=3.5") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert_package_is_installed(prefix, 'python-3')

            run_command(Commands.INSTALL, prefix, "six", "-c", "conda-forge")
            assert_package_is_installed(prefix, "six")

            output, error = run_command(Commands.LIST, prefix, "--explicit")
            self.assertIn("conda-forge", output)

            try:
                with tempfile.NamedTemporaryFile(mode="w", suffix="txt", delete=False) as env_txt:
                    env_txt.write(output)
                    env_txt.close()
                    prefix2 = make_temp_prefix()
                    run_command(Commands.CREATE, prefix2, "--file " + env_txt.name)

                    assert_package_is_installed(prefix2, "python")
                    assert_package_is_installed(prefix2, "six")
                output2, _ = run_command(Commands.LIST, prefix2, "--explicit")
                self.assertEqual(output, output2)
            finally:
                rm_rf(env_txt.name)
