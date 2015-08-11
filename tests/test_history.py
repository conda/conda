import unittest

from .decorators import skip_if_no_mock
from .helpers import mock

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
