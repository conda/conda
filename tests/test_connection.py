# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from conda.connection import CondaHttpAuth
from conda.gateways.anaconda_client import set_binstar_token, remove_binstar_token
from logging import getLogger
from unittest import TestCase

log = getLogger(__name__)


class CondaHttpAuthTests(TestCase):

    def test_add_binstar_token(self):
        try:
            # token already exists in url, don't add anything
            url = "https://conda.anaconda.org/t/dont-add-a-token/biopython/linux-64/repodata.json"
            assert CondaHttpAuth.add_binstar_token(url) == url

            # even if a token is there, don't use it
            set_binstar_token("https://api.anaconda.test", "tk-abacadaba-1029384756")
            url = "https://conda.anaconda.test/t/dont-add-a-token/biopython/linux-64/repodata.json"
            assert CondaHttpAuth.add_binstar_token(url) == url

            # now test adding the token
            url = "https://conda.anaconda.test/biopython/linux-64/repodata.json"
            new_url = "https://conda.anaconda.test/t/tk-abacadaba-1029384756/biopython/linux-64/repodata.json"
            assert CondaHttpAuth.add_binstar_token(url) == new_url
        finally:
            remove_binstar_token("https://api.anaconda.test")
