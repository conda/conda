import json
from unittest import TestCase

from conda import text_type
from conda._vendor.auxlib.ish import dals
from conda.base.context import reset_context
from conda.common.io import captured, env_var, replace_log_streams
from conda.exceptions import CommandNotFoundError, CondaAssertionError, CondaCorruptEnvironmentError, MD5MismatchError, \
    conda_exception_handler, CondaHTTPError, PackageNotFoundError


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
        assert json_obj['error'] == repr(exc)
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
          download saved to: /some/path/on/disk/another-name.tar.bz2
          expected md5 sum: abc123
          actual md5 sum: deadbeef
        """).strip()


    def PackageNotFoundError(self):
        package_name = "Groot"
        exc = PackageNotFoundError(package_name)
        with env_var("CONDA_JSON", "yes", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.PackageNotFoundError'>"
        assert json_obj['message'] == text_type(exc)
        assert json_obj['package_name'] == package_name
        assert json_obj['error'] == repr(exc)

        with env_var("CONDA_JSON", "no", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == "Package not found: Conda could not find Groot"



    def test_CondaHTTPError(self):
        url = "https://download.url/path/to/groot.tar.gz"
        status_code = "Groot"
        reason = "COULD NOT CONNECT"
        elapsed_time = 1.24
        exc = CondaHTTPError(url, status_code, reason, elapsed_time)

        with env_var("CONDA_JSON", "yes", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

            json_obj = json.loads(c.stdout)
            assert not c.stderr
            assert json_obj['exception_type'] == "<class 'conda.exceptions.CondaHTTPError'>"
            assert json_obj['exception_name'] == 'CondaHTTPError'
            assert json_obj['message'] == text_type(exc)
            assert json_obj['error'] == repr(exc)
            assert json_obj['url'] == url
            assert json_obj['status_code'] == status_code
            assert json_obj['reason'] == reason
            assert json_obj['elapsed_time'] == elapsed_time

        with env_var("CONDA_JSON", "no", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == dals("""
                CondaHTTPError: HTTP Groot COULD NOT CONNECT for url <https://download.url/path/to/groot.tar.gz>
                Elapsed: 1.24
                """).strip()


    def test_CommandNotFoundError(self):
        cmd = "instate"
        message = "hello"
        exc = CommandNotFoundError(cmd)

        with env_var("CONDA_JSON", "yes", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.CommandNotFoundError'>"
        assert json_obj['message'] == text_type(exc)
        assert json_obj['error'] == repr(exc)

        with env_var("CONDA_JSON", "no", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == "CommandNotFoundError: Conda could not find the command: 'instate'"


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
