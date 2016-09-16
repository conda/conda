# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import os

from conda.base.context import context, reset_context
from conda.connection import BinstarAuth
from logging import getLogger
from unittest import TestCase

log = getLogger(__name__)


class Request(object):

    def __init__(self, url):
        self.url = url


class BinstarAuthTests(TestCase):

    def test_dont_remove_token(self):
        # regression test associated with #3427
        url = 'https://conda.anaconda.org/t/tk-abc-def-123/binstar/osx-64/repodata.json.bz2'
        request = Request(url)
        ba = BinstarAuth()
        rback = ba(request)
        assert request.url == rback.url == url

    def test_add_anaconda_token(self):
        try:
            token = "tk-abc-def-123"
            os.environ['CONDA_ANACONDA_TOKEN'] = token
            reset_context()
            assert context.anaconda_token == token
            url = "https://conda.anaconda.org/binstar/osx-64/repodata.json.bz2"
            url_with_token = "https://conda.anaconda.org/t/%s/binstar/osx-64/repodata.json.bz2" % token
            request = Request(url)
            ba = BinstarAuth()
            rback = ba(request)
            assert request.url == rback.url == url_with_token
        finally:
            os.environ.pop('CONDA_ANACONDA_TOKEN', None)
            reset_context()
