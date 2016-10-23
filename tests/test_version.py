from __future__ import print_function, absolute_import
import unittest

from conda.version import ver_eval, VersionSpec, VersionOrder, normalized_version

class TestVersionSpec(unittest.TestCase):

    def test_version_order(self):
        versions = [
           (VersionOrder("0.4"),        [[0], [0], [4]]),
           (VersionOrder("0.4.0"),      [[0], [0], [4], [0]]),
           (VersionOrder("0.4.1a.vc11"),[[0], [0], [4], [1, 'a'],[0, 'vc', 11]]),
           (VersionOrder("0.4.1.rc"),   [[0], [0], [4], [1], [0, 'rc']]),
           (VersionOrder("0.4.1.vc11"), [[0], [0], [4], [1],[0, 'vc', 11]]),
           (VersionOrder("0.4.1"),      [[0], [0], [4], [1]]),
           (VersionOrder("0.5*"),       [[0], [0], [5, '*']]),
           (VersionOrder("0.5a1"),      [[0], [0], [5, 'a', 1]]),
           (VersionOrder("0.5b3"),      [[0], [0], [5, 'b', 3]]),
           (VersionOrder("0.5C1"),      [[0], [0], [5, 'c', 1]]),
           (VersionOrder("0.5z"),       [[0], [0], [5, 'z']]),
           (VersionOrder("0.5za"),      [[0], [0], [5, 'za']]),
           (VersionOrder("0.5"),        [[0], [0], [5]]),
           (VersionOrder("0.5_5"),      [[0], [0], [5], [5]]),
           (VersionOrder("0.5-5"),      [[0], [0], [5], [5]]),
           (VersionOrder("0.9.6"),      [[0], [0], [9], [6]]),
           (VersionOrder("0.960923"),   [[0], [0], [960923]]),
           (VersionOrder("1.0"),        [[0], [1], [0]]),
           (VersionOrder("1.0.4a3"),    [[0], [1], [0], [4, 'a', 3]]),
           (VersionOrder("1.0.4b1"),    [[0], [1], [0], [4, 'b', 1]]),
           (VersionOrder("1.0.4"),      [[0], [1], [0], [4]]),
           (VersionOrder("1.1dev1"),    [[0], [1], [1, 'DEV', 1]]),
           (VersionOrder("1.1a1"),      [[0], [1], [1, 'a', 1]]),
           (VersionOrder("1.1.dev1"),   [[0], [1], [1], [0, 'DEV', 1]]),
           (VersionOrder("1.1.a1"),     [[0], [1], [1], [0, 'a', 1]]),
           (VersionOrder("1.1"),        [[0], [1], [1]]),
           (VersionOrder("1.1.post1"),  [[0], [1], [1], [0, float('inf'), 1]]),
           (VersionOrder("1.1.1dev1"),  [[0], [1], [1], [1, 'DEV', 1]]),
           (VersionOrder("1.1.1rc1"),   [[0], [1], [1], [1, 'rc', 1]]),
           (VersionOrder("1.1.1"),      [[0], [1], [1], [1]]),
           (VersionOrder("1.1.1post1"), [[0], [1], [1], [1, float('inf'), 1]]),
           (VersionOrder("1.1post1"),   [[0], [1], [1, float('inf'), 1]]),
           (VersionOrder("2g6"),        [[0], [2, 'g', 6]]),
           (VersionOrder("2.0b1pr0"),   [[0], [2], [0, 'b', 1, 'pr', 0]]),
           (VersionOrder("2.2be.ta29"), [[0], [2], [2, 'be'], [0, 'ta', 29]]),
           (VersionOrder("2.2be5ta29"), [[0], [2], [2, 'be', 5, 'ta', 29]]),
           (VersionOrder("2.2beta29"),  [[0], [2], [2, 'beta', 29]]),
           (VersionOrder("2.2.0.1"),    [[0], [2], [2],[0],[1]]),
           (VersionOrder("3.1.1.6"),    [[0], [3], [1], [1], [6]]),
           (VersionOrder("3.2.p.r0"),   [[0], [3], [2], [0, 'p'], [0, 'r', 0]]),
           (VersionOrder("3.2.pr0"),    [[0], [3], [2], [0, 'pr', 0]]),
           (VersionOrder("3.2.pr.1"),   [[0], [3], [2], [0, 'pr'], [1]]),
           (VersionOrder("5.5.kw"),     [[0], [5], [5], [0, 'kw']]),
           (VersionOrder("11g"),        [[0], [11, 'g']]),
           (VersionOrder("14.3.1"),     [[0], [14], [3], [1]]),
           (VersionOrder("14.3.1.post26.g9d75ca2"),
                                        [[0],[14],[3],[1],[0,float('inf'),26],[0,'g',9,'d',75,'ca',2]]),
           (VersionOrder("1996.07.12"), [[0], [1996], [7], [12]]),
           (VersionOrder("1!0.4.1"),    [[1], [0], [4], [1]]),
           (VersionOrder("1!3.1.1.6"),  [[1], [3], [1], [1], [6]]),
           (VersionOrder("2!0.4.1"),    [[2], [0], [4], [1]]),
        ]

        # check parser
        for v, l in versions:
            self.assertEqual(v.version, l)
        self.assertEqual(VersionOrder("0.4.1.rc"), VersionOrder("  0.4.1.RC  "))
        self.assertEqual(normalized_version("  0.4.1.RC  "), VersionOrder("0.4.1.rc"))
        with self.assertRaises(ValueError):
            VersionOrder("")
        with self.assertRaises(ValueError):
            VersionOrder("  ")
        with self.assertRaises(ValueError):
            VersionOrder("3.5&1")
        with self.assertRaises(ValueError):
            VersionOrder("5.5++")
        with self.assertRaises(ValueError):
            VersionOrder("5.5..mw")
        with self.assertRaises(ValueError):
            VersionOrder("5.5.mw.")
        with self.assertRaises(ValueError):
            VersionOrder("!")
        with self.assertRaises(ValueError):
            VersionOrder("a!1.0")
        with self.assertRaises(ValueError):
            VersionOrder("a!b!1.0")

        # check __eq__
        self.assertEqual(VersionOrder("  0.4.rc  "), VersionOrder("0.4.RC"))
        self.assertEqual(VersionOrder("0.4"), VersionOrder("0.4.0"))
        self.assertNotEqual(VersionOrder("0.4"), VersionOrder("0.4.1"))
        self.assertEqual(VersionOrder("0.4.a1"), VersionOrder("0.4.0a1"))
        self.assertNotEqual(VersionOrder("0.4.a1"), VersionOrder("0.4.1a1"))

        # check __lt__
        self.assertEqual(sorted(versions, key=lambda x: x[0]), versions)

        # test openssl convention
        openssl = [VersionOrder(k) for k in ['1.0.1', '1.0.1post.a', '1.0.1post.b',
                                             '1.0.1post.z', '1.0.1post.za', '1.0.2']]
        self.assertEqual(sorted(openssl), openssl)

    def test_pep440(self):
        # this list must be in sorted order (slightly modified from the PEP 440 test suite
        # https://github.com/pypa/packaging/blob/master/tests/test_version.py)
        VERSIONS = [
            # Implicit epoch of 0
            "1.0a1", "1.0a2.dev456", "1.0a12.dev456", "1.0a12",
            "1.0b1.dev456", "1.0b2", "1.0b2.post345.dev456", "1.0b2.post345",
            "1.0c1.dev456", "1.0c1", "1.0c3", "1.0rc2", "1.0.dev456", "1.0",
            "1.0.post456.dev34", "1.0.post456", "1.1.dev1",
            "1.2.r32+123456", "1.2.rev33+123456",
            "1.2+abc", "1.2+abc123def", "1.2+abc123",
            "1.2+123abc", "1.2+123abc456", "1.2+1234.abc", "1.2+123456",

            # Explicit epoch of 1
            "1!1.0a1", "1!1.0a2.dev456", "1!1.0a12.dev456", "1!1.0a12",
            "1!1.0b1.dev456", "1!1.0b2", "1!1.0b2.post345.dev456", "1!1.0b2.post345",
            "1!1.0c1.dev456", "1!1.0c1", "1!1.0c3", "1!1.0rc2", "1!1.0.dev456", "1!1.0",
            "1!1.0.post456.dev34", "1!1.0.post456", "1!1.1.dev1",
            "1!1.2.r32+123456", "1!1.2.rev33+123456",
            "1!1.2+abc", "1!1.2+abc123def", "1!1.2+abc123",
            "1!1.2+123abc", "1!1.2+123abc456", "1!1.2+1234.abc", "1!1.2+123456",
        ]

        version = [VersionOrder(v) for v in VERSIONS]

        self.assertEqual(version, sorted(version))

    def test_hexrd(self):
        VERSIONS = ['0.3.0.dev', '0.3.3']
        vos = [VersionOrder(v) for v in VERSIONS]
        self.assertEqual(sorted(vos), vos)

    def test_ver_eval(self):
        self.assertEqual(ver_eval('1.7.0', '==1.7'), True)
        self.assertEqual(ver_eval('1.7.0', '<=1.7'), True)
        self.assertEqual(ver_eval('1.7.0', '<1.7'), False)
        self.assertEqual(ver_eval('1.7.0', '>=1.7'), True)
        self.assertEqual(ver_eval('1.7.0', '>1.7'), False)
        self.assertEqual(ver_eval('1.6.7', '>=1.7'), False)
        self.assertEqual(ver_eval('2013a', '>2013b'), False)
        self.assertEqual(ver_eval('2013k', '>2013b'), True)
        self.assertEqual(ver_eval('3.0.0', '>2013b'), False)
        self.assertEqual(ver_eval('1.0.0', '>1.0.0a'), True)
        self.assertEqual(ver_eval('1.0.0', '>1.0.0*'), True)
        self.assertEqual(ver_eval('1.0', '1.0*'), True)
        self.assertEqual(ver_eval('1.0.0', '1.0*'), True)
        self.assertEqual(ver_eval('1.0', '1.0.0*'), True)
        self.assertEqual(ver_eval('1.0.1', '1.0.0*'), False)
        self.assertEqual(ver_eval('2013a', '2013a*'), True)
        self.assertEqual(ver_eval('2013a', '2013b*'), False)
        self.assertEqual(ver_eval('2013ab', '2013a*'), True)
        self.assertEqual(ver_eval('1.3.4', '1.2.4*'), False)
        self.assertEqual(ver_eval('1.2.3+4.5.6', '1.2.3*'), True)
        self.assertEqual(ver_eval('1.2.3+4.5.6', '1.2.3+4*'), True)
        self.assertEqual(ver_eval('1.2.3+4.5.6', '1.2.3+5*'), False)
        self.assertEqual(ver_eval('1.2.3+4.5.6', '1.2.4+5*'), False)

    def test_ver_eval_errors(self):
        self.assertRaises(RuntimeError, ver_eval, '3.0.0', '><2.4.5')
        self.assertRaises(RuntimeError, ver_eval, '3.0.0', '!!2.4.5')
        self.assertRaises(RuntimeError, ver_eval, '3.0.0', '!')

    def test_match(self):
        for vspec, res in [
            ('1.7*', True),   ('1.7.1', True),    ('1.7.0', False),
            ('1.7', False),   ('1.5*', False),    ('>=1.5', True),
            ('!=1.5', True),  ('!=1.7.1', False), ('==1.7.1', True),
            ('==1.7', False), ('==1.7.2', False), ('==1.7.1.0', True),
            ('1.7*|1.8*', True), ('1.8*|1.9*', False),
            ('>1.7,<1.8', True), ('>1.7.1,<1.8', False),
            ('^1.7.1$', True), ('^1\.7\.1$', True), ('^1\.7\.[0-9]+$', True),
            ('^1\.8.*$', False), ('^1\.[5-8]\.1$', True), ('^[^1].*$', False),
            ('^[0-9+]+\.[0-9+]+\.[0-9]+$', True), ('^$', False),
            ('^.*$', True), ('1.7.*|^0.*$', True), ('1.6.*|^0.*$', False),
            ('1.6.*|^0.*$|1.7.1', True), ('^0.*$|1.7.1', True),
            ('1.6.*|^.*\.7\.1$|0.7.1', True),
            ]:
            m = VersionSpec(vspec)
            assert VersionSpec(m) is m
            assert str(m) == vspec
            assert repr(m) == "VersionSpec('%s')"%vspec
            self.assertEqual(m.match('1.7.1'), res)

    def test_local_identifier(self):
        """The separator for the local identifier should be either `.` or `+`"""
        # a valid versionstr should match itself
        versions = (
            '1.7.0'
            '1.7.0.post123'
            '1.7.0.post123.gabcdef9',
            '1.7.0.post123+gabcdef9',
        )
        for version in versions:
            m = VersionSpec(version)
            self.assertTrue(m.match(version))

