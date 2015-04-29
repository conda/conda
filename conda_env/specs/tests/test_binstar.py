import unittest
try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO
from mock import patch, MagicMock
from binstar_client import errors
from ..binstar import BinstarSpec, get_binstar
from ...exceptions import EnvironmentFileDoesNotExist


class TestBinstarSpec(unittest.TestCase):
    def test_invalid_handler(self):
        spec = BinstarSpec('invalid')
        self.assertEqual(spec.valid_handle(), False)
        self.assertEqual(spec.can_process(), False)

    def test_package_not_exist(self):
        with patch('conda_env.specs.binstar.get_binstar') as get_binstar_mock:
            package = MagicMock(side_effect=errors.NotFound('msg'))
            binstar = MagicMock(package=package)
            get_binstar_mock.return_value = binstar
            spec = BinstarSpec('darth/no-exist')
            self.assertEqual(spec.package, None)
            self.assertEqual(spec.can_process(), False)

    def test_package_without_environment_file(self):
        with patch('conda_env.specs.binstar.get_binstar') as get_binstar_mock:
            package = MagicMock(return_value={'files': []})
            binstar = MagicMock(package=package)
            get_binstar_mock.return_value = binstar
            spec = BinstarSpec('darth/no-env-file')

            with self.assertRaises(EnvironmentFileDoesNotExist):
                spec.environment

    def test_download_environment(self):
        fake_package = {
            'files': [{'type': 'env', 'version': '1', 'basename': 'environment.yml'}]
        }
        fake_req = MagicMock(raw=StringIO())
        with patch('conda_env.specs.binstar.get_binstar') as get_binstar_mock:
            package = MagicMock(return_value=fake_package)
            downloader = MagicMock(return_value=fake_req)
            binstar = MagicMock(package=package, download=downloader)
            get_binstar_mock.return_value = binstar

            spec = BinstarSpec('darth/no-env-file')
            self.assertEqual(spec.environment, '')


if __name__ == '__main__':
    unittest.main()
