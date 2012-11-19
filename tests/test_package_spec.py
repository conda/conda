
from distutils.version import LooseVersion
import unittest

from conda.package_spec import (
    apply_default_spec, find_inconsistent_specs, group_package_specs_by_name, package_spec, sort_package_specs_by_name
)

class test_package_spec(unittest.TestCase):

    def test_init_name(self):
        spec = package_spec("foo-bar")
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
            spec = package_spec(spec_string)
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
            spec = package_spec(spec_string)
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

class test_find_inconsistent_specs(unittest.TestCase):

    def test_simple(self):
        a, b, c = package_spec('python 2.7'), package_spec('python 3.1'), package_spec('python 2.7.1')
        specs = [a, b, c]
        self.assertEqual(
            find_inconsistent_specs(specs),
            {
                'python' :  set([
                                package_spec('python 2.7.1'),
                                package_spec('python 3.1'),
                                package_spec('python 2.7'),
                            ])
            }
        )


class test_apply_default_spec(unittest.TestCase):

    def test_present(self):
        a, b, c = package_spec('python'), package_spec('numpy 1.7'), package_spec('scipy 0.11 bld')
        specs = [a, b, c]
        self.assertEqual(
            apply_default_spec(specs, package_spec('python')),
            set([package_spec('python'),
                 package_spec('numpy 1.7'),
                 package_spec('scipy 0.11 bld')])
        )
        self.assertEqual(
            apply_default_spec(specs, package_spec('python 2.7')),
            set([package_spec('python'),
                 package_spec('numpy 1.7'),
                 package_spec('scipy 0.11 bld')])
        )
        self.assertEqual(
            apply_default_spec(specs, package_spec('python 2.7 bld')),
            set([package_spec('python'),
                 package_spec('numpy 1.7'),
                 package_spec('scipy 0.11 bld')])
        )
        self.assertEqual(
            apply_default_spec(specs, package_spec('numpy')),
            set([package_spec('python'),
                 package_spec('numpy 1.7'),
                 package_spec('scipy 0.11 bld')])
        )
        self.assertEqual(
            apply_default_spec(specs, package_spec('numpy 1.6')),
            set([package_spec('python'),
                 package_spec('numpy 1.7'),
                 package_spec('scipy 0.11 bld')])
        )
        self.assertEqual(
            apply_default_spec(specs, package_spec('numpy 1.6 bld')),
            set([package_spec('python'),
                 package_spec('numpy 1.7'),
                 package_spec('scipy 0.11 bld')])
        )
        self.assertEqual(
            apply_default_spec(specs, package_spec('scipy')),
            set([package_spec('python'),
                 package_spec('numpy 1.7'),
                 package_spec('scipy 0.11 bld')])
        )
        self.assertEqual(
            apply_default_spec(specs, package_spec('scipy 0.11')),
            set([package_spec('python'),
                 package_spec('numpy 1.7'),
                 package_spec('scipy 0.11 bld')])
        )
        self.assertEqual(
            apply_default_spec(specs, package_spec('scipy 0.11 bld')),
            set([package_spec('python'),
                 package_spec('numpy 1.7'),
                 package_spec('scipy 0.11 bld')])
        )

    def test_not_present(self):
        a, b = package_spec('python'), package_spec('numpy 1.7')
        specs = [a, b]
        self.assertEqual(
            apply_default_spec(specs, package_spec('scipy')),
            set([package_spec('python'),
                 package_spec('numpy 1.7'),
                 package_spec('scipy')])
        )
        self.assertEqual(
            apply_default_spec(specs, package_spec('scipy 0.11')),
            set([package_spec('python'),
                 package_spec('numpy 1.7'),
                 package_spec('scipy 0.11')])
        )
        self.assertEqual(
            apply_default_spec(specs, package_spec('scipy 0.11 bld')),
            set([package_spec('python'),
                 package_spec('numpy 1.7'),
                 package_spec('scipy 0.11 bld')])
        )


class test_sort_package_specs_by_name(unittest.TestCase):

    def test_simple(self):
        a, b, c = (
            package_spec('numpy 1.7'),
            package_spec('python'),
            package_spec('scipy 0.11 bld'),
        )
        specs = [c, a, b]
        self.assertEqual(
            sort_package_specs_by_name(specs),
            [a, b, c]
        )
    def test_reverse(self):
        a, b, c = (
            package_spec('numpy 1.7'),
            package_spec('python'),
            package_spec('scipy 0.11 bld'),
        )
        specs = [c, a, b]
        self.assertEqual(
            sort_package_specs_by_name(specs, reverse=True),
            [c, b, a]
        )


class test_group_package_specs_by_name(unittest.TestCase):

    def test_simple(self):
        specs = [
            package_spec('scipy 0.11 bld'),
            package_spec('python 2.7'),
            package_spec('numpy 1.7'),
            package_spec('scipy'),
            package_spec('numpy 1.6'),
        ]
        self.assertEqual(
            group_package_specs_by_name(specs),
            {
                'scipy' : set([package_spec('scipy'), package_spec('scipy 0.11 bld')]),
                'numpy' : set([package_spec('numpy 1.6'), package_spec('numpy 1.7')]),
                'python' : set([package_spec('python 2.7')]),
            }
        )


if __name__ == '__main__':
    unittest.main()
