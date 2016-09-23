import pytest
import unittest
from unittest.mock import patch, Mock
import sys
import os

from conda import noarch
from conda_build import noarch_python


def stub_sys_platform(platform):
    def sys_platform(func):
        def func_wrapper(plat):
            sys_plat = sys.platform
            sys.platform = platform
            func(plat)
            sys.platform = sys_plat
        return func_wrapper
    return sys_platform


class TestHelpers(unittest.TestCase):

    def test_get_python_version(self):
        self.assertEquals(noarch.get_noarch_cls("python"), noarch.NoArchPython)
        self.assertEquals(noarch.get_noarch_cls("none"), noarch.NoArch)
        self.assertEquals(noarch.get_noarch_cls(True), noarch.NoArch)
        self.assertEquals(noarch.get_noarch_cls(None), None)

    @stub_sys_platform("win32")
    def test_get_site_packages_dir_win(self):
        site_packages_dir = noarch.get_site_packages_dir("")
        self.assertEquals(site_packages_dir, "Lib")

    @stub_sys_platform("darwin")
    def test_get_site_packages_dir_unix(self):
        with patch.object(noarch, "get_python_version_for_prefix", return_value="3.5") as m:
            site_packages_dir = noarch.get_site_packages_dir("")
            self.assertEquals(site_packages_dir, 'lib/python3.5')

    @stub_sys_platform("win32")
    def test_get_bin_dir_win(self):
        bin_dir = noarch.get_bin_dir("")
        self.assertEquals(bin_dir, "Scripts")

    @stub_sys_platform("darwin")
    def test_get_bin_dir_unix(self):
        bin_dir = noarch.get_bin_dir("")
        self.assertEquals(bin_dir, "bin")

    def test_link_files(self):
        pass

    def test_compile_missing_pyc(self):
        pass


class TestEntryPointCreation(unittest.TestCase):

    def setUp(self):
        test_entry_points = ["cmd = module.foo:func"]
        config = Mock()
        config.info_dir = os.path.join(os.path.dirname(__file__), "info")
        os.mkdir(config.info_dir)
        noarch_python.create_entry_point_information("python", test_entry_points, config)

    def tearDown(self):
        os.remove(os.path.join(os.path.dirname(__file__), "info/noarch.json"))
        os.rmdir(os.path.join(os.path.dirname(__file__), "info"))

    @stub_sys_platform("darwin")
    def test_create_entry_points_unix(self):
        src_dir = os.path.dirname(__file__)
        bin_dir = os.path.join(os.path.dirname(__file__), "tmp_bin")
        entry_point = os.path.join(bin_dir, "cmd")
        os.mkdir(bin_dir)
        prefix = ""
        expected_script = """\
#!bin/python
if __name__ == '__main__':
    import sys
    import module.foo

    sys.exit(module.foo.func())
"""
        noarch.create_entry_points(src_dir, bin_dir, prefix)
        self.assertTrue(os.path.isfile(entry_point))
        with open(entry_point, 'r') as script:
            data = script.read()
            self.assertEqual(data, expected_script)
        os.remove(entry_point)
        os.rmdir(bin_dir)

    @stub_sys_platform("win32")
    def test_create_entry_points_win(self):
        src_dir = os.path.dirname(__file__)
        bin_dir = os.path.join(os.path.dirname(__file__), "tmp_bin")
        entry_point = os.path.join(bin_dir, "cmd-script.py")
        os.mkdir(bin_dir)
        cli_script_src = os.path.join(src_dir, 'cli-64.exe')
        cli_script_dst = os.path.join(bin_dir, "cmd.exe")
        open(cli_script_src, 'a').close()
        prefix = ""
        expected_script = """\
if __name__ == '__main__':
    import sys
    import module.foo

    sys.exit(module.foo.func())
"""
        noarch.create_entry_points(src_dir, bin_dir, prefix)
        self.assertTrue(os.path.isfile(entry_point))
        self.assertTrue(os.path.isfile(cli_script_dst))
        with open(entry_point, 'r') as script:
            data = script.read()
            self.assertEqual(data, expected_script)
        os.remove(entry_point)
        os.remove(cli_script_dst)
        os.remove(cli_script_src)
        os.rmdir(bin_dir)


class TestNoArch(unittest.TestCase):

    def test_link(self):
        pass


class TestNoArchPython(unittest.TestCase):

    def test_link(self):
        pass
