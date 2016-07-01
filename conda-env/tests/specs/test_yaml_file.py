import unittest
import random
try:
    from unittest import mock
except ImportError:
    import mock

from conda_env import env
from conda_env.specs.yaml_file import YamlFileSpec


class TestYAMLFile(unittest.TestCase):
    def test_no_environment_file(self):
        spec = YamlFileSpec(name=None, filename='not-a-file')
        self.assertEqual(spec.can_handle(), False)

    def test_environment_file_exist(self):
        with mock.patch.object(env, 'from_file', return_value={}):
            spec = YamlFileSpec(name=None, filename='environment.yaml')
            self.assertTrue(spec.can_handle())

    def test_get_environment(self):
        r = random.randint(100, 200)
        with mock.patch.object(env, 'from_file', return_value=r):
            spec = YamlFileSpec(name=None, filename='environment.yaml')
            self.assertEqual(spec.environment, r)

    def test_filename(self):
        filename = "filename_{}".format(random.randint(100, 200))
        with mock.patch.object(env, 'from_file') as from_file:
            spec = YamlFileSpec(filename=filename)
            spec.environment
        from_file.assert_called_with(filename)
