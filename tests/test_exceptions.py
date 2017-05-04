import json
from unittest import TestCase

from conda.common.compat import on_win

from conda import text_type
from conda._vendor.auxlib.ish import dals
from conda.base.context import reset_context, context
from conda.common.io import captured, env_var, replace_log_streams
from conda.exceptions import CommandNotFoundError, CondaFileNotFoundError, CondaHTTPError, CondaKeyError, \
    CondaRevisionError, DirectoryNotFoundError, MD5MismatchError, PackageNotFoundError, TooFewArgumentsError, \
    TooManyArgumentsError, conda_exception_handler, BasicClobberError, KnownPackageClobberError, \
    UnknownPackageClobberError, SharedLinkPathClobberError, BinaryPrefixReplacementError, BinaryPrefixReplacementError


def _raise_helper(exception):
    raise exception


class ExceptionTests(TestCase):

    def test_TooManyArgumentsError(self):
        expected = 2
        received = 5
        offending_arguments = "groot"
        exc = TooManyArgumentsError(expected, received, offending_arguments)
        with env_var("CONDA_JSON", "yes", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.TooManyArgumentsError'>"
        assert json_obj['exception_name'] == 'TooManyArgumentsError'
        assert json_obj['message'] == text_type(exc)
        assert json_obj['error'] == repr(exc)
        assert json_obj['expected'] == 2
        assert json_obj['received'] == 5
        assert json_obj['offending_arguments'] == "groot"

        with env_var("CONDA_JSON", "no", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == "TooManyArgumentsError:  Got 5 arguments (g, r, o, o, t) but expected 2."

    def test_TooFewArgumentsError(self):
        expected = 5
        received = 2
        exc = TooFewArgumentsError(expected, received)
        with env_var("CONDA_JSON", "yes", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.TooFewArgumentsError'>"
        assert json_obj['exception_name'] == 'TooFewArgumentsError'
        assert json_obj['message'] == text_type(exc)
        assert json_obj['error'] == repr(exc)
        assert json_obj['expected'] == 5
        assert json_obj['received'] == 2

        with env_var("CONDA_JSON", "no", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == "TooFewArgumentsError:  Got 2 arguments but expected 5."

    def test_BasicClobberError(self):
        source_path = "some/path/on/goodwin.ave"
        target_path = "some/path/to/wright.st"
        exc = BasicClobberError(source_path, target_path, context)
        with env_var("CONDA_PATH_CONFLICT", "prevent", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == dals("""
        ClobberError: Conda was asked to clobber an existing path.
          source path: some/path/on/goodwin.ave
          target path: some/path/to/wright.st
        """).strip()

    def test_KnownPackageClobberError(self):
        target_path = "some/where/on/goodwin.ave"
        colliding_dist_being_linked = "Groot"
        colliding_linked_dist = "Liquid"
        exc = KnownPackageClobberError(target_path, colliding_dist_being_linked, colliding_linked_dist, context)
        with env_var("CONDA_PATH_CONFLICT", "prevent", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == dals("""
        ClobberError: The package 'Groot' cannot be installed due to a
        path collision for 'some/where/on/goodwin.ave'.
        This path already exists in the target prefix, and it won't be removed by
        an uninstall action in this transaction. The path appears to be coming from
        the package 'Liquid', which is already installed in the prefix.
        """).strip()

    def test_UnknownPackageClobberError(self):
        target_path = "siebel/center/for/c.s"
        colliding_dist_being_linked = "Groot"
        exc = UnknownPackageClobberError(target_path, colliding_dist_being_linked, context)
        with env_var("CONDA_PATH_CONFLICT", "prevent", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == dals("""
        ClobberError: The package 'Groot' cannot be installed due to a
        path collision for 'siebel/center/for/c.s'.
        This path already exists in the target prefix, and it won't be removed
        by an uninstall action in this transaction. The path is one that conda
        doesn't recognize. It may have been created by another package manager.
        """).strip()

    def test_SharedLinkPathClobberError(self):
        target_path = "some/where/in/shampoo/banana"
        incompatible_package_dists = "Groot"
        exc = SharedLinkPathClobberError(target_path, incompatible_package_dists, context)
        with env_var("CONDA_PATH_CONFLICT", "prevent", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == dals("""
        ClobberError: This transaction has incompatible packages due to a shared path.
          packages: G, r, o, o, t
          path: 'some/where/in/shampoo/banana'
        """).strip()


    def test_CondaFileNotFoundError(self):
        filename = "Groot"
        exc = CondaFileNotFoundError(filename)
        with env_var("CONDA_JSON", "yes", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.CondaFileNotFoundError'>"
        assert json_obj['exception_name'] == 'CondaFileNotFoundError'
        assert json_obj['message'] == text_type(exc)
        assert json_obj['error'] == repr(exc)

        with env_var("CONDA_JSON", "no", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == "CondaFileNotFoundError: 'Groot'."

    def test_DirectoryNotFoundError(self):
        directory = "Groot"
        exc = DirectoryNotFoundError(directory)
        with env_var("CONDA_JSON", "yes", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.DirectoryNotFoundError'>"
        assert json_obj['exception_name'] == 'DirectoryNotFoundError'
        assert json_obj['message'] == text_type(exc)
        assert json_obj['error'] == repr(exc)
        assert json_obj['directory'] == "Groot"

        with env_var("CONDA_JSON", "no", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == "DirectoryNotFoundError: 'Groot'"

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
        package = "Groot"
        exc = PackageNotFoundError(package)
        with env_var("CONDA_JSON", "yes", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.PackageNotFoundError'>"
        assert json_obj['message'] == text_type(exc)
        assert json_obj['package_name'] == package
        assert json_obj['error'] == repr(exc)

        with env_var("CONDA_JSON", "no", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == "Package not found: Conda could not find Groot"

    def test_CondaRevisionError(self):
        message = "Groot"
        exc = CondaRevisionError(message)
        with env_var("CONDA_JSON", "yes", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.CondaRevisionError'>"
        assert json_obj['exception_name'] == 'CondaRevisionError'
        assert json_obj['message'] == text_type(exc)
        assert json_obj['error'] == repr(exc)

        with env_var("CONDA_JSON", "no", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == "CondaRevisionError: Groot."

    def test_CondaKeyError(self):
        key = "Groot"
        message = "Groot is not a key."
        exc = CondaKeyError(key, message)
        with env_var("CONDA_JSON", "yes", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.CondaKeyError'>"
        assert json_obj['exception_name'] == 'CondaKeyError'
        assert json_obj['message'] == text_type(exc)
        assert json_obj['error'] == repr(exc)
        assert json_obj['key'] == "Groot"

        with env_var("CONDA_JSON", "no", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == "CondaKeyError: 'Groot': Groot is not a key."

    def test_CondaHTTPError(self):
        msg = "Groot"
        url = "https://download.url/path/to/groot.tar.gz"
        status_code = "Groot"
        reason = "COULD NOT CONNECT"
        elapsed_time = 1.24
        exc = CondaHTTPError(msg, url, status_code, reason, elapsed_time)

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

                Groot
                """).strip()

    def test_CommandNotFoundError_simple(self):
        cmd = "instate"
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
        assert c.stderr.strip() == "CommandNotFoundError: 'instate'"

    def test_CommandNotFoundError_conda_build(self):
        cmd = "build"
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
        assert c.stderr.strip() == ("CommandNotFoundError: You need to install conda-build in order to\n" \
                                    "use the 'conda build' command.")

    def test_CommandNotFoundError_activate(self):
        cmd = "activate"
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

        if on_win:
            message = "CommandNotFoundError: 'activate'"
        else:
            message = ("CommandNotFoundError: 'activate is not a conda command.\n"
                       "Did you mean 'source activate'?")
        assert c.stderr.strip() == message

    def test_BinaryPrefixReplacementError(self):
        new_data_length = 1104
        original_data_length = 1404
        new_prefix = "some/where/on/goodwin.ave"
        path = "some/where/by/boneyard/creek"
        placeholder = "save/my/spot/in/374"
        exc = BinaryPrefixReplacementError(path, placeholder, new_prefix,
                                           original_data_length, new_data_length)
        with env_var("CONDA_JSON", "yes", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.BinaryPrefixReplacementError'>"
        assert json_obj['exception_name'] == 'BinaryPrefixReplacementError'
        assert json_obj['message'] == text_type(exc)
        assert json_obj['error'] == repr(exc)
        assert json_obj['new_data_length'] == 1104
        assert json_obj['original_data_length'] == 1404
        assert json_obj['new_prefix'] == new_prefix
        assert json_obj['path'] == path
        assert json_obj['placeholder'] == placeholder

        with env_var("CONDA_JSON", "no", reset_context):
            with captured() as c, replace_log_streams():
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == dals("""
        BinaryPrefixReplacementError: Refusing to replace mismatched data length in binary file.
          path: some/where/by/boneyard/creek
          placeholder: save/my/spot/in/374
          new prefix: some/where/on/goodwin.ave
          original data Length: 1404
          new data length: 1104
        """).strip()
