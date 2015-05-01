import random
import unittest

from conda import exceptions


class InvalidExceptionTestCase(unittest.TestCase):
    def test_requires_an_instruction(self):
        with self.assertRaises(TypeError):
            exceptions.InvalidInstruction()

    def test_extends_from_conda_exception(self):
        e = exceptions.InvalidInstruction("foo")
        self.assertIsInstance(e, exceptions.CondaException)

    def test_creates_message_with_instruction_name(self):
        random_instruction = random.randint(100, 200)
        e = exceptions.InvalidInstruction(random_instruction)
        expected = "No handler for instruction: %s" % random_instruction
        self.assertEqual(expected, str(e))


class UnableToWriteToPackageExceptionTestCase(unittest.TestCase):

    def test_requires_a_package(self):
        with self.assertRaises(TypeError):
            exceptions.UnableToWriteToPackage()

    def test_extends_from_conda_exception(self):
        e = exceptions.UnableToWriteToPackage("foo")
        self.assertIsInstance(e, exceptions.CondaException)

    def test_extends_from_runtime_error(self):
        e = exceptions.UnableToWriteToPackage("bar")
        self.assertIsInstance(e, RuntimeError)

    def test_creates_expected_message(self):
        pkg = "foobar_%s" % random.randint(100, 200)
        expected = (
            "Unable to remove files for package: {pkg_name}\n\n"
            "Please close all processes running code from {pkg_name} and "
            "try again.\n"
        ).format(pkg_name=pkg)
        e = exceptions.UnableToWriteToPackage(pkg)
        self.assertEqual(expected, str(e))
