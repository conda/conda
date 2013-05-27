# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import unittest
from os.path import dirname, join

import conda.config as config


# use condarc from source tree to run these tests against
config.rc_path = join(dirname(dirname(__file__)), 'condarc')


class TestConfig(unittest.TestCase):

    # These tests are mostly to ensure API stability

    def test_globals(self):
        self.assertTrue(config.root_dir)
        self.assertTrue(config.pkgs_dir)
        self.assertTrue(config.envs_dir)

        self.assertTrue(config.DEFAULT_ENV_PREFIX)

    def test_channel_urls(self):
        config.subdir = 'foo'
        urls = config.get_channel_urls()
        self.assertEqual(urls,
                         ['http://repo.continuum.io/pkgs/dev/foo/',
                          'http://repo.continuum.io/pkgs/gpl/foo/',
                          'http://repo.continuum.io/pkgs/free/foo/'])


if __name__ == '__main__':
    unittest.main()
