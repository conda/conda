import unittest
try:
    from unittest import mock
except ImportError:
    import mock
from binstar_client import errors
from conda_env.utils.uploader import Uploader


class UploaderTestCase(unittest.TestCase):
    def test_upload(self):
        uploader = Uploader('package', 'filename')
        with mock.patch.object(uploader.binstar, 'user') as get_user_mock:
            get_user_mock.side_effect = errors.Unauthorized
            with self.assertRaises(errors.Unauthorized):
                uploader.upload()
