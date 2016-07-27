import unittest
try:
    from unittest import mock
except ImportError:
    import mock
from binstar_client import errors
from conda_env.utils.uploader import Uploader


class UploaderTestCase(unittest.TestCase):
    def test_unauthorized(self):
        uploader = Uploader('package', 'filename')
        with mock.patch.object(uploader.binstar, 'user') as get_user_mock:
            get_user_mock.side_effect = errors.Unauthorized
            self.assertEqual(uploader.authorized(), False)

    def test_authorized(self):
        uploader = Uploader('package', 'filename')
        with mock.patch.object(uploader.binstar, 'user') as get_user_mock:
            get_user_mock.return_value = {}
            self.assertEqual(uploader.authorized(), True)

    def test_package_already_exist(self):
        uploader = Uploader('package', 'filename')
        with mock.patch.object(uploader.binstar, 'user') as user_mock:
            user_mock.return_value = {'login': 'user'}
            with mock.patch.object(uploader.binstar, 'distribution') as distribution_mock:
                distribution_mock.return_value = True
                self.assertEqual(uploader.ensure_distribution(), False)
