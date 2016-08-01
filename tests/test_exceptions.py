import random
import unittest

import conda
from conda import exceptions


class InvalidInstructionTestCase(unittest.TestCase):
    def test_requires_an_instruction(self):
        with self.assertRaises(TypeError):
            exceptions.InvalidInstruction()

    def test_extends_from_conda_exception(self):
        e = exceptions.InvalidInstruction("foo")
        self.assertIsInstance(e, conda.CondaError)

    def test_creates_message_with_instruction_name(self):
        random_instruction = random.randint(100, 200)
        e = exceptions.InvalidInstruction(random_instruction)
        expected = "No handler for instruction: %s\n" % random_instruction
        self.assertEqual(expected, str(e))


class CondaErrorTestCase(unittest.TestCase):
    def test_repr_is_correct(self):
        e = conda.CondaError("Can't do that")
        self.assertEqual(repr(e), "CondaError: Can't do that\n")

    def test_inherited_repr_is_correct(self):
        try:
            raise exceptions.CondaValueError('value incorrect')
        except exceptions.CondaValueError as e:
            err = conda.CondaError("Can't do that %s" % e)

        self.assertEqual(repr(err), "CondaError: Can't do that Value error: value incorrect\n\n")

    def test_str_is_correct(self):
        e = conda.CondaError("Can't do that")
        self.assertEqual(str(e), "Can't do that\n")

    def test_inherited_str_is_correct(self):
        try:
            raise exceptions.CondaValueError('value incorrect')
        except exceptions.CondaValueError as e:
            err = conda.CondaError("Can't do that %s" % e)

        self.assertEqual(str(err), "Can't do that Value error: value incorrect\n\n")
