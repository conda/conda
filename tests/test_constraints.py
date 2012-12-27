# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import unittest

import conda.constraints as constraints
from conda.package import Package
from conda.package_spec import PackageSpec

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

class TestConstraints(unittest.TestCase):

    def test_named(self):
        p = Package(bitarray)
        c = constraints.Named("bitarray")
        self.assertEqual(
            True,
            c.match(p)
        )

        c = constraints.Named("foo")
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

        p = Package(bitarray)

        for spec_string, val in d.items():
            spec = PackageSpec(spec_string)
            c = constraints.Satisfies(spec)
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

        p = Package(bitarray)

        for spec_string, val in d.items():
            spec = PackageSpec(spec_string)
            c = constraints.StrictRequires(spec)
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

        p = Package(bitarray)

        for spec_string, val in d.items():
            spec = PackageSpec(spec_string)
            c = constraints.Requires(spec)
            self.assertEqual(
                val,
                c.match(p)
            )

    def test_wildcard(self):
        p = Package(bitarray)
        c = constraints.Wildcard()
        self.assertEqual(
            True,
            c.match(p)
        )

    def test_negate(self):
        p = Package(bitarray)
        c = constraints.Negate(constraints.Named("bitarray"))
        self.assertEqual(
            False,
            c.match(p)
        )

        c = constraints.Negate(constraints.Named("foo"))
        self.assertEqual(
            True,
            c.match(p)
        )

    def test_any_of(self):

        p = Package(bitarray)
        c = constraints.AnyOf(
                constraints.Named("bitarray"),
                constraints.Satisfies(PackageSpec("python=2.7"))
            )

        self.assertEqual(
            True,
            c.match(p)
        )

        c = constraints.AnyOf(
            constraints.Named("bitarray"),
            constraints.Negate(constraints.Named("bitarray"))
        )

        self.assertEqual(
            True,
            c.match(p)
        )

        c = constraints.AnyOf(
            constraints.Named("foo")
        )

        self.assertEqual(
            False,
            c.match(p)
        )

        c = constraints.AnyOf(
            constraints.Named("bitarray"),
            constraints.Negate(constraints.Named("bitarray")),
            constraints.Wildcard()
        )

        self.assertEqual(
            True,
            c.match(p)
        )

    def test_all_of(self):
        p = Package(bitarray)
        c = constraints.AllOf(
                constraints.Named("bitarray"),
                constraints.Satisfies(PackageSpec("python=2.7"))
            )

        self.assertEqual(
            False,
            c.match(p)
        )

        c = constraints.AllOf(
                constraints.Named("bitarray"),
                constraints.Satisfies(PackageSpec("python=2.7")),
                constraints.Negate(constraints.Named("bitarray"))
        )

        self.assertEqual(
            False,
            c.match(p)
        )

        c = constraints.AllOf(
                constraints.Named("bitarray"),
                constraints.Negate(constraints.Named("foo"))
        )

        self.assertEqual(
            True,
            c.match(p)
        )

if __name__ == '__main__':
    unittest.main()
