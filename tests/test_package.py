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
    group_packages_by_name, newest_packages, Package, sort_packages_by_name
)



with open(join(dirname(__file__), 'index.json')) as fi:
    info = json.load(fi)


class TestPackage(unittest.TestCase):

    def test_is_meta(self):
        self.assertEqual(
            Package(info["baz-2.0.1-0.tar.bz2"]).is_meta,
            False
        )
        # test with empty requires set
        self.assertEqual(
            Package(info["foo-0.8.0-0.tar.bz2"]).is_meta,
            False
        )
        self.assertEqual(
            Package(info["meta-0.2-0.tar.bz2"]).is_meta,
            True
        )

    def test_order_with_build_target(self):
        none, ce, pro, w = (
            Package(info["baz-2.0.1-0.tar.bz2"]),
            Package(info["baz-2.0.1-ce0.tar.bz2"]),
            Package(info["baz-2.0.1-pro0.tar.bz2"]),
            Package(info["baz-2.0.1-w0.tar.bz2"]),
        )
        self.assertTrue(none < ce)
        self.assertTrue(ce < pro)
        self.assertTrue(pro < w)


class TestSortPackagesByName(unittest.TestCase):

    def test_simple(self):
        bar, baz, foo = (
            Package(info["bar-1.1-0.tar.bz2"]),
            Package(info["baz-2.0-0.tar.bz2"]),
            Package(info["foo-0.8.0-0.tar.bz2"]),
        )
        pkgs = [foo, baz, bar]
        self.assertEqual(
            sort_packages_by_name(pkgs),
            [bar, baz, foo]
        )

    def test_reverse(self):
        bar, baz, foo = (
            Package(info["bar-1.1-0.tar.bz2"]),
            Package(info["baz-2.0-0.tar.bz2"]),
            Package(info["foo-0.8.0-0.tar.bz2"]),
        )
        pkgs = [foo, baz, bar]
        self.assertEqual(
            sort_packages_by_name(pkgs),
            [bar, baz, foo]
        )

    def test_with_build_target(self):
        bar, b1, b2, b3, b4, foo = (
            Package(info["bar-1.1-0.tar.bz2"]),
            Package(info["baz-2.0.1-0.tar.bz2"]),
            Package(info["baz-2.0.1-ce0.tar.bz2"]),
            Package(info["baz-2.0.1-pro0.tar.bz2"]),
            Package(info["baz-2.0.1-w0.tar.bz2"]),
            Package(info["foo-0.8.0-0.tar.bz2"]),
        )
        pkgs = [b4, b2, foo, b1, bar, b3]
        self.assertEqual(
            sort_packages_by_name(pkgs),
            [bar, b1, b2, b3, b4, foo]
        )


class TestGroupPackagesByName(unittest.TestCase):

    def test_simple(self):
        f1, f2, f3, b1, b2, m  = [
            Package(info["foo-0.8.0-0.tar.bz2"]),
            Package(info["foo-0.8.0-1.tar.bz2"]),
            Package(info["foo-0.9.0-0.tar.bz2"]),
            Package(info["bar-1.0-0.tar.bz2"]),
            Package(info["bar-1.1-0.tar.bz2"]),
            Package(info["meta-0.2-0.tar.bz2"]),
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

    def test_with_build_target(self):
        f1, f2, f3, b1, b2, b3, b4, m  = [
            Package(info["foo-0.8.0-0.tar.bz2"]),
            Package(info["foo-0.8.0-1.tar.bz2"]),
            Package(info["foo-0.9.0-0.tar.bz2"]),
            Package(info["baz-2.0.1-0.tar.bz2"]),
            Package(info["baz-2.0.1-ce0.tar.bz2"]),
            Package(info["baz-2.0.1-pro0.tar.bz2"]),
            Package(info["baz-2.0.1-w0.tar.bz2"]),
            Package(info["meta-0.2-0.tar.bz2"]),
        ]
        pkgs = [f2, f1, b2, f3, b1, m, b4, b3]
        self.assertEqual(
            group_packages_by_name(pkgs),
            {
                'foo' : set([f1, f2, f3]),
                'baz' : set([b1, b2, b3, b4]),
                'meta' : set([m]),
            }
        )


class TestFindNewestPackages(unittest.TestCase):

    def test_simple(self):
        f1, f2, b1, b2, m  = [
            Package(info["foo-0.8.0-0.tar.bz2"]),
            Package(info["foo-0.8.0-1.tar.bz2"]),
            Package(info["bar-1.0-0.tar.bz2"]),
            Package(info["bar-1.1-0.tar.bz2"]),
            Package(info["meta-0.2-0.tar.bz2"]),
        ]
        pkgs = [f2, f1, b2, b1, m]
        self.assertEqual(
            newest_packages(pkgs),
            set([f2, b2, m])
        )

    def test_with_build_target(self):
        f1, f2, f3, b1, b2, b3, b4, m  = [
            Package(info["foo-0.8.0-0.tar.bz2"]),
            Package(info["foo-0.8.0-1.tar.bz2"]),
            Package(info["foo-0.9.0-0.tar.bz2"]),
            Package(info["baz-2.0.1-0.tar.bz2"]),
            Package(info["baz-2.0.1-ce0.tar.bz2"]),
            Package(info["baz-2.0.1-pro0.tar.bz2"]),
            Package(info["baz-2.0.1-w0.tar.bz2"]),
            Package(info["meta-0.2-0.tar.bz2"]),
        ]
        pkgs = [f2, f1, b2, f3, b1, m, b4, b3]
        self.assertEqual(
            newest_packages(pkgs),
            set([f3, b4, m])
        )


if __name__ == '__main__':
    unittest.main()
