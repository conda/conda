# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import unittest

import conda.constraints as constraints
from conda.package import package
from conda.package_spec import package_spec

bitarray = {
    "arch": "x86_64",
    "build": "py26_0",
    "build_number": 0,
    "md5": "e64c350b3d9fa38d2aa326b3b905466a",
    "mtime": 1347411318.0,
    "name": "bitarray",
    "platform": "osx",
    "requires": [
      "python 2.6"
    ],
    "size": 54932,
    "version": "0.8.0"
}

class test_constraints(unittest.TestCase):

    def test_named(self):
        p = package(bitarray)
        c = constraints.named("bitarray")
        self.assertEqual(
            True,
            c.match(p)
        )

        c = constraints.named("foo")
        self.assertEqual(
            False,
            c.match(p)
        )

    def test_satisfies(self):

        d = {
            "bitarray=0.8.0"   :   True,
            "foo=0.8.0"        :   False,
            "bitarray=0.8"     :   True,
            "bitarray=0.9"     :   False

        }

        p = package(bitarray)

        for spec_string, val in d.items():
            spec = package_spec(spec_string)
            c = constraints.satisfies(spec)
            self.assertEqual(
                val,
                c.match(p)
            )

    def test_strict_requires(self):

        d = {
            "python=2.6"   :   True,
            "foo=2.6"      :   False,
            "python=2.7"   :   False,
            "python=3.1"   :   False,
            "python=2"     :   False

        }

        p = package(bitarray)

        for spec_string, val in d.items():
            spec = package_spec(spec_string)
            c = constraints.strict_requires(spec)
            self.assertEqual(
                val,
                c.match(p)
            )

    def test_requires(self):

        d = {
            "python=2.6"   :   True,
            "foo=2.6"      :   True,
            "python=2.7"   :   False,
            "python=3.1"   :   False,
            "python=2"     :   True

        }

        p = package(bitarray)

        for spec_string, val in d.items():
            spec = package_spec(spec_string)
            c = constraints.requires(spec)
            self.assertEqual(
                val,
                c.match(p)
            )

    def test_wildcard(self):
        p = package(bitarray)
        c = constraints.wildcard()
        self.assertEqual(
            True,
            c.match(p)
        )

    def test_negate(self):
        p = package(bitarray)
        c = constraints.negate(constraints.named("bitarray"))
        self.assertEqual(
            False,
            c.match(p)
        )

        c = constraints.negate(constraints.named("foo"))
        self.assertEqual(
            True,
            c.match(p)
        )

    def test_any_of(self):

        p = package(bitarray)
        c = constraints.any_of(
                constraints.named("bitarray"),
                constraints.satisfies(package_spec("python=2.7"))
            )

        self.assertEqual(
            True,
            c.match(p)
        )

        c = constraints.any_of(
            constraints.named("bitarray"),
            constraints.negate(constraints.named("bitarray"))
        )

        self.assertEqual(
            True,
            c.match(p)
        )

        c = constraints.any_of(
            constraints.named("foo")
        )

        self.assertEqual(
            False,
            c.match(p)
        )

        c = constraints.any_of(
            constraints.named("bitarray"),
            constraints.negate(constraints.named("bitarray")),
            constraints.wildcard()
        )

        self.assertEqual(
            True,
            c.match(p)
        )

    def test_all_of(self):
        p = package(bitarray)
        c = constraints.all_of(
                constraints.named("bitarray"),
                constraints.satisfies(package_spec("python=2.7"))
            )

        self.assertEqual(
            False,
            c.match(p)
        )

        c = constraints.all_of(
                constraints.named("bitarray"),
                constraints.satisfies(package_spec("python=2.7")),
                constraints.negate(constraints.named("bitarray"))
        )

        self.assertEqual(
            False,
            c.match(p)
        )

        c = constraints.all_of(
                constraints.named("bitarray"),
                constraints.negate(constraints.named("foo"))
        )

        self.assertEqual(
            True,
            c.match(p)
        )

if __name__ == '__main__':
    unittest.main()
