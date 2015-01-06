import random
import unittest

from conda import exceptions
from conda import packages

from . import helpers


class PackageTestCase(unittest.TestCase):
    def test_acts_as_a_dictionary(self):
        r = random.randint(1000, 2000)
        p = packages.Package(foo="bar", random=r)

        self.assertEqual(p["foo"], "bar")
        self.assertEqual(r, p["random"])

    def test_depends_is_always_present(self):
        p = packages.Package(name="foobar")
        self.assertIn("depends", p)

    def test_depends_defaults_to_empty_array(self):
        p = packages.Package(name="foobar")
        self.assertEqual([], p["depends"])

    def test_allows_depends_to_come_through(self):
        expected = ["foo 1.2.3", "bar 1.2.%s" % random.randint(100, 200)]
        p = packages.Package(depends=expected)
        self.assertIn(expected[0], p["depends"])
        self.assertIn(expected[1], p["depends"])



class from_file_TestCase(unittest.TestCase):
    def test_raises_exception_on_file_not_found(self):
        with self.assertRaises(exceptions.FileNotFound):
            unknown = helpers.support_file("unknown")
            packages.from_file(unknown)


class PackageFromFileWithNoDepends(unittest.TestCase):
    @classmethod
    def setup_class(self):
        filename = helpers.support_file("zlib-bad.json")
        self.package = packages.from_file(filename)

    def test_is_instance_of_package(self):
        self.assertIsInstance(self.package, packages.Package)

    def test_contains_expected_name_and_platform(self):
        self.assertEqual("zlib", self.package["name"])
        self.assertEqual("osx", self.package["platform"])

    def test_contains_empty_depends(self):
        self.assertIsInstance(self.package["depends"], list)


class PackageFromFileWithDepends(unittest.TestCase):
    @classmethod
    def setup_class(self):
        filename = helpers.support_file("zlib.json")
        self.package = packages.from_file(filename)

    def test_is_instance_of_package(self):
        self.assertIsInstance(self.package, packages.Package)

    def test_contains_expected_name_and_platform(self):
        self.assertEqual("zlib", self.package["name"])
        self.assertEqual("osx", self.package["platform"])

    def test_contains_empty_depends(self):
        self.assertIsInstance(self.package["depends"], list)
