# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import unittest
import json
from os.path import dirname, join

from conda.naming import parse_package_filename
from conda.package import package
from conda.package_index import package_index
from conda.package_spec import package_spec


class test_package_index(unittest.TestCase):

    def setUp(self):
        path = join(dirname(__file__), 'index.json')
        with open(path) as fi:
            self.info = json.load(fi)

    def test_create_from_local(self):
        idx = package_index(self.info)

    def test_lookup_from_filename(self):
        idx = package_index(self.info)
        for pkg_filename in self.info:
            self.assertEqual(
                idx.lookup_from_filename(pkg_filename),
                package(self.info[pkg_filename])
            )

    def test_lookup_from_name(self):
        idx = package_index(self.info)

        name_count = {}
        names = set()
        for pkg_filename in self.info:
            name, version, build = parse_package_filename(pkg_filename)
            name_count[name] = name_count.get(name, 0) + 1

        for name in names:
            self.assertEqual(name_count[name], len(idx.lookup_from_name(name)))

    def test_get_deps(self):
        idx = package_index(self.info)
        self.assertEqual(
            idx.get_deps([package(self.info['foo-0.8.0-0.tar.bz2'])]),
            set()
        )
        self.assertEqual(
            idx.get_deps([package(self.info['baz-2.0.1-0.tar.bz2'])], 0),
            set([
                package(self.info['bar-1.1-0.tar.bz2']),
                package(self.info['foo-1.0.0-0.tar.bz2'])
            ])
        )
        self.assertEqual(
            idx.get_deps([package(self.info['baz-2.0.1-0.tar.bz2'])], 1),
            set([
                package(self.info['bar-1.1-0.tar.bz2'])
            ])
        )
        self.assertEqual(
            idx.get_deps([package(self.info['baz-2.0.1-0.tar.bz2'])], 2),
            set([
                package(self.info['bar-1.1-0.tar.bz2']),
                package(self.info['foo-1.0.0-0.tar.bz2'])
            ])
        )

    def test_get_reverse_deps(self):
        idx = package_index(self.info)
        self.assertEqual(
            idx.get_reverse_deps([package(self.info['foo-0.8.0-0.tar.bz2'])]),
            set([
                package(self.info['bar-0.9-0.tar.bz2']),
                package(self.info['baz-2.0-0.tar.bz2']),
            ])
        )
        self.assertEqual(
            idx.get_reverse_deps([package(self.info['foo-0.8.0-0.tar.bz2'])], 1),
            set([
                package(self.info['bar-0.9-0.tar.bz2']),
            ])
        )
        self.assertEqual(
            idx.get_reverse_deps([package(self.info['foo-0.8.0-0.tar.bz2'])], 2),
            set([
                package(self.info['bar-0.9-0.tar.bz2']),
                package(self.info['baz-2.0-0.tar.bz2']),
            ])
        )


if __name__ == '__main__':
    unittest.main()
