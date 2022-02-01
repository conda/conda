# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import codecs
import sys
import unittest

from conda.core.subdir_data import cache_fn_url
from conda.misc import url_pat, walk_prefix
from conda.utils import Utf8NamedTemporaryFile

class TestMisc(unittest.TestCase):

    def test_Utf8NamedTemporaryFile(self):
        test_string = 'ōγђ家固한áêñßôç'
        try:
            with Utf8NamedTemporaryFile(delete=False) as tf:
                tf.write(test_string.encode('utf-8') if hasattr(test_string, 'encode') else test_string)
                fname = tf.name
            with codecs.open(fname, mode='rb', encoding='utf-8') as fh:
                value = fh.read()
            assert value == test_string
        except Exception as e:
            raise e

    def test_cache_fn_url(self):
        url = "http://repo.continuum.io/pkgs/pro/osx-64/"
        # implicit repodata.json
        self.assertEqual(cache_fn_url(url), '7618c8b6.json')
        # explicit repodata.json
        self.assertEqual(cache_fn_url(url, 'repodata.json'), '7618c8b6.json')
        # explicit current_repodata.json
        self.assertEqual(cache_fn_url(url, "current_repodata.json"), '8be5dc16.json')
        url = "http://repo.anaconda.com/pkgs/pro/osx-64/"
        self.assertEqual(cache_fn_url(url), 'e42afea8.json')

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
