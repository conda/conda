import pytest
import unittest
from unittest.mock import patch
import sys

from conda import noarch


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

    def test_get_bin_dir_win(self):
        pass

    def test_link_files(self):
        pass

    def test_compile_missing_pyc(self):
        pass

    def test_create_entry_points(self):
        pass


class TestNoArch(unittest.TestCase):

    def test_link(self):
        pass


class TestNoArchPython(unittest.TestCase):

    def test_link(self):
        pass
