# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import unittest
from os.path import dirname, join

import conda.config as config


# use condarc from source tree to run these tests against
config.RC_PATH = join(dirname(dirname(__file__)), 'condarc')


class TestConfig(unittest.TestCase):

    # These tests are mostly to ensure API stability

    def test_globals(self):
        self.assertTrue(config.CIO_DEFAULT_CHANNELS)
        self.assertTrue(isinstance(config.CIO_DEFAULT_CHANNELS, list))

        self.assertTrue(config.ROOT_DIR)
        self.assertTrue(config.PKGS_DIR)
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


if __name__ == '__main__':
    unittest.main()
