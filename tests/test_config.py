# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import os
import unittest
from os.path import dirname, join

from conda.config import config_default, config, Configuration

# unset CIO_TEST
try:
    del os.environ['CIO_TEST']
except KeyError:
    pass


# Warning: config.load_condarc() will not delete keys that are not there any
# more.

class TestConfig(unittest.TestCase):

    # These tests are mostly to ensure API stability

    # use condarc from source tree to run these tests against
    config.rc_path = join(dirname(__file__), "condarcs", 'condarc')
    config.load_condarc()

    def test_globals(self):
        self.assertTrue(config.root_dir)
        self.assertTrue(config.pkgs_dir)
        self.assertTrue(config.envs_dir)
        self.assertTrue(config.default_prefix)
        self.assertTrue(config.platform)
        self.assertTrue(config.bits)
        self.assertTrue(config.subdir)
        self.assertTrue(config.arch_name)

#    def test_channel_urls(self):
#        config.subdir = 'foo'
#        urls = config.get_channel_urls()
#        self.assertEqual(urls,
#                         ['http://repo.continuum.io/pkgs/dev/foo/',
#                          'http://repo.continuum.io/pkgs/gpl/foo/',
#                          'http://repo.continuum.io/pkgs/free/foo/'])


class TestConfigPrecedence(unittest.TestCase):
    # Make sure that if multiple places have the same configuration values,
    # that they take the correct precedence against one another.

    def test_rc(self):
        config.rc_path = join(dirname(__file__), "condarcs", "condarc2")
        config.load_condarc()
        config.subdir = 'foo'

        self.assertEqual(config.get_channel_urls(), ['http://test.url/foo/'] +
            config_default.get_channel_urls())

        self.assertNotEqual(config.platform, 'myos')

        config.rc_path = None
        config.load_condarc()

    def test_no_rc(self):
        # Loading the rc file does not delete keys, so we have to build a new
        # configuration object to test this.
        config = Configuration()
        self.assertEqual(config.get_channel_urls(),
            config_default.get_channel_urls())

    def test_rc_system(self):
        config.rc_path = join(dirname(__file__), "condarcs", "condarc-system")
        self.assertRaises(SystemExit, lambda: config.load_condarc())

    def test_environment(self):
        for rc_path in [None, join(dirname(__file__), "condarcs", "condarc")]:
            config.rc_path = rc_path
            config.load_condarc()
            os.environ['CIO_TEST'] = '1'
            config.update_env_attrs()

            filer_channels = ['http://filer/pkgs/pro/foo/',
                'http://filer/pkgs/free/foo/']
            filer_channels2 = ['http://filer/test-pkgs/foo/'] + filer_channels

            self.assertEqual(config.get_channel_urls(), filer_channels)
            os.environ['CIO_TEST'] = '2'
            config.update_env_attrs()
            self.assertEqual(config.get_channel_urls(), filer_channels2)

    # TODO: test system vs. user rc files

if __name__ == '__main__':
    unittest.main()
