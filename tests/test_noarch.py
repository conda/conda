import pytest
import unittest

from conda import noarch


class TestHelpers(unittest.TestCase):

    def test_get_python_version(self):
        self.assertEquals(noarch.get_noarch_cls("python"), noarch.NoArchPython)
        self.assertEquals(noarch.get_noarch_cls("none"), noarch.NoArch)
        self.assertEquals(noarch.get_noarch_cls(True), noarch.NoArch)
        self.assertEquals(noarch.get_noarch_cls(None), None)

    def test_get_python_version_for_prefix(self):
        pass

    def test_get_site_packages_dir(self):
        pass

    def test_get_bin_dir(self):
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
