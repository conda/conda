from os.path import dirname
import unittest

from .decorators import skip_if_no_mock
from .helpers import mock
from .test_create import make_temp_prefix

from conda import history


class HistoryTestCase(unittest.TestCase):
    def test_works_as_context_manager(self):
        h = history.History("/path/to/prefix")
        self.assertTrue(getattr(h, '__enter__'))
        self.assertTrue(getattr(h, '__exit__'))

    @skip_if_no_mock
    def test_calls_update_on_enter_and_exit(self):
        h = history.History("/path/to/prefix")
        with mock.patch.object(h, 'update') as update:
            with h:
                self.assertEqual(1, update.call_count)
                pass
        self.assertEqual(2, update.call_count)

    @skip_if_no_mock
    def test_returns_history_object_as_context_object(self):
        h = history.History("/path/to/prefix")
        with mock.patch.object(h, 'update'):
            with h as h2:
                self.assertEqual(h, h2)

    @skip_if_no_mock
    def test_empty_history_check_on_empty_env(self):
        with mock.patch.object(history.History, 'file_is_empty') as mock_file_is_empty:
            with history.History(make_temp_prefix()) as h:
                self.assertEqual(mock_file_is_empty.call_count, 0)
            self.assertEqual(mock_file_is_empty.call_count, 1)
            assert h.file_is_empty()
        self.assertEqual(mock_file_is_empty.call_count, 2)
        assert not h.file_is_empty()


    @skip_if_no_mock
    def test_parse_on_empty_env(self):
        with mock.patch.object(history.History, 'parse') as mock_parse:
            with history.History(make_temp_prefix()) as h:
                self.assertEqual(mock_parse.call_count, 1)
                self.assertEqual(len(h.parse()), 0)
        self.assertEqual(len(h.parse()), 1)


class UserRequestsTestCase(unittest.TestCase):

    h = history.History(dirname(__file__))
    user_requests = h.get_user_requests()

    def test_len(self):
        self.assertEqual(len(self.user_requests), 6)

    def test_0(self):
        self.assertEqual(self.user_requests[0],
                         {'cmd': ['conda', 'update', 'conda'],
                          'date': '2016-02-16 13:31:33'})

    def test_last(self):
        self.assertEqual(self.user_requests[-1],
                         {'action': 'install',
                          'cmd': ['conda', 'install', 'pyflakes'],
                          'date': '2016-02-18 22:53:20',
                          'specs': ['pyflakes', 'conda', 'python 2.7*']})
