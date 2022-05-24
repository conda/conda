# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, print_function

from copy import copy
from random import shuffle
import unittest

from conda.exceptions import InvalidVersionSpec
from conda.models.version import VersionOrder, VersionSpec, normalized_version, ver_eval, treeify
import pytest


class TestVersionSpec(unittest.TestCase):

    def test_version_order(self):
        versions = [
           ("0.4",         [[0], [0], [4]]),
           ("0.4.0",      [[0], [0], [4], [0]]),
           ("0.4.1a.vc11",[[0], [0], [4], [1, 'a'],[0, 'vc', 11]]),
           ("0.4.1.rc",   [[0], [0], [4], [1], [0, 'rc']]),
           ("0.4.1.vc11", [[0], [0], [4], [1],[0, 'vc', 11]]),
           ("0.4.1",      [[0], [0], [4], [1]]),
           ("0.5*",       [[0], [0], [5, '*']]),
           ("0.5a1",      [[0], [0], [5, 'a', 1]]),
           ("0.5b3",      [[0], [0], [5, 'b', 3]]),
           ("0.5C1",      [[0], [0], [5, 'c', 1]]),
           ("0.5z",       [[0], [0], [5, 'z']]),
           ("0.5za",      [[0], [0], [5, 'za']]),
           ("0.5",        [[0], [0], [5]]),
           ("0.5_5",      [[0], [0], [5], [5]]),
           ("0.5-5",      [[0], [0], [5], [5]]),
           ("0.9.6",      [[0], [0], [9], [6]]),
           ("0.960923",   [[0], [0], [960923]]),
           ("1.0",        [[0], [1], [0]]),
           ("1.0.4a3",    [[0], [1], [0], [4, 'a', 3]]),
           ("1.0.4b1",    [[0], [1], [0], [4, 'b', 1]]),
           ("1.0.4",      [[0], [1], [0], [4]]),
           ("1.1dev1",    [[0], [1], [1, 'DEV', 1]]),
           ("1.1_",       [[0], [1], [1, '_']]),
           ("1.1a1",      [[0], [1], [1, 'a', 1]]),
           ("1.1.dev1",   [[0], [1], [1], [0, 'DEV', 1]]),
           ("1.1.a1",     [[0], [1], [1], [0, 'a', 1]]),
           ("1.1",        [[0], [1], [1]]),
           ("1.1.post1",  [[0], [1], [1], [0, float('inf'), 1]]),
           ("1.1.1dev1",  [[0], [1], [1], [1, 'DEV', 1]]),
           ("1.1.1rc1",   [[0], [1], [1], [1, 'rc', 1]]),
           ("1.1.1",      [[0], [1], [1], [1]]),
           ("1.1.1post1", [[0], [1], [1], [1, float('inf'), 1]]),
           ("1.1post1",   [[0], [1], [1, float('inf'), 1]]),
           ("2g6",        [[0], [2, 'g', 6]]),
           ("2.0b1pr0",   [[0], [2], [0, 'b', 1, 'pr', 0]]),
           ("2.2be.ta29", [[0], [2], [2, 'be'], [0, 'ta', 29]]),
           ("2.2be5ta29", [[0], [2], [2, 'be', 5, 'ta', 29]]),
           ("2.2beta29",  [[0], [2], [2, 'beta', 29]]),
           ("2.2.0.1",    [[0], [2], [2],[0],[1]]),
           ("3.1.1.6",    [[0], [3], [1], [1], [6]]),
           ("3.2.p.r0",   [[0], [3], [2], [0, 'p'], [0, 'r', 0]]),
           ("3.2.pr0",    [[0], [3], [2], [0, 'pr', 0]]),
           ("3.2.pr.1",   [[0], [3], [2], [0, 'pr'], [1]]),
           ("5.5.kw",     [[0], [5], [5], [0, 'kw']]),
           ("11g",        [[0], [11, 'g']]),
           ("14.3.1",     [[0], [14], [3], [1]]),
           ("14.3.1.post26.g9d75ca2",
                                        [[0],[14],[3],[1],[0,float('inf'),26],[0,'g',9,'d',75,'ca',2]]),
           ("1996.07.12", [[0], [1996], [7], [12]]),
           ("1!0.4.1",    [[1], [0], [4], [1]]),
           ("1!3.1.1.6",  [[1], [3], [1], [1], [6]]),
           ("2!0.4.1",    [[2], [0], [4], [1]]),
        ]

        # check parser
        versions = [(v, VersionOrder(v), l) for v, l in versions]
        for s, v, l in versions:
            assert VersionOrder(v) is v
            assert str(v) == s.lower().replace('-', '_')
            self.assertEqual(v.version, l)
        self.assertEqual(VersionOrder("0.4.1.rc"), VersionOrder("  0.4.1.RC  "))
        self.assertEqual(normalized_version("  0.4.1.RC  "), VersionOrder("0.4.1.rc"))
        for ver in ("", "", "  ", "3.5&1", "5.5++", "5.5..mw", "!", "a!1.0", "a!b!1.0"):
            self.assertRaises(ValueError, VersionOrder, ver)

        # check __eq__
        self.assertEqual(VersionOrder("  0.4.rc  "), VersionOrder("0.4.RC"))
        self.assertEqual(VersionOrder("0.4"), VersionOrder("0.4.0"))
        self.assertNotEqual(VersionOrder("0.4"), VersionOrder("0.4.1"))
        self.assertEqual(VersionOrder("0.4.a1"), VersionOrder("0.4.0a1"))
        self.assertNotEqual(VersionOrder("0.4.a1"), VersionOrder("0.4.1a1"))

        # check __lt__
        self.assertEqual(sorted(versions, key=lambda x: x[1]), versions)

        # check startswith
        self.assertTrue(VersionOrder("0.4.1").startswith(VersionOrder("0")))
        self.assertTrue(VersionOrder("0.4.1").startswith(VersionOrder("0.4")))
        self.assertTrue(VersionOrder("0.4.1p1").startswith(VersionOrder("0.4")))
        self.assertTrue(VersionOrder("0.4.1p1").startswith(VersionOrder("0.4.1p")))
        self.assertFalse(VersionOrder("0.4.1p1").startswith(VersionOrder("0.4.1q1")))
        self.assertFalse(VersionOrder("0.4").startswith(VersionOrder("0.4.1")))
        self.assertTrue(VersionOrder("0.4.1+1.3").startswith(VersionOrder("0.4.1")))
        self.assertTrue(VersionOrder("0.4.1+1.3").startswith(VersionOrder("0.4.1+1")))
        self.assertFalse(VersionOrder("0.4.1").startswith(VersionOrder("0.4.1+1.3")))
        self.assertFalse(VersionOrder("0.4.1+1").startswith(VersionOrder("0.4.1+1.3")))

    def test_openssl_convention(self):
        openssl = [VersionOrder(k) for k in (
            '1.0.1dev',
            '1.0.1_',  # <- this
            '1.0.1a',
            '1.0.1b',
            '1.0.1c',
            '1.0.1d',
            '1.0.1r',
            '1.0.1rc',
            '1.0.1rc1',
            '1.0.1rc2',
            '1.0.1s',
            '1.0.1',  # <- compared to this
            '1.0.1post.a',
            '1.0.1post.b',
            '1.0.1post.z',
            '1.0.1post.za',
            '1.0.2',
        )]
        shuffled = copy(openssl)
        shuffle(shuffled)
        assert sorted(shuffled) == openssl

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
        self.assertRaises(InvalidVersionSpec, ver_eval, '3.0.0', '><2.4.5')
        self.assertRaises(InvalidVersionSpec, ver_eval, '3.0.0', '!!2.4.5')
        self.assertRaises(InvalidVersionSpec, ver_eval, '3.0.0', '!')

    def test_version_spec_1(self):
        v1 = VersionSpec('1.7.1')
        v2 = VersionSpec('1.7.1*')
        v3 = VersionSpec('1.7.1')
        self.assertTrue(v1.is_exact())
        self.assertFalse(v2.is_exact())
        self.assertTrue(v1 == v3)
        self.assertFalse(v1 != v3)
        self.assertTrue(v1 != v2)
        self.assertFalse(v1 == v2)
        self.assertTrue(v1 != 1.0)
        self.assertFalse(v1 == 1.0)
        self.assertEqual(hash(v1), hash(v3))
        self.assertNotEqual(hash(v1), hash(v2))

    def test_version_spec_2(self):
        v1 = VersionSpec('( (1.5|((1.6|1.7), 1.8), 1.9 |2.0))|2.1')
        self.assertEqual(v1.spec, '1.5|1.6|1.7,1.8,1.9|2.0|2.1')
        self.assertRaises(InvalidVersionSpec, VersionSpec, '(1.5')
        self.assertRaises(InvalidVersionSpec, VersionSpec, '1.5)')
        self.assertRaises(InvalidVersionSpec, VersionSpec, '1.5||1.6')
        self.assertRaises(InvalidVersionSpec, VersionSpec, '^1.5')

    def test_version_spec_3(self):
        v1 = VersionSpec('1.7.1*')
        v2 = VersionSpec('1.7.1.*')
        self.assertFalse(v1.is_exact())
        self.assertFalse(v2.is_exact())
        self.assertTrue(v1 == v2)
        self.assertFalse(v1 != v2)
        self.assertEqual(hash(v1), hash(v2))

    def test_version_spec_4(self):
        v1 = VersionSpec('1.7.1*,1.8.1*')
        v2 = VersionSpec('1.7.1.*,1.8.1.*')
        v3 = VersionSpec('1.7.1*,1.8.1.*')
        assert v1.is_exact() is False
        assert v2.is_exact() is False
        assert v1 == v2 == v3
        assert not v1 != v2
        assert hash(v1) == hash(v2) == hash(v3)

    def test_match(self):
        for vspec, res in [
            ('1.7.*', True),   ('1.7.1', True),    ('1.7.0', False),
            ('1.7', False),   ('1.5.*', False),    ('>=1.5', True),
            ('!=1.5', True),  ('!=1.7.1', False), ('==1.7.1', True),
            ('==1.7', False), ('==1.7.2', False), ('==1.7.1.0', True),
            ('1.7.*|1.8.*', True),
            # ('1.8/*|1.9.*', False),  what was this supposed to be?
            ('>1.7,<1.8', True), ('>1.7.1,<1.8', False),
            ('^1.7.1$', True), (r'^1\.7\.1$', True), (r'^1\.7\.[0-9]+$', True),
            (r'^1\.8.*$', False), (r'^1\.[5-8]\.1$', True), (r'^[^1].*$', False),
            (r'^[0-9+]+\.[0-9+]+\.[0-9]+$', True), ('^$', False),
            ('^.*$', True), ('1.7.*|^0.*$', True), ('1.6.*|^0.*$', False),
            ('1.6.*|^0.*$|1.7.1', True), ('^0.*$|1.7.1', True),
            (r'1.6.*|^.*\.7\.1$|0.7.1', True), ('*', True), ('1.*.1', True),
            ('1.5.*|>1.7,<1.8', True), ('1.5.*|>1.7,<1.7.1', False),
        ]:
            m = VersionSpec(vspec)
            assert VersionSpec(m) is m
            assert str(m) == vspec
            assert repr(m) == "VersionSpec('%s')" % vspec
            assert m.match('1.7.1') == res, vspec

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

    def test_not_eq_star(self):
        assert VersionSpec("=3.3").match("3.3.1")
        assert VersionSpec("=3.3").match("3.3")
        assert not VersionSpec("=3.3").match("3.4")

        assert VersionSpec("3.3.*").match("3.3.1")
        assert VersionSpec("3.3.*").match("3.3")
        assert not VersionSpec("3.3.*").match("3.4")

        assert VersionSpec("=3.3.*").match("3.3.1")
        assert VersionSpec("=3.3.*").match("3.3")
        assert not VersionSpec("=3.3.*").match("3.4")

        assert not VersionSpec("!=3.3.*").match("3.3.1")
        assert VersionSpec("!=3.3.*").match("3.4")
        assert VersionSpec("!=3.3.*").match("3.4.1")

        assert VersionSpec("!=3.3").match("3.3.1")
        assert not VersionSpec("!=3.3").match("3.3.0.0")
        assert not VersionSpec("!=3.3.*").match("3.3.0.0")

    def test_compound_versions(self):
        vs = VersionSpec('>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*')
        assert not vs.match('2.6.8')
        assert vs.match('2.7.2')
        assert not vs.match('3.3')
        assert not vs.match('3.3.4')
        assert vs.match('3.4')
        assert vs.match('3.4a')

    def test_invalid_version_specs(self):
        with pytest.raises(InvalidVersionSpec):
            VersionSpec("~")
        with pytest.raises(InvalidVersionSpec):
            VersionSpec("^")

    def test_compatible_release_versions(self):
        assert VersionSpec("~=1.10").match("1.11.0")
        assert not VersionSpec("~=1.10.0").match("1.11.0")

        assert not VersionSpec("~=3.3.2").match("3.4.0")
        assert not VersionSpec("~=3.3.2").match("3.3.1")
        assert VersionSpec("~=3.3.2").match("3.3.2.0")
        assert VersionSpec("~=3.3.2").match("3.3.3")

        assert VersionSpec("~=3.3.2|==2.2").match("2.2.0")
        assert VersionSpec("~=3.3.2|==2.2").match("3.3.3")
        assert not VersionSpec("~=3.3.2|==2.2").match("2.2.1")

        with pytest.raises(InvalidVersionSpec):
            VersionSpec("~=3.3.2.*")

    def test_pep_440_arbitrary_equality_operator(self):
        # We're going to leave the not implemented for now.
        with pytest.raises(InvalidVersionSpec):
            VersionSpec("===3.3.2")
