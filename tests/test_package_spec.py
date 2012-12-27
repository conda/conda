# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from distutils.version import LooseVersion
import unittest

from conda.package_spec import (
    find_inconsistent_specs, group_package_specs_by_name, PackageSpec, sort_package_specs_by_name
)

class TestPackageSpec(unittest.TestCase):

    def test_init_name(self):
        spec = PackageSpec("foo-bar")
        self.assertEqual(
            spec.name,
            "foo-bar"
        )
        self.assertEqual(
            spec.version,
            None
        )
        self.assertEqual(
            spec.build,
            None
        )

    def test_init_name_version(self):
        spec_strings = ["foo-bar 2.7.1.abc", "foo-bar=2.7.1.abc"]
        for spec_string in spec_strings:
            spec = PackageSpec(spec_string)
            self.assertEqual(
                spec.name,
                "foo-bar"
            )
            self.assertEqual(
                spec.version,
                LooseVersion('2.7.1.abc')
            )
            self.assertEqual(
                spec.build,
                None
            )

    def test_init_name_version_build(self):
        spec_strings = ["foo-bar 2.7.1.abc bld", "foo-bar=2.7.1.abc=bld"]
        for spec_string in spec_strings:
            spec = PackageSpec(spec_string)
            self.assertEqual(
                spec.name,
                "foo-bar"
            )
            self.assertEqual(
                spec.version,
                LooseVersion('2.7.1.abc')
            )
            self.assertEqual(
                spec.build,
                "bld"
            )

class TestFindInconsistentSpecs(unittest.TestCase):

    def test_simple(self):
        a, b, c = PackageSpec('python 2.7'), PackageSpec('python 3.1'), PackageSpec('python 2.7.1')
        specs = [a, b, c]
        self.assertEqual(
            find_inconsistent_specs(specs),
            {
                'python' :  set([
                                PackageSpec('python 2.7.1'),
                                PackageSpec('python 3.1'),
                                PackageSpec('python 2.7'),
                            ])
            }
        )


class TestSortPackageSpecsByName(unittest.TestCase):

    def test_simple(self):
        a, b, c = (
            PackageSpec('numpy 1.7'),
            PackageSpec('python'),
            PackageSpec('scipy 0.11 bld'),
        )
        specs = [c, a, b]
        self.assertEqual(
            sort_package_specs_by_name(specs),
            [a, b, c]
        )
    def test_reverse(self):
        a, b, c = (
            PackageSpec('numpy 1.7'),
            PackageSpec('python'),
            PackageSpec('scipy 0.11 bld'),
        )
        specs = [c, a, b]
        self.assertEqual(
            sort_package_specs_by_name(specs, reverse=True),
            [c, b, a]
        )


class TestGroupPackageSpecsByName(unittest.TestCase):

    def test_simple(self):
        specs = [
            PackageSpec('scipy 0.11 bld'),
            PackageSpec('python 2.7'),
            PackageSpec('numpy 1.7'),
            PackageSpec('scipy'),
            PackageSpec('numpy 1.6'),
        ]
        self.assertEqual(
            group_package_specs_by_name(specs),
            {
                'scipy' : set([PackageSpec('scipy'), PackageSpec('scipy 0.11 bld')]),
                'numpy' : set([PackageSpec('numpy 1.6'), PackageSpec('numpy 1.7')]),
                'python' : set([PackageSpec('python 2.7')]),
            }
        )


if __name__ == '__main__':
    unittest.main()
