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
config.rc_path = join(dirname(__file__), 'condarc')

# unset CIO_TEST

try:
    del os.environ['CIO_TEST']
except KeyError:
    pass


class TestConfig(unittest.TestCase):

    # These tests are mostly to ensure API stability

    def __init__(self, *args, **kwargs):
        config.rc = config.load_condarc(config.rc_path)
        super(TestConfig, self).__init__(*args, **kwargs)

    def test_globals(self):
        self.assertTrue(config.root_dir)
        self.assertTrue(config.pkgs_dirs)
        self.assertTrue(config.envs_dirs)
        self.assertTrue(config.default_prefix)
        self.assertTrue(config.platform)
        self.assertTrue(config.subdir)
        self.assertTrue(config.arch_name)
        self.assertTrue(config.bits in (32, 64))

    def test_pkgs_dir_prefix(self):
        root_dir = config.root_dir
        root_pkgs = join(root_dir, 'pkgs')
        for pi, po in [
            (root_dir, root_pkgs),
            (join(root_dir, 'envs', 'foo'), root_pkgs),
            ('/usr/local/foo', '/usr/local/.pkgs'),
            ]:
            self.assertEqual(config.pkgs_dir_prefix(pi), po)

    def test_proxy_settings(self):
        self.assertEqual(config.get_proxy_servers(),
                         {'http': 'http://user:pass@corp.com:8080',
                          'https': 'https://user:pass@corp.com:8080'})

    def test_normalize_urls(self):
        current_platform = config.subdir
        assert config.DEFAULT_CHANNEL_ALIAS == 'https://conda.binstar.org/'
        assert config.rc.get('channel_alias') == 'https://your.repo/'

        for channel in config.normalize_urls(['defaults', 'system',
            'https://binstar.org/username', 'file:///Users/username/repo',
            'username']):
            assert channel.endswith('/%s/' % current_platform)
        self.assertEqual(config.normalize_urls([
            'defaults', 'system', 'https://conda.binstar.org/username',
            'file:///Users/username/repo', 'username'
            ], 'osx-64'),
            [
                'http://repo.continuum.io/pkgs/free/osx-64/',
                'http://repo.continuum.io/pkgs/pro/osx-64/',
                'https://your.repo/binstar_username/osx-64/',
                'http://some.custom/channel/osx-64/',
                'http://repo.continuum.io/pkgs/free/osx-64/',
                'http://repo.continuum.io/pkgs/pro/osx-64/',
                'https://conda.binstar.org/username/osx-64/',
                'file:///Users/username/repo/osx-64/',
                'https://your.repo/username/osx-64/',
                ])

if __name__ == '__main__':
    unittest.main()
