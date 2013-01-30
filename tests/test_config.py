# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import unittest

from conda import config

class TestConfig(unittest.TestCase):

    # These tests are mostly to ensure API stability

    def test_globals(self):
        self.assertTrue(config.CIO_DEFAULT_CHANNELS)
        self.assertTrue(isinstance(config.CIO_DEFAULT_CHANNELS, list))

        self.assertTrue(config.ROOT_DIR)
        self.assertTrue(config.PACKAGES_DIR)
        self.assertTrue(config.ENVS_DIR)

        self.assertTrue(config.DEFAULT_ENV_PREFIX)
        self.assertTrue(config.RC_PATH)

    def test_load_condrc(self):
        rc = config._load_condarc("condarc")
        self.assertEqual(rc.keys(), ['channels', 'locations'])
        self.assertEqual(rc['locations'], ['~/envs'])
        self.assertEqual(
            rc['channels'],
            ['http://repo.continuum.io/pkgs/dev',
             'http://repo.continuum.io/pkgs/gpl',
             'http://repo.continuum.io/pkgs/free']
        )

    def test_config(self):
        conf = config.Config()
        self.assertTrue(isinstance(conf.conda_version, str))
        self.assertTrue(isinstance(conf.platform, str))
        self.assertTrue(isinstance(conf.root_dir, str))
        self.assertTrue(isinstance(conf.packages_dir, str))
        self.assertTrue(isinstance(conf.system_location, str))
        self.assertTrue(isinstance(conf.user_locations, list))
        self.assertTrue(isinstance(conf.locations, list))
        self.assertTrue(isinstance(conf.channel_base_urls, list))
        self.assertTrue(isinstance(conf.channel_urls, list))
        self.assertTrue(isinstance(conf.environment_paths, list))

if __name__ == '__main__':
    unittest.main()
