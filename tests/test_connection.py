# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re

import json

import os

import responses
from conda._vendor.auxlib.crypt import from_base64
from conda.base.context import context, reset_context
from conda.connection import BinstarAuth, CondaSession
from logging import getLogger
from unittest import TestCase

from conda._vendor.auxlib.logz import stringify

log = getLogger(__name__)


class Request(object):

    def __init__(self, url):
        self.url = url


# class BinstarAuthTests(TestCase):
#
#     def test_dont_remove_token(self):
#         # regression test associated with #3427
#         url = 'https://conda.anaconda.org/t/tk-abc-def-123/binstar/osx-64/repodata.json.bz2'
#         request = Request(url)
#         ba = BinstarAuth()
#         rback = ba(request)
#         assert request.url == rback.url == url
#
#     def test_add_anaconda_token(self):
#         try:
#             token = "tk-abc-def-123"
#             os.environ['CONDA_ANACONDA_TOKEN'] = token
#             reset_context()
#             assert context.anaconda_token == token
#             url = "https://conda.anaconda.org/binstar/osx-64/repodata.json.bz2"
#             url_with_token = "https://conda.anaconda.org/t/%s/binstar/osx-64/repodata.json.bz2" % token
#             request = Request(url)
#             ba = BinstarAuth()
#             rback = ba(request)
#             assert request.url == rback.url == url_with_token
#         finally:
#             os.environ.pop('CONDA_ANACONDA_TOKEN', None)
#             reset_context()




# class CondaSessionTests(TestCase):
#
#     def test_


# test netrc
# test context.proxy
# test username/password in url


@responses.activate
def test_calc_api():
    responses.add_callback(responses.GET, re.compile(r'.*'), callback=lambda r: (200, {}, ""))

    session = CondaSession()
    resp = session.get("http://username123:password456@www.google.com:1234/my/path.html")
    print(stringify(resp))

    assert len(responses.calls) == 1

    request = responses.calls[0].request
    auth_value = request.headers['Authorization'].split()
    assert auth_value[0] == "Basic"
    assert from_base64(auth_value[1]).decode('utf-8') == "username123:password456"



@responses.activate
def test_calc_api2():
    responses.add_callback(responses.GET, re.compile(r'.*'), callback=lambda r: (200, {}, ""))

    session = CondaSession()
    resp = session.get("http://username123:password456@www.google.com:1234/my/path.html")
    print(stringify(resp))

    assert len(responses.calls) == 1

    request = responses.calls[0].request
    auth_value = request.headers['Authorization'].split()
    assert auth_value[0] == "Basic"
    assert from_base64(auth_value[1]).decode('utf-8') == "username123:password456"
