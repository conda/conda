import json
import random
from unittest import TestCase

from conda._vendor.auxlib.ish import dals

from conda.common.compat import text_type

from conda.base.context import reset_context
from conda.common.io import env_var, captured, replace_log_streams

import conda
from conda.exceptions import CondaAssertionError, CondaCorruptEnvironmentError, MD5MismatchError, \
    conda_exception_handler


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


def _raise_helper(exception):
    raise exception


class ExceptionTests(TestCase):

    def test_MD5MismatchError(self):
        url = "https://download.url/path/to/file.tar.bz2"
        target_full_path = "/some/path/on/disk/another-name.tar.bz2"
        expected_md5sum = "abc123"
        actual_md5sum = "deadbeef"
        exc = MD5MismatchError(url, target_full_path, expected_md5sum, actual_md5sum)

        with env_var("CONDA_JSON", "yes", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.MD5MismatchError'>"
        assert json_obj['exception_name'] == 'MD5MismatchError'
        assert json_obj['message'] == text_type(exc)
        assert json_obj['error'] ==  repr(exc)
        assert json_obj['url'] == url
        assert json_obj['target_full_path'] == target_full_path
        assert json_obj['expected_md5sum'] == expected_md5sum
        assert json_obj['actual_md5sum'] == actual_md5sum

        with env_var("CONDA_JSON", "no", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == dals("""
        MD5MismatchError: Conda detected a mismatch between the expected content and downloaded content
        for url 'https://download.url/path/to/file.tar.bz2'.
        Conda saved the downloaded file to '/some/path/on/disk/another-name.tar.bz2'.
        Expected md5 sum: abc123
        Actual md5 sum: deadbeef
        """).strip()


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
