# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from conda.auxlib.compat import Utf8NamedTemporaryFile
from unittest import TestCase
import warnings

import pytest
from requests import HTTPError

from conda.common.compat import ensure_binary, PY3
from conda.common.url import path_to_url
from conda.gateways.anaconda_client import remove_binstar_token, set_binstar_token
from conda.gateways.connection.session import CondaHttpAuth, CondaSession
from conda.gateways.disk.delete import rm_rf

log = getLogger(__name__)


class CondaHttpAuthTests(TestCase):

    def test_add_binstar_token(self):
        try:
            # # token already exists in url, don't add anything
            # url = "https://conda.anaconda.org/t/dont-add-a-token/biopython/linux-64/repodata.json"
            # assert CondaHttpAuth.add_binstar_token(url) == url
            #
            # # even if a token is there, don't use it
            set_binstar_token("https://api.anaconda.test", "tk-abacadaba-1029384756")
            # url = "https://conda.anaconda.test/t/dont-add-a-token/biopython/linux-64/repodata.json"
            # assert CondaHttpAuth.add_binstar_token(url) == url

            # now test adding the token
            url = "https://conda.anaconda.test/biopython/linux-64/repodata.json"
            new_url = "https://conda.anaconda.test/t/tk-abacadaba-1029384756/biopython/linux-64/repodata.json"
            assert CondaHttpAuth.add_binstar_token(url) == new_url
        finally:
            remove_binstar_token("https://api.anaconda.test")


class CondaSessionTests(TestCase):

    def test_local_file_adapter_404(self):
        session = CondaSession()
        test_path = 'file:///some/location/doesnt/exist'
        r = session.get(test_path)
        with pytest.raises(HTTPError) as exc:
            r.raise_for_status()
        assert r.status_code == 404
        assert r.json()['path'] == test_path[len('file://'):]

    def test_local_file_adapter_200(self):
        test_path = None
        try:
            with Utf8NamedTemporaryFile(delete=False) as fh:
                test_path = fh.name
                fh.write(ensure_binary('{"content": "file content"}'))

            test_url = path_to_url(test_path)
            session = CondaSession()
            r = session.get(test_url)
            r.raise_for_status()
            assert r.status_code == 200
            assert r.json()['content'] == "file content"
        finally:
            if test_path is not None:
                rm_rf(test_path)
