import unittest
try:
    from unittest import mock
except ImportError:
    import mock

from conda_env import env
from conda_env.specs.yaml_file import YamlFileSpec
from conda_env.exceptions import EnvironmentFileNotFound


class TestYAMLFile(unittest.TestCase):
    def test_no_environment_file(self):
        spec = YamlFileSpec(name=None, filename='not-a-file')
        with self.assertRaises(EnvironmentFileNotFound):
            spec.can_handle()

    def test_environment_file_exist(self):
        with mock.patch.object(env, 'from_file', return_value={}):
            spec = YamlFileSpec(name=None, filename='environment.yaml')
            self.assertTrue(spec.can_handle())

    def test_get_environment(self):
        with mock.patch.object(env, 'from_file', return_value={}):
            spec = YamlFileSpec(name=None, filename='environment.yaml')
            self.assertIsInstance(spec.environment, dict)
