# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import os
import unittest
from os.path import dirname, join

from conda.config import config_default, config
from conda.api import normalize_urls

# unset CIO_TEST
try:
    del os.environ['CIO_TEST']
except KeyError:
    pass


class TestNormalize(unittest.TestCase):

    config.rc_path = join(dirname(__file__), "condarcs", "condarc")
    config.load_condarc()
    config.subdir = 'foo'

    rc_channels = ['http://repo.continuum.io/pkgs/dev/foo/',
        'http://repo.continuum.io/pkgs/gpl/foo/',
        'http://repo.continuum.io/pkgs/free/foo/']
    def test_normalize_urls(self):
        self.assertEqual(normalize_urls(config.base_urls), self.rc_channels)
        self.assertEqual(normalize_urls(['defaults']), config_default.get_channel_urls())
        self.assertEqual(normalize_urls(['defaults']),
            normalize_urls(config_default.base_urls))
        self.assertEqual(normalize_urls(['system']), self.rc_channels)
