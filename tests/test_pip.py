import random
import unittest

from conda import pip


def generate_random_version():
    return '%s.%s' % (random.randint(1, 5), random.randint(0, 20))


class PipPackageTestCase(unittest.TestCase):
    def test_acts_like_dict(self):
        p = pip.PipPackage(name='foo', version='0.1')
        self.assertIsInstance(p, dict)

    def test_simple_string_as_spec(self):
        version = generate_random_version()
        p = pip.PipPackage(name='bar', version=version)
        expected = 'bar-{version}-<pip>'.format(version=version)
        self.assertEqual(expected, str(p))

    def test_handles_case_where_path_provided(self):
        version = generate_random_version()
        path = '/some/path/%s/foo' % random.randint(0, 10)
        p = pip.PipPackage(name='baz', path=path, version=version)

        expected = 'baz ({path})-{version}-<pip>'.format(path=path,
                                                         version=version)
        self.assertEqual(expected, str(p))
