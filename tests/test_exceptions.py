import random
import unittest

import conda
from conda.exceptions import CondaAssertionError, CondaCorruptEnvironmentError


def test_conda_assertion_error():
    try:
        raise CondaAssertionError("message", 1, 2)
    except CondaAssertionError as err:
        assert str(err) == "Assertion error: message expected 1 and got 2"


def test_conda_corrupt_environment_exception():
    try:
        raise CondaCorruptEnvironmentError("Oh noes corrupt environment")
    except CondaCorruptEnvironmentError as err:
        assert str(err) == "Corrupt environment error: Oh noes corrupt environment"

# class InvalidInstructionTestCase(unittest.TestCase):
#     def test_requires_an_instruction(self):
#         with self.assertRaises(TypeError):
#             exceptions.InvalidInstruction()
#
#     def test_extends_from_conda_exception(self):
#         e = exceptions.InvalidInstruction("foo")
#         self.assertIsInstance(e, conda.CondaError)
#
#     def test_creates_message_with_instruction_name(self):
#         random_instruction = random.randint(100, 200)
#         e = exceptions.InvalidInstruction(random_instruction)
#         expected = "No handler for instruction: %s\n" % random_instruction
#         self.assertEqual(expected, str(e))


# class CondaErrorTestCase(unittest.TestCase):
#     def test_repr_is_correct(self):
#         e = conda.CondaError("Can't do that")
#         self.assertEqual(repr(e), "CondaError: Can't do that\n")
#
#     def test_inherited_repr_is_correct(self):
#         try:
#             raise exceptions.CondaValueError('value incorrect')
#         except exceptions.CondaValueError as e:
#             err = conda.CondaError("Can't do that %s" % e)
#
#         self.assertEqual(repr(err), "CondaError: Can't do that Value error: value incorrect\n\n")
#
#     def test_str_is_correct(self):
#         e = conda.CondaError("Can't do that")
#         self.assertEqual(str(e), "Can't do that\n")
#
#     def test_inherited_str_is_correct(self):
#         try:
#             raise exceptions.CondaValueError('value incorrect')
#         except exceptions.CondaValueError as e:
#             err = conda.CondaError("Can't do that %s" % e)
#
#         self.assertEqual(str(err), "Can't do that Value error: value incorrect\n\n")
