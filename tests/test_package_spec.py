
from distutils.version import LooseVersion
import unittest

from conda.package_spec import find_inconsistent_specs, package_spec

class test_package_spec(unittest.TestCase):

    def test_init(self):
        spec = package_spec("foo-bar 2.7.1.abc")
        self.assertEqual(
            spec.name, 
            "foo-bar"
        )
        self.assertEqual(
            spec.version, 
            LooseVersion('2.7.1.abc')
        )

class test_find_inconsistent_specs(unittest.TestCase):

    def test_simple(self):
        a, b, c = package_spec('python 2.7'), package_spec('python 3.1'), package_spec('python 2.7.1')
        specs = [a,b,c]
        self.assertEqual(
            find_inconsistent_specs(specs),
            set([package_spec('python 2.7.1'),
                 package_spec('python 3.1'),
                 package_spec('python 2.7')])
        )


if __name__ == '__main__':
    unittest.main()
