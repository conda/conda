import random
import unittest

from conda import package

from . import helpers


class PackageTestCase(unittest.TestCase):
    def test_acts_as_a_dictionary(self):
        r = random.randint(1000, 2000)
        p = package.Package(foo="bar", random=r)

        self.assertEqual(p["foo"], "bar")
        self.assertEqual(r, p["random"])

    def test_depends_is_always_present(self):
        p = package.Package(name="foobar")
        self.assertIn("depends", p)

    def test_depends_defaults_to_empty_array(self):
        p = package.Package(name="foobar")
        self.assertEqual([], p["depends"])


class PackageFromFileWithNoDepends(unittest.TestCase):
    @classmethod
    def setup_class(self):
        filename = helpers.support_file("zlib-bad.json")
        self.package = package.from_file(filename)

    def test_is_instance_of_package(self):
        self.assertIsInstance(self.package, package.Package)

    def test_contains_expected_name_and_platform(self):
        self.assertEqual("zlib", self.package["name"])
        self.assertEqual("osx", self.package["platform"])

    def test_contains_empty_depends(self):
        self.assertIsInstance(self.package["depends"], list)


class PackageFromFileWithDepends(unittest.TestCase):
    @classmethod
    def setup_class(self):
        filename = helpers.support_file("zlib.json")
        self.package = package.from_file(filename)

    def test_is_instance_of_package(self):
        self.assertIsInstance(self.package, package.Package)

    def test_contains_expected_name_and_platform(self):
        self.assertEqual("zlib", self.package["name"])
        self.assertEqual("osx", self.package["platform"])

    def test_contains_empty_depends(self):
        self.assertIsInstance(self.package["depends"], list)
