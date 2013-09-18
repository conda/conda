# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import os
import unittest
from os.path import dirname, join

import conda.config as config


# use condarc from source tree to run these tests against
config.rc_path = join(dirname(dirname(__file__)), 'condarc')

# unset CIO_TEST

try:
    del os.environ['CIO_TEST']
except KeyError:
    pass


class TestConfig(unittest.TestCase):

    # These tests are mostly to ensure API stability

    def test_globals(self):
        self.assertTrue(config.root_dir)
        self.assertTrue(config.pkgs_dirs)
        self.assertTrue(config.envs_dirs)
        self.assertTrue(config.default_prefix)
        self.assertTrue(config.platform)
        self.assertTrue(config.bits)
        self.assertTrue(config.subdir)
        self.assertTrue(config.arch_name)

    def test_proxy_settings(self):
        config.rc = config.load_condarc(config.rc_path)
        servers = config.get_proxy_servers()
        self.assertEqual(len(servers),2)
        self.assertEqual(servers['http'],'http://user:pass@corp.com:8080')
        self.assertEqual(servers['https'], 'https://user:pass@corp.com:8080')


if __name__ == '__main__':
    unittest.main()
