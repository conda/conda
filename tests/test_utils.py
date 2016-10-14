from .helpers import assert_equals

from conda import utils

SOME_PREFIX = "/some/prefix"
SOME_FILES = ["a", "b", "c"]


def test_path_translations():
    paths = [
        (r";z:\miniconda\Scripts\pip.exe",
         ":/z/miniconda/Scripts/pip.exe",
         ":/cygdrive/z/miniconda/Scripts/pip.exe"),
        (r";z:\miniconda;z:\Documents (x86)\pip.exe;C:\test",
         ":/z/miniconda:/z/Documents (x86)/pip.exe:/C/test",
         ":/cygdrive/z/miniconda:/cygdrive/z/Documents (x86)/pip.exe:/cygdrive/C/test"),
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
        win2unix = utils.win_path_to_unix(windows_path)
        unix2win = utils.unix_path_to_win(unix_path)

        win2cygwin = utils.win_path_to_cygwin(windows_path)
        cygwin2win = utils.cygwin_path_to_win(cygwin_path)

        print("win2unix == unix_path :: {} == {} :: {}".format(
            win2unix,
            unix_path,
            win2unix == unix_path))
        print("unix2win == windows_path :: {} == {} :: {}".format(
            unix2win,
            windows_path,
            unix2win == windows_path))

        print("win2cygwin == cygwin_path :: {} == {} :: {}".format(
            win2cygwin,
            cygwin_path,
            win2cygwin == cygwin_path))
        print("cygwin2win == windows_path :: {} == {} :: {}".format(
            cygwin2win,
            windows_path,
            cygwin2win == windows_path))

        assert win2unix == unix_path
        assert unix2win == windows_path

        assert win2cygwin == cygwin_path
        assert cygwin2win == windows_path


def test_text_translations():
    test_win_text = "prepending z:\\msarahan\\code\\conda\\tests\\envsk5_b4i\\test 1 and z:\\msarahan\\code\\conda\\tests\\envsk5_b4i\\test 1\\scripts to path"
    test_unix_text = "prepending /z/msarahan/code/conda/tests/envsk5_b4i/test 1 and /z/msarahan/code/conda/tests/envsk5_b4i/test 1/scripts to path"
    assert_equals(test_win_text, utils.unix_path_to_win(test_unix_text))
    assert_equals(test_unix_text, utils.win_path_to_unix(test_win_text))
