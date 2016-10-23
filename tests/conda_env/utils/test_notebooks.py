import json
import unittest
from conda_env.utils.notebooks import Notebook
from ..utils import support_file

notebook = {
    "metadata": {
        "name": "",
        "signature": ""
    },
    "nbformat": 3,
    "nbformat_minor": 0,
    "worksheets": [
        {
            "cells": []
        }
    ]
}


class NotebookTestCase(unittest.TestCase):
    def test_notebook_not_exist(self):
        nb = Notebook('no-exist.ipynb')
        self.assertEqual(nb.inject('content'), False)
        self.assertEqual(nb.msg, "no-exist.ipynb may not exist or you don't have adequate permissions")

    def test_environment_already_exist(self):
        nb = Notebook(support_file('notebook-with-env.ipynb'))
        self.assertEqual(nb.inject('content'), False)

    def test_inject_env(self):
        nb = Notebook(support_file('notebook.ipynb'))
        self.assertTrue(nb.inject('content'))

        with open(support_file('notebook.ipynb'), 'w') as fb:
            fb.write(json.dumps(notebook, sort_keys=True))

    def test_inject(self):
        nb = Notebook(support_file('notebook.ipynb'))
        self.assertTrue(nb.inject('user/environment'))

        with open(support_file('notebook.ipynb'), 'w') as fb:
            fb.write(json.dumps(notebook, sort_keys=True))
