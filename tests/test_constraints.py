import unittest
from conda.package import package
from conda.requirement import requirement
import conda.constraints as constraints

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

        for req, val in d.items():
            r = requirement(req)
            c = constraints.satisfies(r)
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

        for req, val in d.items():
            r = requirement(req)
            c = constraints.strict_requires(r)
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
            "python=2"     :   False

        }

        p = package(bitarray)

        for req, val in d.items():
            r = requirement(req)
            c = constraints.requires(r)
            self.assertEqual(
                val,
                c.match(p)
            )

if __name__ == '__main__':
    unittest.main()