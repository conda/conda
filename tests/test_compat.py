import random
import sys
import unittest

from conda import compat

PY3 = sys.version_info[0] == 3


class TestOf_b(unittest.TestCase):
    @unittest.skipIf(PY3, "python 2 test")
    def test_returns_str_in_python2(self):
        some_str = "some random string %d" % random.randint(100, 200)
        self.assertIsInstance(compat.b(some_str, encoding="utf-8"), str)

    @unittest.skipIf(not PY3, "python 3 test")
    def test_returns_bytes_in_python3(self):
        some_str = "some random string %d" % random.randint(100, 200)
        self.assertIsInstance(compat.b(some_str, encoding="utf-8"), bytes)


class TestOf_u(unittest.TestCase):
    @unittest.skipIf(PY3, "python 2 test")
    def test_returns_unicode_in_python2(self):
        some_str = "some random string %d" % random.randint(100, 200)
        self.assertIsInstance(compat.u(some_str), unicode)

    @unittest.skipIf(not PY3, "python 3 test")
    def test_returns_str_in_python3(self):
        some_str = "some random string %d" % random.randint(100, 200)
        self.assertIsInstance(compat.u(some_str), str)
