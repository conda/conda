# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from conda.models.dist import Dist
from logging import getLogger
from unittest import TestCase

log = getLogger(__name__)


class DistTests(TestCase):

    def test_dists(self):
        d = Dist.from_string("spyder-app-2.3.8-py27_0.tar.bz2")
        assert d.channel is None
        assert d.package_name == "spyder-app"
        assert d.version == "2.3.8"
        assert d.build_string == "py27_0"
        assert d.build_number == 0
        assert d.dist_name == "spyder-app-2.3.8-py27_0"

        assert d == Dist.from_string("spyder-app-2.3.8-py27_0")
        assert d != Dist.from_string("spyder-app-2.3.8-py27_1.tar.bz2")
