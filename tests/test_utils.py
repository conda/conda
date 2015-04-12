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


class can_open_TestCase(unittest.TestCase):
    def test_returns_true_if_can_open(self):
        with create_mock_open():
            self.assertTrue(utils.can_open("/some/path/some/file"))

    def test_returns_false_if_unable_to_open(self):
        with create_mock_open() as o:
            o.side_effect = IOError
            self.assertFalse(utils.can_open("/some/path/some/file"))

    def test_closes_file_handler_if_successful(self):
        with create_mock_open() as o:
            utils.can_open("/some/file")
        o.assert_has_calls([
            mock.call("/some/file", "ab"),
            mock.call().close(),
        ])


class can_open_all_TestCase(unittest.TestCase):
    def test_returns_true_on_success(self):
        with create_mock_open() as o:
            self.assertTrue(utils.can_open_all(SOME_PREFIX, SOME_FILES))

    def test_returns_false_if_unable_to_open_file_for_writing(self):
        with create_mock_open() as o:
            o.side_effect = IOError
            self.assertFalse(utils.can_open_all(SOME_PREFIX, SOME_FILES))

    def test_dispatches_to_can_can_call(self):
        with mock.patch.object(utils, "can_open") as can_open:
            utils.can_open_all(SOME_PREFIX, SOME_FILES)
        self.assertTrue(can_open.called)

    def test_tries_to_open_all_files(self):
        random_files = ['%s' % i for i in range(random.randint(10, 20))]
        with mock.patch.object(utils, "can_open") as can_open:
            utils.can_open_all(SOME_PREFIX, random_files)

    def test_stops_checking_as_soon_as_the_first_file_fails(self):
        with mock.patch.object(utils, "can_open") as can_open:
            can_open.side_effect = [True, False, True]
            self.assertFalse(utils.can_open_all(SOME_PREFIX, SOME_FILES))
        self.assertEqual(can_open.call_count, 2)
