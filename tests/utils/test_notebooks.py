import json
import unittest
import tempfile
try:
    from unittest import mock
except ImportError:
    import mock
from conda_env.utils.notebooks import Notebook
from ..utils import support_file


notebook = {
    'cells': [],
    'metadata': {}
}


class NotebookTestCase(unittest.TestCase):
    def test_notebook_not_exist(self):
        to_yaml = mock.MagicMock(return_value='')
        env = mock.MagicMock(to_yaml=to_yaml)
        nb = Notebook('no-exist.ipynb')
        self.assertEqual(nb.inject(env), False)
        self.assertEqual(nb.msg, "no-exist.ipynb does not exist")

    def test_environment_already_exist(self):
        env = mock.MagicMock()
        nb = Notebook(support_file('notebook-with-env.ipynb'))
        self.assertEqual(nb.inject(env), False)

    def test_inject(self):
        to_yaml = mock.MagicMock(return_value='')
        env = mock.MagicMock(to_yaml=to_yaml)
        nb = Notebook(support_file('notebook.ipynb'))
        self.assertTrue(nb.inject(env))

        with open(support_file('notebook.ipynb'), 'w') as fb:
            fb.write(json.dumps(notebook))
