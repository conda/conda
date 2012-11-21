# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from distutils.version import LooseVersion
import json
from os.path import dirname, join
import unittest

from conda.package import (
    group_packages_by_name, newest_packages, package, sort_packages_by_name
)



with open(join(dirname(__file__), 'index.json')) as fi:
    info = json.load(fi)


class test_package(unittest.TestCase):

    def test_(self):
        pass

    def test_is_meta(self):
        self.assertEqual(
            package(info["baz-2.0.1-0.tar.bz2"]).is_meta,
            False
        )
        # test with empty requires set
        self.assertEqual(
            package(info["foo-0.8.0-0.tar.bz2"]).is_meta,
            False
        )
        self.assertEqual(
            package(info["meta-0.2-0.tar.bz2"]).is_meta,
            True
        )


class test_sort_packages_by_name(unittest.TestCase):

    def test_simple(self):
        bar, baz, foo = (
            package(info["bar-1.1-0.tar.bz2"]),
            package(info["baz-2.0-0.tar.bz2"]),
            package(info["foo-0.8.0-0.tar.bz2"]),
        )
        pkgs = [foo, baz, bar]
        self.assertEqual(
            sort_packages_by_name(pkgs),
            [bar, baz, foo]
        )

    def test_reverse(self):
        bar, baz, foo = (
            package(info["bar-1.1-0.tar.bz2"]),
            package(info["baz-2.0-0.tar.bz2"]),
            package(info["foo-0.8.0-0.tar.bz2"]),
        )
        pkgs = [foo, baz, bar]
        self.assertEqual(
            sort_packages_by_name(pkgs, reverse=True),
            [foo, baz, bar]
        )


class test_group_packages_by_name(unittest.TestCase):

    def test_simple(self):
        f1, f2, f3, b1, b2, m  = [
            package(info["foo-0.8.0-0.tar.bz2"]),
            package(info["foo-0.8.0-1.tar.bz2"]),
            package(info["foo-0.9.0-0.tar.bz2"]),
            package(info["bar-1.0-0.tar.bz2"]),
            package(info["bar-1.1-0.tar.bz2"]),
            package(info["meta-0.2-0.tar.bz2"]),
        ]
        pkgs = [f2, f1, b2, f3, b1, m]
        self.assertEqual(
            group_packages_by_name(pkgs),
            {
                'foo' : set([f1, f2, f3]),
                'bar' : set([b1, b2]),
                'meta' : set([m]),
            }
        )


class test_find_newest_packages(unittest.TestCase):

    def test_simple(self):
        f1, f2, b1, b2, m  = [
            package(info["foo-0.8.0-0.tar.bz2"]),
            package(info["foo-0.8.0-1.tar.bz2"]),
            package(info["bar-1.0-0.tar.bz2"]),
            package(info["bar-1.1-0.tar.bz2"]),
            package(info["meta-0.2-0.tar.bz2"]),
        ]
        pkgs = [f2, f1, b2, b1, m]
        self.assertEqual(
            newest_packages(pkgs),
            set([f2, b2, m])
        )


if __name__ == '__main__':
    unittest.main()
