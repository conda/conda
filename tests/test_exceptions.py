import random
import unittest

from conda import exceptions


class InvalidExceptionTestCase(unittest.TestCase):
    def test_requires_an_instruction(self):
        with self.assertRaises(TypeError):
            exceptions.InvalidInstruction()

    def test_extends_from_conda_exception(self):
        e = exceptions.InvalidInstruction("foo")
        self.assertIsInstance(e, exceptions.CondaError)

    def test_creates_message_with_instruction_name(self):
        random_instruction = random.randint(100, 200)
        e = exceptions.InvalidInstruction(random_instruction)
        expected = "No handler for instruction: %s" % random_instruction
        self.assertEqual(expected, str(e))


def test_lockerror_hierarchy():
    assert issubclass(exceptions.LockError, exceptions.CondaError)
    assert issubclass(exceptions.LockError, RuntimeError)
