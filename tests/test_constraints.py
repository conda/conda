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
        p = package(bitarray)
        r = requirement("bitarray=0.8.0")
        c = constraints.satisfies(r)
        self.assertEqual(
            True,
            c.match(p)
        )

        r = requirement("foo=0.8.0")
        c = constraints.satisfies(r)
        self.assertEqual(
            False,
            c.match(p)
        )

        r = requirement("bitarray=0.8")
        c = constraints.satisfies(r)
        self.assertEqual(
            True,
            c.match(p)
        )

        r = requirement("bitarray=0.9")
        c = constraints.satisfies(r)
        self.assertEqual(
            False,
            c.match(p)
        )

    def test_strict_requires(self):
        p = package(bitarray)
        r = requirement("python=2.6")
        c = constraints.strict_requires(r)
        self.assertEqual(
            True,
            c.match(p)
        )

        r = requirement("foo=2.6")
        c = constraints.strict_requires(r)
        self.assertEqual(
            False,
            c.match(p)
        )

        r = requirement("python=2.7")
        c = constraints.strict_requires(r)
        self.assertEqual(
            False,
            c.match(p)
        )

        r = requirement("python=3.1")
        c = constraints.strict_requires(r)
        self.assertEqual(
            False,
            c.match(p)
        )

        # This may change
        r = requirement("python=2")
        c = constraints.strict_requires(r)
        self.assertEqual(
            False,
            c.match(p)
        )

    def test_requires(self):
        p = package(bitarray)
        r = requirement("python=2.6")
        c = constraints.requires(r)
        self.assertEqual(
            True,
            c.match(p)
        )

        r = requirement("foo=2.6")
        c = constraints.requires(r)
        self.assertEqual(
            True,
            c.match(p)
        )

        r = requirement("python=2.7")
        c = constraints.requires(r)
        self.assertEqual(
            False,
            c.match(p)
        )

        r = requirement("python=3.1")
        c = constraints.requires(r)
        self.assertEqual(
            False,
            c.match(p)
        )

        r = requirement("python=2")
        c = constraints.requires(r)
        self.assertEqual(
            False,
            c.match(p)
        )


if __name__ == '__main__':
    unittest.main()