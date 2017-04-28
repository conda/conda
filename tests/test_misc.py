import os.path
import sys
import unittest

from conda.core.repodata import cache_fn_url
from conda.misc import url_pat, walk_prefix


class TestMisc(unittest.TestCase):

    def test_cache_fn_url(self):
        url = "http://repo.continuum.io/pkgs/pro/osx-64/"
        self.assertEqual(cache_fn_url(url), '7618c8b6.json')

    def test_url_pat_1(self):
        m = url_pat.match('http://www.cont.io/pkgs/linux-64/foo.tar.bz2'
                          '#d6918b03927360aa1e57c0188dcb781b')
        self.assertEqual(m.group('url_p'), 'http://www.cont.io/pkgs/linux-64')
        self.assertEqual(m.group('fn'), 'foo.tar.bz2')
        self.assertEqual(m.group('md5'), 'd6918b03927360aa1e57c0188dcb781b')

    def test_url_pat_2(self):
        m = url_pat.match('http://www.cont.io/pkgs/linux-64/foo.tar.bz2')
        self.assertEqual(m.group('url_p'), 'http://www.cont.io/pkgs/linux-64')
        self.assertEqual(m.group('fn'), 'foo.tar.bz2')
        self.assertEqual(m.group('md5'), None)

    def test_url_pat_3(self):
        m = url_pat.match('http://www.cont.io/pkgs/linux-64/foo.tar.bz2#1234')
        self.assertEqual(m, None)


def make_mock_directory(tmpdir, mock_directory):
    for key, value in mock_directory.items():
        if value is None:
            tmpdir.join(key).write("TEST")
        else:
            make_mock_directory(tmpdir.mkdir(key), value)


def test_walk_prefix(tmpdir):  # tmpdir is a py.test utility
    # Each directory is a dict whose keys are names. If the value is
    # None, then that key represents a file. If it's another dict, that key is
    # a file
    mock_directory = {
        "LICENSE.txt": None,
        "envs": {"ignore1": None,
                 "ignore2": None},
        "python.app": None,
        "bin": {"activate": None,
                "conda": None,
                "deactivate": None,
                "testfile": None},
        "testdir1": {"testfile": None,
                     "testdir2": {"testfile": None}},
        "testfile1": None,
    }

    make_mock_directory(tmpdir, mock_directory)

    # walk_prefix has windows_forward_slahes on by default, so we don't need
    # any special-casing there

    answer = {"testfile1", "bin/testfile", "testdir1/testfile",
              "testdir1/testdir2/testfile"}
    if sys.platform != "darwin":
        answer.add("python.app")

    assert walk_prefix(tmpdir.strpath) == answer


if __name__ == '__main__':
    unittest.main()
