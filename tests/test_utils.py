from contextlib import contextmanager
from os.path import join
import random
import unittest
try:
    from unittest import mock
except ImportError:
    import mock


from conda import utils

SOME_PREFIX = "/some/prefix"
SOME_FILES = ["a", "b", "c"]


def create_mock_open():
    return mock.patch.object(utils, "open", create=True)


class can_open_all_TestCase(unittest.TestCase):
    def test_returns_true_on_success(self):
        with create_mock_open() as o:
            self.assertTrue(utils.can_open_all(SOME_PREFIX, SOME_FILES))

    def test_returns_false_if_unable_to_open_file_for_writing(self):
        with create_mock_open() as o:
            o.side_effect = IOError
            self.assertFalse(utils.can_open_all(SOME_PREFIX, SOME_FILES))

    def test_tries_to_open_all_files(self):
        random_files = ['%s' % i for i in range(random.randint(10, 20))]
        with create_mock_open() as o:
            utils.can_open_all(SOME_PREFIX, random_files)
        self.assertEqual(o.call_count, len(random_files))

    def test_passes_full_path_into_open(self):
        with create_mock_open() as o:
            utils.can_open_all(SOME_PREFIX, SOME_FILES)

        o.assert_has_calls([
            mock.call(join(SOME_PREFIX, SOME_FILES[0]), "ab"),
            mock.call().close(),
            mock.call(join(SOME_PREFIX, SOME_FILES[1]), "ab"),
            mock.call().close(),
            mock.call(join(SOME_PREFIX, SOME_FILES[2]), "ab"),
            mock.call().close(),
        ])
