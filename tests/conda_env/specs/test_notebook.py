import unittest
from conda_env import env
from conda_env.specs.notebook import NotebookSpec
from ..utils import support_file


class TestNotebookSpec(unittest.TestCase):
    def test_no_notebook_file(self):
        spec = NotebookSpec(support_file('simple.yml'))
        self.assertEqual(spec.can_handle(), False)

    def test_notebook_no_env(self):
        spec = NotebookSpec(support_file('notebook.ipynb'))
        self.assertEqual(spec.can_handle(), False)

    def test_notebook_with_env(self):
        spec = NotebookSpec(support_file('notebook_with_env.ipynb'))
        self.assertTrue(spec.can_handle())
        self.assertIsInstance(spec.environment, env.Environment)
