""" Test if we can import everything from conda.
This basically tests syntax correctness and whether the internal imports work.
Created to test py3k compatibility.
"""

from __future__ import print_function, division, absolute_import

import os
import sys
import unittest
import conda
from conda.utils import on_win

PREFIX = os.path.dirname(os.path.abspath(conda.__file__))


class TestImportAllConda(unittest.TestCase):

    def _test_import(self, subpackage):
        # Prepare
        prefix = PREFIX
        module_prefix = 'conda'
        if subpackage:
            prefix = os.path.join(prefix, subpackage)
            module_prefix = '%s.%s' % (module_prefix, subpackage)

        # Try importing root
        __import__(module_prefix)

        # Import each module in given (sub)package
        for fname in os.listdir(prefix):
            # Discard files that are not of interest
            if fname.startswith('__'):
                continue
            elif not fname.endswith('.py'):
                continue
            elif fname.startswith('windows') and not on_win:
                continue
            # Import
            modname = module_prefix + '.' + fname.split('.')[0]
            print('importing', modname)
            __import__(modname)


    def test_import_root(self):
        self._test_import('')

    def test_import_cli(self):
        self._test_import('cli')

    def test_import_progressbar(self):
        self._test_import('_vendor')


if __name__ == '__main__':
    unittest.main()
