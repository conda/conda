# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import os
import unittest
from os.path import dirname, join

from conda.config import config


# use condarc from source tree to run these tests against
config.rc_path = join((dirname(__file__)), 'condarc')
config.load_condarc()

# unset CIO_TEST
try:
    del os.environ['CIO_TEST']
except KeyError:
    pass


class TestConfig(unittest.TestCase):

    # These tests are mostly to ensure API stability

    def test_globals(self):
        self.assertTrue(config.root_dir)
        self.assertTrue(config.pkgs_dir)
        self.assertTrue(config.envs_dir)
        self.assertTrue(config.default_prefix)
        self.assertTrue(config.platform)
        self.assertTrue(config.bits)
        self.assertTrue(config.subdir)
        self.assertTrue(config.arch_name)

    def test_channel_urls(self):
        config.subdir = 'foo'
        urls = config.get_channel_urls()
        self.assertEqual(urls,
                         ['http://repo.continuum.io/pkgs/dev/foo/',
                          'http://repo.continuum.io/pkgs/gpl/foo/',
                          'http://repo.continuum.io/pkgs/free/foo/'])


if __name__ == '__main__':
    unittest.main()
