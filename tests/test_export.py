import os
from os.path import abspath, dirname, exists, join
from conda._vendor.auxlib.compat import Utf8NamedTemporaryFile
from unittest import TestCase

from conda.base.context import context
from conda.core.package_cache_data import PackageCacheData
from conda.gateways.disk.delete import rm_rf
import pytest

from .test_create import Commands, PYTHON_BINARY, make_temp_env, make_temp_package_cache, \
    make_temp_prefix, package_is_installed, run_command

@pytest.mark.integration
class ExportIntegrationTests(TestCase):

    def test_basic(self):
        with make_temp_env("python=3.5") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert package_is_installed(prefix, 'python=3')

            output, error, _ = run_command(Commands.LIST, prefix, "-e")

            with Utf8NamedTemporaryFile(mode="w", suffix="txt", delete=False) as env_txt:
                env_txt.write(output)
                env_txt.flush()
                env_txt.close()
                prefix2 = make_temp_prefix()
                run_command(Commands.CREATE, prefix2 , "--file", env_txt.name)

                assert package_is_installed(prefix2, "python")

            output2, error, _ = run_command(Commands.LIST, prefix2, "-e")
            self.assertEqual(output, output2)

    @pytest.mark.skipif(True, reason="Bring back `conda list --export` #3445")
    def test_multi_channel_export(self):
        """
            When try to import from txt
            every package should come from same channel
        """
        with make_temp_env("python=3.5") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert package_is_installed(prefix, 'python=3')

            run_command(Commands.INSTALL, prefix, "six", "-c", "conda-forge")
            assert package_is_installed(prefix, "six")

            output, error, _ = run_command(Commands.LIST, prefix, "-e")
            self.assertIn("conda-forge", output)
            
            try:
                with Utf8NamedTemporaryFile(mode="w", suffix="txt", delete=False) as env_txt:
                    env_txt.write(output)
                    env_txt.close()
                    prefix2 = make_temp_prefix()
                    run_command(Commands.CREATE, prefix2 , "--file", env_txt.name)

                    assert package_is_installed(prefix2, "python")
                output2, error, _ = run_command(Commands.LIST, prefix2, "-e")
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
            assert package_is_installed(prefix, 'python=3')

            run_command(Commands.INSTALL, prefix, "six", "-c", "conda-forge")
            assert package_is_installed(prefix, "conda-forge::six")

            output, error, _ = run_command(Commands.LIST, prefix, "--explicit")
            assert not error
            assert "conda-forge" in output

            urls1 = set(url for url in output.split() if url.startswith("http"))

            try:
                with Utf8NamedTemporaryFile(mode="w", suffix="txt", delete=False) as env_txt:
                    env_txt.write(output)
                    env_txt.close()
                    prefix2 = make_temp_prefix()
                    run_command(Commands.CREATE, prefix2, "--file", env_txt.name)

                    assert package_is_installed(prefix2, "python")
                    assert package_is_installed(prefix2, "six")
                output2, error2, _ = run_command(Commands.LIST, prefix2, "--explicit")
                assert not error2
                urls2 = set(url for url in output2.split() if url.startswith("http"))
                assert urls1 == urls2
            finally:
                rm_rf(env_txt.name)

    @pytest.mark.skipif(context.subdir not in ["osx-64", "linux-64", "win-64"],
                        reason="test channel only set up for specific subdir")
    def test_channel_explicit_noarch_package_in_other(self):
        """
            When using a noarch package listed in the wrong subdir, conda install and conda install
            with explicit package urls should still work. This is done within a temp package cache
            to allow for the deletion of the package between steps.
        """
        with make_temp_package_cache() as pkgs_dir:
            with make_temp_env("python=3.5") as prefix:
                assert exists(join(prefix, PYTHON_BINARY))
                assert package_is_installed(prefix, 'python=3')

                channel = join(dirname(abspath(__file__)), 'data', 'mismatched_arch_channel')

                run_command(Commands.INSTALL, prefix, "test-package", "--override-channels", "-c", channel)
                assert package_is_installed(prefix, "test-package")

                output, error, _ = run_command(Commands.LIST, prefix, "--explicit")
                assert not error
                assert "mismatched_arch_channel" in output

                urls1 = set(url for url in output.split() if url.startswith("file"))

                print("OUTPUT: " + output)
                print("URLS1: " + str(urls1))

                # delete the installed package from the package cache
                test_package_cache_entries = [join(pkgs_dir, d) for d in os.listdir(pkgs_dir)
                                              if "test-package" in d]
                for entry in test_package_cache_entries:
                    rm_rf(entry)
                if pkgs_dir in PackageCacheData._cache_:
                    del PackageCacheData._cache_[pkgs_dir]

                try:
                    with Utf8NamedTemporaryFile(mode="w", suffix="txt", delete=False) as env_txt:

                        env_txt.write(output)
                        env_txt.close()
                        prefix2 = make_temp_prefix()
                        run_command(Commands.CREATE, prefix2, "--file", env_txt.name)

                        assert package_is_installed(prefix2, "test-package")
                    output2, error2, _ = run_command(Commands.LIST, prefix2, "--explicit")
                    assert not error2
                    urls2 = set(url for url in output2.split() if url.startswith("file"))
                    assert urls1 == urls2
                finally:
                    rm_rf(env_txt.name)
