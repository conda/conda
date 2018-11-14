from conda import utils
from conda.common.path import win_path_to_unix
from .helpers import assert_equals

SOME_PREFIX = "/some/prefix"
SOME_FILES = ["a", "b", "c"]


def test_path_translations():
    paths = [
        (r"z:\miniconda\Scripts\pip.exe",
         "/z/miniconda/Scripts/pip.exe",
         "/cygdrive/z/miniconda/Scripts/pip.exe"),
        (r"z:\miniconda;z:\Documents (x86)\pip.exe;c:\test",
         "/z/miniconda:/z/Documents (x86)/pip.exe:/c/test",
         "/cygdrive/z/miniconda:/cygdrive/z/Documents (x86)/pip.exe:/cygdrive/c/test"),
        # Failures:
        # (r"z:\miniconda\Scripts\pip.exe",
        #  "/z/miniconda/Scripts/pip.exe",
        #  "/cygdrive/z/miniconda/Scripts/pip.exe"),

        # ("z:\\miniconda\\",
        #  "/z/miniconda/",
        #  "/cygdrive/z/miniconda/"),
        ("test dummy text /usr/bin;z:\\documents (x86)\\code\\conda\\tests\\envskhkzts\\test1;z:\\documents\\code\\conda\\tests\\envskhkzts\\test1\\cmd more dummy text",
        "test dummy text /usr/bin:/z/documents (x86)/code/conda/tests/envskhkzts/test1:/z/documents/code/conda/tests/envskhkzts/test1/cmd more dummy text",
        "test dummy text /usr/bin:/cygdrive/z/documents (x86)/code/conda/tests/envskhkzts/test1:/cygdrive/z/documents/code/conda/tests/envskhkzts/test1/cmd more dummy text"),
    ]
    for windows_path, unix_path, cygwin_path in paths:
        assert win_path_to_unix(windows_path) == unix_path
        assert utils.unix_path_to_win(unix_path) == windows_path

        # assert utils.win_path_to_cygwin(windows_path) == cygwin_path
        # assert utils.cygwin_path_to_win(cygwin_path) == windows_path


def test_text_translations():
    test_win_text = "z:\\msarahan\\code\\conda\\tests\\envsk5_b4i\\test 1"
    test_unix_text = "/z/msarahan/code/conda/tests/envsk5_b4i/test 1"
    assert_equals(test_win_text, utils.unix_path_to_win(test_unix_text))
    assert_equals(test_unix_text, win_path_to_unix(test_win_text))
